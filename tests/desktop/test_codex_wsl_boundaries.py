import asyncio
import errno
import json
import socket
import sys
from types import SimpleNamespace

import pytest

from scripts import probe_codex_wsl_boundaries as probe


def test_explicit_wsl_only_invocation(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit):
        probe.main([])
    monkeypatch.setattr(probe, "sys", SimpleNamespace(platform="win32"))
    assert probe.main(["--probe", "--binary", "synthetic", "--workspace-parent", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out) == {"status": "wsl2_required", "production_qualified": False}


def test_environment_never_inherits_accounts_bus_or_executables(monkeypatch, tmp_path):
    for name in ("DBUS_SESSION_BUS_ADDRESS", "HOME", "CODEX_HOME", "XDG_RUNTIME_DIR", "PATH",
                 "OPENAI_API_KEY", "NODE_OPTIONS", "DISPLAY", "WAYLAND_DISPLAY"):
        monkeypatch.setenv(name, "synthetic-private")
    env = probe.environment(tmp_path)
    assert "synthetic-private" not in env.values()
    assert "DBUS_SESSION_BUS_ADDRESS" not in env
    assert env["PATH"] == "/usr/bin:/bin"
    assert env["CODEX_HOME"] != env["HOME"]
    assert env["TMPDIR"] != env["CODEX_HOME"]
    assert probe.credential_key(tmp_path / "a") != probe.credential_key(tmp_path / "b")


@pytest.mark.parametrize("error,denied", [(errno.EACCES, True), (errno.EPERM, True), (errno.EINVAL, False)])
def test_network_canary_handles_denial_at_socket_creation(monkeypatch, capsys, error, denied):
    def denied_socket(*args): raise OSError(error, "synthetic-private")
    monkeypatch.setattr(socket, "socket", denied_socket)
    monkeypatch.setattr(sys, "argv", ["probe", "127.0.0.1", "12345", "tcp"])
    exec(probe.NETWORK_CHECK, {})
    assert json.loads(capsys.readouterr().out) == {"blocked": denied}


@pytest.mark.parametrize("mode", ["pass", "file_allowed", "credential_file"])
def test_partial_failures_never_promote_and_always_remove_owned_workspace(monkeypatch, tmp_path, mode):
    roots, pins = [], []
    monkeypatch.setattr(probe, "reviewed_binary", lambda binary: pins.append(binary))
    async def keyring(binary, root):
        roots.append(root)
        if mode == "credential_file": (root / "auth.json").write_text("synthetic")
        return {"synthetic_roundtrip": True}
    async def sandbox(binary, root, script, args):
        assert script == probe.FILE_CHECK
        return {"read": True, "denied": mode != "file_allowed"}
    async def network(*args): return {"denied": True}
    monkeypatch.setattr(probe, "keyring_probe", keyring)
    monkeypatch.setattr(probe, "sandbox_command", sandbox)
    monkeypatch.setattr(probe, "network_probe", network)
    result = asyncio.run(probe.probe("synthetic", tmp_path))
    assert result["status"] == {"pass": "boundaries_verified_review_required", "file_allowed": "sandbox_write_not_blocked",
                                "credential_file": "unexpected_file_credentials"}[mode]
    assert result["production_qualified"] is False
    assert result["authentication_requested"] is result["inference_requested"] is False
    assert result["disposable_workspace_removed"] is True
    assert all(not root.exists() for root in roots) and len(pins) == 2


@pytest.mark.parametrize("udp", [False, True])
def test_network_listener_detects_a_false_denial_report(monkeypatch, tmp_path, udp):
    async def sandbox(binary, root, script, args):
        address, port, _ = args
        if udp:
            loop = asyncio.get_running_loop()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.setblocking(False)
                await loop.sock_sendto(client, b"probe", (address, int(port)))
                await asyncio.wait_for(loop.sock_recvfrom(client, 32), 2)
        else:
            _, writer = await asyncio.open_connection(address, int(port))
            writer.close()
            await writer.wait_closed()
        return {"blocked": True}
    monkeypatch.setattr(probe, "sandbox_command", sandbox)
    with pytest.raises(probe.InspectionFailure, match="sandbox_network_not_blocked"):
        asyncio.run(probe.network_probe("synthetic", tmp_path, "127.0.0.1", udp))


def test_sandbox_nonzero_exit_is_not_a_successful_denial(monkeypatch, tmp_path):
    async def failed(*args, **kwargs): return 1, b'synthetic-private'
    monkeypatch.setattr(probe, "command", failed)
    with pytest.raises(probe.InspectionFailure, match="^sandbox_command_failed$"):
        asyncio.run(probe.sandbox_command("synthetic", tmp_path, probe.FILE_CHECK, []))
