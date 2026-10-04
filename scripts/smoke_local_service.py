"""Explicit local lifecycle smoke. No provider calls. Uses a new private PostgreSQL cluster."""
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[1]
pg_bin = Path(os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin"))
data = root / ".local" / ("smoke-" + secrets.token_hex(4))
token = secrets.token_urlsafe(48)
command = [str(root / "dist/ltt-service.exe")] if "--packaged" in sys.argv else [sys.executable, "-m", "backend.app.entrypoint"]
process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    process.stdin.write(json.dumps({"token": token, "data_dir": str(data), "pg_bin": str(pg_bin)}) + "\n")
    process.stdin.flush()
    response = json.loads(process.stdout.readline())
    if "endpoint" not in response:
        raise RuntimeError(response.get("error", "Startup failed"))
    endpoint = response["endpoint"]
    with httpx.Client(base_url=endpoint, trust_env=False) as client:
        for _ in range(20):
            try:
                health = client.get("/api/health", headers={"Authorization": "Bearer " + token})
                if health.status_code == 200:
                    break
            except httpx.ConnectError:
                time.sleep(.2)
        assert health.json()["status"] == "ready"
        assert client.get("/api/health").status_code == 401
        assert client.get("/api/library", headers={"Authorization": "Bearer " + token}).json() == []
        login = client.get("/api/connections/codex/login", headers={"Authorization": "Bearer " + token})
        assert login.status_code == 200 and login.json()["status"] == "idle"
        assert login.json()["user_code"] is None and login.headers["cache-control"] == "no-store"
        assert client.get("/api/connections/codex/login").status_code == 401
        term = {"term": "revenue", "bundle_id": "missing-snapshot"}
        assert client.post("/api/terms/lookup", json=term).status_code == 401
        assert client.post("/api/terms/lookup", json=term, headers={"Authorization": "Bearer " + token}).status_code == 404
        path = "/api/imports/preview/file?format=csv&permission_confirmed=true"
        assert client.post(path, content=b"Metric,Value").status_code == 401
        imported = client.post(path, content=b"Metric,Value\nRevenue,123456789.123456789", headers={"Authorization": "Bearer " + token}, timeout=30)
        assert imported.status_code == 200 and imported.headers["cache-control"] == "no-store"
        preview = imported.json()
        assert preview["state"] == "unverified" and not preview["saved"] and not preview["document"]["verified"]
        assert preview["document"]["blocks"][1]["cells"][1]["text"] == "123456789.123456789"
        assert client.get("/api/library", headers={"Authorization": "Bearer " + token}).json() == []
    print("Private PostgreSQL initialization, migrations, authenticated API, empty library, idle sign-in and term lookup endpoints passed.")
    print("Authenticated offline CSV preview preserved exact decimals without library writes through the owned parser worker.")
finally:
    process.stdin.close()
    try:
        process.wait(timeout=45)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Local service did not stop cleanly; inspect the smoke data directory") from None
    assert not (data / "database/data/postmaster.pid").exists(), "PostgreSQL did not stop"
    print("Owned service and private PostgreSQL stopped cleanly.")
