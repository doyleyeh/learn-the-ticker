from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

if os.environ.get("LTT_FORCE_COMPAT_FASTAPI") == "1":
    from backend.compat import FastAPI, HTTPException
else:
    try:
        from fastapi import FastAPI, HTTPException
    except ModuleNotFoundError:  # pragma: no cover - exercised only in dependency-free local gates.
        from backend.compat import FastAPI, HTTPException
try:
    from fastapi.middleware.cors import CORSMiddleware
except ModuleNotFoundError:  # pragma: no cover - exercised only when FastAPI is unavailable.
    CORSMiddleware = None

from backend.data import (
    STUB_TIMESTAMP,
    empty_freshness,
    fallback_asset,
    state_for_asset,
    supported_asset,
)
from backend.chat_sessions import answer_chat_with_session, delete_chat_session, get_chat_session_status
from backend.comparison import generate_comparison
from backend.export import (
    export_asset_page,
    export_asset_source_list,
    export_chat_session_transcript,
    export_chat_transcript,
    export_comparison,
)
from backend.ingestion import (
    get_ingestion_job_status,
    get_pre_cache_job_status,
    request_ingestion,
    request_launch_universe_pre_cache,
    request_pre_cache_for_asset,
)
from backend.glossary import build_glossary_response
from backend.lightweight_data_fetch import (
    DEFAULT_CHART_RANGE,
    SUPPORTED_CHART_RANGES,
    fetch_lightweight_asset_data,
    normalize_chart_range,
)
from backend.lightweight_page import (
    build_lightweight_details_response,
    build_lightweight_overview_response,
    build_lightweight_sources_response,
    build_lightweight_weekly_news_response,
    fetch_lightweight_page_data_if_enabled,
    persist_lightweight_evidence_if_configured,
)
from backend.llm import runtime_diagnostics
from backend.analysis_packs import (
    analysis_pack_repository,
    build_backend_generated_metadata,
    build_economic_indicators_pack,
)
from backend.economic_indicators_live import EconomicIndicatorFetchError, build_live_economic_indicators_pack
from backend.market_news_runtime import build_runtime_market_news_response
from backend.models import (
    AssetChartResponse,
    AssetIdentity,
    AssetPageResponse,
    AssetStatus,
    AnalysisPackImportBundle,
    AnalysisPackImportResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionDeleteResponse,
    ChatSessionStatusResponse,
    ChatTranscriptExportRequest,
    ComparisonExportRequest,
    CompareRequest,
    CompareResponse,
    DetailsResponse,
    ExportFormat,
    ExportResponse,
    GlossaryResponse,
    EconomicIndicatorsPackResponse,
    IngestionJobResponse,
    KnowledgePackBuildResponse,
    LightweightFetchResponse,
    LlmRuntimeDiagnosticsResponse,
    MarketNewsResponse,
    OverviewResponse,
    PreCacheBatchResponse,
    PreCacheJobResponse,
    RecentResponse,
    SearchResponse,
    SourcesResponse,
    StateMessage,
    TrustMetricCatalogResponse,
    TrustMetricValidationRequest,
    TrustMetricValidationResponse,
    WeeklyNewsResponse,
    Citation,
    FreshnessState,
)
from backend.overview import generate_asset_overview
from backend.persistence import (
    BackendReadDependencies,
    backend_read_dependencies_from_app,
    build_backend_read_dependencies_from_local_durable_config,
    configure_backend_read_dependencies,
)
from backend.retrieval import build_asset_knowledge_pack_result
from backend.retrieval_repository import read_persisted_knowledge_pack_response
from backend.search import search_assets
from backend.section_states import response_section_state, with_section_states
from backend.settings import (
    build_admin_route_settings,
    build_cors_settings,
    build_economic_indicators_settings,
    build_lightweight_data_settings,
)
from backend.sources import build_asset_source_drawer_response
from backend.trust_metrics import get_trust_metric_event_catalog, validate_trust_metric_events


