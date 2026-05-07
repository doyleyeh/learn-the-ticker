from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PERSISTENCE_SETTINGS_SCHEMA_VERSION = "persistence-settings-v1"
LOCAL_DURABLE_REPOSITORY_SETTINGS_SCHEMA_VERSION = "local-durable-repository-settings-v1"
LIVE_ACQUISITION_SETTINGS_SCHEMA_VERSION = "live-acquisition-readiness-settings-v1"
LIGHTWEIGHT_DATA_SETTINGS_SCHEMA_VERSION = "lightweight-data-settings-v1"
MARKET_NEWS_SETTINGS_SCHEMA_VERSION = "market-news-settings-v1"
CORS_SETTINGS_SCHEMA_VERSION = "cors-settings-v1"
DEFAULT_DATABASE_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_DATABASE_POOL_PRE_PING = False
DEFAULT_DATABASE_ECHO_SQL = False
DEFAULT_DATABASE_MIGRATIONS_ENABLED = False
DEFAULT_LOCAL_DURABLE_REPOSITORIES_ENABLED = False
DEFAULT_LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE = False
DEFAULT_LIVE_SEC_STOCK_ACQUISITION_ENABLED = False
DEFAULT_LIVE_ETF_ISSUER_ACQUISITION_ENABLED = False
DEFAULT_LIVE_WEEKLY_NEWS_ACQUISITION_ENABLED = False
DEFAULT_LIVE_SOURCE_RATE_LIMIT_READY = False
DEFAULT_DATA_POLICY_MODE = "lightweight"
DEFAULT_LIGHTWEIGHT_LIVE_FETCH_ENABLED = False
DEFAULT_LOCAL_RUNTIME_LIGHTWEIGHT_LIVE_FETCH_ENABLED = True
DEFAULT_LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED = True
DEFAULT_LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED = False
DEFAULT_LOCAL_RUNTIME_LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED = True
DEFAULT_LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS = 15
DEFAULT_LIGHTWEIGHT_FETCH_REUSE_TTL_SECONDS = 30
DEFAULT_LIGHTWEIGHT_PROVIDER_ORDER = ("fmp", "alpha_vantage", "finnhub", "tiingo", "eodhd", "yahoo")
DEFAULT_MARKET_NEWS_FETCH_ENABLED = False
DEFAULT_LOCAL_RUNTIME_MARKET_NEWS_FETCH_ENABLED = True
DEFAULT_MARKET_NEWS_LIVE_SOURCE_SMOKE_ENABLED = False
DEFAULT_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED = False
DEFAULT_LOCAL_RUNTIME_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED = True
DEFAULT_MARKET_NEWS_CACHE_TTL_HOURS = 24
DEFAULT_SEC_EDGAR_USER_AGENT = "learn-the-ticker-local/0.1 contact@example.com"
DEFAULT_LOCAL_DURABLE_OBJECT_NAMESPACE = "local-private-source-artifacts"
DEFAULT_OFFLINE_MIGRATION_DATABASE_URL = "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker"
DEFAULT_CORS_ALLOWED_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
DEFAULT_CORS_ALLOWED_METHODS = ("GET", "POST", "OPTIONS")
MISSING_DATABASE_URL_REASON = "database_url_missing"
LOCAL_DURABLE_DISABLED_REASON = "local_durable_repositories_disabled"
INVALID_LOCAL_DURABLE_OBJECT_NAMESPACE_REASON = "local_durable_object_namespace_invalid"
LIVE_SEC_STOCK_ACQUISITION_DISABLED_REASON = "live_sec_stock_acquisition_opt_in_missing"
LIVE_ETF_ISSUER_ACQUISITION_DISABLED_REASON = "live_etf_issuer_acquisition_opt_in_missing"
LIVE_WEEKLY_NEWS_ACQUISITION_DISABLED_REASON = "live_weekly_news_acquisition_opt_in_missing"
LIVE_SEC_SOURCE_CONFIGURATION_MISSING_REASON = "live_sec_source_configuration_missing"
LIVE_ETF_ISSUER_SOURCE_CONFIGURATION_MISSING_REASON = "live_etf_issuer_source_configuration_missing"
LIVE_WEEKLY_NEWS_SOURCE_CONFIGURATION_MISSING_REASON = "live_weekly_news_official_source_configuration_missing"
LIVE_SOURCE_RATE_LIMIT_NOT_READY_REASON = "live_source_rate_limit_not_ready"
LIVE_SOURCE_SNAPSHOT_WRITER_MISSING_REASON = "live_source_snapshot_writer_missing"
LIVE_KNOWLEDGE_PACK_WRITER_MISSING_REASON = "live_knowledge_pack_writer_missing"
LIVE_WEEKLY_NEWS_WRITER_MISSING_REASON = "live_weekly_news_evidence_writer_missing"
LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON = "lightweight_live_fetch_disabled"
LIGHTWEIGHT_PROVIDER_FALLBACK_DISABLED_REASON = "lightweight_provider_fallback_disabled"
LIGHTWEIGHT_WEEKLY_NEWS_FETCH_DISABLED_REASON = "lightweight_weekly_news_fetch_disabled"
MARKET_NEWS_FETCH_DISABLED_REASON = "market_news_fetch_disabled"
MARKET_NEWS_LIVE_SOURCE_SMOKE_DISABLED_REASON = "market_news_live_source_smoke_disabled"
SENSITIVE_QUERY_KEY_MARKERS = ("password", "pass", "token", "secret", "key", "credential")
_UNSAFE_OBJECT_NAMESPACE_MARKERS = (
    "://",
    "signed",
    "signature=",
    "token=",
    "secret",
    "password",
    "public/",
    "/public/",
    "apps/web/public",
    "next_public",
)


