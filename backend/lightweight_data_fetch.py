from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from backend.data import (
    OUT_OF_SCOPE_COMMON_STOCKS,
    UNSUPPORTED_ASSETS,
    normalize_ticker,
    top500_stock_universe_entry,
)
from backend.etf_universe import ETFUniverseSupportState, etf_universe_entry
from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    DataPolicyMode,
    EvidenceState,
    Freshness,
    FreshnessState,
    LightweightApiFallbackDiagnostics,
    LightweightFallbackFreshnessSummary,
    LightweightFetchCitation,
    LightweightFetchFact,
    LightweightFetchResponse,
    LightweightFetchSource,
    LightweightFetchState,
    LightweightSourceLabel,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
)
from backend.settings import LightweightDataSettings, build_lightweight_data_settings


LIGHTWEIGHT_FETCH_SCHEMA_VERSION = "lightweight-asset-fetch-v1"
DEFAULT_CHART_RANGE = "6mo"
SUPPORTED_CHART_RANGES = ("1d", "5d", "1mo", "6mo", "ytd", "1y", "5y", "max")
CHART_INTERVAL_BY_RANGE = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "1d",
    "6mo": "1d",
    "ytd": "1d",
    "1y": "1d",
    "5y": "1wk",
    "max": "1mo",
}
ALLOWED_LIGHTWEIGHT_HOSTS = {
    "data.sec.gov",
    "finance.yahoo.com",
    "www.sec.gov",
    "query1.finance.yahoo.com",
}
YAHOO_RIGHTS_NOTE = (
    "Yahoo Finance/yfinance-derived provider fallback is source-labeled and normalized for display; "
    "the raw provider payload is not displayed or exported."
)
YAHOO_PROVIDER_USER_AGENT = "Mozilla/5.0 (compatible; learn-the-ticker/0.1; +https://example.local)"
SEC_RIGHTS_NOTE = (
    "SEC public metadata is used as an official source; full raw SEC payloads are not exported by this response."
)
ETF_SCOPE_DISQUALIFIER_MARKERS = (
    "2x",
    "3x",
    "bear",
    "bitcoin",
    "bond",
    "buffer",
    "commodity",
    "covered call",
    "crypto",
    "daily inverse",
    "daily short",
    "etn",
    "futures",
    "gold",
    "inverse",
    "leveraged",
    "multi-asset",
    "option income",
    "short",
    "single stock",
    "treasury",
    "ultra",
    "vix",
)


class LightweightFetchError(ValueError):
    """Raised when the lightweight fetch boundary rejects a URL or payload."""


class JsonFetcher(Protocol):
    no_live_external_calls: bool

    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class UrlLibJsonFetcher:
    no_live_external_calls: bool = False
    max_bytes: int = 4_000_000

    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        _validate_lightweight_url(url)
        request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - guarded by _validate_lightweight_url.
                payload = response.read(self.max_bytes + 1)
        except HTTPError as exc:
            if exc.code == 401 and _is_yahoo_finance_url(url):
                return _fetch_yahoo_json_with_crumb(
                    url,
                    user_agent=user_agent,
                    timeout_seconds=timeout_seconds,
                    max_bytes=self.max_bytes,
                )
            raise
        if len(payload) > self.max_bytes:
            raise LightweightFetchError("lightweight_source_payload_too_large")
        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise LightweightFetchError("lightweight_source_payload_not_json_object")
        return parsed


@dataclass(frozen=True)
class _LightweightFetchReuseKey:
    ticker: str
    chart_range: str
    asset_type_hint: str
    data_policy_mode: str
    live_fetch_enabled: bool
    provider_fallback_enabled: bool
    sec_user_agent_redacted: str
    fetch_timeout_seconds: int
    fetcher_boundary: str


@dataclass(frozen=True)
class _LightweightFetchReuseEntry:
    response: LightweightFetchResponse
    stored_at_seconds: float


_LIGHTWEIGHT_FETCH_REUSE_CACHE: dict[_LightweightFetchReuseKey, _LightweightFetchReuseEntry] = {}


def clear_lightweight_fetch_reuse_cache() -> None:
    _LIGHTWEIGHT_FETCH_REUSE_CACHE.clear()


def fetch_lightweight_asset_data(
    ticker: str,
    *,
    settings: LightweightDataSettings | None = None,
    fetcher: JsonFetcher | None = None,
    retrieved_at: str | None = None,
    chart_range: str = DEFAULT_CHART_RANGE,
    bypass_reuse: bool = False,
) -> LightweightFetchResponse:
    normalized = normalize_ticker(ticker)
    active_settings = settings or build_lightweight_data_settings()
    now = retrieved_at or _utc_now()
    normalized_chart_range = normalize_chart_range(chart_range) or DEFAULT_CHART_RANGE
    if active_settings.data_policy_mode != DataPolicyMode.lightweight.value:
        return _unavailable_response(
            normalized,
            now,
            active_settings,
            reason_code="data_policy_mode_not_lightweight",
            message="Fresh lightweight fetching is disabled because DATA_POLICY_MODE is not lightweight.",
        )
    if fetcher is None and not active_settings.live_fetch_enabled:
        return _unavailable_response(
            normalized,
            now,
            active_settings,
            reason_code="lightweight_live_fetch_disabled",
            message=(
                "Fresh lightweight fetching is opt-in. Set LIGHTWEIGHT_LIVE_FETCH_ENABLED=true "
                "or run the local smoke with --live."
            ),
        )

    reuse_key = _lightweight_fetch_reuse_key(
        normalized,
        active_settings,
        fetcher=fetcher,
        chart_range=normalized_chart_range,
    )
    cache_now = time.monotonic()
    if not bypass_reuse:
        reused = _reuse_cache_get(reuse_key, active_settings, now_seconds=cache_now)
        if reused is not None:
            return reused

    blocked = _manifest_blocked_response(normalized, now, active_settings)
    if blocked is not None:
        return _reuse_cache_store_and_mark(
            reuse_key,
            blocked,
            active_settings,
            now_seconds=cache_now,
            bypass_reuse=bypass_reuse,
        )

    source_fetcher = fetcher or UrlLibJsonFetcher()
    diagnostics: dict[str, Any] = {
        "policy": "official_first_provider_fallback",
        "official_sources_attempted": [],
        "provider_fallback_attempted": False,
        "blocked_by_scope_screen": False,
        "raw_payload_exposed": False,
    }
    yahoo_quote, yahoo_sources, yahoo_facts, yahoo_errors = _try_yahoo_provider_fallback(
        normalized,
        active_settings,
        source_fetcher,
        now,
        chart_range=normalized_chart_range,
    )
    diagnostics["provider_fallback_attempted"] = bool(active_settings.provider_fallback_enabled)
    if yahoo_errors:
        diagnostics["provider_fallback_errors"] = yahoo_errors

    asset_type = _asset_type_from_quote_or_manifest(normalized, yahoo_quote)
    if asset_type is AssetType.stock:
        response = _fetch_stock(
            normalized,
            active_settings,
            source_fetcher,
            now,
            yahoo_quote=yahoo_quote,
            yahoo_sources=yahoo_sources,
            yahoo_facts=yahoo_facts,
            diagnostics=diagnostics,
        )
        return _reuse_cache_store_and_mark(
            reuse_key,
            response,
            active_settings,
            now_seconds=cache_now,
            bypass_reuse=bypass_reuse,
        )
    if asset_type is AssetType.etf:
        response = _fetch_etf(
            normalized,
            active_settings,
            now,
            yahoo_quote=yahoo_quote,
            yahoo_sources=yahoo_sources,
            yahoo_facts=yahoo_facts,
            diagnostics=diagnostics,
            no_live_external_calls=source_fetcher.no_live_external_calls,
        )
        return _reuse_cache_store_and_mark(
            reuse_key,
            response,
            active_settings,
            now_seconds=cache_now,
            bypass_reuse=bypass_reuse,
        )

    response = _unknown_response(
        normalized,
        now,
        active_settings,
        diagnostics={**diagnostics, "quote_type": (yahoo_quote or {}).get("quoteType")},
    )
    return _reuse_cache_store_and_mark(
        reuse_key,
        response,
        active_settings,
        now_seconds=cache_now,
        bypass_reuse=bypass_reuse,
    )


def _lightweight_fetch_reuse_key(
    ticker: str,
    settings: LightweightDataSettings,
    *,
    fetcher: JsonFetcher | None,
    chart_range: str,
) -> _LightweightFetchReuseKey:
    return _LightweightFetchReuseKey(
        ticker=ticker,
        chart_range=chart_range,
        asset_type_hint=_asset_type_reuse_hint(ticker),
        data_policy_mode=settings.data_policy_mode,
        live_fetch_enabled=settings.live_fetch_enabled,
        provider_fallback_enabled=settings.provider_fallback_enabled,
        sec_user_agent_redacted=settings.sec_user_agent_redacted,
        fetch_timeout_seconds=settings.fetch_timeout_seconds,
        fetcher_boundary=_fetcher_reuse_boundary(fetcher),
    )


def _asset_type_reuse_hint(ticker: str) -> str:
    if ticker in UNSUPPORTED_ASSETS:
        return AssetType.unsupported.value
    metadata = OUT_OF_SCOPE_COMMON_STOCKS.get(ticker)
    if metadata:
        return str(metadata.get("asset_type") or AssetType.stock.value)
    if top500_stock_universe_entry(ticker) is not None:
        return AssetType.stock.value
    if etf_universe_entry(ticker) is not None:
        return AssetType.etf.value
    return AssetType.unknown.value


def _fetcher_reuse_boundary(fetcher: JsonFetcher | None) -> str:
    if fetcher is None:
        return "urllib_live_fetcher"
    fetcher_type = type(fetcher)
    return f"{fetcher_type.__module__}.{fetcher_type.__qualname__}:{id(fetcher)}"


