from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from backend.cache import (
    build_comparison_pack_freshness_input,
    build_generated_output_freshness_input,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
)
from backend.citations import (
    CitationEvidence,
    CitationValidationClaim,
    CitationValidationContext,
    CitationValidationIssue,
    CitationValidationReport,
    CitationValidationResult,
    CitationValidationStatus,
    EvidenceKind,
    validate_claims,
)
from backend.models import (
    AssetStatus,
    AssetIdentity,
    AssetType,
    BeginnerBottomLine,
    Citation,
    ComparisonEvidenceAvailability,
    ComparisonEvidenceAvailabilityState,
    ComparisonEvidenceCitationBinding,
    ComparisonEvidenceClaimBinding,
    ComparisonEvidenceDiagnostics,
    ComparisonEvidenceDimension,
    ComparisonEvidenceItem,
    ComparisonEvidenceSide,
    ComparisonEvidenceSideRole,
    ComparisonEvidenceSourceReference,
    ComparisonMetricGroup,
    ComparisonMetricRow,
    CompareResponse,
    EvidenceState,
    FreshnessState,
    KeyDifference,
    SourceAllowlistStatus,
    SourceDocument,
    SourceUsePolicy,
    StateMessage,
    StockEtfBasketStructure,
    StockEtfRelationshipBadge,
    StockEtfRelationshipModel,
    CacheEntryKind,
    CacheScope,
    Freshness,
    OverviewResponse,
)
from backend.data import ELIGIBLE_NOT_CACHED_ASSETS, OUT_OF_SCOPE_COMMON_STOCKS
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    GeneratedOutputCacheContractError,
    GeneratedOutputCacheRepositoryRecords,
    build_deterministic_generated_output_cache_records,
    persist_generated_output_cache_records,
    validate_generated_output_cache_records,
)
from backend.retrieval import (
    AssetKnowledgePack,
    ComparisonKnowledgePack,
    EvidenceGap,
    NormalizedFactFixture,
    RecentDevelopmentFixture,
    RetrievedFact,
    RetrievedRecentDevelopment,
    RetrievedSourceChunk,
    RetrievalFixtureError,
    SourceChunkFixture,
    SourceDocumentFixture,
    build_asset_knowledge_pack,
    build_comparison_knowledge_pack,
)
from backend.repositories.knowledge_packs import KnowledgePackRepositoryContractError, KnowledgePackRepositoryRecords
from backend.retrieval_repository import KnowledgePackRecordReader, read_persisted_knowledge_pack_response
from backend.safety import find_forbidden_output_phrases
from backend.source_policy import resolve_source_policy, source_handoff_fields_from_policy


class ComparisonGenerationError(ValueError):
    """Raised when deterministic comparison generation violates project contracts."""


COMPARISON_PERSISTED_READ_BOUNDARY = "comparison-persisted-read-boundary-v1"


class GeneratedOutputComparisonCacheRecordReader(Protocol):
    def read_comparison_records(self, left_ticker: str, right_ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        ...


@dataclass(frozen=True)
class PersistedComparisonReadResult:
    status: str
    left_ticker: str
    right_ticker: str
    comparison: CompareResponse | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found(self) -> bool:
        return self.status == "found" and self.comparison is not None


@dataclass(frozen=True)
class CitationBinding:
    citation: Citation
    source_document: SourceDocument
    evidence: CitationEvidence


@dataclass(frozen=True)
class PlannedComparisonClaim:
    claim_id: str
    claim_text: str
    citation_ids: list[str]
    claim_type: str = "comparison"
    required_asset_tickers: list[str] | None = None
    freshness_label: FreshnessState | None = None


REQUIRED_COMPARISON_DIMENSIONS = [
    "Benchmark",
    "Expense ratio",
    "Holdings count",
    "Breadth",
    "Educational role",
]

COMPARISON_FACT_FIELDS_BY_DIMENSION = {
    "Benchmark": ["benchmark"],
    "Expense ratio": ["expense_ratio"],
    "Holdings count": ["holdings_count"],
    "Breadth": ["holdings_count"],
    "Educational role": ["beginner_role"],
}

STOCK_ETF_COMPARISON_DIMENSIONS = [
    "Structure",
    "Basket membership",
    "Breadth",
    "Cost model",
    "Educational role",
]

STOCK_STOCK_COMPARISON_DIMENSIONS = [
    "Business model",
    "Revenue trend",
    "Business quality evidence",
    "Risk context",
    "Valuation evidence availability",
]


def generate_comparison(
    left_ticker: str,
    right_ticker: str,
    *,
    persisted_pack_reader: KnowledgePackRecordReader | Any | None = None,
    generated_output_cache_reader: GeneratedOutputComparisonCacheRecordReader | Any | None = None,
    generated_output_cache_writer: Any | None = None,
) -> CompareResponse:
    """Build a CompareResponse-compatible payload from local comparison fixtures."""

    persisted = read_persisted_comparison_response(
        left_ticker,
        right_ticker,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
    )
    if persisted.found and persisted.comparison is not None:
        return persisted.comparison

    left_pack = build_asset_knowledge_pack(left_ticker)
    right_pack = build_asset_knowledge_pack(right_ticker)

    if not left_pack.asset.supported or not right_pack.asset.supported:
        lightweight_comparison = _generate_lightweight_comparison_if_available(left_ticker, right_ticker)
        if lightweight_comparison is not None:
            return lightweight_comparison
        return _unavailable_comparison(left_pack, right_pack)

    try:
        pack = build_comparison_knowledge_pack(left_ticker, right_ticker)
    except RetrievalFixtureError:
        lightweight_comparison = _generate_lightweight_comparison_if_available(left_ticker, right_ticker)
        if lightweight_comparison is not None:
            return lightweight_comparison
        return _unavailable_comparison(
            left_pack,
            right_pack,
            "No deterministic local comparison knowledge pack is available for these tickers.",
        )

    comparison = generate_comparison_from_pack(pack)
    _maybe_write_comparison_generated_output_cache(comparison, pack, generated_output_cache_writer)
    return comparison


def read_persisted_comparison_response(
    left_ticker: str,
    right_ticker: str,
    *,
    persisted_pack_reader: KnowledgePackRecordReader | Any | None = None,
    generated_output_cache_reader: GeneratedOutputComparisonCacheRecordReader | Any | None = None,
) -> PersistedComparisonReadResult:
    left = left_ticker.strip().upper()
    right = right_ticker.strip().upper()
    if persisted_pack_reader is None or generated_output_cache_reader is None:
        return PersistedComparisonReadResult(
            status="not_configured",
            left_ticker=left,
            right_ticker=right,
            diagnostics=("reader:not_configured",),
        )

    try:
        fixture_pack = build_comparison_knowledge_pack(left, right)
    except RetrievalFixtureError:
        return PersistedComparisonReadResult(
            status="blocked_state",
            left_ticker=left,
            right_ticker=right,
            diagnostics=("comparison:no_local_pack",),
        )

    left_read = read_persisted_knowledge_pack_response(left, reader=persisted_pack_reader)
    right_read = read_persisted_knowledge_pack_response(right, reader=persisted_pack_reader)
    for side, read in [("left", left_read), ("right", right_read)]:
        if not read.found or read.response is None or read.records is None:
            return PersistedComparisonReadResult(
                status=read.status,
                left_ticker=left,
                right_ticker=right,
                diagnostics=(f"knowledge_pack:{side}:{read.status}",),
            )
        if not read.response.asset.supported or not read.response.generated_output_available:
            return PersistedComparisonReadResult(
                status="blocked_state",
                left_ticker=left,
                right_ticker=right,
                diagnostics=(f"knowledge_pack:{side}:blocked:{read.response.build_state.value}",),
            )

    cache_read = _read_generated_comparison_cache_records(generated_output_cache_reader, left, right)
    if cache_read.status != "found" or cache_read.records is None:
        return PersistedComparisonReadResult(
            status=cache_read.status,
            left_ticker=left,
            right_ticker=right,
            diagnostics=cache_read.diagnostics,
        )

    try:
        left_pack = _asset_knowledge_pack_from_repository_records(left_read.records)
        right_pack = _asset_knowledge_pack_from_repository_records(right_read.records)
        pack = ComparisonKnowledgePack(
            comparison_pack_id=fixture_pack.comparison_pack_id,
            left_asset_pack=left_pack,
            right_asset_pack=right_pack,
            computed_differences=fixture_pack.computed_differences,
            comparison_sources=sorted(
                [*left_pack.source_documents, *right_pack.source_documents],
                key=lambda source: (source.asset_ticker, source.source_rank, source.source_document_id),
            ),
        )
        _validate_persisted_comparison_identity(pack, fixture_pack, left, right)
        _validate_generated_output_cache_for_comparison(left, right, cache_read.records, pack=pack)
        comparison = generate_comparison_from_pack(pack)
        report = validate_comparison_response(comparison, pack)
        if not report.valid:
            return PersistedComparisonReadResult(
                status="validation_error",
                left_ticker=left,
                right_ticker=right,
                diagnostics=("comparison:citation_validation_failed",),
            )
        _validate_comparison_cache_covers_response(cache_read.records, comparison)
    except (
        GeneratedOutputCacheContractError,
        KnowledgePackRepositoryContractError,
        ComparisonGenerationError,
        LookupError,
        StopIteration,
        ValueError,
        TypeError,
    ) as exc:
        return PersistedComparisonReadResult(
            status="contract_error",
            left_ticker=left,
            right_ticker=right,
            diagnostics=(f"comparison:{exc.__class__.__name__}",),
        )

    return PersistedComparisonReadResult(
        status="found",
        left_ticker=left,
        right_ticker=right,
        comparison=comparison,
        diagnostics=("comparison:persisted_hit",),
    )


def _generate_lightweight_comparison_if_available(left_ticker: str, right_ticker: str) -> CompareResponse | None:
    from backend.lightweight_page import build_lightweight_overview_response_if_enabled

    left = build_lightweight_overview_response_if_enabled(left_ticker)
    right = build_lightweight_overview_response_if_enabled(right_ticker)
    if left is None or right is None:
        return None
    if not left.asset.supported or not right.asset.supported:
        return None
    if not left.citations or not right.citations or not left.source_documents or not right.source_documents:
        return None

    left_citation = _first_lightweight_citation(left)
    right_citation = _first_lightweight_citation(right)
    if left_citation is None or right_citation is None:
        return None

    citation_ids = [left_citation.citation_id, right_citation.citation_id]
    citations = _dedupe_citations([left_citation, right_citation])
    source_documents = _dedupe_source_documents(
        [
            *_source_documents_for_citations(left, [left_citation.citation_id]),
            *_source_documents_for_citations(right, [right_citation.citation_id]),
        ]
    )
    comparison_type = _lightweight_comparison_type(left, right)
    key_differences = _lightweight_key_differences(left, right, citation_ids, comparison_type)
    bottom_line = BeginnerBottomLine(
        summary=(
            f"{left.asset.ticker} and {right.asset.ticker} are shown as a local lightweight comparison using "
            "normalized, source-labeled evidence. Official sources are preferred when available; provider or "
            "Yahoo-style fallback stays labeled as non-official context."
        ),
        citation_ids=citation_ids,
    )
    response = CompareResponse(
        left_asset=left.asset,
        right_asset=right.asset,
        state=StateMessage(
            status=AssetStatus.supported,
            message=(
                "Comparison is supported by local lightweight runtime evidence with official-first/provider/Yahoo "
                "fallback labels; strict source-pack approval and cache promotion are not implied."
            ),
        ),
        comparison_type=comparison_type,
        key_differences=key_differences,
        bottom_line_for_beginners=bottom_line,
        citations=citations,
        source_documents=source_documents,
        metric_groups=_lightweight_comparison_metric_groups(left, right, citation_ids),
    )
    response.evidence_availability = _lightweight_evidence_availability(
        response=response,
        left=left,
        right=right,
        used_citation_ids=citation_ids,
    )
    _assert_safe_copy(response)
    return response


def _first_lightweight_citation(overview: OverviewResponse) -> Citation | None:
    source_ids = {source.source_document_id for source in overview.source_documents}
    for citation in overview.citations:
        if citation.source_document_id in source_ids:
            return citation
    return None


def _lightweight_comparison_type(left: OverviewResponse, right: OverviewResponse) -> str:
    asset_types = {left.asset.asset_type, right.asset.asset_type}
    if asset_types == {AssetType.stock, AssetType.etf}:
        return "stock_vs_etf"
    return f"{left.asset.asset_type.value}_vs_{right.asset.asset_type.value}"


def _lightweight_key_differences(
    left: OverviewResponse,
    right: OverviewResponse,
    citation_ids: list[str],
    comparison_type: str,
) -> list[KeyDifference]:
    left_kind = _lightweight_asset_kind(left)
    right_kind = _lightweight_asset_kind(right)
    left_tier = _lightweight_source_tier(left)
    right_tier = _lightweight_source_tier(right)
    return [
        KeyDifference(
            dimension="Structure",
            plain_english_summary=(
                f"{left.asset.ticker} is shown as {left_kind}, while {right.asset.ticker} is shown as {right_kind} "
                f"in this {comparison_type.replace('_', ' ')} learning view."
            ),
            citation_ids=citation_ids,
        ),
        KeyDifference(
            dimension="Source basis",
            plain_english_summary=(
                f"{left.asset.ticker} currently uses {left_tier} evidence and {right.asset.ticker} currently uses "
                f"{right_tier} evidence; fallback sources are labeled rather than treated as official."
            ),
            citation_ids=citation_ids,
        ),
        KeyDifference(
            dimension="Freshness",
            plain_english_summary=(
                f"{left.asset.ticker} facts are dated {left.freshness.facts_as_of or 'unknown'}, and "
                f"{right.asset.ticker} facts are dated {right.freshness.facts_as_of or 'unknown'} in the local "
                "runtime response."
            ),
            citation_ids=citation_ids,
        ),
        KeyDifference(
            dimension="Educational role",
            plain_english_summary=(
                "This comparison keeps source-labeled facts separate from strict audit approval and generated-output "
                "cache promotion, so missing official components do not hide renderable local evidence."
            ),
            citation_ids=citation_ids,
        ),
    ]


def _lightweight_asset_kind(overview: OverviewResponse) -> str:
    if overview.asset.asset_type is AssetType.stock:
        return "one U.S.-listed company"
    if overview.asset.asset_type is AssetType.etf:
        return "a U.S.-listed ETF basket"
    return "an asset outside the generated comparison scope"


def _lightweight_source_tier(overview: OverviewResponse) -> str:
    diagnostics = overview.fallback_diagnostics
    if diagnostics is None:
        return "source-labeled lightweight"
    labels = {str(label.value if hasattr(label, "value") else label) for label in diagnostics.source_labels}
    if "official" in labels and "provider_derived" in labels:
        return "official plus provider/Yahoo fallback"
    if "official" in labels:
        return "official"
    if "provider_derived" in labels:
        return "provider/Yahoo fallback"
    return "partial lightweight"


def _lightweight_comparison_metric_groups(
    left: OverviewResponse,
    right: OverviewResponse,
    citation_ids: list[str],
) -> list[ComparisonMetricGroup]:
    source_document_ids = _source_document_ids_for_lightweight_citations([left, right], citation_ids)
    rows = [
        ComparisonMetricRow(
            metric_id="asset_type",
            label="Asset type",
            left_value=left.asset.asset_type.value,
            right_value=right.asset.asset_type.value,
            citation_ids=citation_ids,
            source_document_ids=source_document_ids,
            freshness_state=_combined_freshness([left.freshness.freshness_state, right.freshness.freshness_state]),
            evidence_state=EvidenceState.supported,
        ),
        ComparisonMetricRow(
            metric_id="source_tier",
            label="Source tier",
            left_value=_lightweight_source_tier(left),
            right_value=_lightweight_source_tier(right),
            citation_ids=citation_ids,
            source_document_ids=source_document_ids,
            freshness_state=_combined_freshness([left.freshness.freshness_state, right.freshness.freshness_state]),
            evidence_state=EvidenceState.partial,
            limitations="Provider/Yahoo fallback is local display evidence, not strict/audit source-pack approval.",
        ),
        ComparisonMetricRow(
            metric_id="facts_as_of",
            label="Facts as of",
            left_value=left.freshness.facts_as_of or "Unknown",
            right_value=right.freshness.facts_as_of or "Unknown",
            citation_ids=citation_ids,
            source_document_ids=source_document_ids,
            freshness_state=_combined_freshness([left.freshness.freshness_state, right.freshness.freshness_state]),
            evidence_state=EvidenceState.partial,
        ),
    ]
    return [
        ComparisonMetricGroup(
            group_id="lightweight_runtime_evidence",
            title="Lightweight Runtime Evidence",
            rows=rows,
            citation_ids=citation_ids,
            source_document_ids=source_document_ids,
            freshness_state=_combined_freshness([row.freshness_state for row in rows]),
            evidence_state=EvidenceState.partial,
            limitations="Strict source-pack approval and generated-output cache promotion remain separate.",
        )
    ]


def _lightweight_evidence_availability(
    *,
    response: CompareResponse,
    left: OverviewResponse,
    right: OverviewResponse,
    used_citation_ids: list[str],
) -> ComparisonEvidenceAvailability:
    source_documents = _dedupe_source_documents([*left.source_documents, *right.source_documents])
    source_by_id = {source.source_document_id: source for source in source_documents}
    citation_by_id = {
        citation.citation_id: citation
        for citation in _dedupe_citations([*left.citations, *right.citations])
        if citation.citation_id in set(used_citation_ids)
    }
    source_ids = sorted(
        {
            citation.source_document_id
            for citation in citation_by_id.values()
            if citation.source_document_id in source_by_id
        }
    )
    dimensions = [
        ComparisonEvidenceDimension(
            dimension=dimension,
            availability_state=ComparisonEvidenceAvailabilityState.available,
            evidence_state=EvidenceState.partial if dimension != "Structure" else EvidenceState.supported,
            freshness_state=_combined_freshness([left.freshness.freshness_state, right.freshness.freshness_state]),
            left_evidence_item_ids=[],
            right_evidence_item_ids=[],
            shared_evidence_item_ids=[],
            citation_ids=used_citation_ids,
            source_document_ids=source_ids,
            generated_claim_ids=[f"claim_comparison_{_claim_slug(dimension)}"],
        )
        for dimension in [difference.dimension for difference in response.key_differences]
    ]
    claim_bindings = [
        ComparisonEvidenceClaimBinding(
            claim_id=f"claim_comparison_{_claim_slug(difference.dimension)}",
            claim_kind="key_difference",
            dimension=difference.dimension,
            side_role=ComparisonEvidenceSideRole.shared_comparison_support,
            citation_ids=difference.citation_ids,
            source_document_ids=_source_document_ids_for_lightweight_citations([left, right], difference.citation_ids),
            evidence_item_ids=[],
            availability_state=ComparisonEvidenceAvailabilityState.available,
        )
        for difference in response.key_differences
    ]
    if response.bottom_line_for_beginners is not None:
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id="claim_comparison_bottom_line",
                claim_kind="beginner_bottom_line",
                dimension="Beginner bottom line",
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=response.bottom_line_for_beginners.citation_ids,
                source_document_ids=_source_document_ids_for_lightweight_citations(
                    [left, right],
                    response.bottom_line_for_beginners.citation_ids,
                ),
                evidence_item_ids=[],
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )

    citation_bindings: list[ComparisonEvidenceCitationBinding] = []
    for claim in claim_bindings:
        citation_bindings.extend(
            _lightweight_citation_bindings_for_claim(
                claim=claim,
                citation_by_id=citation_by_id,
                source_by_id=source_by_id,
                left_ticker=left.asset.ticker,
                right_ticker=right.asset.ticker,
            )
        )

    return ComparisonEvidenceAvailability(
        comparison_id=_comparison_id(left.asset.ticker, right.asset.ticker),
        comparison_type=response.comparison_type,
        left_asset=left.asset,
        right_asset=right.asset,
        availability_state=ComparisonEvidenceAvailabilityState.available,
        required_dimensions=[dimension.dimension for dimension in dimensions],
        required_evidence_dimensions=dimensions,
        evidence_items=[],
        claim_bindings=claim_bindings,
        citation_bindings=sorted(citation_bindings, key=lambda item: item.binding_id),
        source_references=[
            _source_reference_from_document(
                source_by_id[source_id],
                asset_ticker=_asset_ticker_for_lightweight_source_id(
                    source_id,
                    left_ticker=left.asset.ticker,
                    right_ticker=right.asset.ticker,
                ),
            )
            for source_id in source_ids
        ],
        diagnostics=ComparisonEvidenceDiagnostics(
            no_live_external_calls=False,
            live_provider_calls_attempted=True,
            generated_comparison_available=True,
            unavailable_reasons=[],
        ),
    )


