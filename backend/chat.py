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
    AssetType,
    ChatCitation,
    ChatResponse,
    ChatSourceDocument,
    FreshnessState,
    SafetyClassification,
)
from backend.retrieval import (
    AssetKnowledgePack,
    RetrievedFact,
    RetrievedRecentDevelopment,
    RetrievedSourceChunk,
    build_asset_knowledge_pack,
)
from backend.safety import classify_question, educational_redirect, find_forbidden_output_phrases


class ChatGenerationError(ValueError):
    """Raised when deterministic chat generation violates project contracts."""


@dataclass(frozen=True)
class ChatCitationBinding:
    citation: ChatCitation
    source_document: ChatSourceDocument
    evidence: CitationEvidence


@dataclass(frozen=True)
class PlannedChatClaim:
    claim_id: str
    claim_text: str
    citation_ids: list[str]
    claim_type: str = "factual"
    freshness_label: FreshnessState | None = None


@dataclass(frozen=True)
class _ChatPlan:
    direct_answer: str
    why_it_matters: str
    planned_claims: list[PlannedChatClaim]
    uncertainty: list[str]


def generate_asset_chat(ticker: str, question: str) -> ChatResponse:
    """Build a ChatResponse-compatible payload from a selected asset knowledge pack."""

    return generate_chat_from_pack(build_asset_knowledge_pack(ticker), question)


def generate_chat_from_pack(pack: AssetKnowledgePack, question: str) -> ChatResponse:
    safety_classification = classify_question(question, supported=pack.asset.supported)

    if safety_classification is SafetyClassification.unsupported_asset_redirect:
        return _unsupported_chat(pack, safety_classification)

    if safety_classification is SafetyClassification.personalized_advice_redirect:
        return _advice_redirect_chat(pack, safety_classification)

    plan, bindings = _plan_supported_chat(pack, question)
    evidence = bindings.evidence()
    report = validate_generated_chat_claims(pack, plan.planned_claims, evidence)
    if not report.valid:
        first_issue = report.issues[0]
        raise ChatGenerationError(
            f"Generated chat citation validation failed for {pack.asset.ticker}: "
            f"{first_issue.status.value} on {first_issue.claim_id}"
        )

    response = ChatResponse(
        asset=pack.asset,
        direct_answer=plan.direct_answer,
        why_it_matters=plan.why_it_matters,
        citations=bindings.citations_for_claims(plan.planned_claims),
        source_documents=bindings.source_documents_for_claims(plan.planned_claims),
        uncertainty=plan.uncertainty,
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def validate_chat_response(response: ChatResponse, pack: AssetKnowledgePack) -> CitationValidationReport:
    evidence = _evidence_from_chat_response(pack, response)
    claims = _claims_from_chat_response(response, pack)
    report = validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))
    if not report.valid:
        return report
    return _validate_chat_source_documents(response, pack)


def validate_generated_chat_claims(
    pack: AssetKnowledgePack,
    planned_claims: Iterable[PlannedChatClaim],
    evidence: list[CitationEvidence],
) -> CitationValidationReport:
    claims = [
        CitationValidationClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            citation_ids=claim.citation_ids,
            freshness_label=claim.freshness_label,
        )
        for claim in planned_claims
    ]
    return validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))


