import asyncio
from collections import deque

import pytest

from backend.app.codex_rpc import CodexRPC
from backend.app.runtime_base import RuntimeFailure
from scripts.qualify_conversation_learning import observed_rpc


TIMEOUT = {"code": -32603, "message": "workspace routing discovery timed out"}


def transport(tmp_path, messages, rpc_type=CodexRPC):
    rpc, sent = rpc_type(tmp_path, tmp_path), []
    responses = deque(messages)
    async def send(message):
        sent.append(message)
    async def receive():
        return responses.popleft()
    rpc.send, rpc.receive = send, receive
    return rpc, sent


def test_account_timeout_rechecks_with_new_ids_preserving_ordered_notifications(tmp_path):
    async def run():
        account = {"account": {"type": "chatgpt"}}
        rpc, sent = transport(tmp_path, [
            {"method": "account/updated", "params": {"authMode": "chatgpt"}},
            {"id": 1, "error": TIMEOUT},
            {"method": "test/notification", "params": {}},
            {"id": 2, "result": account},
        ])
        assert await rpc.request("account/read", {"refreshToken": False}) == account
        assert sent == [{"id": i, "method": "account/read", "params": {"refreshToken": False}} for i in (1, 2)]
        assert [(await rpc.event())["method"] for _ in range(2)] == ["account/updated", "test/notification"]
    asyncio.run(run())


def test_repeated_routing_timeouts_stop_after_three_total_attempts(tmp_path):
    async def run():
        rpc, sent = transport(tmp_path, [{"id": i, "error": TIMEOUT} for i in (1, 2, 3)])
        with pytest.raises(RuntimeFailure, match="rejected the request"):
            await rpc.request("account/read", {"refreshToken": False})
        assert len(sent) == 3
    asyncio.run(run())


@pytest.mark.parametrize("method,params,error", [
    ("turn/start", {}, TIMEOUT),
    ("thread/start", {}, TIMEOUT),
    ("account/rateLimits/read", {}, TIMEOUT),
    ("account/read", {"refreshToken": True}, TIMEOUT),
    ("account/read", {}, TIMEOUT),
    ("account/read", {"refreshToken": 0}, TIMEOUT),
    ("account/read", {"refreshToken": False, "extra": True}, TIMEOUT),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "message": "workspace routing discovery unauthorized (401)"}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "message": "workspace routing discovery failed"}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "message": "account changed during workspace routing discovery"}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "message": "workspace routing discovery timed out: private details"}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "code": "-32603"}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "code": -32602}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "data": {"reason": "private details"}}),
    ("account/read", {"refreshToken": False}, {**TIMEOUT, "extra": "private details"}),
])
def test_other_operations_and_ambiguous_authentication_failures_never_retry(tmp_path, method, params, error):
    async def run():
        rpc, sent = transport(tmp_path, [{"id": 1, "error": error}])
        with pytest.raises(RuntimeFailure) as caught:
            await rpc.request(method, params)
        assert len(sent) == 1 and "private" not in str(caught.value)
    asyncio.run(run())


@pytest.mark.parametrize("next_response", [
    {"id": 2, "result": {"account": None}},
    {"id": 2, "result": {"account": {"type": "apiKey"}}},
])
def test_recovery_returns_actual_account_without_reusing_earlier_authentication(tmp_path, next_response):
    async def run():
        from backend.app.codex_runtime import subscription_account
        rpc, sent = transport(tmp_path, [{"id": 1, "error": TIMEOUT}, next_response])
        result = await rpc.request("account/read", {"refreshToken": False})
        assert not subscription_account(result) and len(sent) == 2
    asyncio.run(run())


@pytest.mark.parametrize("response", [
    {"id": 1, "error": TIMEOUT},  # Stale first request response during recovery.
    {"id": True, "error": TIMEOUT},
    {"id": 2, "method": "item/permissions/request", "error": TIMEOUT},
    {"id": 2, "error": {**TIMEOUT, "message": "workspace routing discovery unauthorized (401)"}},
    {"id": 2, "error": TIMEOUT, "result": {}},
])
def test_bad_or_denied_response_during_recovery_stops_without_third_attempt(tmp_path, response):
    async def run():
        rpc, sent = transport(tmp_path, [{"id": 1, "error": TIMEOUT}, response])
        with pytest.raises(RuntimeFailure):
            await rpc.request("account/read", {"refreshToken": False})
        assert len(sent) == 2
    asyncio.run(run())