def configure_cors_middleware(fastapi_app: FastAPI) -> None:
    settings = build_cors_settings()
    fastapi_app.state.cors_settings = settings.safe_diagnostics
    if not settings.enabled or CORSMiddleware is None or not hasattr(fastapi_app, "add_middleware"):
        return

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=list(settings.allowed_methods),
        allow_headers=["*"],
        allow_credentials=settings.allow_credentials,
    )


app = FastAPI(
    title="Learn the Ticker Backend",
    version="0.1.0",
    description="Deterministic FastAPI skeleton for citation-first stock and ETF education.",
)
configure_cors_middleware(app)
configure_backend_read_dependencies(app, build_backend_read_dependencies_from_local_durable_config())


def _asset_payload(ticker: str) -> tuple[AssetIdentity, dict[str, Any] | None]:
    payload = supported_asset(ticker)
    if payload:
        return payload["identity"], payload
    return fallback_asset(ticker), None


def _read_dependencies() -> BackendReadDependencies:
    return backend_read_dependencies_from_app(app)


def _require_admin_routes_enabled() -> None:
    settings = build_admin_route_settings()
    app.state.admin_route_settings = settings.safe_diagnostics
    if not settings.enabled:
        raise HTTPException(status_code=404, detail="Admin routes are disabled in this environment.")


def _with_route_section_state(
    response: Any,
    section_id: str,
    label: str,
    **overrides: Any,
) -> Any:
    return with_section_states(response, [response_section_state(response, section_id, label, **overrides)])


def _with_market_news_section_states(response: MarketNewsResponse) -> MarketNewsResponse:
    origin_state = response_section_state(response, "market_news", "Market News Focus")
    states = [
        response_section_state(
            response.market_news_focus,
            "market_news",
            "Market News Focus",
            data_origin=origin_state.data_origin,
            fallback_reason=origin_state.fallback_reason,
        ).model_copy(update={"source_handoff_state": origin_state.source_handoff_state}),
        _ai_generation_section_state(
            response.market_ai_comprehensive_analysis,
            "market_ai_comprehensive_analysis",
            "Market AI Comprehensive Analysis",
            data_origin=origin_state.data_origin,
            fallback_reason=origin_state.fallback_reason,
        ),
    ]
    return with_section_states(response, states)


def _with_weekly_news_section_states(response: WeeklyNewsResponse) -> WeeklyNewsResponse:
    origin_state = response_section_state(response, "weekly_news", "Weekly News Focus")
    return with_section_states(
        response,
        [
            response_section_state(
                response.weekly_news_focus,
                "weekly_news",
                "Weekly News Focus",
                data_origin=origin_state.data_origin,
                fallback_reason=origin_state.fallback_reason,
            ),
            _ai_generation_section_state(
                response.ai_comprehensive_analysis,
                "ai_comprehensive_analysis",
                "AI Comprehensive Analysis",
                data_origin=origin_state.data_origin,
                fallback_reason=origin_state.fallback_reason,
            ),
        ],
    )


def _ai_generation_section_state(
    response: Any,
    section_id: str,
    label: str,
    *,
    data_origin: str,
    fallback_reason: str | None = None,
) -> Any:
    diagnostics = _generation_diagnostics_payload(response)
    generation_fallback_reason = fallback_reason or _generation_fallback_reason(response)
    analysis_available = bool(getattr(response, "analysis_available", False))
    state_value = str(getattr(getattr(response, "state", None), "value", getattr(response, "state", "")))

    if not analysis_available or state_value in {"suppressed", "no_high_signal", "insufficient_evidence"}:
        return response_section_state(
            response,
            section_id,
            label,
            data_origin=data_origin,
            section_status="insufficient_evidence",
            fallback_reason=generation_fallback_reason or getattr(response, "suppression_reason", None),
            evidence_state="insufficient_evidence",
            diagnostics=diagnostics,
        )

    if bool(getattr(getattr(response, "generation_diagnostics", None), "used_fallback", False)):
        return response_section_state(
            response,
            section_id,
            label,
            data_origin=data_origin,
            section_status="partial",
            fallback_reason=generation_fallback_reason or "deterministic_generation_fallback",
            evidence_state="partial",
            diagnostics=diagnostics,
        )

    return response_section_state(
        response,
        section_id,
        label,
        data_origin=data_origin,
        fallback_reason=fallback_reason,
        diagnostics=diagnostics,
    )


