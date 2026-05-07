from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

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
    as_of: str = DEFAULT_WEEKLY_NEWS_AS_OF,
    settings: MarketNewsSettings | None = None,
    fetcher: MarketNewsFetcher | None = None,
    cache: MarketNewsResponseMemoryCache | None = None,
) -> MarketNewsResponse:
    active_settings = settings or build_market_news_settings()
    if not active_settings.can_attempt_live_fetch:
        return build_market_news_response(as_of=as_of, settings=active_settings)

    source_fetcher = fetcher or UrlLibMarketNewsFetcher()
    response_cache = cache or MARKET_NEWS_RESPONSE_CACHE
    cache_key = _cache_key(as_of, active_settings, source_fetcher)
    ttl_seconds = active_settings.cache_ttl_hours * 60 * 60
    cached = response_cache.get(cache_key, ttl_seconds=ttl_seconds)
    if cached is not None:
        return cached

    response = build_market_news_response(
        as_of=as_of,
        settings=active_settings,
        fetcher=source_fetcher,
    )
    return response_cache.set(cache_key, response)


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
