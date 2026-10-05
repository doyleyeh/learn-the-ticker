"""Actual frozen API restore/restart of synthetic private evidence; no live requests."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import secrets

import httpx

from backend.app.backup import make_backup, read_backup
from backend.app.contracts import Claim, EvidenceBundle, Settings, TermExplanation, TermRequest
from backend.app.evidence_reuse import admit_numeric_interpretations, cached_context, context_references
from backend.app.terms import term_key, validate_explanation
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
        references = context_references([cached_context(bundle)])
        answer = admit_numeric_interpretations(EvidenceBundle(asset=bundle.asset, created_at=bundle.created_at),
            [Claim(asset_id=bundle.asset.id, text="Interpretation of original saved numerical evidence.", source_ids=list(references))], references)
        answer_payload = answer.model_dump(mode="json")
        db.put("bundle:" + answer.id, "bundle", answer_payload, bundle.asset.id)
        term_request = TermRequest(term="Historical P/E", bundle_id=bundle.id)
        term = TermExplanation(id=term_key(term_request), term=term_request.term, bundle_id=bundle.id, asset_id=bundle.asset.id,
            explanation="The retained historical P/E was 29.5.", basis="snapshot", source_ids=[bundle.market.valuations.source_id],
            language="en", level="beginner", provider="codex")
        validate_explanation(term, bundle)
        db.put("term:" + term.id, "term", term.model_dump(mode="json"), bundle.id)
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
        assert (await client.get("/api/bundles/" + answer.id)).json() == answer_payload
    async with service(directory) as client:
        assert (await client.get("/api/bundles/" + bundle.id)).json() == payload
        assert (await client.get("/api/bundles/" + answer.id)).json() == answer_payload
        exported = await client.get("/api/export/" + answer.id)
        assert exported.status_code == 200 and not exported.json()["notes"] and not exported.json()["context_references"]
        settings = (await client.get("/api/settings")).json()
        assert settings["cloud_enabled"] is False and settings["experimental_yahoo_enabled"] is False
        backup = await client.get("/api/library/backup")
        assert backup.status_code == 200
        _, data = read_backup(backup.content)
        assert any(row.kind == "bundle" and row.payload == payload for row in data.records)
        assert any(row.kind == "bundle" and row.payload == answer_payload for row in data.records)
        assert any(row.kind == "term" and row.payload == term.model_dump(mode="json") for row in data.records)
        preview = await client.post("/api/library/restore/preview", content=archive)
        assert preview.status_code == 200 and not preview.json()["can_restore"]
    print("Frozen API restored exact synthetic market/issuer evidence, saved returns, numerical interpretations and original-version references to PostgreSQL; restart/private backup/export filtering/non-empty rejection and reset network settings passed. No provider calls.")


if __name__ == "__main__":
    asyncio.run(check())
