from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from sqlalchemy import inspect, text

from backend.app.api import create_app
from backend.app.db import Database
from backend.app.lifecycle import InstanceLock, PrivatePostgres
from backend.app.migrate import migrate


def main():
    # The native host supplies secrets over stdin, never command arguments or logs.
    config = json.loads(sys.stdin.readline())
    token = config["token"]
    if not isinstance(token, str) or len(token) < 32:
        raise RuntimeError("Invalid native bootstrap credential")
    root = Path(config["data_dir"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = InstanceLock(root)
    postgres = PrivatePostgres(root, Path(config["pg_bin"]))
    database = None
    try:
        postgres.start()
        database = Database(postgres.url())
        tables = inspect(database.engine).get_table_names()
        if "alembic_version" in tables:
            with database.engine.connect() as conn:
                current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if current != "0001":
                # Refuse unknown/future revisions. Upgrades need a restore-tested migration path.
                raise RuntimeError("Database revision is incompatible. Preserve this library and use its matching application version.")
        elif tables:
            raise RuntimeError("Unrecognized database contents; refusing automatic migration")
        migrate(database.engine)
        app = create_app(database, token, root / "research")
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False, timeout_graceful_shutdown=15))

        def shutdown_on_parent_close():
            # Explicit Quit closes stdin; parent crashes also close the owned pipe.
            sys.stdin.read()
            server.should_exit = True

        threading.Thread(target=shutdown_on_parent_close, daemon=True).start()
        print(json.dumps({"endpoint": f"http://127.0.0.1:{sock.getsockname()[1]}"}), flush=True)
        server.run(sockets=[sock])
        sock.close()
    finally:
        if database:
            database.engine.dispose()
        postgres.stop()
        lock.close()


def run():
    try:
        main()
    except Exception:
        # Do not print DB URLs, credentials or traceback locals on the bootstrap channel.
        print(json.dumps({"error": "Local startup failed. Check PostgreSQL runtime, library lock, credential store and schema compatibility."}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
