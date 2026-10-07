import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import login_codex_wsl as login


def test_no_password_or_account_flow_without_interactive_terminal(monkeypatch, tmp_path):
    monkeypatch.setattr(login.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(login.getpass, "getpass", lambda *args: pytest.fail("must not ask for password"))
    with pytest.raises(login.InspectionFailure, match="interactive_terminal_required"):
        login.interactive_password(tmp_path)


@pytest.mark.parametrize("values,reason", [([""], "empty_password_rejected"), (["synthetic-a", "synthetic-b"], "password_confirmation_failed")])
def test_invalid_new_password_stops_before_session(monkeypatch, tmp_path, values, reason):
    monkeypatch.setattr(login.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(login.sys.stderr, "isatty", lambda: True)
    values = iter(values)
    monkeypatch.setattr(login.getpass, "getpass", lambda *args: next(values))
    with pytest.raises(login.InspectionFailure, match=reason):
        login.interactive_password(tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="Linux ownership and permission semantics")
def test_private_persistent_root_rejects_unowned_or_linked_state(tmp_path):
    root = tmp_path / ".local/share/learn-the-ticker/credentials"
    assert login.prepare_root(root, tmp_path) == root
    assert root.stat().st_mode & 0o077 == 0
    assert login.prepare_root(root, tmp_path) == root
    (root / "data/keyrings").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(login.InspectionFailure, match="linked_credential_content_rejected"):
        login.prepare_root(root, tmp_path)
    assert tmp_path.exists()


@pytest.mark.skipif(os.name != "posix", reason="Linux ownership and permission semantics")
def test_credentials_cannot_be_created_inside_git_or_reuse_unmarked_root(tmp_path, monkeypatch):
    root = tmp_path / ".local/share/learn-the-ticker/credentials"
    (tmp_path / ".git").mkdir()
    with pytest.raises(login.InspectionFailure, match="credentials_outside_git_required"):
        login.prepare_root(root, tmp_path)
    assert not root.exists()
    (tmp_path / ".git").rmdir()
    root.mkdir(parents=True, mode=0o700)
    (root / "preserved").write_text("synthetic")
    with pytest.raises(login.InspectionFailure, match="credential_root_marker_required"):
        login.prepare_root(root, tmp_path)
    assert (root / "preserved").read_text() == "synthetic"
    (root / ".ltt-wsl-credentials").write_text("x" * 8192)
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: pytest.fail("oversized marker must not be read"))
    with pytest.raises(login.InspectionFailure, match="credential_root_marker_required"):
        login.prepare_root(root, tmp_path)


def test_private_rpc_injection_restores_default_production_dependencies(monkeypatch, tmp_path):
    from backend.app import codex_rpc
    original_env, original_command = codex_rpc.provider_environment, codex_rpc.executable_command
    env = {"HOME": "synthetic-owned", "DBUS_SESSION_BUS_ADDRESS": "synthetic-private-bus"}
    async def open_rpc(self):
        assert codex_rpc.provider_environment() == env
        assert codex_rpc.executable_command("codex") == ["synthetic-reviewed"]
    monkeypatch.setattr(codex_rpc.CodexRPC, "open", open_rpc)
    rpc = login.login_factory("synthetic-reviewed", env)(tmp_path, tmp_path)
    asyncio.run(rpc.open())
    assert codex_rpc.provider_environment is original_env and codex_rpc.executable_command is original_command


@pytest.mark.parametrize("failure", ["store", "lookup", "clear", "none"])
def test_unlock_must_pass_before_auth_and_session_coordinates_have_no_secrets(monkeypatch, tmp_path, failure):
    created, closed, canaries, provider_calls = [], [], [], []
    class Bus:
        def __init__(self, address): self.stdout = self; self.address = address
        async def readline(self): return self.address.encode()
    async def launch(*args, **kwargs):
        assert "DBUS_SESSION_BUS_ADDRESS" not in kwargs["env"]
        address = next(arg.removeprefix("--address=") for arg in args if arg.startswith("--address="))
        bus = Bus(address)
        created.append(bus)
        return bus
    async def keyring(*args):
        daemon = object()
        created.append(daemon)
        return daemon
    async def command(args, env, root, data=None, **kwargs):
        if args[1] == "store":
            canaries.append(data)
            return (1 if failure == "store" else 0), b""
        if args[1] == "lookup": return 0, b"wrong" if failure == "lookup" else canaries[0]
        if args[1] == "clear": return (1 if failure == "clear" else 0), b""
        pytest.fail("unexpected operation")
    async def close(process):
        if process: closed.append(process)
    class FakeLogin:
        def __init__(self, profile, **kwargs): provider_calls.append(profile)
        async def start(self): return SimpleNamespace(status="authenticated")
        async def close(self): pass
    async def enter():
        text = (tmp_path / "session.json").read_text()
        assert "synthetic-private-password" not in text and canaries[0].decode() not in text
        result = json.loads(text)
        assert set(result) == {"pid", "binary", "environment"}
        assert result["environment"]["CODEX_HOME"] == str(tmp_path / "codex")
    monkeypatch.setattr(login, "launch_owned", launch)
    monkeypatch.setattr(login, "start_keyring", keyring)
    monkeypatch.setattr(login, "command", command)
    monkeypatch.setattr(login, "close_owned", close)
    monkeypatch.setattr(login, "CodexLogin", FakeLogin)
    monkeypatch.setattr(login, "reviewed_binary", lambda binary: binary)
    monkeypatch.setattr(login, "wait_for_enter", enter)
    action = login.session(Path("synthetic"), tmp_path, b"synthetic-private-password")
    if failure == "none": asyncio.run(action)
    else:
        with pytest.raises(login.InspectionFailure): asyncio.run(action)
        assert not provider_calls
    assert len(created) == len(closed) == 2
    assert not (tmp_path / "session.json").exists()
