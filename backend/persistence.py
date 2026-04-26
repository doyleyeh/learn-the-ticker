from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from backend.settings import LocalDurableRepositorySettings, build_local_durable_repository_settings


PERSISTENCE_METADATA_BOUNDARY = "persistence-metadata-boundary-v1"
PERSISTENCE_METADATA_NOTE = (
    "Dormant metadata boundary only. Current asset, retrieval, generation, chat, "
    "comparison, export, cache, and ingestion behavior remains fixture-backed."
)
BACKEND_READ_DEPENDENCIES_SCHEMA_VERSION = "backend-configured-readers-v1"
BACKEND_READ_DEPENDENCIES_APP_STATE_KEY = "learn_the_ticker_read_dependencies"
LOCAL_DURABLE_REPOSITORY_FACTORY_BOUNDARY = "local-durable-repository-factory-boundary-v1"
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
    ingestion_job_ledger: Any | None = field(default=None, repr=False, compare=False)
    source_snapshot_repository: Any | None = field(default=None, repr=False, compare=False)
    diagnostics: dict[str, object] = field(default_factory=dict, repr=False, compare=False)

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
                self.ingestion_job_ledger,
                self.source_snapshot_repository,
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
            "ingestion_job_ledger_configured": self.ingestion_job_ledger is not None,
            "source_snapshot_repository_configured": self.source_snapshot_repository is not None,
            "no_database_connection_opened": True,
            "diagnostics": self.diagnostics,
        }


def default_backend_read_dependencies() -> BackendReadDependencies:
    return BackendReadDependencies()


@dataclass(frozen=True)
class LocalDurableRepositoryFactories:
    settings: LocalDurableRepositorySettings
    session_factory: Callable[[], Any] | None = field(default=None, repr=False, compare=False)
    engine_factory: Any | None = field(default=None, repr=False, compare=False)
    boundary: str = LOCAL_DURABLE_REPOSITORY_FACTORY_BOUNDARY

    @property
    def active(self) -> bool:
        return self.settings.can_construct and (self.session_factory is not None or self.engine_factory is not None)

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "boundary": self.boundary,
            "active": self.active,
            "lazy": True,
            "opens_connection_on_import": False,
            "constructs_repository_factories_only": True,
            "settings": self.settings.safe_diagnostics,
        }

    def build_ingestion_job_ledger(self) -> Any:
        from backend.ingestion_job_repository import IngestionJobLedgerRepository

        return IngestionJobLedgerRepository(session=self._session(), commit_on_write=self.settings.commit_on_write)

    def build_source_snapshot_repository(self) -> Any:
        from backend.source_snapshot_repository import SourceSnapshotArtifactRepository

        return SourceSnapshotArtifactRepository(session=self._session(), commit_on_write=self.settings.commit_on_write)

    def build_knowledge_pack_repository(self) -> Any:
        from backend.knowledge_pack_repository import AssetKnowledgePackRepository

        return AssetKnowledgePackRepository(session=self._session(), commit_on_write=self.settings.commit_on_write)

    def build_weekly_news_repository(self) -> Any:
        from backend.weekly_news_repository import WeeklyNewsEventEvidenceRepository

        return WeeklyNewsEventEvidenceRepository(session=self._session(), commit_on_write=self.settings.commit_on_write)

    def build_generated_output_cache_repository(self) -> Any:
        from backend.generated_output_cache_repository import GeneratedOutputCacheRepository

        return GeneratedOutputCacheRepository(session=self._session(), commit_on_write=self.settings.commit_on_write)

    def build_backend_read_dependencies(self) -> BackendReadDependencies:
        if not self.active:
            return default_backend_read_dependencies()
        knowledge_pack_repository = self.build_knowledge_pack_repository()
        generated_output_cache_repository = self.build_generated_output_cache_repository()
        weekly_news_repository = self.build_weekly_news_repository()
        ingestion_job_ledger = self.build_ingestion_job_ledger()
        source_snapshot_repository = self.build_source_snapshot_repository()
        return BackendReadDependencies(
            persisted_reads_enabled=True,
            knowledge_pack_reader=knowledge_pack_repository,
            generated_output_cache_reader=generated_output_cache_repository,
            weekly_news_reader=weekly_news_repository,
            ingestion_job_ledger=ingestion_job_ledger,
            source_snapshot_repository=source_snapshot_repository,
            diagnostics=self.safe_diagnostics,
        )

    def _session(self) -> Any:
        if not self.active:
            raise RuntimeError("Local durable repository factories are not active.")
        return _LazyDurableSession(self._session_factory())

    def _session_factory(self) -> Callable[[], Any]:
        if self.session_factory is not None:
            return self.session_factory
        if self.engine_factory is not None:
            return self.engine_factory.create_session
        raise RuntimeError("No local durable session factory is configured.")


@dataclass
class _LazyDurableSession:
    session_factory: Callable[[], Any] = field(repr=False)
    _session: Any | None = field(default=None, init=False, repr=False)

    def save_repository_record(self, collection: str, key: str, records: Any) -> Any:
        return self._delegate("save_repository_record", collection, key, records)

    def read_repository_record(self, collection: str, key: str) -> Any | None:
        if hasattr(self._session_or_create(), "read_repository_record"):
            return self._delegate("read_repository_record", collection, key)
        if hasattr(self._session_or_create(), "get_repository_record"):
            return self._delegate("get_repository_record", collection, key)
        if hasattr(self._session_or_create(), "get"):
            return self._delegate("get", collection, key)
        return None

    def get_repository_record(self, collection: str, key: str) -> Any | None:
        return self.read_repository_record(collection, key)

    def add_all(self, rows: list[Any]) -> Any:
        return self._delegate("add_all", rows)

    def commit(self) -> Any:
        if hasattr(self._session_or_create(), "commit"):
            return self._delegate("commit")
        return None

    def _delegate(self, method_name: str, *args: Any) -> Any:
        session = self._session_or_create()
        if not hasattr(session, method_name):
            raise AttributeError(method_name)
        return getattr(session, method_name)(*args)

    def _session_or_create(self) -> Any:
        if self._session is None:
            self._session = self.session_factory()
        return self._session


def build_local_durable_repository_factories(
    *,
    env: dict[str, str] | None = None,
    settings: LocalDurableRepositorySettings | None = None,
    session_factory: Callable[[], Any] | None = None,
    engine_factory: Any | None = None,
) -> LocalDurableRepositoryFactories:
    local_settings = settings or build_local_durable_repository_settings(env=env)
    resolved_engine_factory = engine_factory
    if resolved_engine_factory is None and session_factory is None and local_settings.can_construct:
        try:
            from backend.db import build_engine_factory

            resolved_engine_factory = build_engine_factory(local_settings.database)
        except Exception:
            resolved_engine_factory = None
    return LocalDurableRepositoryFactories(
        settings=local_settings,
        session_factory=session_factory,
        engine_factory=resolved_engine_factory,
    )


def build_backend_read_dependencies_from_local_durable_config(
    *,
    env: dict[str, str] | None = None,
    session_factory: Callable[[], Any] | None = None,
    engine_factory: Any | None = None,
) -> BackendReadDependencies:
    factories = build_local_durable_repository_factories(
        env=env,
        session_factory=session_factory,
        engine_factory=engine_factory,
    )
    if not factories.active:
        return default_backend_read_dependencies()
    try:
        return factories.build_backend_read_dependencies()
    except Exception:
        return default_backend_read_dependencies()


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
