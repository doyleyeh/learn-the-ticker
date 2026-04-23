from __future__ import annotations

import os
from typing import Any

if os.environ.get("LTT_FORCE_COMPAT_FASTAPI") == "1":
    from backend.compat import FastAPI
else:
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError:  # pragma: no cover - exercised only in dependency-free local gates.
        from backend.compat import FastAPI

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
from backend.llm import runtime_diagnostics
from backend.models import (
    AssetIdentity,
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
    IngestionJobResponse,
    KnowledgePackBuildResponse,
    LlmRuntimeDiagnosticsResponse,
    OverviewResponse,
    PreCacheBatchResponse,
    PreCacheJobResponse,
    RecentResponse,
    SearchResponse,
    SourcesResponse,
    TrustMetricCatalogResponse,
    TrustMetricValidationRequest,
    TrustMetricValidationResponse,
    WeeklyNewsResponse,
)
from backend.overview import generate_asset_overview
from backend.retrieval import build_asset_knowledge_pack_result
from backend.search import search_assets
from backend.trust_metrics import get_trust_metric_event_catalog, validate_trust_metric_events


app = FastAPI(
    title="Learn the Ticker Backend",
    version="0.1.0",
    description="Deterministic FastAPI skeleton for citation-first stock and ETF education.",
)


def _asset_payload(ticker: str) -> tuple[AssetIdentity, dict[str, Any] | None]:
    payload = supported_asset(ticker)
    if payload:
        return payload["identity"], payload
    return fallback_asset(ticker), None


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "learn-the-ticker-backend", "as_of": STUB_TIMESTAMP}


@app.get("/api/search", response_model=SearchResponse, tags=["search"])
def search(q: str) -> SearchResponse:
    return search_assets(q)


@app.post("/api/admin/ingest/{ticker}", response_model=IngestionJobResponse, tags=["ingestion"])
def ingest_asset(ticker: str) -> IngestionJobResponse:
    return request_ingestion(ticker)


@app.get("/api/jobs/{job_id}", response_model=IngestionJobResponse, tags=["ingestion"])
def ingestion_job_status(job_id: str) -> IngestionJobResponse:
    return get_ingestion_job_status(job_id)


@app.post("/api/admin/pre-cache/launch-universe", response_model=PreCacheBatchResponse, tags=["ingestion"])
def launch_universe_pre_cache() -> PreCacheBatchResponse:
    return request_launch_universe_pre_cache()


@app.get("/api/admin/pre-cache/launch-universe", response_model=PreCacheBatchResponse, tags=["ingestion"])
def launch_universe_pre_cache_status() -> PreCacheBatchResponse:
    return request_launch_universe_pre_cache()


@app.get("/api/admin/pre-cache/jobs/{job_id}", response_model=PreCacheJobResponse, tags=["ingestion"])
def pre_cache_job_status(job_id: str) -> PreCacheJobResponse:
    return get_pre_cache_job_status(job_id)


@app.post("/api/admin/pre-cache/{ticker}", response_model=PreCacheJobResponse, tags=["ingestion"])
def pre_cache_asset(ticker: str) -> PreCacheJobResponse:
    return request_pre_cache_for_asset(ticker)


@app.get("/api/assets/{ticker}/overview", response_model=OverviewResponse, tags=["assets"])
def asset_overview(ticker: str, mode: str = "beginner") -> OverviewResponse:
    return generate_asset_overview(ticker)


@app.get("/api/assets/{ticker}/knowledge-pack", response_model=KnowledgePackBuildResponse, tags=["assets"])
def asset_knowledge_pack(ticker: str) -> KnowledgePackBuildResponse:
    return build_asset_knowledge_pack_result(ticker)


@app.get("/api/assets/{ticker}/details", response_model=DetailsResponse, tags=["assets"])
def asset_details(ticker: str) -> DetailsResponse:
    asset, payload = _asset_payload(ticker)
    state = state_for_asset(asset)

    if not payload:
        return DetailsResponse(asset=asset, state=state, freshness=empty_freshness(), facts={}, citations=[])

    return DetailsResponse(
        asset=asset,
        state=state,
        freshness=payload["freshness"],
        facts=payload["facts"],
        citations=payload["citations"],
    )