class _ChatCitationRegistry:
    def __init__(self, pack: AssetKnowledgePack) -> None:
        self._pack = pack
        self._bindings_by_citation_id: dict[str, ChatCitationBinding] = {}

    def for_fact(self, retrieved_fact: RetrievedFact, claim_text: str) -> str:
        return self.for_chunk(
            RetrievedSourceChunk(chunk=retrieved_fact.source_chunk, source_document=retrieved_fact.source_document),
            claim_text,
            supports_claim=retrieved_fact.fact.evidence_state == "supported",
            freshness_state=retrieved_fact.fact.freshness_state,
        )

    def for_chunk(
        self,
        retrieved_chunk: RetrievedSourceChunk,
        claim_text: str,
        *,
        supports_claim: bool = True,
        freshness_state: FreshnessState | None = None,
        is_recent: bool | None = None,
    ) -> str:
        citation_id = _citation_id(retrieved_chunk.source_document.source_document_id, retrieved_chunk.chunk.chunk_id)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=self._pack.asset.ticker,
            source_document_id=retrieved_chunk.source_document.source_document_id,
            source_type=retrieved_chunk.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=freshness_state or retrieved_chunk.source_document.freshness_state,
            supported_claim_types=retrieved_chunk.chunk.supported_claim_types,
            supporting_text=retrieved_chunk.chunk.text,
            supports_claim=supports_claim,
            is_recent=is_recent
            if is_recent is not None
            else retrieved_chunk.source_document.source_type == "recent_development",
        )
        return self._add_binding(citation_id, claim_text, retrieved_chunk, evidence)

    def for_recent_development(self, item: RetrievedRecentDevelopment, claim_text: str) -> str:
        return self.for_chunk(
            RetrievedSourceChunk(chunk=item.source_chunk, source_document=item.source_document),
            claim_text,
            supports_claim=item.recent_development.evidence_state == "no_major_recent_development",
            freshness_state=item.recent_development.freshness_state,
            is_recent=True,
        )

    def evidence(self) -> list[CitationEvidence]:
        return [binding.evidence for binding in self._sorted_bindings()]

    def citations_for_claims(self, planned_claims: Iterable[PlannedChatClaim]) -> list[ChatCitation]:
        citations: list[ChatCitation] = []
        for claim in planned_claims:
            for citation_id in claim.citation_ids:
                binding = self._bindings_by_citation_id[citation_id]
                citations.append(
                    ChatCitation(
                        citation_id=citation_id,
                        claim=claim.claim_text,
                        source_document_id=binding.citation.source_document_id,
                        chunk_id=binding.citation.chunk_id,
                    )
                )
        return citations

    def source_documents_for_claims(self, planned_claims: Iterable[PlannedChatClaim]) -> list[ChatSourceDocument]:
        source_documents: list[ChatSourceDocument] = []
        seen_citation_ids: set[str] = set()
        for claim in planned_claims:
            for citation_id in claim.citation_ids:
                if citation_id in seen_citation_ids:
                    continue
                source_documents.append(self._bindings_by_citation_id[citation_id].source_document)
                seen_citation_ids.add(citation_id)
        return source_documents

    def _add_binding(
        self,
        citation_id: str,
        claim_text: str,
        retrieved_chunk: RetrievedSourceChunk,
        evidence: CitationEvidence,
    ) -> str:
        if citation_id not in self._bindings_by_citation_id:
            source_document = _chat_source_document_from_chunk(citation_id, retrieved_chunk)
            self._bindings_by_citation_id[citation_id] = ChatCitationBinding(
                citation=ChatCitation(
                    citation_id=citation_id,
                    claim=claim_text,
                    source_document_id=retrieved_chunk.source_document.source_document_id,
                    chunk_id=retrieved_chunk.chunk.chunk_id,
                ),
                source_document=source_document,
                evidence=evidence,
            )
        return citation_id

    def _sorted_bindings(self) -> list[ChatCitationBinding]:
        return sorted(self._bindings_by_citation_id.values(), key=lambda binding: binding.evidence.citation_id)


