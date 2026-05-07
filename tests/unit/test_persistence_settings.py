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
    CORS_SETTINGS_SCHEMA_VERSION,
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
    LIGHTWEIGHT_DATA_SETTINGS_SCHEMA_VERSION,
    LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON,
    LIGHTWEIGHT_WEEKLY_NEWS_FETCH_DISABLED_REASON,
    MARKET_NEWS_FETCH_DISABLED_REASON,
    MARKET_NEWS_LIVE_SOURCE_SMOKE_DISABLED_REASON,
    MISSING_DATABASE_URL_REASON,
    build_cors_settings,
    build_lightweight_data_settings,
    build_live_acquisition_settings,
    build_local_durable_repository_settings,
    build_market_news_settings,
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


def test_cors_settings_default_to_local_web_origins_and_are_sanitized():
    settings = build_cors_settings(env={})

    assert settings.schema_version == CORS_SETTINGS_SCHEMA_VERSION
    assert settings.enabled is True
    assert settings.allowed_origins == ("http://localhost:3000", "http://127.0.0.1:3000")
    assert settings.allowed_methods == ("GET", "POST", "OPTIONS")
    assert settings.allow_credentials is False
    assert settings.safe_diagnostics["enabled"] is True
    assert "API_KEY" not in str(settings.safe_diagnostics)


def test_cors_settings_parse_explicit_origin_list_and_allow_disabled_empty_value():
    configured = build_cors_settings(
        env={"CORS_ALLOWED_ORIGINS": "https://example.vercel.app, http://localhost:3000"}
    )
    disabled = build_cors_settings(env={"CORS_ALLOWED_ORIGINS": " "})

    assert configured.allowed_origins == ("https://example.vercel.app", "http://localhost:3000")
    assert configured.enabled is True
    assert disabled.allowed_origins == ()
    assert disabled.enabled is False


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


def test_lightweight_data_settings_empty_env_and_pytest_default_to_no_live():
    settings = build_lightweight_data_settings(env={})

    assert settings.schema_version == LIGHTWEIGHT_DATA_SETTINGS_SCHEMA_VERSION
    assert settings.data_policy_mode == "lightweight"
    assert settings.lightweight_enabled is True
    assert settings.live_fetch_enabled is False
    assert settings.provider_fallback_enabled is True
    assert settings.weekly_news_fetch_enabled is False
    assert settings.provider_order == ("fmp", "alpha_vantage", "finnhub", "tiingo", "eodhd", "yahoo")
    assert settings.provider_source_use_reviewed is False
    assert settings.can_fetch_fresh_data is False
    assert LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON in settings.missing_reasons
    assert LIGHTWEIGHT_WEEKLY_NEWS_FETCH_DISABLED_REASON in settings.missing_reasons
    serialized = str(settings.safe_diagnostics)
    assert "test@example.com" not in serialized
    assert "API_KEY" not in serialized

    pytest_default = build_lightweight_data_settings(env={"DATA_POLICY_MODE": "lightweight"})
    assert pytest_default.live_fetch_enabled is False
    assert pytest_default.provider_fallback_enabled is True
    assert pytest_default.can_fetch_fresh_data is False
    assert LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON in pytest_default.missing_reasons


