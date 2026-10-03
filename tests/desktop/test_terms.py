import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import BackupError, make_backup, preview_backup, read_backup, restore_backup
from backend.app.codex_rpc import CodexRPC
from backend.app.contracts import Claim, EvidenceBundle, RuntimeEvent, TermExplanation, TermRequest
from backend.app.db import Database, Job, Record
from backend.app.evidence import factual_context
from backend.app.research import ResearchService
from backend.app.terms import TermService, term_key
from tests.desktop.test_backup import alter
from tests.desktop.test_application import IDENTITY, source


class TermRuntime:
    def __init__(self, result=None, *, wait=False, tool=False):
        self.result = result or {"explanation": "Revenue describes sales before costs.", "basis": "snapshot", "source_ids": ["s1"]}
        self.wait, self.tool, self.calls, self.active, self.maximum = wait, tool, [], 0, 0
        self.started = asyncio.Event()

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        self.calls.append({"prompt": prompt, "browsing": allow_browsing})
        self.active += 1; self.maximum = max(self.maximum, self.active); self.started.set()
        try:
            await asyncio.sleep(.02 if not self.wait else 30)
            if self.tool: yield RuntimeEvent(run_id=run_id, kind="tool.started", text="unexpected search")
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps(self.result))
        finally:
            self.active -= 1


def setup(tmp_path, runtime=None):
    db = Database("sqlite://", testing=True)
    citation = source(verified=True, policy="summary_allowed", excerpt="Revenue is 12 million USD.")
    bundle = EvidenceBundle(asset=IDENTITY, sources=[citation], claims=[Claim(asset_id=IDENTITY.id, kind="fact", text=citation.excerpt, source_ids=["s1"])], notes=[Claim(asset_id=IDENTITY.id, text="UNVERIFIED_PRIVATE_NOTE")])
    for kind, suffix, parent in [("bundle", bundle.id, IDENTITY.id), ("asset", IDENTITY.id, None)]:
        db.put(kind + ":" + suffix, kind, bundle.model_dump(mode="json"), parent)
    db.put("settings", "settings", {"cloud_enabled": True})
    runtime = runtime or TermRuntime()
    research = ResearchService(db, {"codex": runtime}, tmp_path)
    return db, bundle, runtime, research, TermService(research)


async def completed(service, request):
    job = await service.submit(request)
    await service.research.tasks[job["id"]]
    return service.db.job(job["id"])


def test_explanation_uses_only_admitted_context_and_never_changes_facts(tmp_path):
    async def run():
        db, bundle, runtime, research, service = setup(tmp_path)
        before = factual_context(bundle)
        request = TermRequest(term="revenue", bundle_id=bundle.id)
        result = await completed(service, request)
        assert result["status"] == "completed"
        assert result["result"]["interpretation"] is True and result["result"]["source_ids"] == ["s1"]
        assert not runtime.calls[0]["browsing"] and "UNVERIFIED_PRIVATE_NOTE" not in runtime.calls[0]["prompt"]
        assert db.get("asset:" + IDENTITY.id) == bundle.model_dump(mode="json")
        assert factual_context(EvidenceBundle.model_validate(db.get("bundle:" + bundle.id))) == before
        assert len(db.list("bundle")) == 1 and len(db.list("term")) == 1
        # Switching connection does not discard an existing app-owned interpretation.
        db.put("settings", "settings", {"cloud_enabled": False})
        cached = await service.submit(request.model_copy(update={"provider": "claude", "term": "REVENUE"}))
        assert cached["status"] == "cached" and len(runtime.calls) == 1
        assert all(event["kind"] != "message.delta" for event in db.events(result["id"]))
    asyncio.run(run())


def test_cache_versions_language_and_level_are_independent(tmp_path):
    async def run():
        db, bundle, runtime, _, service = setup(tmp_path)
        original = await completed(service, TermRequest(term="revenue", bundle_id=bundle.id))
        changed = bundle.model_copy(update={"id": "new-evidence-version"})
        db.put("bundle:" + changed.id, "bundle", changed.model_dump(mode="json"), IDENTITY.id)
        db.put("asset:" + IDENTITY.id, "asset", changed.model_dump(mode="json"))
        assert service.lookup(TermRequest(term="revenue", bundle_id=changed.id))["status"] == "unavailable"
        for language, level in [("en", "beginner"), ("zh-TW", "beginner"), ("en", "intermediate")]:
            runtime.result = {"explanation": "營收為 12 million USD。" if language == "zh-TW" else "Revenue is 12 million USD.", "basis": "snapshot", "source_ids": ["s1"]}
            result = await completed(service, TermRequest(term="revenue", bundle_id=changed.id, language=language, level=level))
            assert result["status"] == "completed" and result["result"]["language"] == language
        assert len(db.list("term")) == 4 and db.get("term:" + original["result"]["id"]) == original["result"]
    asyncio.run(run())


