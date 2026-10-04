"""Synthetic sources for deterministic tests and isolated PostgreSQL restore checks."""
import json
from datetime import datetime, timezone

from backend.app.contracts import EvidenceBundle
from backend.app.figi_identity import parse_figi_response, valid_figi
from backend.app.financial_evidence import attach_financials
from backend.app.identity import parse_sec_listings
from backend.app.structured_financials import SecFinancialAdapter

AT = datetime(2026, 10, 4, tzinfo=timezone.utc)


def financial_result(*, conflict=False):
    figi = next("BBG00000000" + str(digit) for digit in range(10) if valid_figi("BBG00000000" + str(digit)))
    instrument = parse_figi_response(json.dumps([{"data": [{"figi": figi, "ticker": "SYN",
        "name": "SYNTHETIC COMPANY", "exchCode": "UW", "securityType": "Common Stock",
        "securityType2": "Common Stock", "marketSector": "Equity"}]}]).encode(), query="SYN", search=False, retrieved_at=AT)[0]
    issuer = parse_sec_listings(json.dumps({"fields": ["cik", "name", "ticker", "exchange"],
        "data": [[1, "SYNTHETIC COMPANY", "SYN", "Nasdaq"]]}).encode(), AT)[0]
    class Resolver:
        @property
        def sec(self):
            return self

        def resolve(self, query):
            return [issuer] if query == "SYN" else [instrument]

    base = {"start": "2025-01-01", "end": "2025-12-31", "val": 9007199254740993,
            "accn": "0000009999-26-000001", "filed": "2026-02-01", "form": "10-K", "fy": 2025, "fp": "FY"}
    rows = [base, {**base, "val": 9007199254740992, "filed": "2026-03-01", "accn": "0000009999-26-000002"}]
    if conflict:
        rows.append({**rows[-1], "val": 9007199254740991, "accn": "0000009999-26-000003"})
    raw = json.dumps({"cik": 1, "taxonomy": "us-gaap", "tag": "Revenues", "entityName": "SYNTHETIC COMPANY",
                      "units": {"USD": rows}}).encode()
    return SecFinancialAdapter(Resolver(), lambda *a, **kw: raw, clock=lambda: AT).retrieve("FIGI:chosen", concepts=("Revenues",))


def financial_bundle(*, conflict=False):
    result = financial_result(conflict=conflict)
    base = EvidenceBundle(asset=result.instrument.asset, identity_verification=result.instrument.verification,
                          language="zh-TW", level="intermediate", created_at=AT)
    return attach_financials(base, result, created_at=AT)
