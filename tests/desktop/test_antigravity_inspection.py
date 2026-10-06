import asyncio
import hashlib
from pathlib import Path

import pytest

from scripts import inspect_antigravity as probe


def test_probe_requires_explicit_invocation():
    with pytest.raises(SystemExit) as result:
        probe.main([])
    assert result.value.code == 2


def test_environment_discards_inherited_accounts_hooks_billing_and_profiles(monkeypatch, tmp_path):
    for name in ("AGY_ACCOUNT", "AGY_ADC_AUTH", "ANTIGRAVITY_APP_DATA_DIR", "AGY_LLM_GATEWAY_API_KEY",
                 "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT",
                 "NODE_OPTIONS", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"):
        monkeypatch.setenv(name, "synthetic-private")
    env = probe.inspection_environment(tmp_path)
    assert "synthetic-private" not in env.values()
    assert env["AGY_CLI_DISABLE_AUTO_UPDATE"] == "true"
    assert all(env[name] == str(tmp_path) for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"))


def test_runtime_pin_rejects_size_and_same_size_content_drift(monkeypatch, tmp_path):
    path = tmp_path / "synthetic.exe"
    path.write_bytes(b"synthetic")
    monkeypatch.setattr(probe, "BINARY_BYTES", 9)
    monkeypatch.setattr(probe, "BINARY_SHA512", hashlib.sha512(b"synthetic").hexdigest())
    assert probe.reviewed_binary(path) == path
    for content in (b"changed", b"different"):
        path.write_bytes(content)
        with pytest.raises(probe.InspectionFailure, match="runtime_drift"):
            probe.reviewed_binary(path)


def stream(data):
    value = asyncio.StreamReader()
    value.feed_data(data)
    value.feed_eof()
    return value


@pytest.mark.parametrize("mode", ["normal", "extra_diagnostics", "changed_help", "flood", "exit", "timeout"])
def test_bounded_command_output_and_owned_cleanup(monkeypatch, tmp_path, mode):
    closed, commands = [], []
    help_text = b"Synthetic public help\n"
    monkeypatch.setattr(probe, "HELP_SHA256", hashlib.sha256(help_text).hexdigest())
    if mode == "timeout":
        monkeypatch.setattr(probe, "DEADLINE_SECONDS", 0.03)
    class Process:
        async def wait(self):
            if mode == "timeout":
                await asyncio.Event().wait()
            return 1 if mode == "exit" else 0
    async def launch(*args, **kwargs):
        commands.append(args)
        assert args == ("synthetic.exe", "--help")
        assert kwargs["cwd"] == tmp_path and kwargs["stdin"] == asyncio.subprocess.DEVNULL
        process = Process()
        process.stdout = stream(b"synthetic-private" if mode == "extra_diagnostics" else b"")
        process.stderr = stream(b"x" * (probe.OUTPUT_LIMIT + 1) if mode == "flood"
                                else b"different" if mode == "changed_help" else help_text)
        return process
    async def close(process):
        closed.append(process)
    monkeypatch.setattr(probe, "launch_owned", launch)
    monkeypatch.setattr(probe, "close_owned", close)
    if mode == "normal":
        asyncio.run(probe.inspect_command(Path("synthetic.exe"), "--help", tmp_path))
    else:
        with pytest.raises((probe.InspectionFailure, TimeoutError)):
            asyncio.run(probe.inspect_command(Path("synthetic.exe"), "--help", tmp_path))
    assert len(commands) == len(closed) == 1


def test_login_generation_and_update_cannot_reach_child(monkeypatch, tmp_path):
    async def forbidden(*args, **kwargs):
        pytest.fail("Out-of-scope process launch")
    monkeypatch.setattr(probe, "launch_owned", forbidden)
    for flag in ("--print", "--login", "install", "update", "models", "--dangerously-skip-permissions"):
        with pytest.raises(probe.InspectionFailure, match="command_out_of_scope"):
            asyncio.run(probe.inspect_command(Path("synthetic.exe"), flag, tmp_path))


@pytest.mark.parametrize("write", [False, True])
def test_profile_cleanup_and_unqualified_report(monkeypatch, write):
    profiles, flags, checks = [], [], []
    monkeypatch.setattr(probe, "reviewed_binary", lambda path: checks.append(path))
    async def command(executable, flag, profile):
        flags.append(flag)
        profiles.append(profile)
        if write:
            (profile / "synthetic-unexpected-file").write_text("synthetic")
    monkeypatch.setattr(probe, "inspect_command", command)
    if write:
        with pytest.raises(probe.InspectionFailure, match="unexpected_profile_write"):
            asyncio.run(probe.inspect(Path("synthetic.exe")))
    else:
        report = asyncio.run(probe.inspect(Path("synthetic.exe")))
        assert report["status"] == "prerequisites_verified" and report["version"] == "1.3.0"
        assert all(value is False for key, value in report.items() if key not in ("status", "version"))
        assert flags == ["--version", "--help"] and len(checks) == 3
    assert all(not profile.exists() for profile in profiles)