def test_refresh_regenerates_used_terms_and_preserves_old_snapshot(tmp_path):
    async def run():
        from backend.app.contracts import ResearchRequest
        from tests.desktop.test_application import payload
        db, bundle, runtime, research, service = setup(tmp_path)
        old = await completed(service, TermRequest(term="revenue", bundle_id=bundle.id))
        class HybridRuntime(TermRuntime):
            async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
                if allow_browsing:
                    yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps(payload()))
                else:
                    async for event in super().stream(prompt, run_id, workspace, model, allow_browsing=False):
                        yield event
        research.adapters["codex"] = HybridRuntime({"explanation": "Revenue describes sales before costs. No supported current figures are available.", "basis": "general"})
        research.verifier = lambda source, asset: source
        refresh = await research.submit(ResearchRequest(query="Refresh", asset_id=IDENTITY.id, refresh=True))
        await research.tasks[refresh["id"]]
        # The auto-regeneration uses the same queue and selected connection.
        await asyncio.gather(*list(research.tasks.values()))
        latest = db.get("asset:" + IDENTITY.id)
        assert latest["id"] != bundle.id
        assert db.get("term:" + old["result"]["id"]) == old["result"]
        refreshed = service.lookup(TermRequest(term="revenue", bundle_id=latest["id"]))
        assert refreshed["status"] == "cached" and refreshed["result"]["basis"] == "general"
        assert len(db.list("term")) == 2
        assert any("Refreshing 1 saved term" in event["text"] for event in db.events(refresh["id"]))
    asyncio.run(run())


@pytest.mark.parametrize("result", [
    {"explanation": "Made up citation", "basis": "snapshot", "source_ids": ["other-asset"]},
    {"explanation": "No citation", "basis": "snapshot", "source_ids": []},
    {"explanation": "False generic citation", "basis": "general", "source_ids": ["s1"]},
    {"explanation": "Revenue is 500 USD.", "basis": "snapshot", "source_ids": ["s1"]},
    {"explanation": "You should buy this asset", "basis": "general"},
    {"explanation": "建議你買入這個資產。", "basis": "general"},
    {"explanation": " ", "basis": "general"},
    {"unexpected": "sensitive diagnostic"},
])
def test_invalid_explanations_never_enter_the_cache(tmp_path, result):
    async def run():
        db, bundle, _, _, service = setup(tmp_path, TermRuntime(result))
        job = await completed(service, TermRequest(term="revenue", bundle_id=bundle.id))
        assert job["status"] == "failed" and not db.list("term")
        assert "sensitive" not in job["error"] and db.get("asset:" + IDENTITY.id) == bundle.model_dump(mode="json")
    asyncio.run(run())


def test_generic_terms_work_without_admitted_evidence_and_tools_fail_closed(tmp_path):
    async def run():
        runtime = TermRuntime({"explanation": "Allocation means dividing resources among uses.", "basis": "general"})
        db, bundle, _, _, service = setup(tmp_path, runtime)
        request = TermRequest(term="allocation", bundle_id=bundle.id)
        job = await completed(service, request)
        assert job["status"] == "completed" and job["result"]["source_ids"] == []
        runtime.tool = True
        job = await completed(service, request.model_copy(update={"term": "liquidity"}))
        assert job["status"] == "failed" and len(db.list("term")) == 1
    asyncio.run(run())


def test_deduplication_queue_and_shared_inference_limit(tmp_path):
    async def run():
        db, bundle, runtime, research, service = setup(tmp_path)
        request = TermRequest(term="revenue", bundle_id=bundle.id)
        first = await service.submit(request)
        duplicate = await service.submit(request)
        second = await service.submit(request.model_copy(update={"term": "sales"}))
        assert first["id"] == duplicate["id"]
        await asyncio.gather(research.tasks[first["id"]], research.tasks[second["id"]])
        assert len(runtime.calls) == 2 and runtime.maximum == 1
        async with research.inference:
            pending = await service.submit(request.model_copy(update={"term": "another term"}))
            await asyncio.sleep(.01)
            assert db.job(pending["id"])["status"] == "queued"
            await research.cancel(pending["id"])
            assert db.job(pending["id"])["status"] == "cancelled"
    asyncio.run(run())