def _reuse_cache_get(
    key: _LightweightFetchReuseKey,
    settings: LightweightDataSettings,
    *,
    now_seconds: float,
) -> LightweightFetchResponse | None:
    if not settings.fetch_reuse_enabled:
        return None
    entry = _LIGHTWEIGHT_FETCH_REUSE_CACHE.get(key)
    if entry is None:
        return None
    age_seconds = max(0.0, now_seconds - entry.stored_at_seconds)
    if age_seconds > settings.fetch_reuse_ttl_seconds:
        _LIGHTWEIGHT_FETCH_REUSE_CACHE.pop(key, None)
        return None
    return _response_with_reuse_diagnostics(
        entry.response,
        key,
        settings,
        cache_status="hit",
        age_seconds=age_seconds,
        stored=False,
    )


def _reuse_cache_store_and_mark(
    key: _LightweightFetchReuseKey,
    response: LightweightFetchResponse,
    settings: LightweightDataSettings,
    *,
    now_seconds: float,
    bypass_reuse: bool,
) -> LightweightFetchResponse:
    should_store = settings.fetch_reuse_enabled and not bypass_reuse
    marked = _response_with_reuse_diagnostics(
        response,
        key,
        settings,
        cache_status="bypass" if bypass_reuse else "miss",
        age_seconds=0.0,
        stored=should_store,
    )
    if should_store:
        _LIGHTWEIGHT_FETCH_REUSE_CACHE[key] = _LightweightFetchReuseEntry(
            response=marked.model_copy(deep=True),
            stored_at_seconds=now_seconds,
        )
    return marked


def _response_with_reuse_diagnostics(
    response: LightweightFetchResponse,
    key: _LightweightFetchReuseKey,
    settings: LightweightDataSettings,
    *,
    cache_status: str,
    age_seconds: float,
    stored: bool,
) -> LightweightFetchResponse:
    diagnostics = {
        **response.diagnostics,
        "lightweight_fetch_reuse": {
            "schema_version": "lightweight-fetch-reuse-v1",
            "cache_status": cache_status,
            "enabled": settings.fetch_reuse_enabled,
            "ttl_seconds": settings.fetch_reuse_ttl_seconds,
            "age_seconds": round(age_seconds, 6),
            "stored": stored,
            "key_context": {
                "ticker": key.ticker,
                "chart_range": key.chart_range,
                "asset_type_hint": key.asset_type_hint,
                "data_policy_mode": key.data_policy_mode,
                "live_fetch_enabled": key.live_fetch_enabled,
                "provider_fallback_enabled": key.provider_fallback_enabled,
                "fetcher_boundary": key.fetcher_boundary.split(":", 1)[0],
            },
            "raw_payload_exposed": False,
            "secret_values_exposed": False,
        },
    }
    return response.model_copy(deep=True, update={"diagnostics": diagnostics})


def _fetch_stock(
    ticker: str,
    settings: LightweightDataSettings,
    fetcher: JsonFetcher,
    retrieved_at: str,
    *,
    yahoo_quote: dict[str, Any] | None,
    yahoo_sources: list[LightweightFetchSource],
    yahoo_facts: list[LightweightFetchFact],
    diagnostics: dict[str, Any],
) -> LightweightFetchResponse:
    sources = list(yahoo_sources)
    facts = list(yahoo_facts)
    gaps: list[LightweightFetchFact] = []
    official_errors: list[dict[str, str]] = []
    sec_row: dict[str, Any] | None = None

    try:
        diagnostics["official_sources_attempted"].append("sec_company_tickers_exchange")
        sec_index = fetcher.fetch_json(
            "https://www.sec.gov/files/company_tickers_exchange.json",
            user_agent=settings._sec_user_agent,
            timeout_seconds=settings.fetch_timeout_seconds,
        )
        sec_row = _sec_row_for_ticker(sec_index, ticker)
        if sec_row is not None:
            source = _sec_source(
                ticker,
                "sec_company_tickers_exchange",
                "SEC company tickers and exchanges",
                "https://www.sec.gov/files/company_tickers_exchange.json",
                retrieved_at,
                as_of_date=None,
            )
            sources.append(source)
            facts.append(
                _fact(
                    ticker,
                    "sec_identity",
                    {
                        "ticker": ticker,
                        "company_name": sec_row.get("name"),
                        "cik": _padded_cik(sec_row.get("cik")),
                        "exchange": sec_row.get("exchange"),
                        "source_label": LightweightSourceLabel.official.value,
                    },
                    EvidenceState.supported,
                    FreshnessState.fresh,
                    retrieved_at,
                    source,
                )
            )
    except Exception as exc:
        official_errors.append({"source": "sec_company_tickers_exchange", "error_type": type(exc).__name__})

    cik = _padded_cik(sec_row.get("cik")) if sec_row else None
    latest_filing_date: str | None = None
    if cik:
        try:
            diagnostics["official_sources_attempted"].append("sec_submissions")
            submissions = fetcher.fetch_json(
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                user_agent=settings._sec_user_agent,
                timeout_seconds=settings.fetch_timeout_seconds,
            )
            latest_filing = _latest_filing_metadata(submissions)
            latest_filing_date = latest_filing.get("filing_date")
            source = _sec_source(
                ticker,
                "sec_submissions",
                f"{ticker} SEC submissions",
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                retrieved_at,
                as_of_date=latest_filing_date,
            )
            sources.append(source)
            facts.append(
                _fact(
                    ticker,
                    "latest_sec_filing",
                    latest_filing,
                    EvidenceState.supported if latest_filing else EvidenceState.partial,
                    FreshnessState.fresh if latest_filing else FreshnessState.unknown,
                    retrieved_at,
                    source,
                    as_of_date=latest_filing_date,
                )
            )
        except Exception as exc:
            official_errors.append({"source": "sec_submissions", "error_type": type(exc).__name__})

        try:
            diagnostics["official_sources_attempted"].append("sec_companyfacts")
            companyfacts = fetcher.fetch_json(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                user_agent=settings._sec_user_agent,
                timeout_seconds=settings.fetch_timeout_seconds,
            )
            revenue = _latest_revenue_fact(companyfacts)
            net_income = _latest_gaap_fact(
                companyfacts,
                ("NetIncomeLoss", "ProfitLoss"),
                unit="USD",
                label="Net income",
            )
            assets = _latest_gaap_fact(
                companyfacts,
                ("Assets",),
                unit="USD",
                label="Total assets",
            )
            source = _sec_source(
                ticker,
                "sec_companyfacts",
                f"{ticker} SEC XBRL company facts",
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                retrieved_at,
                as_of_date=(revenue or {}).get("end"),
            )
            sources.append(source)
            if revenue:
                facts.append(
                    _fact(
                        ticker,
                        "latest_revenue_fact",
                        revenue,
                        EvidenceState.supported,
                        FreshnessState.fresh,
                        retrieved_at,
                        source,
                        as_of_date=revenue.get("end"),
                    )
                )
            else:
                gaps.append(
                    _gap(ticker, "latest_revenue_fact", "SEC company facts did not expose a parsed revenue field.", retrieved_at)
                )
            if net_income:
                facts.append(
                    _fact(
                        ticker,
                        "latest_net_income_fact",
                        net_income,
                        EvidenceState.supported,
                        FreshnessState.fresh,
                        retrieved_at,
                        source,
                        as_of_date=net_income.get("end"),
                    )
                )
            if assets:
                facts.append(
                    _fact(
                        ticker,
                        "latest_assets_fact",
                        assets,
                        EvidenceState.supported,
                        FreshnessState.fresh,
                        retrieved_at,
                        source,
                        as_of_date=assets.get("end"),
                    )
                )
        except Exception as exc:
            official_errors.append({"source": "sec_companyfacts", "error_type": type(exc).__name__})

    if not sec_row:
        gaps.append(
            _gap(
                ticker,
                "sec_identity",
                "SEC company ticker metadata was unavailable; provider fallback is labeled when present.",
                retrieved_at,
            )
        )
    if official_errors:
        diagnostics["official_source_errors"] = official_errors

    asset = AssetIdentity(
        ticker=ticker,
        name=str((sec_row or {}).get("name") or (yahoo_quote or {}).get("longname") or (yahoo_quote or {}).get("shortname") or ticker),
        asset_type=AssetType.stock,
        exchange=str((sec_row or {}).get("exchange") or (yahoo_quote or {}).get("exchange") or ""),
        issuer=None,
        status=AssetStatus.supported,
        supported=True,
    )
    return _response_from_parts(
        ticker,
        asset,
        settings,
        retrieved_at,
        sources=sources,
        facts=facts,
        gaps=gaps,
        diagnostics=diagnostics,
        no_live_external_calls=fetcher.no_live_external_calls,
        message="Lightweight stock fetch used SEC official data first and Yahoo-labeled provider fallback where available.",
        preferred_as_of=latest_filing_date,
    )


