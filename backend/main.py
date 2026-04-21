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
    ASSETS,
    STUB_TIMESTAMP,
    empty_freshness,
    fallback_asset,
    normalize_ticker,
    state_for_asset,
    supported_asset,
)
from backend.comparison import generate_comparison
from backend.models import (
    AssetIdentity,
    AssetStatus,
    ChatCitation,
    ChatRequest,
    ChatResponse,
    CompareRequest,
    CompareResponse,
    DetailsResponse,
    OverviewResponse,
    RecentResponse,
    SearchResponse,
    SearchResult,
    SourcesResponse,
    StateMessage,
)
from backend.overview import generate_asset_overview
from backend.safety import classify_question, educational_redirect


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
    query = normalize_ticker(q)
    matches: list[SearchResult] = []

    for payload in ASSETS.values():
        identity: AssetIdentity = payload["identity"]
        name_match = q.strip().lower() in identity.name.lower()
        ticker_match = query == identity.ticker
        if ticker_match or name_match:
            matches.append(
                SearchResult(
                    ticker=identity.ticker,
                    name=identity.name,
                    asset_type=identity.asset_type,
                    exchange=identity.exchange,
                    issuer=identity.issuer,
                    supported=identity.supported,
                    status=identity.status,
                )
            )

    if matches:
        return SearchResponse(
            query=q,
            results=matches,
            state=StateMessage(status=AssetStatus.supported, message="One or more supported assets matched the query."),
        )

    fallback = fallback_asset(q)
    state = state_for_asset(fallback)
    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                ticker=fallback.ticker,
                name=fallback.name,
                asset_type=fallback.asset_type,
                exchange=fallback.exchange,
                issuer=fallback.issuer,
                supported=False,
                status=fallback.status,
                message=state.message,
            )
        ],
        state=state,
    )


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


@app.post("/api/assets/{ticker}/chat", response_model=ChatResponse, tags=["chat"])
def asset_chat(ticker: str, request: ChatRequest) -> ChatResponse:
    asset, payload = _asset_payload(ticker)
    safety_classification = classify_question(request.question, supported=payload is not None)

    if safety_classification.value == "unsupported_asset_redirect":
        return ChatResponse(
            asset=asset,
            direct_answer=state_for_asset(asset).message,
            why_it_matters="The product currently focuses on U.S.-listed common stocks and plain-vanilla ETFs.",
            citations=[],
            uncertainty=["No local asset knowledge pack is available for this ticker."],
            safety_classification=safety_classification,
        )

    if safety_classification.value == "personalized_advice_redirect":
        direct_answer, why_it_matters = educational_redirect()
        return ChatResponse(
            asset=asset,
            direct_answer=direct_answer,
            why_it_matters=why_it_matters,
            citations=[],
            uncertainty=["This skeleton does not use personal circumstances or live market data."],
            safety_classification=safety_classification,
        )

    source = payload["sources"][0]
    citation = payload["citations"][0]
    return ChatResponse(
        asset=asset,
        direct_answer=payload["summary"].what_it_is,
        why_it_matters="Understanding the basic structure helps a beginner separate stable asset facts from recent developments and personal decision-making.",
        citations=[
            ChatCitation(
                claim=payload["summary"].what_it_is,
                source_document_id=source.source_document_id,
                chunk_id=f"chk_{citation.citation_id}",
            )
        ],
        uncertainty=["This is deterministic skeleton data; full retrieval and citation validation arrive in later tasks."],
        safety_classification=safety_classification,
    )
