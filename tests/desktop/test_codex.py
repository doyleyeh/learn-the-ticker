import asyncio
import json
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.codex_login import CodexLogin, DEVICE_URL
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_policy import thread_parameters
from backend.app.codex_runtime import CodexRuntime
from backend.app.db import Database
from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import RuntimeFailure


class FakeRPC:
    def __init__(self, profile=None, workspace=None):
        self.requests = []
        self.events = asyncio.Queue()
        self.account = None
        self.result = {"type": "chatgptDeviceCode", "loginId": "login-1", "verificationUrl": DEVICE_URL, "userCode": "ABCD-1234"}
        self.closed = False

    async def open(self):
        pass

    async def request(self, method, params, **kwargs):
        self.requests.append((method, params))
        if method == "account/read":
            return {"account": self.account}
        if method == "account/login/start":
            return self.result
        if method == "thread/start":
            return {"thread": {"id": "thread-1"}}
        return {}

    async def event(self):
        return await self.events.get()

    async def start_thread(self, model=None):
        await self.request("thread/start", thread_parameters(Path.cwd(), model))
        return "thread-1"

    async def close(self):
        self.closed = True


def test_device_login_success_is_ephemeral_subscription_only_and_idempotent(tmp_path):
    async def run():
        rpc = FakeRPC()
        login = CodexLogin(tmp_path, rpc_factory=lambda *_, **kwargs: rpc)
        assert (await login.start()).status == "pending"
        assert (await login.start()).user_code == "ABCD-1234"
        assert sum(method == "account/login/start" for method, _ in rpc.requests) == 1
        # A different flow cannot complete this request.
        await rpc.events.put({"method": "account/login/completed", "params": {"loginId": "another", "success": True}})
        await asyncio.sleep(0)
        assert login.snapshot().status == "pending"
        rpc.account = {"type": "chatgpt", "email": "private-account@example.test"}
        await rpc.events.put({"method": "account/login/completed", "params": {"loginId": "login-1", "success": True}})
        await login.task
        state = login.snapshot().model_dump_json()
        assert login.snapshot().status == "authenticated"
        assert "ABCD" not in state and "private-account" not in state
        assert login.snapshot().verification_url is None and rpc.closed
        assert not list(tmp_path.iterdir())
    asyncio.run(run())


@pytest.mark.parametrize("field,value", [("verificationUrl", "https://evil.example/codex/device"), ("verificationUrl", DEVICE_URL + "?token=secret"), ("userCode", "<script>"), ("type", "apiKey"), ("loginId", "")])
def test_device_login_rejects_untrusted_or_incompatible_responses(tmp_path, field, value):
    async def run():
        rpc = FakeRPC()
        rpc.result[field] = value
        login = CodexLogin(tmp_path, rpc_factory=lambda *_, **kwargs: rpc)
        assert (await login.start()).status == "failed"
        assert rpc.closed and login.snapshot().user_code is None
    asyncio.run(run())


@pytest.mark.parametrize("outcome", ["cancel", "expire", "failure", "api_key", "external_tokens", "shutdown"])
def test_device_login_terminal_paths_clear_code_and_close_process(tmp_path, outcome):
    async def run():
        rpc = FakeRPC()
        login = CodexLogin(tmp_path, rpc_factory=lambda *_: rpc, lifetime=.01 if outcome == "expire" else 600)
        await login.start()
        if outcome == "cancel":
            await login.cancel()
        elif outcome == "shutdown":
            await login.close()
        elif outcome == "expire":
            await login.task
        else:
            rpc.account = {"type": "apiKey" if outcome == "api_key" else "chatgptAuthTokens"}
            await rpc.events.put({"method": "account/login/completed", "params": {"loginId": "login-1", "success": outcome != "failure", "error": "sensitive provider diagnostic"}})
            await login.task
        state = login.snapshot()
        assert state.status in ("cancelled", "expired", "failed")
        assert state.user_code is None and state.verification_url is None and rpc.closed
        assert "sensitive" not in state.model_dump_json()
        if outcome in ("cancel", "expire", "shutdown"):
            assert ("account/login/cancel", {"loginId": "login-1"}) in rpc.requests
    asyncio.run(run())


def test_existing_subscription_does_not_request_another_code(tmp_path):
    async def run():
        rpc = FakeRPC()
        rpc.account = {"type": "chatgpt"}
        login = CodexLogin(tmp_path, rpc_factory=lambda *_, **kwargs: rpc)
        assert (await login.start()).status == "authenticated"
        assert [method for method, _ in rpc.requests] == ["account/read"] and rpc.closed
    asyncio.run(run())


