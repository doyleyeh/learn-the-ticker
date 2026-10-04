"""Application-owned retained-source operations; no provider or fact publication."""
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from backend.app.contracts import Contract, Source
from backend.app.import_documents import ImportFailure, ParsedDocument
from backend.app.retained_imports import RetainedImport, retain_import


class RetainMetadata(Contract):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    title: str = Field(min_length=1, max_length=200)
    preview_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    storage_and_backup_confirmed: Literal[True]

    @field_validator("storage_and_backup_confirmed", mode="before")
    @classmethod
    def require_permission(cls, value):
        if value is not True:
            raise ValueError("Storage permission is required")
        return value


class RetainURL(RetainMetadata):
    url: str = Field(min_length=1, max_length=2000)


class RetainedImportSummary(Contract):
    id: str
    title: str
    format: Literal["csv", "xlsx", "pdf", "html"]
    origin: Literal["local_file", "public_url"]
    source: Source | None
    checked_at: AwareDatetime
    retained_at: AwareDatetime
    byte_count: int
    content_hash: str
    verified: Literal[False] = False


class RetainedImportView(Contract):
    item: RetainedImportSummary
    document: ParsedDocument


def summary(item):
    return RetainedImportSummary(**item.model_dump(include={"id", "title", "origin", "source", "checked_at", "retained_at", "byte_count"}),
                                 format=item.document.format, content_hash=item.document.content_hash)


class ImportStorage:
    def __init__(self, previews):
        self.previews = previews
        self.db = previews.research.db

    def save(self, raw, preview, metadata):
        if raw is None or preview.document is None:
            raise ImportFailure("storage_unavailable")
        if preview.document.content_hash != metadata.preview_hash:
            raise ImportFailure("preview_changed")
        try:
            return summary(retain_import(self.db, raw, preview, title=metadata.title,
                storage_and_backup_confirmed=metadata.storage_and_backup_confirmed))
        except (ValueError, SQLAlchemyError):
            raise ImportFailure("storage_unavailable") from None

    async def file(self, raw, format, metadata):
        preview = await self.previews.file(raw, format, True)
        return self.save(raw, preview, metadata)

    async def url(self, metadata):
        preview, raw = await self.previews.url_document(metadata.url)
        self.previews.require_online()
        return self.save(raw, preview, metadata)

    def list(self):
        try:
            return [summary(RetainedImport.model_validate(row)) for row in self.db.list("import")]
        except (ValueError, SQLAlchemyError):
            raise ImportFailure("retained_unavailable") from None

    async def view(self, identifier):
        async def operation():
            try:
                item = RetainedImport.model_validate(self.db.get("import:" + identifier))
                # Archives preserve untrusted structure. Reparse original bytes before use.
                document = await self.previews.parse(item.content(), item.document.format)
                if document != item.document:
                    raise ValueError("Parser result changed")
                # Recheck current rights after the asynchronous worker completes.
                RetainedImport.model_validate(item.model_dump(mode="json"))
                return RetainedImportView(item=summary(item), document=document)
            except (ValueError, SQLAlchemyError):
                raise ImportFailure("retained_unavailable") from None
        return await self.previews.run(operation, online=False)
