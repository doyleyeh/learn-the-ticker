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
    AssetType,
    BeginnerSummary,
    Citation,
    Claim,
    FreshnessState,
    MetricValue,
    OverviewResponse,
    RecentDevelopment,
    RiskItem,
    SourceDocument,
    StateMessage,
    SuitabilitySummary,
)
from backend.retrieval import (
    AssetKnowledgePack,
    RetrievedFact,
    RetrievedRecentDevelopment,
    RetrievedSourceChunk,
    SourceDocumentFixture,
    build_asset_knowledge_pack,
)
from backend.safety import find_forbidden_output_phrases


class OverviewGenerationError(ValueError):
    """Raised when deterministic overview generation violates project contracts."""


@dataclass(frozen=True)
class CitationBinding:
    citation: Citation
    source_document: SourceDocument
    evidence: CitationEvidence


@dataclass(frozen=True)
class PlannedClaim:
    claim: Claim
    claim_type: str
    freshness_label: FreshnessState | None = None


def generate_asset_overview(ticker: str) -> OverviewResponse:
    """Build an OverviewResponse-compatible payload from the local retrieval pack."""

    return generate_overview_from_pack(build_asset_knowledge_pack(ticker))


def generate_overview_from_pack(pack: AssetKnowledgePack) -> OverviewResponse:
    if not pack.asset.supported:
        return _unsupported_overview(pack)

    facts_by_field = {item.fact.field_name: item for item in pack.normalized_facts if item.fact.evidence_state == "supported"}
    source_chunks_by_id = {item.chunk.chunk_id: item for item in pack.source_chunks}
    bindings = _CitationRegistry(pack)

    identity_fact = _require_fact(facts_by_field, "canonical_asset_identity")
    identity_citation_id = bindings.for_fact(identity_fact).citation.citation_id

    snapshot = _build_snapshot(pack, facts_by_field, bindings, identity_citation_id)
    beginner_summary = _build_beginner_summary(pack, facts_by_field)
    risk_chunk = _select_risk_chunk(pack)
    risk_citation_id = bindings.for_chunk(risk_chunk).citation.citation_id
    top_risks = _build_top_risks(pack, risk_citation_id)
    recent_developments = _build_recent_developments(pack, bindings)
    suitability_summary = _build_suitability_summary(pack, facts_by_field)

    planned_claims = _build_planned_claims(
        pack=pack,
        facts_by_field=facts_by_field,
        beginner_summary=beginner_summary,
        top_risks=top_risks,
        recent_developments=recent_developments,
        suitability_summary=suitability_summary,
        risk_citation_id=risk_citation_id,
        bindings=bindings,
    )

    report = validate_generated_overview_claims(pack, planned_claims, bindings.evidence())
    if not report.valid:
        first_issue = report.issues[0]
        raise OverviewGenerationError(
            f"Generated overview citation validation failed for {pack.asset.ticker}: "
            f"{first_issue.status.value} on {first_issue.claim_id}"
        )

    response = OverviewResponse(
        asset=pack.asset,
        state=_state_for_pack(pack),
        freshness=pack.freshness,
        snapshot=snapshot,
        beginner_summary=beginner_summary,
        top_risks=top_risks,
        recent_developments=recent_developments,
        suitability_summary=suitability_summary,
        claims=[planned.claim for planned in planned_claims],
        citations=bindings.citations(),
        source_documents=bindings.source_documents(),
    )
    _assert_safe_copy(response)
    return response


def validate_overview_response(overview: OverviewResponse, pack: AssetKnowledgePack) -> CitationValidationReport:
    evidence = _evidence_from_overview(pack, overview)
    claims = [
        CitationValidationClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type=_claim_type_from_id(claim.claim_id),
            citation_ids=claim.citation_ids,
        )
        for claim in overview.claims
    ]
    return validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))


def validate_generated_overview_claims(
    pack: AssetKnowledgePack,
    planned_claims: Iterable[PlannedClaim],
    evidence: list[CitationEvidence],
) -> CitationValidationReport:
    claims = [
        CitationValidationClaim(
            claim_id=planned.claim.claim_id,
            claim_text=planned.claim.claim_text,
            claim_type=planned.claim_type,
            citation_ids=planned.claim.citation_ids,
            freshness_label=planned.freshness_label,
        )
        for planned in planned_claims
    ]
    return validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))