def _fetch_etf(
    ticker: str,
    settings: LightweightDataSettings,
    retrieved_at: str,
    *,
    yahoo_quote: dict[str, Any] | None,
    yahoo_sources: list[LightweightFetchSource],
    yahoo_facts: list[LightweightFetchFact],
    diagnostics: dict[str, Any],
    no_live_external_calls: bool,
) -> LightweightFetchResponse:
    entry = etf_universe_entry(ticker)
    sources: list[LightweightFetchSource] = []
    facts: list[LightweightFetchFact] = []
    gaps: list[LightweightFetchFact] = []
    name = str((yahoo_quote or {}).get("longname") or (yahoo_quote or {}).get("shortname") or (entry.fund_name if entry else ticker))
    disqualifiers = _etf_scope_disqualifiers(ticker, name)
    if disqualifiers:
        diagnostics["blocked_by_scope_screen"] = True
        diagnostics["scope_disqualifiers"] = disqualifiers
        return _blocked_response(
            ticker,
            AssetType.etf,
            name,
            retrieved_at,
            settings,
            LightweightFetchState.out_of_scope,
            f"{ticker} looks like an ETF outside the lightweight in-scope ETF screen: {', '.join(disqualifiers)}.",
            diagnostics=diagnostics,
        )

    manifest_source: LightweightFetchSource | None = None
    if entry is not None:
        manifest_source = LightweightFetchSource(
            source_document_id=f"lw_manifest_{ticker.lower()}_etf_universe",
            source_label=LightweightSourceLabel.partial,
            source_type="local_etf_manifest_signal",
            title="Local supported ETF universe signal",
            publisher="Learn the Ticker local manifest",
            url="data/universes/us_equity_etfs_supported.current.json",
            is_official=False,
            source_quality=SourceQuality.fixture,
            source_use_policy=SourceUsePolicy.metadata_only,
            as_of_date=entry.snapshot_date,
            retrieved_at=retrieved_at,
            date_precision="day",
            freshness_state=entry.evidence.freshness_state,
            fallback_reason="Manifest metadata is a support/scope signal; fresh display fields come from labeled provider fallback.",
            rights_note="Local manifest metadata is operational scope metadata, not investment advice.",
            export_allowed=True,
        )
        sources.append(manifest_source)
        facts.append(
            _fact(
                ticker,
                "etf_manifest_scope_signal",
                {
                    "fund_name": entry.fund_name,
                    "issuer": entry.issuer,
                    "support_state": entry.support_state.value,
                    "etf_category": entry.etf_category.value,
                    "source_label": LightweightSourceLabel.partial.value,
                },
                EvidenceState.partial,
                entry.evidence.freshness_state,
                retrieved_at,
                manifest_source,
                as_of_date=entry.snapshot_date,
                fallback_used=True,
                limitations="Manifest metadata is not issuer evidence; provider fallback supplies fresh local-test fields.",
            )
        )
    else:
        gaps.append(
            _gap(
                ticker,
                "etf_manifest_scope_signal",
                "Ticker was not present in local ETF manifests; lightweight scope screen is heuristic and partial.",
                retrieved_at,
            )
        )

    diagnostics["official_sources_attempted"].append("deterministic_etf_issuer_adapter")
    issuer_sources, issuer_facts, issuer_gaps, issuer_diagnostics = _try_etf_issuer_enrichment(
        ticker,
        entry,
        retrieved_at,
    )
    sources = [*issuer_sources, *sources, *yahoo_sources]
    facts = [*issuer_facts, *facts, *yahoo_facts]
    gaps.extend(issuer_gaps)
    diagnostics.update(issuer_diagnostics)

    if not yahoo_sources:
        gaps.append(
            _gap(
                ticker,
                "provider_fallback",
                "ETF issuer automation did not resolve fresh fields and Yahoo-labeled provider fallback was unavailable.",
                retrieved_at,
            )
        )

    preferred_as_of = _latest_as_of(issuer_sources) if issuer_sources else None
    asset = AssetIdentity(
        ticker=ticker,
        name=name,
        asset_type=AssetType.etf,
        exchange=str((yahoo_quote or {}).get("exchange") or (entry.exchange if entry else "") or ""),
        issuer=entry.issuer if entry else None,
        status=AssetStatus.supported,
        supported=True,
    )
    return _response_from_parts(
        ticker,
        asset,
        settings,
        retrieved_at,
        sources=sources,
        facts=facts,
        gaps=gaps,
        diagnostics=diagnostics,
        no_live_external_calls=no_live_external_calls,
        message=(
            "Lightweight ETF fetch used deterministic issuer evidence before manifest/provider fallback."
            if issuer_sources
            else "Lightweight ETF fetch used manifest/scope metadata and Yahoo-labeled provider fallback while issuer evidence remains unavailable."
        ),
        preferred_as_of=preferred_as_of,
    )


def _try_etf_issuer_enrichment(
    ticker: str,
    entry: Any,
    retrieved_at: str,
) -> tuple[list[LightweightFetchSource], list[LightweightFetchFact], list[LightweightFetchFact], dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "issuer_enrichment_attempted": True,
        "issuer_enrichment_source": "deterministic_etf_issuer_adapter",
        "issuer_enrichment_state": "unavailable",
        "issuer_enrichment_no_live_external_calls": True,
    }
    try:
        from backend.providers import mock_etf_issuer_adapter

        adapter = mock_etf_issuer_adapter()
        response = adapter.fetch(adapter.request(ticker))
    except Exception as exc:
        diagnostics.update(
            {
                "issuer_enrichment_state": "adapter_error",
                "issuer_enrichment_error_type": type(exc).__name__,
            }
        )
        return (
            [],
            [],
            [
                _gap(
                    ticker,
                    "etf_issuer_evidence",
                    "Deterministic ETF issuer evidence is unavailable for this local-MVP slice row.",
                    retrieved_at,
                )
            ],
            diagnostics,
        )

    diagnostics["issuer_enrichment_state"] = response.state.value
    diagnostics["issuer_enrichment_no_live_external_calls"] = response.no_live_external_calls
    if response.state.value != "supported":
        return (
            [],
            [],
            [
                _gap(
                    ticker,
                    "etf_issuer_evidence",
                    "No deterministic issuer fixture is available for this ETF slice row; issuer facts stay partial or unavailable.",
                    retrieved_at,
                )
            ],
            diagnostics,
        )

    if not _valid_etf_issuer_response_binding(ticker, entry, response):
        diagnostics["issuer_enrichment_state"] = "binding_rejected"
        return (
            [],
            [],
            [
                _gap(
                    ticker,
                    "etf_issuer_evidence",
                    "Deterministic issuer fixture failed same-ticker, same-fund, same-issuer, or source-use binding checks.",
                    retrieved_at,
                )
            ],
            diagnostics,
        )

    source_by_id = {
        source.source_document_id: _source_from_etf_issuer_attribution(source, retrieved_at)
        for source in response.source_attributions
    }
    facts: list[LightweightFetchFact] = []
    gaps: list[LightweightFetchFact] = []
    for provider_fact in response.facts:
        if provider_fact.evidence_state is EvidenceState.supported and provider_fact.source_document_ids:
            facts.append(_fact_from_etf_issuer_provider_fact(provider_fact, source_by_id, retrieved_at))
        else:
            gaps.append(
                LightweightFetchFact(
                    fact_id=f"lw_gap_{ticker.lower()}_{provider_fact.field_name}",
                    field_name=provider_fact.field_name,
                    value=provider_fact.value,
                    evidence_state=provider_fact.evidence_state,
                    freshness_state=provider_fact.freshness_state,
                    as_of_date=provider_fact.as_of_date,
                    retrieved_at=retrieved_at,
                    source_labels=[LightweightSourceLabel.unavailable],
                    fallback_used=False,
                    limitations=str(provider_fact.value),
                )
            )

    diagnostics.update(
        {
            "issuer_enrichment_state": "supported",
            "issuer_enrichment_source_count": len(source_by_id),
            "issuer_enrichment_fact_count": len(facts),
            "issuer_enrichment_gap_count": len(gaps),
            "issuer_enrichment_raw_payload_exposed": False,
        }
    )
    return list(source_by_id.values()), facts, gaps, diagnostics


def _valid_etf_issuer_response_binding(ticker: str, entry: Any, response: Any) -> bool:
    asset = response.asset
    if asset is None or asset.ticker != ticker or asset.asset_type is not AssetType.etf:
        return False
    if entry is not None:
        if asset.name != entry.fund_name or asset.issuer != entry.issuer:
            return False
    if not response.no_live_external_calls:
        return False
    if not response.source_attributions or not response.facts:
        return False
    for source in response.source_attributions:
        if source.asset_ticker != ticker or not source.is_official:
            return False
        if source.publisher != asset.issuer:
            return False
        if source.source_use_policy is SourceUsePolicy.rejected:
            return False
        if source.allowlist_status is not SourceAllowlistStatus.allowed:
            return False
        if not source.can_support_canonical_facts:
            return False
        if not source.permitted_operations.can_support_citations:
            return False
        if not source.permitted_operations.can_support_canonical_facts:
            return False
        if source.parser_status.value != "parsed":
            return False
        if getattr(source, "raw_payload_exposed", False):
            return False
    source_ids = {source.source_document_id for source in response.source_attributions}
    for fact in response.facts:
        if fact.asset_ticker != ticker or fact.uses_glossary_as_support:
            return False
        if set(fact.source_document_ids) - source_ids:
            return False
    return True


def _source_from_etf_issuer_attribution(source: Any, retrieved_at: str) -> LightweightFetchSource:
    return LightweightFetchSource(
        source_document_id=source.source_document_id,
        source_label=LightweightSourceLabel.official,
        source_type=source.source_type,
        title=source.title,
        publisher=source.publisher,
        url=source.url,
        is_official=True,
        source_quality=source.source_quality,
        source_use_policy=source.source_use_policy,
        allowlist_status=source.allowlist_status,
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=retrieved_at,
        date_precision="day" if source.as_of_date or source.published_at else "unknown",
        freshness_state=source.freshness_state,
        fallback_reason=None,
        rights_note=(
            "Official issuer fixture metadata is used for lightweight local-MVP display; raw issuer documents "
            "and unrestricted source text are not exposed by this response."
        ),
        export_allowed=source.permitted_operations.can_export_metadata,
    )


def _fact_from_etf_issuer_provider_fact(
    fact: Any,
    source_by_id: dict[str, LightweightFetchSource],
    retrieved_at: str,
) -> LightweightFetchFact:
    source_ids = [source_id for source_id in fact.source_document_ids if source_id in source_by_id]
    return LightweightFetchFact(
        fact_id=fact.fact_id.replace("provider_", "lw_issuer_", 1),
        field_name=fact.field_name,
        value=fact.value,
        evidence_state=fact.evidence_state,
        freshness_state=fact.freshness_state,
        as_of_date=fact.as_of_date,
        retrieved_at=retrieved_at,
        source_document_ids=source_ids,
        source_labels=[source_by_id[source_id].source_label for source_id in source_ids],
        fallback_used=False,
        limitations=None,
    )


