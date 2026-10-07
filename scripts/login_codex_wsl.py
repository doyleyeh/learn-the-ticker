"""Interactive developer sign-in to a separate encrypted WSL Codex keyring.

Run in a real terminal. Never pass passwords as arguments, environment values
or chat messages. This helper does not request inference or qualify production.
"""
import argparse
import asyncio
from contextlib import contextmanager
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from unittest.mock import patch
from urllib.parse import unquote

from backend.app.codex_login import CodexLogin
from backend.app.codex_rpc import CodexRPC
from backend.app.owned_process import close_owned, launch_owned
from scripts.inspect_codex_wsl import InspectionFailure, reviewed_binary
from scripts.probe_codex_wsl_boundaries import command, environment, require, start_keyring


MARKER = "Learn the Ticker WSL qualification credentials v1\n"


def prepare_root(root, home):
    root, home = root.absolute(), home.resolve()
    require(root.is_relative_to(home / ".local/share/learn-the-ticker") and root != home, "app_owned_linux_root_required")
    require(not any(p.is_symlink() for p in (root, *root.parents)), "linked_credential_root_rejected")
    require(not any((p / ".git").exists() for p in (root, *root.parents)), "credentials_outside_git_required")
    if root.exists():
        require(root.is_dir() and root.stat().st_uid == os.getuid() and root.stat().st_mode & 0o077 == 0,
                "private_credential_root_required")
        marker = root / ".ltt-wsl-credentials"
        require(marker.is_file() and not marker.is_symlink() and marker.stat().st_size == len(MARKER.encode())
                and marker.read_text() == MARKER, "credential_root_marker_required")
    else:
        root.mkdir(parents=True, mode=0o700)
        (root / ".ltt-wsl-credentials").write_text(MARKER)
    for name in ("config", "data", "cache", "codex"):
        target = root / name
        require(not target.is_symlink(), "linked_credential_directory_rejected")
        target.mkdir(mode=0o700, exist_ok=True)
        require(target.stat().st_uid == os.getuid() and target.stat().st_mode & 0o077 == 0, "private_credential_directory_required")
    require(not any(p.is_symlink() for p in root.rglob("*")), "linked_credential_content_rejected")
    require(not list(root.rglob("auth.json")), "file_credentials_rejected")
    return root


@contextmanager
def exclusive_session(root):
    import fcntl
    path = root / "session.lock"
    require(not path.is_symlink(), "linked_session_lock_rejected")
    with path.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def interactive_password(root):
    require(sys.stdin.isatty() and sys.stderr.isatty(), "interactive_terminal_required")
    password = getpass.getpass("Local encrypted keyring password (never sent to OpenAI): ")
    require(bool(password), "empty_password_rejected")
    if not list((root / "data/keyrings").glob("*.keyring")):
        require(password == getpass.getpass("Confirm new keyring password: "), "password_confirmation_failed")
    return password.encode()


def login_factory(binary, env):
    class PrivateSessionRPC(CodexRPC):
        async def open(self):
            # Developer-only dependency injection. Keep the production transport,
            # effective configuration and event guards; supply only this owned
            # session's environment and exact reviewed Linux binary.
            with patch("backend.app.codex_rpc.provider_environment", return_value=env.copy()), \
                    patch("backend.app.codex_rpc.executable_command", return_value=[str(binary)]):
                await super().open()
    return PrivateSessionRPC


async def wait_for_enter():
    loop = asyncio.get_running_loop()
    done = loop.create_future()
    def readable():
        sys.stdin.readline()
        if not done.done(): done.set_result(None)
    loop.add_reader(sys.stdin.fileno(), readable)
    try:
        await done
    finally:
        loop.remove_reader(sys.stdin.fileno())