class _CitationRegistry:
    def __init__(self, pack: AssetKnowledgePack) -> None:
        self._pack = pack
        self._bindings_by_citation_id: dict[str, CitationBinding] = {}

    def for_fact(self, retrieved_fact: RetrievedFact) -> CitationBinding:
        citation_id = f"c_{retrieved_fact.fact.fact_id}"
        source_document = _source_document_from_fixture(retrieved_fact.source_document, retrieved_fact.source_chunk.text)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=self._pack.asset.ticker,
            source_document_id=retrieved_fact.source_document.source_document_id,
            source_type=retrieved_fact.source_document.source_type,
            evidence_kind=EvidenceKind.normalized_fact,
            freshness_state=retrieved_fact.fact.freshness_state,
            supported_claim_types=retrieved_fact.source_chunk.supported_claim_types,
            supporting_text=retrieved_fact.source_chunk.text,
            supports_claim=retrieved_fact.fact.evidence_state == "supported",
            is_recent=False,
        )
        return self._add_binding(citation_id, retrieved_fact.source_document, source_document, evidence)

    def for_chunk(self, retrieved_chunk: RetrievedSourceChunk) -> CitationBinding:
        citation_id = f"c_{retrieved_chunk.chunk.chunk_id}"
        source_document = _source_document_from_fixture(retrieved_chunk.source_document, retrieved_chunk.chunk.text)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=self._pack.asset.ticker,
            source_document_id=retrieved_chunk.source_document.source_document_id,
            source_type=retrieved_chunk.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=retrieved_chunk.source_document.freshness_state,
            supported_claim_types=retrieved_chunk.chunk.supported_claim_types,
            supporting_text=retrieved_chunk.chunk.text,
            supports_claim=True,
            is_recent=retrieved_chunk.source_document.source_type == "recent_development",
        )
        return self._add_binding(citation_id, retrieved_chunk.source_document, source_document, evidence)

    def for_recent_development(self, retrieved_recent: RetrievedRecentDevelopment) -> CitationBinding:
        citation_id = f"c_{retrieved_recent.recent_development.event_id}"
        source_document = _source_document_from_fixture(retrieved_recent.source_document, retrieved_recent.source_chunk.text)
        evidence = CitationEvidence(
            citation_id=citation_id,
            asset_ticker=self._pack.asset.ticker,
            source_document_id=retrieved_recent.source_document.source_document_id,
            source_type=retrieved_recent.source_document.source_type,
            evidence_kind=EvidenceKind.document_chunk,
            freshness_state=retrieved_recent.recent_development.freshness_state,
            supported_claim_types=retrieved_recent.source_chunk.supported_claim_types,
            supporting_text=retrieved_recent.source_chunk.text,
            supports_claim=retrieved_recent.recent_development.evidence_state == "no_major_recent_development",
            is_recent=True,
        )
        return self._add_binding(citation_id, retrieved_recent.source_document, source_document, evidence)

    def citations(self) -> list[Citation]:
        return [binding.citation for binding in self._sorted_bindings()]

    def source_documents(self) -> list[SourceDocument]:
        by_id = {binding.source_document.source_document_id: binding.source_document for binding in self._sorted_bindings()}
        return list(by_id.values())

    def evidence(self) -> list[CitationEvidence]:
        return [binding.evidence for binding in self._sorted_bindings()]

    def _add_binding(
        self,
        citation_id: str,
        source_fixture: SourceDocumentFixture,
        source_document: SourceDocument,
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
            source_document=source_document,
            evidence=evidence,
        )
        self._bindings_by_citation_id[citation_id] = binding
        return binding

    def _sorted_bindings(self) -> list[CitationBinding]:
        return sorted(self._bindings_by_citation_id.values(), key=lambda binding: binding.citation.citation_id)


def _unsupported_overview(pack: AssetKnowledgePack) -> OverviewResponse:
    return OverviewResponse(
        asset=pack.asset,
        state=_state_for_pack(pack),
        freshness=pack.freshness,
        snapshot={},
        beginner_summary=None,
        top_risks=[],
        recent_developments=[],
        suitability_summary=None,
        claims=[],
        citations=[],
        source_documents=[],
    )


def _state_for_pack(pack: AssetKnowledgePack) -> StateMessage:
    if pack.asset.status is AssetStatus.supported:
        return StateMessage(status=AssetStatus.supported, message="Asset is supported by deterministic local retrieval fixtures.")
    message = pack.evidence_gaps[0].message if pack.evidence_gaps else "No local retrieval fixture is available for this ticker."
    return StateMessage(status=pack.asset.status, message=message)