def test_original_request_deadline_includes_retry_backoff(tmp_path):
    async def run():
        rpc, sent = transport(tmp_path, [{"id": 1, "error": TIMEOUT}])
        with pytest.raises(RuntimeFailure, match="timed out"):
            await rpc.request("account/read", {"refreshToken": False}, timeout=.01)
        assert len(sent) == 1
    asyncio.run(run())


@pytest.mark.parametrize("method,params,explicit,expected", [
    ("account/read", {"refreshToken": False}, None, 60),
    ("account/read", {"refreshToken": False}, .1, .1),
    ("account/read", {"refreshToken": True}, None, 30),
    ("account/read", {"refreshToken": 0}, None, 30),
    ("turn/start", {}, None, 30),
    ("turn/interrupt", {}, 2, 2),
])
def test_default_recovery_budget_is_account_only_and_explicit_deadlines_take_precedence(tmp_path, monkeypatch, method, params, explicit, expected):
    async def run():
        deadlines = []
        original_timeout = asyncio.timeout
        def observed_timeout(delay):
            deadlines.append(delay)
            return original_timeout(delay)
        monkeypatch.setattr(asyncio, "timeout", observed_timeout)
        rpc, sent = transport(tmp_path, [{"id": 1, "result": {}}])
        assert await rpc.request(method, params, timeout=explicit) == {}
        assert deadlines == [expected] and len(sent) == 1
    asyncio.run(run())


def test_qualification_identifies_a_deadline_without_exposing_request_data(tmp_path, monkeypatch):
    async def run():
        async def send(self, message): pass
        async def receive(self):
            await asyncio.sleep(1)
        monkeypatch.setattr(CodexRPC, "send", send)
        monkeypatch.setattr(CodexRPC, "receive", receive)
        report = {}
        rpc = observed_rpc(report)(tmp_path, tmp_path)
        with pytest.raises(RuntimeFailure, match="timed out"):
            await rpc.request("turn/start", {"private": "prompt"}, timeout=.01)
        assert report == {"failed_request": {"method": "turn/start", "diagnostic": "rpc_timeout", "account_read_attempts": 0}}
    asyncio.run(run())


def test_cancellation_during_recovery_prevents_the_next_request(tmp_path):
    async def run():
        rpc, sent = transport(tmp_path, [{"id": 1, "error": TIMEOUT}])
        task = asyncio.create_task(rpc.request("account/read", {"refreshToken": False}))
        await asyncio.sleep(0)  # First attempt receives its response, then waits.
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(sent) == 1
    asyncio.run(run())


def test_qualification_records_recovered_error_and_retry_count_without_raw_payloads(tmp_path, monkeypatch):
    async def run():
        responses = deque([{"id": 1, "error": TIMEOUT}, {"id": 2, "result": {"account": {"type": "chatgpt"}}}])
        async def send(self, message): pass
        async def receive(self): return responses.popleft()
        monkeypatch.setattr(CodexRPC, "send", send)
        monkeypatch.setattr(CodexRPC, "receive", receive)
        report = {}
        rpc = observed_rpc(report)(tmp_path, tmp_path)
        await rpc.request("account/read", {"refreshToken": False})
        diagnostic = {"method": "account/read", "response": "rpc_error", "code": "-32603", "category": "routing_timeout"}
        assert report == {"first_error": diagnostic, "last_error": diagnostic, "account_read_retries": 1}
    asyncio.run(run())


def test_qualification_keeps_a_later_denial_distinct_from_the_recovered_timeout(tmp_path, monkeypatch):
    async def run():
        responses = deque([{"id": 1, "error": TIMEOUT},
            {"id": 2, "error": {**TIMEOUT, "message": "workspace routing discovery unauthorized (401)"}}])
        async def send(self, message): pass
        async def receive(self): return responses.popleft()
        monkeypatch.setattr(CodexRPC, "send", send)
        monkeypatch.setattr(CodexRPC, "receive", receive)
        report = {}
        rpc = observed_rpc(report)(tmp_path, tmp_path)
        with pytest.raises(RuntimeFailure):
            await rpc.request("account/read", {"refreshToken": False})
        assert report["first_error"]["category"] == "routing_timeout"
        assert report["last_error"]["category"] == "routing_unauthorized"
        assert report["account_read_retries"] == 1
        assert report["failed_request"] == {"method": "account/read", "diagnostic": "rpc_rejected", "account_read_attempts": 2}
    asyncio.run(run())
