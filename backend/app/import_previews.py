"""Ephemeral, permission-aware import previews; no database writes or fact admission."""
import asyncio
import ipaddress
from urllib.parse import urlsplit

from pydantic import AwareDatetime
from typing import Literal

from backend.app.contracts import Contract, Source, SourcePolicy, now
from backend.app.evidence import candidate_metadata, fetch_public_bytes, public_address
from backend.app.import_documents import ImportFailure, ParsedDocument
from backend.app.import_worker import extract_document
from backend.app.runtime_base import RuntimeFailure


class ImportPreview(Contract):
    state: Literal["unverified", "link_only"]
    origin: Literal["local_file", "public_url"]
    source: Source | None = None
    checked_at: AwareDatetime
    document: ParsedDocument | None = None
    saved: Literal[False] = False


MESSAGES = {
    "permission_required": "Confirm that you have permission to process the selected document.",
    "input_limit": "Select a non-empty document no larger than 5 MiB.",
    "content_limit": "The extracted content exceeds the preview limit. Select a smaller document.",
    "table_limit": "This table exceeds the row, column or cell preview limit.",
    "archive_limit": "The workbook archive is malformed or expands beyond the preview limit.",
    "workbook_active_content": "This workbook contains unsupported embedded or active content.",
    "workbook_external_reference": "External workbook links are unsupported. Use a copy without external links.",
    "encrypted_pdf": "Encrypted PDFs are unsupported. Select a permitted, unencrypted copy.",
    "pdf_text_unavailable": "No readable PDF text was found. Scanned pages require a text-based copy.",
    "pdf_active_content": "PDF scripts, automatic actions and embedded attachments are unsupported.",
    "page_limit": "PDF previews support at most 100 pages.",
    "unsupported_format": "Choose a PDF, CSV or XLSX file.",
    "online_permission_required": "Enable online research in Connections before retrieving a URL.",
    "invalid_url": "Use a public HTTPS URL without credentials or authentication parameters.",
    "source_unavailable": "The permitted source could not be retrieved. Redirects and private addresses are not allowed.",
    "queue_full": "The import preview queue is full. Wait for a preview to finish.",
    "worker_limit": "The preview stopped because its processing limit was reached. Try a smaller document.",
    "request_limit": "The preview request is too large or took too long to upload.",
    "storage_permission_required": "Confirm permission to retain this document locally and include it in your backups.",
    "preview_changed": "This document differs from your preview. Preview it again before saving.",
    "storage_unavailable": "The document could not be retained. Check source permissions and the limit of 100 documents or 64 MiB in total.",
    "retained_unavailable": "This retained document is unavailable or no longer passes its integrity and usage checks.",
}


def import_message(error):
    return MESSAGES.get(str(error), "The document could not be safely read. Its format or content may be unsupported.")


def url_candidate(value):
    try:
        source = candidate_metadata(Source(id="import-preview", asset_id="unassigned", url=value, title="Imported URL", publisher="Unverified source"))
        parsed = urlsplit(str(source.url))
        host = (parsed.hostname or "").rstrip(".")
        if parsed.scheme != "https" or parsed.port not in (None, 443) or not host or host.endswith((".localhost", ".local", ".internal")) or host == "localhost":
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if "." not in host:
                raise ValueError() from None
        else:
            if not address.is_global:
                raise ValueError()
        return source
    except (ValueError, TypeError):
        raise ImportFailure("invalid_url") from None


class ImportPreviews:
    def __init__(self, research, *, extractor=extract_document, fetcher=fetch_public_bytes, resolver=public_address):
        self.research, self.extractor, self.fetcher, self.resolver = research, extractor, fetcher, resolver
        self.active = {}

    async def run(self, operation, *, online):
        if len(self.active) >= 20:
            raise ImportFailure("queue_full")
        task = asyncio.create_task(operation())
        self.active[task] = online
        try:
            return await task
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self.active.pop(task, None)

    async def parse(self, raw, format):
        async with self.research.retrieval:
            return await self.extractor(raw, format, permission_confirmed=True)

    async def file(self, raw, format, permission_confirmed):
        if permission_confirmed is not True:
            raise ImportFailure("permission_required")
        if format not in ("csv", "xlsx", "pdf"):
            raise ImportFailure("unsupported_format")
        async def operation():
            document = await self.parse(raw, format)
            return ImportPreview(state="unverified", origin="local_file", document=document, checked_at=now())
        return await self.run(operation, online=False)

    def require_online(self):
        if not self.research.settings().cloud_enabled:
            raise ImportFailure("online_permission_required")

    async def url(self, value):
        preview, _ = await self.url_document(value)
        return preview

    async def url_document(self, value):
        source = url_candidate(value)
        self.require_online()
        async def operation():
            self.require_online()
            try:
                # Validate even link-only targets without downloading their content.
                await self.research.retrieve(self.resolver, urlsplit(str(source.url)).hostname)
                self.require_online()
                if source.policy != SourcePolicy.full_text:
                    return ImportPreview(state="link_only", origin="public_url", source=source, checked_at=now()), None
                raw = await self.research.retrieve(self.fetcher, str(source.url))
                retrieved = now()
                self.require_online()
                document = await self.parse(raw, "html")
                self.require_online()
                # This is a permitted preview, never independent issuer/claim verification.
                preview_source = source.model_copy(update={"retrieved_at": retrieved, "provenance": "user_import",
                    "content_hash": document.content_hash, "excerpt": ""})
                return ImportPreview(state="unverified", origin="public_url", source=preview_source, document=document, checked_at=now()), raw
            except ImportFailure:
                raise
            except RuntimeFailure:
                raise ImportFailure("online_permission_required") from None
            except (ValueError, OSError):
                raise ImportFailure("source_unavailable") from None
        return await self.run(operation, online=True)

    async def close(self, *, online_only=False):
        tasks = [task for task, online in self.active.items() if not online_only or online]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
