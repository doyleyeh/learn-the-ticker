"""Owned-process lifecycle helpers. Never discover or terminate unrelated processes."""
from __future__ import annotations

import os
import secrets
import socket
import subprocess
import tempfile
from pathlib import Path

import keyring
from sqlalchemy import URL, create_engine, text


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class InstanceLock:
    def __init__(self, root: Path):
        self.file = (root / "instance.lock").open("a+b")
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError("This library is already open in another application instance") from None

    def close(self):
        self.file.close()


class PrivatePostgres:
    def __init__(self, root: Path, binaries: Path):
        self.root, self.binaries = root.resolve(), binaries.resolve()
        self.data = self.root / "database" / "data"
        self.started = False
        self.port = 0
        self.password = ""

    def run(self, tool: str, *args, env=None):
        binary = self.binaries / (tool + (".exe" if os.name == "nt" else ""))
        if not binary.is_file():
            raise RuntimeError("PostgreSQL runtime is missing. Set LTT_PG_BIN for the developer preview.")
        # pg_ctl's background server can inherit pipe handles on Windows. File-backed
        # diagnostics and DEVNULL stdin prevent communicate() waiting on descendants.
        with (self.root / "postgres-tools.log").open("ab") as diagnostics:
            result = subprocess.run([str(binary), *map(str, args)], env=env, stdin=subprocess.DEVNULL, stdout=diagnostics, stderr=diagnostics, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode:
            raise RuntimeError(f"Private PostgreSQL {tool} failed; inspect local database diagnostics")
        return result

    def start(self):
        account = str(self.root)
        self.password = keyring.get_password("LearnTheTicker.PostgreSQL", account) or ""
        existing = (self.data / "PG_VERSION").exists()
        if existing and not self.password:
            raise RuntimeError("Database credential is unavailable in the OS credential store. Restore to a new library; do not reinitialize existing data.")
        if not self.password:
            self.password = secrets.token_urlsafe(32)
            keyring.set_password("LearnTheTicker.PostgreSQL", account, self.password)
        if not existing:
            self.data.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=self.root, delete=False, encoding="utf-8") as file:
                file.write(self.password)
                password_file = Path(file.name)
            try:
                os.chmod(password_file, 0o600)
                self.run("initdb", "-D", self.data, "-U", "ltt", "--auth=scram-sha-256", "--encoding=UTF8", "--pwfile", password_file)
            finally:
                password_file.unlink(missing_ok=True)
        if existing and self.recover_running_cluster():
            return
        for _ in range(3):
            self.port = free_port()
            try:
                self.run("pg_ctl", "-D", self.data, "-l", self.root / "postgres.log", "-o", f"-h 127.0.0.1 -p {self.port}", "-w", "start")
                self.started = True
                break
            except RuntimeError:
                # Existing PID belongs to this data directory; never delete it or kill its process.
                if (self.data / "postmaster.pid").exists():
                    raise RuntimeError("Private cluster may already be running; recover it before retrying") from None
        if not self.started:
            raise RuntimeError("Private PostgreSQL could not start after three attempts")
        self.verify_owned_cluster()

    def verify_owned_cluster(self):
        engine = create_engine(self.url(), connect_args={"connect_timeout": 3})
        try:
            with engine.connect() as connection:
                directory = connection.execute(text("SHOW data_directory")).scalar_one()
                address = connection.execute(text("SHOW listen_addresses")).scalar_one()
                if Path(directory).resolve() != self.data.resolve() or address != "127.0.0.1":
                    raise RuntimeError("Database does not match this private loopback cluster")
        finally:
            engine.dispose()

    def recover_running_cluster(self) -> bool:
        # After a supervisor crash the private server may remain alive. Reattach only
        # after password authentication and checking the server's actual data directory.
        # Stale PID files are left for PostgreSQL to handle; never unlink them ourselves.
        pid_file = self.data / "postmaster.pid"
        if not pid_file.exists():
            return False
        try:
            lines = pid_file.read_text(encoding="utf-8").splitlines()
            if len(lines) < 4 or Path(lines[1]).resolve() != self.data.resolve():
                raise RuntimeError("Private PostgreSQL PID metadata does not match the library")
            port = int(lines[3])
            if not 1 <= port <= 65535:
                return False
            self.port = port
            self.verify_owned_cluster()
        except (OSError, ValueError):
            return False
        except RuntimeError:
            raise
        except Exception:
            # Connection failure may mean a stale PID; pg_ctl decides whether startup is safe.
            return False
        self.started = True
        return True

    def url(self) -> str:
        return URL.create("postgresql+psycopg", username="ltt", password=self.password, host="127.0.0.1", port=self.port, database="postgres").render_as_string(hide_password=False)

    def stop(self):
        if self.started:
            self.run("pg_ctl", "-D", self.data, "-w", "-m", "fast", "stop")
            self.started = False