def _build_snapshot(
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _CitationRegistry,
    identity_citation_id: str,
) -> dict[str, MetricValue | str | int | float | None]:
    snapshot: dict[str, MetricValue | str | int | float | None] = {
        "ticker": pack.asset.ticker,
        "name": pack.asset.name,
        "asset_type": pack.asset.asset_type.value,
        "exchange": MetricValue(value=pack.asset.exchange, citation_ids=[identity_citation_id]),
    }
    if pack.asset.issuer:
        snapshot["issuer"] = MetricValue(value=pack.asset.issuer, citation_ids=[identity_citation_id])

    if pack.asset.asset_type is AssetType.etf:
        for field_name in ["benchmark", "expense_ratio", "holdings_count", "beginner_role"]:
            fact = facts_by_field.get(field_name)
            if fact is not None:
                snapshot[field_name] = _metric_from_fact(fact, bindings.for_fact(fact).citation.citation_id)
    elif pack.asset.asset_type is AssetType.stock:
        identity = facts_by_field["canonical_asset_identity"].fact.value
        if isinstance(identity, dict) and identity.get("cik"):
            snapshot["cik"] = MetricValue(value=identity["cik"], citation_ids=[identity_citation_id])
        for field_name in ["primary_business", "company_specific_risk"]:
            fact = facts_by_field.get(field_name)
            if fact is not None:
                snapshot[field_name] = _metric_from_fact(fact, bindings.for_fact(fact).citation.citation_id)

    return snapshot


def _build_beginner_summary(pack: AssetKnowledgePack, facts_by_field: dict[str, RetrievedFact]) -> BeginnerSummary:
    if pack.asset.asset_type is AssetType.etf:
        benchmark = _fact_value(facts_by_field, "benchmark")
        role = str(_fact_value(facts_by_field, "beginner_role")).lower()
        holdings = _fact_value(facts_by_field, "holdings_count")
        expense_ratio = _format_metric(facts_by_field["expense_ratio"].fact.value, facts_by_field["expense_ratio"].fact.unit)
        if pack.asset.ticker == "QQQ":
            main_catch = "The main catch is concentration: this fund is narrower than a broad-market fund, so fewer companies and sectors can drive more of the result."
        else:
            main_catch = "The main catch is that this is still stock-market exposure; index tracking does not remove the risk of losses when large U.S. stocks fall."

        return BeginnerSummary(
            what_it_is=f"{pack.asset.ticker} is a U.S.-listed ETF from {pack.asset.issuer} that seeks to track the {benchmark}.",
            why_people_consider_it=(
                f"Beginners often study it to understand {role}; the local fixture records about {holdings} holdings "
                f"and a {expense_ratio} expense ratio."
            ),
            main_catch=main_catch,
        )

    primary_business = _fact_value(facts_by_field, "primary_business")
    return BeginnerSummary(
        what_it_is=f"{pack.asset.name} is a U.S.-listed company; the local fixture describes its primary business as: {primary_business}",
        why_people_consider_it=(
            "Beginners often study it because the business is familiar and the fixture separates stable business facts "
            "from recent developments."
        ),
        main_catch="A single-company stock is less diversified than an ETF, so company-specific issues can matter more.",
    )


def _build_top_risks(pack: AssetKnowledgePack, risk_citation_id: str) -> list[RiskItem]:
    if pack.asset.ticker == "AAPL":
        risks = [
            ("Company-specific risk", "A single company can be affected by its own product demand, execution, and operating problems."),
            ("Competition", "Consumer technology markets can change quickly when competitors release new products or services."),
            ("Supply chain and regulation", "Global operations can be affected by manufacturing, legal, or regulatory issues."),
        ]
    elif pack.asset.ticker == "QQQ":
        risks = [
            ("Concentration risk", "A smaller group of companies or sectors can drive more of the fund's results."),
            ("Narrower index exposure", "The fund does not represent the whole U.S. stock market, so it can behave differently from broader ETFs."),
            ("Market risk", "The fund can lose value when the stocks in its index decline."),
        ]
    else:
        risks = [
            ("Market risk", "The fund can lose value when large U.S. stocks decline."),
            ("Index-tracking limits", "The fund follows an index, so it does not try to avoid weaker areas of that index."),
            ("Large-company focus", "The fund focuses on large U.S. companies rather than every public company or every asset class."),
        ]

    return [
        RiskItem(title=title, plain_english_explanation=explanation, citation_ids=[risk_citation_id])
        for title, explanation in risks
    ]


def _build_recent_developments(pack: AssetKnowledgePack, bindings: _CitationRegistry) -> list[RecentDevelopment]:
    developments: list[RecentDevelopment] = []
    for item in pack.recent_developments:
        citation_id = bindings.for_recent_development(item).citation.citation_id
        developments.append(
            RecentDevelopment(
                title=item.recent_development.title,
                summary=item.recent_development.summary,
                event_date=item.recent_development.event_date,
                citation_ids=[citation_id],
                freshness_state=item.recent_development.freshness_state,
            )
        )
    return developments