def _try_yahoo_provider_fallback(
    ticker: str,
    settings: LightweightDataSettings,
    fetcher: JsonFetcher,
    retrieved_at: str,
    *,
    chart_range: str = DEFAULT_CHART_RANGE,
) -> tuple[dict[str, Any] | None, list[LightweightFetchSource], list[LightweightFetchFact], list[dict[str, str]]]:
    if not settings.provider_fallback_enabled:
        return None, [], [], [{"source": "yahoo_finance", "error_type": "provider_fallback_disabled"}]
    sources: list[LightweightFetchSource] = []
    facts: list[LightweightFetchFact] = []
    errors: list[dict[str, str]] = []
    quote_payload: dict[str, Any] | None = None
    quote_summary: dict[str, Any] = {}
    chart_payload: dict[str, Any] = {}
    chart_meta: dict[str, Any] = {}
    provider_user_agent = YAHOO_PROVIDER_USER_AGENT
    normalized_chart_range = normalize_chart_range(chart_range) or DEFAULT_CHART_RANGE
    chart_interval = chart_interval_for_range(normalized_chart_range)

    try:
        search_payload = fetcher.fetch_json(
            f"https://query1.finance.yahoo.com/v1/finance/search?q={quote(ticker)}&quotesCount=5&newsCount=0",
            user_agent=provider_user_agent,
            timeout_seconds=settings.fetch_timeout_seconds,
        )
        quote_payload = _exact_yahoo_quote(search_payload, ticker)
    except Exception as exc:
        errors.append({"source": "yahoo_search", "error_type": type(exc).__name__})

    try:
        chart_payload = fetcher.fetch_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}"
            f"?range={quote(normalized_chart_range)}&interval={quote(chart_interval)}",
            user_agent=provider_user_agent,
            timeout_seconds=settings.fetch_timeout_seconds,
        )
        chart_meta = _chart_meta(chart_payload)
    except Exception as exc:
        errors.append({"source": "yahoo_chart", "error_type": type(exc).__name__})

    try:
        modules = ",".join(
            [
                "price",
                "summaryProfile",
                "fundProfile",
                "topHoldings",
                "fundPerformance",
                "summaryDetail",
                "defaultKeyStatistics",
                "financialData",
            ]
        )
        quote_summary_payload = fetcher.fetch_json(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{quote(ticker)}?modules={modules}",
            user_agent=provider_user_agent,
            timeout_seconds=settings.fetch_timeout_seconds,
        )
        quote_summary = _quote_summary_result(quote_summary_payload)
    except Exception as exc:
        errors.append({"source": "yahoo_quote_summary", "error_type": type(exc).__name__})

    merged = {**(quote_payload or {}), **chart_meta}
    if not merged:
        return quote_payload, sources, facts, errors

    provider_as_of = _market_time_as_of(merged) or _chart_latest_as_of(chart_payload)
    source = LightweightFetchSource(
        source_document_id=f"lw_yahoo_{ticker.lower()}_chart_search",
        source_label=LightweightSourceLabel.provider_derived,
        source_type="provider_market_reference",
        title=f"{ticker} Yahoo Finance/yfinance-derived normalized reference",
        publisher="Yahoo Finance",
        url=f"https://finance.yahoo.com/quote/{quote(ticker)}",
        is_official=False,
        source_quality=SourceQuality.provider,
        source_use_policy=SourceUsePolicy.summary_allowed,
        published_at=None,
        as_of_date=provider_as_of,
        retrieved_at=retrieved_at,
        date_precision="day" if provider_as_of else "unknown",
        freshness_state=FreshnessState.fresh,
        fallback_reason="Official issuer/SEC data was incomplete for some local-test fields.",
        rights_note=YAHOO_RIGHTS_NOTE,
        export_allowed=False,
    )
    sources.append(source)
    facts.append(
        _fact(
            ticker,
            "provider_identity_or_market_reference",
            _compact_market_reference(merged),
            EvidenceState.partial,
            FreshnessState.fresh,
            retrieved_at,
            source,
            as_of_date=source.as_of_date,
            fallback_used=True,
            limitations="Provider-derived fallback is useful for local testing but is not official issuer or SEC evidence.",
        )
    )
    market_price = _market_price_reference(merged)
    if market_price:
        facts.append(
            _fact(
                ticker,
                "provider_market_price",
                market_price,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived market price is delayed/reference data for local testing, not trading advice.",
            )
        )
    profile = _provider_profile_overview(merged, quote_summary)
    if profile:
        facts.append(
            _fact(
                ticker,
                "provider_profile_overview",
                profile,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived profile fields are normalized display fallback, not official issuer or SEC evidence.",
            )
        )
    quote_stats = _provider_quote_stats(merged, quote_summary)
    if quote_stats:
        facts.append(
            _fact(
                ticker,
                "provider_quote_stats",
                quote_stats,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived quote and fund stats are normalized display fallback, not official issuer or SEC evidence.",
            )
        )
    top_holdings = _provider_top_holdings(quote_summary)
    if top_holdings:
        facts.append(
            _fact(
                ticker,
                "provider_top_holdings",
                top_holdings,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived holdings are used only as a labeled fallback when official holdings rows are incomplete.",
            )
        )
    sector_weightings = _provider_sector_weightings(quote_summary)
    if sector_weightings:
        facts.append(
            _fact(
                ticker,
                "provider_sector_weightings",
                sector_weightings,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived sector weights are normalized display fallback, not official issuer evidence.",
            )
        )
    fund_performance = _provider_fund_performance(quote_summary)
    if fund_performance:
        facts.append(
            _fact(
                ticker,
                "provider_fund_performance",
                fund_performance,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=fund_performance.get("as_of_date") or source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived performance fields are educational context and not a forecast or recommendation.",
            )
        )
    stock_metrics = _provider_stock_metric_groups(quote_summary, merged)
    if stock_metrics:
        facts.append(
            _fact(
                ticker,
                "provider_stock_metric_groups",
                stock_metrics,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived stock metrics are source-labeled enrichment and remain separate from SEC facts.",
            )
        )
    price_chart = _price_chart_reference(chart_payload, range_label=normalized_chart_range, interval=chart_interval)
    if price_chart:
        facts.append(
            _fact(
                ticker,
                "provider_price_chart",
                price_chart,
                EvidenceState.partial,
                FreshnessState.fresh,
                retrieved_at,
                source,
                as_of_date=price_chart.get("as_of_date") or source.as_of_date,
                fallback_used=True,
                limitations="Provider-derived chart points are delayed or best-effort reference data, not trading guidance.",
            )
        )
    return merged, sources, facts, errors


def _response_from_parts(
    ticker: str,
    asset: AssetIdentity,
    settings: LightweightDataSettings,
    retrieved_at: str,
    *,
    sources: list[LightweightFetchSource],
    facts: list[LightweightFetchFact],
    gaps: list[LightweightFetchFact],
    diagnostics: dict[str, Any],
    no_live_external_calls: bool,
    message: str,
    preferred_as_of: str | None = None,
) -> LightweightFetchResponse:
    source_by_id = {source.source_document_id: source for source in sources}
    citations = [
        LightweightFetchCitation(
            citation_id=f"lw_cite_{source.source_document_id.removeprefix('lw_')}",
            source_document_id=source.source_document_id,
            title=source.title,
            publisher=source.publisher,
            source_label=source.source_label,
            freshness_state=source.freshness_state,
        )
        for source in sources
    ]
    citation_by_source = {citation.source_document_id: citation.citation_id for citation in citations}
    facts = [
        fact.model_copy(update={"citation_ids": [citation_by_source[source_id] for source_id in fact.source_document_ids if source_id in citation_by_source]})
        for fact in facts
    ]
    has_official = any(source.source_label is LightweightSourceLabel.official for source in sources)
    has_provider = any(source.source_label is LightweightSourceLabel.provider_derived for source in sources)
    page_state = EvidenceState.supported if has_official and facts else EvidenceState.partial if facts else EvidenceState.unavailable
    fetch_state = LightweightFetchState.supported if page_state is EvidenceState.supported else LightweightFetchState.partial if facts else LightweightFetchState.unavailable
    as_of = preferred_as_of or _latest_as_of([*sources, *source_by_id.values()])
    return _with_fallback_diagnostics(
        LightweightFetchResponse(
            ticker=ticker,
            data_policy_mode=DataPolicyMode(settings.data_policy_mode),
            fetch_state=fetch_state,
            asset=asset,
            generated_output_eligible=fetch_state in {LightweightFetchState.supported, LightweightFetchState.partial},
            page_render_state=page_state,
            source_priority=[
                "official_sources",
                "local_manifest_scope_signal",
                "reputable_provider_fallback" if has_provider else "provider_fallback_unavailable",
                "partial_or_unavailable_states",
            ],
            freshness=Freshness(
                page_last_updated_at=retrieved_at,
                facts_as_of=as_of,
                holdings_as_of=as_of if asset.asset_type is AssetType.etf else None,
                recent_events_as_of=None,
                freshness_state=FreshnessState.fresh if facts else FreshnessState.unavailable,
            ),
            facts=facts,
            sources=sources,
            citations=citations,
            gaps=gaps,
            diagnostics={
                **diagnostics,
                "settings": settings.safe_diagnostics,
                "official_source_count": sum(
                    1 for source in sources if source.source_label is LightweightSourceLabel.official
                ),
                "provider_fallback_source_count": sum(
                    1 for source in sources if source.source_label is LightweightSourceLabel.provider_derived
                ),
                "gap_count": len(gaps),
                "strict_audit_quality_approval": False,
                "raw_payload_exposed": False,
            },
            no_live_external_calls=no_live_external_calls,
            raw_payload_exposed=False,
            message=message,
        )
    )


def _unavailable_response(
    ticker: str,
    retrieved_at: str,
    settings: LightweightDataSettings,
    *,
    reason_code: str,
    message: str,
) -> LightweightFetchResponse:
    return _with_fallback_diagnostics(
        LightweightFetchResponse(
            ticker=ticker,
            data_policy_mode=DataPolicyMode(
                settings.data_policy_mode if settings.data_policy_mode in {"strict", "lightweight"} else "lightweight"
            ),
            fetch_state=LightweightFetchState.unavailable,
            asset=AssetIdentity(
                ticker=ticker,
                name=ticker,
                asset_type=AssetType.unknown,
                status=AssetStatus.unknown,
                supported=False,
            ),
            generated_output_eligible=False,
            page_render_state=EvidenceState.unavailable,
            source_priority=["official_sources", "reputable_provider_fallback", "partial_or_unavailable_states"],
            freshness=Freshness(
                page_last_updated_at=retrieved_at,
                facts_as_of=None,
                holdings_as_of=None,
                recent_events_as_of=None,
                freshness_state=FreshnessState.unavailable,
            ),
            diagnostics={"reason_code": reason_code, "settings": settings.safe_diagnostics},
            no_live_external_calls=True,
            message=message,
        )
    )


