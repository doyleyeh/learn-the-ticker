from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.app.backup import BackupError, MAX_ARCHIVE_BYTES, make_backup, preview_backup, restore_backup
from backend.app.codex_login import CodexLogin
from backend.app.contracts import ApprovalDecision, Conversation, EvidenceBundle, ResearchRequest, RuntimeModelCatalog, SavedResearch, Settings, TermRequest, now
from backend.app.db import Database
from backend.app.import_previews import ImportPreviews
from backend.app.import_routes import mount_import_routes
from backend.app.research import ResearchService
from backend.app.runtimes import runtimes
from backend.app.terms import TermService

ORIGINS = ("tauri://localhost", "http://tauri.localhost", "https://tauri.localhost", "http://localhost:1420", "http://127.0.0.1:1420")


class SaveRequest(BaseModel):
    bundle_id: str
    title: str = Field(min_length=1, max_length=200)


class ConversationRequest(BaseModel):
    asset_id: str


class ConversationUpdate(BaseModel):
    asset_id: str | None = Field(default=None, max_length=200)
    bookmarked: bool | None = None


def create_app(db: Database, token: str, workspace: Path, *, adapters=None, verifier=None, identity_resolver=None, financial_adapter=None, filing_adapter=None) -> FastAPI:
    if len(token) < 32:
        raise ValueError("A random session credential of at least 32 characters is required")
    codex_profile = workspace.parent / "connections" / "codex"
    service = ResearchService(db, adapters or runtimes(codex_profile), workspace, identity_resolver=identity_resolver, financial_adapter=financial_adapter, filing_adapter=filing_adapter, **({"verifier": verifier} if verifier else {}))
    codex_login = CodexLogin(codex_profile)
    terms = TermService(service)
    imports = ImportPreviews(service)
    settings_lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        db.recover()
        db.expire_conversations(service.settings().retention_days)
        yield
        await codex_login.close()
        await imports.close()
        await service.close()

    app = FastAPI(title="Learn the Ticker Desktop", version="0.2.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service
    app.state.codex_login = codex_login
    app.state.terms = terms
    app.state.imports = imports
    mount_import_routes(app, imports)
    app.add_middleware(CORSMiddleware, allow_origins=list(ORIGINS), allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-Backup-Fingerprint", "X-Import-Metadata"])

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        origin = request.headers.get("origin")
        host = request.url.hostname
        if host not in ("127.0.0.1", "localhost", "testserver") or (origin and origin not in ORIGINS):
            return JSONResponse({"detail": "Untrusted local origin"}, status_code=403)
        if request.method != "OPTIONS" and not secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + token):
            return JSONResponse({"detail": "Local authentication required"}, status_code=401)
        return await call_next(request)

    @app.get("/api/health")
    def health():
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "schema_version": "1"}

    @app.get("/api/settings")
    def settings():
        return service.settings()

    @app.put("/api/settings")
    async def update_settings(value: Settings):
        async with settings_lock:
            return await save_settings(value)

    async def save_settings(value: Settings):
        previous = service.settings()
        changed = (previous.provider, previous.model) != (value.provider, value.model)
        if changed and value.cloud_enabled and any(not task.done() for task in service.tasks.values()):
            raise HTTPException(409, "Finish or cancel active research before changing provider or model")
        if changed and value.model is not None:
            adapter = service.adapters.get(value.provider)
            catalog = await adapter.models() if adapter else None
            if not catalog or catalog.status != "available" or not any(model.id == value.model for model in catalog.models):
                raise HTTPException(409, "Choose an available model from the selected provider catalog; no settings were changed")
        if changed and value.cloud_enabled and any(not task.done() for task in service.tasks.values()):
            raise HTTPException(409, "Finish or cancel active research before changing provider or model")
        db.put("settings", "settings", value.model_dump(mode="json"))
        if not value.cloud_enabled:
            await imports.close(online_only=True)
            await service.close()
        return value

    @app.get("/api/connections")
    async def connections():
        return [await adapter.check() for adapter in service.adapters.values()]

    @app.get("/api/approvals")
    async def approvals():
        return JSONResponse([item.model_dump(mode="json") for item in service.approvals.snapshot()], headers={"Cache-Control": "no-store"})

    @app.post("/api/jobs/{job_id}/approvals/{approval_id}")
    async def review_access(job_id: str, approval_id: str, decision: ApprovalDecision):
        job = db.job(job_id)
        task = service.tasks.get(job_id)
        if not job or job["status"] != "running" or not task or task.done() or not service.settings().cloud_enabled:
            raise HTTPException(409, "Research is no longer active. Nothing was approved.")
        try:
            service.approvals.resolve(job_id, approval_id, decision)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return JSONResponse({"decision": decision.decision}, headers={"Cache-Control": "no-store"})

    @app.get("/api/connections/{provider}/models", response_model=RuntimeModelCatalog)
    async def models(provider: str):
        adapter = service.adapters.get(provider)
        if not adapter:
            raise HTTPException(404, "Connection is unavailable")
        if codex_login.snapshot().status == "pending":
            raise HTTPException(409, "Complete or cancel sign-in before refreshing models")
        catalog = await adapter.models()
        return JSONResponse(catalog.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    def login_response():
        return JSONResponse(codex_login.snapshot().model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @app.get("/api/connections/codex/login")
    async def login_status():
        return login_response()

    @app.post("/api/connections/codex/login")
    async def start_login():
        if any(not task.done() for task in service.tasks.values()):
            raise HTTPException(409, "Finish or cancel active research before changing the connection")
        await codex_login.start()
        return login_response()

    @app.post("/api/connections/codex/login/cancel")
    async def cancel_login():
        await codex_login.cancel()
        return login_response()

    @app.get("/api/library")
    def library():
        return db.list("asset")

    @app.get("/api/library/backup")
    def backup():
        try:
            content = make_backup(db)
        except BackupError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, "Library data could not be validated; no backup was created") from exc
        return Response(content, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="learn-the-ticker-library.lttbackup"'})

    async def backup_body(request: Request) -> bytes:
        data = bytearray()
        async for part in request.stream():
            if len(data) + len(part) > MAX_ARCHIVE_BYTES:
                raise HTTPException(413, "The portable archive exceeds 128 MiB")
            data.extend(part)
        return bytes(data)

    @app.post("/api/library/restore/preview")
    async def restore_preview(request: Request):
        raw = await backup_body(request)
        try:
            return await asyncio.to_thread(preview_backup, db, raw)
        except BackupError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/library/restore")
    async def restore(request: Request):
        raw = await backup_body(request)
        try:
            result = await asyncio.to_thread(restore_backup, db, raw, request.headers.get("X-Backup-Fingerprint", ""))
        except BackupError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"restored": True, "summary": result, "cloud_enabled": False}

    @app.get("/api/assets/{asset_id:path}")
    def asset(asset_id: str):
        result = service.cached(asset_id)
        if result is None:
            raise HTTPException(404, "Asset is not cached; start research to resolve it")
        return result

    @app.post("/api/research", status_code=202)
    async def research(value: ResearchRequest):
        if codex_login.snapshot().status == "pending":
            raise HTTPException(409, "Complete or cancel Codex sign-in before starting research")
        try:
            return await service.submit(value)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/terms/lookup")
    def lookup_term(value: TermRequest):
        try:
            return terms.lookup(value)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/terms", status_code=202)
    async def explain_term(value: TermRequest):
        if codex_login.snapshot().status == "pending":
            raise HTTPException(409, "Complete or cancel Codex sign-in before generating an explanation")
        try:
            return await terms.submit(value)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/jobs/{job_id}")
    async def job(job_id: str):
        result = db.job(job_id)
        if result is None:
            raise HTTPException(404, "Research job not found")
        if result["request"].get("purpose") == "import_explanation" and result.get("result"):
            from backend.app.import_learning import ImportLearningRequest
            try:
                checked = await app.state.import_learning.lookup(ImportLearningRequest.model_validate(result["request"]))
                if checked.get("result") != result["result"]:
                    raise ValueError("Completed result no longer matches its immutable interpretation")
            except ValueError:
                raise HTTPException(409, "This document explanation no longer passes its source and integrity checks.") from None
        return result

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel(job_id: str):
        if db.job(job_id) is None:
            raise HTTPException(404, "Research job not found")
        await service.cancel(job_id)
        return db.job(job_id)

    @app.websocket("/api/events/{job_id}")
    async def events(socket: WebSocket, job_id: str):
        if socket.headers.get("origin") not in ORIGINS:
            await socket.close(code=1008)
            return
        await socket.accept()
        try:
            auth = await asyncio.wait_for(socket.receive_json(), 5)
            if not isinstance(auth, dict) or not isinstance(auth.get("token"), str) or not secrets.compare_digest(auth["token"], token):
                await socket.close(code=1008)
                return
            if not db.job(job_id):
                await socket.close(code=1008)
                return
            after = max(0, int(auth.get("after", 0)))
            while True:
                for event in db.events(job_id, after):
                    after = event["sequence"]
                    await socket.send_json(event)
                current = db.job(job_id)
                if current["status"] not in ("queued", "running"):
                    await socket.close()
                    return
                await asyncio.sleep(0.2)
        except WebSocketDisconnect:
            return
        except (asyncio.TimeoutError, ValueError, TypeError):
            try:
                await socket.close(code=1008)
            except WebSocketDisconnect:
                pass

    @app.post("/api/conversations", status_code=201)
    def create_conversation(value: ConversationRequest):
        if not service.cached(value.asset_id):
            raise HTTPException(404, "Resolve the asset first")
        timestamp = now().isoformat()
        result = Conversation(asset_id=value.asset_id, created_at=timestamp, last_activity=timestamp).model_dump(mode="json")
        db.put("conversation:" + result["id"], "conversation", result)
        return result

    @app.get("/api/conversations")
    def conversations():
        db.expire_conversations(service.settings().retention_days)
        return db.list("conversation")

    @app.put("/api/conversations/{conversation_id}")
    def update_conversation(conversation_id: str, value: ConversationUpdate):
        try:
            return db.update_conversation(conversation_id, asset_id=value.asset_id, bookmarked=value.bookmarked)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/saved")
    def saved():
        return db.list("saved")

    @app.post("/api/saved", status_code=201)
    def save(value: SaveRequest):
        bundle = db.get("bundle:" + value.bundle_id)
        if not bundle:
            raise HTTPException(404, "Evidence snapshot not found")
        result = SavedResearch(bundle_id=value.bundle_id, title=value.title).model_dump(mode="json")
        db.put("saved:" + result["id"], "saved", result, bundle["asset"]["id"])
        return result

    @app.get("/api/bundles/{bundle_id}")
    def bundle(bundle_id: str):
        value = db.get("bundle:" + bundle_id)
        if not value:
            raise HTTPException(404, "Evidence snapshot not found")
        return value

    @app.get("/api/export/{bundle_id}")
    def export(bundle_id: str, format: str = "json"):
        value = EvidenceBundle.model_validate(bundle(bundle_id))
        # Export normalized app data only; never provider transcripts or unrestricted source bodies.
        payload = value.model_dump(mode="json")
        for source in payload["sources"]:
            source.pop("excerpt", None)
        if format == "json":
            return JSONResponse(payload, headers={"Content-Disposition": 'attachment; filename="research.json"'})
        if format != "markdown":
            raise HTTPException(400, "Choose json or markdown")
        def clean(text):
            return text.replace("<", "&lt;").replace(">", "&gt;").replace("[", "\\[").replace("]", "\\]")
        lines = ["# " + clean(value.asset.name), "", f"Research snapshot: {value.created_at.isoformat()}", "", "Educational research; not investment advice.", "", "## Source-backed claims"]
        for claim in value.claims:
            lines += ["", clean(claim.text) + " Sources: " + ", ".join(claim.source_ids)]
        if value.financials is not None:
            lines += ["", "## Issuer financial observations", "",
                      "Issuer: " + clean(value.financials.issuer.name),
                      "Original reported units; historical values include superseded and unresolved conflicting versions."]
            for row in value.financials.observations:
                lines += [f"\n{row.concept}: {row.value} {row.unit}; {row.start or 'instant'} through {row.end}; "
                          f"filed {row.filed} ({row.form}, {row.accession}); {row.revision}; source {row.source_id}; "
                          f"observation {row.id}; supersedes {', '.join(row.supersedes) or 'none'}."]
            lines += ["", "Availability: " + ", ".join(value.financials.gaps)]
        lines += ["", "## Unverified research notes", "", "These notes are not factual evidence."]
        lines += ["\n" + clean(note.text) for note in value.notes]
        lines += ["", "## Sources"]
        for source in value.sources:
            lines += [f"\n{source.id}: {clean(source.title)} — {source.url} (published {source.published_at or 'unknown'}; "
                      f"as of {source.as_of or 'unknown'}; retrieved {source.retrieved_at.isoformat()}; {source.policy.value}; {source.provenance})"]
            if source.filing_publication:
                proof = source.filing_publication
                lines += [f"Filing-date reference: {proof.index_url}; accession {proof.accession}; "
                          f"index retrieved {proof.retrieved_at.isoformat()}; index SHA-256 {proof.index_hash}."]
        return Response("\n".join(lines), media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="research.md"'})

    return app