def _generation_diagnostics_payload(response: Any) -> dict[str, str | int | float | bool | None | list[str]]:
    diagnostics = getattr(response, "generation_diagnostics", None)
    if diagnostics is None:
        return {}
    return {
        "attempted_live": bool(getattr(diagnostics, "attempted_live", False)),
        "used_fallback": bool(getattr(diagnostics, "used_fallback", False)),
        "fallback_reason_codes": list(getattr(diagnostics, "fallback_reason_codes", []) or []),
        "model_name": getattr(diagnostics, "model_name", None),
    }


def _generation_fallback_reason(response: Any) -> str | None:
    diagnostics = getattr(response, "generation_diagnostics", None)
    if diagnostics is None:
        return None
    reason_codes = list(getattr(diagnostics, "fallback_reason_codes", []) or [])
    return ",".join(reason_codes) if reason_codes else None


def _current_economic_indicators_pack() -> EconomicIndicatorsPackResponse:
    imported = analysis_pack_repository().read_fresh_economic_indicators_pack()
    if imported is not None:
        return _with_route_section_state(imported, "economic_indicators", "Economic Indicators")

    settings = build_economic_indicators_settings()
    app.state.economic_indicators_settings = settings.safe_diagnostics
    if settings.live_fetch_enabled:
        try:
            live_pack = build_live_economic_indicators_pack(
                generated_at=_utc_now_iso(),
                timeout_seconds=settings.fetch_timeout_seconds,
            )
            return _with_route_section_state(
                live_pack.model_copy(update={"analysis_pack_metadata": build_backend_generated_metadata()}),
                "economic_indicators",
                "Economic Indicators",
                data_origin="backend_generated",
                fallback_reason=None,
                freshness_state="fresh",
            )
        except EconomicIndicatorFetchError:
            return _with_route_section_state(
                build_economic_indicators_pack(),
                "economic_indicators",
                "Economic Indicators",
                data_origin="deterministic_fixture",
                fallback_reason="economic_indicators_live_fetch_failed",
                freshness_state="unknown",
            )

    return _with_route_section_state(
        build_economic_indicators_pack(),
        "economic_indicators",
        "Economic Indicators",
        data_origin="deterministic_fixture",
        fallback_reason="economic_indicators_live_fetch_disabled",
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _asset_chart_response_from_overview(
    overview: OverviewResponse,
    *,
    requested_range: str,
    normalized_range: str,
) -> AssetChartResponse:
    chart_section = next((section for section in overview.sections if section.section_id == "price_chart"), None)
    chart = chart_section.chart if chart_section and chart_section.chart else None
    if chart and normalize_chart_range(chart.range) != normalized_range:
        chart = None
    if chart is None:
        return AssetChartResponse(
            asset=overview.asset,
            state=StateMessage(
                status=AssetStatus.unknown,
                message=f"Chart data is unavailable for {overview.asset.ticker} range {requested_range}.",
            ),
            requested_range=requested_range,
            supported_ranges=list(SUPPORTED_CHART_RANGES),
            default_range=DEFAULT_CHART_RANGE,
            chart=None,
            citations=[],
            source_documents=[],
            fallback_diagnostics=overview.fallback_diagnostics,
        )

    citation_ids = set(chart.citation_ids)
    source_document_ids = set(chart.source_document_ids)
    return AssetChartResponse(
        asset=overview.asset,
        state=overview.state,
        requested_range=requested_range,
        supported_ranges=list(SUPPORTED_CHART_RANGES),
        default_range=DEFAULT_CHART_RANGE,
        chart=chart,
        citations=[citation for citation in overview.citations if citation.citation_id in citation_ids],
        source_documents=[
            source for source in overview.source_documents if source.source_document_id in source_document_ids
        ],
        fallback_diagnostics=overview.fallback_diagnostics,
    )


def _details_from_configured_reader(ticker: str, readers: BackendReadDependencies) -> DetailsResponse | None:
    pack_reader = readers.reader("knowledge_pack_reader")
    if pack_reader is None:
        return None

    persisted = read_persisted_knowledge_pack_response(ticker, reader=pack_reader)
    if not persisted.found or persisted.response is None or persisted.records is None:
        return None
    if not persisted.response.asset.supported or not persisted.response.generated_output_available:
        return None

    source_by_id = {source.source_document_id: source for source in persisted.records.source_documents}
    facts = {
        fact.field_name: fact.value
        for fact in persisted.records.normalized_facts
        if fact.value is not None and fact.evidence_state == "supported"
    }
    citations = [
        Citation(
            citation_id=f"c_{fact.fact_id}",
            source_document_id=fact.source_document_id,
            title=source_by_id[fact.source_document_id].title if fact.source_document_id in source_by_id else None,
            publisher=source_by_id[fact.source_document_id].publisher if fact.source_document_id in source_by_id else None,
            freshness_state=FreshnessState(fact.freshness_state),
        )
        for fact in persisted.records.normalized_facts
        if fact.value is not None and fact.source_document_id in source_by_id
    ]
    return DetailsResponse(
        asset=persisted.response.asset,
        state=persisted.response.state,
        freshness=persisted.response.freshness,
        facts=facts,
        citations=citations,
    )


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "learn-the-ticker-backend", "as_of": STUB_TIMESTAMP}