def _unsupported_chat(pack: AssetKnowledgePack, safety_classification: SafetyClassification) -> ChatResponse:
    message = _unsupported_message(pack)
    response = ChatResponse(
        asset=pack.asset,
        direct_answer=message,
        why_it_matters="The product currently focuses on U.S.-listed common stocks and plain-vanilla ETFs.",
        citations=[],
        uncertainty=["No local asset knowledge pack is available for this ticker."],
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def _advice_redirect_chat(pack: AssetKnowledgePack, safety_classification: SafetyClassification) -> ChatResponse:
    direct_answer, why_it_matters = educational_redirect()
    response = ChatResponse(
        asset=pack.asset,
        direct_answer=direct_answer,
        why_it_matters=why_it_matters,
        citations=[],
        uncertainty=["This response does not use personal circumstances, live prices, tax details, or trading instructions."],
        safety_classification=safety_classification,
    )
    _assert_safe_copy(response)
    return response


def _plan_supported_chat(pack: AssetKnowledgePack, question: str) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    facts_by_field = {item.fact.field_name: item for item in pack.normalized_facts if item.fact.evidence_state == "supported"}
    chunks_by_claim_type = _chunks_by_claim_type(pack)
    bindings = _ChatCitationRegistry(pack)
    intent = _classify_intent(question)

    if intent == "recent":
        return _recent_plan(pack, facts_by_field, bindings)
    if intent == "risk":
        return _risk_plan(pack, facts_by_field, bindings, chunks_by_claim_type)
    if intent == "suitability":
        return _suitability_plan(pack, facts_by_field, bindings, chunks_by_claim_type)
    if intent == "business":
        if pack.asset.asset_type is AssetType.stock:
            return _stock_business_plan(pack, facts_by_field, bindings)
        return _insufficient_plan(pack, "business_model", "This local ETF fixture does not contain stock-style business-model evidence.")
    if intent in {"holdings", "benchmark", "cost", "breadth"}:
        if pack.asset.asset_type is AssetType.etf:
            return _etf_basics_plan(pack, facts_by_field, bindings, intent)
        return _insufficient_plan(pack, "etf_profile", "This local stock fixture does not contain ETF holdings, benchmark, breadth, or cost evidence.")
    if intent == "valuation":
        return _insufficient_plan(pack, "valuation_context", _gap_message(pack, "valuation_context"))

    return _identity_plan(pack, facts_by_field, bindings)


def _identity_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)

    if pack.asset.asset_type is AssetType.etf:
        benchmark = facts_by_field.get("benchmark")
        if benchmark is not None:
            claim_text = (
                f"{identity_claim.claim_text} It seeks to track the {benchmark.fact.value}."
            )
            citation_id = bindings.for_fact(benchmark, claim_text)
        else:
            claim_text = identity_claim.claim_text
            citation_id = identity_claim.citation_ids[0]
    else:
        business = facts_by_field.get("primary_business")
        if business is not None:
            claim_text = (
                f"{identity_claim.claim_text} Its local fixture says its primary business is: {business.fact.value}"
            )
            citation_id = bindings.for_fact(business, claim_text)
        else:
            claim_text = identity_claim.claim_text
            citation_id = identity_claim.citation_ids[0]

    planned_claims = [identity_claim]
    if claim_text != identity_claim.claim_text:
        planned_claims.append(
            PlannedChatClaim(
                claim_id="chat_identity_detail",
                claim_text=claim_text,
                citation_ids=[citation_id],
                claim_type="factual",
            )
        )

    return (
        _ChatPlan(
            direct_answer=claim_text,
            why_it_matters=(
                "Starting with canonical identity helps a beginner separate stable asset facts from recent developments "
                "or personal decision-making."
            ),
            planned_claims=planned_claims,
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _stock_business_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    business = _require_fact(facts_by_field, "primary_business")
    claim_text = f"{pack.asset.name}'s local fixture describes its primary business as: {business.fact.value}"
    citation_id = bindings.for_fact(business, claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="For a stock, business basics are the starting point for understanding what company-specific risks can affect it.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_stock_business",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="factual",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _etf_basics_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    intent: str,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    field_names_by_intent = {
        "benchmark": ["benchmark"],
        "cost": ["expense_ratio"],
        "holdings": ["holdings_count"],
        "breadth": ["beginner_role", "holdings_count", "benchmark"],
    }
    fields = [field for field in field_names_by_intent[intent] if field in facts_by_field]
    if not fields:
        return _insufficient_plan(pack, intent, f"The local fixture does not contain supported {intent} evidence for this asset.")

    facts = [facts_by_field[field] for field in fields]
    if intent == "benchmark":
        claim_text = f"{pack.asset.ticker} seeks to track the {facts[0].fact.value}."
    elif intent == "cost":
        claim_text = f"The local fixture records {pack.asset.ticker}'s expense ratio as {_format_metric(facts[0].fact.value, facts[0].fact.unit)}."
    elif intent == "holdings":
        claim_text = (
            f"The local fixture records {pack.asset.ticker} as having about "
            f"{_format_metric(facts[0].fact.value, facts[0].fact.unit)}."
        )
    else:
        role = facts_by_field.get("beginner_role")
        holdings = facts_by_field.get("holdings_count")
        benchmark = facts_by_field.get("benchmark")
        claim_text = (
            f"The local fixture frames {pack.asset.ticker} as {str(role.fact.value).lower()}; "
            f"it records about {_format_metric(holdings.fact.value, holdings.fact.unit)} and the {benchmark.fact.value} benchmark."
        )

    citation_ids = [bindings.for_fact(fact, claim_text) for fact in facts]
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters=(
                "ETF basics such as benchmark, holdings breadth, and cost help beginners understand what exposure the fund is designed to provide."
            ),
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id=f"chat_etf_{intent}",
                    claim_text=claim_text,
                    citation_ids=sorted(set(citation_ids)),
                    claim_type="factual" if intent != "breadth" else "interpretation",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _risk_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    chunks_by_claim_type: dict[str, list[RetrievedSourceChunk]],
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    risk_chunk = _first_chunk(chunks_by_claim_type, "risk")
    if risk_chunk is None:
        return _insufficient_plan(pack, "risk", "The local fixture does not contain supported risk evidence for this asset.")

    if pack.asset.ticker == "AAPL":
        claim_text = "A key beginner risk is company-specific risk: Apple can be affected by product demand, competition, supply chain disruption, regulation, and other company-specific issues."
    elif pack.asset.ticker == "QQQ":
        claim_text = "A key beginner risk is concentration: QQQ can be more concentrated than broader equity funds, so fewer companies or sectors can drive more of the result."
    else:
        claim_text = "A key beginner risk is market risk: VOO can lose value when U.S. large-company stocks decline, and index tracking does not remove that risk."

    citation_id = bindings.for_chunk(risk_chunk, claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Risk evidence helps a beginner understand what can go wrong before comparing an asset with broader or narrower alternatives.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_top_risk",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="risk",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _recent_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    if not pack.recent_developments:
        return _insufficient_plan(pack, "recent_development", "The local fixture does not contain recent-development evidence for this asset.")

    recent = pack.recent_developments[0]
    claim_text = f"{recent.recent_development.title}: {recent.recent_development.summary}"
    citation_id = bindings.for_recent_development(recent, claim_text)
    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters="Recent developments are kept separate from stable identity so a short-term update does not redefine what the asset is.",
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_recent_development",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type="recent",
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _suitability_plan(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
    chunks_by_claim_type: dict[str, list[RetrievedSourceChunk]],
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    identity_claim = _canonical_identity_claim(pack, facts_by_field, bindings)
    if pack.asset.asset_type is AssetType.etf:
        role = facts_by_field.get("beginner_role")
        if role is None:
            return _insufficient_plan(pack, "beginner_role", "The local fixture does not contain supported beginner-role evidence for this ETF.")
        if pack.asset.ticker == "QQQ":
            claim_text = (
                "Beginners may study QQQ to learn how narrower, growth-oriented ETF exposure differs from a broader market ETF."
            )
        else:
            claim_text = "Beginners may study VOO to learn how a broad U.S. large-company index ETF works."
        citation_id = bindings.for_fact(role, claim_text)
        claim_type = "interpretation"
    else:
        risk_chunk = _first_chunk(chunks_by_claim_type, "risk")
        if risk_chunk is None:
            return _insufficient_plan(pack, "suitability", "The local fixture does not contain supported suitability evidence for this stock.")
        claim_text = (
            "Beginners may study Apple to learn how a familiar single-company business differs from diversified fund exposure."
        )
        citation_id = bindings.for_chunk(risk_chunk, claim_text)
        claim_type = "risk"

    return (
        _ChatPlan(
            direct_answer=f"{identity_claim.claim_text} {claim_text}",
            why_it_matters=(
                "This is educational framing, not a personal recommendation; beginners can use it to decide what facts and risks to study next."
            ),
            planned_claims=[
                identity_claim,
                PlannedChatClaim(
                    claim_id="chat_educational_suitability",
                    claim_text=claim_text,
                    citation_ids=[citation_id],
                    claim_type=claim_type,
                )
            ],
            uncertainty=_fixture_limits(pack),
        ),
        bindings,
    )


def _insufficient_plan(
    pack: AssetKnowledgePack,
    field_name: str,
    message: str,
) -> tuple[_ChatPlan, _ChatCitationRegistry]:
    return (
        _ChatPlan(
            direct_answer=f"Insufficient evidence: {message}",
            why_it_matters=(
                "When the selected asset knowledge pack is missing evidence, the safer answer is to say what is unknown instead of filling the gap."
            ),
            planned_claims=[],
            uncertainty=[*_fixture_limits(pack), _gap_message(pack, field_name)],
        ),
        _ChatCitationRegistry(pack),
    )


def _canonical_identity_claim(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _ChatCitationRegistry,
) -> PlannedChatClaim:
    identity = _require_fact(facts_by_field, "canonical_asset_identity")
    if pack.asset.asset_type is AssetType.etf:
        issuer = f" from {pack.asset.issuer}" if pack.asset.issuer else ""
        claim_text = f"{pack.asset.ticker} is {pack.asset.name}, a plain-vanilla ETF listed in the U.S.{issuer}."
    else:
        claim_text = f"{pack.asset.ticker} is {pack.asset.name}, a U.S.-listed stock."
    citation_id = bindings.for_fact(identity, claim_text)
    return PlannedChatClaim(
        claim_id="chat_canonical_identity",
        claim_text=claim_text,
        citation_ids=[citation_id],
        claim_type="factual",
    )


def _classify_intent(question: str) -> str:
    text = " ".join(question.lower().split())
    if any(term in text for term in ["recent", "changed", "change", "news", "latest", "new development", "development"]):
        return "recent"
    if any(term in text for term in ["risk", "risks", "biggest catch", "main catch", "what can go wrong", "downside"]):
        return "risk"
    if any(term in text for term in ["beginner", "beginners", "why people", "why consider", "suitable", "fit", "use this", "use it"]):
        return "suitability"
    if any(term in text for term in ["business", "make money", "does apple do", "company do", "sells", "products", "services"]):
        return "business"
    if any(term in text for term in ["holding", "holdings", "hold", "holds", "owns", "own", "how many companies"]):
        return "holdings"
    if any(term in text for term in ["benchmark", "index", "track", "tracks"]):
        return "benchmark"
    if any(term in text for term in ["fee", "cost", "expense ratio", "expenses"]):
        return "cost"
    if any(term in text for term in ["broad", "breadth", "diversified", "narrow", "concentrated", "concentration"]):
        return "breadth"
    if any(term in text for term in ["valuation", "valued", "p/e", "pe ratio", "multiple", "expensive", "cheap"]):
        return "valuation"
    return "identity"


def _chunks_by_claim_type(pack: AssetKnowledgePack) -> dict[str, list[RetrievedSourceChunk]]:
    chunks: dict[str, list[RetrievedSourceChunk]] = {}
    for item in pack.source_chunks:
        for claim_type in item.chunk.supported_claim_types:
            chunks.setdefault(claim_type, []).append(item)
    return chunks


def _first_chunk(
    chunks_by_claim_type: dict[str, list[RetrievedSourceChunk]],
    claim_type: str,
) -> RetrievedSourceChunk | None:
    chunks = chunks_by_claim_type.get(claim_type)
    if not chunks:
        return None
    return sorted(chunks, key=lambda item: (item.source_document.source_rank, item.chunk.chunk_order))[0]


def _require_fact(facts_by_field: dict[str, RetrievedFact], field_name: str) -> RetrievedFact:
    fact = facts_by_field.get(field_name)
    if fact is None:
        raise ChatGenerationError(f"Required fact is missing from retrieval pack: {field_name}.")
    return fact


def _fixture_limits(pack: AssetKnowledgePack) -> list[str]:
    notes = ["This answer is bounded to the local fixture-backed asset knowledge pack and does not use live market data."]
    if pack.freshness.facts_as_of:
        notes.append(f"Stable facts are as of {pack.freshness.facts_as_of}.")
    if pack.freshness.recent_events_as_of:
        notes.append(f"Recent-development evidence is as of {pack.freshness.recent_events_as_of}.")
    return notes


def _gap_message(pack: AssetKnowledgePack, field_name: str) -> str:
    for gap in pack.evidence_gaps:
        if gap.field_name == field_name:
            return gap.message
    return f"No local fixture evidence is available for {field_name}."


def _unsupported_message(pack: AssetKnowledgePack) -> str:
    if pack.asset.status is AssetStatus.unknown:
        return "This ticker is not available in the local skeleton data yet."
    if pack.evidence_gaps:
        return pack.evidence_gaps[0].message
    return "This asset is outside the current U.S. stock and plain-vanilla ETF scope."


def _format_metric(value: Any, unit: str | None) -> str:
    if unit:
        return f"{value}{unit}"
    return str(value)


def _chat_source_document_from_chunk(citation_id: str, retrieved_chunk: RetrievedSourceChunk) -> ChatSourceDocument:
    source = retrieved_chunk.source_document
    return ChatSourceDocument(
        citation_id=citation_id,
        source_document_id=source.source_document_id,
        chunk_id=retrieved_chunk.chunk.chunk_id,
        title=source.title,
        source_type=source.source_type,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=source.retrieved_at,
        freshness_state=source.freshness_state,
        is_official=source.is_official,
        supporting_passage=retrieved_chunk.chunk.text,
    )


def _validate_chat_source_documents(response: ChatResponse, pack: AssetKnowledgePack) -> CitationValidationReport:
    citation_ids = {citation.citation_id for citation in response.citations}
    if not citation_ids and not response.source_documents:
        return _valid_chat_validation_report()

    source_documents_by_citation_id = {source.citation_id: source for source in response.source_documents}
    source_chunks_by_key = {
        (item.source_document.source_document_id, item.chunk.chunk_id): item for item in pack.source_chunks
    }

    issues: list[CitationValidationIssue] = []
    for citation in response.citations:
        source_document = source_documents_by_citation_id.get(citation.citation_id)
        if source_document is None:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id="chat_source_metadata",
                    citation_id=citation.citation_id,
                    source_document_id=citation.source_document_id,
                    message="Chat citation is missing source-document metadata.",
                )
            )
            continue

        if source_document.source_document_id != citation.source_document_id or source_document.chunk_id != citation.chunk_id:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id="chat_source_metadata",
                    citation_id=citation.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata does not match the citation binding.",
                )
            )
            continue

        expected = source_chunks_by_key.get((source_document.source_document_id, source_document.chunk_id))
        if expected is None:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.citation_not_found,
                    claim_id="chat_source_metadata",
                    citation_id=source_document.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata is not present in the selected asset knowledge pack.",
                )
            )
            continue

        if expected.chunk.asset_ticker != pack.asset.ticker or expected.source_document.asset_ticker != pack.asset.ticker:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.wrong_asset,
                    claim_id="chat_source_metadata",
                    citation_id=source_document.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata belongs to an asset outside the selected pack.",
                )
            )
            continue

        expected_source = expected.source_document
        metadata_matches_pack = (
            source_document.title == expected_source.title
            and source_document.source_type == expected_source.source_type
            and source_document.url == expected_source.url
            and source_document.published_at == expected_source.published_at
            and source_document.as_of_date == expected_source.as_of_date
            and source_document.retrieved_at == expected_source.retrieved_at
            and source_document.freshness_state is expected_source.freshness_state
            and source_document.supporting_passage == expected.chunk.text
        )
        if not metadata_matches_pack:
            issues.append(
                CitationValidationIssue(
                    status=CitationValidationStatus.insufficient_evidence,
                    claim_id="chat_source_metadata",
                    citation_id=source_document.citation_id,
                    source_document_id=source_document.source_document_id,
                    message="Chat source-document metadata does not match the selected asset knowledge pack.",
                )
            )

    extra_metadata_ids = set(source_documents_by_citation_id) - citation_ids
    for citation_id in sorted(extra_metadata_ids):
        source_document = source_documents_by_citation_id[citation_id]
        issues.append(
            CitationValidationIssue(
                status=CitationValidationStatus.citation_not_found,
                claim_id="chat_source_metadata",
                citation_id=citation_id,
                source_document_id=source_document.source_document_id,
                message="Chat source-document metadata has no matching chat citation.",
            )
        )

    if not issues:
        return _valid_chat_validation_report()

    return CitationValidationReport(
        status=issues[0].status,
        results=[
            CitationValidationResult(
                claim_id="chat_source_metadata",
                status=issues[0].status,
                issues=issues,
            )
        ],
    )


