import asyncio
import json

import pytest

from backend.app.codex_runtime import CodexRuntime
from backend.app.codex_messages import MAX_CHARACTERS, MAX_MESSAGES
from backend.app.contracts import ResearchRequest, RuntimeCapabilities, TermRequest
from backend.app.runtime_base import RuntimeFailure
from tests.desktop.test_codex import FakeRPC


def event(method, **params):
    return {"method": method, "params": {"threadId": "thread-1", "turnId": "turn-1", **params}}


def message(item_id, text, phase=None):
    item = {"type": "agentMessage", "id": item_id, "phase": phase}
    return [
        event("item/started", item=item | {"text": ""}),
        event("item/agentMessage/delta", itemId=item_id, delta=text),
        event("item/completed", item=item | {"text": text}),
    ]


def turn_completed(status="completed"):
    return event("turn/completed", turn={"id": "turn-1", "status": status})


@pytest.fixture
def rpc(monkeypatch):
    rpc = FakeRPC()
    rpc.account = {"type": "chatgpt"}
    monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)

    async def qualified(self):
        return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)

    # Synthetic transport only; never changes production qualification or starts a process.
    monkeypatch.setattr(CodexRuntime, "check", qualified)
    return rpc


def test_commentary_cannot_contaminate_structured_answer(tmp_path, rpc):
    async def run():
        answer = '{"candidates": [], "sources": [], "claims": []}'
        for item in [*message("progress", "PRIVATE_PROGRESS_SENTINEL", "commentary"),
                     *message("answer", answer, "final_answer"), turn_completed()]:
            await rpc.events.put(item)
        events = [item async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path)]
        text = "".join(item.text for item in events if item.kind == "message.delta")
        assert text == answer
        assert json.loads(text)["claims"] == []
        assert "PRIVATE_PROGRESS_SENTINEL" not in repr(events)
        assert rpc.closed
    asyncio.run(run())


@pytest.mark.parametrize("messages,expected", [
    ([*message("a", "Legacy "), *message("b", "answer")], "Legacy answer"),
    ([*message("a", "Unknown progress"), *message("b", "Answer", "final_answer")], "Answer"),
    ([*message("a", "Progress", "commentary"), *message("b", "Legacy answer")], "Legacy answer"),
    ([*message("a", "Progress", "commentary")], ""),
    ([*message("a", "Part one ", "final_answer"), *message("b", "part two", "final_answer")], "Part one part two"),
])
def test_explicit_answers_take_precedence_and_unknown_phases_keep_legacy_order(tmp_path, rpc, messages, expected):
    async def run():
        for item in [*messages, turn_completed()]:
            await rpc.events.put(item)
        events = [item async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path)]
        assert "".join(item.text for item in events) == expected
        assert rpc.closed
    asyncio.run(run())


@pytest.mark.parametrize("start_phase,end_phase", [(None, "final_answer"), ("final_answer", None), (None, None)])
def test_completed_item_is_authoritative_even_without_full_deltas(tmp_path, rpc, start_phase, end_phase):
    async def run():
        events = message("answer", "PARTIAL_PRIVATE_DELTA", start_phase)
        events[-1]["params"]["item"].update(phase=end_phase, text="Authoritative answer")
        for item in [*events, turn_completed()]:
            await rpc.events.put(item)
        output = [item async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path)]
        assert [item.text for item in output] == ["Authoritative answer"]
    asyncio.run(run())


@pytest.mark.parametrize("events", [
    [event("item/agentMessage/delta", itemId="unknown", delta="PRIVATE")],
    [message("a", "PRIVATE")[-1]],
    [message("a", "PRIVATE")[0], message("a", "PRIVATE")[0]],
    [*message("a", "PRIVATE"), message("a", "PRIVATE")[-1]],
    [*message("a", "PRIVATE"), event("item/agentMessage/delta", itemId="a", delta="PRIVATE")],
    [message("a", "PRIVATE")[0]],
    [message("a", "PRIVATE", "commentary")[0], message("a", "PRIVATE", "final_answer")[-1]],
    [event("item/started", item={"type": "agentMessage", "id": [], "text": "PRIVATE"})],
    [event("item/started", item={"type": "agentMessage", "id": "a", "text": "PRIVATE", "phase": "unknown"})],
    [event("item/started", item={"type": "agentMessage", "id": "a", "text": "PRIVATE", "phase": {}})],
    [event("item/started", item={"type": "agentMessage", "id": "a"})],
    [message("a", "PRIVATE")[0], event("item/agentMessage/delta", itemId="a", delta=[])],
    [message("a", "PRIVATE")[0], event("item/completed", item={"type": "agentMessage", "id": "a", "text": []})],
])
def test_invalid_message_lifecycle_fails_without_output_or_replay(tmp_path, rpc, events):
    async def run():
        for item in [*events, turn_completed()]:
            await rpc.events.put(item)
        output = []
        with pytest.raises(RuntimeFailure) as error:
            async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path):
                output.append(item)
        assert not output and "PRIVATE" not in str(error.value)
        assert rpc.closed
        assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in rpc.requests
        assert sum(method == "turn/start" for method, _ in rpc.requests) == 1
    asyncio.run(run())


