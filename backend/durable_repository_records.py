from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION = "durable-repository-records-v1"
DURABLE_REPOSITORY_RECORD_TABLE = "durable_repository_records"
DURABLE_REPOSITORY_RECORD_TABLES = (DURABLE_REPOSITORY_RECORD_TABLE,)
_FORBIDDEN_PAYLOAD_MARKERS = (
    "authorization:",
    "bearer ",
    '"api_key"',
    '"raw_provider_payload_stored":true',
    '"raw_article_text_stored":true',
    '"raw_provider_payload":',
    '"raw_article_body":',
    '"hidden_prompt":',
    '"raw_model_reasoning":',
    '"secrets_stored":true',
    '"secret_values_stored":true',
)


class DurableRepositoryRecordError(ValueError):
    """Raised when durable repository record storage would break local safety rules."""


@dataclass(frozen=True)
class DurableRepositoryRecordSummary:
    collection: str
    record_key: str
    payload_checksum: str
    model_type: str
    updated_at: str


class DurableRepositoryRecordSession:
    """SQLite-backed implementation of the repository session protocol.

    Repository classes validate their domain-specific records before calling this
    session. This adapter stores that validated payload durably so configured
    local repositories can be restarted and read back through the same
    `get_repository_record(collection, key)` boundary used by in-memory tests.
    """

    def __init__(self, database_path: str | Path, *, initialize_schema: bool = True) -> None:
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        if initialize_schema:
            execute_durable_repository_record_schema(self._connection)

    @classmethod
    def from_database_url(cls, database_url: str, *, initialize_schema: bool = True) -> "DurableRepositoryRecordSession":
        return cls(_sqlite_path_from_database_url(database_url), initialize_schema=initialize_schema)

    def save_repository_record(self, collection: str, key: str, records: Any) -> DurableRepositoryRecordSummary:
        normalized_collection = _safe_identifier(collection, "collection")
        normalized_key = _safe_identifier(key, "record_key")
        payload = _jsonable_payload(records)
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        _assert_safe_payload(payload_json)
        payload_checksum = f"sha256:{hashlib.sha256(payload_json.encode('utf-8')).hexdigest()}"
        now = _utc_now()
        model_type = f"{type(records).__module__}.{type(records).__name__}"
        self._connection.execute(
            f"""
            insert into {DURABLE_REPOSITORY_RECORD_TABLE}
                (collection, record_key, schema_version, model_type, payload_json, payload_checksum, created_at, updated_at)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(collection, record_key) do update set
                schema_version=excluded.schema_version,
                model_type=excluded.model_type,
                payload_json=excluded.payload_json,
                payload_checksum=excluded.payload_checksum,
                updated_at=excluded.updated_at
            """,
            (
                normalized_collection,
                normalized_key,
                DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION,
                model_type,
                payload_json,
                payload_checksum,
                now,
                now,
            ),
        )
        return DurableRepositoryRecordSummary(
            collection=normalized_collection,
            record_key=normalized_key,
            payload_checksum=payload_checksum,
            model_type=model_type,
            updated_at=now,
        )

    def get_repository_record(self, collection: str, key: str) -> Any | None:
        row = self._connection.execute(
            f"""
            select schema_version, payload_json
            from {DURABLE_REPOSITORY_RECORD_TABLE}
            where collection = ? and record_key = ?
            """,
            (_safe_identifier(collection, "collection"), _safe_identifier(key, "record_key")),
        ).fetchone()
        if row is None:
            return None
        if row["schema_version"] != DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION:
            return None
        return json.loads(row["payload_json"])

    def read_repository_record(self, collection: str, key: str) -> Any | None:
        return self.get_repository_record(collection, key)

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def execute_durable_repository_record_schema(connection: sqlite3.Connection) -> tuple[str, ...]:
    connection.execute(
        f"""
        create table if not exists {DURABLE_REPOSITORY_RECORD_TABLE} (
            collection text not null,
            record_key text not null,
            schema_version text not null,
            model_type text not null,
            payload_json text not null,
            payload_checksum text not null,
            created_at text not null,
            updated_at text not null,
            primary key (collection, record_key)
        )
        """
    )
    connection.execute(
        f"""
        create index if not exists ix_{DURABLE_REPOSITORY_RECORD_TABLE}_updated_at
        on {DURABLE_REPOSITORY_RECORD_TABLE} (updated_at)
        """
    )
    connection.commit()
    return DURABLE_REPOSITORY_RECORD_TABLES


def inspect_durable_repository_record_schema(connection: sqlite3.Connection) -> dict[str, list[str]]:
    rows = connection.execute(
        "select name from sqlite_master where type = 'table' and name = ?",
        (DURABLE_REPOSITORY_RECORD_TABLE,),
    ).fetchall()
    if not rows:
        return {}
    columns = [
        str(row["name"] if isinstance(row, sqlite3.Row) else row[1])
        for row in connection.execute(f"pragma table_info({DURABLE_REPOSITORY_RECORD_TABLE})").fetchall()
    ]
    return {DURABLE_REPOSITORY_RECORD_TABLE: columns}


def _jsonable_payload(records: Any) -> Any:
    if hasattr(records, "model_dump"):
        return records.model_dump(mode="json")
    return json.loads(json.dumps(records, sort_keys=True, default=str))


def _assert_safe_payload(payload_json: str) -> None:
    lowered = payload_json.lower()
    for marker in _FORBIDDEN_PAYLOAD_MARKERS:
        if marker in lowered:
            raise DurableRepositoryRecordError("Durable repository records must not store raw secrets or payloads.")


def _safe_identifier(value: str, label: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise DurableRepositoryRecordError(f"{label} is required.")
    if len(cleaned) > 240:
        raise DurableRepositoryRecordError(f"{label} is too long for durable repository record storage.")
    if any(character in cleaned for character in ("\x00", "\n", "\r")):
        raise DurableRepositoryRecordError(f"{label} contains an unsafe control character.")
    return cleaned


def _sqlite_path_from_database_url(database_url: str) -> Path:
    parsed = urlsplit(database_url)
    if parsed.scheme != "sqlite":
        raise DurableRepositoryRecordError("Only sqlite DATABASE_URL values can use the local durable record session.")
    if parsed.netloc and parsed.netloc not in {"", "localhost"}:
        raise DurableRepositoryRecordError("SQLite durable record URLs must use a local filesystem path.")
    if parsed.path in {"", "/"}:
        raise DurableRepositoryRecordError("SQLite durable record URLs require a database path.")
    return Path(unquote(parsed.path))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