@app.get("/api/search", response_model=SearchResponse, tags=["search"])
def search(q: str) -> SearchResponse:
    return search_assets(q)


@app.post("/api/admin/ingest/{ticker}", response_model=IngestionJobResponse, tags=["ingestion"])
def ingest_asset(ticker: str) -> IngestionJobResponse:
    _require_admin_routes_enabled()
    readers = _read_dependencies()
    return request_ingestion(ticker, ingestion_job_ledger=readers.reader("ingestion_job_ledger"))


@app.get("/api/jobs/{job_id}", response_model=IngestionJobResponse, tags=["ingestion"])
def ingestion_job_status(job_id: str) -> IngestionJobResponse:
    readers = _read_dependencies()
    return get_ingestion_job_status(job_id, ingestion_job_ledger=readers.reader("ingestion_job_ledger"))


@app.post("/api/admin/pre-cache/launch-universe", response_model=PreCacheBatchResponse, tags=["ingestion"])
def launch_universe_pre_cache() -> PreCacheBatchResponse:
    _require_admin_routes_enabled()
    readers = _read_dependencies()
    return request_launch_universe_pre_cache(ingestion_job_ledger=readers.reader("ingestion_job_ledger"))


@app.get("/api/admin/pre-cache/launch-universe", response_model=PreCacheBatchResponse, tags=["ingestion"])
def launch_universe_pre_cache_status() -> PreCacheBatchResponse:
    _require_admin_routes_enabled()
    readers = _read_dependencies()
    return request_launch_universe_pre_cache(ingestion_job_ledger=readers.reader("ingestion_job_ledger"))


@app.get("/api/admin/pre-cache/jobs/{job_id}", response_model=PreCacheJobResponse, tags=["ingestion"])
def pre_cache_job_status(job_id: str) -> PreCacheJobResponse:
    _require_admin_routes_enabled()
    readers = _read_dependencies()
    return get_pre_cache_job_status(job_id, ingestion_job_ledger=readers.reader("ingestion_job_ledger"))


@app.post("/api/admin/pre-cache/{ticker}", response_model=PreCacheJobResponse, tags=["ingestion"])
def pre_cache_asset(ticker: str) -> PreCacheJobResponse:
    _require_admin_routes_enabled()
    readers = _read_dependencies()
    return request_pre_cache_for_asset(ticker, ingestion_job_ledger=readers.reader("ingestion_job_ledger"))