def _unknown_response(
    ticker: str,
    retrieved_at: str,
    settings: LightweightDataSettings,
    *,
    diagnostics: dict[str, Any],
) -> LightweightFetchResponse:
    return _with_fallback_diagnostics(
        LightweightFetchResponse(
            ticker=ticker,
            data_policy_mode=DataPolicyMode.lightweight,
            fetch_state=LightweightFetchState.unknown,
            asset=AssetIdentity(
                ticker=ticker,
                name=ticker,
                asset_type=AssetType.unknown,
                status=AssetStatus.unknown,
                supported=False,
            ),
            generated_output_eligible=False,
            page_render_state=EvidenceState.unknown,
            source_priority=["official_sources", "reputable_provider_fallback", "partial_or_unavailable_states"],
            freshness=Freshness(
                page_last_updated_at=retrieved_at,
                facts_as_of=None,
                holdings_as_of=None,
                recent_events_as_of=None,
                freshness_state=FreshnessState.unknown,
            ),
            diagnostics={**diagnostics, "settings": settings.safe_diagnostics},
            no_live_external_calls=False,
            message="No recognized stock or in-scope ETF could be resolved from official or provider fallback metadata.",
        )
    )


def _blocked_response(
    ticker: str,
    asset_type: AssetType,
    name: str,
    retrieved_at: str,
    settings: LightweightDataSettings,
    fetch_state: LightweightFetchState,
    message: str,
    *,
    diagnostics: dict[str, Any] | None = None,
) -> LightweightFetchResponse:
    return _with_fallback_diagnostics(
        LightweightFetchResponse(
            ticker=ticker,
            data_policy_mode=DataPolicyMode.lightweight,
            fetch_state=fetch_state,
            asset=AssetIdentity(
                ticker=ticker,
                name=name,
                asset_type=asset_type,
                status=AssetStatus.unsupported,
                supported=False,
            ),
            generated_output_eligible=False,
            page_render_state=EvidenceState.unsupported,
            source_priority=["scope_screen_before_generation", "partial_or_unavailable_states"],
            freshness=Freshness(
                page_last_updated_at=retrieved_at,
                facts_as_of=None,
                holdings_as_of=None,
                recent_events_as_of=None,
                freshness_state=FreshnessState.unavailable,
            ),
            diagnostics={**(diagnostics or {}), "settings": settings.safe_diagnostics, "blocked_generated_output": True},
            no_live_external_calls=True,
            message=message,
        )
    )


def _with_fallback_diagnostics(response: LightweightFetchResponse) -> LightweightFetchResponse:
    return response.model_copy(update={"fallback_diagnostics": build_lightweight_api_fallback_diagnostics(response)})


def build_lightweight_api_fallback_diagnostics(response: LightweightFetchResponse) -> LightweightApiFallbackDiagnostics:
    label_counts = Counter(source.source_label.value for source in response.sources)
    reason_codes = _fallback_reason_codes(response, label_counts)
    return LightweightApiFallbackDiagnostics(
        source_path=_fallback_source_path(response, label_counts),
        reason_codes=reason_codes,
        fetch_state=response.fetch_state,
        page_render_state=response.page_render_state,
        generated_output_eligible=response.generated_output_eligible,
        source_labels=[LightweightSourceLabel(label) for label in sorted(label_counts)],
        source_label_counts=dict(sorted(label_counts.items())),
        source_count=len(response.sources),
        citation_count=len(response.citations),
        fact_count=len(response.facts),
        gap_count=len(response.gaps),
        official_source_count=label_counts.get(LightweightSourceLabel.official.value, 0),
        provider_fallback_source_count=label_counts.get(LightweightSourceLabel.provider_derived.value, 0),
        partial_source_count=label_counts.get(LightweightSourceLabel.partial.value, 0),
        unavailable_source_count=label_counts.get(LightweightSourceLabel.unavailable.value, 0),
        issuer_evidence_state=_issuer_evidence_state(response, label_counts),
        freshness=LightweightFallbackFreshnessSummary(
            page_last_updated_at=response.freshness.page_last_updated_at,
            facts_as_of=response.freshness.facts_as_of,
            holdings_as_of=response.freshness.holdings_as_of,
            recent_events_as_of=response.freshness.recent_events_as_of,
            freshness_state=response.freshness.freshness_state,
        ),
        raw_payload_exposed=response.raw_payload_exposed or bool(response.diagnostics.get("raw_payload_exposed")),
        secret_values_exposed=False,
        raw_payload_fields_exposed=False,
        hidden_prompt_or_reasoning_exposed=False,
        diagnostics_are_sanitized=True,
    )


def _fallback_source_path(response: LightweightFetchResponse, label_counts: Counter[str]) -> str:
    if response.fetch_state in {LightweightFetchState.unsupported, LightweightFetchState.out_of_scope}:
        return "blocked_scope_screen"
    if response.fetch_state is LightweightFetchState.unknown:
        return "unknown_or_unavailable"
    if response.fetch_state is LightweightFetchState.unavailable:
        return "lightweight_fetch_unavailable"
    if response.asset.asset_type is AssetType.stock:
        if label_counts.get(LightweightSourceLabel.official.value) and label_counts.get(
            LightweightSourceLabel.provider_derived.value
        ):
            return "sec_official_provider_fallback"
        if label_counts.get(LightweightSourceLabel.official.value):
            return "sec_official"
        if label_counts.get(LightweightSourceLabel.provider_derived.value):
            return "provider_fallback_only"
        return "stock_partial_or_unavailable"
    if response.asset.asset_type is AssetType.etf:
        if response.diagnostics.get("issuer_enrichment_state") == "supported":
            return "issuer_backed_etf_provider_fallback"
        if label_counts.get(LightweightSourceLabel.partial.value) and label_counts.get(
            LightweightSourceLabel.provider_derived.value
        ):
            return "etf_manifest_scope_provider_fallback"
        if label_counts.get(LightweightSourceLabel.partial.value):
            return "etf_manifest_scope_partial"
        if label_counts.get(LightweightSourceLabel.provider_derived.value):
            return "provider_fallback_only"
        return "etf_partial_or_unavailable"
    return "unknown_or_unavailable"


def _fallback_reason_codes(response: LightweightFetchResponse, label_counts: Counter[str]) -> list[str]:
    codes: list[str] = [f"fetch_state_{response.fetch_state.value}", f"page_render_state_{response.page_render_state.value}"]
    if response.generated_output_eligible:
        codes.append("generated_output_eligible")
    else:
        codes.append("generated_output_blocked")
    if response.diagnostics.get("reason_code"):
        codes.append(str(response.diagnostics["reason_code"]))
    if response.diagnostics.get("blocked_generated_output"):
        codes.append("blocked_generated_output")
    if label_counts.get(LightweightSourceLabel.official.value):
        codes.append("official_source_evidence")
    if label_counts.get(LightweightSourceLabel.provider_derived.value):
        codes.append("provider_fallback_used")
    if label_counts.get(LightweightSourceLabel.partial.value):
        codes.append("manifest_or_partial_source_signal")
    issuer_state = _issuer_evidence_state(response, label_counts)
    if issuer_state != "not_applicable":
        codes.append(f"issuer_evidence_{issuer_state}")
    if response.gaps or response.page_render_state in {
        EvidenceState.partial,
        EvidenceState.unavailable,
        EvidenceState.unknown,
        EvidenceState.insufficient_evidence,
    }:
        codes.append("partial_or_unavailable_evidence_gaps")
    codes.append("raw_payload_hidden")
    return sorted(dict.fromkeys(codes))


def _issuer_evidence_state(response: LightweightFetchResponse, label_counts: Counter[str]) -> str:
    if response.asset.asset_type is not AssetType.etf:
        return "not_applicable"
    if response.fetch_state in {LightweightFetchState.unsupported, LightweightFetchState.out_of_scope}:
        return "blocked"
    if response.diagnostics.get("issuer_enrichment_state") == "supported":
        return "supported"
    if label_counts.get(LightweightSourceLabel.partial.value) or response.gaps:
        return "partial"
    return "unavailable"


def _manifest_blocked_response(
    ticker: str,
    retrieved_at: str,
    settings: LightweightDataSettings,
) -> LightweightFetchResponse | None:
    if ticker in UNSUPPORTED_ASSETS:
        return _blocked_response(
            ticker,
            AssetType.unsupported,
            ticker,
            retrieved_at,
            settings,
            LightweightFetchState.unsupported,
            UNSUPPORTED_ASSETS[ticker],
        )
    if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        metadata = OUT_OF_SCOPE_COMMON_STOCKS[ticker]
        return _blocked_response(
            ticker,
            AssetType(str(metadata.get("asset_type") or AssetType.stock.value)),
            str(metadata.get("name") or ticker),
            retrieved_at,
            settings,
            LightweightFetchState.out_of_scope,
            str(metadata.get("reason") or "Asset is outside the current MVP scope."),
        )
    entry = etf_universe_entry(ticker)
    if entry and entry.support_state in {ETFUniverseSupportState.recognized_unsupported, ETFUniverseSupportState.out_of_scope}:
        return _blocked_response(
            ticker,
            AssetType.etf,
            entry.fund_name,
            retrieved_at,
            settings,
            LightweightFetchState.unsupported
            if entry.support_state is ETFUniverseSupportState.recognized_unsupported
            else LightweightFetchState.out_of_scope,
            entry.entry_provenance,
        )
    return None


def _sec_source(
    ticker: str,
    source_type: str,
    title: str,
    url: str,
    retrieved_at: str,
    *,
    as_of_date: str | None,
) -> LightweightFetchSource:
    return LightweightFetchSource(
        source_document_id=f"lw_sec_{ticker.lower()}_{source_type}",
        source_label=LightweightSourceLabel.official,
        source_type=source_type,
        title=title,
        publisher="U.S. SEC",
        url=url,
        is_official=True,
        source_quality=SourceQuality.official,
        source_use_policy=SourceUsePolicy.full_text_allowed,
        allowlist_status=SourceAllowlistStatus.allowed,
        as_of_date=as_of_date,
        retrieved_at=retrieved_at,
        date_precision="day" if as_of_date else "unknown",
        freshness_state=FreshnessState.fresh,
        rights_note=SEC_RIGHTS_NOTE,
        export_allowed=True,
    )