@dataclass(frozen=True)
class PersistenceSettings:
    schema_version: str
    database_url_configured: bool
    database_url_redacted: str | None
    database_driver: str | None
    database_host: str | None
    database_name: str | None
    connect_timeout_seconds: int
    pool_pre_ping: bool
    echo_sql: bool
    migrations_enabled: bool
    missing_reasons: tuple[str, ...] = ()
    _database_url: str | None = field(default=None, repr=False, compare=False)

    @property
    def status(self) -> str:
        return "configured" if self.database_url_configured else "missing_config"

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "database_url_configured": self.database_url_configured,
            "database_url_redacted": self.database_url_redacted,
            "database_driver": self.database_driver,
            "database_host": self.database_host,
            "database_name": self.database_name,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "pool_pre_ping": self.pool_pre_ping,
            "echo_sql": self.echo_sql,
            "migrations_enabled": self.migrations_enabled,
            "missing_reasons": list(self.missing_reasons),
        }


@dataclass(frozen=True)
class LiveAcquisitionSettings:
    schema_version: str
    sec_stock_enabled: bool
    etf_issuer_enabled: bool
    weekly_news_enabled: bool
    sec_source_configured: bool
    etf_issuer_source_configured: bool
    weekly_news_official_source_configured: bool
    rate_limit_ready: bool
    source_snapshot_writer_ready: bool
    knowledge_pack_writer_ready: bool
    weekly_news_evidence_writer_ready: bool
    generated_output_cache_writer_ready: bool
    missing_reasons: tuple[str, ...] = ()

    @property
    def sec_stock_ready(self) -> bool:
        return (
            self.sec_stock_enabled
            and self.sec_source_configured
            and self.rate_limit_ready
            and self.source_snapshot_writer_ready
            and self.knowledge_pack_writer_ready
        )

    @property
    def etf_issuer_ready(self) -> bool:
        return (
            self.etf_issuer_enabled
            and self.etf_issuer_source_configured
            and self.rate_limit_ready
            and self.source_snapshot_writer_ready
            and self.knowledge_pack_writer_ready
        )

    @property
    def weekly_news_ready(self) -> bool:
        return (
            self.weekly_news_enabled
            and self.weekly_news_official_source_configured
            and self.rate_limit_ready
            and self.weekly_news_evidence_writer_ready
        )

    @property
    def status(self) -> str:
        return "configured" if self.sec_stock_ready or self.etf_issuer_ready or self.weekly_news_ready else "blocked"

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "sec_stock_enabled": self.sec_stock_enabled,
            "etf_issuer_enabled": self.etf_issuer_enabled,
            "weekly_news_enabled": self.weekly_news_enabled,
            "sec_source_configured": self.sec_source_configured,
            "etf_issuer_source_configured": self.etf_issuer_source_configured,
            "weekly_news_official_source_configured": self.weekly_news_official_source_configured,
            "rate_limit_ready": self.rate_limit_ready,
            "source_snapshot_writer_ready": self.source_snapshot_writer_ready,
            "knowledge_pack_writer_ready": self.knowledge_pack_writer_ready,
            "weekly_news_evidence_writer_ready": self.weekly_news_evidence_writer_ready,
            "generated_output_cache_writer_ready": self.generated_output_cache_writer_ready,
            "missing_reasons": list(self.missing_reasons),
        }


