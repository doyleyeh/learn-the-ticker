from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

from backend import db
from backend.cache import compute_source_document_checksum
from backend.durable_repository_records import (
    DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION,
    DURABLE_REPOSITORY_RECORD_TABLE,
    DURABLE_REPOSITORY_RECORD_TABLES,
    DurableRepositoryRecordError,
    DurableRepositoryRecordSession,
    execute_durable_repository_record_schema,
    inspect_durable_repository_record_schema,
)
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    GeneratedOutputCacheRepository,
    build_deterministic_generated_output_cache_records,
)
from backend.knowledge_pack_repository import knowledge_pack_records_from_acquisition_result
from backend.models import (
    CacheEntryKind,
    CacheScope,
    EvidenceState,
    FreshnessFactInput,
    FreshnessState,
    KnowledgePackFreshnessInput,
    SectionFreshnessInput,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    SourceChecksumInput,
    WeeklyNewsEventType,
)
from backend.persistence import persistence_metadata_diagnostics, target_metadata
from backend.persistence import (
    LOCAL_DURABLE_REPOSITORY_FACTORY_BOUNDARY,
    build_backend_read_dependencies_from_local_durable_config,
    build_local_durable_repository_factories,
)
from backend.provider_adapters.etf_issuer import build_etf_issuer_acquisition_result
from backend.providers import fetch_mock_provider_response, mock_etf_issuer_adapter
from backend.source_snapshot_repository import source_snapshot_records_from_acquisition_result
from backend.weekly_news_repository import (
    WeeklyNewsEventCandidateRow,
    WeeklyNewsEventEvidenceRepository,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
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
    build_admin_route_settings,
    build_cors_settings,
    build_lightweight_data_settings,
    build_live_acquisition_settings,
    build_local_durable_repository_settings,
    build_migration_persistence_settings,
    build_market_news_settings,
    build_persistence_settings,
    offline_migration_database_url,
    redact_database_url,
)
from scripts.run_durable_schema_smoke import run_durable_schema_smoke


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


def _golden_voo_acquisition():
    adapter = mock_etf_issuer_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "VOO").licensing
    return build_etf_issuer_acquisition_result(adapter, adapter.request("VOO"), licensing)


def _weekly_news_candidate() -> WeeklyNewsEventCandidateRow:
    return WeeklyNewsEventCandidateRow(
        candidate_event_id="durable_schema_weekly_event",
        window_id="wnf_window:VOO:2026-04-23",
        asset_ticker="VOO",
        source_asset_ticker="VOO",
        event_type=WeeklyNewsEventType.methodology_change.value,
        event_title="Durable schema weekly event persisted headline",
        event_summary="Persisted Weekly News Focus summary for durable schema smoke.",
        event_date="2026-04-21",
        published_at="2026-04-21T12:00:00Z",
        retrieved_at="2026-04-23T12:00:00Z",
        period_bucket="current_week_to_date",
        source_document_id="src_durable_schema_weekly_event",
        source_chunk_id="chk_durable_schema_weekly_event",
        citation_ids=["c_weekly_durable_schema_event"],
        citation_asset_tickers={"c_weekly_durable_schema_event": "VOO"},
        source_type=WeeklyNewsSourceRankTier.official_filing.value,
        source_title="Durable Schema Weekly Event Source",
        source_publisher="Fixture Publisher",
        source_url="local://fixtures/voo/weekly-news/durable-schema-event",
        source_rank=1,
        source_rank_tier=WeeklyNewsSourceRankTier.official_filing.value,
        source_quality=SourceQuality.official.value,
        allowlist_status=SourceAllowlistStatus.allowed.value,
        source_use_policy=SourceUsePolicy.summary_allowed.value,
        freshness_state=FreshnessState.fresh.value,
        evidence_state=EvidenceState.supported.value,
        importance_score=10,
        high_signal=True,
        promotional=False,
        irrelevant=False,
        duplicate_group_id="durable_schema_weekly_event",
        candidate_decision="selected",
        suppression_reason_codes=[],
        title_checksum="sha256:title:durable-schema-weekly-event",
        evidence_checksum="sha256:evidence:durable-schema-weekly-event",
    )


