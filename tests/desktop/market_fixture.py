"""Synthetic market evidence for deterministic persistence and operation tests."""
from dataclasses import replace
import json

from backend.app.contracts import EvidenceBundle
from backend.app.identity import ResolvedIdentity
from backend.app.market_history import parse_yahoo_chart
from backend.app.market_mapping import map_yahoo_history
from backend.app.market_evidence import attach_market
from tests.desktop.financial_fixture import AT, financial_bundle, financial_result


def market_bundle(*, financials=True):
    if financials:
        base = financial_bundle()
    else:
        instrument = financial_result().instrument
        base = EvidenceBundle(asset=instrument.asset, identity_verification=instrument.verification, created_at=AT)
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
    history = replace(parse_yahoo_chart(raw, "SYN", "2026-01-01", "2026-01-31"), retrieved_at=AT)
    mapped = map_yahoo_history(history, ResolvedIdentity(base.asset, base.identity_verification), at=AT)
    return attach_market(base, mapped, personal_mode=True, created_at=AT)
