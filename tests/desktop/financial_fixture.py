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


async def publish_financial_snapshot(db, workspace):
    """Exercise production orchestration against synthetic sources/runtime in a real DB."""
    from backend.app.contracts import Claim, ResearchRequest, RuntimeEvent, Source
    from backend.app.research import ResearchService
    from backend.app.evidence import verify_candidate
    from backend.app.sec_filings import SecFilingsAdapter
    result = financial_result(conflict=True)
    class Resolver:
        def resolve(self, query):
            return [result.instrument]
    class Financial:
        def retrieve(self, *args, **kwargs):
            return result
    raw_filings = json.dumps({"cik": "0000000001", "name": "SYNTHETIC COMPANY", "filings": {"recent": {
        "accessionNumber": ["0000009999-26-000004"], "filingDate": ["2026-09-17"], "reportDate": ["2026-09-15"],
        "form": ["8-K"], "primaryDocument": ["event.htm"]}}}).encode()
    filing_adapter = SecFilingsAdapter(lambda *args, **kwargs: raw_filings, clock=lambda: AT)
    def verifier(source, asset):
        value = verify_candidate(source, asset, lambda _: "SYNTHETIC COMPANY reported a material event.")
        return value.model_copy(update={"retrieved_at": AT})
    class Runtime:
        async def stream(self, prompt, run_id, workspace, model=None):
            assert "CURRENT RETRIEVAL OF HISTORICAL ISSUER EVIDENCE" in prompt
            source = Source(id="event", asset_id=result.instrument.asset.id,
                url="https://www.sec.gov/Archives/edgar/data/1/000000999926000004/event.htm", title="Synthetic event", publisher="candidate")
            claim = Claim(asset_id=source.asset_id, kind="fact", text="SYNTHETIC COMPANY reported a material event.", source_ids=[source.id])
            yield RuntimeEvent(run_id=run_id, kind="message.delta",
                text=json.dumps({"candidates": [result.instrument.asset.model_dump(mode="json")],
                    "sources": [source.model_dump(mode="json")], "claims": [claim.model_dump(mode="json")]}))
    db.put("settings", "settings", {"cloud_enabled": True})
    service = ResearchService(db, {"codex": Runtime()}, workspace, identity_resolver=Resolver(),
                              financial_adapter=Financial(), filing_adapter=filing_adapter, verifier=verifier, clock=lambda: AT)
    try:
        job = await service.submit(ResearchRequest(query=result.instrument.asset.id))
        await service.tasks[job["id"]]
        job = db.job(job["id"])
        assert job["status"] == "completed"
        assert len(job["result"]["financials"]["observations"]) == 3
        assert job["result"]["sources"][0]["filing_publication"]["filed"] == "2026-09-17"
        return job
    finally:
        await service.close()
