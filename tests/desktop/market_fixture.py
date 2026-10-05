"""Synthetic market evidence for deterministic persistence and operation tests."""
from dataclasses import replace
import json

from backend.app.contracts import EvidenceBundle
from backend.app.identity import ResolvedIdentity
from backend.app.market_history import parse_yahoo_chart
from backend.app.market_mapping import map_yahoo_history
from backend.app.market_evidence import attach_market
from tests.desktop.financial_fixture import AT, financial_bundle, financial_result


def market_bundle(*, financials=True, valuations=False, estimates=False):
    if financials:
        base = financial_bundle()
    else:
        instrument = financial_result().instrument
        base = EvidenceBundle(asset=instrument.asset, identity_verification=instrument.verification, created_at=AT)
    mapped = map_yahoo_history(market_candidate(), ResolvedIdentity(base.asset, base.identity_verification), at=AT)
    if valuations:
        mapped = replace(mapped, valuations=valuation_candidate())
    if estimates:
        mapped = replace(mapped, estimates=estimate_candidate())
    return attach_market(base, mapped, personal_mode=True, created_at=AT)


def market_candidate():
    data = {"chart": {"error": None, "result": [{
        "meta": {"symbol": "SYN", "currency": "USD", "exchangeTimezoneName": "America/New_York",
                 "exchangeName": "NMS", "fullExchangeName": "NasdaqGS", "instrumentType": "EQUITY", "longName": "Synthetic company"},
        "timestamp": [1767364200, 1767623400],
        "indicators": {"quote": [{"open": [10, 11], "high": [12, 15], "low": [9, 10], "close": [11, 14],
                                   "volume": [9007199254740993, 100]}], "adjclose": [{"adjclose": [10, 14]}]},
        "events": {"dividends": {"event": {"date": 1767364200, "amount": 0.5}},
                   "splits": {"event": {"date": 1767364200, "numerator": 3, "denominator": 2}}},
    }]}}
    raw = json.dumps(data).encode().replace(b'"amount": 0.5', b'"amount": 0.123456789012345678')
    return replace(parse_yahoo_chart(raw, "SYN", "2026-01-01", "2026-01-31"), retrieved_at=AT)


def valuation_candidate():
    from backend.app.market_valuations import parse_valuations
    rows = []
    for kind, period, currency, values in (
        ("quarterlyPeRatio", "3M", None, ["28.123456789012345678", None]),
        ("annualMarketCap", "12M", "USD", ["9007199254740993", "9007199254740992"]),
        ("trailingPeRatio", "TTM", None, ["28.123456789012345678", "29.5"]),
    ):
        rows.append({"meta": {"symbol": ["SYN"], "type": [kind]}, kind: [
            {"asOfDate": date, "periodType": period, "currencyCode": currency,
             "reportedValue": {"raw": value}} for date, value in zip(("2026-01-02", "2026-01-05"), values)]})
    raw = json.dumps({"timeseries": {"result": rows, "error": None}}).encode()
    for value in (b"28.123456789012345678", b"9007199254740993", b"9007199254740992", b"29.5"):
        raw = raw.replace(b'"' + value + b'"', value)
    return replace(parse_valuations(raw, "SYN", "2026-01-01", "2026-01-31"), retrieved_at=AT)


def estimate_candidate():
    from backend.app.market_estimates import parse_estimates
    from tests.desktop.test_market_estimates import payload
    data = payload()
    row = data["quoteSummary"]["result"][0]["earningsTrend"]["trend"][0]
    row["endDate"] = "2026-03-31"
    raw = json.dumps(data).replace("1.25", "1.25000000000000001").encode()
    return replace(parse_estimates(raw, "SYN"), retrieved_at=AT)