def _valid_chat_validation_report() -> CitationValidationReport:
    return CitationValidationReport(
        status=CitationValidationStatus.valid,
        results=[CitationValidationResult(claim_id="chat_source_metadata", status=CitationValidationStatus.valid)],
    )


def _evidence_from_chat_response(pack: AssetKnowledgePack, response: ChatResponse) -> list[CitationEvidence]:
    source_chunks_by_key = {
        (item.source_document.source_document_id, item.chunk.chunk_id): item for item in pack.source_chunks
    }
    evidence_by_id: dict[str, CitationEvidence] = {}
    for citation in response.citations:
        key = (citation.source_document_id, citation.chunk_id)
        item = source_chunks_by_key.get(key)
        if item is None:
            continue
        citation_id = _citation_id(citation.source_document_id, citation.chunk_id)
        evidence_by_id[citation_id] = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=item.chunk.asset_ticker,
            source_document_id=item.source_document.source_document_id,
            source_type=item.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=item.source_document.freshness_state,
            supported_claim_types=item.chunk.supported_claim_types,
            supporting_text=item.chunk.text,
            supports_claim=True,
            is_recent=item.source_document.source_type == "recent_development",
        )
    return list(evidence_by_id.values())


def _claims_from_chat_response(
    response: ChatResponse,
    pack: AssetKnowledgePack,
) -> list[CitationValidationClaim]:
    if not response.citations:
        return [
            CitationValidationClaim(
                claim_id="chat_response_direct_answer",
                claim_text=response.direct_answer,
                claim_type="factual",
                citation_ids=[],
                citation_required=_requires_citations(response, pack),
                important=_requires_citations(response, pack),
            )
        ]

    source_chunks_by_key = {
        (item.source_document.source_document_id, item.chunk.chunk_id): item for item in pack.source_chunks
    }
    claims: list[CitationValidationClaim] = []
    for index, citation in enumerate(response.citations, start=1):
        key = (citation.source_document_id, citation.chunk_id)
        chunk = source_chunks_by_key.get(key)
        claims.append(
            CitationValidationClaim(
                claim_id=f"chat_response_claim_{index}",
                claim_text=citation.claim,
                claim_type=_infer_claim_type(citation.claim, chunk),
                citation_ids=[_citation_id(citation.source_document_id, citation.chunk_id)],
            )
        )
    return claims