def test_lightweight_data_settings_local_runtime_defaults_live_when_not_ci_or_pytest(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("BUILDKITE", raising=False)
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("LIGHTWEIGHT_LIVE_FETCH_ENABLED", raising=False)
    monkeypatch.delenv("LTT_LIGHTWEIGHT_LIVE_FETCH_ENABLED", raising=False)
    monkeypatch.delenv("LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED", raising=False)
    monkeypatch.delenv("LTT_LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED", raising=False)
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATA_POLICY_MODE", "lightweight")
    monkeypatch.setenv("LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED", "true")

    os_environment_default = build_lightweight_data_settings()
    local_default = build_lightweight_data_settings(env={"APP_ENV": "local"})

    assert os_environment_default.live_fetch_enabled is True
    assert os_environment_default.weekly_news_fetch_enabled is True
    assert os_environment_default.provider_fallback_enabled is True
    assert os_environment_default.can_fetch_fresh_data is True
    assert local_default.live_fetch_enabled is True
    assert local_default.weekly_news_fetch_enabled is True
    assert local_default.provider_fallback_enabled is True
    assert local_default.can_fetch_fresh_data is True
    assert LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON not in local_default.missing_reasons
    assert LIGHTWEIGHT_WEEKLY_NEWS_FETCH_DISABLED_REASON not in local_default.missing_reasons

    explicit_disabled = build_lightweight_data_settings(
        env={
            "APP_ENV": "local",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "false",
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "false",
        }
    )
    assert explicit_disabled.live_fetch_enabled is False
    assert explicit_disabled.weekly_news_fetch_enabled is False
    assert explicit_disabled.can_fetch_fresh_data is False
    assert LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON in explicit_disabled.missing_reasons
    assert LIGHTWEIGHT_WEEKLY_NEWS_FETCH_DISABLED_REASON in explicit_disabled.missing_reasons

    ci_default = build_lightweight_data_settings(env={"CI": "true"})
    assert ci_default.live_fetch_enabled is False
    assert ci_default.weekly_news_fetch_enabled is False
    assert ci_default.can_fetch_fresh_data is False

    ci_explicit_enabled = build_lightweight_data_settings(
        env={
            "CI": "true",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "true",
        }
    )
    assert ci_explicit_enabled.live_fetch_enabled is True
    assert ci_explicit_enabled.weekly_news_fetch_enabled is True
    assert ci_explicit_enabled.can_fetch_fresh_data is True


def test_market_news_settings_runtime_defaults_preserve_deterministic_paths(monkeypatch):
    empty_env = build_market_news_settings(env={})
    assert empty_env.fetch_enabled is False
    assert empty_env.live_source_real_fetch_enabled is False
    assert empty_env.can_attempt_live_fetch is False
    assert MARKET_NEWS_FETCH_DISABLED_REASON in empty_env.missing_reasons

    pytest_default = build_market_news_settings(env={"APP_ENV": "local"})
    assert pytest_default.fetch_enabled is False
    assert pytest_default.live_source_real_fetch_enabled is False
    assert pytest_default.can_attempt_live_fetch is False

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("BUILDKITE", raising=False)
    monkeypatch.delenv("JENKINS_URL", raising=False)
    monkeypatch.delenv("MARKET_NEWS_FETCH_ENABLED", raising=False)
    monkeypatch.delenv("LTT_MARKET_NEWS_FETCH_ENABLED", raising=False)
    monkeypatch.delenv("MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED", raising=False)
    monkeypatch.delenv("LTT_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    os_environment_default = build_market_news_settings()
    local_default = build_market_news_settings(env={"APP_ENV": "local"})

    assert os_environment_default.fetch_enabled is True
    assert os_environment_default.live_source_real_fetch_enabled is True
    assert os_environment_default.can_attempt_live_fetch is True
    assert local_default.fetch_enabled is True
    assert local_default.live_source_real_fetch_enabled is True
    assert local_default.can_attempt_live_fetch is True
    assert MARKET_NEWS_FETCH_DISABLED_REASON not in local_default.missing_reasons
    assert MARKET_NEWS_LIVE_SOURCE_SMOKE_DISABLED_REASON in local_default.missing_reasons

    explicit_disabled = build_market_news_settings(
        env={
            "APP_ENV": "local",
            "MARKET_NEWS_FETCH_ENABLED": "false",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "false",
        }
    )
    assert explicit_disabled.fetch_enabled is False
    assert explicit_disabled.live_source_real_fetch_enabled is False
    assert explicit_disabled.can_attempt_live_fetch is False

    ci_default = build_market_news_settings(env={"CI": "true"})
    assert ci_default.fetch_enabled is False
    assert ci_default.live_source_real_fetch_enabled is False
    assert ci_default.can_attempt_live_fetch is False

    ci_explicit_enabled = build_market_news_settings(
        env={
            "CI": "true",
            "LTT_MARKET_NEWS_FETCH_ENABLED": "true",
            "LTT_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
        }
    )
    assert ci_explicit_enabled.fetch_enabled is True
    assert ci_explicit_enabled.live_source_real_fetch_enabled is True
    assert ci_explicit_enabled.can_attempt_live_fetch is True


def test_lightweight_data_settings_explicit_live_fetch_configuration_still_overrides_defaults():
    enabled = build_lightweight_data_settings(
        env={
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_ORDER": "alpha_vantage,yfinance",
            "LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED": "true",
            "ALPHA_VANTAGE_API_KEY": "super-secret-alpha",
            "LIGHTWEIGHT_FETCH_CACHE_DIR": "/tmp/ltt-cache",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-test/0.1 person@example.com",
            "LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS": "9",
        }
    )

    assert enabled.can_fetch_fresh_data is True
    assert enabled.weekly_news_fetch_enabled is True
    assert enabled.provider_order == ("alpha_vantage", "yahoo")
    assert enabled.provider_credentials_configured["alpha_vantage"] is True
    assert enabled.provider_source_use_reviewed is True
    assert enabled.credential_for("alpha_vantage") == "super-secret-alpha"
    assert enabled.fetch_persistent_cache_dir == "/tmp/ltt-cache"
    assert enabled.safe_diagnostics["fetch_persistent_cache_enabled"] is True
    assert enabled.fetch_timeout_seconds == 9
    assert enabled.sec_user_agent_redacted == "learn-the-ticker-test/0.1 person@<redacted>"
    assert enabled.missing_reasons == ()
    assert "super-secret-alpha" not in str(enabled.safe_diagnostics)


def test_market_news_settings_include_optional_persistent_cache_without_secrets():
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKET_NEWS_CACHE_DIR": "/tmp/ltt-market-news-cache",
            "MARKETAUX_API_KEY": "marketaux-secret",
        }
    )

    assert settings.can_attempt_live_fetch is True
    assert settings.persistent_cache_dir == "/tmp/ltt-market-news-cache"
    assert settings.safe_diagnostics["persistent_cache_enabled"] is True
    assert settings.provider_credentials_configured["marketaux"] is True
    assert "marketaux-secret" not in str(settings)
    assert "marketaux-secret" not in str(settings.safe_diagnostics)


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