def _lightweight_citation_bindings_for_claim(
    *,
    claim: ComparisonEvidenceClaimBinding,
    citation_by_id: dict[str, Citation],
    source_by_id: dict[str, SourceDocument],
    left_ticker: str,
    right_ticker: str,
) -> list[ComparisonEvidenceCitationBinding]:
    bindings: list[ComparisonEvidenceCitationBinding] = []
    for citation_id in claim.citation_ids:
        citation = citation_by_id.get(citation_id)
        if citation is None:
            continue
        source = source_by_id.get(citation.source_document_id)
        if source is None:
            continue
        asset_ticker = _asset_ticker_for_lightweight_source_id(
            source.source_document_id,
            left_ticker=left_ticker,
            right_ticker=right_ticker,
        )
        bindings.append(
            ComparisonEvidenceCitationBinding(
                binding_id=f"lw_{claim.claim_id}_{citation_id}",
                claim_id=claim.claim_id,
                dimension=claim.dimension,
                citation_id=citation_id,
                source_document_id=source.source_document_id,
                asset_ticker=asset_ticker,
                side_role=_side_role_for_asset(asset_ticker, left_ticker, right_ticker),
                freshness_state=citation.freshness_state,
                source_quality=source.source_quality,
                allowlist_status=source.allowlist_status,
                source_use_policy=source.source_use_policy,
                permitted_operations=source.permitted_operations,
                supports_generated_claim=(
                    source.permitted_operations.can_support_generated_output
                    and source.permitted_operations.can_support_citations
                ),
            )
        )
    return bindings


def _source_reference_from_document(source: SourceDocument, *, asset_ticker: str) -> ComparisonEvidenceSourceReference:
    return ComparisonEvidenceSourceReference(
        source_document_id=source.source_document_id,
        asset_ticker=asset_ticker,
        source_type=source.source_type,
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
        permitted_operations=source.permitted_operations,
    )


def _source_documents_for_citations(overview: OverviewResponse, citation_ids: list[str]) -> list[SourceDocument]:
    source_ids = {
        citation.source_document_id
        for citation in overview.citations
        if citation.citation_id in set(citation_ids)
    }
    return [source for source in overview.source_documents if source.source_document_id in source_ids]


def _source_document_ids_for_lightweight_citations(
    overviews: list[OverviewResponse],
    citation_ids: list[str],
) -> list[str]:
    ids: list[str] = []
    wanted = set(citation_ids)
    for overview in overviews:
        ids.extend(citation.source_document_id for citation in overview.citations if citation.citation_id in wanted)
    return sorted(dict.fromkeys(ids))


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    deduped: dict[str, Citation] = {}
    for citation in citations:
        deduped.setdefault(citation.citation_id, citation)
    return list(deduped.values())


def _dedupe_source_documents(sources: list[SourceDocument]) -> list[SourceDocument]:
    deduped: dict[str, SourceDocument] = {}
    for source in sources:
        deduped.setdefault(source.source_document_id, source)
    return list(deduped.values())


def _asset_ticker_for_lightweight_source_id(source_document_id: str, *, left_ticker: str, right_ticker: str) -> str:
    normalized = source_document_id.upper()
    if left_ticker.upper() in normalized:
        return left_ticker
    if right_ticker.upper() in normalized:
        return right_ticker
    return left_ticker


@dataclass(frozen=True)
class _GeneratedOutputComparisonCacheReadResult:
    status: str
    left_ticker: str
    right_ticker: str
    records: GeneratedOutputCacheRepositoryRecords | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


def _read_generated_comparison_cache_records(
    reader: GeneratedOutputComparisonCacheRecordReader | Any,
    left_ticker: str,
    right_ticker: str,
) -> _GeneratedOutputComparisonCacheReadResult:
    try:
        raw_records = _read_generated_comparison_cache_reader(reader, left_ticker, right_ticker)
        if raw_records is None:
            return _GeneratedOutputComparisonCacheReadResult(
                status="miss",
                left_ticker=left_ticker,
                right_ticker=right_ticker,
                diagnostics=("generated_output_cache:miss",),
            )
        records = (
            raw_records
            if isinstance(raw_records, GeneratedOutputCacheRepositoryRecords)
            else GeneratedOutputCacheRepositoryRecords.model_validate(raw_records)
        )
        validated = validate_generated_output_cache_records(records)
    except GeneratedOutputCacheContractError as exc:
        return _GeneratedOutputComparisonCacheReadResult(
            status="contract_error",
            left_ticker=left_ticker,
            right_ticker=right_ticker,
            diagnostics=(f"generated_output_cache:{exc.__class__.__name__}",),
        )
    except Exception as exc:  # pragma: no cover - caller observes sanitized status only.
        return _GeneratedOutputComparisonCacheReadResult(
            status="reader_error",
            left_ticker=left_ticker,
            right_ticker=right_ticker,
            diagnostics=(f"generated_output_cache:{exc.__class__.__name__}",),
        )
    return _GeneratedOutputComparisonCacheReadResult(
        status="found",
        left_ticker=left_ticker,
        right_ticker=right_ticker,
        records=validated,
        diagnostics=("generated_output_cache:found",),
    )


def _read_generated_comparison_cache_reader(
    reader: GeneratedOutputComparisonCacheRecordReader | Any,
    left_ticker: str,
    right_ticker: str,
) -> GeneratedOutputCacheRepositoryRecords | None:
    if isinstance(reader, dict):
        return (
            reader.get((left_ticker, right_ticker))
            or reader.get(f"{left_ticker}:{right_ticker}")
            or reader.get(f"{left_ticker}-to-{right_ticker}")
            or reader.get(_comparison_id(left_ticker, right_ticker))
        )
    if hasattr(reader, "read_comparison_records"):
        return reader.read_comparison_records(left_ticker, right_ticker)
    if hasattr(reader, "read_generated_comparison_records"):
        return reader.read_generated_comparison_records(left_ticker, right_ticker)
    if hasattr(reader, "read_generated_output_cache_records"):
        return reader.read_generated_output_cache_records(left_ticker, right_ticker)
    if hasattr(reader, "read"):
        return reader.read(left_ticker, right_ticker)
    if hasattr(reader, "get"):
        return reader.get((left_ticker, right_ticker))
    raise GeneratedOutputCacheContractError(
        "Injected generated-output comparison reader must expose read_comparison_records(left, right), "
        "read_generated_comparison_records(left, right), read_generated_output_cache_records(left, right), "
        "read(left, right), or get((left, right))."
    )


