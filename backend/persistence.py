from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PERSISTENCE_METADATA_BOUNDARY = "persistence-metadata-boundary-v1"
PERSISTENCE_METADATA_NOTE = (
    "Dormant metadata boundary only. Current asset, retrieval, generation, chat, "
    "comparison, export, cache, and ingestion behavior remains fixture-backed."
)
BACKEND_READ_DEPENDENCIES_SCHEMA_VERSION = "backend-configured-readers-v1"
BACKEND_READ_DEPENDENCIES_APP_STATE_KEY = "learn_the_ticker_read_dependencies"
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


@dataclass(frozen=True)
class BackendReadDependencies:
    schema_version: str = BACKEND_READ_DEPENDENCIES_SCHEMA_VERSION
    persisted_reads_enabled: bool = False
    knowledge_pack_reader: Any | None = field(default=None, repr=False, compare=False)
    generated_output_cache_reader: Any | None = field(default=None, repr=False, compare=False)
    weekly_news_reader: Any | None = field(default=None, repr=False, compare=False)
    chat_session_reader: Any | None = field(default=None, repr=False, compare=False)
    chat_session_writer: Any | None = field(default=None, repr=False, compare=False)

    @property
    def active(self) -> bool:
        return self.persisted_reads_enabled and any(
            reader is not None
            for reader in [
                self.knowledge_pack_reader,
                self.generated_output_cache_reader,
                self.weekly_news_reader,
                self.chat_session_reader,
                self.chat_session_writer,
            ]
        )

    def reader(self, name: str) -> Any | None:
        if not self.active:
            return None
        return getattr(self, name)

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "persisted_reads_enabled": self.persisted_reads_enabled,
            "active": self.active,
            "knowledge_pack_reader_configured": self.knowledge_pack_reader is not None,
            "generated_output_cache_reader_configured": self.generated_output_cache_reader is not None,
            "weekly_news_reader_configured": self.weekly_news_reader is not None,
            "chat_session_reader_configured": self.chat_session_reader is not None,
            "chat_session_writer_configured": self.chat_session_writer is not None,
            "no_database_connection_opened": True,
        }


def default_backend_read_dependencies() -> BackendReadDependencies:
    return BackendReadDependencies()


def configure_backend_read_dependencies(app: Any, dependencies: BackendReadDependencies | None) -> None:
    if not hasattr(app, "state"):
        return
    setattr(app.state, BACKEND_READ_DEPENDENCIES_APP_STATE_KEY, dependencies or default_backend_read_dependencies())


def backend_read_dependencies_from_app(app: Any) -> BackendReadDependencies:
    state = getattr(app, "state", None)
    dependencies = getattr(state, BACKEND_READ_DEPENDENCIES_APP_STATE_KEY, None) if state is not None else None
    if isinstance(dependencies, BackendReadDependencies):
        return dependencies
    return default_backend_read_dependencies()


try:
    from sqlalchemy import MetaData
except ModuleNotFoundError:  # pragma: no cover - exercised when dependencies are not installed.

    class _DormantMetadata:
        def __init__(self) -> None:
            self.naming_convention = NAMING_CONVENTION
            self.tables: dict[str, object] = {}

    target_metadata = _DormantMetadata()
else:
    target_metadata = MetaData(naming_convention=NAMING_CONVENTION)


def persistence_metadata_diagnostics() -> dict[str, object]:
    return {
        "boundary": PERSISTENCE_METADATA_BOUNDARY,
        "note": PERSISTENCE_METADATA_NOTE,
        "table_count": len(target_metadata.tables),
        "dormant": True,
    }
