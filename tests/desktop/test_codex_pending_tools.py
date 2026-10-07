import asyncio

import pytest

from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import RuntimeFailure
from tests.desktop.test_approvals import ReviewRPC, access, restricted_item
from tests.desktop.test_codex_messages import message, turn_completed


class Decision:
    def __init__(self, outcome="deny"):
        self.outcome, self.calls = outcome, 0

    async def review(self, *args):
        self.calls += 1
        return self.outcome


@pytest.fixture
def connection(tmp_path, monkeypatch):
    rpc = ReviewRPC()
    monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)
    async def qualified(self):
        return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
    monkeypatch.setattr(CodexRuntime, "check", qualified)
    runtime = CodexRuntime(tmp_path)
    runtime.approvals = Decision()
    return rpc, runtime


@pytest.mark.parametrize("kind", ["fileChange", "commandExecution"])
@pytest.mark.parametrize("outcome", ["deny", "cancel", "expired"])
def test_proposed_work_can_only_be_declined_or_cancelled(connection, tmp_path, kind, outcome):
    async def run():
        rpc, runtime = connection
        runtime.approvals = Decision(outcome)
        for item in [restricted_item(kind=kind), access(f"item/{kind}/requestApproval"),
                     restricted_item("declined", kind), *message("answer", "Answer", "final_answer"), turn_completed()]:
            await rpc.events.put(item)
        output = []
        async def collect():
            async for item in runtime.stream("synthetic", "run", tmp_path): output.append(item)
        if outcome == "deny": await collect()
        elif outcome == "cancel":
            with pytest.raises(asyncio.CancelledError): await collect()
        else:
            with pytest.raises(RuntimeFailure, match="expired"): await collect()
        assert [item.text for item in output if item.kind == "message.delta"] == (["Answer"] if outcome == "deny" else [])
        assert runtime.approvals.calls == 1 and rpc.closed
        assert rpc.sent == [{"id": 9, "result": {"decision": "decline" if outcome == "deny" else "cancel"}}]
        assert "sensitive" not in repr(output) and "C:/private" not in repr(output)
        if outcome != "deny": assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in rpc.requests
    asyncio.run(run())


def changed_start(**fields):
    event = restricted_item()
    event["params"]["item"].update(fields)
    return event


@pytest.mark.parametrize("events", [
    [access()],
    [restricted_item("declined")],
    [restricted_item(), restricted_item("declined")],
    [restricted_item(), access("item/commandExecution/requestApproval")],
    [restricted_item(), restricted_item()],
    [restricted_item()],
    [restricted_item(), access()],
    [restricted_item(), access(), restricted_item("completed")],
    [restricted_item(), access(), restricted_item("failed")],
    [restricted_item(), access(), restricted_item("declined", item_id="foreign")],
    [restricted_item(), access(), restricted_item("declined"), restricted_item("declined")],
    [restricted_item(), access(), access() | {"id": 10}],
    [changed_start(aggregatedOutput="PRIVATE_EXECUTED_OUTPUT")],
    [changed_start(exitCode=0)],
    [changed_start(status="completed")],
    [changed_start(id=[])],
    [restricted_item(item_id=str(n)) for n in range(4)],
])
def test_unreviewed_executed_replayed_or_unresolved_tools_never_publish_answer(connection, tmp_path, events):
    async def run():
        rpc, runtime = connection
        for item in [*events, *message("answer", "PRIVATE_ANSWER", "final_answer"), turn_completed()]:
            await rpc.events.put(item)
        output = []
        with pytest.raises(RuntimeFailure) as error:
            async for item in runtime.stream("synthetic", "run", tmp_path): output.append(item)
        assert not any(item.kind == "message.delta" for item in output)
        assert "PRIVATE" not in str(error.value) + repr(output)
        assert rpc.closed and all(reply["result"] == {"decision": "decline"} for reply in rpc.sent)
        assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in rpc.requests
    asyncio.run(run())


@pytest.mark.parametrize("kind", ["fileChange", "commandExecution"])
def test_cached_only_operations_cannot_open_tool_review(connection, tmp_path, kind):
    async def run():
        rpc, runtime = connection
        await rpc.events.put(restricted_item(kind=kind))
        with pytest.raises(RuntimeFailure, match="permitted research tools"):
            _ = [item async for item in runtime.stream("synthetic", "run", tmp_path, allow_browsing=False)]
        assert runtime.approvals.calls == 0 and not rpc.sent and rpc.closed
    asyncio.run(run())


@pytest.mark.parametrize("method", ["item/commandExecution/outputDelta", "item/commandExecution/terminalInteraction",
                                   "item/fileChange/outputDelta", "command/exec/outputDelta", "process/outputDelta"])
def test_execution_output_cannot_hide_between_pending_and_declined_items(connection, tmp_path, method):
    async def run():
        rpc, runtime = connection
        for item in [restricted_item(), access(),
                     {"method": method, "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1", "delta": "PRIVATE_OUTPUT"}},
                     restricted_item("declined"), *message("answer", "PRIVATE_ANSWER", "final_answer"), turn_completed()]:
            await rpc.events.put(item)
        output = []
        with pytest.raises(RuntimeFailure, match="permitted research tools") as error:
            async for item in runtime.stream("synthetic", "run", tmp_path): output.append(item)
        assert not any(item.kind == "message.delta" for item in output)
        assert "PRIVATE" not in str(error.value) + repr(output)
        assert runtime.approvals.calls == 1 and rpc.closed
        assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in rpc.requests
    asyncio.run(run())
