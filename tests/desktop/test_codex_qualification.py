import asyncio
import json
import os
from collections import deque
from pathlib import Path

import pytest

from backend.app.codex_runtime import CodexRuntime
from backend.app.codex_usage import require_included_usage
from backend.app.contracts import RuntimeCapabilities, RuntimeEvent
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from backend.app.runtime_policy import QUALIFICATIONS
from scripts.qualify_codex import preflight, live_probes, collect, ProbeRuntime, resolve_profile, observed_rpc
from backend.app.codex_rpc import CodexRPC
from tests.desktop.test_codex import FakeRPC


@pytest.mark.skipif(os.name != "nt", reason="native Windows sandbox policy")
@pytest.mark.parametrize("status", ["notConfigured", "updateRequired", None, "unknown"])
def test_windows_sandbox_not_ready_stops_preflight_and_generation(tmp_path, monkeypatch, status):
    async def run():
        rpc = FakeRPC(); rpc.account = {"type": "chatgpt"}
        request = rpc.request
        async def observed_request(method, params, **kwargs):
            if method == "windowsSandbox/readiness": return {"status": status}
            return await request(method, params, **kwargs)
        rpc.request = observed_request
        async def discovery(self):
            return RuntimeCapabilities(provider="codex", installed=True, version="synthetic", qualification="protocol_only")
        monkeypatch.setattr(AIRuntime, "check", discovery)
        report = await preflight(tmp_path, None, rpc_factory=lambda *args, **kwargs: rpc)
        assert report["blocker"] == "windows_sandbox_setup_required"
        assert not report["generation_requested"] and report["status"] == "blocked"
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *args, **kwargs: rpc)
        with pytest.raises(RuntimeFailure, match="Windows sandbox needs setup"):
            await collect(ProbeRuntime(tmp_path, "synthetic"), "synthetic", tmp_path, None)
        assert rpc.closed
        assert all(method not in ("turn/start", "windowsSandbox/setupStart") for method, _ in rpc.requests)
    asyncio.run(run())


@pytest.mark.parametrize("permission", [None, False, 0, 1, "true"])
def test_included_usage_requires_explicit_permission_even_with_credits_and_percentages(permission):
    with pytest.raises(RuntimeFailure, match="Included subscription usage"):
        require_included_usage({"ordinaryUsageAllowed": permission, "rateLimits": {"credits": {"hasCredits": True, "unlimited": True}, "primary": {"usedPercent": 0}}})


def test_usage_failure_stops_before_inference_and_does_not_expose_account_data(tmp_path, monkeypatch):
    async def run():
        rpc = FakeRPC(); rpc.account = {"type": "chatgpt"}
        original = rpc.request
        async def request(method, params, **kwargs):
            if method == "account/rateLimits/read": return {"ordinaryUsageAllowed": None, "private": "secret-account"}
            return await original(method, params, **kwargs)
        rpc.request = request
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *_, **kwargs: rpc)
        async def qualified(self): return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True, browsing=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified)
        with pytest.raises(RuntimeFailure, match="Included subscription usage") as exc:
            _ = [event async for event in CodexRuntime(tmp_path).stream("example", "run", tmp_path)]
        assert "secret-account" not in str(exc.value) and rpc.closed
        assert not any(method == "turn/start" for method, _ in rpc.requests)
    asyncio.run(run())


