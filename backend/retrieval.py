from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models import AssetIdentity, AssetStatus, AssetType, Freshness, FreshnessState


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_PATH = ROOT / "data" / "retrieval_fixtures.json"


class RetrievalFixtureError(ValueError):
    """Raised when local retrieval fixtures violate the citation-first contract."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceDocumentFixture(StrictModel):
    source_document_id: str
    asset_ticker: str
    source_type: str
    source_rank: int
    title: str
    publisher: str
    url: str
    published_at: str | None = None
    retrieved_at: str
    content_type: str
    is_official: bool
    freshness_state: FreshnessState
    as_of_date: str | None = None


class SourceChunkFixture(StrictModel):
    chunk_id: str
    asset_ticker: str
    source_document_id: str
    section_name: str
    chunk_order: int
    text: str
    token_count: int
    char_start: int
    char_end: int
    supported_claim_types: list[str] = Field(default_factory=list)


class NormalizedFactFixture(StrictModel):
    fact_id: str
    asset_ticker: str
    fact_type: str
    field_name: str
    value: Any
    unit: str | None = None
    period: str | None = None
    as_of_date: str | None = None
    source_document_id: str
    source_chunk_id: str
    extraction_method: str
    confidence: float
    freshness_state: FreshnessState
    evidence_state: str


class RecentDevelopmentFixture(StrictModel):
    event_id: str
    asset_ticker: str
    event_type: str
    title: str
    summary: str
    event_date: str | None = None
    source_document_id: str
    source_chunk_id: str
    importance_score: float
    freshness_state: FreshnessState
    evidence_state: str


class EvidenceGap(StrictModel):
    gap_id: str
    asset_ticker: str
    field_name: str
    evidence_state: str
    message: str
    freshness_state: FreshnessState
    source_document_id: str | None = None
    source_chunk_id: str | None = None


class AssetFixture(StrictModel):
    asset: AssetIdentity
    freshness: Freshness
    source_documents: list[SourceDocumentFixture]
    source_chunks: list[SourceChunkFixture]
    normalized_facts: list[NormalizedFactFixture]
    recent_developments: list[RecentDevelopmentFixture]
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)


class ComparisonDifferenceFixture(StrictModel):
    difference_id: str
    dimension: str
    summary: str
    fact_ids: list[str]
    source_chunk_ids: list[str]


class ComparisonFixture(StrictModel):
    comparison_pack_id: str
    left_ticker: str
    right_ticker: str
    computed_differences: list[ComparisonDifferenceFixture]


class RetrievalFixtureDataset(StrictModel):
    generated_at: str
    no_live_external_calls: bool
    unsupported_assets: dict[str, str]
    assets: list[AssetFixture]
    comparison_packs: list[ComparisonFixture] = Field(default_factory=list)


class RetrievedSourceChunk(StrictModel):
    chunk: SourceChunkFixture
    source_document: SourceDocumentFixture


class RetrievedFact(StrictModel):
    fact: NormalizedFactFixture
    source_document: SourceDocumentFixture
    source_chunk: SourceChunkFixture


class RetrievedRecentDevelopment(StrictModel):
    recent_development: RecentDevelopmentFixture
    source_document: SourceDocumentFixture
    source_chunk: SourceChunkFixture


class AssetKnowledgePack(StrictModel):
    asset: AssetIdentity
    freshness: Freshness
    source_documents: list[SourceDocumentFixture] = Field(default_factory=list)
    normalized_facts: list[RetrievedFact] = Field(default_factory=list)
    source_chunks: list[RetrievedSourceChunk] = Field(default_factory=list)
    recent_developments: list[RetrievedRecentDevelopment] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)


class ComparisonKnowledgePack(StrictModel):
    comparison_pack_id: str
    left_asset_pack: AssetKnowledgePack
    right_asset_pack: AssetKnowledgePack
    computed_differences: list[ComparisonDifferenceFixture]
    comparison_sources: list[SourceDocumentFixture]


@lru_cache(maxsize=1)
def load_retrieval_fixture_dataset(fixture_path: str | None = None) -> RetrievalFixtureDataset:
    path = Path(fixture_path) if fixture_path else DEFAULT_FIXTURE_PATH
    dataset = RetrievalFixtureDataset.model_validate(json.loads(path.read_text(encoding="utf-8")))
    _validate_dataset(dataset)
    return dataset


def supported_fixture_tickers() -> list[str]:
    dataset = load_retrieval_fixture_dataset()
    return sorted(asset.asset.ticker for asset in dataset.assets if asset.asset.supported)


def build_asset_knowledge_pack(ticker: str) -> AssetKnowledgePack:
    dataset = load_retrieval_fixture_dataset()
    normalized = _normalize_ticker(ticker)
    fixture = _asset_fixture(dataset, normalized)

    if fixture is None:
        return _empty_pack(dataset, normalized)

    source_by_id = {source.source_document_id: source for source in fixture.source_documents}
    chunk_by_id = {chunk.chunk_id: chunk for chunk in fixture.source_chunks}

    retrieved_facts = [
        RetrievedFact(
            fact=fact,
            source_document=source_by_id[fact.source_document_id],
            source_chunk=chunk_by_id[fact.source_chunk_id],
        )
        for fact in fixture.normalized_facts
    ]
    retrieved_chunks = [
        RetrievedSourceChunk(chunk=chunk, source_document=source_by_id[chunk.source_document_id])
        for chunk in fixture.source_chunks
    ]
    retrieved_recent = [
        RetrievedRecentDevelopment(
            recent_development=recent,
            source_document=source_by_id[recent.source_document_id],
            source_chunk=chunk_by_id[recent.source_chunk_id],
        )
        for recent in fixture.recent_developments
    ]

    return AssetKnowledgePack(
        asset=fixture.asset,
        freshness=fixture.freshness,
        source_documents=fixture.source_documents,
        normalized_facts=retrieved_facts,
        source_chunks=retrieved_chunks,
        recent_developments=retrieved_recent,
        evidence_gaps=fixture.evidence_gaps,
    )


def build_comparison_knowledge_pack(left_ticker: str, right_ticker: str) -> ComparisonKnowledgePack:
    dataset = load_retrieval_fixture_dataset()
    left = _normalize_ticker(left_ticker)
    right = _normalize_ticker(right_ticker)
    comparison = _comparison_fixture(dataset, left, right)

    if comparison is None:
        raise RetrievalFixtureError(f"No comparison fixture exists for {left} vs {right}.")

    left_pack = build_asset_knowledge_pack(left)
    right_pack = build_asset_knowledge_pack(right)
    if not left_pack.asset.supported or not right_pack.asset.supported:
        raise RetrievalFixtureError(f"Comparison fixture {comparison.comparison_pack_id} references unsupported assets.")

    allowed_assets = {left_pack.asset.ticker, right_pack.asset.ticker}
    sources_by_id = {
        source.source_document_id: source
        for source in [*left_pack.source_documents, *right_pack.source_documents]
        if source.asset_ticker in allowed_assets
    }
    comparison_sources = sorted(sources_by_id.values(), key=lambda source: (source.asset_ticker, source.source_rank))

    return ComparisonKnowledgePack(
        comparison_pack_id=comparison.comparison_pack_id,
        left_asset_pack=left_pack,
        right_asset_pack=right_pack,
        computed_differences=comparison.computed_differences,
        comparison_sources=comparison_sources,
    )


def _empty_pack(dataset: RetrievalFixtureDataset, ticker: str) -> AssetKnowledgePack:
    unsupported_reason = dataset.unsupported_assets.get(ticker)
    status = AssetStatus.unsupported if unsupported_reason else AssetStatus.unknown
    asset_type = AssetType.unsupported if unsupported_reason else AssetType.unknown
    message = unsupported_reason or "No local retrieval fixture is available for this ticker."
    asset = AssetIdentity(
        ticker=ticker,
        name=ticker,
        asset_type=asset_type,
        exchange=None,
        issuer=None,
        status=status,
        supported=False,
    )
    freshness = Freshness(
        page_last_updated_at=dataset.generated_at,
        facts_as_of=None,
        holdings_as_of=None,
        recent_events_as_of=None,
        freshness_state=FreshnessState.unavailable,
    )
    evidence_state = "unsupported" if unsupported_reason else "missing"
    return AssetKnowledgePack(
        asset=asset,
        freshness=freshness,
        evidence_gaps=[
            EvidenceGap(
                gap_id=f"gap_{ticker.lower()}_{evidence_state}",
                asset_ticker=ticker,
                field_name="asset_knowledge_pack",
                evidence_state=evidence_state,
                message=message,
                freshness_state=FreshnessState.unavailable,
            )
        ],
    )


def _validate_dataset(dataset: RetrievalFixtureDataset) -> None:
    if not dataset.no_live_external_calls:
        raise RetrievalFixtureError("Retrieval fixtures must explicitly disable live external calls.")

    asset_tickers = set()
    source_by_id: dict[str, SourceDocumentFixture] = {}
    chunk_by_id: dict[str, SourceChunkFixture] = {}
    fact_by_id: dict[str, NormalizedFactFixture] = {}

    for asset_fixture in dataset.assets:
        ticker = asset_fixture.asset.ticker
        if ticker in asset_tickers:
            raise RetrievalFixtureError(f"Duplicate asset fixture for {ticker}.")
        asset_tickers.add(ticker)

        if asset_fixture.asset.status is not AssetStatus.supported or not asset_fixture.asset.supported:
            raise RetrievalFixtureError(f"Asset fixture {ticker} must be supported.")

        for source in asset_fixture.source_documents:
            if source.asset_ticker != ticker:
                raise RetrievalFixtureError(f"Source {source.source_document_id} belongs to the wrong asset.")
            if source.source_document_id in source_by_id:
                raise RetrievalFixtureError(f"Duplicate source document ID {source.source_document_id}.")
            source_by_id[source.source_document_id] = source

        asset_source_ids = {source.source_document_id for source in asset_fixture.source_documents}
        for chunk in asset_fixture.source_chunks:
            if chunk.asset_ticker != ticker:
                raise RetrievalFixtureError(f"Chunk {chunk.chunk_id} belongs to the wrong asset.")
            source = source_by_id.get(chunk.source_document_id)
            if source is None or source.source_document_id not in asset_source_ids or source.asset_ticker != ticker:
                raise RetrievalFixtureError(f"Chunk {chunk.chunk_id} references an invalid source.")
            if chunk.chunk_id in chunk_by_id:
                raise RetrievalFixtureError(f"Duplicate source chunk ID {chunk.chunk_id}.")
            chunk_by_id[chunk.chunk_id] = chunk

        asset_chunk_ids = {chunk.chunk_id for chunk in asset_fixture.source_chunks}
        for fact in asset_fixture.normalized_facts:
            if fact.asset_ticker != ticker:
                raise RetrievalFixtureError(f"Fact {fact.fact_id} belongs to the wrong asset.")
            _validate_evidence_reference(fact.fact_id, ticker, fact.source_document_id, fact.source_chunk_id, source_by_id, chunk_by_id)
            if fact.source_chunk_id not in asset_chunk_ids:
                raise RetrievalFixtureError(f"Fact {fact.fact_id} references a chunk outside {ticker}.")
            if fact.fact_id in fact_by_id:
                raise RetrievalFixtureError(f"Duplicate normalized fact ID {fact.fact_id}.")
            fact_by_id[fact.fact_id] = fact

        for recent in asset_fixture.recent_developments:
            if recent.asset_ticker != ticker:
                raise RetrievalFixtureError(f"Recent development {recent.event_id} belongs to the wrong asset.")
            _validate_evidence_reference(
                recent.event_id,
                ticker,
                recent.source_document_id,
                recent.source_chunk_id,
                source_by_id,
                chunk_by_id,
            )

        for gap in asset_fixture.evidence_gaps:
            if gap.asset_ticker != ticker:
                raise RetrievalFixtureError(f"Evidence gap {gap.gap_id} belongs to the wrong asset.")
            if gap.source_document_id or gap.source_chunk_id:
                _validate_evidence_reference(
                    gap.gap_id,
                    ticker,
                    gap.source_document_id or "",
                    gap.source_chunk_id or "",
                    source_by_id,
                    chunk_by_id,
                )

    for comparison in dataset.comparison_packs:
        allowed = {comparison.left_ticker, comparison.right_ticker}
        if not allowed <= asset_tickers:
            raise RetrievalFixtureError(f"Comparison fixture {comparison.comparison_pack_id} references missing assets.")

        for difference in comparison.computed_differences:
            for fact_id in difference.fact_ids:
                fact = fact_by_id.get(fact_id)
                if fact is None or fact.asset_ticker not in allowed:
                    raise RetrievalFixtureError(f"Comparison difference {difference.difference_id} references invalid fact {fact_id}.")
            for chunk_id in difference.source_chunk_ids:
                chunk = chunk_by_id.get(chunk_id)
                if chunk is None or chunk.asset_ticker not in allowed:
                    raise RetrievalFixtureError(f"Comparison difference {difference.difference_id} references invalid chunk {chunk_id}.")


def _validate_evidence_reference(
    item_id: str,
    ticker: str,
    source_document_id: str,
    source_chunk_id: str,
    source_by_id: dict[str, SourceDocumentFixture],
    chunk_by_id: dict[str, SourceChunkFixture],
) -> None:
    source = source_by_id.get(source_document_id)
    chunk = chunk_by_id.get(source_chunk_id)
    if source is None:
        raise RetrievalFixtureError(f"{item_id} references missing source document {source_document_id}.")
    if chunk is None:
        raise RetrievalFixtureError(f"{item_id} references missing source chunk {source_chunk_id}.")
    if source.asset_ticker != ticker or chunk.asset_ticker != ticker:
        raise RetrievalFixtureError(f"{item_id} references evidence from the wrong asset.")
    if chunk.source_document_id != source.source_document_id:
        raise RetrievalFixtureError(f"{item_id} source document and source chunk do not match.")


def _asset_fixture(dataset: RetrievalFixtureDataset, ticker: str) -> AssetFixture | None:
    return next((fixture for fixture in dataset.assets if fixture.asset.ticker == ticker), None)


def _comparison_fixture(dataset: RetrievalFixtureDataset, left: str, right: str) -> ComparisonFixture | None:
    return next(
        (
            comparison
            for comparison in dataset.comparison_packs
            if {comparison.left_ticker, comparison.right_ticker} == {left, right}
        ),
        None,
    )


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()