def _generated_cache_records_for_voo():
    source_checksum = compute_source_document_checksum(
        SourceChecksumInput(
            source_document_id="src_voo_durable_schema",
            asset_ticker="VOO",
            source_type="issuer_fact_sheet",
            source_rank=1,
            publisher="Issuer Fixture",
            retrieved_at="2026-04-25T18:04:25Z",
            freshness_state=FreshnessState.fresh,
            citation_ids=["c_voo_durable_schema"],
            fact_bindings=["fact_voo_durable_schema"],
            cache_allowed=True,
            export_allowed=False,
        )
    )
    knowledge_input = KnowledgePackFreshnessInput(
        asset_ticker="VOO",
        pack_identity="VOO",
        source_checksums=[source_checksum],
        canonical_facts=[
            FreshnessFactInput(
                fact_id="fact_voo_durable_schema",
                asset_ticker="VOO",
                field_name="overview",
                value="Fixture overview fact",
                freshness_state=FreshnessState.fresh,
                evidence_state="supported",
                source_document_ids=["src_voo_durable_schema"],
                citation_ids=["c_voo_durable_schema"],
            )
        ],
        recent_events=[],
        evidence_gaps=[],
        page_freshness_state=FreshnessState.fresh,
        section_freshness_labels=[
            SectionFreshnessInput(
                section_id="beginner_summary",
                freshness_state=FreshnessState.fresh,
                evidence_state="supported",
            )
        ],
    )
    return build_deterministic_generated_output_cache_records(
        cache_entry_id="generated-output-voo-durable-schema",
        output_identity="asset:VOO",
        mode_or_output_type="beginner-overview",
        artifact_category=GeneratedOutputArtifactCategory.asset_overview_section,
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        prompt_version="asset-page-prompt-v1",
        knowledge_input=knowledge_input,
        citation_ids=["c_voo_durable_schema"],
        created_at="2026-04-25T18:04:25Z",
        expires_at="2026-05-02T18:04:25Z",
        ttl_seconds=604800,
        asset_ticker="VOO",
    )


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


def test_durable_repository_record_schema_smoke_applies_and_inspects_throwaway_sqlite(tmp_path):
    database_path = tmp_path / "durable-schema-smoke.db"

    result = run_durable_schema_smoke(database_path=database_path)

    assert result["schema_version"] == "durable-schema-smoke-v1"
    assert result["status"] == "passed"
    assert result["repository_record_schema_version"] == DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION
    assert result["applied_tables"] == [DURABLE_REPOSITORY_RECORD_TABLE]
    assert result["restart_read_succeeded"] is True
    assert result["secret_values_stored"] is False

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        schema = inspect_durable_repository_record_schema(connection)

    assert schema[DURABLE_REPOSITORY_RECORD_TABLE] == [
        "collection",
        "record_key",
        "schema_version",
        "model_type",
        "payload_json",
        "payload_checksum",
        "created_at",
        "updated_at",
    ]


def test_durable_repository_record_migration_revision_is_importable_and_limited():
    revision_path = ROOT / "alembic/versions/20260513_0009_durable_repository_record_contracts.py"
    source = revision_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("durable_repository_record_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260513_0009"
    assert module.down_revision == "20260425_0008"
    assert module.DURABLE_REPOSITORY_RECORD_TABLE_NAMES == DURABLE_REPOSITORY_RECORD_TABLES
    assert '"durable_repository_records"' in source
    for forbidden in ["provider_secrets", "public_snapshot_urls", "signed_urls", "user_accounts"]:
        assert forbidden not in source


def test_sqlite_durable_repository_records_survive_restart_for_core_repositories(tmp_path):
    database_path = tmp_path / "durable-repositories.db"
    env = {
        "LOCAL_DURABLE_REPOSITORIES_ENABLED": "true",
        "LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE": "true",
        "LOCAL_DURABLE_OBJECT_NAMESPACE": "local-private-source-artifacts",
        "DATABASE_URL": f"sqlite:///{database_path}",
    }

    acquisition = _golden_voo_acquisition()
    source_records = source_snapshot_records_from_acquisition_result(acquisition, ingestion_job_id="pre-cache-launch-voo")
    knowledge_records = knowledge_pack_records_from_acquisition_result(acquisition, source_records)
    weekly_records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="VOO",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[_weekly_news_candidate()],
    )
    cache_records = _generated_cache_records_for_voo()

    writer_dependencies = build_backend_read_dependencies_from_local_durable_config(env=env)
    assert writer_dependencies.active is True
    writer_dependencies.source_snapshot_repository.persist(source_records)
    writer_dependencies.knowledge_pack_reader.persist(knowledge_records)
    writer_dependencies.weekly_news_reader.persist(weekly_records)
    writer_dependencies.generated_output_cache_reader.persist(cache_records)
    writer_dependencies.ingestion_job_ledger.save(
        writer_dependencies.ingestion_job_ledger.serialize_response(request_ingestion("SPY"))
    )

    reader_dependencies = build_backend_read_dependencies_from_local_durable_config(env=env)
    assert reader_dependencies.source_snapshot_repository.read_source_snapshot_records("VOO").artifacts
    assert reader_dependencies.knowledge_pack_reader.read_knowledge_pack_records("VOO").envelope.ticker == "VOO"
    assert reader_dependencies.weekly_news_reader.read_weekly_news_event_evidence_records("VOO").selected_events
    assert reader_dependencies.generated_output_cache_reader.read_asset_overview_records("VOO").envelopes[0].asset_ticker == "VOO"
    assert reader_dependencies.ingestion_job_ledger.get("ingest-on-demand-spy").ledger.ticker == "SPY"

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"select collection, record_key, payload_checksum from {DURABLE_REPOSITORY_RECORD_TABLE} order by collection, record_key"
        ).fetchall()

    assert {(row["collection"], row["record_key"]) for row in rows} >= {
        ("asset_knowledge_pack", "VOO"),
        ("generated_output_cache_lookup", "asset:VOO:asset_overview_section"),
        ("ingestion_job_ledger", "ingest-on-demand-spy"),
        ("source_snapshot_artifacts", "source_snapshot_artifacts"),
        ("weekly_news_event_evidence", "VOO"),
    }
    assert all(str(row["payload_checksum"]).startswith("sha256:") for row in rows)


