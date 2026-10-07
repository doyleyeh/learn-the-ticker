import asyncio
from collections import deque

import pytest

from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import AIRuntime
from scripts import setup_codex_sandbox


class SetupRPC:
    def __init__(self, *, readiness="updateRequired", success=True, mode="elevated", timeout=False):
        self.readiness, self.success, self.mode, self.timeout = readiness, success, mode, timeout
        self.calls, self.opened, self.closed = [], 0, 0
        self.events = deque([{"method": "windowsSandbox/setupCompleted", "params": {"mode": mode, "success": success, "error": "private diagnostic"}}])

    async def open(self): self.opened += 1
    async def close(self): self.closed += 1
    async def request(self, method, params):
        self.calls.append((method, params))
        if method == "windowsSandbox/readiness": return {"status": self.readiness}
        if method == "windowsSandbox/setupStart": return {"started": True}
        pytest.fail("Unexpected login, inference, or other RPC")

    async def event(self):
        if self.timeout: await asyncio.Future()
        self.readiness = "ready"
        return self.events.popleft()


@pytest.fixture(autouse=True)
def reviewed_runtime(monkeypatch):
    async def discover(self):
        return RuntimeCapabilities(provider="codex", installed=True, version="synthetic", qualification="protocol_only")
    monkeypatch.setattr(AIRuntime, "check", discover)


@pytest.mark.parametrize("readiness,expected", [("ready", 0), ("updateRequired", 2), ("notConfigured", 2), ("unknown", 2)])
def test_inspection_never_starts_setup_or_generation(tmp_path, readiness, expected):
    rpc = SetupRPC(readiness=readiness)
    assert asyncio.run(setup_codex_sandbox.setup(tmp_path, rpc_factory=lambda *args, **kwargs: rpc)) == expected
    assert rpc.calls == [("windowsSandbox/readiness", {})] and rpc.closed


def test_explicit_setup_has_no_project_roots_and_reopens_before_success(tmp_path, capsys):
    rpc = SetupRPC()
    assert asyncio.run(setup_codex_sandbox.setup(tmp_path, apply=True, rpc_factory=lambda *args, **kwargs: rpc)) == 0
    assert ("windowsSandbox/setupStart", {"mode": "elevated"}) in rpc.calls
    assert rpc.opened == 2 and rpc.closed == 2
    assert "private diagnostic" not in capsys.readouterr().out


@pytest.mark.parametrize("options", [{"success": False}, {"mode": "unelevated"}, {"timeout": True}])
def test_failed_setup_is_sanitized_and_never_retried(tmp_path, capsys, options):
    rpc = SetupRPC(**options)
    assert asyncio.run(setup_codex_sandbox.setup(tmp_path, apply=True, rpc_factory=lambda *args, **kwargs: rpc, timeout=.01)) == 2
    assert sum(method == "windowsSandbox/setupStart" for method, _ in rpc.calls) == 1
    assert rpc.opened == 1 and rpc.closed
    assert "private diagnostic" not in capsys.readouterr().out