@dataclass(frozen=True)
class LightweightDataSettings:
    schema_version: str
    data_policy_mode: str
    live_fetch_enabled: bool
    provider_fallback_enabled: bool
    weekly_news_fetch_enabled: bool
    sec_user_agent_configured: bool
    sec_user_agent_redacted: str
    fetch_timeout_seconds: int
    fetch_reuse_ttl_seconds: int
    fetch_persistent_cache_dir: str | None = None
    provider_order: tuple[str, ...] = DEFAULT_LIGHTWEIGHT_PROVIDER_ORDER
    provider_credentials_configured: dict[str, bool] = field(default_factory=dict)
    provider_source_use_reviewed: bool = False
    missing_reasons: tuple[str, ...] = ()
    _provider_credentials: dict[str, str | None] = field(default_factory=dict, repr=False, compare=False)
    _sec_user_agent: str = field(default=DEFAULT_SEC_EDGAR_USER_AGENT, repr=False, compare=False)

    @property
    def lightweight_enabled(self) -> bool:
        return self.data_policy_mode == DEFAULT_DATA_POLICY_MODE

    @property
    def can_fetch_fresh_data(self) -> bool:
        return self.lightweight_enabled and self.live_fetch_enabled

    @property
    def fetch_reuse_enabled(self) -> bool:
        return self.fetch_reuse_ttl_seconds > 0

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "data_policy_mode": self.data_policy_mode,
            "lightweight_enabled": self.lightweight_enabled,
            "live_fetch_enabled": self.live_fetch_enabled,
            "provider_fallback_enabled": self.provider_fallback_enabled,
            "weekly_news_fetch_enabled": self.weekly_news_fetch_enabled,
            "sec_user_agent_configured": self.sec_user_agent_configured,
            "sec_user_agent_redacted": self.sec_user_agent_redacted,
            "fetch_timeout_seconds": self.fetch_timeout_seconds,
            "fetch_reuse_enabled": self.fetch_reuse_enabled,
            "fetch_reuse_ttl_seconds": self.fetch_reuse_ttl_seconds,
            "fetch_persistent_cache_enabled": self.fetch_persistent_cache_dir is not None,
            "fetch_persistent_cache_dir_configured": self.fetch_persistent_cache_dir is not None,
            "provider_order": list(self.provider_order),
            "provider_credentials_configured": dict(self.provider_credentials_configured),
            "provider_source_use_reviewed": self.provider_source_use_reviewed,
            "missing_reasons": list(self.missing_reasons),
        }

    def credential_for(self, provider: str) -> str | None:
        return self._provider_credentials.get(provider)


@dataclass(frozen=True)
class MarketNewsSettings:
    schema_version: str
    fetch_enabled: bool
    live_source_smoke_enabled: bool
    live_source_real_fetch_enabled: bool
    cache_ttl_hours: int
    fetch_timeout_seconds: int
    persistent_cache_dir: str | None = None
    provider_credentials_configured: dict[str, bool] = field(default_factory=dict)
    missing_reasons: tuple[str, ...] = ()
    _credentials: dict[str, str | None] = field(default_factory=dict, repr=False, compare=False)

    @property
    def can_attempt_live_fetch(self) -> bool:
        return self.fetch_enabled and self.live_source_real_fetch_enabled

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "fetch_enabled": self.fetch_enabled,
            "live_source_smoke_enabled": self.live_source_smoke_enabled,
            "live_source_real_fetch_enabled": self.live_source_real_fetch_enabled,
            "cache_ttl_hours": self.cache_ttl_hours,
            "fetch_timeout_seconds": self.fetch_timeout_seconds,
            "persistent_cache_enabled": self.persistent_cache_dir is not None,
            "persistent_cache_dir_configured": self.persistent_cache_dir is not None,
            "provider_credentials_configured": dict(self.provider_credentials_configured),
            "missing_reasons": list(self.missing_reasons),
        }

    def credential_for(self, provider: str) -> str | None:
        return self._credentials.get(provider)


@dataclass(frozen=True)
class LocalDurableRepositorySettings:
    schema_version: str
    enabled: bool
    database: PersistenceSettings
    object_namespace: str | None
    object_namespace_configured: bool
    commit_on_write: bool
    missing_reasons: tuple[str, ...] = ()
    invalid_reasons: tuple[str, ...] = ()

    @property
    def can_construct(self) -> bool:
        return (
            self.enabled
            and self.database.database_url_configured
            and not self.invalid_reasons
        )

    @property
    def status(self) -> str:
        if self.can_construct:
            return "configured"
        if not self.enabled:
            return "disabled"
        if self.invalid_reasons:
            return "invalid_config"
        return "missing_config"

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "enabled": self.enabled,
            "can_construct": self.can_construct,
            "database_url_configured": self.database.database_url_configured,
            "database_url_redacted": self.database.database_url_redacted,
            "database_driver": self.database.database_driver,
            "database_host": self.database.database_host,
            "database_name": self.database.database_name,
            "object_namespace_configured": self.object_namespace_configured,
            "object_namespace": self.object_namespace,
            "commit_on_write": self.commit_on_write,
            "missing_reasons": list(self.missing_reasons),
            "invalid_reasons": list(self.invalid_reasons),
        }


