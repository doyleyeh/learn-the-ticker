from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.cache import (
    build_cache_key,
    build_knowledge_pack_freshness_input,
    compute_knowledge_pack_freshness_hash,
    evaluate_cache_revalidation,
)
from backend.data import ELIGIBLE_NOT_CACHED_ASSETS
from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    CacheEntryKind,
    CacheEntryState,
    CacheKeyMetadata,
    CacheScope,
    Freshness,
    FreshnessState,
    IngestionCapabilities,
    KnowledgePackBuildResponse,
    KnowledgePackBuildState,
    KnowledgePackChunkMetadata,
    KnowledgePackCounts,
    KnowledgePackEvidenceGapMetadata,
    KnowledgePackFactMetadata,
    KnowledgePackRecentDevelopmentMetadata,
    KnowledgePackSourceMetadata,
    SectionFreshnessInput,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    StateMessage,
)
from backend.source_policy import resolve_source_policy, source_can_support_generated_output


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_PATH = ROOT / "data" / "retrieval_fixtures.json"
KNOWLEDGE_PACK_BUILD_SCHEMA_VERSION = "asset-knowledge-pack-build-v1"


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
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy


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


def build_asset_knowledge_pack_result(
    ticker: str,
    *,
    persisted_reader: Any | None = None,
) -> KnowledgePackBuildResponse:
    if persisted_reader is not None:
        from backend.retrieval_repository import read_persisted_knowledge_pack_response

        persisted = read_persisted_knowledge_pack_response(ticker, reader=persisted_reader)
        if persisted.found and persisted.response is not None:
            return persisted.response

    dataset = load_retrieval_fixture_dataset()
    normalized = _normalize_ticker(ticker)
    fixture = _asset_fixture(dataset, normalized)

    if fixture is not None:
        return _supported_pack_build_response(build_asset_knowledge_pack(normalized))

    if normalized in ELIGIBLE_NOT_CACHED_ASSETS:
        return _non_generated_pack_build_response(
            dataset=dataset,
            ticker=normalized,
            build_state=KnowledgePackBuildState.eligible_not_cached,
            cache_state=CacheEntryState.eligible_not_cached,
            asset=_eligible_not_cached_asset(normalized),
            message=(
                "This eligible launch-universe asset is not locally cached, so no generated page, "
                "chat answer, comparison output, source facts, citations, or reusable generated-output "
                "cache hit is available."
            ),
            evidence_state="eligible_not_cached",
        )

    unsupported_reason = dataset.unsupported_assets.get(normalized)
    if unsupported_reason:
        return _non_generated_pack_build_response(
            dataset=dataset,
            ticker=normalized,
            build_state=KnowledgePackBuildState.unsupported,
            cache_state=CacheEntryState.unsupported,
            asset=AssetIdentity(
                ticker=normalized,
                name=normalized,
                asset_type=AssetType.unsupported,
                exchange=None,
                issuer=None,
                status=AssetStatus.unsupported,
                supported=False,
            ),
            message=f"{unsupported_reason} No knowledge pack or generated output is created.",
            evidence_state="unsupported",
        )

    return _non_generated_pack_build_response(
        dataset=dataset,
        ticker=normalized,
        build_state=KnowledgePackBuildState.unknown,
        cache_state=CacheEntryState.unknown,
        asset=AssetIdentity(
            ticker=normalized,
            name=normalized,
            asset_type=AssetType.unknown,
            exchange=None,
            issuer=None,
            status=AssetStatus.unknown,
            supported=False,
        ),
        message="No local cached asset knowledge pack exists for this unknown ticker; no facts are invented.",
        evidence_state="unknown",
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


def _supported_pack_build_response(pack: AssetKnowledgePack) -> KnowledgePackBuildResponse:
    section_freshness = _section_freshness_labels(pack)
    freshness_input = build_knowledge_pack_freshness_input(pack, section_freshness_labels=section_freshness)
    freshness_hash = compute_knowledge_pack_freshness_hash(freshness_input)
    cache_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.knowledge_pack,
            scope=CacheScope.knowledge_pack,
            asset_ticker=pack.asset.ticker,
            pack_identity=_pack_id(pack.asset.ticker, KnowledgePackBuildState.available),
            mode_or_output_type="local-fixture",
            schema_version=KNOWLEDGE_PACK_BUILD_SCHEMA_VERSION,
            source_freshness_state=freshness_input.page_freshness_state,
            input_freshness_hash=freshness_hash,
        )
    )
    cache_revalidation = evaluate_cache_revalidation(None, cache_key, freshness_hash)
    citation_ids = _derived_citation_ids(pack)
    source_document_ids = sorted(source.source_document_id for source in pack.source_documents)

    return KnowledgePackBuildResponse(
        schema_version=KNOWLEDGE_PACK_BUILD_SCHEMA_VERSION,
        ticker=pack.asset.ticker,
        asset=pack.asset,
        asset_type=pack.asset.asset_type,
        pack_id=_pack_id(pack.asset.ticker, KnowledgePackBuildState.available),
        build_state=KnowledgePackBuildState.available,
        state=StateMessage(
            status=AssetStatus.supported,
            message="Cached local asset knowledge pack metadata is available from deterministic retrieval fixtures.",
        ),
        generated_output_available=True,
        reusable_generated_output_cache_hit=cache_revalidation.reusable,
        generated_route=f"/assets/{pack.asset.ticker}",
        capabilities=IngestionCapabilities(
            can_open_generated_page=True,
            can_answer_chat=True,
            can_compare=True,
            can_request_ingestion=False,
        ),
        freshness=pack.freshness,
        section_freshness=section_freshness,
        source_document_ids=source_document_ids,
        citation_ids=citation_ids,
        counts=KnowledgePackCounts(
            source_document_count=len(pack.source_documents),
            citation_count=len(citation_ids),
            normalized_fact_count=len(pack.normalized_facts),
            source_chunk_count=len(pack.source_chunks),
            recent_development_count=len(pack.recent_developments),
            evidence_gap_count=len(pack.evidence_gaps),
        ),
        source_documents=_source_metadata(pack),
        normalized_facts=_fact_metadata(pack),
        source_chunks=_chunk_metadata(pack),
        recent_developments=_recent_metadata(pack),
        evidence_gaps=_gap_metadata(pack.evidence_gaps),
        source_checksums=freshness_input.source_checksums,
        knowledge_pack_freshness_hash=freshness_hash,
        cache_key=cache_key,
        cache_revalidation=cache_revalidation,
        message="Knowledge-pack response contains metadata and hash inputs only; raw source document text is not exported.",
    )