def test_cancellation_and_permission_revocation_preserve_saved_versions(tmp_path):
    async def run():
        db, bundle, runtime, research, service = setup(tmp_path, TermRuntime(wait=True))
        job = await service.submit(TermRequest(term="revenue", bundle_id=bundle.id))
        await runtime.started.wait()
        await research.cancel(job["id"])
        assert db.job(job["id"])["status"] == "cancelled" and runtime.active == 0 and not db.list("term")
        db.put("settings", "settings", {"cloud_enabled": False})
        with pytest.raises(ValueError, match="off"):
            await service.submit(TermRequest(term="debt", bundle_id=bundle.id))
    asyncio.run(run())


def test_lookup_is_read_only_and_api_rejects_unknown_bundle(tmp_path):
    db, bundle, runtime, _, _ = setup(tmp_path)
    app = create_app(db, "x" * 40, tmp_path, adapters={"codex": runtime})
    request = TermRequest(term="revenue", bundle_id=bundle.id).model_dump(mode="json")
    with TestClient(app) as client:
        assert client.post("/api/terms/lookup", json=request).status_code == 401
        headers = {"Authorization": "Bearer " + "x" * 40}
        for _ in range(2):
            assert client.post("/api/terms/lookup", json=request, headers=headers).json()["status"] == "unavailable"
        assert not runtime.calls and not db.list("term")
        assert client.post("/api/terms/lookup", json=request | {"bundle_id": "missing"}, headers=headers).status_code == 404


def test_explanations_backup_restore_and_reference_validation(tmp_path):
    async def run():
        db, bundle, _, _, service = setup(tmp_path)
        result = await completed(service, TermRequest(term="revenue", bundle_id=bundle.id))
        raw = make_backup(db)
        target = Database("sqlite://", testing=True)
        summary = preview_backup(target, raw)
        assert summary.term_explanations == 1
        restore_backup(target, raw, summary.fingerprint)
        assert target.list("term") == db.list("term") and target.job(result["id"])["result"] == result["result"]
        def break_citation(value):
            next(row for row in value["records"] if row["kind"] == "term")["payload"]["source_ids"] = ["fabricated"]
        with pytest.raises(BackupError): read_backup(alter(raw, change=break_citation))
        def break_request(value): value["jobs"][0]["request"]["term"] = "different term"
        with pytest.raises(BackupError): read_backup(alter(raw, change=break_request))
    asyncio.run(run())


def test_term_publication_rolls_back_with_failed_record_write(tmp_path):
    async def run():
        db, bundle, _, _, service = setup(tmp_path)
        def fail_term(mapper, connection, target):
            if target.kind == "term": raise RuntimeError("Injected failure")
        event.listen(Record, "before_insert", fail_term)
        try: result = await completed(service, TermRequest(term="revenue", bundle_id=bundle.id))
        finally: event.remove(Record, "before_insert", fail_term)
        assert result["status"] == "failed" and result["result"] is None and not db.list("term")
    asyncio.run(run())


def test_codex_cached_only_policy_is_configured_on_the_process(tmp_path, monkeypatch):
    from tests.desktop.test_codex_policy import config_response, features_response
    async def run():
        captured = {}
        async def wait(): return 0
        async def spawn(*args, **kwargs): captured.update(args=args, kwargs=kwargs); return SimpleNamespace(returncode=0, wait=wait)
        async def ignore(*args, **kwargs): return {}
        async def request(method, params):
            if method == "config/read": return config_response()
            if method == "experimentalFeature/list": return features_response()
            return {}
        monkeypatch.setattr("backend.app.codex_rpc.executable_command", lambda _: ["codex.exe"])
        monkeypatch.setattr("backend.app.codex_rpc.launch_owned", spawn)
        rpc = CodexRPC(tmp_path / "profile", tmp_path / "workspace", allow_browsing=False)
        rpc.request, rpc.send = request, ignore
        await rpc.open(); await rpc.close()
        assert 'web_search="disabled"' in captured["args"] and "features.shell_tool=false" in captured["args"]
        assert captured["kwargs"]["env"]["CODEX_HOME"] == str((tmp_path / "profile").resolve())
    asyncio.run(run())