@dataclass(frozen=True)
class CorsSettings:
    schema_version: str
    allowed_origins: tuple[str, ...]
    allowed_methods: tuple[str, ...]
    allow_credentials: bool

    @property
    def enabled(self) -> bool:
        return bool(self.allowed_origins)

    @property
    def safe_diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "allowed_origins": list(self.allowed_origins),
            "allowed_methods": list(self.allowed_methods),
            "allow_credentials": self.allow_credentials,
        }


def build_persistence_settings(env: dict[str, str] | None = None) -> PersistenceSettings:
    source = os.environ if env is None else env
    database_url = _clean_optional(source.get("DATABASE_URL"))
    parsed = _parse_database_url(database_url)

    return PersistenceSettings(
        schema_version=PERSISTENCE_SETTINGS_SCHEMA_VERSION,
        database_url_configured=database_url is not None,
        database_url_redacted=redact_database_url(database_url),
        database_driver=parsed["driver"],
        database_host=parsed["host"],
        database_name=parsed["database"],
        connect_timeout_seconds=_int_setting(
            source.get("DATABASE_CONNECT_TIMEOUT_SECONDS"),
            DEFAULT_DATABASE_CONNECT_TIMEOUT_SECONDS,
            minimum=1,
        ),
        pool_pre_ping=_bool_setting(source.get("DATABASE_POOL_PRE_PING"), DEFAULT_DATABASE_POOL_PRE_PING),
        echo_sql=_bool_setting(source.get("DATABASE_ECHO_SQL"), DEFAULT_DATABASE_ECHO_SQL),
        migrations_enabled=_bool_setting(source.get("DATABASE_MIGRATIONS_ENABLED"), DEFAULT_DATABASE_MIGRATIONS_ENABLED),
        missing_reasons=() if database_url else (MISSING_DATABASE_URL_REASON,),
        _database_url=database_url,
    )


def build_cors_settings(env: dict[str, str] | None = None) -> CorsSettings:
    source = os.environ if env is None else env
    raw_origins = source.get("CORS_ALLOWED_ORIGINS")
    allowed_origins = _csv_setting(raw_origins) if raw_origins is not None else DEFAULT_CORS_ALLOWED_ORIGINS

    return CorsSettings(
        schema_version=CORS_SETTINGS_SCHEMA_VERSION,
        allowed_origins=allowed_origins,
        allowed_methods=DEFAULT_CORS_ALLOWED_METHODS,
        allow_credentials=False,
    )


def build_local_durable_repository_settings(env: dict[str, str] | None = None) -> LocalDurableRepositorySettings:
    source = os.environ if env is None else env
    database = build_persistence_settings(env=dict(source))
    enabled = _bool_setting(
        source.get("LOCAL_DURABLE_REPOSITORIES_ENABLED"),
        DEFAULT_LOCAL_DURABLE_REPOSITORIES_ENABLED,
    )
    namespace = _clean_optional(source.get("LOCAL_DURABLE_OBJECT_NAMESPACE"))
    object_namespace = namespace or (DEFAULT_LOCAL_DURABLE_OBJECT_NAMESPACE if enabled else None)
    invalid_reasons = []
    if object_namespace and not _valid_local_object_namespace(object_namespace):
        invalid_reasons.append(INVALID_LOCAL_DURABLE_OBJECT_NAMESPACE_REASON)

    missing_reasons = []
    if not enabled:
        missing_reasons.append(LOCAL_DURABLE_DISABLED_REASON)
    if enabled and not database.database_url_configured:
        missing_reasons.append(MISSING_DATABASE_URL_REASON)

    return LocalDurableRepositorySettings(
        schema_version=LOCAL_DURABLE_REPOSITORY_SETTINGS_SCHEMA_VERSION,
        enabled=enabled,
        database=database,
        object_namespace=object_namespace,
        object_namespace_configured=namespace is not None,
        commit_on_write=_bool_setting(
            source.get("LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE"),
            DEFAULT_LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE,
        ),
        missing_reasons=tuple(missing_reasons),
        invalid_reasons=tuple(invalid_reasons),
    )