def _asset_knowledge_pack_from_repository_records(records: KnowledgePackRepositoryRecords) -> AssetKnowledgePack:
    source_rows = sorted(
        records.source_documents,
        key=lambda row: (row.asset_ticker, row.source_rank, row.source_document_id),
    )
    source_by_id = {row.source_document_id: row for row in source_rows}
    sources = [
        SourceDocumentFixture(
            source_document_id=row.source_document_id,
            asset_ticker=row.asset_ticker,
            source_type=row.source_type,
            source_rank=row.source_rank,
            title=row.title,
            publisher=row.publisher,
            url=row.url,
            published_at=row.published_at,
            retrieved_at=row.retrieved_at,
            content_type="text",
            is_official=row.is_official,
            freshness_state=FreshnessState(row.freshness_state),
            as_of_date=row.as_of_date,
            source_quality=row.source_quality,
            allowlist_status=row.allowlist_status,
            source_use_policy=row.source_use_policy,
        )
        for row in source_rows
    ]
    source_fixtures_by_id = {source.source_document_id: source for source in sources}

    chunks = []
    for row in sorted(records.source_chunks, key=lambda item: (item.source_document_id, item.chunk_order, item.chunk_id)):
        if not row.stored_text:
            raise KnowledgePackRepositoryContractError(
                f"Chunk {row.chunk_id} has no persisted text for comparison generation."
            )
        chunks.append(
            RetrievedSourceChunk(
                chunk=SourceChunkFixture(
                    chunk_id=row.chunk_id,
                    asset_ticker=row.asset_ticker,
                    source_document_id=row.source_document_id,
                    section_name=row.section_name,
                    chunk_order=row.chunk_order,
                    text=row.stored_text,
                    token_count=row.token_count,
                    char_start=0,
                    char_end=len(row.stored_text),
                    supported_claim_types=row.supported_claim_types,
                ),
                source_document=source_fixtures_by_id[row.source_document_id],
            )
        )
    chunks_by_id = {item.chunk.chunk_id: item for item in chunks}

    facts = []
    for row in sorted(records.normalized_facts, key=lambda item: item.fact_id):
        if row.value is None:
            raise KnowledgePackRepositoryContractError(f"Fact {row.fact_id} has no persisted value for comparison generation.")
        source = source_by_id[row.source_document_id]
        facts.append(
            RetrievedFact(
                fact=NormalizedFactFixture(
                    fact_id=row.fact_id,
                    asset_ticker=row.asset_ticker,
                    fact_type=row.fact_type,
                    field_name=row.field_name,
                    value=row.value,
                    unit=row.unit,
                    period=row.period,
                    as_of_date=row.as_of_date,
                    source_document_id=row.source_document_id,
                    source_chunk_id=row.source_chunk_id,
                    extraction_method=row.extraction_method,
                    confidence=float(row.confidence or 0.0),
                    freshness_state=FreshnessState(row.freshness_state),
                    evidence_state=row.evidence_state,
                ),
                source_document=source_fixtures_by_id[source.source_document_id],
                source_chunk=chunks_by_id[row.source_chunk_id].chunk,
            )
        )

    recent_developments = []
    for row in sorted(records.recent_developments, key=lambda item: item.event_id):
        if row.title is None or row.summary is None:
            raise KnowledgePackRepositoryContractError(
                f"Recent development {row.event_id} has no persisted title or summary for comparison generation."
            )
        source = source_by_id[row.source_document_id]
        recent_developments.append(
            RetrievedRecentDevelopment(
                recent_development=RecentDevelopmentFixture(
                    event_id=row.event_id,
                    asset_ticker=row.asset_ticker,
                    event_type=row.event_type,
                    title=row.title,
                    summary=row.summary,
                    event_date=row.event_date,
                    source_document_id=row.source_document_id,
                    source_chunk_id=row.source_chunk_id,
                    importance_score=row.importance_score,
                    freshness_state=FreshnessState(row.freshness_state),
                    evidence_state=row.evidence_state,
                ),
                source_document=source_fixtures_by_id[source.source_document_id],
                source_chunk=chunks_by_id[row.source_chunk_id].chunk,
            )
        )

    return AssetKnowledgePack(
        asset=AssetIdentity.model_validate(records.envelope.asset),
        freshness=Freshness.model_validate(records.envelope.freshness),
        source_documents=sources,
        normalized_facts=facts,
        source_chunks=chunks,
        recent_developments=recent_developments,
        evidence_gaps=[
            EvidenceGap(
                gap_id=row.gap_id,
                asset_ticker=row.asset_ticker,
                field_name=row.field_name,
                evidence_state=row.evidence_state,
                message=row.message or "",
                freshness_state=FreshnessState(row.freshness_state),
                source_document_id=row.source_document_id,
                source_chunk_id=row.source_chunk_id,
            )
            for row in sorted(records.evidence_gaps, key=lambda item: item.gap_id)
        ],
    )


def _validate_persisted_comparison_identity(
    pack: ComparisonKnowledgePack,
    fixture_pack: ComparisonKnowledgePack,
    left_ticker: str,
    right_ticker: str,
) -> None:
    if pack.left_asset_pack.asset.ticker != left_ticker or pack.right_asset_pack.asset.ticker != right_ticker:
        raise GeneratedOutputCacheContractError("Persisted comparison pack must preserve requested left/right identity.")
    if not pack.left_asset_pack.asset.supported or not pack.right_asset_pack.asset.supported:
        raise GeneratedOutputCacheContractError("Persisted comparison pack cannot generate output for unsupported assets.")
    if (
        pack.left_asset_pack.asset.asset_type != fixture_pack.left_asset_pack.asset.asset_type
        or pack.right_asset_pack.asset.asset_type != fixture_pack.right_asset_pack.asset.asset_type
    ):
        raise GeneratedOutputCacheContractError("Persisted comparison pack asset types must match deterministic scope.")


def _validate_generated_output_cache_for_comparison(
    left_ticker: str,
    right_ticker: str,
    records: GeneratedOutputCacheRepositoryRecords,
    *,
    pack: ComparisonKnowledgePack,
) -> None:
    if len(records.envelopes) != 1:
        raise GeneratedOutputCacheContractError("Comparison reuse requires exactly one generated-output cache envelope.")
    envelope = records.envelopes[0]
    if envelope.comparison_left_ticker != left_ticker or envelope.comparison_right_ticker != right_ticker:
        raise GeneratedOutputCacheContractError("Comparison cache must preserve requested left/right identity.")
    if envelope.comparison_id != pack.comparison_pack_id:
        raise GeneratedOutputCacheContractError("Comparison cache must bind to the requested comparison pack.")
    if envelope.entry_kind != CacheEntryKind.comparison.value or envelope.cache_scope != CacheScope.comparison.value:
        raise GeneratedOutputCacheContractError("Comparison cache records must be comparison scoped.")
    if envelope.artifact_category != GeneratedOutputArtifactCategory.comparison_output.value:
        raise GeneratedOutputCacheContractError("Comparison cache records must use the comparison output artifact category.")
    if envelope.output_identity != f"comparison:{left_ticker}-to-{right_ticker}":
        raise GeneratedOutputCacheContractError("Comparison cache output identity must match the requested direction.")
    if envelope.asset_ticker is not None:
        raise GeneratedOutputCacheContractError("Comparison cache records must not bind a single asset scope.")
    if not envelope.cacheable or not envelope.generated_output_available:
        raise GeneratedOutputCacheContractError("Comparison cache records must be cacheable and generated-output available.")

    pack_source_ids = {source.source_document_id for source in pack.comparison_sources}
    pack_citation_ids = {
        *{f"c_{item.fact.fact_id}" for item in [*pack.left_asset_pack.normalized_facts, *pack.right_asset_pack.normalized_facts]},
        *{f"c_{item.chunk.chunk_id}" for item in [*pack.left_asset_pack.source_chunks, *pack.right_asset_pack.source_chunks]},
        *{
            f"c_{item.recent_development.event_id}"
            for item in [*pack.left_asset_pack.recent_developments, *pack.right_asset_pack.recent_developments]
        },
    }
    if not set(envelope.source_document_ids) <= pack_source_ids:
        raise GeneratedOutputCacheContractError("Comparison cache source IDs must belong to the same comparison pack.")
    if not set(envelope.citation_ids) <= pack_citation_ids:
        raise GeneratedOutputCacheContractError("Comparison cache citation IDs must belong to the same comparison pack.")

    knowledge_input = build_comparison_pack_freshness_input(pack)
    if envelope.source_document_ids:
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in set(envelope.source_document_ids)
                ]
            }
        )
    expected_knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    if envelope.knowledge_pack_freshness_hash != expected_knowledge_hash:
        raise GeneratedOutputCacheContractError("Comparison cache knowledge-pack freshness hash does not match current evidence.")
    generated_input = build_generated_output_freshness_input(
        output_identity=envelope.output_identity,
        entry_kind=CacheEntryKind.comparison,
        scope=CacheScope.comparison,
        schema_version=envelope.schema_version,
        prompt_version=envelope.prompt_version,
        model_name=envelope.model_name,
        knowledge_input=knowledge_input,
    )
    if envelope.generated_output_freshness_hash != compute_generated_output_freshness_hash(generated_input):
        raise GeneratedOutputCacheContractError("Comparison cache generated-output freshness hash does not match current evidence.")


def _validate_comparison_cache_covers_response(
    records: GeneratedOutputCacheRepositoryRecords,
    response: CompareResponse,
) -> None:
    envelope = records.envelopes[0]
    response_source_ids = {source.source_document_id for source in response.source_documents}
    response_citation_ids = {citation.citation_id for citation in response.citations}
    if not response_source_ids <= set(envelope.source_document_ids):
        raise GeneratedOutputCacheContractError("Comparison cache source bindings do not cover generated response sources.")
    if envelope.citation_ids and not response_citation_ids <= set(envelope.citation_ids):
        raise GeneratedOutputCacheContractError("Comparison cache citation bindings do not cover generated response citations.")


def generate_comparison_from_pack(pack: ComparisonKnowledgePack) -> CompareResponse:
    if not pack.left_asset_pack.asset.supported or not pack.right_asset_pack.asset.supported:
        return _unavailable_comparison(pack.left_asset_pack, pack.right_asset_pack)
    if _is_stock_vs_stock(pack):
        return _generate_stock_vs_stock_comparison_from_pack(pack)
    if _is_stock_vs_etf(pack):
        return _generate_stock_vs_etf_comparison_from_pack(pack)

    bindings = _ComparisonCitationRegistry(pack)
    left_facts = _supported_facts_by_field(pack.left_asset_pack)
    right_facts = _supported_facts_by_field(pack.right_asset_pack)
    required_assets = [pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker]

    key_differences = [
        _benchmark_difference(pack, left_facts, right_facts, bindings),
        _expense_ratio_difference(pack, left_facts, right_facts, bindings),
        _holdings_count_difference(left_facts, right_facts, bindings),
        _breadth_difference(left_facts, right_facts, bindings),
        _educational_role_difference(pack, left_facts, right_facts, bindings),
    ]
    bottom_line = _bottom_line_for_beginners(pack, left_facts, right_facts, bindings)
    planned_claims = _planned_claims(key_differences, bottom_line, required_assets)

    report = validate_generated_comparison_claims(pack, planned_claims, bindings.evidence())
    if not report.valid:
        first_issue = report.issues[0]
        raise ComparisonGenerationError(
            f"Generated comparison citation validation failed for {pack.comparison_pack_id}: "
            f"{first_issue.status.value} on {first_issue.claim_id}"
        )

    response = CompareResponse(
        left_asset=pack.left_asset_pack.asset,
        right_asset=pack.right_asset_pack.asset,
        state=StateMessage(
            status=AssetStatus.supported,
            message="Comparison is supported by deterministic local retrieval fixtures.",
        ),
        comparison_type=f"{pack.left_asset_pack.asset.asset_type.value}_vs_{pack.right_asset_pack.asset.asset_type.value}",
        key_differences=key_differences,
        bottom_line_for_beginners=bottom_line,
        citations=bindings.citations(),
        source_documents=bindings.source_documents(),
    )
    response.evidence_availability = _available_evidence_availability(
        response=response,
        pack=pack,
        bindings=bindings,
        left_facts=left_facts,
        right_facts=right_facts,
    )
    _assert_safe_copy(response)
    return response


def _generate_stock_vs_stock_comparison_from_pack(pack: ComparisonKnowledgePack) -> CompareResponse:
    bindings = _ComparisonCitationRegistry(pack)
    left_facts = _supported_facts_by_field(pack.left_asset_pack)
    right_facts = _supported_facts_by_field(pack.right_asset_pack)
    required_assets = [pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker]

    key_differences = _stock_stock_key_differences(pack, left_facts, right_facts, bindings)
    bottom_line = _stock_stock_bottom_line(pack, left_facts, right_facts, bindings)
    planned_claims = _planned_claims(key_differences, bottom_line, required_assets)

    report = validate_generated_comparison_claims(pack, planned_claims, bindings.evidence())
    if not report.valid:
        first_issue = report.issues[0]
        raise ComparisonGenerationError(
            f"Generated stock-vs-stock citation validation failed for {pack.comparison_pack_id}: "
            f"{first_issue.status.value} on {first_issue.claim_id}"
        )

    response = CompareResponse(
        left_asset=pack.left_asset_pack.asset,
        right_asset=pack.right_asset_pack.asset,
        state=StateMessage(
            status=AssetStatus.supported,
            message="Stock-vs-stock comparison is supported by deterministic local retrieval fixtures.",
        ),
        comparison_type="stock_vs_stock",
        key_differences=key_differences,
        bottom_line_for_beginners=bottom_line,
        citations=bindings.citations(),
        source_documents=bindings.source_documents(),
        metric_groups=_stock_stock_metric_groups(pack, left_facts, right_facts, bindings),
    )
    response.evidence_availability = _available_stock_stock_evidence_availability(
        response=response,
        pack=pack,
        bindings=bindings,
        left_facts=left_facts,
        right_facts=right_facts,
    )
    _assert_safe_copy(response)
    return response


def _generate_stock_vs_etf_comparison_from_pack(pack: ComparisonKnowledgePack) -> CompareResponse:
    bindings = _ComparisonCitationRegistry(pack)
    left_facts = _supported_facts_by_field(pack.left_asset_pack)
    right_facts = _supported_facts_by_field(pack.right_asset_pack)
    stock_pack, etf_pack = _stock_etf_asset_packs(pack)
    stock_facts = left_facts if stock_pack.asset.ticker == pack.left_asset_pack.asset.ticker else right_facts
    etf_facts = left_facts if etf_pack.asset.ticker == pack.left_asset_pack.asset.ticker else right_facts
    required_assets = [pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker]

    key_differences = _stock_etf_key_differences(pack, stock_facts, etf_facts, bindings)
    bottom_line = _stock_etf_bottom_line(pack, stock_facts, etf_facts, bindings)
    planned_claims = _planned_claims(key_differences, bottom_line, required_assets)

    report = validate_generated_comparison_claims(pack, planned_claims, bindings.evidence())
    if not report.valid:
        first_issue = report.issues[0]
        raise ComparisonGenerationError(
            f"Generated stock-vs-ETF citation validation failed for {pack.comparison_pack_id}: "
            f"{first_issue.status.value} on {first_issue.claim_id}"
        )

    response = CompareResponse(
        left_asset=pack.left_asset_pack.asset,
        right_asset=pack.right_asset_pack.asset,
        state=StateMessage(
            status=AssetStatus.supported,
            message="Stock-vs-ETF comparison is supported by deterministic local retrieval fixtures.",
        ),
        comparison_type="stock_vs_etf",
        key_differences=key_differences,
        bottom_line_for_beginners=bottom_line,
        citations=bindings.citations(),
        source_documents=bindings.source_documents(),
        stock_etf_relationship=_stock_etf_relationship_model(stock_pack, etf_pack, stock_facts, etf_facts, bindings),
    )
    response.evidence_availability = _available_stock_etf_evidence_availability(
        response=response,
        pack=pack,
        bindings=bindings,
        stock_pack=stock_pack,
        etf_pack=etf_pack,
        stock_facts=stock_facts,
        etf_facts=etf_facts,
    )
    _assert_safe_copy(response)
    return response