@pytest.mark.parametrize("location", ["start", "delta", "completion", "cumulative_delta", "cumulative_completion", "items"])
def test_discarded_commentary_and_answers_are_bounded(tmp_path, rpc, location):
    async def run():
        oversized = "x" * (MAX_CHARACTERS + 1)
        if location == "items":
            events = [item for n in range(MAX_MESSAGES + 1) for item in message(str(n), "", "commentary")]
        elif location.startswith("cumulative"):
            events = [*message("a", "x" * MAX_CHARACTERS, "commentary"), *message("b", "x", "commentary")]
            if location == "cumulative_completion":
                events = [item for item in events if item["method"] != "item/agentMessage/delta"]
        else:
            events = message("a", "", "commentary")
            if location == "start": events[0]["params"]["item"]["text"] = oversized
            elif location == "delta": events[1]["params"]["delta"] = oversized
            else: events[2]["params"]["item"]["text"] = oversized
        for item in [*events, turn_completed()]:
            await rpc.events.put(item)
        with pytest.raises(RuntimeFailure, match="exceeded"):
            _ = [item async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path)]
        assert rpc.closed
    asyncio.run(run())


@pytest.mark.parametrize("terminal", [
    turn_completed("failed"),
    event("error", error={"message": "PRIVATE_DIAGNOSTIC"}),
    event("item/started", item={"type": "commandExecution", "command": "PRIVATE_COMMAND"}),
])
def test_answer_is_withheld_if_turn_later_fails_or_uses_prohibited_tool(tmp_path, rpc, terminal):
    async def run():
        for item in [*message("a", "PRIVATE_ANSWER", "final_answer"), terminal]:
            await rpc.events.put(item)
        output = []
        with pytest.raises(RuntimeFailure) as error:
            async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path):
                output.append(item)
        assert not output and "PRIVATE" not in str(error.value) and rpc.closed
    asyncio.run(run())


def test_cancellation_discards_buffered_answer_and_interrupts_owned_turn(tmp_path, rpc):
    async def run():
        for item in message("a", "PRIVATE_ANSWER", "final_answer"):
            await rpc.events.put(item)
        drained = asyncio.Event()
        receive = rpc.event

        async def observed_event():
            if rpc.events.empty(): drained.set()
            return await receive()

        rpc.event = observed_event
        output = []

        async def collect():
            async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path):
                output.append(item)

        task = asyncio.create_task(collect())
        await asyncio.wait_for(drained.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        assert not output and rpc.closed
        assert ("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}) in rpc.requests
    asyncio.run(run())


def test_search_progress_remains_normalized_and_reasoning_is_discarded(tmp_path, rpc):
    async def run():
        for item in [*message("a", "PRIVATE_PROGRESS", "commentary"),
                     event("item/reasoning/textDelta", delta="PRIVATE_REASONING"),
                     event("item/started", item={"type": "webSearch", "id": "search", "query": "PRIVATE_QUERY"}),
                     *message("b", "Answer", "final_answer"), turn_completed()]:
            await rpc.events.put(item)
        output = [item async for item in CodexRuntime(tmp_path).stream("example", "run", tmp_path)]
        assert [(item.kind, item.text) for item in output] == [("tool.started", "Searching online sources"), ("message.delta", "Answer")]
        assert "PRIVATE" not in repr(output)
    asyncio.run(run())


@pytest.mark.parametrize("consumer", ["research", "term"])
@pytest.mark.parametrize("invalid_final", [False, True])
def test_only_completed_answer_reaches_structured_validation_and_persistence(tmp_path, rpc, consumer, invalid_final):
    from backend.app.api import create_app
    from backend.app.db import Database
    from backend.app.evidence import verify_candidate
    from tests.desktop.test_application import TOKEN, payload
    from tests.desktop.test_terms import setup

    async def run():
        runtime = CodexRuntime(tmp_path)
        if consumer == "research":
            db = Database("sqlite://", testing=True)
            service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, verifier=lambda s, a: verify_candidate(s, a, lambda _: "Synthetic Example Company provides test services.")).state.service
            research = service
            db.put("settings", "settings", {"cloud_enabled": True})
            request = ResearchRequest(query="Synthetic business")
            answer = json.dumps(payload())
        else:
            db, bundle, _, research, service = setup(tmp_path, runtime)
            request = TermRequest(term="revenue", bundle_id=bundle.id)
            answer = json.dumps({"explanation": "Revenue describes sales before costs.", "basis": "snapshot", "source_ids": ["s1"]})
        messages = [*message("a", "PRIVATE_PROGRESS_SENTINEL", "commentary"), *message("b", answer, "final_answer")]
        if invalid_final:
            messages[-1]["params"]["item"]["text"] = "PRIVATE_INVALID_JSON"
        for item in [*messages, turn_completed()]:
            await rpc.events.put(item)
        job = await service.submit(request)
        await research.tasks[job["id"]]
        saved = db.job(job["id"])
        assert saved["status"] == ("failed" if invalid_final else "completed")
        persisted = json.dumps([saved, db.events(job["id"]), db.list("bundle"), db.list("term")])
        assert "PRIVATE_PROGRESS_SENTINEL" not in persisted and "PRIVATE_INVALID_JSON" not in persisted
        assert all(item["kind"] != "message.delta" for item in db.events(job["id"]))
        if invalid_final:
            assert not db.list("term")
            if consumer == "research": assert not db.list("bundle") and not db.list("asset")
        elif consumer == "research":
            assert len(saved["result"]["claims"]) == 1
        else:
            assert saved["result"]["interpretation"] and saved["result"]["source_ids"] == ["s1"]
        assert rpc.closed
        await research.close()
    asyncio.run(run())