def build_live_acquisition_settings(env: dict[str, str] | None = None) -> LiveAcquisitionSettings:
    source = os.environ if env is None else env
    sec_stock_enabled = _bool_setting(
        _first_present(
            source,
            "LIVE_SEC_STOCK_ACQUISITION_ENABLED",
            "SEC_STOCK_LIVE_ACQUISITION_ENABLED",
        ),
        DEFAULT_LIVE_SEC_STOCK_ACQUISITION_ENABLED,
    )
    etf_issuer_enabled = _bool_setting(
        _first_present(
            source,
            "LIVE_ETF_ISSUER_ACQUISITION_ENABLED",
            "ETF_ISSUER_LIVE_ACQUISITION_ENABLED",
        ),
        DEFAULT_LIVE_ETF_ISSUER_ACQUISITION_ENABLED,
    )
    weekly_news_enabled = _bool_setting(
        _first_present(
            source,
            "LIVE_WEEKLY_NEWS_ACQUISITION_ENABLED",
            "WEEKLY_NEWS_LIVE_ACQUISITION_ENABLED",
        ),
        DEFAULT_LIVE_WEEKLY_NEWS_ACQUISITION_ENABLED,
    )
    sec_source_configured = _bool_setting(
        _first_present(source, "LIVE_SEC_SOURCE_CONFIGURED", "SEC_EDGAR_SOURCE_CONFIGURED"),
        False,
    )
    etf_issuer_source_configured = _bool_setting(
        _first_present(source, "LIVE_ETF_ISSUER_SOURCE_CONFIGURED", "ETF_ISSUER_SOURCE_CONFIGURED"),
        False,
    )
    weekly_news_official_source_configured = _bool_setting(
        _first_present(
            source,
            "LIVE_WEEKLY_NEWS_OFFICIAL_SOURCE_CONFIGURED",
            "WEEKLY_NEWS_OFFICIAL_SOURCE_CONFIGURED",
        ),
        False,
    )
    rate_limit_ready = _bool_setting(
        _first_present(source, "LIVE_SOURCE_RATE_LIMIT_READY", "SOURCE_ACQUISITION_RATE_LIMIT_READY"),
        DEFAULT_LIVE_SOURCE_RATE_LIMIT_READY,
    )
    source_snapshot_writer_ready = _bool_setting(
        _first_present(source, "LIVE_ACQUISITION_SOURCE_SNAPSHOT_WRITER_READY"),
        False,
    )
    knowledge_pack_writer_ready = _bool_setting(
        _first_present(source, "LIVE_ACQUISITION_KNOWLEDGE_PACK_WRITER_READY"),
        False,
    )
    weekly_news_evidence_writer_ready = _bool_setting(
        _first_present(source, "LIVE_ACQUISITION_WEEKLY_NEWS_WRITER_READY"),
        False,
    )
    generated_output_cache_writer_ready = _bool_setting(
        _first_present(source, "LIVE_ACQUISITION_GENERATED_OUTPUT_CACHE_WRITER_READY"),
        False,
    )
    missing_reasons = []
    if not sec_stock_enabled:
        missing_reasons.append(LIVE_SEC_STOCK_ACQUISITION_DISABLED_REASON)
    if not etf_issuer_enabled:
        missing_reasons.append(LIVE_ETF_ISSUER_ACQUISITION_DISABLED_REASON)
    if not weekly_news_enabled:
        missing_reasons.append(LIVE_WEEKLY_NEWS_ACQUISITION_DISABLED_REASON)
    if sec_stock_enabled and not sec_source_configured:
        missing_reasons.append(LIVE_SEC_SOURCE_CONFIGURATION_MISSING_REASON)
    if etf_issuer_enabled and not etf_issuer_source_configured:
        missing_reasons.append(LIVE_ETF_ISSUER_SOURCE_CONFIGURATION_MISSING_REASON)
    if weekly_news_enabled and not weekly_news_official_source_configured:
        missing_reasons.append(LIVE_WEEKLY_NEWS_SOURCE_CONFIGURATION_MISSING_REASON)
    if (sec_stock_enabled or etf_issuer_enabled or weekly_news_enabled) and not rate_limit_ready:
        missing_reasons.append(LIVE_SOURCE_RATE_LIMIT_NOT_READY_REASON)
    if (sec_stock_enabled or etf_issuer_enabled) and not source_snapshot_writer_ready:
        missing_reasons.append(LIVE_SOURCE_SNAPSHOT_WRITER_MISSING_REASON)
    if (sec_stock_enabled or etf_issuer_enabled) and not knowledge_pack_writer_ready:
        missing_reasons.append(LIVE_KNOWLEDGE_PACK_WRITER_MISSING_REASON)
    if weekly_news_enabled and not weekly_news_evidence_writer_ready:
        missing_reasons.append(LIVE_WEEKLY_NEWS_WRITER_MISSING_REASON)

    return LiveAcquisitionSettings(
        schema_version=LIVE_ACQUISITION_SETTINGS_SCHEMA_VERSION,
        sec_stock_enabled=sec_stock_enabled,
        etf_issuer_enabled=etf_issuer_enabled,
        weekly_news_enabled=weekly_news_enabled,
        sec_source_configured=sec_source_configured,
        etf_issuer_source_configured=etf_issuer_source_configured,
        weekly_news_official_source_configured=weekly_news_official_source_configured,
        rate_limit_ready=rate_limit_ready,
        source_snapshot_writer_ready=source_snapshot_writer_ready,
        knowledge_pack_writer_ready=knowledge_pack_writer_ready,
        weekly_news_evidence_writer_ready=weekly_news_evidence_writer_ready,
        generated_output_cache_writer_ready=generated_output_cache_writer_ready,
        missing_reasons=tuple(missing_reasons),
    )


