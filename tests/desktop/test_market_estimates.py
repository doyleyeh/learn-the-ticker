import asyncio
import base64
import copy
import json
from datetime import datetime, timezone

import pytest

from backend.app.market_estimates import estimate_request, parse_estimates
from backend.app.market_history import MAX_BYTES, MarketDataError
from backend.app.market_transport import YahooEstimatePolicy, YahooPolicy, YahooValuationPolicy
from backend.app import yfinance_worker

START, END = "2026-01-01", "2026-10-04"


def payload():
    return {"quoteSummary": {"error": None, "result": [{"earningsTrend": {"trend": [
        {"period": "0q", "endDate": "2026-12-31", "earningsEstimate": {
            "earningsCurrency": "USD", "avg": {"raw": 1.25, "fmt": "untrusted"},
            "low": {"raw": -1}, "high": {"raw": 2}, "numberOfAnalysts": {"raw": 12}},
         "revenueEstimate": {"revenueCurrency": "USD", "avg": {"raw": 9007199254740993}}},
        {"period": "+5y", "growth": {"raw": 0.2}},
    ]}}]}}


def row(data):
    return data["quoteSummary"]["result"][0]["earningsTrend"]["trend"][0]


def parsed(data=None):
    return parse_estimates(json.dumps(data if data is not None else payload()).encode(), "TEST")


def test_original_estimates_keep_decimals_periods_and_per_metric_units():
    raw = json.dumps(payload()).replace("1.25", "1.25000000000000001").encode()
    candidate = parse_estimates(raw, "TEST")
    eps, revenue = candidate.points
    assert eps.average == "1.25000000000000001" and eps.low == "-1" and eps.analysts == 12
    assert revenue.average == "9007199254740993" and revenue.analysts is None
    assert eps.period_end == "2026-12-31" and eps.period == "0q"
    assert eps.currency == revenue.currency == "USD"
    assert candidate.retrieved_at is None and len(candidate.content_hash) == 64
    assert candidate.source_url == "https://finance.yahoo.com/quote/TEST/analysis/"
    assert len(candidate.points) == 2  # No long-term growth or inferred periods.


@pytest.mark.parametrize("change,reason", [("currency", "currency_missing"), ("date", "period_missing"), ("values", "value_missing")])
def test_missing_support_never_infers_from_other_fields(change, reason):
    data = payload()
    target = row(data)
    if change == "currency":
        del target["earningsEstimate"]["earningsCurrency"]
    elif change == "date":
        del target["endDate"]
    else:
        for key in ("avg", "low", "high"):
            target["earningsEstimate"][key] = {"fmt": "1.2M"}
    point = parsed(data).points[0]
    assert point.reason == reason and point.average is point.low is point.high is None
    if change == "currency":
        assert parsed(data).points[1].average == "9007199254740993"


@pytest.mark.parametrize("field,value", [("avg", {"raw": True}), ("avg", {"raw": "1.25"}),
    ("avg", {"raw": 1e50}), ("avg", 12), ("numberOfAnalysts", {"raw": 2.5}),
    ("numberOfAnalysts", {"raw": -1}), ("numberOfAnalysts", {"raw": 10001}),
    ("earningsCurrency", "EUR"), ("earningsCurrency", "<script>")])
def test_invalid_numbers_counts_and_currency_are_rejected(field, value):
    data = payload()
    row(data)["earningsEstimate"][field] = value
    with pytest.raises(MarketDataError, match="invalid_yahoo_estimates"):
        parsed(data)


@pytest.mark.parametrize("change", ["error", "extra_result", "module", "symbol", "trend_symbol", "period",
    "duplicate", "rows", "bad_date", "bad_metric", "bad_trend"])
def test_wrong_or_ambiguous_response_is_rejected(change):
    data = payload()
    item = data["quoteSummary"]["result"][0]
    trend = item["earningsTrend"]["trend"]
    if change == "error":
        data["quoteSummary"]["error"] = {"description": "private provider diagnostic"}
    elif change == "extra_result":
        data["quoteSummary"]["result"].append(copy.deepcopy(item))
    elif change == "module":
        item["recommendationTrend"] = {}
    elif change == "symbol":
        item["symbol"] = "OTHER"
    elif change == "trend_symbol":
        item["earningsTrend"]["symbol"] = "OTHER"
    elif change == "period":
        row(data)["period"] = "12M"
    elif change == "duplicate":
        trend.append(copy.deepcopy(trend[0]))
    elif change == "rows":
        trend.extend(copy.deepcopy(trend) * 3)
    elif change == "bad_date":
        row(data)["endDate"] = "2026-2-1"
    elif change == "bad_metric":
        row(data)["revenueEstimate"] = "diagnostic"
    else:
        item["earningsTrend"]["trend"] = {}
    with pytest.raises(MarketDataError, match="invalid_yahoo_estimates"):
        parsed(data)