def _non_generated_pack_build_response(
    *,
    dataset: RetrievalFixtureDataset,
    ticker: str,
    build_state: KnowledgePackBuildState,
    cache_state: CacheEntryState,
    asset: AssetIdentity,
    message: str,
    evidence_state: str,
) -> KnowledgePackBuildResponse:
    pack_id = _pack_id(ticker, build_state)
    freshness = Freshness(
        page_last_updated_at=dataset.generated_at,
        facts_as_of=None,
        holdings_as_of=None,
        recent_events_as_of=None,
        freshness_state=FreshnessState.unavailable,
    )
    cache_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.knowledge_pack,
            scope=CacheScope.knowledge_pack,
            asset_ticker=ticker,
            pack_identity=pack_id,
            mode_or_output_type=build_state.value,
            schema_version=KNOWLEDGE_PACK_BUILD_SCHEMA_VERSION,
            source_freshness_state=FreshnessState.unavailable,
            input_freshness_hash=pack_id,
        )
    )
    cache_revalidation = evaluate_cache_revalidation(None, cache_key, input_state=cache_state)
    gap = KnowledgePackEvidenceGapMetadata(
        gap_id=f"gap_{ticker.lower()}_{evidence_state}",
        asset_ticker=ticker,
        field_name="asset_knowledge_pack",
        evidence_state=evidence_state,
        freshness_state=FreshnessState.unavailable,
        message=message,
    )

    return KnowledgePackBuildResponse(
        schema_version=KNOWLEDGE_PACK_BUILD_SCHEMA_VERSION,
        ticker=ticker,
        asset=asset,
        asset_type=asset.asset_type,
        pack_id=pack_id,
        build_state=build_state,
        state=StateMessage(status=asset.status, message=message),
        generated_output_available=False,
        reusable_generated_output_cache_hit=cache_revalidation.reusable,
        generated_route=None,
        capabilities=IngestionCapabilities(
            can_open_generated_page=False,
            can_answer_chat=False,
            can_compare=False,
            can_request_ingestion=build_state is KnowledgePackBuildState.eligible_not_cached,
        ),
        freshness=freshness,
        section_freshness=[],
        source_document_ids=[],
        citation_ids=[],
        counts=KnowledgePackCounts(evidence_gap_count=1),
        source_documents=[],
        normalized_facts=[],
        source_chunks=[],
        recent_developments=[],
        evidence_gaps=[gap],
        source_checksums=[],
        knowledge_pack_freshness_hash=None,
        cache_key=cache_key,
        cache_revalidation=cache_revalidation,
        message=message,
    )


