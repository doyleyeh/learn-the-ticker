from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PERSISTENCE_SETTINGS_SCHEMA_VERSION = "persistence-settings-v1"
LOCAL_DURABLE_REPOSITORY_SETTINGS_SCHEMA_VERSION = "local-durable-repository-settings-v1"
DEFAULT_DATABASE_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_DATABASE_POOL_PRE_PING = False
DEFAULT_DATABASE_ECHO_SQL = False
DEFAULT_DATABASE_MIGRATIONS_ENABLED = False
DEFAULT_LOCAL_DURABLE_REPOSITORIES_ENABLED = False
DEFAULT_LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE = False
DEFAULT_LOCAL_DURABLE_OBJECT_NAMESPACE = "local-private-source-artifacts"
DEFAULT_OFFLINE_MIGRATION_DATABASE_URL = "postgresql+psycopg://placeholder@localhost:5432/learn_the_ticker"
MISSING_DATABASE_URL_REASON = "database_url_missing"
LOCAL_DURABLE_DISABLED_REASON = "local_durable_repositories_disabled"
INVALID_LOCAL_DURABLE_OBJECT_NAMESPACE_REASON = "local_durable_object_namespace_invalid"
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
