import asyncio
import base64
import copy
import json
from datetime import datetime, timezone

import pytest

from backend.app.market_history import MAX_BYTES, MarketDataError
from backend.app.market_transport import YahooPolicy, YahooValuationPolicy
from backend.app.market_valuations import parse_valuations, valuation_request
from backend.app import yfinance_worker

START, END = "2021-01-01", "2026-01-31"


def payload(symbol="TEST"):
    return {"timeseries": {"error": None, "result": [
        {"meta": {"symbol": [symbol], "type": ["quarterlyPeRatio"]},
         "quarterlyPeRatio": [{"asOfDate": "2025-12-31", "periodType": "3M", "currencyCode": "USD",
                               "reportedValue": {"raw": 1.25}}]},
        {"meta": {"symbol": [symbol], "type": ["annualMarketCap"]},
         "annualMarketCap": [{"asOfDate": "2025-12-31", "periodType": "12M", "currencyCode": "USD",
                              "reportedValue": {"raw": 9007199254740993}}]},
    ]}}


def parsed(data=None):
    return parse_valuations(json.dumps(data or payload()).encode(), "TEST", START, END)


def test_original_decimals_dates_and_missing_metrics_without_recalculation():
    raw = json.dumps(payload()).replace("1.25", "1.25000000000000001").encode()
    candidate = parse_valuations(raw, "TEST", START, END)
    assert {p.value for p in candidate.points} == {"9007199254740993", "1.25000000000000001"}
    assert {p.date for p in candidate.points} == {"2025-12-31"}
    assert {(p.metric, p.sampling, p.period_type) for p in candidate.points} == {
        ("PeRatio", "quarterly", "3M"), ("MarketCap", "annual", "12M")}
    assert candidate.retrieved_at is None and len(candidate.content_hash) == 64
    assert candidate.source_url == "https://finance.yahoo.com/quote/TEST/key-statistics/"


@pytest.mark.parametrize("field,value", [("asOfDate", "2027-01-01"), ("asOfDate", "2020-12-31"),
    ("asOfDate", "2025-2-1"), ("periodType", "12M"), ("currencyCode", "EUR"),
    ("reportedValue", {"raw": True}), ("reportedValue", {"raw": "1.25"}),
    ("reportedValue", {"raw": 1e50})])
def test_reject_wrong_dates_periods_currency_and_numbers(field, value):
    data = payload()
    data["timeseries"]["result"][0]["quarterlyPeRatio"][0][field] = value
    with pytest.raises(MarketDataError, match="invalid_yahoo_valuations"):
        parsed(data)


@pytest.mark.parametrize("change", ["symbol", "type", "extra_type", "duplicate_series", "duplicate_date", "error"])
def test_reject_ambiguous_or_foreign_series(change):
    data = payload()
    result = data["timeseries"]["result"]
    if change == "symbol":
        result[0]["meta"]["symbol"] = ["OTHER"]
    elif change == "type":
        result[0]["meta"]["type"] = ["quarterlyForwardPeRatio"]
    elif change == "extra_type":
        result[0]["quarterlyForwardPeRatio"] = []
    elif change == "duplicate_series":
        result.append(copy.deepcopy(result[0]))
    elif change == "duplicate_date":
        result[0]["quarterlyPeRatio"].append(copy.deepcopy(result[0]["quarterlyPeRatio"][0]))
    else:
        data["timeseries"]["error"] = {"description": "private diagnostic"}
    with pytest.raises(MarketDataError, match="invalid_yahoo_valuations"):
        parsed(data)


def test_missing_and_empty_observations_stay_missing():
    data = payload()
    data["timeseries"]["result"][0]["quarterlyPeRatio"][0]["reportedValue"] = {"raw": None}
    assert next(p for p in parsed(data).points if p.metric == "PeRatio").value is None
    assert not parsed({"timeseries": {"result": [], "error": None}}).points


def test_unitless_ratios_do_not_invent_currency_and_currencyless_amounts_are_withheld():
    data = payload()
    for item in data["timeseries"]["result"]:
        del item[item["meta"]["type"][0]][0]["currencyCode"]
    rows = {p.metric: p for p in parsed(data).points}
    assert rows["PeRatio"].value == "1.25" and rows["PeRatio"].currency is None
    assert rows["MarketCap"].value is None and rows["MarketCap"].reason == "currency_missing"


def test_trailing_reported_period_is_preserved_separately_from_sampling():
    data = payload()
    item = data["timeseries"]["result"][0]
    item["meta"]["type"] = ["trailingPeRatio"]
    item["trailingPeRatio"] = item.pop("quarterlyPeRatio")
    item["trailingPeRatio"][0]["periodType"] = "TTM"
    point = next(p for p in parsed(data).points if p.metric == "PeRatio")
    assert point.sampling == "trailing" and point.period_type == "TTM"


@pytest.mark.parametrize("raw,code", [(b"x" * (MAX_BYTES + 1), "response_size"),
    (b'{"timeseries":{},"timeseries":{}}', "duplicate_field"),
    (b'{"value":NaN}', "invalid_number")], ids=["oversize", "duplicate", "nonfinite"])
def test_original_response_is_bounded_and_strict(raw, code):
    with pytest.raises(MarketDataError, match=code):
        parse_valuations(raw, "TEST", START, END)


def test_one_exact_valuation_request_and_no_history_policy_expansion():
    url, params = valuation_request("TEST", START, END)
    policy = YahooValuationPolicy("TEST", START, END)
    assert policy.before("GET", "https://fc.yahoo.com") == "cookie"
    assert policy.before("GET", "https://query1.finance.yahoo.com/v1/test/getcrumb") == "crumb"
    assert policy.before("GET", url, params) == "valuation"
    policy.received("valuation", 200, b"original")
    assert policy.raw == b"original" and policy.count == 3
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        policy.before("GET", url, params)
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        YahooPolicy("TEST", START, END).before("GET", url, params)


@pytest.mark.parametrize("change", ["method", "symbol", "type", "date", "host", "chart", "query", "float_date"])
def test_valuation_transport_does_not_expand_scope(change):
    url, params = valuation_request("TEST", START, END)
    method = "GET"
    if change == "method":
        method = "POST"
    elif change in ("symbol", "type"):
        params[change] = "OTHER"
    elif change == "date":
        params["period1"] = 0
    elif change == "float_date":
        params["period1"] = float(params["period1"])
    elif change == "host":
        url = url.replace("query2.finance.yahoo.com", "localhost")
    elif change == "query":
        url += "?token=secret"
    else:
        url = "https://query2.finance.yahoo.com/v8/finance/chart/TEST"
        params = {"range": "1d", "interval": "1d"}
    policy = YahooValuationPolicy("TEST", START, END)
    with pytest.raises(MarketDataError, match="request_not_allowed"):
        policy.before(method, url, params)
    assert policy.count == 0


def test_worker_preserves_original_payload_and_retrieval_time(monkeypatch):
    calls = []
    async def fake(request):
        calls.append(request)
        return {"raw": base64.b64encode(json.dumps(payload()).encode()).decode(), "requests": 3, "version": yfinance_worker.VERSION}
    monkeypatch.setattr(yfinance_worker, "run_worker", fake)
    candidate, count = asyncio.run(yfinance_worker.fetch_yahoo_valuations("TEST", START, END))
    assert calls == [{"symbol": "TEST", "start": START, "end": END, "operation": "valuation"}]
    assert count == 3 and candidate.retrieved_at <= datetime.now(timezone.utc)
    assert any(p.value == "9007199254740993" for p in candidate.points)
