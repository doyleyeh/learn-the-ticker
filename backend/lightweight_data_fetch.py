from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

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
ALLOWED_LIGHTWEIGHT_HOSTS = {
    "data.sec.gov",
    "www.sec.gov",
    "query1.finance.yahoo.com",
}
YAHOO_RIGHTS_NOTE = (
    "Yahoo Finance/yfinance-derived provider fallback is source-labeled and normalized for display; "
    "the raw provider payload is not displayed or exported."
)
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
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - guarded by _validate_lightweight_url.
            payload = response.read(self.max_bytes + 1)
        if len(payload) > self.max_bytes:
            raise LightweightFetchError("lightweight_source_payload_too_large")
        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise LightweightFetchError("lightweight_source_payload_not_json_object")
        return parsed


def fetch_lightweight_asset_data(
    ticker: str,
    *,
    settings: LightweightDataSettings | None = None,
    fetcher: JsonFetcher | None = None,
    retrieved_at: str | None = None,
) -> LightweightFetchResponse:
    normalized = normalize_ticker(ticker)
    active_settings = settings or build_lightweight_data_settings()
    now = retrieved_at or _utc_now()
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

    blocked = _manifest_blocked_response(normalized, now, active_settings)
    if blocked is not None:
        return blocked

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
    )
    diagnostics["provider_fallback_attempted"] = bool(active_settings.provider_fallback_enabled)
    if yahoo_errors:
        diagnostics["provider_fallback_errors"] = yahoo_errors

    asset_type = _asset_type_from_quote_or_manifest(normalized, yahoo_quote)
    if asset_type is AssetType.stock:
        return _fetch_stock(
            normalized,
            active_settings,
            source_fetcher,
            now,
            yahoo_quote=yahoo_quote,
            yahoo_sources=yahoo_sources,
            yahoo_facts=yahoo_facts,
            diagnostics=diagnostics,
        )
    if asset_type is AssetType.etf:
        return _fetch_etf(
            normalized,
            active_settings,
            now,
            yahoo_quote=yahoo_quote,
            yahoo_sources=yahoo_sources,
            yahoo_facts=yahoo_facts,
            diagnostics=diagnostics,
            no_live_external_calls=source_fetcher.no_live_external_calls,
        )

    return _unknown_response(
        normalized,
        now,
        active_settings,
        diagnostics={**diagnostics, "quote_type": (yahoo_quote or {}).get("quoteType")},
    )


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
    sources = list(yahoo_sources)
    facts = list(yahoo_facts)
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

    if not yahoo_sources:
        gaps.append(
            _gap(
                ticker,
                "provider_fallback",
                "ETF issuer automation did not resolve fresh fields and Yahoo-labeled provider fallback was unavailable.",
                retrieved_at,
            )
        )

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
        message="Lightweight ETF fetch used manifest/scope metadata and Yahoo-labeled provider fallback for fresh local-test fields.",
    )