@app.get("/api/assets/{ticker}/overview", response_model=OverviewResponse, tags=["assets"])
def asset_overview(ticker: str, mode: str = "beginner") -> OverviewResponse:
    readers = _read_dependencies()
    stable_asset_page_mode = mode in {"asset_page_stable", "stable"}
    economic_pack = None if stable_asset_page_mode else _current_economic_indicators_pack()
    lightweight_response = fetch_lightweight_page_data_if_enabled(ticker)
    if lightweight_response is not None:
        persist_lightweight_evidence_if_configured(
            lightweight_response,
            source_snapshot_repository=readers.reader("source_snapshot_repository"),
            knowledge_pack_repository=readers.reader("knowledge_pack_reader"),
        )
        overview = build_lightweight_overview_response(
            lightweight_response,
            economic_indicators=economic_pack,
            include_timely_context=not stable_asset_page_mode,
        )
        return _with_route_section_state(
            overview.model_copy(update={"economic_indicators": economic_pack}),
            "asset_overview",
            "Asset overview",
        )

    overview = generate_asset_overview(
        ticker,
        persisted_pack_reader=readers.reader("knowledge_pack_reader"),
        generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        source_snapshot_reader=readers.reader("source_snapshot_repository"),
        persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
        economic_indicators=economic_pack,
    )
    return _with_route_section_state(
        overview.model_copy(update={"economic_indicators": economic_pack}),
        "asset_overview",
        "Asset overview",
    )


@app.get("/api/economic-indicators", response_model=EconomicIndicatorsPackResponse, tags=["market-news"])
def economic_indicators() -> EconomicIndicatorsPackResponse:
    return _current_economic_indicators_pack()


@app.post(
    "/api/admin/analysis-packs/import",
    response_model=AnalysisPackImportResponse,
    tags=["market-news"],
)
def import_analysis_pack_bundle(bundle: AnalysisPackImportBundle) -> AnalysisPackImportResponse:
    _require_admin_routes_enabled()
    return analysis_pack_repository().import_bundle(bundle)


@app.get("/api/market-news", response_model=MarketNewsResponse, tags=["market-news"])
def market_news() -> MarketNewsResponse:
    imported = analysis_pack_repository().read_fresh_market_news_response()
    if imported is not None:
        return _with_market_news_section_states(imported)
    response = build_runtime_market_news_response(economic_indicators=_current_economic_indicators_pack())
    return _with_market_news_section_states(
        response.model_copy(update={"analysis_pack_metadata": build_backend_generated_metadata()})
    )


@app.get("/api/assets/{ticker}/chart", response_model=AssetChartResponse, tags=["assets"])
def asset_chart(ticker: str, range: str = DEFAULT_CHART_RANGE) -> AssetChartResponse:
    requested_range = str(range or DEFAULT_CHART_RANGE)
    normalized_range = normalize_chart_range(requested_range)
    if normalized_range is None:
        asset, _ = _asset_payload(ticker)
        return AssetChartResponse(
            asset=asset,
            state=StateMessage(
                status=AssetStatus.unknown,
                message=(
                    f"Chart range '{requested_range}' is unavailable. Supported ranges are "
                    f"{', '.join(SUPPORTED_CHART_RANGES)}."
                ),
            ),
            requested_range=requested_range,
            supported_ranges=list(SUPPORTED_CHART_RANGES),
            default_range=DEFAULT_CHART_RANGE,
            chart=None,
            citations=[],
            source_documents=[],
        )

    active_settings = build_lightweight_data_settings()
    if active_settings.can_fetch_fresh_data:
        lightweight_fetch = fetch_lightweight_asset_data(ticker, settings=active_settings, chart_range=normalized_range)
        overview = build_lightweight_overview_response(lightweight_fetch)
        return _asset_chart_response_from_overview(overview, requested_range=requested_range, normalized_range=normalized_range)

    readers = _read_dependencies()
    overview = generate_asset_overview(
        ticker,
        persisted_pack_reader=readers.reader("knowledge_pack_reader"),
        generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        source_snapshot_reader=readers.reader("source_snapshot_repository"),
        persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
    )
    return _asset_chart_response_from_overview(overview, requested_range=requested_range, normalized_range=normalized_range)


@app.get("/api/assets/{ticker}/knowledge-pack", response_model=KnowledgePackBuildResponse, tags=["assets"])
def asset_knowledge_pack(ticker: str) -> KnowledgePackBuildResponse:
    readers = _read_dependencies()
    return build_asset_knowledge_pack_result(ticker, persisted_reader=readers.reader("knowledge_pack_reader"))


