"""Independent synthetic comparison inputs, with no live identity/source requests."""
import json

from backend.app.contracts import AssetIdentity, EvidenceBundle, IdentityVerification
from backend.app.figi_identity import parse_figi_response
from backend.app.financial_evidence import attach_financials
from backend.app.identity import identity_hash, parse_sec_listings
from backend.app.structured_financials import SecFinancialAdapter
from tests.desktop.financial_fixture import AT, financial_bundle


def comparison_pair(*, unit="USD", end="2025-12-31", conflict=False):
    left = financial_bundle()
    instrument = parse_figi_response(json.dumps([{"data": [{"figi": "BBG000BLNNH6", "ticker": "SECOND",
        "name": "SECOND SYNTHETIC COMPANY", "exchCode": "UW", "securityType": "Common Stock",
        "securityType2": "Common Stock", "marketSector": "Equity"}]}]).encode(), query="SECOND", search=False, retrieved_at=AT)[0]
    issuer = parse_sec_listings(json.dumps({"fields": ["cik", "name", "ticker", "exchange"],
        "data": [[2, "SECOND SYNTHETIC COMPANY", "SECOND", "Nasdaq"]]}).encode(), AT)[0]
    class Resolver:
        @property
        def sec(self):
            return self
        def resolve(self, query):
            return [issuer] if query == "SECOND" else [instrument]
    base = {"start": "2025-01-01", "end": end, "val": 9007199254740993,
        "accn": "0000000002-26-000001", "filed": "2026-02-01", "form": "10-K", "fy": 2025, "fp": "FY"}
    rows = [base]
    if conflict:
        rows.append({**base, "val": 9007199254740994, "accn": "0000000002-26-000002"})
    raw = json.dumps({"cik": 2, "taxonomy": "us-gaap", "tag": "Revenues", "entityName": "SECOND SYNTHETIC COMPANY", "units": {unit: rows}}).encode()
    result = SecFinancialAdapter(Resolver(), lambda *a, **kw: raw, clock=lambda: AT).retrieve("FIGI:second", concepts=("Revenues",))
    right = attach_financials(EvidenceBundle(asset=instrument.asset, identity_verification=instrument.verification, created_at=AT), result, created_at=AT)
    return left, right


def empty_comparison_asset(kind="etf"):
    asset = AssetIdentity(id="TEST:" + kind, symbol="EMPTY", name="Synthetic " + kind, asset_type=kind)
    proof = IdentityVerification(authority="synthetic-identity", source_url="https://identity.example/test",
        retrieved_at=AT, content_hash="b" * 64, identity_hash=identity_hash(asset))
    return EvidenceBundle(asset=asset, identity_verification=proof, created_at=AT)


def seed_comparison(db, pair=None):
    from backend.app.contracts import Settings
    pair = pair or comparison_pair()
    for bundle in pair:
        payload = bundle.model_dump(mode="json")
        db.put("bundle:" + bundle.id, "bundle", payload, bundle.asset.id)
        db.put("asset:" + bundle.asset.id, "asset", payload)
    db.put("settings", "settings", Settings(cloud_enabled=True).model_dump(mode="json"))
    return pair