def _build_suitability_summary(pack: AssetKnowledgePack, facts_by_field: dict[str, RetrievedFact]) -> SuitabilitySummary:
    if pack.asset.asset_type is AssetType.etf:
        role = _fact_value(facts_by_field, "beginner_role")
        if pack.asset.ticker == "QQQ":
            may_not_fit = "It may be less useful for learning broad-market diversification because the fixture describes narrower Nasdaq-100 exposure."
        else:
            may_not_fit = "It may be less useful for learning about bonds, international stocks, or narrow sector funds."
        return SuitabilitySummary(
            may_fit=f"Educationally, this overview can help someone learn how a {str(role).lower()} works.",
            may_not_fit=may_not_fit,
            learn_next="Compare benchmark, holdings count, cost, and concentration with a similar ETF before drawing conclusions.",
        )

    return SuitabilitySummary(
        may_fit="Educationally, this overview can help someone learn how a large single-company business model is described from filings.",
        may_not_fit="It should not be confused with diversified fund exposure because one company carries company-specific risk.",
        learn_next="Compare company-specific risk with ETF diversification and review which facts are unavailable in the local fixture.",
    )


def _build_planned_claims(
    *,
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    beginner_summary: BeginnerSummary,
    top_risks: list[RiskItem],
    recent_developments: list[RecentDevelopment],
    suitability_summary: SuitabilitySummary,
    risk_citation_id: str,
    bindings: _CitationRegistry,
) -> list[PlannedClaim]:
    planned: list[PlannedClaim] = []

    if pack.asset.asset_type is AssetType.etf:
        for field_name in ["canonical_asset_identity", "benchmark", "expense_ratio", "holdings_count", "beginner_role"]:
            fact = _require_fact(facts_by_field, field_name)
            citation_id = bindings.for_fact(fact).citation.citation_id
            planned.append(
                PlannedClaim(
                    claim=Claim(
                        claim_id=f"claim_factual_{field_name}",
                        claim_text=_claim_text_for_fact(pack, fact),
                        citation_ids=[citation_id],
                    ),
                    claim_type="factual" if field_name != "beginner_role" else "interpretation",
                )
            )
        what_it_is_citation = bindings.for_fact(_require_fact(facts_by_field, "benchmark")).citation.citation_id
    else:
        for field_name in ["canonical_asset_identity", "primary_business"]:
            fact = _require_fact(facts_by_field, field_name)
            citation_id = bindings.for_fact(fact).citation.citation_id
            planned.append(
                PlannedClaim(
                    claim=Claim(
                        claim_id=f"claim_factual_{field_name}",
                        claim_text=_claim_text_for_fact(pack, fact),
                        citation_ids=[citation_id],
                    ),
                    claim_type="factual",
                )
            )
        what_it_is_citation = bindings.for_fact(_require_fact(facts_by_field, "primary_business")).citation.citation_id

    planned.append(
        PlannedClaim(
            claim=Claim(
                claim_id="claim_factual_beginner_summary",
                claim_text=beginner_summary.what_it_is,
                citation_ids=[what_it_is_citation],
            ),
            claim_type="factual",
        )
    )

    for index, risk in enumerate(top_risks, start=1):
        planned.append(
            PlannedClaim(
                claim=Claim(
                    claim_id=f"claim_risk_top_{index}",
                    claim_text=f"{risk.title}: {risk.plain_english_explanation}",
                    citation_ids=[risk_citation_id],
                ),
                claim_type="risk",
            )
        )

    for index, item in enumerate(recent_developments, start=1):
        planned.append(
            PlannedClaim(
                claim=Claim(
                    claim_id=f"claim_recent_{index}",
                    claim_text=f"{item.title}: {item.summary}",
                    citation_ids=item.citation_ids,
                ),
                claim_type="recent",
            )
        )

    planned.append(
        PlannedClaim(
            claim=Claim(
                claim_id="claim_risk_suitability_framing",
                claim_text=f"{suitability_summary.may_not_fit} {suitability_summary.learn_next}",
                citation_ids=[risk_citation_id],
            ),
            claim_type="risk",
        )
    )
    return planned


def _claim_text_for_fact(pack: AssetKnowledgePack, fact: RetrievedFact) -> str:
    value = fact.fact.value
    if fact.fact.field_name == "canonical_asset_identity":
        type_label = "ETF" if pack.asset.asset_type is AssetType.etf else "stock"
        article = "an" if pack.asset.asset_type is AssetType.etf else "a"
        return f"{pack.asset.ticker} is identified as {pack.asset.name}, {article} {type_label}."
    if fact.fact.field_name == "expense_ratio":
        value = _format_metric(value, fact.fact.unit)
    return f"{pack.asset.ticker} {fact.fact.field_name.replace('_', ' ')} is {value}."