@app.get("/api/assets/{ticker}/fresh-data", response_model=LightweightFetchResponse, tags=["assets"])
def asset_fresh_data(ticker: str) -> LightweightFetchResponse:
    response = fetch_lightweight_asset_data(ticker)
    readers = _read_dependencies()
    persist_lightweight_evidence_if_configured(
        response,
        source_snapshot_repository=readers.reader("source_snapshot_repository"),
        knowledge_pack_repository=readers.reader("knowledge_pack_reader"),
    )
    return response


@app.get("/api/assets/{ticker}/details", response_model=DetailsResponse, tags=["assets"])
def asset_details(ticker: str) -> DetailsResponse:
    readers = _read_dependencies()
    lightweight_response = fetch_lightweight_page_data_if_enabled(ticker)
    if lightweight_response is not None:
        persist_lightweight_evidence_if_configured(
            lightweight_response,
            source_snapshot_repository=readers.reader("source_snapshot_repository"),
            knowledge_pack_repository=readers.reader("knowledge_pack_reader"),
        )
        return _with_route_section_state(
            build_lightweight_details_response(lightweight_response),
            "asset_details",
            "Asset details",
        )

    persisted_details = _details_from_configured_reader(ticker, readers)
    if persisted_details is not None:
        return _with_route_section_state(
            persisted_details,
            "asset_details",
            "Asset details",
            data_origin="durable_repository",
        )

    asset, payload = _asset_payload(ticker)
    state = state_for_asset(asset)

    if not payload:
        return _with_route_section_state(
            DetailsResponse(asset=asset, state=state, freshness=empty_freshness(), facts={}, citations=[]),
            "asset_details",
            "Asset details",
            data_origin="unavailable",
            section_status="unavailable",
            fallback_reason="no_supported_asset_payload",
            freshness_state="unavailable",
            evidence_state="unavailable",
        )

    return _with_route_section_state(
        DetailsResponse(
            asset=asset,
            state=state,
            freshness=payload["freshness"],
            facts=payload["facts"],
            citations=payload["citations"],
        ),
        "asset_details",
        "Asset details",
    )


@app.get("/api/assets/{ticker}/sources", response_model=SourcesResponse, tags=["assets"])
def asset_sources(
    ticker: str,
    citation_id: str | None = None,
    source_document_id: str | None = None,
) -> SourcesResponse:
    readers = _read_dependencies()
    lightweight_response = fetch_lightweight_page_data_if_enabled(ticker)
    if lightweight_response is not None:
        persist_lightweight_evidence_if_configured(
            lightweight_response,
            source_snapshot_repository=readers.reader("source_snapshot_repository"),
            knowledge_pack_repository=readers.reader("knowledge_pack_reader"),
        )
        return _with_route_section_state(
            build_lightweight_sources_response(
                lightweight_response,
                citation_id=citation_id,
                source_document_id=source_document_id,
            ),
            "source_drawer",
            "Source drawer",
        )

    return _with_route_section_state(
        build_asset_source_drawer_response(
            ticker,
            citation_id=citation_id,
            source_document_id=source_document_id,
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
            source_snapshot_reader=readers.reader("source_snapshot_repository"),
            persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
        ),
        "source_drawer",
        "Source drawer",
    )


@app.get("/api/assets/{ticker}", response_model=AssetPageResponse, tags=["assets"])
def asset_page(ticker: str) -> AssetPageResponse:
    overview = asset_overview(ticker)
    details = asset_details(ticker)
    sources = asset_sources(ticker)
    return AssetPageResponse(
        asset=overview.asset,
        state=overview.state,
        overview=overview,
        details=details,
        sources=sources,
        section_states=[
            *overview.section_states,
            *details.section_states,
            *sources.section_states,
        ],
    )


@app.get("/api/assets/{ticker}/glossary", response_model=GlossaryResponse, tags=["assets"])
def asset_glossary(ticker: str, term: str | None = None) -> GlossaryResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        build_glossary_response(ticker, term=term, persisted_pack_reader=readers.reader("knowledge_pack_reader")),
        "glossary_context",
        "Glossary context",
    )


