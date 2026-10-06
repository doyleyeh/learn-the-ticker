"""Portable application data, never SQL, filesystem trees, credentials or provider profiles."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
import zlib
from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.contracts import AssetIdentity, BackupSummary, Conversation, EvidenceBundle, ResearchRequest, RuntimeEvent, SavedResearch, Settings, TermExplanation, TermRequest, now
from backend.app.db import Database, Event, Job, Record
from backend.app.evidence import validate_claim_sources
from backend.app.identity import identity_hash
from backend.app.retained_imports import MAX_ATTACHMENTS, MAX_ATTACHMENT_BYTES, RetainedImport
from backend.app.import_documents import MAX_INPUT
from backend.app.terms import term_key, validate_explanation
from backend.app.import_learning import ImportExplanation, ImportLearningRequest, learning_key, validate_learning
from backend.app.import_storage import RetainedImportView, summary as import_summary
from backend.app.comparisons import ComparisonResult, validate_comparison

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_CONTENT_BYTES = 256 * 1024 * 1024
FORMAT = "learn-the-ticker.library"
MAX_MANIFEST_BYTES = 64 * 1024


class BackupError(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoredRecord(StrictModel):
    id: str = Field(max_length=200)
    kind: Literal["asset", "bundle", "conversation", "saved", "settings", "term", "import", "import_explanation", "comparison"]
    parent_id: str | None = Field(default=None, max_length=200)
    updated_at: AwareDatetime
    payload: dict


class StoredJob(StrictModel):
    id: str = Field(min_length=1, max_length=36)
    status: Literal["queued", "running", "completed", "failed", "cancelled", "interrupted", "needs_identity"]
    request: ResearchRequest | TermRequest | ImportLearningRequest
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


class AttachmentEntry(StrictModel):
    id: str = Field(pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    byte_count: int = Field(gt=0, le=MAX_INPUT)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def path(self):
        return "attachments/" + self.id + ".bin"


class Manifest(StrictModel):
    format: Literal["learn-the-ticker.library"] = FORMAT
    format_version: Literal["1", "2"] = "1"
    database_revision: Literal["0001"] = "0001"
    application_version: str = "0.2.0"
    created_at: AwareDatetime = Field(default_factory=now)
    content_bytes: int = Field(ge=0, le=MAX_CONTENT_BYTES)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    credentials_included: Literal[False] = False
    attachments: list[AttachmentEntry] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)

    @model_validator(mode="after")
    def validate_attachments(self):
        if ((self.format_version == "1" and self.attachments)
                or (self.format_version == "2" and not self.attachments)
                or len({entry.id for entry in self.attachments}) != len(self.attachments)
                or sum(entry.byte_count for entry in self.attachments) > MAX_ATTACHMENT_BYTES):
            raise ValueError("Invalid attachment manifest")
        return self


def utc(value: datetime) -> datetime:
    # SQLite test doubles lose timezone metadata; production uses timestamptz.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def validate_library(data: LibraryData):
    """Validate types and references without executing files, SQL or network requests."""
    if len({row.id for row in data.records}) != len(data.records):
        raise BackupError("Duplicate library record")
    records = {row.id: row for row in data.records}
    bundles: dict[str, EvidenceBundle] = {}
    imports = [row for row in data.records if row.kind == "import"]
    if len(imports) > MAX_ATTACHMENTS:
        raise BackupError("Library exceeds the current 100 retained-document archive limit")
    attachment_bytes = 0
    for row in data.records:
        model = {"asset": EvidenceBundle, "bundle": EvidenceBundle, "settings": Settings, "conversation": Conversation, "saved": SavedResearch, "term": TermExplanation, "import": RetainedImport, "import_explanation": ImportExplanation, "comparison": ComparisonResult}[row.kind]
        value = model.model_validate(row.payload)
        suffix = value.asset.id if row.kind == "asset" else getattr(value, "id", "")
        expected = "settings" if row.kind == "settings" else row.kind + ":" + suffix
        if row.id != expected:
            raise BackupError("Record identity does not match its content")
        if isinstance(value, RetainedImport):
            attachment_bytes += value.byte_count
            if row.parent_id is not None or attachment_bytes > MAX_ATTACHMENT_BYTES:
                raise BackupError("Retained document references or aggregate size are invalid")
        if isinstance(value, EvidenceBundle):
            if row.kind == "asset" and value.completion != "complete":
                raise BackupError("An incomplete run cannot be the current asset snapshot")
            if value.identity_verification and value.identity_verification.identity_hash != identity_hash(value.asset):
                raise BackupError("Identity verification does not match the evidence scope")
            if value.created_at.tzinfo is None:
                raise BackupError("Evidence timestamps must include a timezone")
            try:
                validate_claim_sources(value)
            except ValueError as exc:
                raise BackupError(str(exc)) from exc
            if row.kind == "bundle":
                bundles[value.id] = value
        # Re-serialize through known models. Unknown fields such as tokens fail validation.
        row.payload = value.model_dump(mode="json")

    from backend.app.evidence_reuse import validate_context_references
    for bundle in bundles.values():
        validate_context_references(bundle, bundles.get)
    for row in data.records:
        value = row.payload
        if row.kind == "asset":
            if value["id"] not in bundles or bundles[value["id"]].model_dump(mode="json") != value:
                raise BackupError("Current asset snapshot is missing or inconsistent")
        elif row.kind == "saved" and value["bundle_id"] not in bundles:
            raise BackupError("Saved report references missing evidence")
        elif row.kind == "comparison":
            if row.parent_id is not None:
                raise BackupError("Comparison cannot belong to one asset only")
            validate_comparison(ComparisonResult.model_validate(value), bundles.get)
        elif row.kind == "term":
            if value["bundle_id"] not in bundles or row.parent_id != value["bundle_id"]:
                raise BackupError("Term explanation references missing evidence")
            validate_explanation(TermExplanation.model_validate(value), bundles[value["bundle_id"]])
        elif row.kind == "import_explanation":
            source = records.get("import:" + value["document_id"])
            if not source or source.kind != "import" or row.parent_id != value["document_id"]:
                raise BackupError("Import explanation references missing material")
            retained = RetainedImport.model_validate(source.payload)
            validate_learning(ImportExplanation.model_validate(value), RetainedImportView(item=import_summary(retained), document=retained.document))
        elif row.kind == "conversation":
            if "asset:" + value["asset_id"] not in records:
                raise BackupError("Conversation scope is missing from the library")
            contexts = [(value.get("context_bundle_id"), value["asset_id"])]
            for message in value["messages"]:
                bundle_id = message.get("bundle_id")
                if bundle_id and (bundle_id not in bundles or (message.get("asset_id") and bundles[bundle_id].asset.id != message["asset_id"])):
                    raise BackupError("Conversation response references missing or wrong-asset evidence")
                contexts.append((message.get("context_bundle_id"), message.get("asset_id")))
            for version, asset_id in contexts:
                if version and (version not in bundles or bundles[version].asset.id != asset_id):
                    raise BackupError("Conversation page context references missing or wrong-asset evidence")
            selected = value.get("context_bundle_id")
            if selected and identity_hash(bundles[selected].asset) != identity_hash(EvidenceBundle.model_validate(records["asset:" + value["asset_id"]].payload).asset):
                raise BackupError("Conversation page context does not match its current scope")

    jobs = {job.id: job for job in data.jobs}
    if len(jobs) != len(data.jobs) or len({event.id for event in data.events}) != len(data.events):
        raise BackupError("Duplicate jobs or events")
    for job in data.jobs:
        if isinstance(job.request, ImportLearningRequest):
            source = records.get("import:" + job.request.document_id)
            if not source or source.kind != "import" or source.payload["document"]["content_hash"] != job.request.content_hash:
                raise BackupError("Import job material is missing or changed")
            if (job.status == "completed") != (job.result is not None):
                raise BackupError("Import job completion is inconsistent")
            if job.result is not None:
                explanation = ImportExplanation.model_validate(job.result)
                record = records.get("import_explanation:" + explanation.id)
                if (not record or record.payload != explanation.model_dump(mode="json") or explanation.id != learning_key(job.request)
                        or (explanation.provider, explanation.model) != (job.request.provider, job.request.model)):
                    raise BackupError("Completed import explanation is missing or inconsistent")
            continue
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
        version = job.request.context_bundle_id
        if version and (not job.request.conversation_id or version not in bundles or bundles[version].asset.id != job.request.asset_id):
            raise BackupError("Job page context is missing or inconsistent")
        if job.result and "asset" in job.result:
            bundle = EvidenceBundle.model_validate(job.result)
            if bundle.completion == "section_checkpoint" and job.status not in ("running", "failed", "cancelled", "interrupted"):
                raise BackupError("Section checkpoint has an invalid job status")
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
    attachments = []
    retained_bytes = {}
    for row in data.records:
        if row.kind == "import":
            document = RetainedImport.model_validate(row.payload)
            entry = AttachmentEntry(id=document.id, byte_count=document.byte_count, sha256=document.document.content_hash)
            attachments.append(entry)
            retained_bytes[entry.path] = document.content()
            # Raw bytes have their own bounded, checksummed members in format 2.
            row.payload.pop("content_base64")
    payload = data.model_dump_json().encode("utf-8")
    if len(payload) > MAX_CONTENT_BYTES:
        raise BackupError("Library exceeds the current 256 MiB portable archive limit; no partial backup was created")
    manifest = Manifest(format_version="2" if attachments else "1", attachments=attachments,
                        content_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest.model_dump_json(exclude={"attachments"} if not attachments else set()))
        archive.writestr("library.json", payload)
        for name, content in retained_bytes.items():
            archive.writestr(name, content)
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
            names = {entry.filename for entry in entries}
            if len(entries) > MAX_ATTACHMENTS + 2 or len(names) != len(entries) or not {"manifest.json", "library.json"} <= names:
                raise BackupError("Archive has missing, duplicate or excessive entries")
            manifest_info, content_info = archive.getinfo("manifest.json"), archive.getinfo("library.json")
            if manifest_info.file_size > MAX_MANIFEST_BYTES or content_info.file_size > MAX_CONTENT_BYTES:
                raise BackupError("Archive contents exceed the allowed size")
            if any(entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for entry in entries):
                raise BackupError("Encrypted or unsupported archive entries")
            manifest = Manifest.model_validate_json(read_member(archive, manifest_info, MAX_MANIFEST_BYTES))
            if names != {"manifest.json", "library.json", *(entry.path for entry in manifest.attachments)}:
                raise BackupError("Archive contains unregistered attachment paths")
            payload = read_member(archive, content_info, MAX_CONTENT_BYTES)
            if len(payload) != manifest.content_bytes or hashlib.sha256(payload).hexdigest() != manifest.sha256:
                raise BackupError("Backup checksum does not match; the archive may be incomplete or modified")
            data = LibraryData.model_validate_json(payload)
            import_rows = [row for row in data.records if row.kind == "import"]
            expected = {"import:" + entry.id: entry for entry in manifest.attachments}
            if len(import_rows) != len(expected) or {row.id for row in import_rows} != expected.keys():
                raise BackupError("Retained document manifest references do not match")
            for row in import_rows:
                entry = expected[row.id]
                content = read_member(archive, archive.getinfo(entry.path), entry.byte_count)
                if (len(content) != entry.byte_count or hashlib.sha256(content).hexdigest() != entry.sha256
                        or "content_base64" in row.payload or not isinstance(row.payload.get("document"), dict)
                        or row.payload.get("byte_count") != entry.byte_count
                        or row.payload.get("document", {}).get("content_hash") != entry.sha256):
                    raise BackupError("Retained document checksum or reference mismatch")
                row.payload["content_base64"] = base64.b64encode(content).decode("ascii")
            validate_library(data)
            return manifest, data
    except BackupError:
        raise
    except (ValidationError, ValueError, KeyError, TypeError, OSError, RuntimeError, zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise BackupError("Invalid or incompatible library archive") from exc


def read_member(archive, entry, limit):
    if entry.file_size > limit:
        raise BackupError("Archive entry exceeds its permitted size")
    with archive.open(entry) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit or len(raw) != entry.file_size:
        raise BackupError("Archive entry exceeds its permitted size")
    return raw


def restore_allowed(db: Database) -> bool:
    with db.session() as session:
        return session.scalar(select(Record.id).where(Record.kind != "settings").limit(1)) is None and session.scalar(select(Job.id).limit(1)) is None and session.scalar(select(Event.id).limit(1)) is None


def preview_backup(db: Database, raw: bytes) -> BackupSummary:
    manifest, data = read_backup(raw)
    counts = Counter(record.kind for record in data.records)
    allowed = restore_allowed(db)
    return BackupSummary(format_version=manifest.format_version, created_at=manifest.created_at, fingerprint=hashlib.sha256(raw).hexdigest(), assets=counts["asset"], evidence_versions=counts["bundle"], conversations=counts["conversation"], saved_reports=counts["saved"], term_explanations=counts["term"], retained_imports=counts["import"], import_explanations=counts["import_explanation"], attachment_bytes=sum(entry.byte_count for entry in manifest.attachments), jobs=len(data.jobs), can_restore=allowed, reason=None if allowed else "Restore requires an empty library. Keep this installation intact and restore into a new library to preserve newer research.")


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
                payload = {**payload, "cloud_enabled": False, "experimental_yahoo_enabled": False, "start_at_login": False}
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
