import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, restore_backup
from backend.app.contracts import SourcePolicy
from backend.app.db import Database
from backend.app.runtime_base import RuntimeFailure
from backend.app.source_registry import source_rule
from backend.app.source_review import SourceReviewBroker, SourceReviewDecision, SourceReviewScope
from tests.desktop.source_review_fixture import review_service, start_review

URL = "https://www.sec.gov/Archives/edgar/data/1/000000999926000003/event.htm"


async def pending(broker, task=None):
    for _ in range(2000):
        if broker.snapshot():
            return broker.snapshot()[0]
        if task and task.done():
            pytest.fail("Research finished before review: " + repr(task.exception()))
        await asyncio.sleep(.001)
    pytest.fail("Source review did not appear")


@pytest.mark.parametrize("outcome", ["select", "skip", "cancel", "expire"])
def test_bounded_correlated_once_only_decisions(outcome):
    async def run():
        broker = SourceReviewBroker(lifetime=.02 if outcome == "expire" else 5)
        task = asyncio.create_task(broker.review("job", "asset", {URL: source_rule(URL)}))
        request = await pending(broker, task)
        for decision in (SourceReviewDecision(source_ids=["foreign"]), SourceReviewDecision(source_ids=[request.sources[0].id] * 2),
                         SourceReviewDecision(cancel=True, source_ids=[request.sources[0].id])):
            with pytest.raises(ValueError):
                broker.resolve("job", request.id, decision)
        with pytest.raises(ValueError):
            broker.resolve("foreign", request.id, SourceReviewDecision())
        with pytest.raises(RuntimeFailure):
            await broker.review("job", "asset", {URL: source_rule(URL)})
        if outcome != "expire":
            broker.resolve("job", request.id, SourceReviewDecision(cancel=outcome == "cancel",
                source_ids=[request.sources[0].id] if outcome == "select" else []))
            with pytest.raises(ValueError):
                broker.resolve("job", request.id, SourceReviewDecision())
        if outcome == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await task
        elif outcome == "expire":
            with pytest.raises(RuntimeFailure, match="expired"):
                await task
        else:
            assert await task == ({URL} if outcome == "select" else set())
        assert not broker.snapshot() and not SourceReviewBroker().snapshot()
    asyncio.run(run())


def test_selection_is_exact_current_rights_and_toggle_cannot_bypass(tmp_path, monkeypatch):
    async def run():
        service, calls = review_service(Database("sqlite://", testing=True), tmp_path)
        scope = SourceReviewScope(service, "job")
        task = asyncio.create_task(scope.select("asset", [URL, "https://unreviewed.example/", "https://api.openfigi.com/v3/search"]))
        request = await pending(service.source_reviews)
        assert [str(row.url) for row in request.sources] == [URL]
        service.db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": False})
        assert scope.active() and not scope.allowed(URL) and not calls
        service.source_reviews.resolve("job", request.id, SourceReviewDecision(source_ids=[request.sources[0].id]))
        assert await task == {URL} and scope.allowed(URL)
        assert not scope.allowed(URL.replace("event.htm", "other.htm"))
        monkeypatch.setattr("backend.app.source_review.source_rule", lambda url: replace(source_rule(URL), policy=SourcePolicy.link))
        assert not scope.allowed(URL)
        assert await scope.select("asset", [URL]) == set()
        await service.close()
    asyncio.run(run())


@pytest.mark.parametrize("phase,outcome", [(0, "skip"), (0, "cancel"), (1, "cancel"), (2, "skip"), (3, "complete")])
def test_manual_production_stages_retrieve_only_selected_and_preserve_versions(tmp_path, phase, outcome):
    async def run():
        service, calls = review_service(Database("sqlite://", testing=True), tmp_path)
        job = await start_review(service)
        task = service.tasks[job["id"]]
        all_selected, partial = set(), None
        for stage in range(3):
            request = await pending(service.source_reviews, task)
            assert set(calls) <= all_selected
            assert service.inference._value == 1 and service.retrieval._value == 2
            if stage == 0:
                assert not calls and not service.db.list("bundle")
            else:
                partial = service.db.job(job["id"])["result"]
                assert partial["completion"] == "section_checkpoint"
            # Only revenue is selected from the concept group; all other metrics stay gaps.
            selected = [row for row in request.sources if stage != 0 or str(row.url).endswith("/Revenues.json")]
            stop = stage == phase
            decision = SourceReviewDecision(cancel=stop and outcome == "cancel",
                source_ids=[] if stop else [row.id for row in selected])
            if not stop:
                all_selected.update(str(row.url) for row in selected)
            service.source_reviews.resolve(job["id"], request.id, decision)
            if stop:
                break
        await asyncio.gather(task, return_exceptions=True)
        final = service.db.job(job["id"])
        assert set(calls) <= all_selected
        assert final["status"] == ("cancelled" if outcome == "cancel" else "completed"), final
        if outcome == "complete":
            assert final["result"]["claims"] and final["result"]["financials"]["observations"]
            assert all(row["concept"] == "us-gaap:Revenues" for row in final["result"]["financials"]["observations"])
            assert final["result"]["sources"][-1]["url"] in all_selected
            target = Database("sqlite://", testing=True)
            archive = make_backup(service.db)
            restore_backup(target, archive, preview_backup(target, archive).fingerprint)
            assert target.job(job["id"])["result"] == final["result"]
        if outcome == "skip":
            assert not final["result"]["claims"]
        if partial:
            assert service.db.get("bundle:" + partial["id"]) == partial
        assert not service.source_reviews.snapshot() and not service.db.list("source_review")
        await service.close()
    asyncio.run(run())