def test_login_api_requires_local_auth_and_never_persists_device_code(tmp_path):
    db = Database("sqlite://", testing=True)
    app = create_app(db, "x" * 40, tmp_path / "research")
    rpc = FakeRPC()
    app.state.codex_login.rpc_factory = lambda *_: rpc
    with TestClient(app) as client:
        assert client.post("/api/connections/codex/login").status_code == 401
        headers = {"Authorization": "Bearer " + "x" * 40}
        response = client.post("/api/connections/codex/login", headers=headers)
        assert response.json()["status"] == "pending" and response.headers["cache-control"] == "no-store"
        assert client.post("/api/research", json={"query": "example"}, headers=headers).status_code == 409
        assert client.get("/api/settings", headers=headers).json()["cloud_enabled"] is False
        assert not db.list("asset") and not db.list("settings")
        result = client.post("/api/connections/codex/login/cancel", headers=headers).json()
        assert result["status"] == "cancelled" and result["user_code"] is None


def test_rpc_preserves_notifications_before_response_and_sanitizes_errors(tmp_path):
    async def run():
        rpc = CodexRPC(tmp_path, tmp_path)
        messages = deque([{"method": "item/agentMessage/delta", "params": {"delta": "early"}}, {"id": 1, "result": {"ok": True}}])
        sent = []
        async def send(value): sent.append(value)
        async def receive(): return messages.popleft()
        rpc.send, rpc.receive = send, receive
        assert await rpc.request("turn/start", {}) == {"ok": True}
        assert (await rpc.event())["params"]["delta"] == "early"
        messages.append({"id": 2, "error": {"message": "secret diagnostic"}})
        with pytest.raises(RuntimeFailure) as error:
            await rpc.request("account/read", {})
        assert "secret diagnostic" not in str(error.value)
    asyncio.run(run())


@pytest.mark.parametrize("mode", ["permission", "flood", "timeout", "malformed"])
def test_rpc_fails_closed_on_unbounded_or_unexpected_protocol(tmp_path, mode):
    async def run():
        rpc = CodexRPC(tmp_path, tmp_path)
        async def send(_): pass
        async def receive():
            if mode == "timeout": await asyncio.sleep(1)
            if mode == "permission": return {"id": 1, "method": "item/commandExecution/requestApproval"}
            if mode == "malformed": return {"unrecognized": "private"}
            return {"method": "noise"}
        rpc.send, rpc.receive = send, receive
        with pytest.raises(RuntimeFailure): await rpc.request("test", {}, timeout=.01)
        assert len(rpc.pending) <= 256
    asyncio.run(run())


@pytest.mark.parametrize("raw", [b"[]\n", b"invalid\n", b""])
def test_rpc_rejects_non_object_and_malformed_wire_output(tmp_path, raw):
    async def run():
        rpc = CodexRPC(tmp_path, tmp_path)
        reader = asyncio.StreamReader()
        reader.feed_data(raw); reader.feed_eof()
        rpc.process = SimpleNamespace(stdout=reader)
        with pytest.raises(RuntimeFailure): await rpc.receive()
    asyncio.run(run())


def test_codex_generation_checks_subscription_and_normalizes_events(tmp_path, monkeypatch):
    async def run():
        rpc = FakeRPC()
        rpc.account = {"type": "chatgpt"}
        for event in [
            {"method": "item/reasoning/summaryTextDelta", "params": {"delta": "hidden"}},
            {"method": "item/agentMessage/delta", "params": {"delta": "Answer"}},
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}},
        ]: await rpc.events.put(event)
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)
        # Explicit synthetic qualification, not a production supported-version claim.
        async def qualified_check(self):
            return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified_check)
        events = [event async for event in CodexRuntime(tmp_path).stream("question", "run", tmp_path)]
        assert [event.text for event in events] == ["Answer"] and rpc.closed
        thread = next(params for method, params in rpc.requests if method == "thread/start")
        assert thread["sandbox"] == "read-only" and thread["approvalPolicy"] == "on-request"
        rpc.account = {"type": "apiKey"}
        rpc.requests.clear()
        with pytest.raises(RuntimeFailure, match="API-key"):
            _ = [event async for event in CodexRuntime(tmp_path).stream("question", "run", tmp_path)]
        assert all(method != "turn/start" for method, _ in rpc.requests)
    asyncio.run(run())


@pytest.mark.parametrize("kind,browsing", [("commandExecution", True), ("fileChange", True), ("mcpToolCall", True), ("webSearch", False), ("unknownTool", True)])
def test_unexpected_tool_events_abort_without_exposing_payloads(tmp_path, monkeypatch, kind, browsing):
    async def run():
        rpc = FakeRPC()
        rpc.account = {"type": "chatgpt"}
        await rpc.events.put({"method": "item/started", "params": {"item": {"type": kind, "arguments": "private provider payload"}}})
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)
        async def qualified_check(self):
            return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified_check)
        with pytest.raises(RuntimeFailure, match="permitted research tools") as exc:
            _ = [event async for event in CodexRuntime(tmp_path).stream("question", "run", tmp_path, allow_browsing=browsing)]
        assert rpc.closed and "private provider payload" not in str(exc.value)
    asyncio.run(run())