@app.get("/api/assets/{ticker}/export", response_model=ExportResponse, tags=["exports"])
def asset_page_export(ticker: str, export_format: ExportFormat = ExportFormat.markdown) -> ExportResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        export_asset_page(
            ticker,
            export_format,
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
            source_snapshot_reader=readers.reader("source_snapshot_repository"),
            persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
        ),
        "export",
        "Asset page export",
    )


@app.get("/api/assets/{ticker}/sources/export", response_model=ExportResponse, tags=["exports"])
def asset_sources_export(ticker: str, export_format: ExportFormat = ExportFormat.markdown) -> ExportResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        export_asset_source_list(
            ticker,
            export_format,
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
            source_snapshot_reader=readers.reader("source_snapshot_repository"),
            persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
        ),
        "export",
        "Asset source-list export",
    )


@app.get("/api/assets/{ticker}/recent", response_model=RecentResponse, tags=["assets"])
def asset_recent(ticker: str) -> RecentResponse:
    readers = _read_dependencies()
    overview = generate_asset_overview(
        ticker,
        persisted_pack_reader=readers.reader("knowledge_pack_reader"),
        generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        source_snapshot_reader=readers.reader("source_snapshot_repository"),
        persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
    )
    return RecentResponse(
        asset=overview.asset,
        state=overview.state,
        recent_developments=overview.recent_developments,
        citations=overview.citations,
    )


@app.get("/api/assets/{ticker}/weekly-news", response_model=WeeklyNewsResponse, tags=["assets"])
def asset_weekly_news(ticker: str) -> WeeklyNewsResponse:
    imported = analysis_pack_repository().read_fresh_weekly_news_response(ticker)
    if imported is not None:
        return _with_weekly_news_section_states(imported)

    readers = _read_dependencies()
    economic_pack = _current_economic_indicators_pack()
    lightweight_response = fetch_lightweight_page_data_if_enabled(ticker)
    if lightweight_response is not None:
        persist_lightweight_evidence_if_configured(
            lightweight_response,
            source_snapshot_repository=readers.reader("source_snapshot_repository"),
            knowledge_pack_repository=readers.reader("knowledge_pack_reader"),
        )
        response = build_lightweight_weekly_news_response(lightweight_response, economic_indicators=economic_pack)
        return _with_weekly_news_section_states(
            response.model_copy(update={"analysis_pack_metadata": build_backend_generated_metadata()})
        )

    overview = generate_asset_overview(
        ticker,
        persisted_pack_reader=readers.reader("knowledge_pack_reader"),
        generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        source_snapshot_reader=readers.reader("source_snapshot_repository"),
        persisted_weekly_news_reader=readers.reader("weekly_news_reader"),
        economic_indicators=economic_pack,
    )
    return _with_weekly_news_section_states(
        WeeklyNewsResponse(
            asset=overview.asset,
            state=overview.state,
            weekly_news_focus=overview.weekly_news_focus,
            ai_comprehensive_analysis=overview.ai_comprehensive_analysis,
            analysis_pack_metadata=build_backend_generated_metadata(),
        )
    )


@app.post("/api/compare", response_model=CompareResponse, tags=["compare"])
def compare_assets(request: CompareRequest) -> CompareResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        generate_comparison(
            request.left_ticker,
            request.right_ticker,
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        ),
        "comparison",
        "Comparison",
    )


@app.post("/api/compare/export", response_model=ExportResponse, tags=["exports"])
def compare_assets_export(request: ComparisonExportRequest) -> ExportResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        export_comparison(
            request,
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        ),
        "export",
        "Comparison export",
    )


@app.get("/api/compare/export", response_model=ExportResponse, tags=["exports"])
def compare_assets_export_query(
    left_ticker: str,
    right_ticker: str,
    export_format: ExportFormat = ExportFormat.markdown,
) -> ExportResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        export_comparison(
            ComparisonExportRequest(left_ticker=left_ticker, right_ticker=right_ticker, export_format=export_format),
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        ),
        "export",
        "Comparison export",
    )


