import asyncio
import hashlib
from types import SimpleNamespace

import pytest

from scripts import inspect_codex_wsl as probe


def test_requires_explicit_invocation_and_stops_on_other_platforms(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        probe.main([])
    monkeypatch.setattr(probe, "sys", SimpleNamespace(platform="win32"))
    assert probe.main(["--inspect", "--binary", "synthetic"]) == 2
    assert '"status":"wsl2_required"' in capsys.readouterr().out


def test_no_inherited_credentials_bus_windows_path_or_runtime_configuration(monkeypatch, tmp_path):
    for name in ("OPENAI_API_KEY", "CODEX_ACCESS_TOKEN", "CODEX_HOME", "HOME", "PATH",
                 "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR", "NODE_OPTIONS", "CODEX_CA_CERTIFICATE"):
        monkeypatch.setenv(name, "synthetic-private")
    env = probe.inspection_environment(tmp_path)
    assert "synthetic-private" not in env.values()
    assert env["HOME"] == env["CODEX_HOME"] == str(tmp_path)
    assert env["PATH"] == "/usr/bin:/bin"
    assert "DBUS_SESSION_BUS_ADDRESS" not in env


def test_binary_pin_rejects_content_and_size_drift(tmp_path, monkeypatch):
    binary = tmp_path / "codex"
    binary.write_bytes(b"synthetic")
    monkeypatch.setattr(probe, "BINARY_BYTES", 9)
    monkeypatch.setattr(probe, "BINARY_SHA256", hashlib.sha256(b"synthetic").hexdigest())
    assert probe.reviewed_binary(binary) == binary
    for content in (b"different", b"short"):
        binary.write_bytes(content)
        with pytest.raises(probe.InspectionFailure, match="runtime_drift"):
            probe.reviewed_binary(binary)


def stream(value):
    result = asyncio.StreamReader()
    result.feed_data(value)
    result.feed_eof()
    return result


@pytest.mark.parametrize("mode", ["normal", "exit", "version", "help", "flood", "timeout", "credential"])
def test_bounded_scope_output_and_owned_cleanup(tmp_path, monkeypatch, mode):
    closed = []
    class Process:
        async def wait(self):
            if mode == "timeout":
                await asyncio.Event().wait()
            return 1 if mode == "exit" else 0
    async def launch(*args, **kwargs):
        assert args == ("synthetic", "--help" if mode == "help" else "--version")
        assert kwargs["cwd"] == tmp_path
        assert kwargs["stdin"] == asyncio.subprocess.DEVNULL
        assert kwargs["env"] == probe.inspection_environment(tmp_path)
        process = Process()
        process.stdout = stream(b"x" * (probe.OUTPUT_LIMIT + 1) if mode == "flood" else
                                b"private-wrong" if mode in ("version", "help") else
                                ("codex-cli " + probe.VERSION + "\n").encode())
        process.stderr = stream(b"")
        if mode == "credential":
            (tmp_path / "auth.json").write_text("synthetic")
        return process
    async def close(process): closed.append(process)
    monkeypatch.setattr(probe, "launch_owned", launch)
    monkeypatch.setattr(probe, "close_owned", close)
    monkeypatch.setattr(probe, "DEADLINE_SECONDS", 0.02 if mode == "timeout" else 1)
    action = probe.inspect_command("synthetic", "--help" if mode == "help" else "--version", tmp_path)
    if mode == "normal":
        assert asyncio.run(action)["stdout_bytes"] > 0
    else:
        with pytest.raises((probe.InspectionFailure, asyncio.TimeoutError)) as error:
            asyncio.run(action)
        assert "private-wrong" not in str(error.value)
    assert len(closed) == 1


def test_out_of_scope_command_never_launches(tmp_path):
    with pytest.raises(probe.InspectionFailure, match="command_out_of_scope"):
        asyncio.run(probe.inspect_command("synthetic", "login", tmp_path))


def test_success_remains_unqualified_and_profiles_are_removed(monkeypatch):
    profiles = []
    monkeypatch.setattr(probe, "reviewed_binary", lambda path: path)
    async def command(binary, flag, profile):
        profiles.append(profile)
        return {"stdout_bytes": 1, "stderr_bytes": 0, "stdout_sha256": "synthetic"}
    monkeypatch.setattr(probe, "inspect_command", command)
    report = asyncio.run(probe.inspect("synthetic"))
    assert len(profiles) == 2 and all(not path.exists() for path in profiles)
    for key in ("authentication_requested", "inference_requested", "credential_isolation_qualified",
                "sandbox_qualified", "generation_qualified"):
        assert report[key] is False