def build_lightweight_data_settings(env: dict[str, str] | None = None) -> LightweightDataSettings:
    source = os.environ if env is None else env
    env_was_provided = env is not None
    mode = _clean_optional(source.get("DATA_POLICY_MODE")) or DEFAULT_DATA_POLICY_MODE
    mode = mode.strip().lower()
    live_fetch_enabled = _bool_setting(
        _first_present(source, "LIGHTWEIGHT_LIVE_FETCH_ENABLED", "LTT_LIGHTWEIGHT_LIVE_FETCH_ENABLED"),
        _default_lightweight_live_fetch_enabled(source, env_was_provided=env_was_provided),
    )
    provider_fallback_enabled = _bool_setting(
        _first_present(
            source,
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED",
            "LTT_LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED",
        ),
        DEFAULT_LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED,
    )
    weekly_news_fetch_enabled = _bool_setting(
        _first_present(
            source,
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED",
            "LTT_LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED",
        ),
        _default_local_runtime_enabled(
            source,
            env_was_provided=env_was_provided,
            deterministic_default=DEFAULT_LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED,
            local_runtime_default=DEFAULT_LOCAL_RUNTIME_LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED,
        ),
    )
    user_agent = _clean_optional(
        _first_present(source, "SEC_EDGAR_USER_AGENT", "LIGHTWEIGHT_SEC_USER_AGENT")
    ) or DEFAULT_SEC_EDGAR_USER_AGENT
    fetch_timeout = _int_setting(
        _first_present(source, "LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS", "LTT_LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS"),
        DEFAULT_LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS,
        minimum=1,
    )
    fetch_reuse_ttl = _int_setting(
        _first_present(
            source,
            "LIGHTWEIGHT_FETCH_REUSE_TTL_SECONDS",
            "LTT_LIGHTWEIGHT_FETCH_REUSE_TTL_SECONDS",
        ),
        DEFAULT_LIGHTWEIGHT_FETCH_REUSE_TTL_SECONDS,
        minimum=0,
    )
    provider_order = _lightweight_provider_order(
        _first_present(source, "LIGHTWEIGHT_PROVIDER_ORDER", "LTT_LIGHTWEIGHT_PROVIDER_ORDER")
    )
    persistent_cache_dir = _clean_optional(
        _first_present(source, "LIGHTWEIGHT_FETCH_CACHE_DIR", "LTT_LIGHTWEIGHT_FETCH_CACHE_DIR")
    )
    provider_source_use_reviewed = _bool_setting(
        _first_present(
            source,
            "LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED",
            "LTT_LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED",
        ),
        False,
    )
    credential_env_by_provider = {
        "fmp": "FMP_API_KEY",
        "alpha_vantage": "ALPHA_VANTAGE_API_KEY",
        "finnhub": "FINNHUB_API_KEY",
        "tiingo": "TIINGO_API_KEY",
        "eodhd": "EODHD_API_KEY",
    }
    provider_credentials = {
        provider: _clean_optional(source.get(env_name))
        for provider, env_name in credential_env_by_provider.items()
    }
    provider_credential_flags = {provider: bool(value) for provider, value in provider_credentials.items()}
    missing_reasons = []
    if mode != DEFAULT_DATA_POLICY_MODE:
        missing_reasons.append("data_policy_mode_not_lightweight")
    if not live_fetch_enabled:
        missing_reasons.append(LIGHTWEIGHT_LIVE_FETCH_DISABLED_REASON)
    if not provider_fallback_enabled:
        missing_reasons.append(LIGHTWEIGHT_PROVIDER_FALLBACK_DISABLED_REASON)
    if not weekly_news_fetch_enabled:
        missing_reasons.append(LIGHTWEIGHT_WEEKLY_NEWS_FETCH_DISABLED_REASON)

    return LightweightDataSettings(
        schema_version=LIGHTWEIGHT_DATA_SETTINGS_SCHEMA_VERSION,
        data_policy_mode=mode,
        live_fetch_enabled=live_fetch_enabled,
        provider_fallback_enabled=provider_fallback_enabled,
        weekly_news_fetch_enabled=weekly_news_fetch_enabled,
        sec_user_agent_configured=bool(user_agent),
        sec_user_agent_redacted=_redact_user_agent(user_agent),
        fetch_timeout_seconds=fetch_timeout,
        fetch_reuse_ttl_seconds=fetch_reuse_ttl,
        fetch_persistent_cache_dir=persistent_cache_dir,
        provider_order=provider_order,
        provider_credentials_configured=provider_credential_flags,
        provider_source_use_reviewed=provider_source_use_reviewed,
        missing_reasons=tuple(missing_reasons),
        _provider_credentials=provider_credentials,
        _sec_user_agent=user_agent,
    )


