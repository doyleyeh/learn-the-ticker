"""Bounded, immutable untrusted attachments. No factual admission or provider access."""
import base64
import binascii
import hashlib
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field, field_validator, model_validator

from backend.app.contracts import Contract, Source, SourcePolicy, now, uid
from backend.app.import_documents import Budget, MAX_INPUT, ParsedDocument
from backend.app.import_previews import ImportPreview
from backend.app.source_registry import source_rule

MAX_ENCODED = 4 * ((MAX_INPUT + 2) // 3)
MAX_ATTACHMENTS = 100
MAX_ATTACHMENT_BYTES = 64 * 1024 * 1024


class RetainedImport(Contract):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    id: str = Field(default_factory=uid, pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    title: str = Field(min_length=1, max_length=200)
    origin: Literal["local_file", "public_url"]
    source: Source | None = None
    document: ParsedDocument
    checked_at: AwareDatetime
    retained_at: AwareDatetime = Field(default_factory=now)
    storage_and_backup_confirmed: Literal[True]
    # This permission never implies cloud transmission, source truth or chart eligibility.
    verified: Literal[False] = False
    byte_count: int = Field(gt=0, le=MAX_INPUT)
    content_base64: str = Field(min_length=1, max_length=MAX_ENCODED, repr=False)

    @field_validator("storage_and_backup_confirmed", mode="before")
    @classmethod
    def explicit_permission(cls, value):
        if value is not True:
            raise ValueError("Explicit storage and backup permission is required")
        return value

    def content(self) -> bytes:
        try:
            raw = base64.b64decode(self.content_base64, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError("Invalid retained document encoding") from None
        if (len(raw) != self.byte_count or not 0 < len(raw) <= MAX_INPUT
                or base64.b64encode(raw).decode("ascii") != self.content_base64
                or hashlib.sha256(raw).hexdigest() != self.document.content_hash):
            raise ValueError("Retained document checksum or size mismatch")
        return raw

    @model_validator(mode="after")
    def validate_attachment(self):
        self.content()
        if not self.title.strip() or any(ord(c) < 32 for c in self.title):
            raise ValueError("Invalid retained document title")
        if self.retained_at < self.checked_at or "unverified_import" not in self.document.limitations:
            raise ValueError("Invalid retained document provenance")
        # Archive validation checks bounded structure; it never executes a parser.
        budget = Budget()
        for block in self.document.blocks:
            budget.text(block.text)
            budget.row(block.cells)
            for cell in block.cells:
                budget.text(cell.text)
                if cell.raw_value and cell.raw_value != cell.text:
                    budget.text(cell.raw_value)
        if self.origin == "local_file":
            if self.source is not None or self.document.format not in ("pdf", "csv", "xlsx"):
                raise ValueError("Local retained imports cannot self-attest publisher metadata")
        else:
            source = self.source
            rule = source_rule(str(source.url)) if source else None
            if (not source or not rule or rule.policy != SourcePolicy.full_text
                    or source.policy != rule.policy or source.publisher != rule.publisher
                    or source.official != rule.official or source.verified or source.excerpt
                    or source.asset_id != "unassigned" or source.provenance != "user_import"
                    or source.content_hash != self.document.content_hash
                    or source.published_at or source.as_of or source.filing_publication
                    or source.retrieved_at > self.checked_at or self.document.format != "html"):
                raise ValueError("Retained URL rights or provenance are invalid")
        return self


def retain_import(db, raw: bytes, preview: ImportPreview, *, title: str, storage_and_backup_confirmed: bool):
    """Internal storage boundary; preview endpoints deliberately do not call it.

    Callers must obtain a production parser preview and distinct storage/backup
    permission. It cannot publish research, admit sources or contact a provider.
    """
    if storage_and_backup_confirmed is not True:
        raise ValueError("Explicit storage and backup permission is required")
    if preview.state != "unverified" or preview.document is None or not 0 < len(raw) <= MAX_INPUT:
        raise ValueError("Only bounded parsed documents can be retained")
    record = RetainedImport(title=title, origin=preview.origin, source=preview.source,
        document=preview.document, checked_at=preview.checked_at, byte_count=len(raw),
        storage_and_backup_confirmed=True, content_base64=base64.b64encode(raw).decode("ascii"))
    db.put("import:" + record.id, "import", record.model_dump(mode="json"))
    return record


def validate_import_write(session, record_id, payload, parent_id):
    from sqlalchemy import select, text
    from backend.app.db import Record
    document = RetainedImport.model_validate(payload)
    if record_id != "import:" + document.id or parent_id is not None:
        raise ValueError("Retained import identity is inconsistent")
    if session.bind.dialect.name == "postgresql":
        # Serialize capacity checks, including concurrent first imports, with writers.
        session.execute(text("LOCK TABLE records IN SHARE ROW EXCLUSIVE MODE"))
    existing = list(session.scalars(select(Record).where(Record.kind == "import", Record.id != record_id)))
    if len(existing) >= MAX_ATTACHMENTS or sum(RetainedImport.model_validate(row.payload).byte_count for row in existing) + document.byte_count > MAX_ATTACHMENT_BYTES:
        raise ValueError("Retained documents exceed the current portable archive capacity")
