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
from backend.chat import generate_asset_chat
from backend.comparison import generate_comparison
from backend.export import export_asset_page, export_asset_source_list, export_chat_transcript, export_comparison
from backend.ingestion import get_ingestion_job_status, request_ingestion
from backend.models import (
    AssetIdentity,
    ChatRequest,
    ChatResponse,
    ChatTranscriptExportRequest,
    ComparisonExportRequest,
    CompareRequest,
    CompareResponse,
    DetailsResponse,
    ExportFormat,
    ExportResponse,
    IngestionJobResponse,
    OverviewResponse,
    RecentResponse,
    SearchResponse,
    SourcesResponse,
)
from backend.overview import generate_asset_overview
from backend.search import search_assets


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


@app.get("/api/assets/{ticker}/overview", response_model=OverviewResponse, tags=["assets"])
def asset_overview(ticker: str, mode: str = "beginner") -> OverviewResponse:
    return generate_asset_overview(ticker)


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
    return generate_asset_chat(ticker, request.question)


@app.post("/api/assets/{ticker}/chat/export", response_model=ExportResponse, tags=["exports"])
def asset_chat_export(ticker: str, request: ChatTranscriptExportRequest) -> ExportResponse:
    return export_chat_transcript(ticker, request)