async def session(binary, root, password):
    bus = keyring = login = None
    manifest = root / "session.json"
    require(not manifest.is_symlink(), "linked_session_manifest_rejected")
    with tempfile.TemporaryDirectory(prefix="ltt-wsl-session-") as directory:
        runtime = Path(directory)
        (runtime / "run/keyring").mkdir(parents=True, mode=0o700)
        (runtime / "tmp").mkdir(mode=0o700)
        env = environment(root)
        env.update(CODEX_HOME=str(root / "codex"), XDG_RUNTIME_DIR=str(runtime / "run"), TMPDIR=str(runtime / "tmp"))
        try:
            bus = await launch_owned("/usr/bin/dbus-daemon", "--session", "--nofork", "--print-address=1",
                                     "--address=unix:path=" + str(runtime / "run/bus"), env=env, cwd=root,
                                     stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                                     stderr=asyncio.subprocess.DEVNULL)
            address = (await asyncio.wait_for(bus.stdout.readline(), 3)).decode().strip()
            require(address.startswith("unix:path=") and unquote(address.split(",", 1)[0][10:]) == str(runtime / "run/bus"),
                    "private_bus_address_rejected")
            env["DBUS_SESSION_BUS_ADDRESS"] = address
            keyring = await start_keyring(runtime, env, password)
            password = b""
            # Test unlock/storage before starting any provider authorization.
            canary = secrets.token_urlsafe(32).encode()
            key = secrets.token_hex(12)
            attrs = ["service", "LearnTheTicker.WSLUnlockProbe", "scope", key]
            code, _ = await command(["/usr/bin/secret-tool", "store", "--label=LTT synthetic unlock check", *attrs], env, root, canary)
            require(code == 0, "keyring_unlock_failed")
            code, value = await command(["/usr/bin/secret-tool", "lookup", *attrs], env, root)
            require(code == 0 and value.strip() == canary, "keyring_unlock_failed")
            code, _ = await command(["/usr/bin/secret-tool", "clear", *attrs], env, root)
            require(code == 0, "keyring_canary_cleanup_failed")
            reviewed_binary(binary)
            login = CodexLogin(root / "codex", rpc_factory=login_factory(binary, env))
            state = await login.start()
            if state.status == "pending":
                # The validated official URL and ephemeral code are displayed
                # only in this interactive terminal, never written to a report.
                print(state.verification_url, flush=True)
                print("Device code: " + state.user_code, flush=True)
                await login.task
                state = login.snapshot()
            require(state.status == "authenticated", "subscription_sign_in_incomplete")
            require(not list(root.rglob("auth.json")), "unexpected_file_credentials")
            reviewed_binary(binary)
            # Local session coordinates only; no passwords, codes or tokens.
            manifest.write_text(json.dumps({"pid": os.getpid(), "binary": str(binary), "environment": env}))
            manifest.chmod(0o600)
            print("Dedicated WSL ChatGPT sign-in connected. No inference or billing was requested.", flush=True)
            print("Keep this terminal open for qualification. Press Enter to close the private credential session.", flush=True)
            await wait_for_enter()
        finally:
            try:
                if login: await login.close()
            finally:
                try:
                    await close_owned(keyring)
                finally:
                    await close_owned(bus)
                    manifest.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", action="store_true", required=True)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(sys.platform == "linux" and "microsoft-standard-wsl2" in os.uname().release.lower(), "wsl2_required")
        require(sys.stdin.isatty() and sys.stderr.isatty(), "interactive_terminal_required")
        reviewed_binary(args.binary)
        old_umask = os.umask(0o077)
        try:
            root = prepare_root(Path.home() / ".local/share/learn-the-ticker/wsl-codex-credentials", Path.home())
            with exclusive_session(root):
                password = interactive_password(root)
                asyncio.run(session(args.binary, root, password))
        finally:
            os.umask(old_umask)
        return 0
    except InspectionFailure as exc:
        print("Stopped: " + str(exc), file=sys.stderr)
    except (Exception, KeyboardInterrupt):
        print("Stopped: WSL credential session unavailable or cancelled. No fallback was attempted.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
