from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from backend.citations import (
    CitationEvidence,
    CitationValidationClaim,
    CitationValidationContext,
    CitationValidationReport,
    EvidenceKind,
    validate_claims,
)
from backend.models import (
    AssetStatus,
    BeginnerBottomLine,
    Citation,
    CompareResponse,
    FreshnessState,
    KeyDifference,
    StateMessage,
)
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


class ComparisonGenerationError(ValueError):
    """Raised when deterministic comparison generation violates project contracts."""


@dataclass(frozen=True)
class CitationBinding:
    citation: Citation
    evidence: CitationEvidence


@dataclass(frozen=True)
class PlannedComparisonClaim:
    claim_id: str
    claim_text: str
    citation_ids: list[str]
    claim_type: str = "comparison"
    required_asset_tickers: list[str] | None = None
    freshness_label: FreshnessState | None = None


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

    return validate_claims(
        claims,
        evidence,
        CitationValidationContext(
            allowed_asset_tickers=[pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker],
            comparison_pack_id=pack.comparison_pack_id,
        ),
    )


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
        )
        return self._add_binding(citation_id, retrieved_chunk.source_document, evidence)

    def citations(self) -> list[Citation]:
        return [binding.citation for binding in self._sorted_bindings()]

    def evidence(self) -> list[CitationEvidence]:
        return [binding.evidence for binding in self._sorted_bindings()]

    def evidence_for_citation_ids(self, citation_ids: Iterable[str]) -> list[CitationEvidence]:
        evidence: list[CitationEvidence] = []
        for citation_id in sorted(set(citation_ids)):
            binding = self._binding_for_citation_id(citation_id)
            if binding is not None:
                evidence.append(binding.evidence)
        return evidence

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
    )


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