def _fact(
    ticker: str,
    field_name: str,
    value: Any,
    evidence_state: EvidenceState,
    freshness_state: FreshnessState,
    retrieved_at: str,
    source: LightweightFetchSource,
    *,
    as_of_date: str | None = None,
    fallback_used: bool = False,
    limitations: str | None = None,
) -> LightweightFetchFact:
    return LightweightFetchFact(
        fact_id=f"lw_fact_{ticker.lower()}_{field_name}",
        field_name=field_name,
        value=value,
        evidence_state=evidence_state,
        freshness_state=freshness_state,
        as_of_date=as_of_date,
        retrieved_at=retrieved_at,
        source_document_ids=[source.source_document_id],
        source_labels=[source.source_label],
        fallback_used=fallback_used or source.source_label in {LightweightSourceLabel.provider_derived, LightweightSourceLabel.fallback},
        limitations=limitations,
    )


def _gap(ticker: str, field_name: str, message: str, retrieved_at: str) -> LightweightFetchFact:
    return LightweightFetchFact(
        fact_id=f"lw_gap_{ticker.lower()}_{field_name}",
        field_name=field_name,
        value=message,
        evidence_state=EvidenceState.partial,
        freshness_state=FreshnessState.unavailable,
        retrieved_at=retrieved_at,
        source_labels=[LightweightSourceLabel.partial],
        fallback_used=False,
        limitations=message,
    )


def _asset_type_from_quote_or_manifest(ticker: str, quote_payload: dict[str, Any] | None) -> AssetType:
    manifest_entry = top500_stock_universe_entry(ticker)
    if manifest_entry is not None:
        return AssetType.stock
    etf_entry = etf_universe_entry(ticker)
    if etf_entry is not None:
        return AssetType.etf
    quote_type = str((quote_payload or {}).get("quoteType") or (quote_payload or {}).get("typeDisp") or "").upper()
    instrument_type = str((quote_payload or {}).get("instrumentType") or "").upper()
    if quote_type == "ETF" or instrument_type == "ETF":
        return AssetType.etf
    if quote_type in {"EQUITY", "STOCK"}:
        return AssetType.stock
    return AssetType.unknown


