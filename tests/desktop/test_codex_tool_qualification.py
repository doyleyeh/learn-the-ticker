import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.app.codex_catalog import RestrictedCatalog
from scripts import qualify_codex_tools as probes
from tests.desktop.test_codex import FakeRPC
from tests.desktop.test_codex_catalog import payload


class SyntheticRPC(FakeRPC):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.account = {"type": "chatgpt"}
        self.process, self.catalog = object(), None

    async def restrict_model(self, selected):
        await super().restrict_model(selected)
        self.catalog = RestrictedCatalog(payload(), selected)

    async def request(self, method, params, **kwargs):
        result = await super().request(method, params, **kwargs)
        if method == "turn/start":
            await self.events.put({"id": 9, "method": "item/permissions/requestApproval", "params": {
                "threadId": "thread-1", "turnId": "turn-1", "itemId": "permission-1",
                "permissions": {"network": {"enabled": True}}}})
        return result

    async def receive(self): return await self.events.get()
    async def event(self): return await self.receive()

    async def send(self, message):
        assert message == {"id": 9, "result": {"permissions": {}, "scope": "turn"}}
        params = {"threadId": "thread-1", "turnId": "turn-1"}
        await self.events.put({"method": "item/completed", "params": {**params, "item": {
            "id": "permission-1", "type": "functionCallOutput", "name": "request_permissions", "namespace": "functions",
            "output": '{"permissions":{"network":null,"file_system":null},"scope":"turn"}'}}})
        item = {"id": "message-1", "type": "agentMessage", "phase": "final_answer", "text": ""}
        await self.events.put({"method": "item/started", "params": {**params, "item": item}})
        await self.events.put({"method": "item/completed", "params": {**params, "item": {**item, "text": json.dumps({
            "denied": True, "tools": ["web.run", "functions.request_permissions"]})}}})
        await self.events.put({"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"}}})

    async def close(self):
        self.process = None
        if self.catalog:
            self.catalog.close()
            self.catalog = None
        await super().close()


@pytest.mark.parametrize("decision", ["deny", "cancel"])
def test_synthetic_probe_uses_real_adapter_broker_and_empty_responses(tmp_path, monkeypatch, decision):
    async def qualified(*args, **kwargs): pass
    monkeypatch.setattr(probes.ProbeRuntime, "require_generation", qualified)
    report = asyncio.run(probes.permission_probe(tmp_path, tmp_path, "synthetic-model", "synthetic", decision, rpc_base=SyntheticRPC))
    assert report["permission_requested"] and report["only_empty_turn_responses"]
    assert report["turns"] == 1 and report["owned_processes_closed"] and report["temporary_catalogs_removed"]
    assert report["no_pending_access"]
    if decision == "deny": assert report["denial_acknowledged"] and report["reported_inventory_matches"]
    else: assert report["cancelled"]


@pytest.mark.parametrize("ready", [False, True])
def test_no_live_probes_without_preflight_and_actual_enforcement(tmp_path, monkeypatch, ready):
    async def enforcement(*args): return ready
    async def forbidden(*args, **kwargs): pytest.fail("unauthorized inference")
    monkeypatch.setattr(probes, "permission_probe", forbidden)
    monkeypatch.setattr(probes, "enforcement_ready", enforcement)
    before = {"status": "blocked", "generation_requested": False}
    assert asyncio.run(probes.acceptance(tmp_path, before)) == before
    if not ready:
        result = asyncio.run(probes.acceptance(tmp_path, {"status": "preflight_passed", "generation_requested": False}))
        assert result["blocker"] == "sandbox_enforcement" and not result["generation_requested"]


def test_default_cli_path_does_not_request_inference(tmp_path, monkeypatch, capsys):
    async def preflight(*args): return {"status": "preflight_passed", "generation_requested": False, "live_qualified": False}
    async def forbidden(*args): pytest.fail("default invocation ran inference")
    monkeypatch.setattr(probes, "resolve_profile", lambda _: tmp_path)
    monkeypatch.setattr(probes, "preflight", preflight)
    monkeypatch.setattr(probes, "acceptance", forbidden)
    assert asyncio.run(probes.run(SimpleNamespace(profile=None, model=None, live=False))) == 0
    assert json.loads(capsys.readouterr().out)["generation_requested"] is False