def test_empty_dataset_and_missing_metric_remain_explicit():
    data = payload()
    del row(data)["revenueEstimate"]
    assert parsed(data).points[1].reason == "currency_missing"
    data["quoteSummary"]["result"][0]["earningsTrend"]["trend"] = []
    assert parsed(data).points == ()


@pytest.mark.parametrize("raw,code", [(b"x" * (MAX_BYTES + 1), "response_size"),
    (b'{"quoteSummary":{},"quoteSummary":{}}', "duplicate_field"),
    (b'{"value":NaN}', "invalid_number")], ids=["oversize", "duplicate", "nonfinite"])
def test_response_size_duplicate_keys_and_nonfinite(raw, code):
    with pytest.raises(MarketDataError, match=code):
        parse_estimates(raw, "TEST")


def test_one_exact_request_and_original_capture_without_expanding_old_policies():
    url, params = estimate_request("TEST")
    policy = YahooEstimatePolicy("TEST", START, END)
    assert policy.before("GET", "https://fc.yahoo.com") == "cookie"
    assert policy.before("GET", "https://query1.finance.yahoo.com/v1/test/getcrumb") == "crumb"
    assert policy.before("GET", url, params) == "estimates"
    policy.received("estimates", 200, b"original")
    assert policy.count == 3 and policy.raw == b"original"
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        policy.before("GET", url, params)
    for cls in (YahooPolicy, YahooValuationPolicy):
        with pytest.raises(MarketDataError, match="request_not_allowed"):
            cls("TEST", START, END).before("GET", url, params)


@pytest.mark.parametrize("change", ["method", "symbol", "modules", "host", "path", "query", "extra"])
def test_transport_scope_is_exact(change):
    url, params = estimate_request("TEST")
    method = "GET"
    if change == "method":
        method = "POST"
    elif change in ("symbol", "modules"):
        params[change] = "OTHER"
    elif change == "host":
        url = url.replace("query2.finance.yahoo.com", "localhost")
    elif change == "path":
        url = url.replace("TEST", "OTHER")
    elif change == "query":
        url += "?token=private"
    else:
        params["extra"] = "ignored"
    policy = YahooEstimatePolicy("TEST", START, END)
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        policy.before(method, url, params)
    assert policy.count == 0


@pytest.mark.parametrize("status,code", [(401, "source_access_denied"), (403, "source_access_denied"),
    (429, "source_rate_limited"), (302, "source_redirect")])
def test_denial_is_sticky_and_never_retries(status, code):
    policy = YahooEstimatePolicy("TEST", START, END)
    url, params = estimate_request("TEST")
    policy.before("GET", url, params)
    with pytest.raises(MarketDataError, match=code):
        policy.received("estimates", status, b"raw private diagnostic")
    with pytest.raises(MarketDataError, match=code):
        policy.before("GET", url, params)
    assert policy.count == 1 and policy.raw is None


def test_worker_original_payload_and_time(monkeypatch):
    calls = []
    async def fake(request):
        calls.append(request)
        return {"raw": base64.b64encode(json.dumps(payload()).encode()).decode(), "requests": 3, "version": yfinance_worker.VERSION}
    monkeypatch.setattr(yfinance_worker, "run_worker", fake)
    candidate, count = asyncio.run(yfinance_worker.fetch_yahoo_estimates("TEST", START, END))
    assert calls == [{"symbol": "TEST", "start": START, "end": END, "operation": "estimates"}]
    assert count == 3 and candidate.retrieved_at <= datetime.now(timezone.utc)
    assert candidate.points[1].average == "9007199254740993"


@pytest.mark.parametrize("operation", [None, "recommendations", "earningsTrend", 42])
def test_invalid_worker_operation_never_opens_session(operation):
    with pytest.raises(MarketDataError, match="invalid_worker_request"):
        yfinance_worker.retrieve({"symbol": "TEST", "start": START, "end": END, "operation": operation})