@pytest.mark.parametrize("account,quota,blocker", [
    (None, True, "dedicated_subscription_sign_in"),
    ({"type": "apiKey"}, True, "unsupported_authentication"),
    ({"type": "chatgpt"}, None, "included_usage_unconfirmed_or_exhausted"),
    ({"type": "chatgpt"}, False, "included_usage_unconfirmed_or_exhausted"),
    ({"type": "chatgpt"}, True, None),
])
def test_preflight_never_signs_in_generates_or_promotes_qualification(tmp_path, monkeypatch, account, quota, blocker):
    async def run():
        rpc = FakeRPC(); rpc.account = account
        original = rpc.request
        async def request(method, params, **kwargs):
            if method == "account/rateLimits/read": return {"ordinaryUsageAllowed": quota, "accountId": "private-account"}
            return await original(method, params, **kwargs)
        rpc.request = request
        async def discover(self): return RuntimeCapabilities(provider="codex", installed=True, qualification="protocol_only", version="0.158.0-alpha.2.1")
        monkeypatch.setattr(AIRuntime, "check", discover)
        before = dict(QUALIFICATIONS)
        report = await preflight(tmp_path, None, rpc_factory=lambda *_, **kwargs: rpc)
        assert report["blocker"] == blocker and not report["generation_requested"] and not report["live_qualified"]
        assert "private-account" not in str(report) and rpc.closed and QUALIFICATIONS == before
        assert not any(method in ("turn/start", "account/login/start") for method, _ in rpc.requests)
        if blocker:
            assert await live_probes(tmp_path, report) == report
    asyncio.run(run())


def test_probe_refuses_version_change_between_preflight_and_turn(tmp_path, monkeypatch):
    async def discover(self): return RuntimeCapabilities(provider="codex", installed=True, qualification="protocol_only", version="different")
    monkeypatch.setattr(AIRuntime, "check", discover)
    with pytest.raises(RuntimeFailure):
        asyncio.run(ProbeRuntime(tmp_path, "recorded-version").require_generation(allow_browsing=False))


def test_probe_output_limit_closes_stream_before_temporary_workspace_cleanup(tmp_path):
    async def run():
        closed = []
        class Probe:
            async def stream(self, *args, **kwargs):
                try: yield RuntimeEvent(run_id="probe", kind="message.delta", text="x" * 20001)
                finally: closed.append(True)
        with pytest.raises(RuntimeFailure): await collect(Probe(), "synthetic", tmp_path, None)
        assert closed
    asyncio.run(run())


def test_quota_error_in_restricted_probe_stops_instead_of_continuing(tmp_path, monkeypatch):
    async def run():
        async def enforced(profile): return True
        monkeypatch.setattr("scripts.qualify_codex.enforcement_ready", enforced)
        calls = []
        async def collector(runtime, prompt, workspace, model, **kwargs):
            calls.append(Path(workspace).name)
            if calls[-1] == "cached": return "100 [fixture-1]", 0
            if calls[-1] == "source": return '{"url":"https://www.investor.gov/example"}', 1
            raise RuntimeFailure("Included subscription usage is unavailable")
        monkeypatch.setattr("scripts.qualify_codex.collect", collector)
        report = await live_probes(tmp_path, {"status": "preflight_passed", "version": "synthetic", "model": "synthetic", "live_qualified": False})
        assert calls == ["cached", "source", "restricted"]
        assert report["status"] == "blocked" and not report["live_qualified"]
    asyncio.run(run())


def test_qualification_refuses_developer_profile_and_subdirectories(tmp_path, monkeypatch):
    developer = tmp_path / "developer"
    user_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: user_home)
    monkeypatch.setenv("CODEX_HOME", str(developer))
    for profile in (developer, developer / "child", user_home / ".codex", user_home / ".codex" / "child"):
        with pytest.raises(ValueError, match="dedicated"): resolve_profile(str(profile))
    assert resolve_profile(str(tmp_path / "application")) == (tmp_path / "application").resolve()