@app.get("/api/assets/{ticker}/sources", response_model=SourcesResponse, tags=["assets"])
def asset_sources(ticker: str) -> SourcesResponse:
    overview = generate_asset_overview(ticker)
    return SourcesResponse(asset=overview.asset, state=overview.state, sources=overview.source_documents)


@app.get("/api/assets/{ticker}/export", response_model=ExportResponse, tags=["exports"])
def asset_page_export(ticker: str, export_format: ExportFormat = ExportFormat.markdown) -> ExportResponse:
    return export_asset_page(ticker, export_format)


@app.get("/api/assets/{ticker}/sources/export", response_model=ExportResponse, tags=["exports"])
def asset_sources_export(ticker: str, export_format: ExportFormat = ExportFormat.markdown) -> ExportResponse:
    return export_asset_source_list(ticker, export_format)


@app.get("/api/assets/{ticker}/recent", response_model=RecentResponse, tags=["assets"])
def asset_recent(ticker: str) -> RecentResponse:
    overview = generate_asset_overview(ticker)
    return RecentResponse(
        asset=overview.asset,
        state=overview.state,
        recent_developments=overview.recent_developments,
        citations=overview.citations,
    )


@app.get("/api/assets/{ticker}/weekly-news", response_model=WeeklyNewsResponse, tags=["assets"])
def asset_weekly_news(ticker: str) -> WeeklyNewsResponse:
    overview = generate_asset_overview(ticker)
    return WeeklyNewsResponse(
        asset=overview.asset,
        state=overview.state,
        weekly_news_focus=overview.weekly_news_focus,
        ai_comprehensive_analysis=overview.ai_comprehensive_analysis,
    )


@app.post("/api/compare", response_model=CompareResponse, tags=["compare"])
def compare_assets(request: CompareRequest) -> CompareResponse:
    return generate_comparison(request.left_ticker, request.right_ticker)


@app.post("/api/compare/export", response_model=ExportResponse, tags=["exports"])
def compare_assets_export(request: ComparisonExportRequest) -> ExportResponse:
    return export_comparison(request)


@app.get("/api/compare/export", response_model=ExportResponse, tags=["exports"])
def compare_assets_export_query(
    left_ticker: str,
    right_ticker: str,
    export_format: ExportFormat = ExportFormat.markdown,
) -> ExportResponse:
    return export_comparison(
        ComparisonExportRequest(left_ticker=left_ticker, right_ticker=right_ticker, export_format=export_format)
    )


@app.post("/api/assets/{ticker}/chat", response_model=ChatResponse, tags=["chat"])
def asset_chat(ticker: str, request: ChatRequest) -> ChatResponse:
    return answer_chat_with_session(ticker, request)


@app.get("/api/chat-sessions/{conversation_id}", response_model=ChatSessionStatusResponse, tags=["chat"])
def chat_session_status(conversation_id: str) -> ChatSessionStatusResponse:
    return get_chat_session_status(conversation_id)


@app.post("/api/chat-sessions/{conversation_id}/delete", response_model=ChatSessionDeleteResponse, tags=["chat"])
def chat_session_delete(conversation_id: str) -> ChatSessionDeleteResponse:
    return delete_chat_session(conversation_id)


@app.get("/api/chat-sessions/{conversation_id}/export", response_model=ExportResponse, tags=["exports"])
def chat_session_export(
    conversation_id: str,
    export_format: ExportFormat = ExportFormat.markdown,
) -> ExportResponse:
    return export_chat_session_transcript(conversation_id, export_format)


@app.post("/api/assets/{ticker}/chat/export", response_model=ExportResponse, tags=["exports"])
def asset_chat_export(ticker: str, request: ChatTranscriptExportRequest) -> ExportResponse:
    return export_chat_transcript(ticker, request)


@app.get("/api/trust-metrics/catalog", response_model=TrustMetricCatalogResponse, tags=["trust-metrics"])
def trust_metrics_catalog() -> TrustMetricCatalogResponse:
    return get_trust_metric_event_catalog()


@app.post("/api/trust-metrics/validate", response_model=TrustMetricValidationResponse, tags=["trust-metrics"])
def trust_metrics_validate(request: TrustMetricValidationRequest) -> TrustMetricValidationResponse:
    return validate_trust_metric_events(request.events)


@app.get("/api/llm/runtime", response_model=LlmRuntimeDiagnosticsResponse, tags=["llm"])
def llm_runtime() -> LlmRuntimeDiagnosticsResponse:
    return runtime_diagnostics()