def _eligible_not_cached_asset(ticker: str) -> AssetIdentity:
    metadata = ELIGIBLE_NOT_CACHED_ASSETS[ticker]
    return AssetIdentity(
        ticker=ticker,
        name=str(metadata["name"]),
        asset_type=AssetType(str(metadata["asset_type"])),
        exchange=str(metadata["exchange"]) if metadata.get("exchange") else None,
        issuer=str(metadata["issuer"]) if metadata.get("issuer") else None,
        status=AssetStatus.unknown,
        supported=False,
    )


def _section_freshness_labels(pack: AssetKnowledgePack) -> list[SectionFreshnessInput]:
    labels = [
        SectionFreshnessInput(
            section_id="page",
            freshness_state=pack.freshness.freshness_state,
            evidence_state="supported",
            as_of_date=pack.freshness.facts_as_of,
            retrieved_at=pack.freshness.page_last_updated_at,
        ),
        SectionFreshnessInput(
            section_id="canonical_facts",
            freshness_state=pack.freshness.freshness_state,
            evidence_state="supported" if pack.normalized_facts else "unavailable",
            as_of_date=pack.freshness.facts_as_of,
            retrieved_at=pack.freshness.page_last_updated_at,
        ),
        SectionFreshnessInput(
            section_id="source_documents",
            freshness_state=_combined_freshness([source.freshness_state for source in pack.source_documents]),
            evidence_state="supported" if pack.source_documents else "unavailable",
            retrieved_at=pack.freshness.page_last_updated_at,
        ),
        SectionFreshnessInput(
            section_id="recent_developments",
            freshness_state=_combined_freshness([item.recent_development.freshness_state for item in pack.recent_developments]),
            evidence_state=_recent_evidence_state(pack),
            as_of_date=pack.freshness.recent_events_as_of,
            retrieved_at=pack.freshness.page_last_updated_at,
        ),
        SectionFreshnessInput(
            section_id="weekly_news_focus",
            freshness_state=_combined_freshness([item.recent_development.freshness_state for item in pack.recent_developments]),
            evidence_state="no_high_signal" if _recent_evidence_state(pack) == "no_major_recent_development" else _recent_evidence_state(pack),
            as_of_date=pack.freshness.recent_events_as_of,
            retrieved_at=pack.freshness.page_last_updated_at,
        ),
        SectionFreshnessInput(
            section_id="ai_comprehensive_analysis",
            freshness_state=pack.freshness.freshness_state,
            evidence_state="insufficient_evidence",
            as_of_date=pack.freshness.recent_events_as_of,
            retrieved_at=pack.freshness.page_last_updated_at,
        ),
    ]
    if pack.asset.asset_type is AssetType.etf:
        labels.append(
            SectionFreshnessInput(
                section_id="holdings",
                freshness_state=pack.freshness.freshness_state if pack.freshness.holdings_as_of else FreshnessState.unavailable,
                evidence_state="supported" if pack.freshness.holdings_as_of else "unavailable",
                as_of_date=pack.freshness.holdings_as_of,
                retrieved_at=pack.freshness.page_last_updated_at,
            )
        )
    if pack.evidence_gaps:
        labels.append(
            SectionFreshnessInput(
                section_id="evidence_gaps",
                freshness_state=_combined_freshness([gap.freshness_state for gap in pack.evidence_gaps]),
                evidence_state="mixed",
                retrieved_at=pack.freshness.page_last_updated_at,
            )
        )
    return sorted(labels, key=lambda label: label.section_id)


