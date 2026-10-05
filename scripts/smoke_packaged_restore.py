"""Actual frozen API restore/restart of synthetic private evidence; no live requests."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import secrets

import httpx

from backend.app.backup import make_backup, read_backup
from backend.app.contracts import Settings
from backend.app.db import Database
from backend.app.owned_process import close_owned, launch_owned
from tests.desktop.market_fixture import market_bundle

ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def service(directory):
    executable = ROOT / "dist/ltt-service.exe"
    if not executable.is_file():
        raise RuntimeError("Build the Windows sidecar before packaged restore verification")
    token = secrets.token_urlsafe(48)
    process = await launch_owned(str(executable), cwd=ROOT, stdin=asyncio.subprocess.PIPE,
                                 stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        process.stdin.write((json.dumps({"token": token, "data_dir": str(directory),
            "pg_bin": os.environ.get("LTT_PG_BIN", "C:/Program Files/PostgreSQL/17/bin")}) + "\n").encode())
        await process.stdin.drain()
        bootstrap = json.loads(await asyncio.wait_for(process.stdout.readline(), 45))
        if "endpoint" not in bootstrap:
            raise RuntimeError("Frozen service bootstrap failed")
        async with httpx.AsyncClient(base_url=bootstrap["endpoint"], trust_env=False, timeout=30,
                                      headers={"Authorization": "Bearer " + token}) as client:
            for _ in range(30):
                try:
                    if (await client.get("/api/health")).status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(.2)
            else:
                raise RuntimeError("Frozen service did not become ready")
            yield client
    finally:
        await close_owned(process, grace=45)
        assert not (directory / "database/data/postmaster.pid").exists(), "Private cluster did not stop cleanly"


async def check():
    # A synthetic archive is built in memory; the target is actual private PostgreSQL.
    db = Database("sqlite://", testing=True)
    try:
        bundle = market_bundle(valuations=True)
        payload = bundle.model_dump(mode="json")
        db.put("bundle:" + bundle.id, "bundle", payload, bundle.asset.id)
        db.put("asset:" + bundle.asset.id, "asset", payload, bundle.asset.id)
        db.put("settings", "settings", Settings(cloud_enabled=True, experimental_yahoo_enabled=True).model_dump(mode="json"))
        archive = make_backup(db)
    finally:
        db.engine.dispose()
    directory = ROOT / ".local" / ("frozen-market-restore-" + secrets.token_hex(4))
    async with service(directory) as client:
        preview = await client.post("/api/library/restore/preview", content=archive)
        assert preview.status_code == 200 and preview.json()["can_restore"]
        restored = await client.post("/api/library/restore", content=archive,
                                     headers={"X-Backup-Fingerprint": preview.json()["fingerprint"]})
        assert restored.status_code == 200 and restored.json()["restored"]
        assert (await client.get("/api/bundles/" + bundle.id)).json() == payload
    async with service(directory) as client:
        assert (await client.get("/api/bundles/" + bundle.id)).json() == payload
        settings = (await client.get("/api/settings")).json()
        assert settings["cloud_enabled"] is False and settings["experimental_yahoo_enabled"] is False
        backup = await client.get("/api/library/backup")
        assert backup.status_code == 200
        _, data = read_backup(backup.content)
        assert any(row.kind == "bundle" and row.payload == payload for row in data.records)
        preview = await client.post("/api/library/restore/preview", content=archive)
        assert preview.status_code == 200 and not preview.json()["can_restore"]
    print("Frozen API restored exact synthetic market/issuer evidence, citations and saved returns to PostgreSQL; restart/private backup/non-empty rejection and reset network settings passed. No provider calls.")


if __name__ == "__main__":
    asyncio.run(check())