def test_sign_in_helper_refuses_redirected_device_code_output(monkeypatch, capsys):
    from types import SimpleNamespace
    from scripts import connect_codex
    monkeypatch.setattr(connect_codex.sys, "argv", ["connect_codex"])
    monkeypatch.setattr(connect_codex.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    async def forbidden(*args): pytest.fail("sign-in started in a redirected process")
    monkeypatch.setattr(connect_codex, "connect", forbidden)
    assert connect_codex.main() == 2
    assert "interactive terminal" in capsys.readouterr().out


@pytest.mark.parametrize("failure,reason", [
    (json.JSONDecodeError("private-provider-message", "private-provider-output", 0), "invalid_json"),
    (RuntimeFailure("Codex reported activity outside the permitted research tools."), "prohibited_tool_activity"),
    (RuntimeFailure("private-provider-diagnostic"), "runtime_or_probe_check_failed"),
])
def test_live_failure_records_stage_without_text_or_retry(tmp_path, monkeypatch, failure, reason):
    async def enforced(profile): return True
    monkeypatch.setattr("scripts.qualify_codex.enforcement_ready", enforced)
    calls = []
    async def collector(runtime, prompt, workspace, model, **kwargs):
        calls.append(Path(workspace).name)
        if calls[-1] == "cached": return "100 [fixture-1]", 0
        raise failure
    monkeypatch.setattr("scripts.qualify_codex.collect", collector)
    report = asyncio.run(live_probes(tmp_path, {"status": "preflight_passed", "version": "synthetic", "model": "synthetic", "live_qualified": False}))
    assert calls == ["cached", "source"]
    assert report["stage"] == "source" and report["failure_reason"] == reason
    assert report["status"] == "blocked" and not report["live_qualified"]
    assert "private-provider" not in json.dumps(report)


@pytest.mark.parametrize("failure", [False, RuntimeFailure("private diagnostic")])
def test_enforcement_failure_stops_live_probe_before_any_inference(tmp_path, monkeypatch, failure):
    async def enforced(profile):
        if isinstance(failure, Exception): raise failure
        return failure
    async def forbidden(*args, **kwargs): pytest.fail("inference before enforcement")
    monkeypatch.setattr("scripts.qualify_codex.enforcement_ready", enforced)
    monkeypatch.setattr("scripts.qualify_codex.collect", forbidden)
    report = asyncio.run(live_probes(tmp_path, {"status": "preflight_passed", "live_qualified": False}))
    assert report["blocker"] == "sandbox_enforcement" and not report["generation_requested"]
    assert "private" not in str(report)


def test_live_observations_allow_only_fixed_categories(tmp_path, monkeypatch):
    observations = {}
    payloads = deque([
        {"method": "item/started", "params": {"item": {"type": "agentMessage", "phase": "commentary", "text": "private-provider-text"}, "threadId": "private-thread"}},
        {"method": "item/completed", "params": {"item": {"type": "agentMessage", "phase": "final_answer", "text": "private-provider-text"}}},
        {"method": "item/started", "params": {"item": {"type": {"private": "provider"}}}},
        {"method": "error", "params": {"error": {"codexErrorInfo": "usageLimitExceeded", "message": "private-provider-error"}}},
        {"method": "turn/completed", "params": {"turn": {"status": "failed", "error": {"message": "private-later-error"}}}},
    ])
    async def receive(self): return payloads.popleft()
    monkeypatch.setattr(CodexRPC, "receive", receive)
    rpc = observed_rpc(observations)(tmp_path, tmp_path / "source")
    async def run():
        while payloads: await rpc.receive()
    asyncio.run(run())
    assert observations["source"] == {
        "item_types": ["agentMessage", "other"], "message_phases": ["commentary", "final_answer"],
        "provider_error": "usageLimitExceeded", "turn_started": False, "turn_completed": False,
    }
    assert "private" not in json.dumps(observations)


@pytest.mark.parametrize("installed,version,expected", [
    (False, None, "could not be found or started"),
    (True, None, "version could not be verified"),
    (True, "0.0.1", "0.0.1"),
])
def test_sign_in_distinguishes_missing_unverified_and_unsupported_runtime(tmp_path, monkeypatch, capsys, installed, version, expected):
    from scripts import connect_codex
    async def discover(self):
        return RuntimeCapabilities(provider="codex", installed=installed, version=version)
    def forbidden(*args): pytest.fail("sign-in started without a reviewed runtime")
    monkeypatch.setattr(AIRuntime, "check", discover)
    monkeypatch.setattr(connect_codex, "CodexLogin", forbidden)
    assert asyncio.run(connect_codex.connect(tmp_path)) == 2
    assert expected in capsys.readouterr().out