@app.post("/api/assets/{ticker}/chat", response_model=ChatResponse, tags=["chat"])
def asset_chat(ticker: str, request: ChatRequest) -> ChatResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        answer_chat_with_session(
            ticker,
            request,
            persisted_reader=readers.reader("chat_session_reader"),
            persisted_writer=readers.reader("chat_session_writer"),
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        ),
        "asset_chat",
        "Asset chat",
    )


@app.get("/api/chat-sessions/{conversation_id}", response_model=ChatSessionStatusResponse, tags=["chat"])
def chat_session_status(conversation_id: str) -> ChatSessionStatusResponse:
    readers = _read_dependencies()
    return get_chat_session_status(conversation_id, persisted_reader=readers.reader("chat_session_reader"))


@app.post("/api/chat-sessions/{conversation_id}/delete", response_model=ChatSessionDeleteResponse, tags=["chat"])
def chat_session_delete(conversation_id: str) -> ChatSessionDeleteResponse:
    readers = _read_dependencies()
    return delete_chat_session(
        conversation_id,
        persisted_reader=readers.reader("chat_session_reader"),
        persisted_writer=readers.reader("chat_session_writer"),
    )


@app.get("/api/chat-sessions/{conversation_id}/export", response_model=ExportResponse, tags=["exports"])
def chat_session_export(
    conversation_id: str,
    export_format: ExportFormat = ExportFormat.markdown,
) -> ExportResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        export_chat_session_transcript(
            conversation_id,
            export_format,
            persisted_session_reader=readers.reader("chat_session_reader"),
        ),
        "export",
        "Chat transcript export",
    )


@app.post("/api/assets/{ticker}/chat/export", response_model=ExportResponse, tags=["exports"])
def asset_chat_export(ticker: str, request: ChatTranscriptExportRequest) -> ExportResponse:
    readers = _read_dependencies()
    return _with_route_section_state(
        export_chat_transcript(
            ticker,
            request,
            persisted_session_reader=readers.reader("chat_session_reader"),
            persisted_pack_reader=readers.reader("knowledge_pack_reader"),
            generated_output_cache_reader=readers.reader("generated_output_cache_reader"),
        ),
        "export",
        "Chat transcript export",
    )


@app.get("/api/trust-metrics/catalog", response_model=TrustMetricCatalogResponse, tags=["trust-metrics"])
def trust_metrics_catalog() -> TrustMetricCatalogResponse:
    return get_trust_metric_event_catalog()


@app.post("/api/trust-metrics/validate", response_model=TrustMetricValidationResponse, tags=["trust-metrics"])
def trust_metrics_validate(request: TrustMetricValidationRequest) -> TrustMetricValidationResponse:
    return validate_trust_metric_events(request.events)


@app.get("/api/llm/runtime", response_model=LlmRuntimeDiagnosticsResponse, tags=["llm"])
def llm_runtime() -> LlmRuntimeDiagnosticsResponse:
    settings = {
        "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "mock"),
        "LLM_LIVE_GENERATION_ENABLED": os.environ.get("LLM_LIVE_GENERATION_ENABLED", "false"),
        "OPENROUTER_BASE_URL": os.environ.get("OPENROUTER_BASE_URL"),
        "OPENROUTER_FREE_MODEL_ORDER": os.environ.get("OPENROUTER_FREE_MODEL_ORDER"),
        "OPENROUTER_PAID_FALLBACK_MODEL": os.environ.get("OPENROUTER_PAID_FALLBACK_MODEL"),
        "OPENROUTER_PAID_FALLBACK_ENABLED": os.environ.get("OPENROUTER_PAID_FALLBACK_ENABLED", "true"),
        "LLM_VALIDATION_RETRY_COUNT": os.environ.get("LLM_VALIDATION_RETRY_COUNT", "1"),
        "LLM_REASONING_SUMMARY_ONLY": os.environ.get("LLM_REASONING_SUMMARY_ONLY", "true"),
    }
    return runtime_diagnostics(settings, server_side_key_present=bool(os.environ.get("OPENROUTER_API_KEY")))
