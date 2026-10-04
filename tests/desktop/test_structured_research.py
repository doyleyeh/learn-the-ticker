import asyncio
import json
import threading

from backend.app.backup import make_backup, preview_backup, restore_backup
from backend.app.contracts import ResearchRequest, RuntimeEvent
from backend.app.db import Database
from backend.app.research import ResearchService
from tests.desktop.financial_fixture import AT, financial_result


class Resolver:
    def __init__(self, result):
        self.result = result

    def resolve(self, query):
        return [self.result.instrument]


class FinancialAdapter:
    def __init__(self, result):
        self.result, self.calls = result, 0

    def retrieve(self, query, *, resolved, cancelled):
        self.calls += 1
        assert resolved == self.result.instrument and not cancelled.is_set()
        return self.result


class Runtime:
    def __init__(self, result):
        self.result, self.prompts, self.active, self.maximum = result, [], 0, 0

    async def stream(self, prompt, run_id, workspace, model=None):
        self.prompts.append(prompt)
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            await asyncio.sleep(0)
            # Deliberately invented model numeric value must remain outside the DTO.
            payload = {"candidates": [self.result.instrument.asset.model_dump(mode="json")],
                       "claims": [{"asset_id": self.result.instrument.asset.id, "text": "Invented 12345", "kind": "fact", "value": 12345, "unit": "USD"}]}
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps(payload))
        finally:
            self.active -= 1


def service_at(tmp_path, *, financial=None, runtime=None):
    result = financial_result()
    runtime = runtime or Runtime(result)
    financial = financial or FinancialAdapter(result)
    db = Database("sqlite://", testing=True)
    db.put("settings", "settings", {"cloud_enabled": True})
    service = ResearchService(db, {"codex": runtime}, tmp_path, identity_resolver=Resolver(result),
                              financial_adapter=financial, clock=lambda: AT)
    return service, runtime, financial


async def finish(service, request=None):
    job = await service.submit(request or ResearchRequest(query="FIGI:chosen"))
    await service.tasks[job["id"]]
    return service.db.job(job["id"])


def test_structured_first_context_and_atomic_publication_survive_restore(tmp_path):
    async def scenario():
        service, runtime, financial = service_at(tmp_path)
        job = await finish(service)
        assert job["status"] == "completed", job
        assert financial.calls == 1 and "CURRENT RETRIEVAL OF HISTORICAL ISSUER EVIDENCE" in runtime.prompts[0]
        assert '"value": "9007199254740992"' in runtime.prompts[0]
        result = job["result"]
        assert len(result["financials"]["observations"]) == 2 and not result["claims"]
        assert all(row["value"] is None for row in result["notes"])
        assert service.db.get("asset:" + result["asset"]["id"]) == result
        assert service.db.get("bundle:" + result["id"]) == result
        assert all("9007199254740992" not in json.dumps(event) for event in service.db.events(job["id"]))
        archive = make_backup(service.db)
        target = Database("sqlite://", testing=True)
        restore_backup(target, archive, preview_backup(target, archive).fingerprint)
        assert target.job(job["id"])["result"] == result
        # A later refresh preserves the first immutable version.
        refreshed = await finish(service, ResearchRequest(query="Latest history", asset_id=result["asset"]["id"], refresh=True))
        assert refreshed["status"] == "completed" and financial.calls == 2
        assert service.db.get("bundle:" + result["id"]) == result and len(service.db.list("bundle")) == 4
        assert sum(row["completion"] == "section_checkpoint" for row in service.db.list("bundle")) == 2
        await service.close()
    asyncio.run(scenario())


def test_manual_review_never_automatically_retrieves_or_admits_financials(tmp_path):
    async def scenario():
        service, runtime, financial = service_at(tmp_path)
        service.db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": True})
        job = await finish(service)
        assert job["status"] == "completed" and job["result"]["financials"] is None and financial.calls == 0
        assert "awaits source review" in runtime.prompts[0]
        assert any("awaits source review" in note["text"] for note in job["result"]["notes"])
        await service.close()
    asyncio.run(scenario())


def test_manual_review_enabled_during_inference_prevents_automatic_publication(tmp_path):
    async def scenario():
        service, runtime, _ = service_at(tmp_path)
        original = runtime.stream
        async def change_setting(*args, **kwargs):
            service.db.put("settings", "settings", {"cloud_enabled": True, "manual_source_review": True})
            async for event in original(*args, **kwargs):
                yield event
        runtime.stream = change_setting
        job = await finish(service)
        assert job["status"] == "completed" and job["result"]["financials"] is None
        assert not job["result"]["sources"]
        await service.close()
    asyncio.run(scenario())


def test_failed_structured_source_is_disclosed_without_model_numeric_fallback(tmp_path):
    class Broken:
        def retrieve(self, *args, **kwargs):
            raise OSError("PRIVATE token and response body")
    async def scenario():
        service, runtime, _ = service_at(tmp_path, financial=Broken())
        job = await finish(service)
        assert job["status"] == "completed" and job["result"]["financials"] is None
        assert "PRIVATE" not in json.dumps(job) and "PRIVATE" not in runtime.prompts[0]
        assert not job["result"]["claims"] and all(row["value"] is None for row in job["result"]["notes"])
        assert any("unavailable" in row["text"] for row in job["result"]["notes"])
        await service.close()
    asyncio.run(scenario())


def test_concurrent_retrievals_are_bounded_and_cancelled_io_keeps_its_slot(tmp_path):
    async def scenario():
        service, runtime, _ = service_at(tmp_path)
        released = threading.Event()
        first_two = threading.Event()
        lock = threading.Lock()
        counts = {"active": 0, "maximum": 0, "started": 0}
        class Blocking:
            def retrieve(self, *args, cancelled, **kwargs):
                with lock:
                    counts["active"] += 1
                    counts["started"] += 1
                    counts["maximum"] = max(counts["maximum"], counts["active"])
                    if counts["started"] == 2:
                        first_two.set()
                try:
                    assert released.wait(5)
                    if cancelled.is_set():
                        raise InterruptedError()
                    return financial_result()
                finally:
                    with lock:
                        counts["active"] -= 1
        service.financial_adapter = Blocking()
        jobs = [await service.submit(ResearchRequest(query="FIGI:chosen")) for _ in range(3)]
        tasks = [service.tasks[job["id"]] for job in jobs]
        try:
            assert await asyncio.to_thread(first_two.wait, 3), counts
            await service.cancel(jobs[0]["id"])
            assert counts["active"] == 2 and counts["started"] == 2
            assert service.retrieval.locked() and not runtime.prompts
        finally:
            released.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        assert counts["maximum"] == 2 and runtime.maximum == 1 and len(runtime.prompts) == 2
        assert service.db.job(jobs[0]["id"])["status"] == "cancelled"
        assert all(service.db.job(job["id"])["status"] == "completed" for job in jobs[1:])
        await service.close()
        assert not service.retrieval_workers
    asyncio.run(scenario())


def test_consent_revocation_after_retrieval_prevents_inference_and_publication(tmp_path):
    async def scenario():
        service, runtime, _ = service_at(tmp_path)
        class Revoking:
            def retrieve(self, *args, **kwargs):
                service.db.put("settings", "settings", {"cloud_enabled": False})
                return financial_result()
        service.financial_adapter = Revoking()
        job = await finish(service)
        assert job["status"] == "failed" and not runtime.prompts
        assert not service.db.list("asset") and not service.db.list("bundle")
        await service.close()
    asyncio.run(scenario())