def test_durable_repository_record_session_rejects_obvious_secret_payloads(tmp_path):
    session = DurableRepositoryRecordSession(tmp_path / "durable-records.db")

    with pytest.raises(DurableRepositoryRecordError):
        session.save_repository_record("unsafe", "secret", {"api_key": "placeholder"})


def test_local_durable_repository_fail_fast_blocks_silent_production_fallback():
    with pytest.raises(RuntimeError):
        build_backend_read_dependencies_from_local_durable_config(
            env={
                "LOCAL_DURABLE_REPOSITORIES_ENABLED": "true",
                "LOCAL_DURABLE_REPOSITORIES_FAIL_FAST": "true",
                "DATABASE_URL": "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker",
                "LOCAL_DURABLE_OBJECT_NAMESPACE": "public/snapshots",
            },
            session_factory=FakeDurableSession,
        )


def test_admin_routes_default_on_locally_and_off_in_production():
    local = build_admin_route_settings(env={})
    production = build_admin_route_settings(env={"APP_ENV": "production"})
    explicit = build_admin_route_settings(env={"APP_ENV": "production", "ADMIN_ROUTES_ENABLED": "true"})

    assert local.enabled is True
    assert production.enabled is False
    assert explicit.enabled is True
    assert production.safe_diagnostics["explicit_env_value"] is False


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


def test_migration_persistence_settings_prefer_direct_migration_url():
    settings = build_migration_persistence_settings(
        env={
            "DATABASE_URL": "postgresql+psycopg://runtime:runtime-secret@pooler.example/neondb?sslmode=require",
            "MIGRATION_DATABASE_URL": "postgresql+psycopg://migrator:migration-secret@direct.example/neondb?sslmode=require",
        }
    )

    assert settings.database_host == "direct.example"
    assert "migration-secret" not in str(settings.safe_diagnostics)
    assert "runtime-secret" not in str(settings.safe_diagnostics)


def test_database_env_placeholders_are_server_side_only():
    root_env = (ROOT / ".env.example").read_text(encoding="utf-8")
    api_env = (ROOT / "deploy/env/api.example.env").read_text(encoding="utf-8")
    worker_env = (ROOT / "deploy/env/worker.example.env").read_text(encoding="utf-8")
    web_env = (ROOT / "apps/web/.env.example").read_text(encoding="utf-8")

    for text in [root_env, api_env, worker_env]:
        assert "DATABASE_URL" in text
        assert "MIGRATION_DATABASE_URL" in text
        assert "DATABASE_CONNECT_TIMEOUT_SECONDS" in text
        assert "DATABASE_POOL_PRE_PING" in text
        assert "ADMIN_ROUTES_ENABLED" in text
        assert "LOCAL_DURABLE_REPOSITORIES_FAIL_FAST" in text
        assert "DATABASE_ECHO_SQL" in text
        assert "DATABASE_MIGRATIONS_ENABLED" in text

    assert "NEXT_PUBLIC_DATABASE_URL" not in web_env
    assert "DATABASE_URL" not in web_env
