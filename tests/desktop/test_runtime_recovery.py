import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.approvals import ApprovalBroker
from backend.app.codex_approvals import CodexApprovals
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import ResearchRequest, RuntimeCapabilities, RuntimeEvent
from backend.app.db import Database, Job
from backend.app.runtime_base import RuntimeFailure
from tests.desktop.test_approvals import ReviewRPC, access, pending
from tests.desktop.test_codex import FakeRPC


@pytest.mark.parametrize("method,params", [
    ("item/agentMessage/delta", {"threadId": "foreign", "turnId": "turn-1", "itemId": "item", "delta": "private"}),
    ("item/agentMessage/delta", {"threadId": "thread-1", "turnId": "old", "itemId": "item", "delta": "private"}),
    ("turn/completed", {"threadId": "thread-1", "turn": {"id": "old", "status": "completed"}}),
    ("turn/completed", {"threadId": "thread-1", "turn": []}),
])
def test_unrelated_events_never_complete_or_contaminate_a_turn(tmp_path, monkeypatch, method, params):
    async def run():
        rpc = FakeRPC(); rpc.account = {"type": "chatgpt"}
        await rpc.events.put({"method": method, "params": params})
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)
        async def qualified(self): return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified)
        emitted = []
        with pytest.raises(RuntimeFailure, match="unexpected thread or turn"):
            async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path): emitted.append(item)
        assert not emitted and rpc.closed
        assert sum(method == "turn/start" for method, _ in rpc.requests) == 1
        assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in rpc.requests
    asyncio.run(run())


def test_disconnect_with_pending_review_clears_request_without_reply_or_replay():
    async def run():
        broker, rpc = ApprovalBroker(), ReviewRPC()
        died = asyncio.Event()
        async def disconnected():
            await died.wait()
            raise RuntimeFailure("disconnected")
        rpc.wait_disconnected = disconnected
        task = asyncio.create_task(CodexApprovals(rpc, broker, "run", "thread-1", "turn-1").handle(access()))
        await pending(broker)
        died.set()
        with pytest.raises(RuntimeFailure, match="disconnected"): await task
        assert not broker.snapshot() and not rpc.sent
    asyncio.run(run())


def test_boolean_response_id_is_not_a_matching_integer_rpc_id(tmp_path):
    async def run():
        rpc = CodexRPC(tmp_path, tmp_path)
        async def send(value): pass
        async def receive(): return {"id": True, "result": {}}
        rpc.send, rpc.receive = send, receive
        with pytest.raises(RuntimeFailure, match="unexpected response"): await rpc.request("example", {})
    asyncio.run(run())


def test_process_exit_is_detected_even_if_stdout_descendant_pipe_stays_open(tmp_path):
    async def run():
        rpc = CodexRPC(tmp_path, tmp_path)
        rpc.process = SimpleNamespace(returncode=None)
        waiting = asyncio.create_task(rpc.wait_disconnected())
        await asyncio.sleep(0)
        rpc.process.returncode = 7
        with pytest.raises(RuntimeFailure, match="retry explicitly"): await asyncio.wait_for(waiting, 1)
    asyncio.run(run())


@pytest.mark.parametrize("mode", ["cancel", "oversized"])
def test_consumer_failure_or_cancellation_closes_generator_before_return(tmp_path, mode):
    async def run():
        entered, closed = asyncio.Event(), asyncio.Event()
        class Runtime:
            async def stream(self, *args):
                try:
                    entered.set()
                    if mode == "cancel": await asyncio.Future()
                    yield RuntimeEvent(run_id=args[1], kind="message.delta", text="x" * 1_000_001)
                finally:
                    closed.set()
        db = Database("sqlite://", testing=True)
        app = create_app(db, "x" * 40, tmp_path, adapters={"codex": Runtime()})
        service = app.state.service
        db.put("settings", "settings", {"cloud_enabled": True})
        job = await service.submit(ResearchRequest(query="Explain an example business"))
        task = service.tasks[job["id"]]
        await entered.wait()
        if mode == "cancel": await service.cancel(job["id"])
        else: await task
        assert closed.is_set()
        assert db.job(job["id"])["status"] == ("cancelled" if mode == "cancel" else "failed")
    asyncio.run(run())


def test_service_restart_marks_interrupted_and_state_reads_do_not_replay(tmp_path):
    class NoReplay:
        async def stream(self, *args, **kwargs): pytest.fail("replayed inference"); yield
    db = Database("sqlite://", testing=True)
    with db.session.begin() as session:
        session.add(Job(id="previous-run", request=ResearchRequest(query="example").model_dump(mode="json"), status="running"))
    app = create_app(db, "x" * 40, tmp_path, adapters={"codex": NoReplay()})
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + "x" * 40}
        for _ in range(2):
            assert client.get("/api/jobs/previous-run", headers=headers).json()["status"] == "interrupted"
            assert client.get("/api/approvals", headers=headers).json() == []
        assert not app.state.service.tasks


def test_cancel_interrupts_only_current_turn_and_reconnect_requires_new_explicit_run(tmp_path, monkeypatch):
    async def run():
        first, second = FakeRPC(), FakeRPC()
        first.account = second.account = {"type": "chatgpt"}
        queue = [first, second]
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: queue.pop(0))
        async def qualified(self): return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified)
        runtime = CodexRuntime(tmp_path)
        async def collect(): return [event async for event in runtime.stream("example", "run", tmp_path)]
        task = asyncio.create_task(collect())
        async with asyncio.timeout(1):
            while not any(method == "turn/start" for method, _ in first.requests): await asyncio.sleep(.001)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        assert first.closed and len(queue) == 1
        assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in first.requests
        await second.events.put({"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"}}})
        assert await collect() == []
        assert second.closed
        for rpc in (first, second):
            assert sum(method == "turn/start" for method, _ in rpc.requests) == 1
            assert not any(method == "thread/resume" for method, _ in rpc.requests)
            assert next(params for method, params in rpc.requests if method == "thread/start")["ephemeral"]
