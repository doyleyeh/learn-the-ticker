"""Portable application data, never SQL, filesystem trees, credentials or provider profiles."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
import zlib
from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.contracts import AssetIdentity, BackupSummary, Conversation, EvidenceBundle, ResearchRequest, RuntimeEvent, SavedResearch, Settings, SourcePolicy, TermExplanation, TermRequest, now
from backend.app.db import Database, Event, Job, Record
from backend.app.terms import term_key, validate_explanation

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_CONTENT_BYTES = 256 * 1024 * 1024
FORMAT = "learn-the-ticker.library"


class BackupError(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoredRecord(StrictModel):
    id: str = Field(max_length=200)
    kind: Literal["asset", "bundle", "conversation", "saved", "settings", "term"]
    parent_id: str | None = Field(default=None, max_length=200)
    updated_at: AwareDatetime
    payload: dict


class StoredJob(StrictModel):
    id: str = Field(min_length=1, max_length=36)
    status: Literal["queued", "running", "completed", "failed", "cancelled", "interrupted", "needs_identity"]
    request: ResearchRequest | TermRequest
    result: dict | None = None
    error: str | None = Field(default=None, max_length=1000)
    created_at: AwareDatetime


class StoredEvent(StrictModel):
    id: int = Field(ge=1)
    job_id: str = Field(max_length=36)
    payload: RuntimeEvent


class LibraryData(StrictModel):
    records: list[StoredRecord] = Field(max_length=100000)
    jobs: list[StoredJob] = Field(max_length=100000)
    events: list[StoredEvent] = Field(max_length=1000000)


class IdentityResult(StrictModel):
    candidates: list[AssetIdentity] = Field(max_length=20)
    message: str | None = Field(default=None, max_length=1000)


class EducationalResult(StrictModel):
    educational_redirect: str = Field(max_length=10000)


class Manifest(StrictModel):
    format: Literal["learn-the-ticker.library"] = FORMAT
    format_version: Literal["1"] = "1"
    database_revision: Literal["0001"] = "0001"
    application_version: str = "0.2.0"
    created_at: AwareDatetime = Field(default_factory=now)
    content_bytes: int = Field(ge=0, le=MAX_CONTENT_BYTES)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    credentials_included: Literal[False] = False


def utc(value: datetime) -> datetime:
    # SQLite test doubles lose timezone metadata; production uses timestamptz.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def validate_library(data: LibraryData):
    """Validate types and references without executing files, SQL or network requests."""
    if len({row.id for row in data.records}) != len(data.records):
        raise BackupError("Duplicate library record")
    records = {row.id: row for row in data.records}
    bundles: dict[str, EvidenceBundle] = {}
    for row in data.records:
        model = {"asset": EvidenceBundle, "bundle": EvidenceBundle, "settings": Settings, "conversation": Conversation, "saved": SavedResearch, "term": TermExplanation}[row.kind]
        value = model.model_validate(row.payload)
        suffix = value.asset.id if row.kind == "asset" else getattr(value, "id", "")
        expected = "settings" if row.kind == "settings" else row.kind + ":" + suffix
        if row.id != expected:
            raise BackupError("Record identity does not match its content")
        if isinstance(value, EvidenceBundle):
            if value.created_at.tzinfo is None:
                raise BackupError("Evidence timestamps must include a timezone")
            sources = {source.id: source for source in value.sources}
            if len(sources) != len(value.sources) or any(source.asset_id != value.asset.id or source.policy == SourcePolicy.rejected for source in value.sources):
                raise BackupError("Invalid evidence sources")
            claim_ids = {claim.id for claim in [*value.claims, *value.notes]}
            if len(claim_ids) != len(value.claims) + len(value.notes):
                raise BackupError("Duplicate claims")
            for claim in [*value.claims, *value.notes]:
                if claim.asset_id != value.asset.id or any(sid not in sources for sid in claim.source_ids):
                    raise BackupError("Wrong-asset or missing citation")
            for claim in value.claims:
                if claim.kind == "unverified_note" or not claim.source_ids or any(not sources[sid].verified for sid in claim.source_ids):
                    raise BackupError("Unverified material cannot become canonical evidence")
            if any(note.kind != "unverified_note" or note.value is not None or note.input_claim_ids for note in value.notes):
                raise BackupError("Unverified notes cannot contain calculation inputs")
            if row.kind == "bundle":
                bundles[value.id] = value
        # Re-serialize through known models. Unknown fields such as tokens fail validation.
        row.payload = value.model_dump(mode="json")

    for row in data.records:
        value = row.payload
        if row.kind == "asset":
            if value["id"] not in bundles or bundles[value["id"]].model_dump(mode="json") != value:
                raise BackupError("Current asset snapshot is missing or inconsistent")
        elif row.kind == "saved" and value["bundle_id"] not in bundles:
            raise BackupError("Saved report references missing evidence")
        elif row.kind == "term":
            if value["bundle_id"] not in bundles or row.parent_id != value["bundle_id"]:
                raise BackupError("Term explanation references missing evidence")
            validate_explanation(TermExplanation.model_validate(value), bundles[value["bundle_id"]])
        elif row.kind == "conversation":
            if "asset:" + value["asset_id"] not in records:
                raise BackupError("Conversation scope is missing from the library")
            for message in value["messages"]:
                bundle_id = message.get("bundle_id")
                if bundle_id and (bundle_id not in bundles or (message.get("asset_id") and bundles[bundle_id].asset.id != message["asset_id"])):
                    raise BackupError("Conversation response references missing or wrong-asset evidence")

    jobs = {job.id: job for job in data.jobs}
    if len(jobs) != len(data.jobs) or len({event.id for event in data.events}) != len(data.events):
        raise BackupError("Duplicate jobs or events")
    for job in data.jobs:
        if isinstance(job.request, TermRequest):
            if job.request.bundle_id not in bundles:
                raise BackupError("Term job evidence is missing")
            if job.result:
                explanation = TermExplanation.model_validate(job.result)
                record = records.get("term:" + explanation.id)
                if not record or record.payload != explanation.model_dump(mode="json") or explanation.id != term_key(job.request):
                    raise BackupError("Completed term job is missing or inconsistent")
            continue
        if job.request.conversation_id and "conversation:" + job.request.conversation_id not in records:
            raise BackupError("Job conversation is missing")
        if job.result and "asset" in job.result:
            bundle = EvidenceBundle.model_validate(job.result)
            if bundle.id not in bundles or bundles[bundle.id].model_dump(mode="json") != bundle.model_dump(mode="json"):
                raise BackupError("Completed job evidence is missing or inconsistent")
        elif job.result:
            model = IdentityResult if "candidates" in job.result else EducationalResult
            model.model_validate(job.result)
    for event in data.events:
        if event.job_id not in jobs or event.payload.run_id != event.job_id:
            raise BackupError("Event has no matching job")
        if event.payload.kind == "message.delta" or set(event.payload.data) - {"status", "bundle_id"}:
            raise BackupError("Raw provider events are not portable library data")


def make_backup(db: Database) -> bytes:
    # Repeatable read makes records, jobs and events one consistent snapshot even
    # when a research job completes while the backup is being read.
    with db.engine.connect() as connection:
        if connection.dialect.name == "postgresql":
            connection = connection.execution_options(isolation_level="REPEATABLE READ")
        with Session(connection) as session, session.begin():
            data = LibraryData(
                records=[StoredRecord(id=row.id, kind=row.kind, parent_id=row.parent_id, payload=row.payload, updated_at=utc(row.updated_at)) for row in session.scalars(select(Record).order_by(Record.id))],
                jobs=[StoredJob(id=row.id, status=row.status, request=row.request, result=row.result, error=row.error, created_at=utc(row.created_at)) for row in session.scalars(select(Job).order_by(Job.id))],
                events=[StoredEvent(id=row.id, job_id=row.job_id, payload=row.payload) for row in session.scalars(select(Event).order_by(Event.id))],
            )
    try:
        validate_library(data)
    except (ValueError, TypeError, KeyError) as exc:
        raise BackupError("Library contains unsupported or inconsistent records; backup was not created") from exc
    payload = data.model_dump_json().encode("utf-8")
    if len(payload) > MAX_CONTENT_BYTES:
        raise BackupError("Library exceeds the current 256 MiB portable archive limit; no partial backup was created")
    manifest = Manifest(content_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest.model_dump_json())
        archive.writestr("library.json", payload)
    result = output.getvalue()
    if len(result) > MAX_ARCHIVE_BYTES:
        raise BackupError("Compressed library exceeds the current 128 MiB archive limit")
    return result


def read_backup(raw: bytes) -> tuple[Manifest, LibraryData]:
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise BackupError("Archive is too large")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) != 2 or {entry.filename for entry in entries} != {"manifest.json", "library.json"}:
                raise BackupError("Archive must contain only the library and its manifest")
            manifest_info, content_info = archive.getinfo("manifest.json"), archive.getinfo("library.json")
            if manifest_info.file_size > 10000 or content_info.file_size > MAX_CONTENT_BYTES:
                raise BackupError("Archive contents exceed the allowed size")
            if any(entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for entry in entries):
                raise BackupError("Encrypted or unsupported archive entries")
            manifest = Manifest.model_validate_json(archive.read("manifest.json"))
            payload = archive.read("library.json")
            if len(payload) != manifest.content_bytes or hashlib.sha256(payload).hexdigest() != manifest.sha256:
                raise BackupError("Backup checksum does not match; the archive may be incomplete or modified")
            data = LibraryData.model_validate_json(payload)
            validate_library(data)
            return manifest, data
    except BackupError:
        raise
    except (ValidationError, ValueError, KeyError, TypeError, OSError, RuntimeError, zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise BackupError("Invalid or incompatible library archive") from exc


def restore_allowed(db: Database) -> bool:
    with db.session() as session:
        return session.scalar(select(Record.id).where(Record.kind != "settings").limit(1)) is None and session.scalar(select(Job.id).limit(1)) is None and session.scalar(select(Event.id).limit(1)) is None


def preview_backup(db: Database, raw: bytes) -> BackupSummary:
    manifest, data = read_backup(raw)
    counts = Counter(record.kind for record in data.records)
    allowed = restore_allowed(db)
    return BackupSummary(created_at=manifest.created_at, fingerprint=hashlib.sha256(raw).hexdigest(), assets=counts["asset"], evidence_versions=counts["bundle"], conversations=counts["conversation"], saved_reports=counts["saved"], term_explanations=counts["term"], jobs=len(data.jobs), can_restore=allowed, reason=None if allowed else "Restore requires an empty library. Keep this installation intact and restore into a new library to preserve newer research.")


def restore_backup(db: Database, raw: bytes, fingerprint: str) -> BackupSummary:
    if not fingerprint or fingerprint != hashlib.sha256(raw).hexdigest():
        raise BackupError("The selected archive changed after preview; validate it again")
    summary = preview_backup(db, raw)
    if not summary.can_restore:
        raise BackupError(summary.reason)
    _, data = read_backup(raw)
    with db.session.begin() as session:
        if db.engine.dialect.name == "postgresql":
            # Serializes the empty-library check with every writer; never replace existing work.
            session.execute(text("LOCK TABLE records, research_jobs, runtime_events IN ACCESS EXCLUSIVE MODE"))
        if session.scalar(select(Record.id).where(Record.kind != "settings").limit(1)) or session.scalar(select(Job.id).limit(1)) or session.scalar(select(Event.id).limit(1)):
            raise BackupError("The library changed after preview; no data was replaced")
        settings_row = session.get(Record, "settings")
        if settings_row:
            session.delete(settings_row)
            session.flush()
        has_settings = False
        for row in data.records:
            payload = row.payload
            if row.kind == "settings":
                has_settings = True
                payload = {**payload, "cloud_enabled": False, "start_at_login": False}
            session.add(Record(id=row.id, kind=row.kind, parent_id=row.parent_id, payload=payload, updated_at=row.updated_at))
        if not has_settings:
            session.add(Record(id="settings", kind="settings", payload=Settings().model_dump(mode="json")))
        for row in data.jobs:
            interrupted = row.status in ("queued", "running")
            session.add(Job(id=row.id, status="interrupted" if interrupted else row.status, request=row.request.model_dump(mode="json"), result=row.result, error="Restored run requires an explicit retry; no subscription call was repeated." if interrupted else row.error, created_at=row.created_at))
        session.flush()
        for row in data.events:
            session.add(Event(id=row.id, job_id=row.job_id, payload=row.payload.model_dump(mode="json")))
        session.flush()
        if db.engine.dialect.name == "postgresql":
            session.execute(text("SELECT setval(pg_get_serial_sequence('runtime_events', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM runtime_events"))
    return summary
