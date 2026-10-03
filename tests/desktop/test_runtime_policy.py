"""Installation and authentication cannot self-certify subscription capabilities."""
import asyncio
from types import SimpleNamespace

import pytest

from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import AIRuntime, RuntimeFailure, runtime_version
from backend.app.runtime_policy import QUALIFICATIONS, Qualification, apply_qualification
from backend.app.runtimes import CLIRuntime


@pytest.mark.parametrize("provider,raw,expected", [
    ("codex", b"codex-cli 0.158.0-alpha.2.1\n", "0.158.0-alpha.2.1"),
    ("codex", b"codex-cli 1.2.3+build.4\n", "1.2.3+build.4"),
    ("gemini", b"0.37.1\n", "0.37.1"),
    ("claude", b"2.1.0 (Claude Code)\n", "2.1.0"),
    ("codex", b"debug secret 1.2.3\n", None),
    ("codex", b"codex-cli 1.2.3\nprivate diagnostic", None),
    ("codex", b"codex-cli 1.2.3trailing", None),
    ("codex", b"\xff", None),
])
def test_exact_version_identity_and_untrusted_output(provider, raw, expected):
    assert runtime_version(provider, raw) == expected


def test_capabilities_default_to_disabled_and_unknown_versions_stay_disabled():
    result = RuntimeCapabilities(provider="codex", installed=True, version="999.1.0", authentication="authenticated", generation=True, approvals=True)
    result = apply_qualification(result)
    assert result.qualification == "unqualified"
    assert not any(getattr(result, name) for name in ("generation", "browsing", "streaming", "cancellation", "approvals"))
    defaults = RuntimeCapabilities(provider="claude")
    assert not defaults.streaming and not defaults.cancellation


@pytest.mark.parametrize("authentication", ["unknown", "required", "unsupported", "authenticated"])
def test_protocol_only_never_enables_inference_even_after_sign_in(authentication):
    result = apply_qualification(RuntimeCapabilities(provider="codex", installed=True, version="0.158.0-alpha.2.1", authentication=authentication))
    assert result.qualification == "protocol_only"
    assert not result.generation and not result.browsing and not result.approvals
    # A stable release is not equivalent to the tested prerelease.
    assert apply_qualification(RuntimeCapabilities(provider="codex", installed=True, version="0.158.0")).qualification == "unqualified"


def test_reviewed_capabilities_require_authentication_and_do_not_expand(monkeypatch):
    monkeypatch.setitem(QUALIFICATIONS, ("codex", "1.2.3-test"), Qualification(live=True, generation=True, streaming=True))
    result = RuntimeCapabilities(provider="codex", installed=True, version="1.2.3-test")
    assert not apply_qualification(result).generation
    result.authentication = "authenticated"
    apply_qualification(result)
    assert result.generation and result.streaming
    assert not result.browsing and not result.cancellation and not result.approvals


class VersionProcess:
    def __init__(self, output, exit_code=0):
        self.stdout = asyncio.StreamReader()
        self.stdout.feed_data(output)
        self.stdout.feed_eof()
        self.returncode = None
        self.exit_code = exit_code
        self.killed = False

    async def wait(self):
        if self.returncode is None:
            self.returncode = self.exit_code
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


@pytest.mark.parametrize("output,exit_code", [
    (b"codex-cli 0.158.0-alpha.2.1\n", 0),
    (b"codex-cli 0.158.0-alpha.2.1\n", 1),
    (b"private-secret diagnostic", 0),
    (b"private-secret" * 1000, 0),
])
def test_version_process_is_bounded_and_never_exposes_diagnostics(tmp_path, monkeypatch, output, exit_code):
    async def run():
        process = VersionProcess(output, exit_code)
        calls = []
        async def spawn(*args, **kwargs):
            calls.append(args)
            return process
        monkeypatch.setattr("backend.app.runtime_base.executable_command", lambda _: ["codex.exe"])
        monkeypatch.setattr("backend.app.runtime_base.asyncio.create_subprocess_exec", spawn)
        result = await CodexRuntime().check()
        assert result.installed and not result.generation and not result.approvals
        assert calls == [("codex.exe", "--version")]
        assert "private-secret" not in result.model_dump_json()
        if len(output) > 4096:
            assert process.killed
        if exit_code:
            assert result.version is None
    asyncio.run(run())


def test_known_codex_authentication_is_reported_without_qualification(tmp_path, monkeypatch):
    async def run():
        async def discover(_):
            return apply_qualification(RuntimeCapabilities(provider="codex", installed=True, version="0.158.0-alpha.2.1"))
        calls = []
        async def request(method, params):
            calls.append(method)
            return {"account": {"type": "chatgpt", "email": "private@example.test"}}
        async def noop(): pass
        def factory(*args, **kwargs):
            assert kwargs["allow_browsing"] is False
            return SimpleNamespace(open=noop, close=noop, request=request)
        monkeypatch.setattr(AIRuntime, "check", discover)
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", factory)
        result = await CodexRuntime(tmp_path).check()
        assert result.authentication == "authenticated" and result.qualification == "protocol_only"
        assert not result.generation and not result.approvals
        assert calls == ["account/read"] and "private@example" not in result.model_dump_json()
    asyncio.run(run())


@pytest.mark.parametrize("provider", ["codex", "gemini", "claude"])
def test_unqualified_stream_never_starts_provider_inference(tmp_path, monkeypatch, provider):
    async def run():
        async def discover(_):
            return RuntimeCapabilities(provider=provider, installed=True, version="999.0.0", reason="Unqualified version")
        monkeypatch.setattr(AIRuntime, "check", discover)
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *a, **k: pytest.fail("No unsupported protocol launch"))
        monkeypatch.setattr("backend.app.runtimes.executable_command", lambda *a: pytest.fail("No inference command"))
        runtime = CodexRuntime(tmp_path) if provider == "codex" else CLIRuntime(provider)
        with pytest.raises(RuntimeFailure, match="Unqualified"):
            _ = [event async for event in runtime.stream("prompt", "run", tmp_path)]
    asyncio.run(run())


def test_cached_only_qualification_cannot_browse(tmp_path, monkeypatch):
    async def run():
        async def qualified(_):
            return RuntimeCapabilities(provider="codex", installed=True, authentication="authenticated", qualification="live", generation=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified)
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *a, **k: pytest.fail("Browsing must be rejected first"))
        with pytest.raises(RuntimeFailure, match="cached/imported"):
            _ = [event async for event in CodexRuntime(tmp_path).stream("prompt", "run", tmp_path)]
    asyncio.run(run())
