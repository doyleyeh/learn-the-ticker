"""Production-path source review using synthetic bytes, never live services."""
import json
import asyncio

from backend.app.contracts import ResearchRequest, RuntimeEvent, Source
from backend.app.evidence import verify_candidate
from backend.app.research import ResearchService
from backend.app.sec_filings import SecFilingsAdapter, document_url
from backend.app.structured_financials import SecFinancialAdapter
from backend.app.source_review import SourceReviewDecision
from tests.desktop.financial_fixture import AT, financial_result
from tests.desktop.test_sec_filings import raw as filing_bytes
from tests.desktop.test_sec_financials import raw as concept_bytes


def review_service(db, workspace):
    result, calls = financial_result(), []
    class IssuerResolver:
        def resolve(self, query):
            return [result.issuer]
    class Resolver:
        sec = IssuerResolver()
        def resolve(self, query):
            return [result.instrument]
    def fetch(url, **_):
        calls.append(url)
        if "/submissions/" in url:
            return filing_bytes()
        concept = url.rsplit("/", 1)[-1].removesuffix(".json")
        return concept_bytes(concept=concept)
    def verify(source, asset):
        calls.append(str(source.url))
        return verify_candidate(source, asset, lambda _: "SYNTHETIC COMPANY reported a material event.").model_copy(update={"retrieved_at": AT})
    class Runtime:
        async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
            if not allow_browsing:
                context = json.loads(prompt.split("ADMITTED SNAPSHOT: ")[1])
                market = context["market"]
                yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({
                    "explanation": "The retained daily close is 14 USD. It is a historical observation, not a live quote.",
                    "basis": "snapshot", "source_ids": [market["source_id"]]}))
                return
            source = Source(id="reviewed-filing", asset_id=result.instrument.asset.id,
                url=document_url("0000000001", "0000009999-26-000003", "event.htm"), title="Synthetic filing", publisher="candidate")
            payload = {"candidates": [result.instrument.asset.model_dump(mode="json")], "sources": [], "claims": []}
            if "INDEPENDENTLY RETRIEVED FILING SOURCES" in prompt:
                payload.update(sources=[source.model_dump(mode="json")], claims=[{"asset_id": result.instrument.asset.id,
                    "kind": "fact", "text": "SYNTHETIC COMPANY reported a material event.", "source_ids": [source.id]}])
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps(payload))
    resolver = Resolver()
    db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": True})
    service = ResearchService(db, {"codex": Runtime()}, workspace, identity_resolver=resolver, verifier=verify,
        financial_adapter=SecFinancialAdapter(resolver, fetch, clock=lambda: AT),
        filing_adapter=SecFilingsAdapter(fetch, clock=lambda: AT), clock=lambda: AT)
    return service, calls


async def start_review(service):
    return await service.submit(ResearchRequest(query="Synthetic source review"))


async def next_review(service, task):
    for _ in range(2000):
        rows = service.source_reviews.snapshot()
        if rows:
            return rows[0]
        if task.done():
            raise AssertionError("Synthetic research ended before its expected source review")
        await asyncio.sleep(.001)
    raise AssertionError("Synthetic source review did not appear")


async def publish_review_snapshot(db, workspace):
    service, calls = review_service(db, workspace)
    try:
        job = await start_review(service)
        task = service.tasks[job["id"]]
        allowed = set()
        for stage in range(3):
            request = await next_review(service, task)
            assert set(calls) <= allowed
            selected = [row for row in request.sources if stage != 0 or str(row.url).endswith("/Revenues.json")]
            allowed.update(str(row.url) for row in selected)
            service.source_reviews.resolve(job["id"], request.id, SourceReviewDecision(source_ids=[row.id for row in selected]))
        await task
        result = db.job(job["id"])
        assert result["status"] == "completed" and result["result"]["claims"] and result["result"]["financials"]["observations"]
        assert set(calls) == allowed and not service.source_reviews.snapshot()
        return result
    finally:
        await service.close()


async def backup_during_review(db, workspace):
    from backend.app.backup import make_backup
    original = db.get("settings")
    service, calls = review_service(db, workspace)
    try:
        job = await start_review(service)
        request = await next_review(service, service.tasks[job["id"]])
        assert not calls and db.job(job["id"])["status"] == "running"
        # Preserve the existing archive settings; a pending decision is memory-only.
        db.put("settings", "settings", original)
        return make_backup(db), job["id"], request.id
    finally:
        await service.close()