def build_market_news_settings(env: dict[str, str] | None = None) -> MarketNewsSettings:
    source = os.environ if env is None else env
    env_was_provided = env is not None
    fetch_enabled = _bool_setting(
        _first_present(source, "MARKET_NEWS_FETCH_ENABLED", "LTT_MARKET_NEWS_FETCH_ENABLED"),
        _default_local_runtime_enabled(
            source,
            env_was_provided=env_was_provided,
            deterministic_default=DEFAULT_MARKET_NEWS_FETCH_ENABLED,
            local_runtime_default=DEFAULT_LOCAL_RUNTIME_MARKET_NEWS_FETCH_ENABLED,
        ),
    )
    live_source_smoke_enabled = _bool_setting(
        _first_present(
            source,
            "MARKET_NEWS_LIVE_SOURCE_SMOKE_ENABLED",
            "LTT_MARKET_NEWS_LIVE_SOURCE_SMOKE_ENABLED",
        ),
        DEFAULT_MARKET_NEWS_LIVE_SOURCE_SMOKE_ENABLED,
    )
    live_source_real_fetch_enabled = _bool_setting(
        _first_present(
            source,
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED",
            "LTT_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED",
        ),
        _default_local_runtime_enabled(
            source,
            env_was_provided=env_was_provided,
            deterministic_default=DEFAULT_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED,
            local_runtime_default=DEFAULT_LOCAL_RUNTIME_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED,
        ),
    )
    cache_ttl_hours = _int_setting(
        _first_present(source, "MARKET_NEWS_CACHE_TTL_HOURS", "LTT_MARKET_NEWS_CACHE_TTL_HOURS"),
        DEFAULT_MARKET_NEWS_CACHE_TTL_HOURS,
        minimum=1,
    )
    fetch_timeout = _int_setting(
        _first_present(
            source,
            "MARKET_NEWS_FETCH_TIMEOUT_SECONDS",
            "LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS",
            "LTT_LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS",
        ),
        DEFAULT_LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS,
        minimum=1,
    )
    persistent_cache_dir = _clean_optional(
        _first_present(source, "MARKET_NEWS_CACHE_DIR", "LTT_MARKET_NEWS_CACHE_DIR")
    )
    credential_env_by_provider = {
        "marketaux": "MARKETAUX_API_KEY",
        "alpha_vantage": "ALPHA_VANTAGE_API_KEY",
        "finnhub": "FINNHUB_API_KEY",
        "guardian": "GUARDIAN_API_KEY",
        "gnews": "GNEWS_API_KEY",
        "mediastack": "MEDIASTACK_API_KEY",
        "newsapi": "NEWSAPI_API_KEY",
    }
    credentials = {
        provider: _clean_optional(source.get(env_name))
        for provider, env_name in credential_env_by_provider.items()
    }
    credential_flags = {provider: bool(value) for provider, value in credentials.items()}
    missing_reasons = []
    if not fetch_enabled:
        missing_reasons.append(MARKET_NEWS_FETCH_DISABLED_REASON)
    if not live_source_smoke_enabled:
        missing_reasons.append(MARKET_NEWS_LIVE_SOURCE_SMOKE_DISABLED_REASON)
    if fetch_enabled and live_source_real_fetch_enabled and not any(credential_flags.values()):
        missing_reasons.append("market_news_keyed_provider_credentials_missing")

    return MarketNewsSettings(
        schema_version=MARKET_NEWS_SETTINGS_SCHEMA_VERSION,
        fetch_enabled=fetch_enabled,
        live_source_smoke_enabled=live_source_smoke_enabled,
        live_source_real_fetch_enabled=live_source_real_fetch_enabled,
        cache_ttl_hours=cache_ttl_hours,
        fetch_timeout_seconds=fetch_timeout,
        persistent_cache_dir=persistent_cache_dir,
        provider_credentials_configured=credential_flags,
        missing_reasons=tuple(missing_reasons),
        _credentials=credentials,
    )


def redact_database_url(database_url: str | None) -> str | None:
    cleaned = _clean_optional(database_url)
    if cleaned is None:
        return None

    try:
        parsed = urlsplit(cleaned)
    except ValueError:
        return "<redacted-database-url>"

    if not parsed.scheme or not parsed.netloc:
        return "<redacted-database-url>"

    host = _host_with_optional_port(parsed)
    netloc = f"<credentials>@{host}" if parsed.username or parsed.password else host
    query = _redacted_query(parsed.query)
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))


