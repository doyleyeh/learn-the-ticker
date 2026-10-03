import asyncio
from pathlib import Path

import pytest

from backend.app.codex_runtime import CodexRuntime
from backend.app.codex_usage import require_included_usage
from backend.app.contracts import RuntimeCapabilities, RuntimeEvent
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from backend.app.runtime_policy import QUALIFICATIONS
from scripts.qualify_codex import preflight, live_probes, collect, ProbeRuntime, resolve_profile
from tests.desktop.test_codex import FakeRPC


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