def _stock_etf_key_differences(
    pack: ComparisonKnowledgePack,
    stock_facts: dict[str, RetrievedFact],
    etf_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> list[KeyDifference]:
    for dimension in STOCK_ETF_COMPARISON_DIMENSIONS:
        _require_difference(pack, dimension)

    stock_identity = _require_fact(stock_facts, "canonical_asset_identity")
    stock_business = _require_fact(stock_facts, "primary_business")
    etf_benchmark = _require_fact(etf_facts, "benchmark")
    etf_holdings = _require_fact(etf_facts, "holdings_exposure_detail")
    etf_holdings_count = _require_fact(etf_facts, "holdings_count")
    etf_expense = _require_fact(etf_facts, "expense_ratio")
    etf_role = _require_fact(etf_facts, "beginner_role")

    stock_ticker = stock_identity.fact.asset_ticker
    etf_ticker = etf_benchmark.fact.asset_ticker

    return [
        KeyDifference(
            dimension="Structure",
            plain_english_summary=(
                f"{stock_ticker} is represented by the local filing fixture as one operating company, while "
                f"{etf_ticker} is represented by issuer fixtures as an ETF basket that tracks the {etf_benchmark.fact.value}."
            ),
            citation_ids=[
                bindings.for_fact(stock_business).citation.citation_id,
                bindings.for_fact(etf_benchmark).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Basket membership",
            plain_english_summary=(
                f"{etf_ticker}'s local holdings fixture lists Apple among top holdings, but this deterministic pack "
                "does not verify a precise holding weight, sector exposure, top-10 concentration, or full overlap calculation."
            ),
            citation_ids=[
                bindings.for_fact(stock_identity).citation.citation_id,
                bindings.for_fact(etf_holdings).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Breadth",
            plain_english_summary=(
                f"{stock_ticker} is one company in this comparison, while the local facts list {etf_ticker} "
                f"with about {_format_metric(etf_holdings_count.fact.value, etf_holdings_count.fact.unit)}."
            ),
            citation_ids=[
                bindings.for_fact(stock_identity).citation.citation_id,
                bindings.for_fact(etf_holdings_count).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Cost model",
            plain_english_summary=(
                f"{etf_ticker} has an ETF expense-ratio fact in the local issuer fixture; {stock_ticker} is a common "
                "stock in this pack, so an ETF expense ratio is not the matching comparison field."
            ),
            citation_ids=[
                bindings.for_fact(stock_identity).citation.citation_id,
                bindings.for_fact(etf_expense).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Educational role",
            plain_english_summary=(
                f"This stock-vs-ETF view separates learning about {stock_ticker}'s single business from learning "
                f"about {etf_ticker}'s basket exposure and {_role_phrase(etf_role.fact.value)} role."
            ),
            citation_ids=[
                bindings.for_fact(stock_business).citation.citation_id,
                bindings.for_fact(etf_role).citation.citation_id,
                bindings.for_fact(etf_holdings).citation.citation_id,
            ],
        ),
    ]


def _stock_etf_bottom_line(
    pack: ComparisonKnowledgePack,
    stock_facts: dict[str, RetrievedFact],
    etf_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> BeginnerBottomLine:
    stock_identity = _require_fact(stock_facts, "canonical_asset_identity")
    stock_business = _require_fact(stock_facts, "primary_business")
    etf_benchmark = _require_fact(etf_facts, "benchmark")
    etf_holdings = _require_fact(etf_facts, "holdings_exposure_detail")
    etf_holdings_count = _require_fact(etf_facts, "holdings_count")

    stock_ticker = stock_identity.fact.asset_ticker
    etf_ticker = etf_benchmark.fact.asset_ticker
    return BeginnerBottomLine(
        summary=(
            f"{stock_ticker} and {etf_ticker} are different structures: one is a single company, and the other "
            "is an ETF basket. The local evidence verifies that Apple appears in the VOO holdings fixture, but "
            "it does not verify a precise holding weight or full overlap calculation, so this comparison treats "
            "the relationship as partial educational context."
        ),
        citation_ids=[
            bindings.for_fact(stock_identity).citation.citation_id,
            bindings.for_fact(stock_business).citation.citation_id,
            bindings.for_fact(etf_benchmark).citation.citation_id,
            bindings.for_fact(etf_holdings).citation.citation_id,
            bindings.for_fact(etf_holdings_count).citation.citation_id,
        ],
    )


def _stock_etf_relationship_model(
    stock_pack: AssetKnowledgePack,
    etf_pack: AssetKnowledgePack,
    stock_facts: dict[str, RetrievedFact],
    etf_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> StockEtfRelationshipModel:
    stock_identity = _require_fact(stock_facts, "canonical_asset_identity")
    stock_business = _require_fact(stock_facts, "primary_business")
    etf_benchmark = _require_fact(etf_facts, "benchmark")
    etf_holdings = _require_fact(etf_facts, "holdings_exposure_detail")
    etf_holdings_count = _require_fact(etf_facts, "holdings_count")

    stock_citation = bindings.for_fact(stock_business).citation.citation_id
    stock_identity_citation = bindings.for_fact(stock_identity).citation.citation_id
    etf_profile_citation = bindings.for_fact(etf_benchmark).citation.citation_id
    etf_holdings_citation = bindings.for_fact(etf_holdings).citation.citation_id
    etf_holdings_count_citation = bindings.for_fact(etf_holdings_count).citation.citation_id

    stock_ticker = stock_pack.asset.ticker
    etf_ticker = etf_pack.asset.ticker
    return StockEtfRelationshipModel(
        stock_ticker=stock_ticker,
        etf_ticker=etf_ticker,
        relationship_state="direct_holding",
        evidence_state=EvidenceState.partial,
        badges=[
            StockEtfRelationshipBadge(
                label="Comparison type",
                value="Stock vs ETF",
                marker="comparison_type",
                relationship_state="direct_holding",
                evidence_state=EvidenceState.supported,
                citation_ids=[stock_citation, etf_profile_citation],
            ),
            StockEtfRelationshipBadge(
                label="Stock ticker",
                value=stock_ticker,
                marker="stock_ticker",
                relationship_state="direct_holding",
                evidence_state=EvidenceState.supported,
                citation_ids=[stock_identity_citation],
            ),
            StockEtfRelationshipBadge(
                label="ETF ticker",
                value=etf_ticker,
                marker="etf_ticker",
                relationship_state="direct_holding",
                evidence_state=EvidenceState.supported,
                citation_ids=[etf_profile_citation],
            ),
            StockEtfRelationshipBadge(
                label="Relationship state",
                value="Direct holding listed; exact weight unavailable",
                marker="relationship_state",
                relationship_state="direct_holding",
                evidence_state=EvidenceState.partial,
                citation_ids=[stock_identity_citation, etf_holdings_citation],
            ),
            StockEtfRelationshipBadge(
                label="Evidence boundary",
                value="Same comparison pack only",
                marker="evidence_boundary",
                relationship_state="direct_holding",
                evidence_state=EvidenceState.supported,
                citation_ids=[stock_citation, etf_profile_citation, etf_holdings_citation],
            ),
        ],
        basket_structure=StockEtfBasketStructure(
            stock_ticker=stock_ticker,
            etf_ticker=etf_ticker,
            stock_role_summary=f"{stock_ticker} is shown as a single company with products, services, and company-specific risks.",
            etf_basket_summary=(
                f"{etf_ticker} is shown as an ETF basket with about "
                f"{_format_metric(etf_holdings_count.fact.value, etf_holdings_count.fact.unit)} in the local fixture."
            ),
            relationship_summary=(
                "The local VOO holdings fixture lists Apple among top holdings. The pack does not include exact "
                "holding weight, sector exposure, top-10 concentration, or full overlap evidence, so the "
                "relationship is labeled partial."
            ),
            overlap_or_membership_state="direct_holding",
            evidence_state=EvidenceState.partial,
            unavailable_detail=(
                "Exact holding weight, top-10 concentration, sector exposure, and full overlap are unavailable "
                "in this deterministic pack."
            ),
            citation_ids=[stock_identity_citation, stock_citation, etf_profile_citation, etf_holdings_citation, etf_holdings_count_citation],
        ),
    )


def _stock_stock_key_differences(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> list[KeyDifference]:
    for dimension in STOCK_STOCK_COMPARISON_DIMENSIONS:
        _require_difference(pack, dimension)

    left_business = _require_fact(left_facts, "primary_business")
    right_business = _require_fact(right_facts, "primary_business")
    left_revenue = _require_fact(left_facts, "financial_quality_revenue_trend")
    right_revenue = _require_fact(right_facts, "financial_quality_revenue_trend")
    left_quality = _require_fact(left_facts, "business_quality_strength")
    right_quality = _require_fact(right_facts, "business_quality_strength")
    left_risk = _require_fact(left_facts, "company_specific_risk")
    right_risk = _require_fact(right_facts, "company_specific_risk")
    left_valuation = _require_fact(left_facts, "valuation_data_limitation")
    right_valuation = _require_fact(right_facts, "valuation_data_limitation")

    left_ticker = pack.left_asset_pack.asset.ticker
    right_ticker = pack.right_asset_pack.asset.ticker
    return [
        KeyDifference(
            dimension="Business model",
            plain_english_summary=(
                f"{left_ticker}'s local filing fixture describes the business as {str(left_business.fact.value).lower()} "
                f"{right_ticker}'s fixture describes the business as {str(right_business.fact.value).lower()}"
            ),
            citation_ids=[
                bindings.for_fact(left_business).citation.citation_id,
                bindings.for_fact(right_business).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Revenue trend",
            plain_english_summary=(
                f"The local SEC XBRL fixtures record {left_ticker} revenue moving from {left_revenue.fact.value}, "
                f"while {right_ticker} revenue moved from {right_revenue.fact.value}."
            ),
            citation_ids=[
                bindings.for_fact(left_revenue).citation.citation_id,
                bindings.for_fact(right_revenue).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Business quality evidence",
            plain_english_summary=(
                f"{left_ticker}'s fixture evidence highlights {left_quality.fact.value} "
                f"{right_ticker}'s fixture evidence highlights {right_quality.fact.value}"
            ),
            citation_ids=[
                bindings.for_fact(left_quality).citation.citation_id,
                bindings.for_fact(right_quality).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Risk context",
            plain_english_summary=(
                f"{left_ticker}'s risk fixture notes product demand, competition, supply chain, regulation, "
                f"and company-specific risks; {right_ticker}'s risk fixture notes cloud/software competition, "
                "cybersecurity, regulation, and customer-spending risks."
            ),
            citation_ids=[
                bindings.for_fact(left_risk).citation.citation_id,
                bindings.for_fact(right_risk).citation.citation_id,
            ],
        ),
        KeyDifference(
            dimension="Valuation evidence availability",
            plain_english_summary=(
                f"The local fixtures do not include current valuation metrics for {left_ticker} or {right_ticker}, "
                "so this comparison does not compare valuation levels."
            ),
            citation_ids=[
                bindings.for_fact(left_valuation).citation.citation_id,
                bindings.for_fact(right_valuation).citation.citation_id,
            ],
        ),
    ]


def _stock_stock_bottom_line(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> BeginnerBottomLine:
    left_business = _require_fact(left_facts, "primary_business")
    right_business = _require_fact(right_facts, "primary_business")
    left_revenue = _require_fact(left_facts, "financial_quality_revenue_trend")
    right_revenue = _require_fact(right_facts, "financial_quality_revenue_trend")
    left_risk = _require_fact(left_facts, "company_specific_risk")
    right_risk = _require_fact(right_facts, "company_specific_risk")
    left_ticker = pack.left_asset_pack.asset.ticker
    right_ticker = pack.right_asset_pack.asset.ticker

    return BeginnerBottomLine(
        summary=(
            f"{left_ticker} and {right_ticker} are both single-company stocks in this deterministic pack. "
            "For beginner learning, compare the source-backed business model, revenue trend, and risk context; "
            "do not treat this as a personal decision rule."
        ),
        citation_ids=[
            bindings.for_fact(left_business).citation.citation_id,
            bindings.for_fact(right_business).citation.citation_id,
            bindings.for_fact(left_revenue).citation.citation_id,
            bindings.for_fact(right_revenue).citation.citation_id,
            bindings.for_fact(left_risk).citation.citation_id,
            bindings.for_fact(right_risk).citation.citation_id,
        ],
    )


def _stock_stock_metric_groups(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> list[ComparisonMetricGroup]:
    left_revenue = _require_fact(left_facts, "financial_quality_revenue_trend")
    right_revenue = _require_fact(right_facts, "financial_quality_revenue_trend")
    left_business = _require_fact(left_facts, "primary_business")
    right_business = _require_fact(right_facts, "primary_business")
    left_valuation = _require_fact(left_facts, "valuation_data_limitation")
    right_valuation = _require_fact(right_facts, "valuation_data_limitation")
    left_quality = _require_fact(left_facts, "business_quality_strength")
    right_quality = _require_fact(right_facts, "business_quality_strength")

    return [
        _comparison_metric_group(
            "profile",
            "Profile",
            [
                _comparison_metric_row(
                    pack,
                    "primary_business",
                    "Primary business",
                    left_business.fact.value,
                    right_business.fact.value,
                    [bindings.for_fact(left_business).citation.citation_id, bindings.for_fact(right_business).citation.citation_id],
                    bindings,
                    EvidenceState.supported,
                ),
            ],
            bindings,
        ),
        _comparison_metric_group(
            "market_value_enterprise_value",
            "Market Value / Enterprise Value",
            [
                _unavailable_comparison_metric_row("market_cap", "Market cap"),
                _unavailable_comparison_metric_row("enterprise_value", "Enterprise value"),
            ],
            bindings,
            limitations="The deterministic stock comparison pack does not include current market cap or enterprise value.",
        ),
        _comparison_metric_group(
            "price_performance",
            "Price Performance",
            [
                _unavailable_comparison_metric_row("one_week_price_performance", "1-week price performance"),
                _unavailable_comparison_metric_row("three_month_price_performance", "3-month price performance"),
                _unavailable_comparison_metric_row("ytd_price_performance", "YTD price performance"),
                _unavailable_comparison_metric_row("one_year_price_performance", "1-year price performance"),
            ],
            bindings,
            limitations="Price-performance fields require provider or market-data enrichment and remain unavailable in this deterministic comparison pack.",
        ),
        _comparison_metric_group(
            "income_statement",
            "Income Statement",
            [
                _comparison_metric_row(
                    pack,
                    "revenue_trend",
                    "Revenue trend",
                    left_revenue.fact.value,
                    right_revenue.fact.value,
                    [bindings.for_fact(left_revenue).citation.citation_id, bindings.for_fact(right_revenue).citation.citation_id],
                    bindings,
                    EvidenceState.supported,
                    as_of_date=left_revenue.fact.as_of_date or right_revenue.fact.as_of_date,
                ),
            ],
            bindings,
        ),
        _comparison_metric_group(
            "balance_sheet",
            "Balance Sheet",
            [_unavailable_comparison_metric_row("balance_sheet_snapshot", "Balance sheet snapshot")],
            bindings,
            limitations="Balance-sheet comparison rows are unavailable until the comparison pack includes normalized balance-sheet facts.",
        ),
        _comparison_metric_group(
            "cash_flow",
            "Cash Flow",
            [_unavailable_comparison_metric_row("cash_flow_snapshot", "Cash-flow snapshot")],
            bindings,
            limitations="Cash-flow comparison rows are unavailable until the comparison pack includes normalized cash-flow facts.",
        ),
        _comparison_metric_group(
            "valuation_ratios",
            "Valuation Ratios",
            [
                _comparison_metric_row(
                    pack,
                    "valuation_data_availability",
                    "Valuation data availability",
                    left_valuation.fact.value,
                    right_valuation.fact.value,
                    [bindings.for_fact(left_valuation).citation.citation_id, bindings.for_fact(right_valuation).citation.citation_id],
                    bindings,
                    EvidenceState.partial,
                    as_of_date=left_valuation.fact.as_of_date or right_valuation.fact.as_of_date,
                    limitations="Current ratio values are unavailable; row explains the evidence gap.",
                ),
            ],
            bindings,
            limitations="The comparison does not compare current valuation levels because the local fixture marks those fields unavailable.",
        ),
        _comparison_metric_group(
            "margins_earnings_returns_ownership",
            "Margins, Earnings, Returns, And Ownership",
            [
                _comparison_metric_row(
                    pack,
                    "business_quality_context",
                    "Business quality context",
                    left_quality.fact.value,
                    right_quality.fact.value,
                    [bindings.for_fact(left_quality).citation.citation_id, bindings.for_fact(right_quality).citation.citation_id],
                    bindings,
                    EvidenceState.supported,
                ),
                _unavailable_comparison_metric_row("margin_ratios", "Margin ratios"),
                _unavailable_comparison_metric_row("earnings_snapshot", "Earnings snapshot"),
                _unavailable_comparison_metric_row("returns_snapshot", "Returns snapshot"),
                _unavailable_comparison_metric_row("ownership_snapshot", "Ownership snapshot"),
            ],
            bindings,
            limitations="Only business-quality context is available; margin, earnings, returns, and ownership metrics need normalized provider or SEC facts.",
        ),
    ]


def _comparison_metric_group(
    group_id: str,
    title: str,
    rows: list[ComparisonMetricRow],
    bindings: _ComparisonCitationRegistry,
    *,
    limitations: str | None = None,
) -> ComparisonMetricGroup:
    citation_ids = sorted({citation_id for row in rows for citation_id in row.citation_ids})
    evidence_states = {row.evidence_state for row in rows}
    evidence_state = EvidenceState.supported if evidence_states == {EvidenceState.supported} else EvidenceState.partial if citation_ids else EvidenceState.unavailable
    freshness_state = _combined_freshness([row.freshness_state for row in rows]) if citation_ids else FreshnessState.unavailable
    return ComparisonMetricGroup(
        group_id=group_id,
        title=title,
        rows=rows,
        citation_ids=citation_ids,
        source_document_ids=_source_document_ids_for_citations(citation_ids, bindings),
        freshness_state=freshness_state,
        evidence_state=evidence_state,
        limitations=limitations,
    )


def _comparison_metric_row(
    pack: ComparisonKnowledgePack,
    metric_id: str,
    label: str,
    left_value: Any,
    right_value: Any,
    citation_ids: list[str],
    bindings: _ComparisonCitationRegistry,
    evidence_state: EvidenceState,
    *,
    as_of_date: str | None = None,
    limitations: str | None = None,
) -> ComparisonMetricRow:
    del pack
    return ComparisonMetricRow(
        metric_id=metric_id,
        label=label,
        left_value=_comparison_metric_value(left_value),
        right_value=_comparison_metric_value(right_value),
        citation_ids=citation_ids,
        source_document_ids=_source_document_ids_for_citations(citation_ids, bindings),
        freshness_state=_combined_freshness(
            [
                binding.citation.freshness_state
                for citation_id in citation_ids
                for binding in [bindings.binding_for_citation_id(citation_id)]
                if binding is not None
            ]
        ),
        evidence_state=evidence_state,
        as_of_date=as_of_date,
        limitations=limitations,
    )


def _unavailable_comparison_metric_row(metric_id: str, label: str) -> ComparisonMetricRow:
    return ComparisonMetricRow(
        metric_id=metric_id,
        label=label,
        left_value="Unavailable in current evidence",
        right_value="Unavailable in current evidence",
        citation_ids=[],
        source_document_ids=[],
        freshness_state=FreshnessState.unavailable,
        evidence_state=EvidenceState.unavailable,
        limitations="Unavailable in the deterministic local comparison pack.",
    )


def _comparison_metric_value(value: Any) -> str | float | int | None:
    if isinstance(value, (str, int, float)) or value is None:
        return value
    return str(value)


def validate_comparison_response(
    comparison: CompareResponse,
    pack: ComparisonKnowledgePack,
) -> CitationValidationReport:
    bindings = _ComparisonCitationRegistry(pack)
    used_citation_ids = {
        *{citation_id for item in comparison.key_differences for citation_id in item.citation_ids},
        *(
            set(comparison.bottom_line_for_beginners.citation_ids)
            if comparison.bottom_line_for_beginners is not None
            else set()
        ),
    }
    evidence = bindings.evidence_for_citation_ids(used_citation_ids)
    claims = [
        CitationValidationClaim(
            claim_id=f"claim_comparison_{_claim_slug(item.dimension)}",
            claim_text=item.plain_english_summary,
            claim_type="comparison",
            citation_ids=item.citation_ids,
            freshness_label=_comparison_claim_freshness_label(item.dimension),
            required_asset_tickers=[pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker],
        )
        for item in comparison.key_differences
    ]
    if comparison.bottom_line_for_beginners is not None:
        claims.append(
            CitationValidationClaim(
                claim_id="claim_comparison_bottom_line",
                claim_text=comparison.bottom_line_for_beginners.summary,
                claim_type="comparison",
                citation_ids=comparison.bottom_line_for_beginners.citation_ids,
                required_asset_tickers=[pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker],
            )
        )

    report = validate_claims(
        claims,
        evidence,
        CitationValidationContext(
            allowed_asset_tickers=[pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker],
            comparison_pack_id=pack.comparison_pack_id,
        ),
    )
    if not report.valid:
        return report
    return _validate_comparison_source_documents(comparison, pack)


def _maybe_write_comparison_generated_output_cache(
    comparison: CompareResponse,
    pack: ComparisonKnowledgePack,
    writer: Any | None,
) -> None:
    if writer is None or comparison.state.status is not AssetStatus.supported:
        return
    try:
        report = validate_comparison_response(comparison, pack)
        if not report.valid or find_forbidden_output_phrases(str(comparison.model_dump(mode="json"))):
            return
        source_ids = {source.source_document_id for source in comparison.source_documents}
        citations_by_source: dict[str, list[str]] = {}
        for citation in comparison.citations:
            citations_by_source.setdefault(citation.source_document_id, []).append(citation.citation_id)
        knowledge_input = build_comparison_pack_freshness_input(pack)
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum.model_copy(
                        update={"citation_ids": sorted(citations_by_source.get(checksum.source_document_id, []))}
                    )
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in source_ids
                ]
            }
        )
        records = build_deterministic_generated_output_cache_records(
            cache_entry_id=(
                f"generated-output-{comparison.left_asset.ticker.lower()}-"
                f"{comparison.right_asset.ticker.lower()}-comparison"
            ),
            output_identity=f"comparison:{comparison.left_asset.ticker}-to-{comparison.right_asset.ticker}",
            mode_or_output_type="beginner-comparison",
            artifact_category=GeneratedOutputArtifactCategory.comparison_output,
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            schema_version="comparison-v1",
            prompt_version="comparison-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=[citation.citation_id for citation in comparison.citations],
            created_at="2026-04-25T18:33:44Z",
            ttl_seconds=604800,
            comparison_id=pack.comparison_pack_id,
            comparison_left_ticker=comparison.left_asset.ticker,
            comparison_right_ticker=comparison.right_asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


def validate_generated_comparison_claims(
    pack: ComparisonKnowledgePack,
    planned_claims: Iterable[PlannedComparisonClaim],
    evidence: list[CitationEvidence],
) -> CitationValidationReport:
    claims = [
        CitationValidationClaim(
            claim_id=planned.claim_id,
            claim_text=planned.claim_text,
            claim_type=planned.claim_type,
            citation_ids=planned.citation_ids,
            freshness_label=planned.freshness_label,
            required_asset_tickers=planned.required_asset_tickers
            or [pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker],
        )
        for planned in planned_claims
    ]
    return validate_claims(
        claims,
        evidence,
        CitationValidationContext(
            allowed_asset_tickers=[pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker],
            comparison_pack_id=pack.comparison_pack_id,
        ),
    )


class _ComparisonCitationRegistry:
    def __init__(self, pack: ComparisonKnowledgePack) -> None:
        self._pack = pack
        self._bindings_by_citation_id: dict[str, CitationBinding] = {}
        self._facts_by_id = {
            item.fact.fact_id: item
            for item in [*pack.left_asset_pack.normalized_facts, *pack.right_asset_pack.normalized_facts]
        }
        self._chunks_by_id = {
            item.chunk.chunk_id: item
            for item in [*pack.left_asset_pack.source_chunks, *pack.right_asset_pack.source_chunks]
        }

    def for_fact(self, retrieved_fact: RetrievedFact) -> CitationBinding:
        citation_id = f"c_{retrieved_fact.fact.fact_id}"
        source_document = _source_document_from_fixture(retrieved_fact.source_document, retrieved_fact.source_chunk.text)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=retrieved_fact.fact.asset_ticker,
            source_document_id=source_document.source_document_id,
            source_type=source_document.source_type,
            evidence_kind=EvidenceKind.normalized_fact,
            freshness_state=retrieved_fact.fact.freshness_state,
            retrieved_at=source_document.retrieved_at,
            as_of_date=source_document.as_of_date,
            published_at=source_document.published_at,
            supported_claim_types=retrieved_fact.source_chunk.supported_claim_types,
            supporting_text=retrieved_fact.source_chunk.text,
            supports_claim=retrieved_fact.fact.evidence_state == "supported",
            is_recent=False,
            allowlist_status=source_document.allowlist_status,
            source_use_policy=source_document.source_use_policy,
            source_identity=source_document.source_identity,
            is_official=source_document.is_official,
            source_quality=source_document.source_quality,
            storage_rights=source_document.storage_rights,
            export_rights=source_document.export_rights,
            review_status=source_document.review_status,
            approval_rationale=source_document.approval_rationale,
            parser_status=source_document.parser_status,
            parser_failure_diagnostics=source_document.parser_failure_diagnostics,
        )
        return self._add_binding(citation_id, retrieved_fact.source_document, evidence)

    def for_chunk(self, retrieved_chunk: RetrievedSourceChunk) -> CitationBinding:
        citation_id = f"c_{retrieved_chunk.chunk.chunk_id}"
        source_document = _source_document_from_fixture(retrieved_chunk.source_document, retrieved_chunk.chunk.text)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=retrieved_chunk.chunk.asset_ticker,
            source_document_id=source_document.source_document_id,
            source_type=source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=retrieved_chunk.source_document.freshness_state,
            retrieved_at=source_document.retrieved_at,
            as_of_date=source_document.as_of_date,
            published_at=source_document.published_at,
            supported_claim_types=retrieved_chunk.chunk.supported_claim_types,
            supporting_text=retrieved_chunk.chunk.text,
            supports_claim=True,
            is_recent=False,
            allowlist_status=source_document.allowlist_status,
            source_use_policy=source_document.source_use_policy,
            source_identity=source_document.source_identity,
            is_official=source_document.is_official,
            source_quality=source_document.source_quality,
            storage_rights=source_document.storage_rights,
            export_rights=source_document.export_rights,
            review_status=source_document.review_status,
            approval_rationale=source_document.approval_rationale,
            parser_status=source_document.parser_status,
            parser_failure_diagnostics=source_document.parser_failure_diagnostics,
        )
        return self._add_binding(citation_id, retrieved_chunk.source_document, evidence)

    def citations(self) -> list[Citation]:
        return [binding.citation for binding in self._sorted_bindings()]

    def source_documents(self) -> list[SourceDocument]:
        by_id = {binding.source_document.source_document_id: binding.source_document for binding in self._sorted_bindings()}
        return list(by_id.values())

    def evidence(self) -> list[CitationEvidence]:
        return [binding.evidence for binding in self._sorted_bindings()]

    def evidence_for_citation_ids(self, citation_ids: Iterable[str]) -> list[CitationEvidence]:
        evidence: list[CitationEvidence] = []
        for citation_id in sorted(set(citation_ids)):
            binding = self._binding_for_citation_id(citation_id)
            if binding is not None:
                evidence.append(binding.evidence)
        return evidence

    def binding_for_citation_id(self, citation_id: str) -> CitationBinding | None:
        return self._binding_for_citation_id(citation_id)

    def _binding_for_citation_id(self, citation_id: str) -> CitationBinding | None:
        existing = self._bindings_by_citation_id.get(citation_id)
        if existing is not None:
            return existing

        if not citation_id.startswith("c_"):
            return None

        evidence_id = citation_id[2:]
        fact = self._facts_by_id.get(evidence_id)
        if fact is not None:
            return self.for_fact(fact)
        chunk = self._chunks_by_id.get(evidence_id)
        if chunk is not None:
            return self.for_chunk(chunk)
        return None

    def _add_binding(
        self,
        citation_id: str,
        source_fixture: SourceDocumentFixture,
        evidence: CitationEvidence,
    ) -> CitationBinding:
        binding = self._bindings_by_citation_id.get(citation_id)
        if binding is not None:
            return binding

        binding = CitationBinding(
            citation=Citation(
                citation_id=citation_id,
                source_document_id=source_fixture.source_document_id,
                title=source_fixture.title,
                publisher=source_fixture.publisher,
                freshness_state=source_fixture.freshness_state,
            ),
            source_document=_source_document_from_fixture(source_fixture, evidence.supporting_text or ""),
            evidence=evidence,
        )
        self._bindings_by_citation_id[citation_id] = binding
        return binding

    def _sorted_bindings(self) -> list[CitationBinding]:
        return sorted(self._bindings_by_citation_id.values(), key=lambda binding: binding.citation.citation_id)


def _benchmark_difference(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> KeyDifference:
    _require_difference(pack, "Benchmark")
    left_benchmark = _require_fact(left_facts, "benchmark")
    right_benchmark = _require_fact(right_facts, "benchmark")
    return KeyDifference(
        dimension="Benchmark",
        plain_english_summary=(
            f"{pack.left_asset_pack.asset.ticker} tracks the {left_benchmark.fact.value}, while "
            f"{pack.right_asset_pack.asset.ticker} tracks the {right_benchmark.fact.value}."
        ),
        citation_ids=[bindings.for_fact(left_benchmark).citation.citation_id, bindings.for_fact(right_benchmark).citation.citation_id],
    )


def _expense_ratio_difference(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> KeyDifference:
    _require_difference(pack, "Expense ratio")
    left_expense = _require_fact(left_facts, "expense_ratio")
    right_expense = _require_fact(right_facts, "expense_ratio")
    return KeyDifference(
        dimension="Expense ratio",
        plain_english_summary=(
            f"The fixture records {pack.left_asset_pack.asset.ticker}'s expense ratio as "
            f"{_format_metric(left_expense.fact.value, left_expense.fact.unit)} and "
            f"{pack.right_asset_pack.asset.ticker}'s as {_format_metric(right_expense.fact.value, right_expense.fact.unit)}."
        ),
        citation_ids=[bindings.for_fact(left_expense).citation.citation_id, bindings.for_fact(right_expense).citation.citation_id],
    )


def _holdings_count_difference(
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> KeyDifference:
    left_holdings = _require_fact(left_facts, "holdings_count")
    right_holdings = _require_fact(right_facts, "holdings_count")
    return KeyDifference(
        dimension="Holdings count",
        plain_english_summary=(
            f"The local facts list {left_holdings.fact.asset_ticker} with about "
            f"{_format_metric(left_holdings.fact.value, left_holdings.fact.unit)} and "
            f"{right_holdings.fact.asset_ticker} with about {_format_metric(right_holdings.fact.value, right_holdings.fact.unit)}."
        ),
        citation_ids=[bindings.for_fact(left_holdings).citation.citation_id, bindings.for_fact(right_holdings).citation.citation_id],
    )


def _breadth_difference(
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> KeyDifference:
    left_holdings = _require_fact(left_facts, "holdings_count")
    right_holdings = _require_fact(right_facts, "holdings_count")
    broader, narrower = _broader_and_narrower(left_holdings, right_holdings)
    return KeyDifference(
        dimension="Breadth",
        plain_english_summary=(
            f"Using holdings count as the local breadth signal, {broader.fact.asset_ticker} is broader than "
            f"{narrower.fact.asset_ticker}; this is not a full overlap calculation."
        ),
        citation_ids=[bindings.for_fact(left_holdings).citation.citation_id, bindings.for_fact(right_holdings).citation.citation_id],
    )


def _educational_role_difference(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> KeyDifference:
    _require_difference(pack, "Beginner role")
    left_role = _require_fact(left_facts, "beginner_role")
    right_role = _require_fact(right_facts, "beginner_role")
    return KeyDifference(
        dimension="Educational role",
        plain_english_summary=(
            f"The local education facts frame {pack.left_asset_pack.asset.ticker} as "
            f"{_role_phrase(left_role.fact.value)} and {pack.right_asset_pack.asset.ticker} as "
            f"{_role_phrase(right_role.fact.value)}."
        ),
        citation_ids=[bindings.for_fact(left_role).citation.citation_id, bindings.for_fact(right_role).citation.citation_id],
    )


def _bottom_line_for_beginners(
    pack: ComparisonKnowledgePack,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
    bindings: _ComparisonCitationRegistry,
) -> BeginnerBottomLine:
    left_role = _require_fact(left_facts, "beginner_role")
    right_role = _require_fact(right_facts, "beginner_role")
    left_holdings = _require_fact(left_facts, "holdings_count")
    right_holdings = _require_fact(right_facts, "holdings_count")
    left_expense = _require_fact(left_facts, "expense_ratio")
    right_expense = _require_fact(right_facts, "expense_ratio")

    return BeginnerBottomLine(
        summary=(
            f"For beginner learning, {pack.left_asset_pack.asset.ticker} is framed as "
            f"{_role_phrase(left_role.fact.value)}, while {pack.right_asset_pack.asset.ticker} is framed as "
            f"{_role_phrase(right_role.fact.value)}. Compare their benchmark, cost, and holdings breadth as source-backed "
            "structure facts, not as a personal decision rule."
        ),
        citation_ids=[
            bindings.for_fact(left_role).citation.citation_id,
            bindings.for_fact(right_role).citation.citation_id,
            bindings.for_fact(left_holdings).citation.citation_id,
            bindings.for_fact(right_holdings).citation.citation_id,
            bindings.for_fact(left_expense).citation.citation_id,
            bindings.for_fact(right_expense).citation.citation_id,
        ],
    )


def _planned_claims(
    key_differences: list[KeyDifference],
    bottom_line: BeginnerBottomLine,
    required_assets: list[str],
) -> list[PlannedComparisonClaim]:
    planned = [
        PlannedComparisonClaim(
            claim_id=f"claim_comparison_{_claim_slug(item.dimension)}",
            claim_text=item.plain_english_summary,
            citation_ids=item.citation_ids,
            required_asset_tickers=required_assets,
            freshness_label=_comparison_claim_freshness_label(item.dimension),
        )
        for item in key_differences
    ]
    planned.append(
        PlannedComparisonClaim(
            claim_id="claim_comparison_bottom_line",
            claim_text=bottom_line.summary,
            citation_ids=bottom_line.citation_ids,
            required_asset_tickers=required_assets,
        )
    )
    return planned


def _comparison_claim_freshness_label(dimension: str) -> FreshnessState | None:
    if dimension == "Valuation evidence availability":
        return FreshnessState.unavailable
    return None


def _unavailable_comparison(
    left_pack: AssetKnowledgePack,
    right_pack: AssetKnowledgePack,
    message: str | None = None,
) -> CompareResponse:
    if not left_pack.asset.supported:
        state = _state_for_pack(left_pack)
    elif not right_pack.asset.supported:
        state = _state_for_pack(right_pack)
    else:
        state = StateMessage(
            status=AssetStatus.unknown,
            message=message or "No deterministic local comparison knowledge pack is available for these tickers.",
        )

    return CompareResponse(
        left_asset=left_pack.asset,
        right_asset=right_pack.asset,
        state=state,
        comparison_type="unavailable",
        key_differences=[],
        bottom_line_for_beginners=None,
        citations=[],
        source_documents=[],
        evidence_availability=_non_generated_evidence_availability(
            left_pack=left_pack,
            right_pack=right_pack,
            state=_non_generated_availability_state(left_pack, right_pack, message),
            comparison_type="unavailable",
            message=state.message,
        ),
    )


def _available_evidence_availability(
    response: CompareResponse,
    pack: ComparisonKnowledgePack,
    bindings: _ComparisonCitationRegistry,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
) -> ComparisonEvidenceAvailability:
    evidence_items: list[ComparisonEvidenceItem] = []
    dimensions: list[ComparisonEvidenceDimension] = []
    claim_bindings: list[ComparisonEvidenceClaimBinding] = []
    citation_bindings: list[ComparisonEvidenceCitationBinding] = []

    evidence_item_ids_by_dimension: dict[str, list[str]] = {}

    for dimension in REQUIRED_COMPARISON_DIMENSIONS:
        dimension_items: list[ComparisonEvidenceItem] = []
        for side, facts in [
            (ComparisonEvidenceSide.left, left_facts),
            (ComparisonEvidenceSide.right, right_facts),
        ]:
            for field_name in COMPARISON_FACT_FIELDS_BY_DIMENSION[dimension]:
                fact = _require_fact(facts, field_name)
                citation_binding = bindings.for_fact(fact)
                side_role = _side_role_for_asset(
                    fact.fact.asset_ticker,
                    pack.left_asset_pack.asset.ticker,
                    pack.right_asset_pack.asset.ticker,
                )
                item = _evidence_item_for_fact(dimension, side, side_role, fact, citation_binding)
                dimension_items.append(item)
                evidence_items.append(item)

        item_ids = [item.evidence_item_id for item in dimension_items]
        citation_ids = sorted({citation_id for item in dimension_items for citation_id in item.citation_ids})
        source_document_ids = sorted(
            {source_id for item in dimension_items for source_id in [item.source_document_id] if source_id is not None}
        )
        evidence_item_ids_by_dimension[dimension] = item_ids
        dimensions.append(
            ComparisonEvidenceDimension(
                dimension=dimension,
                availability_state=ComparisonEvidenceAvailabilityState.available,
                evidence_state=EvidenceState.supported,
                freshness_state=_combined_freshness([item.freshness_state for item in dimension_items]),
                left_evidence_item_ids=[item.evidence_item_id for item in dimension_items if item.side is ComparisonEvidenceSide.left],
                right_evidence_item_ids=[item.evidence_item_id for item in dimension_items if item.side is ComparisonEvidenceSide.right],
                shared_evidence_item_ids=[],
                citation_ids=citation_ids,
                source_document_ids=source_document_ids,
                generated_claim_ids=[f"claim_comparison_{_claim_slug(dimension)}"],
            )
        )

    for difference in response.key_differences:
        claim_id = f"claim_comparison_{_claim_slug(difference.dimension)}"
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id=claim_id,
                claim_kind="key_difference",
                dimension=difference.dimension,
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=difference.citation_ids,
                source_document_ids=_source_document_ids_for_citations(difference.citation_ids, bindings),
                evidence_item_ids=evidence_item_ids_by_dimension.get(difference.dimension, []),
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )
        citation_bindings.extend(
            _citation_bindings_for_claim(
                claim_id=claim_id,
                dimension=difference.dimension,
                citation_ids=difference.citation_ids,
                bindings=bindings,
                left_ticker=pack.left_asset_pack.asset.ticker,
                right_ticker=pack.right_asset_pack.asset.ticker,
            )
        )

    if response.bottom_line_for_beginners is not None:
        bottom_line_citation_ids = response.bottom_line_for_beginners.citation_ids
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id="claim_comparison_bottom_line",
                claim_kind="beginner_bottom_line",
                dimension="Beginner bottom line",
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=bottom_line_citation_ids,
                source_document_ids=_source_document_ids_for_citations(bottom_line_citation_ids, bindings),
                evidence_item_ids=sorted({item.evidence_item_id for item in evidence_items if item.dimension in {
                    "Expense ratio",
                    "Holdings count",
                    "Educational role",
                }}),
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )
        citation_bindings.extend(
            _citation_bindings_for_claim(
                claim_id="claim_comparison_bottom_line",
                dimension="Beginner bottom line",
                citation_ids=bottom_line_citation_ids,
                bindings=bindings,
                left_ticker=pack.left_asset_pack.asset.ticker,
                right_ticker=pack.right_asset_pack.asset.ticker,
            )
        )

    return ComparisonEvidenceAvailability(
        comparison_id=_comparison_id(pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker),
        comparison_type=response.comparison_type,
        left_asset=response.left_asset,
        right_asset=response.right_asset,
        availability_state=ComparisonEvidenceAvailabilityState.available,
        required_dimensions=REQUIRED_COMPARISON_DIMENSIONS,
        required_evidence_dimensions=dimensions,
        evidence_items=evidence_items,
        claim_bindings=claim_bindings,
        citation_bindings=sorted(citation_bindings, key=lambda item: item.binding_id),
        source_references=[
            _source_reference_from_fixture(source)
            for source in sorted(pack.comparison_sources, key=lambda source: source.source_document_id)
            if source.source_document_id in {source.source_document_id for source in response.source_documents}
        ],
        diagnostics=ComparisonEvidenceDiagnostics(
            generated_comparison_available=True,
            unavailable_reasons=[],
        ),
    )


def _available_stock_etf_evidence_availability(
    response: CompareResponse,
    pack: ComparisonKnowledgePack,
    bindings: _ComparisonCitationRegistry,
    stock_pack: AssetKnowledgePack,
    etf_pack: AssetKnowledgePack,
    stock_facts: dict[str, RetrievedFact],
    etf_facts: dict[str, RetrievedFact],
) -> ComparisonEvidenceAvailability:
    evidence_items: list[ComparisonEvidenceItem] = []
    dimensions: list[ComparisonEvidenceDimension] = []
    claim_bindings: list[ComparisonEvidenceClaimBinding] = []
    citation_bindings: list[ComparisonEvidenceCitationBinding] = []
    evidence_item_ids_by_dimension: dict[str, list[str]] = {}

    dimension_facts = _stock_etf_dimension_facts(stock_facts, etf_facts)
    for dimension in STOCK_ETF_COMPARISON_DIMENSIONS:
        dimension_items: list[ComparisonEvidenceItem] = []
        for fact in dimension_facts[dimension]:
            citation_binding = bindings.for_fact(fact)
            side = _side_for_asset(
                fact.fact.asset_ticker,
                pack.left_asset_pack.asset.ticker,
                pack.right_asset_pack.asset.ticker,
            )
            side_role = _side_role_for_asset(
                fact.fact.asset_ticker,
                pack.left_asset_pack.asset.ticker,
                pack.right_asset_pack.asset.ticker,
            )
            item = _evidence_item_for_fact(dimension, side, side_role, fact, citation_binding)
            dimension_items.append(item)
            evidence_items.append(item)

        item_ids = [item.evidence_item_id for item in dimension_items]
        citation_ids = sorted({citation_id for item in dimension_items for citation_id in item.citation_ids})
        source_document_ids = sorted(
            {source_id for item in dimension_items for source_id in [item.source_document_id] if source_id is not None}
        )
        evidence_item_ids_by_dimension[dimension] = item_ids
        dimensions.append(
            ComparisonEvidenceDimension(
                dimension=dimension,
                availability_state=ComparisonEvidenceAvailabilityState.available,
                evidence_state=EvidenceState.partial if dimension == "Basket membership" else EvidenceState.supported,
                freshness_state=_combined_freshness([item.freshness_state for item in dimension_items]),
                left_evidence_item_ids=[
                    item.evidence_item_id for item in dimension_items if item.side is ComparisonEvidenceSide.left
                ],
                right_evidence_item_ids=[
                    item.evidence_item_id for item in dimension_items if item.side is ComparisonEvidenceSide.right
                ],
                shared_evidence_item_ids=[],
                citation_ids=citation_ids,
                source_document_ids=source_document_ids,
                generated_claim_ids=[f"claim_comparison_{_claim_slug(dimension)}"],
                unavailable_reason=(
                    "AAPL membership in VOO is verified from the local holdings fixture, but exact weight, "
                    "sector exposure, top-10 concentration, and full overlap are unavailable."
                    if dimension == "Basket membership"
                    else None
                ),
            )
        )

    for difference in response.key_differences:
        claim_id = f"claim_comparison_{_claim_slug(difference.dimension)}"
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id=claim_id,
                claim_kind="key_difference",
                dimension=difference.dimension,
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=difference.citation_ids,
                source_document_ids=_source_document_ids_for_citations(difference.citation_ids, bindings),
                evidence_item_ids=evidence_item_ids_by_dimension.get(difference.dimension, []),
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )
        citation_bindings.extend(
            _citation_bindings_for_claim(
                claim_id=claim_id,
                dimension=difference.dimension,
                citation_ids=difference.citation_ids,
                bindings=bindings,
                left_ticker=pack.left_asset_pack.asset.ticker,
                right_ticker=pack.right_asset_pack.asset.ticker,
            )
        )

    if response.bottom_line_for_beginners is not None:
        bottom_line_citation_ids = response.bottom_line_for_beginners.citation_ids
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id="claim_comparison_bottom_line",
                claim_kind="beginner_bottom_line",
                dimension="Beginner bottom line",
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=bottom_line_citation_ids,
                source_document_ids=_source_document_ids_for_citations(bottom_line_citation_ids, bindings),
                evidence_item_ids=sorted({item.evidence_item_id for item in evidence_items}),
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )
        citation_bindings.extend(
            _citation_bindings_for_claim(
                claim_id="claim_comparison_bottom_line",
                dimension="Beginner bottom line",
                citation_ids=bottom_line_citation_ids,
                bindings=bindings,
                left_ticker=pack.left_asset_pack.asset.ticker,
                right_ticker=pack.right_asset_pack.asset.ticker,
            )
        )

    return ComparisonEvidenceAvailability(
        comparison_id=_comparison_id(pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker),
        comparison_type=response.comparison_type,
        left_asset=response.left_asset,
        right_asset=response.right_asset,
        availability_state=ComparisonEvidenceAvailabilityState.available,
        required_dimensions=STOCK_ETF_COMPARISON_DIMENSIONS,
        required_evidence_dimensions=dimensions,
        evidence_items=evidence_items,
        claim_bindings=claim_bindings,
        citation_bindings=sorted(citation_bindings, key=lambda item: item.binding_id),
        source_references=[
            _source_reference_from_fixture(source)
            for source in sorted(pack.comparison_sources, key=lambda source: source.source_document_id)
            if source.source_document_id in {source.source_document_id for source in response.source_documents}
        ],
        diagnostics=ComparisonEvidenceDiagnostics(
            generated_comparison_available=True,
            unavailable_reasons=[],
        ),
    )


def _available_stock_stock_evidence_availability(
    response: CompareResponse,
    pack: ComparisonKnowledgePack,
    bindings: _ComparisonCitationRegistry,
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
) -> ComparisonEvidenceAvailability:
    evidence_items: list[ComparisonEvidenceItem] = []
    dimensions: list[ComparisonEvidenceDimension] = []
    claim_bindings: list[ComparisonEvidenceClaimBinding] = []
    citation_bindings: list[ComparisonEvidenceCitationBinding] = []
    evidence_item_ids_by_dimension: dict[str, list[str]] = {}

    dimension_facts = _stock_stock_dimension_facts(left_facts, right_facts)
    for dimension in STOCK_STOCK_COMPARISON_DIMENSIONS:
        dimension_items: list[ComparisonEvidenceItem] = []
        for fact in dimension_facts[dimension]:
            citation_binding = bindings.for_fact(fact)
            side = _side_for_asset(
                fact.fact.asset_ticker,
                pack.left_asset_pack.asset.ticker,
                pack.right_asset_pack.asset.ticker,
            )
            side_role = _side_role_for_asset(
                fact.fact.asset_ticker,
                pack.left_asset_pack.asset.ticker,
                pack.right_asset_pack.asset.ticker,
            )
            item = _evidence_item_for_fact(dimension, side, side_role, fact, citation_binding)
            dimension_items.append(item)
            evidence_items.append(item)

        item_ids = [item.evidence_item_id for item in dimension_items]
        citation_ids = sorted({citation_id for item in dimension_items for citation_id in item.citation_ids})
        source_document_ids = sorted(
            {source_id for item in dimension_items for source_id in [item.source_document_id] if source_id is not None}
        )
        evidence_item_ids_by_dimension[dimension] = item_ids
        valuation_dimension = dimension == "Valuation evidence availability"
        dimensions.append(
            ComparisonEvidenceDimension(
                dimension=dimension,
                availability_state=ComparisonEvidenceAvailabilityState.available,
                evidence_state=EvidenceState.partial if valuation_dimension else EvidenceState.supported,
                freshness_state=_combined_freshness([item.freshness_state for item in dimension_items]),
                left_evidence_item_ids=[
                    item.evidence_item_id for item in dimension_items if item.side is ComparisonEvidenceSide.left
                ],
                right_evidence_item_ids=[
                    item.evidence_item_id for item in dimension_items if item.side is ComparisonEvidenceSide.right
                ],
                shared_evidence_item_ids=[],
                citation_ids=citation_ids,
                source_document_ids=source_document_ids,
                generated_claim_ids=[f"claim_comparison_{_claim_slug(dimension)}"],
                unavailable_reason=(
                    "Current valuation metrics are unavailable in the deterministic local fixtures for both stocks."
                    if valuation_dimension
                    else None
                ),
            )
        )

    for difference in response.key_differences:
        claim_id = f"claim_comparison_{_claim_slug(difference.dimension)}"
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id=claim_id,
                claim_kind="key_difference",
                dimension=difference.dimension,
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=difference.citation_ids,
                source_document_ids=_source_document_ids_for_citations(difference.citation_ids, bindings),
                evidence_item_ids=evidence_item_ids_by_dimension.get(difference.dimension, []),
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )
        citation_bindings.extend(
            _citation_bindings_for_claim(
                claim_id=claim_id,
                dimension=difference.dimension,
                citation_ids=difference.citation_ids,
                bindings=bindings,
                left_ticker=pack.left_asset_pack.asset.ticker,
                right_ticker=pack.right_asset_pack.asset.ticker,
            )
        )

    if response.bottom_line_for_beginners is not None:
        bottom_line_citation_ids = response.bottom_line_for_beginners.citation_ids
        claim_bindings.append(
            ComparisonEvidenceClaimBinding(
                claim_id="claim_comparison_bottom_line",
                claim_kind="beginner_bottom_line",
                dimension="Beginner bottom line",
                side_role=ComparisonEvidenceSideRole.shared_comparison_support,
                citation_ids=bottom_line_citation_ids,
                source_document_ids=_source_document_ids_for_citations(bottom_line_citation_ids, bindings),
                evidence_item_ids=sorted({item.evidence_item_id for item in evidence_items if item.dimension != "Valuation evidence availability"}),
                availability_state=ComparisonEvidenceAvailabilityState.available,
            )
        )
        citation_bindings.extend(
            _citation_bindings_for_claim(
                claim_id="claim_comparison_bottom_line",
                dimension="Beginner bottom line",
                citation_ids=bottom_line_citation_ids,
                bindings=bindings,
                left_ticker=pack.left_asset_pack.asset.ticker,
                right_ticker=pack.right_asset_pack.asset.ticker,
            )
        )

    return ComparisonEvidenceAvailability(
        comparison_id=_comparison_id(pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker),
        comparison_type=response.comparison_type,
        left_asset=response.left_asset,
        right_asset=response.right_asset,
        availability_state=ComparisonEvidenceAvailabilityState.available,
        required_dimensions=STOCK_STOCK_COMPARISON_DIMENSIONS,
        required_evidence_dimensions=dimensions,
        evidence_items=evidence_items,
        claim_bindings=claim_bindings,
        citation_bindings=sorted(citation_bindings, key=lambda item: item.binding_id),
        source_references=[
            _source_reference_from_fixture(source)
            for source in sorted(pack.comparison_sources, key=lambda source: source.source_document_id)
            if source.source_document_id in {source.source_document_id for source in response.source_documents}
        ],
        diagnostics=ComparisonEvidenceDiagnostics(
            generated_comparison_available=True,
            unavailable_reasons=[],
        ),
    )


def _stock_etf_dimension_facts(
    stock_facts: dict[str, RetrievedFact],
    etf_facts: dict[str, RetrievedFact],
) -> dict[str, list[RetrievedFact]]:
    stock_identity = _require_fact(stock_facts, "canonical_asset_identity")
    stock_business = _require_fact(stock_facts, "primary_business")
    etf_benchmark = _require_fact(etf_facts, "benchmark")
    etf_holdings = _require_fact(etf_facts, "holdings_exposure_detail")
    etf_holdings_count = _require_fact(etf_facts, "holdings_count")
    etf_expense = _require_fact(etf_facts, "expense_ratio")
    etf_role = _require_fact(etf_facts, "beginner_role")
    return {
        "Structure": [stock_business, etf_benchmark],
        "Basket membership": [stock_identity, etf_holdings],
        "Breadth": [stock_identity, etf_holdings_count],
        "Cost model": [stock_identity, etf_expense],
        "Educational role": [stock_business, etf_role, etf_holdings],
    }


def _stock_stock_dimension_facts(
    left_facts: dict[str, RetrievedFact],
    right_facts: dict[str, RetrievedFact],
) -> dict[str, list[RetrievedFact]]:
    return {
        "Business model": [
            _require_fact(left_facts, "primary_business"),
            _require_fact(right_facts, "primary_business"),
        ],
        "Revenue trend": [
            _require_fact(left_facts, "financial_quality_revenue_trend"),
            _require_fact(right_facts, "financial_quality_revenue_trend"),
        ],
        "Business quality evidence": [
            _require_fact(left_facts, "business_quality_strength"),
            _require_fact(right_facts, "business_quality_strength"),
        ],
        "Risk context": [
            _require_fact(left_facts, "company_specific_risk"),
            _require_fact(right_facts, "company_specific_risk"),
        ],
        "Valuation evidence availability": [
            _require_fact(left_facts, "valuation_data_limitation"),
            _require_fact(right_facts, "valuation_data_limitation"),
        ],
    }


def _non_generated_evidence_availability(
    left_pack: AssetKnowledgePack,
    right_pack: AssetKnowledgePack,
    state: ComparisonEvidenceAvailabilityState,
    comparison_type: str,
    message: str,
) -> ComparisonEvidenceAvailability:
    dimensions = [
        ComparisonEvidenceDimension(
            dimension=dimension,
            availability_state=state,
            evidence_state=_evidence_state_for_availability(state),
            freshness_state=FreshnessState.unavailable if state is not ComparisonEvidenceAvailabilityState.stale else FreshnessState.stale,
            unavailable_reason=message,
        )
        for dimension in REQUIRED_COMPARISON_DIMENSIONS
    ]
    return ComparisonEvidenceAvailability(
        comparison_id=_comparison_id(left_pack.asset.ticker, right_pack.asset.ticker),
        comparison_type=comparison_type,
        left_asset=_selected_asset_for_availability(left_pack.asset),
        right_asset=_selected_asset_for_availability(right_pack.asset),
        availability_state=state,
        required_dimensions=REQUIRED_COMPARISON_DIMENSIONS,
        required_evidence_dimensions=dimensions,
        evidence_items=[],
        claim_bindings=[],
        citation_bindings=[],
        source_references=[],
        diagnostics=ComparisonEvidenceDiagnostics(
            generated_comparison_available=False,
            unavailable_reasons=[message],
            empty_state_reason=message,
        ),
    )


def _non_generated_availability_state(
    left_pack: AssetKnowledgePack,
    right_pack: AssetKnowledgePack,
    message: str | None,
) -> ComparisonEvidenceAvailabilityState:
    for pack in [left_pack, right_pack]:
        ticker = pack.asset.ticker
        if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
            return ComparisonEvidenceAvailabilityState.out_of_scope
        if ticker in ELIGIBLE_NOT_CACHED_ASSETS:
            return ComparisonEvidenceAvailabilityState.eligible_not_cached
        if pack.asset.status is AssetStatus.unsupported:
            return ComparisonEvidenceAvailabilityState.unsupported
        if pack.asset.status is AssetStatus.unknown:
            return ComparisonEvidenceAvailabilityState.unknown

    if message:
        return ComparisonEvidenceAvailabilityState.no_local_pack
    return ComparisonEvidenceAvailabilityState.unavailable


def _evidence_state_for_availability(state: ComparisonEvidenceAvailabilityState) -> EvidenceState:
    if state is ComparisonEvidenceAvailabilityState.unsupported:
        return EvidenceState.unsupported
    if state is ComparisonEvidenceAvailabilityState.stale:
        return EvidenceState.stale
    if state in {ComparisonEvidenceAvailabilityState.partial, ComparisonEvidenceAvailabilityState.no_local_pack}:
        return EvidenceState.mixed
    if state is ComparisonEvidenceAvailabilityState.insufficient_evidence:
        return EvidenceState.insufficient_evidence
    if state is ComparisonEvidenceAvailabilityState.unknown:
        return EvidenceState.unknown
    return EvidenceState.unavailable


def _selected_asset_for_availability(asset: AssetIdentity) -> AssetIdentity:
    ticker = asset.ticker
    if ticker in ELIGIBLE_NOT_CACHED_ASSETS:
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
    if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
        metadata = OUT_OF_SCOPE_COMMON_STOCKS[ticker]
        return AssetIdentity(
            ticker=ticker,
            name=str(metadata["name"]),
            asset_type=AssetType(str(metadata["asset_type"])),
            exchange=str(metadata["exchange"]) if metadata.get("exchange") else None,
            issuer=str(metadata["issuer"]) if metadata.get("issuer") else None,
            status=AssetStatus.unknown,
            supported=False,
        )
    return asset


def _evidence_item_for_fact(
    dimension: str,
    side: ComparisonEvidenceSide,
    side_role: ComparisonEvidenceSideRole,
    fact: RetrievedFact,
    citation_binding: CitationBinding,
) -> ComparisonEvidenceItem:
    decision = resolve_source_policy(
        url=fact.source_document.url,
        source_identifier=fact.source_document.url if fact.source_document.url.startswith("local://") else None,
    )
    return ComparisonEvidenceItem(
        evidence_item_id=f"evidence_{_claim_slug(dimension)}_{side.value}_{fact.fact.fact_id}",
        dimension=dimension,
        side=side,
        side_role=side_role,
        asset_ticker=fact.fact.asset_ticker,
        field_name=fact.fact.field_name,
        fact_id=fact.fact.fact_id,
        source_chunk_id=fact.source_chunk.chunk_id,
        source_document_id=fact.source_document.source_document_id,
        citation_ids=[citation_binding.citation.citation_id],
        evidence_state=EvidenceState(fact.fact.evidence_state),
        freshness_state=fact.fact.freshness_state,
        as_of_date=fact.fact.as_of_date,
        retrieved_at=fact.source_document.retrieved_at,
        is_official=fact.source_document.is_official,
        source_quality=fact.source_document.source_quality,
        allowlist_status=fact.source_document.allowlist_status,
        source_use_policy=fact.source_document.source_use_policy,
        permitted_operations=decision.permitted_operations,
    )


def _citation_bindings_for_claim(
    claim_id: str,
    dimension: str,
    citation_ids: list[str],
    bindings: _ComparisonCitationRegistry,
    left_ticker: str,
    right_ticker: str,
) -> list[ComparisonEvidenceCitationBinding]:
    availability_bindings: list[ComparisonEvidenceCitationBinding] = []
    for citation_id in citation_ids:
        binding = bindings.binding_for_citation_id(citation_id)
        if binding is None:
            continue
        side_role = _side_role_for_asset(binding.evidence.asset_ticker, left_ticker, right_ticker)
        source_document = binding.source_document
        availability_bindings.append(
            ComparisonEvidenceCitationBinding(
                binding_id=f"binding_{claim_id}_{citation_id}",
                claim_id=claim_id,
                dimension=dimension,
                citation_id=citation_id,
                source_document_id=source_document.source_document_id,
                asset_ticker=binding.evidence.asset_ticker,
                side_role=side_role,
                freshness_state=source_document.freshness_state,
                source_quality=source_document.source_quality,
                allowlist_status=source_document.allowlist_status,
                source_use_policy=source_document.source_use_policy,
                permitted_operations=source_document.permitted_operations,
                supports_generated_claim=(
                    binding.evidence.supports_claim
                    and source_document.permitted_operations.can_support_generated_output
                    and source_document.permitted_operations.can_support_citations
                    and source_document.source_use_policy
                    not in {SourceUsePolicy.rejected, SourceUsePolicy.metadata_only, SourceUsePolicy.link_only}
                    and source_document.allowlist_status is SourceAllowlistStatus.allowed
                ),
            )
        )
    return availability_bindings


def _source_document_ids_for_citations(citation_ids: Iterable[str], bindings: _ComparisonCitationRegistry) -> list[str]:
    source_document_ids = []
    for citation_id in citation_ids:
        binding = bindings.binding_for_citation_id(citation_id)
        if binding is not None:
            source_document_ids.append(binding.source_document.source_document_id)
    return sorted(set(source_document_ids))


def _source_reference_from_fixture(source: SourceDocumentFixture) -> ComparisonEvidenceSourceReference:
    decision = resolve_source_policy(
        url=source.url,
        source_identifier=source.url if source.url.startswith("local://") else None,
    )
    return ComparisonEvidenceSourceReference(
        source_document_id=source.source_document_id,
        asset_ticker=source.asset_ticker,
        source_type=source.source_type,
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
        permitted_operations=decision.permitted_operations,
        **source_handoff_fields_from_policy(
            decision,
            source_identity=source.url or source.source_document_id,
            approval_rationale="Deterministic comparison fixture source passed local source-use policy review.",
        ),
    )


def _side_role_for_asset(
    asset_ticker: str,
    left_ticker: str,
    right_ticker: str,
) -> ComparisonEvidenceSideRole:
    if asset_ticker == left_ticker:
        return ComparisonEvidenceSideRole.left_side_support
    if asset_ticker == right_ticker:
        return ComparisonEvidenceSideRole.right_side_support
    return ComparisonEvidenceSideRole.shared_comparison_support


def _side_for_asset(
    asset_ticker: str,
    left_ticker: str,
    right_ticker: str,
) -> ComparisonEvidenceSide:
    if asset_ticker == left_ticker:
        return ComparisonEvidenceSide.left
    if asset_ticker == right_ticker:
        return ComparisonEvidenceSide.right
    return ComparisonEvidenceSide.shared


def _is_stock_vs_etf(pack: ComparisonKnowledgePack) -> bool:
    return {pack.left_asset_pack.asset.asset_type, pack.right_asset_pack.asset.asset_type} == {
        AssetType.stock,
        AssetType.etf,
    }


def _is_stock_vs_stock(pack: ComparisonKnowledgePack) -> bool:
    return (
        pack.left_asset_pack.asset.asset_type is AssetType.stock
        and pack.right_asset_pack.asset.asset_type is AssetType.stock
    )


def _stock_etf_asset_packs(pack: ComparisonKnowledgePack) -> tuple[AssetKnowledgePack, AssetKnowledgePack]:
    if pack.left_asset_pack.asset.asset_type is AssetType.stock and pack.right_asset_pack.asset.asset_type is AssetType.etf:
        return pack.left_asset_pack, pack.right_asset_pack
    if pack.left_asset_pack.asset.asset_type is AssetType.etf and pack.right_asset_pack.asset.asset_type is AssetType.stock:
        return pack.right_asset_pack, pack.left_asset_pack
    raise ComparisonGenerationError("Expected one stock asset and one ETF asset for stock-vs-ETF generation.")


def _combined_freshness(states: list[FreshnessState]) -> FreshnessState:
    if not states:
        return FreshnessState.unavailable
    for state in [FreshnessState.unavailable, FreshnessState.unknown, FreshnessState.stale]:
        if state in states:
            return state
    return FreshnessState.fresh


def _comparison_id(left_ticker: str, right_ticker: str) -> str:
    return f"comparison-{left_ticker.lower()}-to-{right_ticker.lower()}-local-fixture-v1"


def _state_for_pack(pack: AssetKnowledgePack) -> StateMessage:
    if pack.asset.status is AssetStatus.supported:
        return StateMessage(status=AssetStatus.supported, message="Asset is supported by deterministic local retrieval fixtures.")
    message = pack.evidence_gaps[0].message if pack.evidence_gaps else "No local retrieval fixture is available for this ticker."
    return StateMessage(status=pack.asset.status, message=message)


def _supported_facts_by_field(pack: AssetKnowledgePack) -> dict[str, RetrievedFact]:
    return {item.fact.field_name: item for item in pack.normalized_facts if item.fact.evidence_state == "supported"}


def _require_fact(facts_by_field: dict[str, RetrievedFact], field_name: str) -> RetrievedFact:
    fact = facts_by_field.get(field_name)
    if fact is None:
        raise ComparisonGenerationError(f"Required comparison fact is missing: {field_name}.")
    return fact


def _require_difference(pack: ComparisonKnowledgePack, dimension: str) -> None:
    if not any(difference.dimension == dimension for difference in pack.computed_differences):
        raise ComparisonGenerationError(
            f"Comparison pack {pack.comparison_pack_id} is missing required {dimension} difference."
        )


def _broader_and_narrower(left: RetrievedFact, right: RetrievedFact) -> tuple[RetrievedFact, RetrievedFact]:
    if _numeric_value(left.fact.value) >= _numeric_value(right.fact.value):
        return left, right
    return right, left


def _numeric_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError as exc:
        raise ComparisonGenerationError(f"Expected numeric holdings count, got {value!r}.") from exc


def _format_metric(value: Any, unit: str | None) -> str:
    if unit == "%":
        return f"{value}{unit}"
    if unit:
        return f"{value} {unit}"
    return str(value)


def _role_phrase(value: Any) -> str:
    text = str(value)
    return f"{text[:1].lower()}{text[1:]}" if text else text


def _source_document_from_fixture(source: SourceDocumentFixture, supporting_passage: str) -> SourceDocument:
    decision = resolve_source_policy(
        url=source.url,
        source_identifier=source.url if source.url.startswith("local://") else None,
    )
    return SourceDocument(
        source_document_id=source.source_document_id,
        source_type=source.source_type,
        title=source.title,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=source.retrieved_at,
        freshness_state=source.freshness_state,
        is_official=source.is_official,
        supporting_passage=supporting_passage,
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        permitted_operations=decision.permitted_operations,
    )


def _validate_comparison_source_documents(
    comparison: CompareResponse,
    pack: ComparisonKnowledgePack,
) -> CitationValidationReport:
    used_citation_ids = {
        *{citation_id for item in comparison.key_differences for citation_id in item.citation_ids},
        *(
            set(comparison.bottom_line_for_beginners.citation_ids)
            if comparison.bottom_line_for_beginners is not None
            else set()
        ),
    }
    if not used_citation_ids and not comparison.citations and not comparison.source_documents:
        return _valid_comparison_validation_report()

    issues: list[CitationValidationIssue] = []
    citations_by_id = {citation.citation_id: citation for citation in comparison.citations}
    extra_citation_ids = set(citations_by_id) - used_citation_ids
    missing_citation_ids = used_citation_ids - set(citations_by_id)

    for citation_id in sorted(missing_citation_ids):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.citation_not_found,
                claim_id="comparison_source_metadata",
                citation_id=citation_id,
                message="Comparison response is missing citation metadata for a used citation.",
            )
        )
    for citation_id in sorted(extra_citation_ids):
        citation = citations_by_id[citation_id]
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.citation_not_found,
                claim_id="comparison_source_metadata",
                citation_id=citation_id,
                source_document_id=citation.source_document_id,
                message="Comparison response includes citation metadata that is not used by generated claims.",
            )
        )

    source_documents_by_id = {source.source_document_id: source for source in comparison.source_documents}
    expected_sources_by_id = {source.source_document_id: source for source in pack.comparison_sources}
    source_chunks_by_id = {
        item.chunk.chunk_id: item for item in [*pack.left_asset_pack.source_chunks, *pack.right_asset_pack.source_chunks]
    }
    facts_by_id = {
        item.fact.fact_id: item for item in [*pack.left_asset_pack.normalized_facts, *pack.right_asset_pack.normalized_facts]
    }

    needed_source_ids = {
        citation.source_document_id for citation_id, citation in citations_by_id.items() if citation_id in used_citation_ids
    }
    missing_source_ids = needed_source_ids - set(source_documents_by_id)
    extra_source_ids = set(source_documents_by_id) - needed_source_ids

    for source_document_id in sorted(missing_source_ids):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.citation_not_found,
                claim_id="comparison_source_metadata",
                source_document_id=source_document_id,
                message="Comparison citation is missing source-document metadata.",
            )
        )
    for source_document_id in sorted(extra_source_ids):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.citation_not_found,
                claim_id="comparison_source_metadata",
                source_document_id=source_document_id,
                message="Comparison source-document metadata has no matching generated citation.",
            )
        )

    expected_passages_by_source_id: dict[str, set[str]] = {}
    for citation_id in used_citation_ids:
        evidence_id = citation_id[2:] if citation_id.startswith("c_") else citation_id
        fact = facts_by_id.get(evidence_id)
        if fact is not None:
            expected_passages_by_source_id.setdefault(fact.source_document.source_document_id, set()).add(
                fact.source_chunk.text
            )
            continue
        chunk = source_chunks_by_id.get(evidence_id)
        if chunk is not None:
            expected_passages_by_source_id.setdefault(chunk.source_document.source_document_id, set()).add(chunk.chunk.text)

    for source_document_id in sorted(needed_source_ids & set(source_documents_by_id)):
        source_document = source_documents_by_id[source_document_id]
        expected_source = expected_sources_by_id.get(source_document_id)
        if expected_source is None:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.wrong_asset,
                    claim_id="comparison_source_metadata",
                    source_document_id=source_document_id,
                    message="Comparison source-document metadata belongs outside the selected comparison pack.",
                )
            )
            continue

        issues.extend(_comparison_source_metadata_issues(source_document, expected_source, expected_passages_by_source_id))

    if not issues:
        return _valid_comparison_validation_report()

    return CitationValidationReport(
        status=issues[0].status,
        results=[
            CitationValidationResult(
                claim_id="comparison_source_metadata",
                status=issues[0].status,
                issues=issues,
            )
        ],
    )


