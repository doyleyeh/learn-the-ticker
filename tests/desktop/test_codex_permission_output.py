import asyncio
import json

import pytest

from backend.app.codex_approvals import CodexApprovals
from backend.app.runtime_base import RuntimeFailure
from tests.desktop.test_approvals import ReviewRPC, access


def output(**changes):
    return {"type": "functionCallOutput", "id": "item-1", "name": "request_permissions", "namespace": None,
            "output": json.dumps({"permissions": {"network": None, "file_system": None}, "scope": "turn"}), **changes}


async def denied():
    class Broker:
        async def review(self, *args): return "deny"
    rpc = ReviewRPC()
    handler = CodexApprovals(rpc, Broker(), "run", "thread-1", "turn-1")
    await handler.handle(access("item/permissions/requestApproval"))
    assert rpc.sent == [{"id": 9, "result": {"permissions": {}, "scope": "turn"}}]
    return handler


@pytest.mark.parametrize("started,array", [(False, False), (True, False), (False, True), (True, True)])
def test_only_correlated_denied_permission_outputs_can_finish(started, array):
    async def run():
        handler = await denied()
        item = output()
        if array: item["output"] = [{"type": "input_text", "text": item["output"]}]
        if started:
            handler.permission_output(item, completed=False)
            with pytest.raises(RuntimeFailure): handler.finish()
        handler.permission_output(item, completed=True)
        handler.finish()
        with pytest.raises(RuntimeFailure): handler.permission_output(item, completed=True)
        with pytest.raises(RuntimeFailure): await handler.handle({**access("item/permissions/requestApproval"), "id": 10})
    asyncio.run(run())


@pytest.mark.parametrize("changes", [
    {"id": "foreign"}, {"name": "exec_command"}, {"namespace": "untrusted"},
    {"output": "private-provider-diagnostic"}, {"output": "x" * 513},
    {"output": [{"type": "input_image", "image_url": "private"}]},
    {"output": '{"permissions":{},"permissions":{},"scope":"turn"}'},
    {"output": '{"permissions":{},"scope":"session"}'},
    {"output": '{"permissions":{"network":{"enabled":true}},"scope":"turn"}'},
    {"output": '{"permissions":{"file_system":{"write":["private"]}},"scope":"turn"}'},
    {"output": '{"permissions":{"unknown":null},"scope":"turn"}'},
    {"output": '{"permissions":{},"scope":"turn","extra":true}'},
])
def test_unknown_granted_or_malformed_outputs_fail_without_payload_leakage(changes):
    async def run():
        handler = await denied()
        with pytest.raises(RuntimeFailure) as exc: handler.permission_output(output(**changes), completed=True)
        assert "private" not in str(exc.value)
    asyncio.run(run())


def test_matching_function_output_without_denial_is_rejected():
    handler = CodexApprovals(ReviewRPC(), None, "run", "thread-1", "turn-1")
    with pytest.raises(RuntimeFailure): handler.permission_output(output(), completed=True)


@pytest.mark.parametrize("choice", ["allow", "unknown", None])
def test_broker_cannot_grant_even_with_an_invalid_decision(choice):
    async def run():
        class Broker:
            async def review(self, *args): return choice
        rpc = ReviewRPC()
        with pytest.raises(RuntimeFailure):
            await CodexApprovals(rpc, Broker(), "run", "thread-1", "turn-1").handle(access("item/permissions/requestApproval"))
        assert rpc.sent == [{"id": 9, "result": {"permissions": {}, "scope": "turn"}}]
    asyncio.run(run())