def normalize_chart_range(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    aliases = {
        "1m": "1mo",
        "6m": "6mo",
        "all": "max",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in SUPPORTED_CHART_RANGES else None


def chart_interval_for_range(range_label: str) -> str:
    return CHART_INTERVAL_BY_RANGE.get(range_label, CHART_INTERVAL_BY_RANGE[DEFAULT_CHART_RANGE])


def _sec_row_for_ticker(payload: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    fields = payload.get("fields")
    data = payload.get("data")
    if not isinstance(fields, list) or not isinstance(data, list):
        return None
    normalized_fields = [str(field) for field in fields]
    for row in data:
        if not isinstance(row, list) or len(row) != len(normalized_fields):
            continue
        item = dict(zip(normalized_fields, row, strict=True))
        sec_ticker = normalize_ticker(str(item.get("ticker") or ""))
        if sec_ticker in {ticker, ticker.replace(".", "-")}:
            return item
    return None


def _latest_filing_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    recent = ((payload.get("filings") or {}).get("recent") or {})
    forms = recent.get("form") or []
    filing_dates = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    accession_numbers = recent.get("accessionNumber") or []
    for preferred in ("10-K", "10-Q"):
        for index, form in enumerate(forms):
            if form != preferred:
                continue
            return {
                "form_type": form,
                "filing_date": _list_value(filing_dates, index),
                "report_date": _list_value(report_dates, index),
                "accession_number": _list_value(accession_numbers, index),
                "source_label": LightweightSourceLabel.official.value,
            }
    if forms:
        return {
            "form_type": _list_value(forms, 0),
            "filing_date": _list_value(filing_dates, 0),
            "report_date": _list_value(report_dates, 0),
            "accession_number": _list_value(accession_numbers, 0),
            "source_label": LightweightSourceLabel.official.value,
        }
    return {}


def _latest_revenue_fact(payload: dict[str, Any]) -> dict[str, Any] | None:
    return _latest_gaap_fact(
        payload,
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
        unit="USD",
        label="Revenue",
    )


def _latest_gaap_fact(
    payload: dict[str, Any],
    concepts: tuple[str, ...],
    *,
    unit: str,
    label: str,
) -> dict[str, Any] | None:
    facts = ((payload.get("facts") or {}).get("us-gaap") or {})
    for concept in concepts:
        concept_payload = facts.get(concept) or {}
        units = concept_payload.get("units") or {}
        unit_facts = units.get(unit) or []
        if not isinstance(unit_facts, list) or not unit_facts:
            continue
        sorted_facts = sorted(
            [item for item in unit_facts if isinstance(item, dict) and item.get("val") is not None],
            key=lambda item: (str(item.get("filed") or ""), str(item.get("end") or "")),
            reverse=True,
        )
        if sorted_facts:
            item = sorted_facts[0]
            return {
                "concept": concept,
                "label": concept_payload.get("label") or label,
                "value": item.get("val"),
                "unit": unit,
                "fy": item.get("fy"),
                "fp": item.get("fp"),
                "form": item.get("form"),
                "filed": item.get("filed"),
                "end": item.get("end"),
                "source_label": LightweightSourceLabel.official.value,
            }
    return None


def _exact_yahoo_quote(payload: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    quotes = payload.get("quotes")
    if not isinstance(quotes, list):
        return None
    for quote_payload in quotes:
        if not isinstance(quote_payload, dict):
            continue
        if normalize_ticker(str(quote_payload.get("symbol") or "")) == ticker:
            return quote_payload
    return None


def _chart_meta(payload: dict[str, Any]) -> dict[str, Any]:
    result = ((payload.get("chart") or {}).get("result") or [])
    if not result or not isinstance(result[0], dict):
        return {}
    meta = result[0].get("meta") or {}
    return meta if isinstance(meta, dict) else {}


def _quote_summary_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = ((payload.get("quoteSummary") or {}).get("result") or [])
    if not result or not isinstance(result[0], dict):
        return {}
    return result[0]


def _provider_profile_overview(market_reference: dict[str, Any], quote_summary: dict[str, Any]) -> dict[str, Any]:
    summary_profile = _module(quote_summary, "summaryProfile")
    fund_profile = _module(quote_summary, "fundProfile")
    summary_detail = _module(quote_summary, "summaryDetail")
    default_stats = _module(quote_summary, "defaultKeyStatistics")
    financial_data = _module(quote_summary, "financialData")
    price = _module(quote_summary, "price")
    officers = summary_profile.get("companyOfficers") if isinstance(summary_profile.get("companyOfficers"), list) else []
    ceo = _company_ceo(officers)
    fields = {
        "symbol": market_reference.get("symbol") or _clean_text(price.get("symbol")),
        "name": market_reference.get("longname") or market_reference.get("shortname") or _display_value(price.get("longName")),
        "quote_type": market_reference.get("quoteType") or market_reference.get("instrumentType"),
        "exchange": market_reference.get("fullExchangeName") or market_reference.get("exchangeName") or market_reference.get("exchange"),
        "currency": market_reference.get("currency") or _display_value(price.get("currency")),
        "category": _clean_text(fund_profile.get("categoryName")),
        "fund_family": _clean_text(fund_profile.get("family")),
        "legal_type": _clean_text(fund_profile.get("legalType")),
        "net_assets": _metric_payload(summary_detail.get("totalAssets") or default_stats.get("totalAssets"), unit="USD"),
        "yield": _percent_payload(summary_detail.get("yield")),
        "ytd_return": _percent_payload(summary_detail.get("ytdReturn")),
        "sector": _clean_text(summary_profile.get("sector")),
        "industry": _clean_text(summary_profile.get("industry")),
        "ceo": ceo,
        "full_time_employees": _number_value(summary_profile.get("fullTimeEmployees")),
        "long_business_summary": _clean_text(summary_profile.get("longBusinessSummary")),
        "market_cap": _metric_payload(price.get("marketCap") or default_stats.get("marketCap"), unit="USD"),
        "enterprise_value": _metric_payload(default_stats.get("enterpriseValue"), unit="USD"),
        "trailing_pe": _metric_payload(summary_detail.get("trailingPE")),
        "forward_pe": _metric_payload(summary_detail.get("forwardPE")),
        "eps_ttm": _metric_payload(default_stats.get("trailingEps")),
        "forward_eps": _metric_payload(default_stats.get("forwardEps")),
        "dividend_yield": _percent_payload(summary_detail.get("dividendYield")),
        "revenue_ttm": _metric_payload(financial_data.get("totalRevenue"), unit="USD"),
        "free_cash_flow": _metric_payload(financial_data.get("freeCashflow"), unit="USD"),
    }
    return {key: value for key, value in fields.items() if _present(value)}


def _provider_quote_stats(market_reference: dict[str, Any], quote_summary: dict[str, Any]) -> dict[str, Any]:
    summary_detail = _module(quote_summary, "summaryDetail")
    default_stats = _module(quote_summary, "defaultKeyStatistics")
    fund_profile = _module(quote_summary, "fundProfile")
    profile = _provider_profile_overview(market_reference, quote_summary)
    rows = [
        _quote_stat(
            "previous_close",
            "Previous Close",
            _first_present(summary_detail.get("previousClose"), market_reference.get("chartPreviousClose")),
            value_type="currency",
        ),
        _quote_stat("open", "Open", _first_present(summary_detail.get("open"), market_reference.get("regularMarketOpen")), value_type="currency"),
        _quote_stat(
            "day_range",
            "Day's Range",
            _range_display(
                _first_present(summary_detail.get("dayLow"), market_reference.get("regularMarketDayLow")),
                _first_present(summary_detail.get("dayHigh"), market_reference.get("regularMarketDayHigh")),
            ),
        ),
        _quote_stat(
            "fifty_two_week_range",
            "52 Week Range",
            _range_display(
                _first_present(summary_detail.get("fiftyTwoWeekLow"), market_reference.get("fiftyTwoWeekLow")),
                _first_present(summary_detail.get("fiftyTwoWeekHigh"), market_reference.get("fiftyTwoWeekHigh")),
            ),
        ),
        _quote_stat("bid", "Bid", _quote_price_size(summary_detail.get("bid"), summary_detail.get("bidSize")), value_type="currency"),
        _quote_stat("ask", "Ask", _quote_price_size(summary_detail.get("ask"), summary_detail.get("askSize")), value_type="currency"),
        _quote_stat(
            "volume",
            "Volume",
            _first_present(summary_detail.get("volume"), market_reference.get("regularMarketVolume")),
            value_type="number",
        ),
        _quote_stat(
            "average_volume",
            "Avg. Volume",
            _first_present(summary_detail.get("averageVolume"), market_reference.get("averageDailyVolume3Month")),
            value_type="number",
        ),
        _quote_stat("net_assets", "Net Assets", profile.get("net_assets") or _metric_payload(summary_detail.get("totalAssets"), unit="USD"), value_type="currency"),
        _quote_stat("nav", "NAV", _first_present(summary_detail.get("navPrice"), summary_detail.get("nav")), value_type="currency"),
        _quote_stat("pe_ratio_ttm", "PE Ratio (TTM)", _first_present(summary_detail.get("trailingPE"), profile.get("trailing_pe")), value_type="number"),
        _quote_stat("yield", "Yield", profile.get("yield") or _percent_payload(summary_detail.get("yield")), value_type="percent"),
        _quote_stat("ytd_return", "YTD Daily Total Return", profile.get("ytd_return") or _percent_payload(summary_detail.get("ytdReturn")), value_type="percent"),
        _quote_stat("beta_5y_monthly", "Beta (5Y Monthly)", _first_present(default_stats.get("beta"), summary_detail.get("beta")), value_type="number"),
        _quote_stat(
            "expense_ratio",
            "Expense Ratio (net)",
            _first_present(
                _percent_payload(summary_detail.get("annualReportExpenseRatio")),
                _percent_payload(default_stats.get("annualReportExpenseRatio")),
                _percent_payload(fund_profile.get("annualReportExpenseRatio")),
                _percent_payload(fund_profile.get("expenseRatio")),
            ),
            value_type="percent",
        ),
    ]
    rows = [row for row in rows if row.get("value") not in (None, "")]
    return {"rows": rows, "source_label": LightweightSourceLabel.provider_derived.value} if rows else {}


def _provider_top_holdings(quote_summary: dict[str, Any]) -> list[dict[str, Any]]:
    top_holdings = _module(quote_summary, "topHoldings")
    holdings = top_holdings.get("holdings")
    if not isinstance(holdings, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(holdings, start=1):
        if not isinstance(item, dict):
            continue
        symbol = _clean_text(item.get("symbol"))
        name = _clean_text(item.get("holdingName") or item.get("name"))
        weight = _percent_value(item.get("holdingPercent"))
        if not (symbol or name or weight is not None):
            continue
        normalized.append(
            {
                "rank": index,
                "symbol": symbol,
                "name": name or symbol or f"Holding {index}",
                "weight": weight,
                "unit": "percent_weight",
                "source_label": LightweightSourceLabel.provider_derived.value,
            }
        )
    return normalized[:10]


def _provider_sector_weightings(quote_summary: dict[str, Any]) -> list[dict[str, Any]]:
    top_holdings = _module(quote_summary, "topHoldings")
    sectors = top_holdings.get("sectorWeightings")
    if not isinstance(sectors, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in sectors:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            weight = _percent_value(value)
            if weight is None:
                continue
            normalized.append(
                {
                    "sector": _sector_label(str(key)),
                    "weight": weight,
                    "unit": "percent_weight",
                    "source_label": LightweightSourceLabel.provider_derived.value,
                }
            )
    return sorted(normalized, key=lambda row: float(row.get("weight") or 0), reverse=True)


def _provider_fund_performance(quote_summary: dict[str, Any]) -> dict[str, Any]:
    module = _module(quote_summary, "fundPerformance")
    trailing = _module(module, "trailingReturns")
    trailing_rows: list[dict[str, Any]] = []
    for key, label in [
        ("ytd", "YTD"),
        ("oneMonth", "1-Month"),
        ("threeMonth", "3-Month"),
        ("oneYear", "1-Year"),
        ("threeYear", "3-Year"),
        ("fiveYear", "5-Year"),
        ("tenYear", "10-Year"),
        ("lastBullMkt", "Last Bull Market"),
        ("lastBearMkt", "Last Bear Market"),
    ]:
        value = _percent_value(trailing.get(key))
        if value is not None:
            trailing_rows.append({"period": label, "return": value, "unit": "percent"})

    annual_module = _module(module, "annualTotalReturns")
    annual_rows: list[dict[str, Any]] = []
    returns = annual_module.get("returns")
    if isinstance(returns, list):
        for item in returns:
            if not isinstance(item, dict):
                continue
            year = _clean_text(item.get("year"))
            value = _percent_value(item.get("annualValue"))
            if year and value is not None:
                annual_rows.append({"year": year, "return": value, "unit": "percent"})

    as_of_date = _date_from_yahoo(trailing.get("asOfDate") or annual_module.get("asOfDate"))
    result = {
        "trailing_returns": trailing_rows,
        "annual_returns": annual_rows,
        "as_of_date": as_of_date,
        "source_label": LightweightSourceLabel.provider_derived.value,
    }
    return {key: value for key, value in result.items() if _present(value)}


def _provider_stock_metric_groups(quote_summary: dict[str, Any], market_reference: dict[str, Any]) -> dict[str, Any]:
    profile = _provider_profile_overview(market_reference, quote_summary)
    summary_detail = _module(quote_summary, "summaryDetail")
    default_stats = _module(quote_summary, "defaultKeyStatistics")
    financial_data = _module(quote_summary, "financialData")
    groups = [
        {
            "group_id": "market_value_enterprise_value",
            "title": "Market Value / Enterprise Value",
            "metrics": [
                _provider_metric("market_cap", "Market cap", profile.get("market_cap")),
                _provider_metric("enterprise_value", "Enterprise value", profile.get("enterprise_value")),
            ],
        },
        {
            "group_id": "price_performance",
            "title": "Price Performance",
            "metrics": [
                _provider_metric("fifty_two_week_change", "52-week change", _percent_payload(summary_detail.get("52WeekChange"))),
                _provider_metric("sandp_fifty_two_week_change", "S&P 500 52-week change", _percent_payload(summary_detail.get("SandP52WeekChange"))),
            ],
        },
        {
            "group_id": "income_statement",
            "title": "Income Statement Snapshot",
            "metrics": [
                _provider_metric("total_revenue", "Revenue TTM", _metric_payload(financial_data.get("totalRevenue"), unit="USD")),
                _provider_metric("gross_profit", "Gross profit", _metric_payload(financial_data.get("grossProfits"), unit="USD")),
                _provider_metric("revenue_growth", "Revenue growth", _percent_payload(financial_data.get("revenueGrowth"))),
                _provider_metric("ebitda", "EBITDA", _metric_payload(financial_data.get("ebitda"), unit="USD")),
            ],
        },
        {
            "group_id": "balance_sheet",
            "title": "Balance Sheet Snapshot",
            "metrics": [
                _provider_metric("total_cash", "Cash", _metric_payload(financial_data.get("totalCash"), unit="USD")),
                _provider_metric("total_debt", "Debt", _metric_payload(financial_data.get("totalDebt"), unit="USD")),
                _provider_metric("current_ratio", "Current ratio", _metric_payload(financial_data.get("currentRatio"))),
            ],
        },
        {
            "group_id": "cash_flow",
            "title": "Cash Flow Snapshot",
            "metrics": [
                _provider_metric("operating_cashflow", "Operating cash flow", _metric_payload(financial_data.get("operatingCashflow"), unit="USD")),
                _provider_metric("free_cashflow", "Free cash flow", _metric_payload(financial_data.get("freeCashflow"), unit="USD")),
            ],
        },
        {
            "group_id": "valuation_ratios",
            "title": "Valuation Ratios",
            "metrics": [
                _provider_metric("trailing_pe", "P/E", _metric_payload(summary_detail.get("trailingPE"))),
                _provider_metric("forward_pe", "Forward P/E", _metric_payload(summary_detail.get("forwardPE"))),
                _provider_metric("price_to_book", "Price/book", _metric_payload(default_stats.get("priceToBook"))),
                _provider_metric("enterprise_to_ebitda", "EV/EBITDA", _metric_payload(default_stats.get("enterpriseToEbitda"))),
            ],
        },
        {
            "group_id": "margins_returns_ownership",
            "title": "Margins, Returns, And Ownership",
            "metrics": [
                _provider_metric("gross_margin", "Gross margin", _percent_payload(financial_data.get("grossMargins"))),
                _provider_metric("operating_margin", "Operating margin", _percent_payload(financial_data.get("operatingMargins"))),
                _provider_metric("profit_margin", "Profit margin", _percent_payload(financial_data.get("profitMargins"))),
                _provider_metric("return_on_assets", "Return on assets", _percent_payload(financial_data.get("returnOnAssets"))),
                _provider_metric("return_on_equity", "Return on equity", _percent_payload(financial_data.get("returnOnEquity"))),
                _provider_metric("institutional_ownership", "Institutional ownership", _percent_payload(default_stats.get("heldPercentInstitutions"))),
            ],
        },
        {
            "group_id": "profile",
            "title": "Profile",
            "metrics": [
                _provider_metric("sector", "Sector", profile.get("sector")),
                _provider_metric("industry", "Industry", profile.get("industry")),
                _provider_metric("ceo", "CEO", profile.get("ceo")),
                _provider_metric("eps_ttm", "EPS TTM", profile.get("eps_ttm")),
                _provider_metric("dividend_yield", "Dividend yield", profile.get("dividend_yield")),
            ],
        },
    ]
    groups = [
        group | {"metrics": [metric for metric in group["metrics"] if metric.get("value") is not None]}
        for group in groups
    ]
    groups = [group for group in groups if group["metrics"]]
    return {"groups": groups, "source_label": LightweightSourceLabel.provider_derived.value} if groups else {}


def _price_chart_reference(payload: dict[str, Any], *, range_label: str, interval: str) -> dict[str, Any]:
    result = ((payload.get("chart") or {}).get("result") or [])
    if not result or not isinstance(result[0], dict):
        return {}
    item = result[0]
    timestamps = item.get("timestamp") if isinstance(item.get("timestamp"), list) else []
    quote_payloads = ((item.get("indicators") or {}).get("quote") or [])
    quote_payload = quote_payloads[0] if quote_payloads and isinstance(quote_payloads[0], dict) else {}
    closes = quote_payload.get("close") if isinstance(quote_payload.get("close"), list) else []
    volumes = quote_payload.get("volume") if isinstance(quote_payload.get("volume"), list) else []
    points: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        close = _list_value(closes, index)
        if not isinstance(timestamp, (int, float)) or not isinstance(close, (int, float)):
            continue
        volume = _list_value(volumes, index)
        points.append(
            {
                "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "close": float(close),
                "volume": volume if isinstance(volume, (int, float)) else None,
            }
        )
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    if not points:
        return {}
    return {
        "range": range_label,
        "interval": interval,
        "currency": meta.get("currency"),
        "points": points,
        "as_of_date": points[-1]["timestamp"][:10],
        "delayed_or_best_effort_label": "Yahoo Finance/yfinance-derived delayed or best-effort chart points",
        "source_label": LightweightSourceLabel.provider_derived.value,
    }


def _compact_market_reference(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "symbol",
            "shortname",
            "longname",
            "quoteType",
            "typeDisp",
            "instrumentType",
            "exchange",
            "exchangeName",
            "fullExchangeName",
            "currency",
            "regularMarketPrice",
            "chartPreviousClose",
            "regularMarketTime",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
        )
        if payload.get(key) is not None
    }


def _market_price_reference(payload: dict[str, Any]) -> dict[str, Any] | None:
    price = payload.get("regularMarketPrice")
    previous_close = payload.get("chartPreviousClose")
    if price is None and previous_close is None:
        return None
    return {
        key: payload.get(key)
        for key in (
            "symbol",
            "regularMarketPrice",
            "chartPreviousClose",
            "currency",
            "regularMarketTime",
            "fullExchangeName",
        )
        if payload.get(key) is not None
    }


def _market_time_as_of(payload: dict[str, Any]) -> str | None:
    value = payload.get("regularMarketTime")
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()


def _chart_latest_as_of(payload: dict[str, Any]) -> str | None:
    result = ((payload.get("chart") or {}).get("result") or [])
    if not result or not isinstance(result[0], dict):
        return None
    timestamps = result[0].get("timestamp")
    if not isinstance(timestamps, list):
        return None
    numeric = [timestamp for timestamp in timestamps if isinstance(timestamp, (int, float))]
    if not numeric:
        return None
    return datetime.fromtimestamp(max(numeric), tz=timezone.utc).date().isoformat()


def _module(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _clean_text(value: Any) -> str | None:
    display = _display_value(value)
    if display is None:
        return None
    text = str(display).strip()
    return text or None


def _display_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("fmt", "longFmt", "shortFmt"):
            if value.get(key) not in (None, ""):
                return value.get(key)
        return value.get("raw")
    return value


def _number_value(value: Any) -> float | int | None:
    if isinstance(value, dict):
        value = value.get("raw")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _percent_value(value: Any) -> float | None:
    numeric = _number_value(value)
    if numeric is None:
        return None
    percent = float(numeric)
    if abs(percent) <= 1:
        percent *= 100
    return round(percent, 4)


def _metric_payload(value: Any, *, unit: str | None = None) -> dict[str, Any] | None:
    numeric = _number_value(value)
    display = _clean_text(value)
    if numeric is None and display is None:
        return None
    return {key: item for key, item in {"value": numeric if numeric is not None else display, "display": display, "unit": unit}.items() if item is not None}


def _percent_payload(value: Any) -> dict[str, Any] | None:
    percent = _percent_value(value)
    display = _clean_text(value)
    if percent is None and display is None:
        return None
    return {
        key: item
        for key, item in {"value": percent if percent is not None else display, "display": display, "unit": "%"}.items()
        if item is not None
    }


def _provider_metric(metric_id: str, label: str, payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        value = payload.get("display") or payload.get("value")
        unit = payload.get("unit")
    else:
        value = payload
        unit = None
    return {"metric_id": metric_id, "label": label, "value": value, "unit": unit}


def _quote_stat(metric_id: str, label: str, payload: Any, *, value_type: str = "text") -> dict[str, Any]:
    value, unit = _display_payload(payload)
    return {
        key: item
        for key, item in {
            "metric_id": metric_id,
            "label": label,
            "value": value,
            "unit": unit,
            "value_type": value_type,
            "source_label": LightweightSourceLabel.provider_derived.value,
        }.items()
        if item is not None
    }


def _display_payload(payload: Any) -> tuple[Any, str | None]:
    if isinstance(payload, dict):
        return payload.get("display") or payload.get("value") or _display_value(payload), payload.get("unit")
    return _display_value(payload), None


def _first_present(*values: Any) -> Any:
    for value in values:
        if _present(value):
            return value
    return None


def _range_display(low: Any, high: Any) -> str | None:
    low_display = _clean_text(low)
    high_display = _clean_text(high)
    if low_display and high_display:
        return f"{low_display} - {high_display}"
    return low_display or high_display


def _quote_price_size(price: Any, size: Any) -> str | None:
    price_display = _clean_text(price)
    size_display = _clean_text(size)
    if price_display and size_display:
        return f"{price_display} x {size_display}"
    return price_display


def _company_ceo(officers: list[Any]) -> str | None:
    for officer in officers:
        if not isinstance(officer, dict):
            continue
        title = str(officer.get("title") or "").lower()
        if "chief executive" in title or title == "ceo" or " ceo" in f" {title}":
            return _clean_text(officer.get("name"))
    for officer in officers:
        if isinstance(officer, dict):
            name = _clean_text(officer.get("name"))
            if name:
                return name
    return None


def _date_from_yahoo(value: Any) -> str | None:
    numeric = _number_value(value)
    if numeric is not None:
        return datetime.fromtimestamp(float(numeric), tz=timezone.utc).date().isoformat()
    text = _clean_text(value)
    return text


def _sector_label(value: str) -> str:
    explicit = {
        "technology": "Technology",
        "financial_services": "Financial Services",
        "communication_services": "Communication Services",
        "consumer_cyclical": "Consumer Cyclical",
        "consumer_defensive": "Consumer Defensive",
        "healthcare": "Healthcare",
        "industrials": "Industrials",
        "energy": "Energy",
        "utilities": "Utilities",
        "realestate": "Real Estate",
        "real_estate": "Real Estate",
        "basic_materials": "Basic Materials",
    }
    normalized = value.strip().lower()
    return explicit.get(normalized, normalized.replace("_", " ").title())


def _present(value: Any) -> bool:
    if value is None:
        return False
    if value == "":
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def _etf_scope_disqualifiers(ticker: str, name: str) -> list[str]:
    if ticker in UNSUPPORTED_ASSETS or ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        return ["manifest_blocked"]
    lower = f"{ticker} {name}".lower()
    return [marker for marker in ETF_SCOPE_DISQUALIFIER_MARKERS if marker in lower]


def _validate_lightweight_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise LightweightFetchError("lightweight_fetch_requires_https")
    if parsed.username or parsed.password:
        raise LightweightFetchError("lightweight_fetch_url_credentials_rejected")
    hostname = (parsed.hostname or "").lower()
    if hostname not in ALLOWED_LIGHTWEIGHT_HOSTS:
        raise LightweightFetchError("lightweight_fetch_host_not_allowed")


def _is_yahoo_finance_url(url: str) -> bool:
    return (urlsplit(url).hostname or "").lower() in {"query1.finance.yahoo.com", "finance.yahoo.com"}


def _fetch_yahoo_json_with_crumb(
    url: str,
    *,
    user_agent: str,
    timeout_seconds: int,
    max_bytes: int,
) -> dict[str, Any]:
    _validate_lightweight_url(url)
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    seed_url = _yahoo_cookie_seed_url(url)
    _validate_lightweight_url(seed_url)
    seed_request = Request(seed_url, headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"})
    with opener.open(seed_request, timeout=timeout_seconds) as seed_response:  # noqa: S310 - guarded by _validate_lightweight_url.
        seed_response.read(2048)
    crumb_url = "https://query1.finance.yahoo.com/v1/test/getcrumb"
    _validate_lightweight_url(crumb_url)
    crumb_request = Request(crumb_url, headers={"User-Agent": user_agent, "Accept": "text/plain"})
    with opener.open(crumb_request, timeout=timeout_seconds) as crumb_response:  # noqa: S310 - guarded by _validate_lightweight_url.
        crumb = crumb_response.read(512).decode("utf-8").strip()
    if not crumb:
        raise LightweightFetchError("yahoo_crumb_unavailable")
    request = Request(_append_query_param(url, "crumb", crumb), headers={"User-Agent": user_agent, "Accept": "application/json"})
    with opener.open(request, timeout=timeout_seconds) as response:  # noqa: S310 - guarded by _validate_lightweight_url.
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise LightweightFetchError("lightweight_source_payload_too_large")
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise LightweightFetchError("lightweight_source_payload_not_json_object")
    return parsed


def _yahoo_cookie_seed_url(url: str) -> str:
    parsed = urlsplit(url)
    parts = [part for part in parsed.path.split("/") if part]
    ticker = "SPY"
    if parts:
        ticker = parts[-1].upper()
    return f"https://finance.yahoo.com/quote/{quote(ticker)}"


def _append_query_param(url: str, key: str, value: str) -> str:
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.append((key, value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _padded_cik(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(int(value)).zfill(10)
    except (TypeError, ValueError):
        text = str(value).strip()
        return text.zfill(10) if text.isdigit() else None


def _list_value(items: Any, index: int) -> Any:
    if isinstance(items, list) and index < len(items):
        return items[index]
    return None


def _latest_as_of(sources: list[LightweightFetchSource]) -> str | None:
    dates = sorted({source.as_of_date for source in sources if source.as_of_date})
    return dates[-1] if dates else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def lightweight_payload_checksum(payload: LightweightFetchResponse) -> str:
    body = json.dumps(payload.model_dump(mode="json", exclude={"diagnostics"}), sort_keys=True)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()