def _requires_citations(response: ChatResponse, pack: AssetKnowledgePack) -> bool:
    if response.safety_classification is not SafetyClassification.educational:
        return False
    if not pack.asset.supported:
        return False
    return "insufficient evidence" not in response.direct_answer.lower()


def _infer_claim_type(claim_text: str, chunk: RetrievedSourceChunk | None) -> str:
    text = claim_text.lower()
    supported = set(chunk.chunk.supported_claim_types) if chunk is not None else set()
    if "recent" in supported:
        return "recent"
    if "risk" in supported and any(term in text for term in ["risk", "concentration", "lose value", "company-specific"]):
        return "risk"
    if "suitability" in supported and any(term in text for term in ["beginner", "educational", "study"]):
        return "suitability"
    if "interpretation" in supported and any(term in text for term in ["beginner", "broad", "narrower", "exposure"]):
        return "interpretation"
    return "factual"


def _citation_id(source_document_id: str, chunk_id: str) -> str:
    return f"chat_{source_document_id}_{chunk_id}"


def _assert_safe_copy(response: ChatResponse) -> None:
    dumped = response.model_dump(mode="json")
    hits = find_forbidden_output_phrases(_flatten_text(dumped))
    if hits:
        raise ChatGenerationError(f"Generated chat leaked forbidden output phrases: {hits}")


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return ""
