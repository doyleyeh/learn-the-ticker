from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from backend.market_news import (
    MARKET_NEWS_SOURCE_ADAPTER_BOUNDARY,
    MarketNewsFetchError,
    MarketNewsFetcher,
    build_market_news_response,
    market_news_provider_adapters,
)
from backend.models import MarketNewsResponse
from backend.settings import MarketNewsSettings, build_market_news_settings
from backend.weekly_news import DEFAULT_WEEKLY_NEWS_AS_OF


MARKET_NEWS_RUNTIME_BOUNDARY = "market-news-runtime-v1"
MARKET_NEWS_PROVIDER_USER_AGENT = "Mozilla/5.0 (compatible; learn-the-ticker/0.1; +https://example.local)"
MARKET_NEWS_ALLOWED_HOSTS = {
    "api.gdeltproject.org",
    "api.marketaux.com",
    "api.mediastack.com",
    "content.guardianapis.com",
    "feeds.finance.yahoo.com",
    "finnhub.io",
    "gnews.io",
    "news.google.com",
    "newsapi.org",
    "query1.finance.yahoo.com",
    "www.alphavantage.co",
}


@dataclass(frozen=True)
class UrlLibMarketNewsFetcher:
    no_live_external_calls: bool = False
    max_bytes: int = 2_000_000
    user_agent: str = MARKET_NEWS_PROVIDER_USER_AGENT

    def fetch_json(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> Any:
        text = self.fetch_text(
            url,
            headers={"Accept": "application/json", **(headers or {})},
            timeout_seconds=timeout_seconds,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise MarketNewsFetchError("market_news_json_payload_invalid") from exc

    def fetch_text(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> str:
        _validate_market_news_url(url)
        request_headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        request_headers.update(headers or {})
        request = Request(url, headers=request_headers)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URLs are adapter-owned and host-allowlisted.
                payload = response.read(self.max_bytes + 1)
        except URLError as exc:
            raise MarketNewsFetchError("market_news_live_fetch_failed") from exc
        if len(payload) > self.max_bytes:
            raise MarketNewsFetchError("market_news_payload_too_large")
        return payload.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class MarketNewsRuntimeCacheKey:
    as_of: str
    settings_schema_version: str
    fetch_timeout_seconds: int
    fetch_enabled: bool
    live_source_real_fetch_enabled: bool
    provider_credentials_configured: tuple[tuple[str, bool], ...]
    provider_adapter_boundary: str
    providers: tuple[str, ...]
    fetcher_boundary: str


@dataclass(frozen=True)
class _MarketNewsResponseCacheEntry:
    response: MarketNewsResponse
    stored_at_seconds: float


class MarketNewsResponseMemoryCache:
    def __init__(self) -> None:
        self._entries: dict[MarketNewsRuntimeCacheKey, _MarketNewsResponseCacheEntry] = {}

    def clear(self) -> None:
        self._entries.clear()

    def get(
        self,
        key: MarketNewsRuntimeCacheKey,
        *,
        ttl_seconds: int,
        now_seconds: float | None = None,
    ) -> MarketNewsResponse | None:
        if ttl_seconds <= 0:
            return None
        entry = self._entries.get(key)
        if entry is None:
            return None
        now = time.monotonic() if now_seconds is None else now_seconds
        if now - entry.stored_at_seconds > ttl_seconds:
            self._entries.pop(key, None)
            return None
        return entry.response

    def set(
        self,
        key: MarketNewsRuntimeCacheKey,
        response: MarketNewsResponse,
        *,
        now_seconds: float | None = None,
    ) -> MarketNewsResponse:
        now = time.monotonic() if now_seconds is None else now_seconds
        self._entries[key] = _MarketNewsResponseCacheEntry(response=response, stored_at_seconds=now)
        return response


MARKET_NEWS_RESPONSE_CACHE = MarketNewsResponseMemoryCache()


def build_runtime_market_news_response(
    *,
    as_of: str | None = None,
    settings: MarketNewsSettings | None = None,
    fetcher: MarketNewsFetcher | None = None,
    cache: MarketNewsResponseMemoryCache | None = None,
) -> MarketNewsResponse:
    active_settings = settings or build_market_news_settings()
    effective_as_of = as_of or _runtime_market_news_as_of(active_settings)
    if not active_settings.can_attempt_live_fetch:
        return build_market_news_response(as_of=effective_as_of, settings=active_settings)

    source_fetcher = fetcher or UrlLibMarketNewsFetcher()
    response_cache = cache or MARKET_NEWS_RESPONSE_CACHE
    cache_key = _cache_key(effective_as_of, active_settings, source_fetcher)
    ttl_seconds = active_settings.cache_ttl_hours * 60 * 60
    cached = response_cache.get(cache_key, ttl_seconds=ttl_seconds)
    if cached is not None:
        return cached
    persisted = _persistent_cache_get(cache_key, active_settings, now_epoch_seconds=time.time())
    if persisted is not None:
        response_cache.set(cache_key, persisted)
        return persisted

    response = build_market_news_response(
        as_of=effective_as_of,
        settings=active_settings,
        fetcher=source_fetcher,
    )
    _persistent_cache_store(cache_key, response, active_settings)
    return response_cache.set(cache_key, response)


def _runtime_market_news_as_of(settings: MarketNewsSettings) -> str:
    if settings.can_attempt_live_fetch:
        return datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    return DEFAULT_WEEKLY_NEWS_AS_OF


def _cache_key(
    as_of: str,
    settings: MarketNewsSettings,
    fetcher: MarketNewsFetcher,
) -> MarketNewsRuntimeCacheKey:
    return MarketNewsRuntimeCacheKey(
        as_of=str(as_of),
        settings_schema_version=settings.schema_version,
        fetch_timeout_seconds=settings.fetch_timeout_seconds,
        fetch_enabled=settings.fetch_enabled,
        live_source_real_fetch_enabled=settings.live_source_real_fetch_enabled,
        provider_credentials_configured=tuple(sorted(settings.provider_credentials_configured.items())),
        provider_adapter_boundary=MARKET_NEWS_SOURCE_ADAPTER_BOUNDARY,
        providers=tuple(adapter.provider for adapter in market_news_provider_adapters()),
        fetcher_boundary=fetcher.__class__.__name__,
    )


def _persistent_cache_get(
    key: MarketNewsRuntimeCacheKey,
    settings: MarketNewsSettings,
    *,
    now_epoch_seconds: float,
) -> MarketNewsResponse | None:
    if not settings.persistent_cache_dir:
        return None
    path = _persistent_cache_path(key, settings)
    if path is None or not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        stored_at = float(envelope.get("stored_at_epoch_seconds"))
        age_seconds = max(0.0, now_epoch_seconds - stored_at)
        if age_seconds > settings.cache_ttl_hours * 60 * 60:
            path.unlink(missing_ok=True)
            return None
        raw_response = envelope.get("response")
        if not isinstance(raw_response, dict):
            return None
        return MarketNewsResponse.model_validate(raw_response)
    except Exception:
        return None


def _persistent_cache_store(
    key: MarketNewsRuntimeCacheKey,
    response: MarketNewsResponse,
    settings: MarketNewsSettings,
) -> None:
    if not settings.persistent_cache_dir:
        return
    path = _persistent_cache_path(key, settings)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        source_records = [
            {
                "source_document_id": source.source_document_id,
                "source_checksum": hashlib.sha256(
                    json.dumps(
                        {
                            "source_document_id": source.source_document_id,
                            "publisher": source.publisher,
                            "url": source.url,
                            "published_at": source.published_at,
                            "as_of_date": source.as_of_date,
                            "retrieved_at": source.retrieved_at,
                            "source_use_policy": source.source_use_policy.value,
                            "freshness_state": source.freshness_state.value,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    ).encode("utf-8")
                ).hexdigest(),
                "source_use_policy": source.source_use_policy.value,
                "storage_mode": "metadata_hashes_and_bounded_summaries_only",
                "ttl_seconds": settings.cache_ttl_hours * 60 * 60,
                "raw_body_stored": False,
                "secret_values_exposed": False,
            }
            for source in response.market_news_focus.source_documents
        ]
        envelope = {
            "schema_version": "market-news-persistent-cache-v1",
            "stored_at_epoch_seconds": time.time(),
            "key_checksum": _persistent_cache_key_checksum(key),
            "ttl_seconds": settings.cache_ttl_hours * 60 * 60,
            "source_cache_records": source_records,
            "response_checksum": hashlib.sha256(
                json.dumps(response.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            ).hexdigest(),
            "raw_article_bodies_stored": False,
            "raw_provider_payloads_stored": False,
            "secret_values_exposed": False,
            "response": response.model_dump(mode="json"),
        }
        path.write_text(json.dumps(envelope, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    except Exception:
        return


def _persistent_cache_path(
    key: MarketNewsRuntimeCacheKey,
    settings: MarketNewsSettings,
) -> Path | None:
    if not settings.persistent_cache_dir:
        return None
    base = Path(settings.persistent_cache_dir).expanduser()
    return base / "market_news" / f"{_persistent_cache_key_checksum(key)}.json"


def _persistent_cache_key_checksum(key: MarketNewsRuntimeCacheKey) -> str:
    payload = {
        "schema_version": MARKET_NEWS_RUNTIME_BOUNDARY,
        "as_of": key.as_of,
        "settings_schema_version": key.settings_schema_version,
        "fetch_timeout_seconds": key.fetch_timeout_seconds,
        "fetch_enabled": key.fetch_enabled,
        "live_source_real_fetch_enabled": key.live_source_real_fetch_enabled,
        "provider_credentials_configured": key.provider_credentials_configured,
        "provider_adapter_boundary": key.provider_adapter_boundary,
        "providers": key.providers,
        "fetcher_boundary": key.fetcher_boundary,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _validate_market_news_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise MarketNewsFetchError("market_news_source_url_invalid") from exc
    if parsed.scheme != "https":
        raise MarketNewsFetchError("market_news_source_url_scheme_blocked")
    host = (parsed.hostname or "").lower()
    if host not in MARKET_NEWS_ALLOWED_HOSTS:
        raise MarketNewsFetchError("market_news_source_host_blocked")