def _select_risk_chunk(pack: AssetKnowledgePack) -> RetrievedSourceChunk:
    for item in pack.source_chunks:
        if "risk" in item.chunk.supported_claim_types:
            return item
    raise OverviewGenerationError(f"No risk evidence chunk is available for {pack.asset.ticker}.")


def _require_fact(facts_by_field: dict[str, RetrievedFact], field_name: str) -> RetrievedFact:
    fact = facts_by_field.get(field_name)
    if fact is None:
        raise OverviewGenerationError(f"Required fact is missing from retrieval pack: {field_name}.")
    return fact


def _metric_from_fact(retrieved_fact: RetrievedFact, citation_id: str) -> MetricValue:
    return MetricValue(value=retrieved_fact.fact.value, unit=retrieved_fact.fact.unit, citation_ids=[citation_id])


def _fact_value(facts_by_field: dict[str, RetrievedFact], field_name: str) -> Any:
    return _require_fact(facts_by_field, field_name).fact.value


def _format_metric(value: Any, unit: str | None) -> str:
    if unit:
        return f"{value}{unit}"
    return str(value)


def _source_document_from_fixture(source: SourceDocumentFixture, supporting_passage: str) -> SourceDocument:
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
    )


def _evidence_from_overview(pack: AssetKnowledgePack, overview: OverviewResponse) -> list[CitationEvidence]:
    evidence_by_id: dict[str, CitationEvidence] = {}
    facts_by_citation_id = {f"c_{item.fact.fact_id}": item for item in pack.normalized_facts}
    chunks_by_citation_id = {f"c_{item.chunk.chunk_id}": item for item in pack.source_chunks}
    recent_by_citation_id = {f"c_{item.recent_development.event_id}": item for item in pack.recent_developments}

    for citation in overview.citations:
        if citation.citation_id in facts_by_citation_id:
            item = facts_by_citation_id[citation.citation_id]
            evidence_by_id[citation.citation_id] = CitationEvidence(
                citation_id=citation.citation_id,
                asset_ticker=pack.asset.ticker,
                source_document_id=item.source_document.source_document_id,
                source_type=item.source_document.source_type,
                evidence_kind=EvidenceKind.normalized_fact,
                freshness_state=item.fact.freshness_state,
                supported_claim_types=item.source_chunk.supported_claim_types,
                supporting_text=item.source_chunk.text,
                supports_claim=item.fact.evidence_state == "supported",
                is_recent=False,
            )
        elif citation.citation_id in chunks_by_citation_id:
            item = chunks_by_citation_id[citation.citation_id]
            evidence_by_id[citation.citation_id] = CitationEvidence(
                citation_id=citation.citation_id,
                asset_ticker=pack.asset.ticker,
                source_document_id=item.source_document.source_document_id,
                source_type=item.source_document.source_type,
                evidence_kind=EvidenceKind.document_chunk,
                freshness_state=item.source_document.freshness_state,
                supported_claim_types=item.chunk.supported_claim_types,
                supporting_text=item.chunk.text,
                supports_claim=True,
                is_recent=item.source_document.source_type == "recent_development",
            )
        elif citation.citation_id in recent_by_citation_id:
            item = recent_by_citation_id[citation.citation_id]
            evidence_by_id[citation.citation_id] = CitationEvidence(
                citation_id=citation.citation_id,
                asset_ticker=pack.asset.ticker,
                source_document_id=item.source_document.source_document_id,
                source_type=item.source_document.source_type,
                evidence_kind=EvidenceKind.document_chunk,
                freshness_state=item.recent_development.freshness_state,
                supported_claim_types=item.source_chunk.supported_claim_types,
                supporting_text=item.source_chunk.text,
                supports_claim=item.recent_development.evidence_state == "no_major_recent_development",
                is_recent=True,
            )

    return list(evidence_by_id.values())


def _claim_type_from_id(claim_id: str) -> str:
    if claim_id.startswith("claim_recent_"):
        return "recent"
    if claim_id.startswith("claim_risk_"):
        return "risk"
    if claim_id == "claim_factual_beginner_role":
        return "interpretation"
    return "factual"


def _assert_safe_copy(response: OverviewResponse) -> None:
    dumped = response.model_dump(mode="json")
    hits = find_forbidden_output_phrases(_flatten_text(dumped))
    if hits:
        raise OverviewGenerationError(f"Generated overview leaked forbidden output phrases: {hits}")


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return ""