def _try_yahoo_provider_fallback(
    ticker: str,
    settings: LightweightDataSettings,
    fetcher: JsonFetcher,
    retrieved_at: str,
) -> tuple[dict[str, Any] | None, list[LightweightFetchSource], list[LightweightFetchFact], list[dict[str, str]]]:
    if not settings.provider_fallback_enabled:
        return None, [], [], [{"source": "yahoo_finance", "error_type": "provider_fallback_disabled"}]
    sources: list[LightweightFetchSource] = []
    facts: list[LightweightFetchFact] = []
    errors: list[dict[str, str]] = []
    quote_payload: dict[str, Any] | None = None
    chart_meta: dict[str, Any] = {}

    try:
        search_payload = fetcher.fetch_json(
            f"https://query1.finance.yahoo.com/v1/finance/search?q={quote(ticker)}&quotesCount=5&newsCount=0",
            user_agent=settings._sec_user_agent,
            timeout_seconds=settings.fetch_timeout_seconds,
        )
        quote_payload = _exact_yahoo_quote(search_payload, ticker)
    except Exception as exc:
        errors.append({"source": "yahoo_search", "error_type": type(exc).__name__})

    try:
        chart_payload = fetcher.fetch_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}?range=1d&interval=1d",
            user_agent=settings._sec_user_agent,
            timeout_seconds=settings.fetch_timeout_seconds,
        )
        chart_meta = _chart_meta(chart_payload)
    except Exception as exc:
        errors.append({"source": "yahoo_chart", "error_type": type(exc).__name__})

    merged = {**(quote_payload or {}), **chart_meta}
    if not merged:
        return quote_payload, sources, facts, errors

    source = LightweightFetchSource(
        source_document_id=f"lw_yahoo_{ticker.lower()}_chart_search",
        source_label=LightweightSourceLabel.provider_derived,
        source_type="provider_market_reference",
        title=f"{ticker} Yahoo Finance/yfinance-derived market reference",
        publisher="Yahoo Finance",
        url=f"https://finance.yahoo.com/quote/{quote(ticker)}",
        is_official=False,
        source_quality=SourceQuality.provider,
        source_use_policy=SourceUsePolicy.summary_allowed,
        published_at=None,
        as_of_date=_market_time_as_of(merged),
        retrieved_at=retrieved_at,
        date_precision="day" if _market_time_as_of(merged) else "unknown",
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
    return LightweightFetchResponse(
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
            "official_source_count": sum(1 for source in sources if source.source_label is LightweightSourceLabel.official),
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


def _unavailable_response(
    ticker: str,
    retrieved_at: str,
    settings: LightweightDataSettings,
    *,
    reason_code: str,
    message: str,
) -> LightweightFetchResponse:
    return LightweightFetchResponse(
        ticker=ticker,
        data_policy_mode=DataPolicyMode(settings.data_policy_mode if settings.data_policy_mode in {"strict", "lightweight"} else "lightweight"),
        fetch_state=LightweightFetchState.unavailable,
        asset=AssetIdentity(ticker=ticker, name=ticker, asset_type=AssetType.unknown, status=AssetStatus.unknown, supported=False),
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


def _unknown_response(
    ticker: str,
    retrieved_at: str,
    settings: LightweightDataSettings,
    *,
    diagnostics: dict[str, Any],
) -> LightweightFetchResponse:
    return LightweightFetchResponse(
        ticker=ticker,
        data_policy_mode=DataPolicyMode.lightweight,
        fetch_state=LightweightFetchState.unknown,
        asset=AssetIdentity(ticker=ticker, name=ticker, asset_type=AssetType.unknown, status=AssetStatus.unknown, supported=False),
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
    return LightweightFetchResponse(
        ticker=ticker,
        data_policy_mode=DataPolicyMode.lightweight,
        fetch_state=fetch_state,
        asset=AssetIdentity(ticker=ticker, name=name, asset_type=asset_type, status=AssetStatus.unsupported, supported=False),
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
    facts = ((payload.get("facts") or {}).get("us-gaap") or {})
    for concept in ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"):
        concept_payload = facts.get(concept) or {}
        units = concept_payload.get("units") or {}
        usd_facts = units.get("USD") or []
        if not isinstance(usd_facts, list) or not usd_facts:
            continue
        sorted_facts = sorted(
            [item for item in usd_facts if isinstance(item, dict) and item.get("val") is not None],
            key=lambda item: (str(item.get("filed") or ""), str(item.get("end") or "")),
            reverse=True,
        )
        if sorted_facts:
            item = sorted_facts[0]
            return {
                "concept": concept,
                "label": concept_payload.get("label") or concept,
                "value": item.get("val"),
                "unit": "USD",
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


def _market_time_as_of(payload: dict[str, Any]) -> str | None:
    value = payload.get("regularMarketTime")
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()


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