def _comparison_source_metadata_issues(
    source_document: SourceDocument,
    expected_source: SourceDocumentFixture,
    expected_passages_by_source_id: dict[str, set[str]],
) -> list[CitationValidationIssue]:
    issues: list[CitationValidationIssue] = []
    source_document_id = source_document.source_document_id

    if source_document.source_type != expected_source.source_type:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.unsupported_source,
                claim_id="comparison_source_metadata",
                source_document_id=source_document_id,
                message="Comparison source-document metadata changed the source type from the selected comparison pack.",
            )
        )

    if (
        source_document.title != expected_source.title
        or source_document.publisher != expected_source.publisher
        or source_document.url != expected_source.url
        or source_document.published_at != expected_source.published_at
        or source_document.as_of_date != expected_source.as_of_date
        or source_document.retrieved_at != expected_source.retrieved_at
        or source_document.is_official != expected_source.is_official
    ):
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.insufficient_evidence,
                claim_id="comparison_source_metadata",
                source_document_id=source_document_id,
                message="Comparison source-document metadata does not match the selected comparison pack.",
            )
        )

    if source_document.freshness_state != expected_source.freshness_state:
        status = (
            CitationValidationStatus.stale_source
            if source_document.freshness_state is FreshnessState.stale
            else CitationValidationStatus.insufficient_evidence
        )
        issues.append(
            CitationValidationIssue(
                status=status,
                claim_id="comparison_source_metadata",
                source_document_id=source_document_id,
                message="Comparison source-document freshness does not match the selected comparison pack.",
            )
        )

    expected_passages = expected_passages_by_source_id.get(source_document_id, set())
    if not source_document.supporting_passage.strip() or source_document.supporting_passage not in expected_passages:
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.insufficient_evidence,
                claim_id="comparison_source_metadata",
                source_document_id=source_document_id,
                message="Comparison source-document metadata is missing a supporting passage from the selected comparison pack.",
            )
        )

    return issues


def _valid_comparison_validation_report() -> CitationValidationReport:
    return CitationValidationReport(
        status=CitationValidationStatus.valid,
        results=[CitationValidationResult(claim_id="comparison_source_metadata", status=CitationValidationStatus.valid)],
    )


def _claim_slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _assert_safe_copy(response: CompareResponse) -> None:
    hits = find_forbidden_output_phrases(_flatten_text(response.model_dump(mode="json")))
    if hits:
        raise ComparisonGenerationError(f"Generated comparison leaked forbidden output phrases: {hits}")


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return ""