def offline_migration_database_url(settings: PersistenceSettings | None = None) -> str:
    return DEFAULT_OFFLINE_MIGRATION_DATABASE_URL


def _parse_database_url(database_url: str | None) -> dict[str, str | None]:
    cleaned = _clean_optional(database_url)
    if cleaned is None:
        return {"driver": None, "host": None, "database": None}

    try:
        parsed = urlsplit(cleaned)
    except ValueError:
        return {"driver": None, "host": None, "database": None}

    database_name = parsed.path.lstrip("/") or None
    return {
        "driver": parsed.scheme or None,
        "host": parsed.hostname,
        "database": database_name,
    }


def _host_with_optional_port(parsed) -> str:
    hostname = parsed.hostname or "<host>"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    if parsed.port is None:
        return hostname
    return f"{hostname}:{parsed.port}"


def _redacted_query(query: str) -> str:
    if not query:
        return ""
    pairs = parse_qsl(query, keep_blank_values=True)
    redacted_pairs = [
        (key, "<redacted>" if _is_sensitive_query_key(key) else value)
        for key, value in pairs
    ]
    return urlencode(redacted_pairs)


def _is_sensitive_query_key(key: str) -> bool:
    normalized = key.lower()
    return any(marker in normalized for marker in SENSITIVE_QUERY_KEY_MARKERS)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _redact_user_agent(value: str) -> str:
    stripped = value.strip()
    if "@" in stripped:
        return stripped.split("@", 1)[0].rstrip(" <(") + "@<redacted>"
    return stripped


def _csv_setting(value: str | None) -> tuple[str, ...]:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return ()
    return tuple(item.strip() for item in cleaned.split(",") if item.strip())


def _lightweight_provider_order(value: str | None) -> tuple[str, ...]:
    aliases = {"yfinance": "yahoo", "yahoo_finance": "yahoo", "alphavantage": "alpha_vantage"}
    allowed = {*DEFAULT_LIGHTWEIGHT_PROVIDER_ORDER}
    requested = _csv_setting(value)
    if not requested:
        return DEFAULT_LIGHTWEIGHT_PROVIDER_ORDER
    normalized: list[str] = []
    for item in requested:
        provider = aliases.get(item.strip().lower(), item.strip().lower())
        if provider in allowed and provider not in normalized:
            normalized.append(provider)
    if "yahoo" not in normalized:
        normalized.append("yahoo")
    return tuple(normalized) if normalized else DEFAULT_LIGHTWEIGHT_PROVIDER_ORDER


def _first_present(source: dict[str, str] | os._Environ[str], *names: str) -> str | None:
    for name in names:
        value = source.get(name)
        if value is not None:
            return value
    return None


def _default_lightweight_live_fetch_enabled(
    source: dict[str, str] | os._Environ[str],
    *,
    env_was_provided: bool,
) -> bool:
    return _default_local_runtime_enabled(
        source,
        env_was_provided=env_was_provided,
        deterministic_default=DEFAULT_LIGHTWEIGHT_LIVE_FETCH_ENABLED,
        local_runtime_default=DEFAULT_LOCAL_RUNTIME_LIGHTWEIGHT_LIVE_FETCH_ENABLED,
    )


def _default_local_runtime_enabled(
    source: dict[str, str] | os._Environ[str],
    *,
    env_was_provided: bool,
    deterministic_default: bool,
    local_runtime_default: bool,
) -> bool:
    if env_was_provided and not source:
        return deterministic_default
    if _running_in_ci_or_pytest(source):
        return deterministic_default
    return local_runtime_default


def _running_in_ci_or_pytest(source: dict[str, str] | os._Environ[str]) -> bool:
    for name in ("CI", "GITHUB_ACTIONS", "BUILDKITE"):
        if _bool_setting(source.get(name), False) or _bool_setting(os.environ.get(name), False):
            return True
    for name in ("JENKINS_URL", "PYTEST_CURRENT_TEST"):
        if source.get(name) is not None or os.environ.get(name) is not None:
            return True
    return False


def _valid_local_object_namespace(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized.startswith(("/", ".", "~")) or ".." in normalized.split("/"):
        return False
    return not any(marker in normalized for marker in _UNSAFE_OBJECT_NAMESPACE_MARKERS)


def _bool_setting(value: str | bool | None, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_setting(value: str | int | None, default: int, *, minimum: int) -> int:
    if isinstance(value, int):
        return max(value, minimum)
    if value is None or value == "":
        return default
    try:
        return max(int(value), minimum)
    except ValueError:
        return default
