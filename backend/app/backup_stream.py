"""File-based portable archives with bounded rows and an owned validation index.

No extraction paths or SQL come from an archive. The caller owns uploaded files;
created archives and scratch indexes live only inside their context managers.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import struct
import zipfile
import zlib
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from backend.app.backup import (
    AttachmentEntry, BackupError, FORMAT, MAX_ARCHIVE_BYTES as LEGACY_LIMIT,
    MAX_MANIFEST_BYTES, StrictModel, read_backup, read_member, restore_allowed, restore_rows,
)
from backend.app.backup_index import TABLES, indexed_snapshot, temporary_index
from backend.app.contracts import BackupSummary, now
from backend.app.retained_imports import MAX_ATTACHMENTS, MAX_ATTACHMENT_BYTES, RetainedImport

MAX_ARCHIVE_BYTES = 64 * 1024**3
MAX_CONTENT_BYTES = 64 * 1024**3
MAX_ROW_BYTES = 64 * 1024**2
MAX_DIRECTORY_BYTES = 256 * 1024
ROW_LIMITS = {"records": 100000, "jobs": 100000, "events": 1000000}
TABLE_PATHS = {name: name + ".ndjson" for name in TABLES}


class TableEntry(StrictModel):
    byte_count: int = Field(ge=0, le=MAX_CONTENT_BYTES)
    row_count: int = Field(ge=0, le=1000000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class StreamManifest(StrictModel):
    format: Literal["learn-the-ticker.library"] = FORMAT
    format_version: Literal["3"] = "3"
    database_revision: Literal["0001"] = "0001"
    application_version: str = "0.2.0"
    created_at: AwareDatetime = Field(default_factory=now)
    credentials_included: Literal[False] = False
    tables: dict[Literal["records", "jobs", "events"], TableEntry]
    attachments: list[AttachmentEntry] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)

    @model_validator(mode="after")
    def valid_members(self):
        if set(self.tables) != set(TABLES) or any(row.row_count > ROW_LIMITS[name] for name, row in self.tables.items()):
            raise ValueError("Archive table counts are invalid")
        if len({item.id for item in self.attachments}) != len(self.attachments):
            raise ValueError("Duplicate archive attachment")
        attachment_bytes = sum(item.byte_count for item in self.attachments)
        if attachment_bytes > MAX_ATTACHMENT_BYTES or attachment_bytes + sum(row.byte_count for row in self.tables.values()) > MAX_CONTENT_BYTES:
            raise ValueError("Archive content exceeds its permitted size")
        return self


class LimitedWriter:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        if self.stream.tell() + len(data) > MAX_ARCHIVE_BYTES:
            raise BackupError("Compressed archive exceeds the 64 GiB limit")
        return self.stream.write(data)

    def tell(self):
        return self.stream.tell()

    def seek(self, *args):
        return self.stream.seek(*args)

    def flush(self):
        return self.stream.flush()


def write_index(index, path):
    """Only call with a validated index and a new application-owned output path."""
    tables, attachments = {}, []
    total = 0
    with path.open("xb") as output, zipfile.ZipFile(LimitedWriter(output), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, member in TABLE_PATHS.items():
            digest, count, size = hashlib.sha256(), 0, 0
            with archive.open(member, "w", force_zip64=True) as stream:
                for row in getattr(index, name).values():
                    if name == "records" and row.kind == "import":
                        item = RetainedImport.model_validate(row.payload)
                        attachments.append(AttachmentEntry(id=item.id, byte_count=item.byte_count, sha256=item.document.content_hash))
                        row.payload.pop("content_base64")
                    data = row.model_dump_json().encode("utf-8") + b"\n"
                    count += 1
                    size += len(data)
                    total += len(data)
                    if len(data) > MAX_ROW_BYTES or count > ROW_LIMITS[name] or total > MAX_CONTENT_BYTES:
                        raise BackupError("Archive rows exceed the permitted size or count")
                    stream.write(data)
                    digest.update(data)
            tables[name] = TableEntry(byte_count=size, row_count=count, sha256=digest.hexdigest())
        for item in attachments:
            content = RetainedImport.model_validate(index.records["import:" + item.id].payload).content()
            total += len(content)
            if total > MAX_CONTENT_BYTES:
                raise BackupError("Archive content exceeds its permitted size")
            archive.writestr(item.path, content)
        manifest = StreamManifest(tables=tables, attachments=attachments)
        raw = manifest.model_dump_json().encode()
        if len(raw) > MAX_MANIFEST_BYTES:
            raise BackupError("Archive manifest exceeds its permitted size")
        archive.writestr("manifest.json", raw)
    return manifest


@contextmanager
def create_backup_file(db):
    with TemporaryDirectory(prefix="ltt-library-archive-") as directory:
        path = Path(directory) / "library.lttbackup"
        try:
            with indexed_snapshot(db) as index:
                write_index(index, path)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, sqlite3.Error) as exc:
            raise BackupError("Library backup could not be completed; no partial archive was published") from exc
        yield path


def check_directory(stream):
    """Bound ZIP directory allocation before ZipFile constructs its entry list.

    Accept ordinary ZIP and the fixed ZIP64 end records produced by ZipFile;
    reject split archives, excessive members, extensions and inconsistent offsets.
    """
    stream.seek(0, 2)
    size = stream.tell()
    if size > MAX_ARCHIVE_BYTES or size < 22:
        raise BackupError("Archive size is invalid")
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise BackupError("Archive directory is missing")
    _, disk, directory_disk, disk_count, count, directory_size, directory_offset, comment = struct.unpack_from("<4s4H2IH", tail, offset)
    end = size - len(tail) + offset
    if offset + 22 + comment != len(tail) or disk or directory_disk or disk_count != count:
        raise BackupError("Archive directory is inconsistent")
    if end >= 20:
        stream.seek(end - 20)
        locator = stream.read(20)
        if locator[:4] == b"PK\x06\x07":
            _, zip_disk, zip_offset, disks = struct.unpack("<4sIQI", locator)
            if zip_disk or disks != 1 or zip_offset + 56 != end - 20:
                raise BackupError("Unsupported ZIP64 directory")
            stream.seek(zip_offset)
            record = stream.read(56)
            signature, record_size, _, _, disk, directory_disk, disk_count, count, directory_size, directory_offset = struct.unpack("<4sQ2H2I4Q", record)
            if signature != b"PK\x06\x06" or record_size != 44 or disk or directory_disk or disk_count != count:
                raise BackupError("Unsupported ZIP64 directory")
            end = zip_offset
    if count > MAX_ATTACHMENTS + 4 or directory_size > MAX_DIRECTORY_BYTES or directory_offset + directory_size != end:
        raise BackupError("Archive directory exceeds its permitted size or is inconsistent")
    stream.seek(0)
    return size


def fingerprint_stream(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_ARCHIVE_BYTES:
            raise BackupError("Archive size changed or exceeds its permitted size")
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def read_tables(archive, manifest, index):
    expected = {"import:" + item.id: item for item in manifest.attachments}
    for name, member in TABLE_PATHS.items():
        entry, digest, size, count = manifest.tables[name], hashlib.sha256(), 0, 0
        if archive.getinfo(member).file_size != entry.byte_count:
            raise BackupError("Archive table size differs from its manifest")
        with archive.open(member) as stream:
            while raw := stream.readline(MAX_ROW_BYTES + 1):
                count += 1
                size += len(raw)
                if len(raw) > MAX_ROW_BYTES or not raw.endswith(b"\n") or count > entry.row_count or size > entry.byte_count:
                    raise BackupError("Archive table rows are oversized or incomplete")
                digest.update(raw)
                row = TABLES[name].model_validate_json(raw)
                if name == "records" and row.kind == "import":
                    item = expected.pop(row.id, None)
                    if (item is None or "content_base64" in row.payload or row.payload.get("byte_count") != item.byte_count
                            or not isinstance(row.payload.get("document"), dict) or row.payload["document"].get("content_hash") != item.sha256):
                        raise BackupError("Retained document reference differs from its manifest")
                    content = read_member(archive, archive.getinfo(item.path), item.byte_count)
                    if len(content) != item.byte_count or hashlib.sha256(content).hexdigest() != item.sha256:
                        raise BackupError("Retained document checksum differs from its manifest")
                    row.payload["content_base64"] = base64.b64encode(content).decode("ascii")
                getattr(index, name).add(row)
        if (count, size, digest.hexdigest()) != (entry.row_count, entry.byte_count, entry.sha256):
            raise BackupError("Archive table checksum or count differs from its manifest")
    if expected:
        raise BackupError("Archive attachment has no retained document")


@contextmanager
def read_backup_file(path):
    with temporary_index() as index:
        try:
            with Path(path).open("rb") as source:
                size = check_directory(source)
                fingerprint = fingerprint_stream(source)
                with zipfile.ZipFile(source) as archive:
                    entries = archive.infolist()
                    names = {entry.filename for entry in entries}
                    if (len(names) != len(entries) or "manifest.json" not in names
                            or any(entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for entry in entries)):
                        raise BackupError("Archive contains duplicate, encrypted or unsupported entries")
                    raw_manifest = read_member(archive, archive.getinfo("manifest.json"), MAX_MANIFEST_BYTES)
                    # Legacy archives retain their original bounded parser and limits.
                    version = json.loads(raw_manifest).get("format_version")
                    if version in ("1", "2"):
                        if size > LEGACY_LIMIT:
                            raise BackupError("Legacy archive exceeds its original size limit")
                        source.seek(0)
                        manifest, data = read_backup(source.read(LEGACY_LIMIT + 1))
                        for name in TABLES:
                            for row in getattr(data, name):
                                getattr(index, name).add(row)
                        del data
                    else:
                        manifest = StreamManifest.model_validate_json(raw_manifest)
                        if names != {"manifest.json", *TABLE_PATHS.values(), *(item.path for item in manifest.attachments)}:
                            raise BackupError("Archive contains unregistered members")
                        if sum(item.file_size for item in entries) > MAX_CONTENT_BYTES + MAX_MANIFEST_BYTES:
                            raise BackupError("Archive expanded contents exceed the permitted size")
                        read_tables(archive, manifest, index)
                index.validate()
                if fingerprint_stream(source) != fingerprint:
                    raise BackupError("Archive changed while it was being validated")
        except BackupError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError, OSError, RuntimeError, EOFError, struct.error, zipfile.BadZipFile, zlib.error, sqlite3.Error) as exc:
            raise BackupError("Invalid or incompatible library archive") from exc
        yield manifest, index, fingerprint


def archive_summary(db, manifest, index, fingerprint):
    counts = Counter(row.kind for row in index.records.values())
    allowed = restore_allowed(db)
    return BackupSummary(format_version=manifest.format_version, created_at=manifest.created_at, fingerprint=fingerprint,
        assets=counts["asset"], evidence_versions=counts["bundle"], conversations=counts["conversation"],
        saved_reports=counts["saved"], term_explanations=counts["term"], retained_imports=counts["import"],
        import_explanations=counts["import_explanation"], comparisons=counts["comparison"], dated_reports=counts["report"],
        attachment_bytes=sum(item.byte_count for item in manifest.attachments), jobs=len(index.jobs), can_restore=allowed,
        reason=None if allowed else "Restore requires an empty library. Keep this installation intact and restore into a new library to preserve newer research.")


def preview_backup_file(db, path):
    with read_backup_file(path) as (manifest, index, fingerprint):
        return archive_summary(db, manifest, index, fingerprint)


def restore_backup_file(db, path, fingerprint):
    with read_backup_file(path) as (manifest, index, actual):
        if not fingerprint or fingerprint != actual:
            raise BackupError("The selected archive changed after preview; validate it again")
        summary = archive_summary(db, manifest, index, actual)
        if not summary.can_restore:
            raise BackupError(summary.reason)
        restore_rows(db, index.records.values(), index.jobs.values(), index.events.values())
        return summary
