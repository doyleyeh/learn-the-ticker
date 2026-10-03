import asyncio
import json

import httpx
import pytest

from backend.app.api import create_app
from backend.app.approvals import ApprovalBroker
from backend.app.codex_approvals import CodexApprovals
from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import ApprovalDecision, ResearchRequest, RuntimeCapabilities
from backend.app.db import Database
from backend.app.runtime_base import RuntimeFailure
from tests.desktop.test_codex import FakeRPC


def access(method="item/fileChange/requestApproval", **params):
    return {"id": 9, "method": method, "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1", "reason": "sensitive raw reason", "grantRoot": "C:/private", **params}}


class ReviewRPC(FakeRPC):
    def __init__(self):
        super().__init__()
        self.account = {"type": "chatgpt"}
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


async def pending(broker):
    for _ in range(100):
        if broker.snapshot(): return broker.snapshot()[0]
        await asyncio.sleep(.001)
    pytest.fail("access review did not appear")


@pytest.mark.parametrize("method,response", [
    ("item/fileChange/requestApproval", {"decision": "decline"}),
    ("item/commandExecution/requestApproval", {"decision": "decline"}),
    ("item/permissions/requestApproval", {"permissions": {}, "scope": "turn"}),
])
def test_correlated_denial_never_echoes_or_grants_vendor_scope(method, response):
    async def run():
        broker, rpc = ApprovalBroker(), ReviewRPC()
        handler = CodexApprovals(rpc, broker, "run-1", "thread-1", "turn-1")
        task = asyncio.create_task(handler.handle(access(method, permissions={"network": {"enabled": True}})))
        request = await pending(broker)
        assert "private" not in request.model_dump_json() and "sensitive" not in request.model_dump_json()
        broker.resolve("run-1", request.id, ApprovalDecision(decision="deny"))
        with pytest.raises(ValueError): broker.resolve("run-1", request.id, ApprovalDecision(decision="deny"))
        await task
        assert rpc.sent == [{"id": 9, "result": response}] and not broker.snapshot()
        with pytest.raises(RuntimeFailure, match="repeated"): await handler.handle(access(method))
    asyncio.run(run())


@pytest.mark.parametrize("change", [
    {"params": {"threadId": "foreign", "turnId": "turn-1", "itemId": "item"}},
    {"params": {"threadId": "thread-1", "turnId": "foreign", "itemId": "item"}},
    {"params": []}, {"id": True}, {"id": "private\nvalue"},
    {"method": "item/tool/call"}, {"method": "account/chatgptAuthTokens/refresh"},
])
def test_foreign_malformed_or_unsupported_requests_never_reach_review(change):
    async def run():
        broker, rpc = ApprovalBroker(), ReviewRPC()
        with pytest.raises(RuntimeFailure): await CodexApprovals(rpc, broker, "run", "thread-1", "turn-1").handle(access() | change)
        assert not broker.snapshot() and not rpc.sent
    asyncio.run(run())


def test_expiry_and_cancellation_clear_ephemeral_requests_without_grant():
    async def run():
        broker, rpc = ApprovalBroker(lifetime=.01), ReviewRPC()
        with pytest.raises(RuntimeFailure, match="expired"):
            await CodexApprovals(rpc, broker, "run", "thread-1", "turn-1").handle(access())
        assert rpc.sent == [{"id": 9, "result": {"decision": "cancel"}}]
        assert not broker.snapshot()
        broker = ApprovalBroker()
        task = asyncio.create_task(broker.review("run", "codex", "permissions"))
        request = await pending(broker)
        with pytest.raises(ValueError): broker.resolve("foreign-run", request.id, ApprovalDecision(decision="deny"))
        with pytest.raises(RuntimeFailure, match="Another"): await broker.review("other", "codex", "command")
        broker.cancel("run")
        with pytest.raises(asyncio.CancelledError): await task
        assert not broker.snapshot()
        with pytest.raises(ValueError): broker.resolve("run", request.id, ApprovalDecision(decision="deny"))
        assert not ApprovalBroker().snapshot()  # No recovery or replay across broker instances.
    asyncio.run(run())


def test_user_cancel_is_terminal_and_request_limit_is_bounded():
    async def run():
        broker, rpc = ApprovalBroker(), ReviewRPC()
        handler = CodexApprovals(rpc, broker, "run", "thread-1", "turn-1")
        task = asyncio.create_task(handler.handle(access("item/permissions/requestApproval")))
        request = await pending(broker)
        broker.resolve("run", request.id, ApprovalDecision(decision="cancel"))
        with pytest.raises(asyncio.CancelledError): await task
        assert rpc.sent[-1]["result"] == {"permissions": {}, "scope": "turn"}
        handler.seen = {(int, n) for n in range(3)}
        with pytest.raises(RuntimeFailure, match="exceeded"): await handler.handle(access())
    asyncio.run(run())


@pytest.mark.parametrize("outcome", ["deny", "cancel", "revoke"])
def test_authenticated_app_reviews_active_run_only_and_excludes_requests_from_library(tmp_path, monkeypatch, outcome):
    async def run():
        rpc = ReviewRPC()
        await rpc.events.put(access())
        await rpc.events.put({"method": "item/agentMessage/delta", "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "message-1", "delta": json.dumps({"candidates": [], "sources": [], "claims": []})}})
        await rpc.events.put({"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"}}})
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)
        async def qualified(self):
            return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified)
        db = Database("sqlite://", testing=True)
        app = create_app(db, "x" * 40, tmp_path, adapters={"codex": CodexRuntime(tmp_path)})
        service = app.state.service
        db.put("settings", "settings", {"cloud_enabled": True})
        job = await service.submit(ResearchRequest(query="Explain this example business"))
        task = service.tasks[job["id"]]
        request = await pending(service.approvals)
        route = f"/api/jobs/{job['id']}/approvals/{request.id}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            assert (await client.get("/api/approvals")).status_code == 401
            assert (await client.post(route, json={"decision": "deny"})).status_code == 401
            client.headers["Authorization"] = "Bearer " + "x" * 40
            response = await client.get("/api/approvals")
            assert response.headers["cache-control"] == "no-store" and len(response.json()) == 1
            assert (await client.post(route, json={"decision": "accept"})).status_code == 422
            assert (await client.post(route, json={"decision": "deny", "permissions": {"network": True}})).status_code == 422
            assert (await client.post(route.replace(job["id"], "foreign"), json={"decision": "deny"})).status_code == 409
            if outcome == "revoke":
                assert (await client.put("/api/settings", json={"cloud_enabled": False})).status_code == 200
            else:
                assert (await client.post(route, json={"decision": outcome})).status_code == 200
            await asyncio.gather(task, return_exceptions=True)
            assert (await client.post(route, json={"decision": "deny"})).status_code == 409
            assert (await client.get("/api/approvals")).json() == []
        assert rpc.closed and db.job(job["id"])["status"] == ("needs_identity" if outcome == "deny" else "cancelled")
        persisted = json.dumps(db.events(job["id"]))
        assert request.id not in persisted and "sensitive" not in persisted and "C:/private" not in persisted
        assert not db.list("approval")
        await service.close()
    asyncio.run(run())