def _source_metadata(pack: AssetKnowledgePack) -> list[KnowledgePackSourceMetadata]:
    fact_ids_by_source: dict[str, list[str]] = {}
    recent_ids_by_source: dict[str, list[str]] = {}
    chunk_ids_by_source: dict[str, list[str]] = {}
    citation_ids_by_source: dict[str, list[str]] = {}

    for item in pack.normalized_facts:
        source_id = item.fact.source_document_id
        fact_ids_by_source.setdefault(source_id, []).append(item.fact.fact_id)
        citation_ids_by_source.setdefault(source_id, []).append(_fact_citation_id(item.fact))
    for item in pack.recent_developments:
        source_id = item.recent_development.source_document_id
        recent_ids_by_source.setdefault(source_id, []).append(item.recent_development.event_id)
        citation_ids_by_source.setdefault(source_id, []).append(_recent_citation_id(item.recent_development))
    for item in pack.source_chunks:
        source_id = item.chunk.source_document_id
        chunk_ids_by_source.setdefault(source_id, []).append(item.chunk.chunk_id)
        citation_ids_by_source.setdefault(source_id, []).append(_chunk_citation_id(item.chunk))

    return [
        KnowledgePackSourceMetadata(
            source_document_id=source.source_document_id,
            asset_ticker=source.asset_ticker,
            source_type=source.source_type,
            source_rank=source.source_rank,
            title=source.title,
            publisher=source.publisher,
            url=source.url,
            published_at=source.published_at,
            as_of_date=source.as_of_date,
            retrieved_at=source.retrieved_at,
            freshness_state=source.freshness_state,
            is_official=source.is_official,
            source_quality=source.source_quality,
            allowlist_status=source.allowlist_status,
            source_use_policy=source.source_use_policy,
            permitted_operations=_policy_decision_for_source(source).permitted_operations,
            citation_ids=sorted(set(citation_ids_by_source.get(source.source_document_id, []))),
            fact_ids=sorted(set(fact_ids_by_source.get(source.source_document_id, []))),
            recent_event_ids=sorted(set(recent_ids_by_source.get(source.source_document_id, []))),
            chunk_ids=sorted(set(chunk_ids_by_source.get(source.source_document_id, []))),
        )
        for source in sorted(pack.source_documents, key=lambda item: (item.asset_ticker, item.source_rank, item.source_document_id))
    ]


def _fact_metadata(pack: AssetKnowledgePack) -> list[KnowledgePackFactMetadata]:
    return [
        KnowledgePackFactMetadata(
            fact_id=item.fact.fact_id,
            asset_ticker=item.fact.asset_ticker,
            fact_type=item.fact.fact_type,
            field_name=item.fact.field_name,
            source_document_id=item.fact.source_document_id,
            source_chunk_id=item.fact.source_chunk_id,
            extraction_method=item.fact.extraction_method,
            freshness_state=item.fact.freshness_state,
            evidence_state=item.fact.evidence_state,
            as_of_date=item.fact.as_of_date,
            citation_ids=[_fact_citation_id(item.fact)],
        )
        for item in sorted(pack.normalized_facts, key=lambda item: item.fact.fact_id)
    ]


def _chunk_metadata(pack: AssetKnowledgePack) -> list[KnowledgePackChunkMetadata]:
    return [
        KnowledgePackChunkMetadata(
            chunk_id=item.chunk.chunk_id,
            asset_ticker=item.chunk.asset_ticker,
            source_document_id=item.chunk.source_document_id,
            section_name=item.chunk.section_name,
            chunk_order=item.chunk.chunk_order,
            token_count=item.chunk.token_count,
            supported_claim_types=item.chunk.supported_claim_types,
            citation_ids=[_chunk_citation_id(item.chunk)],
        )
        for item in sorted(pack.source_chunks, key=lambda item: (item.chunk.source_document_id, item.chunk.chunk_order, item.chunk.chunk_id))
    ]


