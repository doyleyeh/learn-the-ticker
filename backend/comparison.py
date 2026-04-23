from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

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
    CompareResponse,
    EvidenceState,
    FreshnessState,
    KeyDifference,
    SourceAllowlistStatus,
    SourceDocument,
    SourceUsePolicy,
    StateMessage,
)
from backend.data import ELIGIBLE_NOT_CACHED_ASSETS, OUT_OF_SCOPE_COMMON_STOCKS
from backend.retrieval import (
    AssetKnowledgePack,
    ComparisonKnowledgePack,
    RetrievedFact,
    RetrievedSourceChunk,
    RetrievalFixtureError,
    SourceDocumentFixture,
    build_asset_knowledge_pack,
    build_comparison_knowledge_pack,
)
from backend.safety import find_forbidden_output_phrases
from backend.source_policy import resolve_source_policy


class ComparisonGenerationError(ValueError):
    """Raised when deterministic comparison generation violates project contracts."""


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


def generate_comparison(left_ticker: str, right_ticker: str) -> CompareResponse:
    """Build a CompareResponse-compatible payload from local comparison fixtures."""

    left_pack = build_asset_knowledge_pack(left_ticker)
    right_pack = build_asset_knowledge_pack(right_ticker)

    if not left_pack.asset.supported or not right_pack.asset.supported:
        return _unavailable_comparison(left_pack, right_pack)

    try:
        pack = build_comparison_knowledge_pack(left_ticker, right_ticker)
    except RetrievalFixtureError:
        return _unavailable_comparison(
            left_pack,
            right_pack,
            "No deterministic local comparison knowledge pack is available for these tickers.",
        )

    return generate_comparison_from_pack(pack)


def generate_comparison_from_pack(pack: ComparisonKnowledgePack) -> CompareResponse:
    if not pack.left_asset_pack.asset.supported or not pack.right_asset_pack.asset.supported:
        return _unavailable_comparison(pack.left_asset_pack, pack.right_asset_pack)

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
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=retrieved_fact.fact.asset_ticker,
            source_document_id=retrieved_fact.source_document.source_document_id,
            source_type=retrieved_fact.source_document.source_type,
            evidence_kind=EvidenceKind.normalized_fact,
            freshness_state=retrieved_fact.fact.freshness_state,
            supported_claim_types=retrieved_fact.source_chunk.supported_claim_types,
            supporting_text=retrieved_fact.source_chunk.text,
            supports_claim=retrieved_fact.fact.evidence_state == "supported",
            is_recent=False,
            allowlist_status=retrieved_fact.source_document.allowlist_status,
            source_use_policy=retrieved_fact.source_document.source_use_policy,
        )
        return self._add_binding(citation_id, retrieved_fact.source_document, evidence)

    def for_chunk(self, retrieved_chunk: RetrievedSourceChunk) -> CitationBinding:
        citation_id = f"c_{retrieved_chunk.chunk.chunk_id}"
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=retrieved_chunk.chunk.asset_ticker,
            source_document_id=retrieved_chunk.source_document.source_document_id,
            source_type=retrieved_chunk.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=retrieved_chunk.source_document.freshness_state,
            supported_claim_types=retrieved_chunk.chunk.supported_claim_types,
            supporting_text=retrieved_chunk.chunk.text,
            supports_claim=True,
            is_recent=False,
            allowlist_status=retrieved_chunk.source_document.allowlist_status,
            source_use_policy=retrieved_chunk.source_document.source_use_policy,
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
