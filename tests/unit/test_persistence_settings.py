from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from backend import db
from backend.persistence import persistence_metadata_diagnostics, target_metadata
from backend.persistence import (
    LOCAL_DURABLE_REPOSITORY_FACTORY_BOUNDARY,
    build_backend_read_dependencies_from_local_durable_config,
    build_local_durable_repository_factories,
)
from backend.ingestion import request_ingestion
from backend.settings import (
    INVALID_LOCAL_DURABLE_OBJECT_NAMESPACE_REASON,
    LOCAL_DURABLE_DISABLED_REASON,
    LIVE_ETF_ISSUER_ACQUISITION_DISABLED_REASON,
    LIVE_KNOWLEDGE_PACK_WRITER_MISSING_REASON,
    LIVE_SEC_SOURCE_CONFIGURATION_MISSING_REASON,
    LIVE_SEC_STOCK_ACQUISITION_DISABLED_REASON,
    LIVE_SOURCE_RATE_LIMIT_NOT_READY_REASON,
    LIVE_SOURCE_SNAPSHOT_WRITER_MISSING_REASON,
    LIVE_WEEKLY_NEWS_ACQUISITION_DISABLED_REASON,
    LIVE_WEEKLY_NEWS_SOURCE_CONFIGURATION_MISSING_REASON,
    LIVE_WEEKLY_NEWS_WRITER_MISSING_REASON,
    MISSING_DATABASE_URL_REASON,
    build_live_acquisition_settings,
    build_local_durable_repository_settings,
    build_persistence_settings,
    offline_migration_database_url,
    redact_database_url,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeDurableSession:
    def __init__(self):
        self.records = {}
        self.rows = []
        self.commits = 0

    def save_repository_record(self, collection, key, records):
        self.records[(collection, key)] = records

    def get_repository_record(self, collection, key):
        return self.records.get((collection, key))

    def add_all(self, rows):
        self.rows.extend(rows)

    def commit(self):
        self.commits += 1


def test_persistence_settings_default_to_missing_config_without_secrets():
    settings = build_persistence_settings(env={})

    assert settings.database_url_configured is False
    assert settings.status == "missing_config"
    assert MISSING_DATABASE_URL_REASON in settings.missing_reasons
    assert settings.database_url_redacted is None
    assert settings.connect_timeout_seconds == 5
    assert settings.safe_diagnostics["database_url_configured"] is False
    assert "DATABASE_URL" not in str(settings.safe_diagnostics)


def test_database_url_redaction_hides_credentials_and_sensitive_query_values():
    raw_url = (
        "postgresql+psycopg://app_user:super-secret-password@db.internal:5432/learn_the_ticker"
        "?sslmode=require&password=query-secret&application_name=learn-the-ticker"
    )
    settings = build_persistence_settings(
        env={
            "DATABASE_URL": raw_url,
            "DATABASE_CONNECT_TIMEOUT_SECONDS": "7",
            "DATABASE_POOL_PRE_PING": "true",
            "DATABASE_ECHO_SQL": "false",
            "DATABASE_MIGRATIONS_ENABLED": "false",
        }
    )
    diagnostics = settings.safe_diagnostics
    serialized = str(diagnostics)

    assert settings.database_url_configured is True
    assert diagnostics["status"] == "configured"
    assert diagnostics["database_driver"] == "postgresql+psycopg"
    assert diagnostics["database_host"] == "db.internal"
    assert diagnostics["database_name"] == "learn_the_ticker"
    assert diagnostics["connect_timeout_seconds"] == 7
    assert diagnostics["pool_pre_ping"] is True
    assert "<credentials>@db.internal:5432" in settings.database_url_redacted
    assert "password=%3Credacted%3E" in settings.database_url_redacted
    assert "super-secret-password" not in serialized
    assert "query-secret" not in serialized
    assert "app_user" not in serialized
    assert raw_url not in serialized


def test_redact_database_url_handles_missing_or_invalid_values():
    assert redact_database_url(None) is None
    assert redact_database_url("") is None
    assert redact_database_url("not a url") == "<redacted-database-url>"


def test_database_engine_factory_is_lazy_and_sanitized(monkeypatch):
    raw_url = "postgresql+psycopg://app_user:secret@db.internal:5432/learn_the_ticker"
    settings = build_persistence_settings(env={"DATABASE_URL": raw_url})
    factory = db.build_engine_factory(settings)
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_create_engine(url: str, **kwargs):
        calls.append((url, kwargs))
        return {"engine": "fake"}

    monkeypatch.setattr(db, "_load_sqlalchemy_create_engine", lambda: fake_create_engine)

    assert calls == []
    diagnostics = factory.safe_diagnostics
    assert diagnostics["lazy"] is True
    assert diagnostics["opens_connection_on_import"] is False
    assert "secret" not in str(diagnostics)

    engine = factory.create_engine()

    assert engine == {"engine": "fake"}
    assert calls == [
        (
            raw_url,
            {
                "future": True,
                "pool_pre_ping": False,
                "echo": False,
                "connect_args": {"connect_timeout": 5},
            },
        )
    ]


def test_database_engine_factory_rejects_missing_url_without_importing_sqlalchemy(monkeypatch):
    settings = build_persistence_settings(env={})
    factory = db.build_engine_factory(settings)

    def fail_loader():
        raise AssertionError("SQLAlchemy should not be imported when DATABASE_URL is missing")

    monkeypatch.setattr(db, "_load_sqlalchemy_create_engine", fail_loader)

    with pytest.raises(db.PersistenceConfigurationError):
        factory.create_engine()


def test_local_durable_repository_settings_default_to_disabled_fallback():
    settings = build_local_durable_repository_settings(env={})

    assert settings.enabled is False
    assert settings.can_construct is False
    assert settings.status == "disabled"
    assert LOCAL_DURABLE_DISABLED_REASON in settings.missing_reasons
    assert settings.safe_diagnostics["database_url_configured"] is False
    assert "DATABASE_URL" not in str(settings.safe_diagnostics)


def test_local_durable_repository_settings_are_explicit_and_sanitized():
    raw_url = "postgresql+psycopg://app_user:secret@localhost:5432/learn_the_ticker?password=query-secret"
    settings = build_local_durable_repository_settings(
        env={
            "LOCAL_DURABLE_REPOSITORIES_ENABLED": "true",
            "LOCAL_DURABLE_OBJECT_NAMESPACE": "local-private-source-artifacts",
            "LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE": "true",
            "DATABASE_URL": raw_url,
        }
    )
    serialized = str(settings.safe_diagnostics)

    assert settings.enabled is True
    assert settings.can_construct is True
    assert settings.status == "configured"
    assert settings.object_namespace == "local-private-source-artifacts"
    assert settings.commit_on_write is True
    assert "<credentials>@localhost:5432" in serialized
    assert "secret" not in serialized
    assert "app_user" not in serialized
    assert raw_url not in serialized


def test_local_durable_repository_settings_reject_public_or_signed_storage_namespaces():
    settings = build_local_durable_repository_settings(
        env={
            "LOCAL_DURABLE_REPOSITORIES_ENABLED": "true",
            "DATABASE_URL": "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker",
            "LOCAL_DURABLE_OBJECT_NAMESPACE": "https://storage.example/public/snapshots?signature=abc",
        }
    )

    assert settings.can_construct is False
    assert settings.status == "invalid_config"
    assert INVALID_LOCAL_DURABLE_OBJECT_NAMESPACE_REASON in settings.invalid_reasons


def test_live_acquisition_settings_default_to_blocked_and_sanitized():
    settings = build_live_acquisition_settings(env={})

    assert settings.status == "blocked"
    assert settings.sec_stock_ready is False
    assert settings.etf_issuer_ready is False
    assert settings.weekly_news_ready is False
    assert LIVE_SEC_STOCK_ACQUISITION_DISABLED_REASON in settings.missing_reasons
    assert LIVE_ETF_ISSUER_ACQUISITION_DISABLED_REASON in settings.missing_reasons
    assert LIVE_WEEKLY_NEWS_ACQUISITION_DISABLED_REASON in settings.missing_reasons
    serialized = str(settings.safe_diagnostics)
    assert "API_KEY" not in serialized
    assert "DATABASE_URL" not in serialized
    assert "secret" not in serialized.lower()


def test_live_acquisition_settings_require_source_rate_limit_and_writer_readiness():
    missing = build_live_acquisition_settings(
        env={
            "LIVE_SEC_STOCK_ACQUISITION_ENABLED": "true",
            "LIVE_ETF_ISSUER_ACQUISITION_ENABLED": "false",
        }
    )

    assert missing.sec_stock_ready is False
    assert LIVE_SEC_SOURCE_CONFIGURATION_MISSING_REASON in missing.missing_reasons
    assert LIVE_SOURCE_RATE_LIMIT_NOT_READY_REASON in missing.missing_reasons
    assert LIVE_SOURCE_SNAPSHOT_WRITER_MISSING_REASON in missing.missing_reasons
    assert LIVE_KNOWLEDGE_PACK_WRITER_MISSING_REASON in missing.missing_reasons

    ready = build_live_acquisition_settings(
        env={
            "LIVE_SEC_STOCK_ACQUISITION_ENABLED": "true",
            "LIVE_ETF_ISSUER_ACQUISITION_ENABLED": "true",
            "LIVE_SEC_SOURCE_CONFIGURED": "true",
            "LIVE_ETF_ISSUER_SOURCE_CONFIGURED": "true",
            "LIVE_SOURCE_RATE_LIMIT_READY": "true",
            "LIVE_ACQUISITION_SOURCE_SNAPSHOT_WRITER_READY": "true",
            "LIVE_ACQUISITION_KNOWLEDGE_PACK_WRITER_READY": "true",
        }
    )

    assert ready.status == "configured"
    assert ready.sec_stock_ready is True
    assert ready.etf_issuer_ready is True
    assert ready.weekly_news_ready is False
    assert ready.generated_output_cache_writer_ready is False

    weekly_missing = build_live_acquisition_settings(
        env={
            "LIVE_WEEKLY_NEWS_ACQUISITION_ENABLED": "true",
        }
    )
    assert weekly_missing.weekly_news_ready is False
    assert LIVE_WEEKLY_NEWS_SOURCE_CONFIGURATION_MISSING_REASON in weekly_missing.missing_reasons
    assert LIVE_SOURCE_RATE_LIMIT_NOT_READY_REASON in weekly_missing.missing_reasons
    assert LIVE_WEEKLY_NEWS_WRITER_MISSING_REASON in weekly_missing.missing_reasons

    weekly_ready = build_live_acquisition_settings(
        env={
            "LIVE_WEEKLY_NEWS_ACQUISITION_ENABLED": "true",
            "LIVE_WEEKLY_NEWS_OFFICIAL_SOURCE_CONFIGURED": "true",
            "LIVE_SOURCE_RATE_LIMIT_READY": "true",
            "LIVE_ACQUISITION_WEEKLY_NEWS_WRITER_READY": "true",
        }
    )
    assert weekly_ready.status == "configured"
    assert weekly_ready.weekly_news_ready is True
    assert weekly_ready.sec_stock_ready is False
    assert weekly_ready.etf_issuer_ready is False


def test_local_durable_repository_factories_are_lazy_and_build_configured_readers():
    raw_url = "postgresql+psycopg://app_user:secret@localhost:5432/learn_the_ticker"
    sessions: list[FakeDurableSession] = []

    def session_factory():
        session = FakeDurableSession()
        sessions.append(session)
        return session

    factories = build_local_durable_repository_factories(
        env={
            "LOCAL_DURABLE_REPOSITORIES_ENABLED": "true",
            "DATABASE_URL": raw_url,
            "LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE": "true",
        },
        session_factory=session_factory,
    )

    assert factories.boundary == LOCAL_DURABLE_REPOSITORY_FACTORY_BOUNDARY
    assert factories.active is True
    assert sessions == []
    assert factories.safe_diagnostics["opens_connection_on_import"] is False
    assert "secret" not in str(factories.safe_diagnostics)

    dependencies = factories.build_backend_read_dependencies()

    assert dependencies.active is True
    assert sessions == []
    assert dependencies.knowledge_pack_reader is not None
    assert dependencies.generated_output_cache_reader is not None
    assert dependencies.weekly_news_reader is not None
    assert dependencies.ingestion_job_ledger is not None
    assert dependencies.source_snapshot_repository is not None
    assert dependencies.safe_diagnostics["source_snapshot_repository_configured"] is True

    dependencies.ingestion_job_ledger.save(
        dependencies.ingestion_job_ledger.serialize_response(request_ingestion("SPY"))
    )

    assert len(sessions) == 1
    assert sessions[0].commits == 1


def test_backend_read_dependencies_fall_back_when_local_durable_config_is_absent_or_invalid():
    disabled = build_backend_read_dependencies_from_local_durable_config(env={})
    invalid = build_backend_read_dependencies_from_local_durable_config(
        env={
            "LOCAL_DURABLE_REPOSITORIES_ENABLED": "true",
            "DATABASE_URL": "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker",
            "LOCAL_DURABLE_OBJECT_NAMESPACE": "public/snapshots",
        },
        session_factory=FakeDurableSession,
    )

    assert disabled.active is False
    assert invalid.active is False


def test_persistence_metadata_boundary_is_dormant():
    diagnostics = persistence_metadata_diagnostics()

    assert diagnostics["boundary"] == "persistence-metadata-boundary-v1"
    assert diagnostics["dormant"] is True
    assert diagnostics["table_count"] == 0
    assert len(target_metadata.tables) == 0


def test_alembic_scaffold_is_present_and_dormant():
    required_paths = [
        "alembic.ini",
        "alembic/env.py",
        "alembic/script.py.mako",
        "alembic/versions/20260425_0001_persistence_baseline.py",
    ]

    for path in required_paths:
        assert (ROOT / path).exists(), f"{path} should exist"

    alembic_ini = (ROOT / "alembic.ini").read_text(encoding="utf-8")
    env_py = (ROOT / "alembic/env.py").read_text(encoding="utf-8")
    revision_py = (ROOT / "alembic/versions/20260425_0001_persistence_baseline.py").read_text(encoding="utf-8")

    assert "script_location = alembic" in alembic_ini
    assert "target_metadata" in env_py
    assert "offline_migration_database_url" in env_py
    assert "build_engine_factory(settings).create_engine()" in env_py
    assert "op.create_table" not in revision_py
    assert "create_table" not in revision_py
    assert "knowledge_pack" not in revision_py
    assert "chat" not in revision_py
    assert "cache" not in revision_py
    assert "source" not in revision_py


def test_baseline_revision_imports_without_alembic_or_database_connection():
    revision_path = ROOT / "alembic/versions/20260425_0001_persistence_baseline.py"
    spec = importlib.util.spec_from_file_location("baseline_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0001"
    assert module.down_revision is None
    assert module.upgrade() is None
    assert module.downgrade() is None


def test_offline_migration_url_has_deterministic_placeholder_without_env():
    settings = build_persistence_settings(env={})

    assert offline_migration_database_url(settings) == (
        "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker"
    )


def test_offline_migration_url_never_returns_configured_secret():
    settings = build_persistence_settings(
        env={"DATABASE_URL": "postgresql+psycopg://app_user:secret@db.internal:5432/learn_the_ticker"}
    )

    offline_url = offline_migration_database_url(settings)

    assert offline_url == "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker"
    assert "secret" not in offline_url
    assert "app_user" not in offline_url


def test_database_env_placeholders_are_server_side_only():
    root_env = (ROOT / ".env.example").read_text(encoding="utf-8")
    api_env = (ROOT / "deploy/env/api.example.env").read_text(encoding="utf-8")
    worker_env = (ROOT / "deploy/env/worker.example.env").read_text(encoding="utf-8")
    web_env = (ROOT / "apps/web/.env.example").read_text(encoding="utf-8")

    for text in [root_env, api_env, worker_env]:
        assert "DATABASE_URL" in text
        assert "DATABASE_CONNECT_TIMEOUT_SECONDS" in text
        assert "DATABASE_POOL_PRE_PING" in text
        assert "DATABASE_ECHO_SQL" in text
        assert "DATABASE_MIGRATIONS_ENABLED" in text

    assert "NEXT_PUBLIC_DATABASE_URL" not in web_env
    assert "DATABASE_URL" not in web_env