def _recent_metadata(pack: AssetKnowledgePack) -> list[KnowledgePackRecentDevelopmentMetadata]:
    return [
        KnowledgePackRecentDevelopmentMetadata(
            event_id=item.recent_development.event_id,
            asset_ticker=item.recent_development.asset_ticker,
            event_type=item.recent_development.event_type,
            event_date=item.recent_development.event_date,
            source_document_id=item.recent_development.source_document_id,
            source_chunk_id=item.recent_development.source_chunk_id,
            importance_score=item.recent_development.importance_score,
            freshness_state=item.recent_development.freshness_state,
            evidence_state=item.recent_development.evidence_state,
            citation_ids=[_recent_citation_id(item.recent_development)],
        )
        for item in sorted(pack.recent_developments, key=lambda item: item.recent_development.event_id)
    ]


def _gap_metadata(gaps: list[EvidenceGap]) -> list[KnowledgePackEvidenceGapMetadata]:
    return [
        KnowledgePackEvidenceGapMetadata(
            gap_id=gap.gap_id,
            asset_ticker=gap.asset_ticker,
            field_name=gap.field_name,
            evidence_state=gap.evidence_state,
            freshness_state=gap.freshness_state,
            source_document_id=gap.source_document_id,
            source_chunk_id=gap.source_chunk_id,
            message=gap.message,
        )
        for gap in sorted(gaps, key=lambda item: item.gap_id)
    ]


def _derived_citation_ids(pack: AssetKnowledgePack) -> list[str]:
    return sorted(
        {
            *{_fact_citation_id(item.fact) for item in pack.normalized_facts},
            *{_chunk_citation_id(item.chunk) for item in pack.source_chunks},
            *{_recent_citation_id(item.recent_development) for item in pack.recent_developments},
        }
    )


def _fact_citation_id(fact: NormalizedFactFixture) -> str:
    return f"c_{fact.fact_id}"


def _chunk_citation_id(chunk: SourceChunkFixture) -> str:
    return f"c_{chunk.chunk_id}"


def _recent_citation_id(recent: RecentDevelopmentFixture) -> str:
    return f"c_{recent.event_id}"


def _pack_id(ticker: str, state: KnowledgePackBuildState) -> str:
    suffix = "local-fixture" if state is KnowledgePackBuildState.available else state.value.replace("_", "-")
    return f"asset-knowledge-pack-{ticker.lower()}-{suffix}-v1"


def _combined_freshness(states: list[FreshnessState]) -> FreshnessState:
    if not states:
        return FreshnessState.unavailable
    for state in [FreshnessState.unavailable, FreshnessState.unknown, FreshnessState.stale]:
        if state in states:
            return state
    return FreshnessState.fresh


def _recent_evidence_state(pack: AssetKnowledgePack) -> str:
    states = {item.recent_development.evidence_state for item in pack.recent_developments}
    if not states:
        return "unavailable"
    if states == {"no_major_recent_development"}:
        return "no_major_recent_development"
    if states == {"supported"}:
        return "supported"
    return "mixed"


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
            decision = _policy_decision_for_source(source)
            if source.source_quality is not decision.source_quality:
                raise RetrievalFixtureError(f"Source {source.source_document_id} quality disagrees with source policy.")
            if source.allowlist_status is not decision.allowlist_status:
                raise RetrievalFixtureError(f"Source {source.source_document_id} allowlist status disagrees with source policy.")
            if source.source_use_policy is not decision.source_use_policy:
                raise RetrievalFixtureError(f"Source {source.source_document_id} source-use policy disagrees with source policy.")
            if not source_can_support_generated_output(decision):
                raise RetrievalFixtureError(f"Source {source.source_document_id} cannot support generated output or citations.")
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


def _policy_decision_for_source(source: SourceDocumentFixture):
    return resolve_source_policy(
        url=source.url,
        source_identifier=source.url if source.url.startswith("local://") else None,
    )


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