@pytest.mark.parametrize("outcome", ["skip", "cancel", "revoke", "restore"])
def test_authenticated_api_lifecycle_never_persists_or_replays_reviews(tmp_path, outcome):
    async def run():
        db = Database("sqlite://", testing=True)
        service, calls = review_service(db, tmp_path)
        app = create_app(db, "s" * 40, tmp_path, adapters=service.adapters, verifier=service.verifier,
            identity_resolver=service.identity_resolver, financial_adapter=service.financial_adapter, filing_adapter=service.filing_adapter)
        service = app.state.service
        from tests.desktop.financial_fixture import AT
        service.clock = lambda: AT
        job = await start_review(service)
        task = service.tasks[job["id"]]
        request = await pending(service.source_reviews, task)
        route = f"/api/jobs/{job['id']}/source-reviews/{request.id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            assert (await client.get("/api/source-reviews")).status_code == 401
            assert (await client.post(route, json={})).status_code == 401
            client.headers["Authorization"] = "Bearer " + "s" * 40
            response = await client.get("/api/source-reviews")
            assert len(response.json()) == 1 and response.headers["cache-control"] == "no-store"
            assert (await client.post(route, json={"permissions": {"network": True}})).status_code == 422
            assert (await client.post(route.replace(job["id"], "foreign"), json={})).status_code == 409
            if outcome == "revoke":
                assert (await client.put("/api/settings", json={"cloud_enabled": False})).status_code == 200
            elif outcome == "restore":
                archive = make_backup(db)
                target = Database("sqlite://", testing=True)
                restore_backup(target, archive, preview_backup(target, archive).fingerprint)
                assert target.job(job["id"])["status"] == "interrupted"
                assert request.id not in json.dumps(target.job(job["id"]))
                await service.cancel(job["id"])
            else:
                assert (await client.post(route, json={"cancel": outcome == "cancel"})).status_code == 200
            await asyncio.gather(task, return_exceptions=True)
            assert (await client.get("/api/source-reviews")).json() == []
            assert (await client.post(route, json={"source_ids": [request.sources[0].id]})).status_code == 409
        assert not calls
        assert request.id not in json.dumps(db.events(job["id"]))
        await service.close()
    asyncio.run(run())


def test_reviews_for_distinct_jobs_are_bounded_and_independently_cancelled():
    async def run():
        broker = SourceReviewBroker()
        tasks = [asyncio.create_task(broker.review(str(index), "asset", {URL: source_rule(URL)})) for index in range(20)]
        await asyncio.sleep(0)
        assert len(broker.snapshot()) == 20
        with pytest.raises(RuntimeFailure, match="full"):
            await broker.review("overflow", "asset", {URL: source_rule(URL)})
        broker.cancel("0")
        await asyncio.gather(tasks[0], return_exceptions=True)
        assert len(broker.snapshot()) == 19
        broker.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        assert not broker.snapshot()
    asyncio.run(run())


@pytest.mark.parametrize("malformed", ["unsupported", "wrong_asset", "unknown_rights"])
def test_approved_candidate_still_requires_identity_literal_support_and_rights(tmp_path, malformed):
    async def run():
        from backend.app.contracts import ResearchRequest, RuntimeEvent, Source
        from tests.desktop.financial_fixture import financial_result
        service, calls = review_service(Database("sqlite://", testing=True), tmp_path)
        issuer = financial_result().issuer
        service.identity_resolver.resolve = lambda query: [issuer]
        # No prefetch candidates, so the model proposal is reviewed after inference.
        service.filing_adapter.retrieve = lambda *a, **kw: []
        class Runtime:
            async def stream(self, prompt, run_id, workspace, model=None):
                source = Source(id="candidate", asset_id=issuer.asset.id,
                    url="https://unreviewed.example/story" if malformed == "unknown_rights" else URL,
                    title="Untrusted candidate", publisher="UNTRUSTED", policy=SourcePolicy.full_text, verified=True,
                    excerpt="Untrusted invention", provenance="verified_retrieval")
                yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({"candidates": [issuer.asset.model_dump(mode="json")],
                    "sources": [source.model_dump(mode="json")], "claims": [{"asset_id": "wrong" if malformed == "wrong_asset" else issuer.asset.id,
                    "kind": "fact", "text": "Invented statement" if malformed == "unsupported" else "SYNTHETIC COMPANY reported a material event.", "source_ids": [source.id]}]}))
        service.adapters = {"codex": Runtime()}
        job = await service.submit(ResearchRequest(query="Synthetic issuer"))
        task = service.tasks[job["id"]]
        index = await pending(service.source_reviews, task)
        service.source_reviews.resolve(job["id"], index.id, SourceReviewDecision())
        if malformed != "unknown_rights":
            request = await pending(service.source_reviews, task)
            assert not calls and "UNTRUSTED" not in request.model_dump_json()
            service.source_reviews.resolve(job["id"], request.id, SourceReviewDecision(source_ids=[request.sources[0].id]))
        await task
        final = service.db.job(job["id"])
        assert final["status"] == "completed" and not final["result"]["claims"], final
        assert not any(row["completion"] == "section_checkpoint" for row in service.db.list("bundle"))
        assert calls == ([] if malformed == "unknown_rights" else [URL])
        await service.close()
    asyncio.run(run())
