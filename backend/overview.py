from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from backend.citations import (
    CitationEvidence,
    CitationValidationClaim,
    CitationValidationContext,
    CitationValidationReport,
    EvidenceKind,
    validate_claims,
)
from backend.cache import build_knowledge_pack_freshness_input, compute_knowledge_pack_freshness_hash
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    GeneratedOutputCacheContractError,
    GeneratedOutputCacheRepositoryRecords,
    build_deterministic_generated_output_cache_records,
    persist_generated_output_cache_records,
    validate_generated_output_cache_records,
)
from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    CacheEntryKind,
    CacheScope,
    BeginnerSummary,
    Citation,
    Claim,
    EvidenceState,
    FreshnessState,
    MetricValue,
    OverviewMetric,
    OverviewResponse,
    OverviewSection,
    OverviewSectionFreshnessCitationBinding,
    OverviewSectionFreshnessDiagnostics,
    OverviewSectionFreshnessSourceBinding,
    OverviewSectionFreshnessValidation,
    OverviewSectionFreshnessValidationOutcome,
    OverviewSectionItem,
    OverviewSectionType,
    RecentDevelopment,
    RiskItem,
    SectionFreshnessInput,
    SourceDocument,
    Freshness,
    StateMessage,
    SuitabilitySummary,
)
from backend.retrieval import (
    AssetKnowledgePack,
    EvidenceGap,
    NormalizedFactFixture,
    RetrievedFact,
    RetrievedRecentDevelopment,
    RetrievedSourceChunk,
    RecentDevelopmentFixture,
    SourceChunkFixture,
    SourceDocumentFixture,
    _section_freshness_labels,
    build_asset_knowledge_pack,
)
from backend.repositories.knowledge_packs import (
    KnowledgePackRepositoryRecords,
    KnowledgePackRepositoryContractError,
)
from backend.retrieval_repository import (
    KnowledgePackRecordReader,
    read_persisted_knowledge_pack_response,
)
from backend.safety import find_forbidden_output_phrases
from backend.source_policy import resolve_source_policy
from backend.weekly_news import (
    DEFAULT_WEEKLY_NEWS_AS_OF,
    WeeklyNewsEventEvidenceRecordReader,
    build_ai_comprehensive_analysis,
    build_weekly_news_focus_from_pack,
    read_persisted_weekly_news_focus,
)


class OverviewGenerationError(ValueError):
    """Raised when deterministic overview generation violates project contracts."""


OVERVIEW_PERSISTED_READ_BOUNDARY = "overview-persisted-read-boundary-v1"


class GeneratedOutputCacheRecordReader(Protocol):
    def read_generated_output_cache_records(self, ticker: str) -> GeneratedOutputCacheRepositoryRecords | None:
        ...


@dataclass(frozen=True)
class PersistedOverviewReadResult:
    status: str
    ticker: str
    overview: OverviewResponse | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found(self) -> bool:
        return self.status == "found" and self.overview is not None


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


@dataclass(frozen=True)
class FreshnessValidationSubject:
    section_id: str
    section_type: OverviewSectionType
    displayed_freshness_state: FreshnessState
    displayed_evidence_state: EvidenceState
    displayed_as_of_date: str | None
    displayed_retrieved_at: str | None
    citation_ids: tuple[str, ...]
    source_document_ids: tuple[str, ...]
    supporting_freshness_states: tuple[FreshnessState, ...]
    supporting_as_of_dates: tuple[str, ...]
    supporting_retrieved_ats: tuple[str, ...]
    has_gap_evidence: bool = False
    limitations: str | None = None


def generate_asset_overview(
    ticker: str,
    *,
    persisted_pack_reader: KnowledgePackRecordReader | Any | None = None,
    generated_output_cache_reader: GeneratedOutputCacheRecordReader | Any | None = None,
    generated_output_cache_writer: Any | None = None,
    persisted_weekly_news_reader: WeeklyNewsEventEvidenceRecordReader | Any | None = None,
) -> OverviewResponse:
    """Build an OverviewResponse-compatible payload from the local retrieval pack."""

    persisted = read_persisted_overview_response(
        ticker,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
    )
    if persisted.found and persisted.overview is not None:
        return persisted.overview

    pack = build_asset_knowledge_pack(ticker)
    overview = generate_overview_from_pack(
        pack,
        persisted_weekly_news_reader=persisted_weekly_news_reader,
    )
    _maybe_write_overview_generated_output_cache(overview, pack, generated_output_cache_writer)
    return overview


def read_persisted_overview_response(
    ticker: str,
    *,
    persisted_pack_reader: KnowledgePackRecordReader | Any | None = None,
    generated_output_cache_reader: GeneratedOutputCacheRecordReader | Any | None = None,
) -> PersistedOverviewReadResult:
    normalized = ticker.strip().upper()
    if persisted_pack_reader is None or generated_output_cache_reader is None:
        return PersistedOverviewReadResult(
            status="not_configured",
            ticker=normalized,
            diagnostics=("reader:not_configured",),
        )

    pack_read = read_persisted_knowledge_pack_response(normalized, reader=persisted_pack_reader)
    if not pack_read.found or pack_read.response is None or pack_read.records is None:
        return PersistedOverviewReadResult(
            status=pack_read.status,
            ticker=normalized,
            diagnostics=(f"knowledge_pack:{pack_read.status}",),
        )
    if not pack_read.response.asset.supported or not pack_read.response.generated_output_available:
        return PersistedOverviewReadResult(
            status="blocked_state",
            ticker=normalized,
            diagnostics=(f"knowledge_pack:blocked:{pack_read.response.build_state.value}",),
        )

    cache_records_result = _read_generated_output_cache_records(generated_output_cache_reader, normalized)
    if cache_records_result.status != "found" or cache_records_result.records is None:
        return PersistedOverviewReadResult(
            status=cache_records_result.status,
            ticker=normalized,
            diagnostics=cache_records_result.diagnostics,
        )

    try:
        pack = _asset_knowledge_pack_from_repository_records(pack_read.records)
        _validate_generated_output_cache_for_overview(
            normalized,
            cache_records_result.records,
            pack=pack,
            pack_records=pack_read.records,
            knowledge_pack_hash=pack_read.response.knowledge_pack_freshness_hash,
        )
        overview = generate_overview_from_pack(pack)
        report = validate_overview_response(overview, pack)
        if not report.valid:
            return PersistedOverviewReadResult(
                status="validation_error",
                ticker=normalized,
                diagnostics=("overview:citation_validation_failed",),
            )
    except (
        GeneratedOutputCacheContractError,
        KnowledgePackRepositoryContractError,
        OverviewGenerationError,
        LookupError,
        StopIteration,
        ValueError,
        TypeError,
    ) as exc:
        return PersistedOverviewReadResult(
            status="contract_error",
            ticker=normalized,
            diagnostics=(f"overview:{exc.__class__.__name__}",),
        )

    return PersistedOverviewReadResult(
        status="found",
        ticker=normalized,
        overview=overview,
        diagnostics=("overview:persisted_hit",),
    )


@dataclass(frozen=True)
class _GeneratedOutputCacheReadResult:
    status: str
    ticker: str
    records: GeneratedOutputCacheRepositoryRecords | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


def _read_generated_output_cache_records(
    reader: GeneratedOutputCacheRecordReader | Any,
    ticker: str,
) -> _GeneratedOutputCacheReadResult:
    try:
        raw_records = _read_generated_output_cache_reader(reader, ticker)
        if raw_records is None:
            return _GeneratedOutputCacheReadResult(
                status="miss",
                ticker=ticker,
                diagnostics=("generated_output_cache:miss",),
            )
        records = (
            raw_records
            if isinstance(raw_records, GeneratedOutputCacheRepositoryRecords)
            else GeneratedOutputCacheRepositoryRecords.model_validate(raw_records)
        )
        validated = validate_generated_output_cache_records(records)
    except GeneratedOutputCacheContractError as exc:
        return _GeneratedOutputCacheReadResult(
            status="contract_error",
            ticker=ticker,
            diagnostics=(f"generated_output_cache:{exc.__class__.__name__}",),
        )
    except Exception as exc:  # pragma: no cover - caller observes sanitized status only.
        return _GeneratedOutputCacheReadResult(
            status="reader_error",
            ticker=ticker,
            diagnostics=(f"generated_output_cache:{exc.__class__.__name__}",),
        )
    return _GeneratedOutputCacheReadResult(
        status="found",
        ticker=ticker,
        records=validated,
        diagnostics=("generated_output_cache:found",),
    )


def _read_generated_output_cache_reader(
    reader: GeneratedOutputCacheRecordReader | Any,
    ticker: str,
) -> GeneratedOutputCacheRepositoryRecords | None:
    if isinstance(reader, dict):
        return reader.get(ticker)
    if hasattr(reader, "read_generated_output_cache_records"):
        return reader.read_generated_output_cache_records(ticker)
    if hasattr(reader, "read_asset_overview_records"):
        return reader.read_asset_overview_records(ticker)
    if hasattr(reader, "read"):
        return reader.read(ticker)
    if hasattr(reader, "get"):
        return reader.get(ticker)
    raise GeneratedOutputCacheContractError(
        "Injected generated-output cache reader must expose read_generated_output_cache_records(ticker), "
        "read_asset_overview_records(ticker), read(ticker), or get(ticker)."
    )


def _asset_knowledge_pack_from_repository_records(records: KnowledgePackRepositoryRecords) -> AssetKnowledgePack:
    source_rows = sorted(
        records.source_documents,
        key=lambda row: (row.asset_ticker, row.source_rank, row.source_document_id),
    )
    source_by_id = {row.source_document_id: row for row in source_rows}
    chunk_rows = sorted(
        records.source_chunks,
        key=lambda row: (row.source_document_id, row.chunk_order, row.chunk_id),
    )

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
    for row in chunk_rows:
        if not row.stored_text:
            raise KnowledgePackRepositoryContractError(
                f"Chunk {row.chunk_id} has no persisted text for overview generation."
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

    facts = []
    for row in sorted(records.normalized_facts, key=lambda item: item.fact_id):
        if row.value is None:
            raise KnowledgePackRepositoryContractError(f"Fact {row.fact_id} has no persisted value for overview generation.")
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
                source_chunk=next(item.chunk for item in chunks if item.chunk.chunk_id == row.source_chunk_id),
            )
        )

    recent_developments = []
    for row in sorted(records.recent_developments, key=lambda item: item.event_id):
        if row.title is None or row.summary is None:
            raise KnowledgePackRepositoryContractError(
                f"Recent development {row.event_id} has no persisted title or summary for overview generation."
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
                source_chunk=next(item.chunk for item in chunks if item.chunk.chunk_id == row.source_chunk_id),
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


def _validate_generated_output_cache_for_overview(
    ticker: str,
    records: GeneratedOutputCacheRepositoryRecords,
    *,
    pack: AssetKnowledgePack,
    pack_records: KnowledgePackRepositoryRecords,
    knowledge_pack_hash: str | None,
) -> None:
    if len(records.envelopes) != 1:
        raise GeneratedOutputCacheContractError("Overview reuse requires exactly one generated-output cache envelope.")
    envelope = records.envelopes[0]
    if envelope.asset_ticker != ticker or pack.asset.ticker != ticker:
        raise GeneratedOutputCacheContractError("Overview cache and knowledge pack must bind to the requested asset.")
    if envelope.entry_kind != CacheEntryKind.asset_page.value or envelope.cache_scope != CacheScope.asset.value:
        raise GeneratedOutputCacheContractError("Overview cache records must be asset-page scoped.")
    if envelope.artifact_category != GeneratedOutputArtifactCategory.asset_overview_section.value:
        raise GeneratedOutputCacheContractError("Overview cache records must use the asset overview artifact category.")
    if envelope.output_identity != f"asset:{ticker}":
        raise GeneratedOutputCacheContractError("Overview cache output identity must match the requested asset.")
    if not envelope.cacheable or not envelope.generated_output_available:
        raise GeneratedOutputCacheContractError("Overview cache records must be cacheable and generated-output available.")

    if not pack_records.section_freshness_inputs:
        raise GeneratedOutputCacheContractError("Overview persisted pack records require section freshness labels.")
    section_freshness = [
        SectionFreshnessInput(
            section_id=row.section_id,
            freshness_state=FreshnessState(row.freshness_state),
            evidence_state=row.evidence_state,
            as_of_date=row.as_of_date,
            retrieved_at=row.retrieved_at,
        )
        for row in pack_records.section_freshness_inputs
    ]
    knowledge_input = build_knowledge_pack_freshness_input(pack, section_freshness_labels=section_freshness)
    expected_knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    if knowledge_pack_hash != expected_knowledge_hash or envelope.knowledge_pack_freshness_hash != expected_knowledge_hash:
        raise GeneratedOutputCacheContractError("Overview cache knowledge-pack freshness hash does not match current evidence.")

    pack_source_ids = {source.source_document_id for source in pack.source_documents}
    pack_citation_ids = {
        *{f"c_{item.fact.fact_id}" for item in pack.normalized_facts},
        *{f"c_{item.chunk.chunk_id}" for item in pack.source_chunks},
        *{f"c_{item.recent_development.event_id}" for item in pack.recent_developments},
    }
    if not set(envelope.source_document_ids) <= pack_source_ids:
        raise GeneratedOutputCacheContractError("Overview cache source IDs must belong to the same persisted knowledge pack.")
    if not set(envelope.citation_ids) <= pack_citation_ids:
        raise GeneratedOutputCacheContractError("Overview cache citation IDs must belong to the same persisted knowledge pack.")


def generate_overview_from_pack(
    pack: AssetKnowledgePack,
    *,
    persisted_weekly_news_reader: WeeklyNewsEventEvidenceRecordReader | Any | None = None,
) -> OverviewResponse:
    if not pack.asset.supported:
        return _unsupported_overview(pack)

    facts_by_field = {item.fact.field_name: item for item in pack.normalized_facts if item.fact.evidence_state == "supported"}
    bindings = _CitationRegistry(pack)

    identity_fact = _require_fact(facts_by_field, "canonical_asset_identity")
    identity_citation_id = bindings.for_fact(identity_fact).citation.citation_id

    snapshot = _build_snapshot(pack, facts_by_field, bindings, identity_citation_id)
    beginner_summary = _build_beginner_summary(pack, facts_by_field)
    risk_chunk = _select_risk_chunk(pack)
    risk_citation_id = bindings.for_chunk(risk_chunk).citation.citation_id
    top_risks = _build_top_risks(pack, risk_citation_id)
    recent_developments = _build_recent_developments(pack, bindings)
    weekly_news_read = read_persisted_weekly_news_focus(
        pack.asset,
        as_of=DEFAULT_WEEKLY_NEWS_AS_OF,
        persisted_event_reader=persisted_weekly_news_reader,
    )
    weekly_news_focus = (
        weekly_news_read.weekly_news_focus
        if weekly_news_read.found and weekly_news_read.weekly_news_focus is not None
        else build_weekly_news_focus_from_pack(pack, as_of=DEFAULT_WEEKLY_NEWS_AS_OF)
    )
    suitability_summary = _build_suitability_summary(pack, facts_by_field)
    sections = _build_overview_sections(
        pack=pack,
        facts_by_field=facts_by_field,
        bindings=bindings,
        top_risks=top_risks,
        recent_developments=recent_developments,
        suitability_summary=suitability_summary,
        risk_chunk=risk_chunk,
    )

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

    canonical_citation_ids = [identity_citation_id]
    ai_comprehensive_analysis = build_ai_comprehensive_analysis(
        pack.asset,
        weekly_news_focus,
        canonical_fact_citation_ids=canonical_citation_ids,
        canonical_source_document_ids=[identity_fact.source_document.source_document_id],
        minimum_weekly_news_item_count=weekly_news_read.minimum_ai_analysis_item_count,
        high_signal_weekly_news_item_count=(
            weekly_news_read.high_signal_selected_item_count if weekly_news_read.found else None
        ),
    )
    citations = bindings.citations()
    source_documents = bindings.source_documents()

    response = OverviewResponse(
        asset=pack.asset,
        state=_state_for_pack(pack),
        freshness=pack.freshness,
        snapshot=snapshot,
        beginner_summary=beginner_summary,
        top_risks=top_risks,
        recent_developments=recent_developments,
        weekly_news_focus=weekly_news_focus,
        ai_comprehensive_analysis=ai_comprehensive_analysis,
        suitability_summary=suitability_summary,
        claims=[planned.claim for planned in planned_claims],
        citations=citations,
        source_documents=source_documents,
        sections=sections,
        section_freshness_validation=[],
    )
    response = response.model_copy(
        update={
            "section_freshness_validation": build_overview_section_freshness_validation(
                overview=response,
                pack=pack,
            )
        }
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
    claims.extend(_section_validation_claims(overview))
    return validate_claims(claims, evidence, CitationValidationContext(allowed_asset_tickers=[pack.asset.ticker]))


def _maybe_write_overview_generated_output_cache(
    overview: OverviewResponse,
    pack: AssetKnowledgePack,
    writer: Any | None,
) -> None:
    if writer is None or not overview.asset.supported:
        return
    try:
        report = validate_overview_response(overview, pack)
        if not report.valid or find_forbidden_output_phrases(str(overview.model_dump(mode="json"))):
            return
        source_ids = {source.source_document_id for source in overview.source_documents}
        citations_by_source: dict[str, list[str]] = {}
        for citation in overview.citations:
            citations_by_source.setdefault(citation.source_document_id, []).append(citation.citation_id)
        section_labels = [
            SectionFreshnessInput(
                section_id=item.section_id,
                freshness_state=item.displayed_freshness_state,
                evidence_state=item.displayed_evidence_state.value,
                as_of_date=item.displayed_as_of_date,
                retrieved_at=item.displayed_retrieved_at,
            )
            for item in overview.section_freshness_validation
        ]
        knowledge_input = build_knowledge_pack_freshness_input(pack, section_freshness_labels=section_labels)
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
            cache_entry_id=f"generated-output-{overview.asset.ticker.lower()}-overview",
            output_identity=f"asset:{overview.asset.ticker}",
            mode_or_output_type="beginner-overview",
            artifact_category=GeneratedOutputArtifactCategory.asset_overview_section,
            entry_kind=CacheEntryKind.asset_page,
            scope=CacheScope.asset,
            schema_version="asset-page-v1",
            prompt_version="asset-page-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=[citation.citation_id for citation in overview.citations],
            created_at=overview.freshness.page_last_updated_at,
            ttl_seconds=604800,
            asset_ticker=overview.asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


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


def build_overview_section_freshness_validation(
    *,
    overview: OverviewResponse,
    pack: AssetKnowledgePack,
) -> list[OverviewSectionFreshnessValidation]:
    if not pack.asset.supported or overview.asset.ticker != pack.asset.ticker:
        return []

    pack_sources_by_id = {source.source_document_id: source for source in pack.source_documents}
    overview_citations = {
        citation.citation_id: citation
        for citation in [
            *overview.citations,
            *(overview.weekly_news_focus.citations if overview.weekly_news_focus else []),
        ]
    }
    overview_sources = {
        source.source_document_id: source
        for source in [
            *overview.source_documents,
            *(overview.weekly_news_focus.source_documents if overview.weekly_news_focus else []),
        ]
    }
    knowledge_inputs_by_id = {label.section_id: label for label in _section_freshness_labels(pack)}
    subjects = [
        *[_subject_from_section(section) for section in overview.sections],
        *(
            [_subject_from_weekly_news(overview, knowledge_inputs_by_id.get("weekly_news_focus"))]
            if overview.weekly_news_focus is not None
            else []
        ),
        *(
            [_subject_from_ai_analysis(overview, knowledge_inputs_by_id.get("ai_comprehensive_analysis"))]
            if overview.ai_comprehensive_analysis is not None
            else []
        ),
    ]

    validations: list[OverviewSectionFreshnessValidation] = []
    for subject in subjects:
        matched_inputs = [
            knowledge_inputs_by_id[section_id]
            for section_id in _matched_knowledge_pack_section_ids(subject, pack.asset.asset_type)
            if section_id in knowledge_inputs_by_id
        ]
        source_bindings, missing_source_ids, same_asset_sources = _source_bindings_for_subject(
            subject,
            pack_asset_ticker=pack.asset.ticker,
            pack_sources_by_id=pack_sources_by_id,
            overview_sources=overview_sources,
        )
        citation_bindings, missing_citation_ids, same_asset_citations = _citation_bindings_for_subject(
            subject,
            pack_asset_ticker=pack.asset.ticker,
            pack_sources_by_id=pack_sources_by_id,
            overview_citations=overview_citations,
        )
        validated_freshness = _validated_subject_freshness(subject, matched_inputs)
        validated_as_of_date = _validated_subject_as_of_date(subject, matched_inputs)
        validated_retrieved_at = _validated_subject_retrieved_at(subject, matched_inputs)

        mismatch_reasons: list[str] = []
        if subject.displayed_freshness_state is not validated_freshness:
            mismatch_reasons.append("displayed_freshness_state_not_supported")
        if (
            subject.displayed_as_of_date
            and validated_as_of_date
            and subject.displayed_as_of_date != validated_as_of_date
        ):
            mismatch_reasons.append("displayed_as_of_date_not_supported")
        if (
            subject.displayed_retrieved_at
            and validated_retrieved_at
            and subject.displayed_retrieved_at != validated_retrieved_at
        ):
            mismatch_reasons.append("displayed_retrieved_at_not_supported")
        if missing_source_ids:
            mismatch_reasons.append("missing_source_document_bindings")
        if missing_citation_ids:
            mismatch_reasons.append("missing_citation_bindings")
        if not same_asset_sources:
            mismatch_reasons.append("wrong_asset_source_binding")
        if not same_asset_citations:
            mismatch_reasons.append("wrong_asset_citation_binding")

        if mismatch_reasons:
            outcome = OverviewSectionFreshnessValidationOutcome.mismatch
        elif _subject_has_validation_limitations(subject):
            outcome = OverviewSectionFreshnessValidationOutcome.validated_with_limitations
        else:
            outcome = OverviewSectionFreshnessValidationOutcome.validated

        validations.append(
            OverviewSectionFreshnessValidation(
                section_id=subject.section_id,
                section_type=subject.section_type,
                displayed_freshness_state=subject.displayed_freshness_state,
                displayed_evidence_state=subject.displayed_evidence_state,
                displayed_as_of_date=subject.displayed_as_of_date,
                displayed_retrieved_at=subject.displayed_retrieved_at,
                validated_freshness_state=validated_freshness,
                validated_as_of_date=validated_as_of_date,
                validated_retrieved_at=validated_retrieved_at,
                validation_outcome=outcome,
                limitation_message=_validation_limitation_message(subject, outcome),
                mismatch_message=(
                    "Displayed freshness metadata does not match the deterministic same-asset evidence inputs."
                    if mismatch_reasons
                    else None
                ),
                citation_bindings=citation_bindings,
                source_bindings=source_bindings,
                knowledge_pack_freshness_inputs=matched_inputs,
                diagnostics=OverviewSectionFreshnessDiagnostics(
                    matched_knowledge_pack_section_ids=[item.section_id for item in matched_inputs],
                    missing_citation_ids=missing_citation_ids,
                    missing_source_document_ids=missing_source_ids,
                    mismatch_reasons=mismatch_reasons,
                    same_asset_citation_bindings_only=same_asset_citations,
                    same_asset_source_bindings_only=same_asset_sources,
                ),
            )
        )
    return validations


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
            allowlist_status=retrieved_fact.source_document.allowlist_status,
            source_use_policy=retrieved_fact.source_document.source_use_policy,
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
            allowlist_status=retrieved_chunk.source_document.allowlist_status,
            source_use_policy=retrieved_chunk.source_document.source_use_policy,
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
            allowlist_status=retrieved_recent.source_document.allowlist_status,
            source_use_policy=retrieved_recent.source_document.source_use_policy,
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
    weekly_news_focus = build_weekly_news_focus_from_pack(pack, as_of=DEFAULT_WEEKLY_NEWS_AS_OF)
    ai_comprehensive_analysis = build_ai_comprehensive_analysis(pack.asset, weekly_news_focus)
    return OverviewResponse(
        asset=pack.asset,
        state=_state_for_pack(pack),
        freshness=pack.freshness,
        snapshot={},
        beginner_summary=None,
        top_risks=[],
        recent_developments=[],
        weekly_news_focus=weekly_news_focus,
        ai_comprehensive_analysis=ai_comprehensive_analysis,
        suitability_summary=None,
        claims=[],
        citations=[],
        source_documents=[],
        sections=[],
        section_freshness_validation=[],
    )


def _subject_from_section(section: OverviewSection) -> FreshnessValidationSubject:
    supporting_freshness_states = tuple(
        [item.freshness_state for item in section.items] + [metric.freshness_state for metric in section.metrics]
    )
    supporting_as_of_dates = tuple(
        [
            *[item.as_of_date for item in section.items if item.as_of_date],
            *[metric.as_of_date for metric in section.metrics if metric.as_of_date],
        ]
    )
    supporting_retrieved_ats = tuple(
        [
            *[item.retrieved_at for item in section.items if item.retrieved_at],
            *[metric.retrieved_at for metric in section.metrics if metric.retrieved_at],
        ]
    )
    has_gap_evidence = any(
        item.evidence_state is not EvidenceState.supported or not item.source_document_ids
        for item in section.items
    ) or any(
        metric.evidence_state is not EvidenceState.supported or not metric.source_document_ids
        for metric in section.metrics
    )
    return FreshnessValidationSubject(
        section_id=section.section_id,
        section_type=section.section_type,
        displayed_freshness_state=section.freshness_state,
        displayed_evidence_state=section.evidence_state,
        displayed_as_of_date=section.as_of_date,
        displayed_retrieved_at=section.retrieved_at,
        citation_ids=tuple(section.citation_ids),
        source_document_ids=tuple(section.source_document_ids),
        supporting_freshness_states=supporting_freshness_states,
        supporting_as_of_dates=supporting_as_of_dates,
        supporting_retrieved_ats=supporting_retrieved_ats,
        has_gap_evidence=has_gap_evidence,
        limitations=section.limitations,
    )


def _subject_from_weekly_news(
    overview: OverviewResponse,
    matched_input: SectionFreshnessInput | None,
) -> FreshnessValidationSubject:
    if overview.weekly_news_focus is None:
        raise OverviewGenerationError("Weekly News Focus metadata is required for freshness validation.")

    weekly = overview.weekly_news_focus
    evidence_state = weekly.evidence_state
    supporting_freshness_states = tuple(item.freshness_state for item in weekly.items)
    supporting_as_of_dates = tuple(
        [
            weekly.window.as_of_date,
            *[item.source.as_of_date for item in weekly.items if item.source.as_of_date],
        ]
    )
    supporting_retrieved_ats = tuple(item.source.retrieved_at for item in weekly.items if item.source.retrieved_at)
    return FreshnessValidationSubject(
        section_id="weekly_news_focus",
        section_type=OverviewSectionType.weekly_news_focus,
        displayed_freshness_state=(
            supporting_freshness_states[0]
            if supporting_freshness_states
            else matched_input.freshness_state if matched_input is not None else FreshnessState.fresh
        ),
        displayed_evidence_state=evidence_state,
        displayed_as_of_date=weekly.window.as_of_date,
        displayed_retrieved_at=next(iter(supporting_retrieved_ats), None)
        or (matched_input.retrieved_at if matched_input is not None else None),
        citation_ids=tuple(citation.citation_id for citation in weekly.citations),
        source_document_ids=tuple(source.source_document_id for source in weekly.source_documents),
        supporting_freshness_states=supporting_freshness_states,
        supporting_as_of_dates=supporting_as_of_dates,
        supporting_retrieved_ats=supporting_retrieved_ats,
        has_gap_evidence=evidence_state is not EvidenceState.supported,
        limitations=weekly.empty_state.message if weekly.empty_state is not None else None,
    )


def _subject_from_ai_analysis(
    overview: OverviewResponse,
    matched_input: SectionFreshnessInput | None,
) -> FreshnessValidationSubject:
    if overview.ai_comprehensive_analysis is None:
        raise OverviewGenerationError("AI Comprehensive Analysis metadata is required for freshness validation.")

    analysis = overview.ai_comprehensive_analysis
    displayed_freshness = matched_input.freshness_state if matched_input is not None else FreshnessState.unavailable
    evidence_state = EvidenceState.supported if analysis.analysis_available else EvidenceState.insufficient_evidence
    supporting_freshness_states = (
        (matched_input.freshness_state,) if matched_input is not None else ()
    )
    supporting_as_of_dates = (
        (matched_input.as_of_date,) if matched_input is not None and matched_input.as_of_date else ()
    )
    supporting_retrieved_ats = (
        (matched_input.retrieved_at,) if matched_input is not None and matched_input.retrieved_at else ()
    )
    return FreshnessValidationSubject(
        section_id="ai_comprehensive_analysis",
        section_type=OverviewSectionType.ai_comprehensive_analysis,
        displayed_freshness_state=displayed_freshness,
        displayed_evidence_state=evidence_state,
        displayed_as_of_date=matched_input.as_of_date if matched_input is not None else None,
        displayed_retrieved_at=matched_input.retrieved_at if matched_input is not None else None,
        citation_ids=tuple(analysis.citation_ids),
        source_document_ids=tuple(analysis.source_document_ids),
        supporting_freshness_states=supporting_freshness_states,
        supporting_as_of_dates=supporting_as_of_dates,
        supporting_retrieved_ats=supporting_retrieved_ats,
        has_gap_evidence=evidence_state is not EvidenceState.supported,
        limitations=analysis.suppression_reason,
    )


def _matched_knowledge_pack_section_ids(
    subject: FreshnessValidationSubject,
    asset_type: AssetType,
) -> list[str]:
    if subject.section_type is OverviewSectionType.recent_developments:
        return ["recent_developments"]
    if subject.section_type is OverviewSectionType.weekly_news_focus:
        return ["weekly_news_focus", "recent_developments"]
    if subject.section_type is OverviewSectionType.ai_comprehensive_analysis:
        return ["ai_comprehensive_analysis", "weekly_news_focus"]

    matched: list[str] = []
    if subject.section_type in {
        OverviewSectionType.stable_facts,
        OverviewSectionType.risk,
        OverviewSectionType.educational_suitability,
    }:
        matched.append("canonical_facts")
    if asset_type is AssetType.etf and subject.section_id == "holdings_exposure":
        matched.append("holdings")
    if subject.has_gap_evidence or subject.section_type is OverviewSectionType.evidence_gap:
        matched.append("evidence_gaps")
    return matched


def _source_bindings_for_subject(
    subject: FreshnessValidationSubject,
    *,
    pack_asset_ticker: str,
    pack_sources_by_id: dict[str, SourceDocumentFixture],
    overview_sources: dict[str, SourceDocument],
) -> tuple[list[OverviewSectionFreshnessSourceBinding], list[str], bool]:
    bindings: list[OverviewSectionFreshnessSourceBinding] = []
    missing_source_ids: list[str] = []
    same_asset_sources = True
    for source_id in sorted(set(subject.source_document_ids)):
        source = overview_sources.get(source_id)
        pack_source = pack_sources_by_id.get(source_id)
        if (
            source is not None
            and pack_source is None
            and subject.section_type
            in {OverviewSectionType.weekly_news_focus, OverviewSectionType.ai_comprehensive_analysis}
        ):
            bindings.append(
                OverviewSectionFreshnessSourceBinding(
                    source_document_id=source.source_document_id,
                    asset_ticker=pack_asset_ticker,
                    source_type=source.source_type,
                    freshness_state=source.freshness_state,
                    as_of_date=source.as_of_date or source.published_at,
                    retrieved_at=source.retrieved_at,
                )
            )
            continue
        if source is None or pack_source is None:
            missing_source_ids.append(source_id)
            continue
        same_asset_sources = same_asset_sources and pack_source.asset_ticker == pack_asset_ticker
        bindings.append(
            OverviewSectionFreshnessSourceBinding(
                source_document_id=source.source_document_id,
                asset_ticker=pack_source.asset_ticker,
                source_type=source.source_type,
                freshness_state=source.freshness_state,
                as_of_date=source.as_of_date or source.published_at,
                retrieved_at=source.retrieved_at,
            )
        )
    return bindings, missing_source_ids, same_asset_sources


def _citation_bindings_for_subject(
    subject: FreshnessValidationSubject,
    *,
    pack_asset_ticker: str,
    pack_sources_by_id: dict[str, SourceDocumentFixture],
    overview_citations: dict[str, Citation],
) -> tuple[list[OverviewSectionFreshnessCitationBinding], list[str], bool]:
    bindings: list[OverviewSectionFreshnessCitationBinding] = []
    missing_citation_ids: list[str] = []
    same_asset_citations = True
    for citation_id in sorted(set(subject.citation_ids)):
        citation = overview_citations.get(citation_id)
        pack_source = pack_sources_by_id.get(citation.source_document_id) if citation is not None else None
        if (
            citation is not None
            and pack_source is None
            and subject.section_type
            in {OverviewSectionType.weekly_news_focus, OverviewSectionType.ai_comprehensive_analysis}
        ):
            bindings.append(
                OverviewSectionFreshnessCitationBinding(
                    citation_id=citation.citation_id,
                    source_document_id=citation.source_document_id,
                    asset_ticker=pack_asset_ticker,
                    freshness_state=citation.freshness_state,
                    evidence_state=subject.displayed_evidence_state,
                )
            )
            continue
        if citation is None or pack_source is None:
            missing_citation_ids.append(citation_id)
            continue
        same_asset_citations = same_asset_citations and pack_source.asset_ticker == pack_asset_ticker
        bindings.append(
            OverviewSectionFreshnessCitationBinding(
                citation_id=citation.citation_id,
                source_document_id=citation.source_document_id,
                asset_ticker=pack_source.asset_ticker,
                freshness_state=citation.freshness_state,
                evidence_state=subject.displayed_evidence_state,
            )
        )
    return bindings, missing_citation_ids, same_asset_citations


def _validated_subject_freshness(
    subject: FreshnessValidationSubject,
    matched_inputs: list[SectionFreshnessInput],
) -> FreshnessState:
    states = [
        *subject.supporting_freshness_states,
        *[item.freshness_state for item in matched_inputs if item.section_id in {"weekly_news_focus", "ai_comprehensive_analysis"}],
    ]
    if not states:
        return subject.displayed_freshness_state
    return _combined_freshness(states)


def _validated_subject_as_of_date(
    subject: FreshnessValidationSubject,
    matched_inputs: list[SectionFreshnessInput],
) -> str | None:
    return next(iter(subject.supporting_as_of_dates), None) or next(
        (item.as_of_date for item in matched_inputs if item.as_of_date),
        None,
    )


def _validated_subject_retrieved_at(
    subject: FreshnessValidationSubject,
    matched_inputs: list[SectionFreshnessInput],
) -> str | None:
    return next(iter(subject.supporting_retrieved_ats), None) or next(
        (item.retrieved_at for item in matched_inputs if item.retrieved_at),
        None,
    )


def _subject_has_validation_limitations(subject: FreshnessValidationSubject) -> bool:
    return subject.has_gap_evidence or subject.displayed_evidence_state is not EvidenceState.supported


def _validation_limitation_message(
    subject: FreshnessValidationSubject,
    outcome: OverviewSectionFreshnessValidationOutcome,
) -> str | None:
    if outcome is OverviewSectionFreshnessValidationOutcome.mismatch:
        return None
    if subject.limitations:
        return subject.limitations
    if outcome is OverviewSectionFreshnessValidationOutcome.validated_with_limitations:
        return (
            f"This section remains limited by {subject.displayed_evidence_state.value.replace('_', ' ')} same-asset evidence."
        )
    return None


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


def _build_overview_sections(
    *,
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _CitationRegistry,
    top_risks: list[RiskItem],
    recent_developments: list[RecentDevelopment],
    suitability_summary: SuitabilitySummary,
    risk_chunk: RetrievedSourceChunk,
) -> list[OverviewSection]:
    if pack.asset.asset_type is AssetType.stock:
        return _build_stock_sections(
            pack=pack,
            facts_by_field=facts_by_field,
            bindings=bindings,
            top_risks=top_risks,
            recent_developments=recent_developments,
            suitability_summary=suitability_summary,
            risk_chunk=risk_chunk,
        )
    if pack.asset.asset_type is AssetType.etf:
        return _build_etf_sections(
            pack=pack,
            facts_by_field=facts_by_field,
            bindings=bindings,
            top_risks=top_risks,
            recent_developments=recent_developments,
            suitability_summary=suitability_summary,
            risk_chunk=risk_chunk,
        )
    return []


def _build_stock_sections(
    *,
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _CitationRegistry,
    top_risks: list[RiskItem],
    recent_developments: list[RecentDevelopment],
    suitability_summary: SuitabilitySummary,
    risk_chunk: RetrievedSourceChunk,
) -> list[OverviewSection]:
    primary_business = _require_fact(facts_by_field, "primary_business")
    primary_business_binding = bindings.for_fact(primary_business)
    products_services = facts_by_field.get("products_services_detail")
    strength = facts_by_field.get("business_quality_strength")
    revenue_trend = facts_by_field.get("financial_quality_revenue_trend")
    valuation_limitation = facts_by_field.get("valuation_data_limitation")
    valuation_gap = _gap_for_field(pack, "valuation_context")
    risk_binding = bindings.for_chunk(risk_chunk)

    return [
        _section(
            section_id="business_overview",
            title="Business Overview",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=f"{pack.asset.name} is described in the local fixture as a company that sells devices, software, accessories, and services.",
            items=[
                _supported_item(
                    item_id="primary_business",
                    title="Primary business",
                    summary=str(primary_business.fact.value),
                    binding=primary_business_binding,
                    as_of_date=primary_business.fact.as_of_date,
                )
            ],
        ),
        _section(
            section_id="products_services",
            title="Products Or Services",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary="The current fixture supports a high-level split between product and services activity, but not a full segment table.",
            items=[
                _supported_item(
                    item_id="products_and_services",
                    title="Products and services",
                    summary=str(products_services.fact.value) if products_services else "The local fixture supports only high-level products and services detail.",
                    binding=bindings.for_fact(products_services) if products_services else bindings.for_fact(primary_business),
                    as_of_date=products_services.fact.as_of_date if products_services else primary_business.fact.as_of_date,
                ),
                _gap_item(
                    item_id="business_segments",
                    title="Business segments",
                    summary="The local fixture does not include source-backed segment, revenue-driver, geographic-exposure, or competitor detail.",
                    evidence_state=EvidenceState.unknown,
                    freshness_state=FreshnessState.unknown,
                ),
            ],
            evidence_state=EvidenceState.mixed,
        ),
        _section(
            section_id="strengths",
            title="Strengths",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=(
                str(strength.fact.value)
                if strength
                else "The current local fixture does not include source-backed evidence for competitive advantages, industry tailwinds, or other strengths."
            ),
            items=[
                _supported_item(
                    item_id="business_quality_strength",
                    title="Business-quality point",
                    summary=str(strength.fact.value),
                    binding=bindings.for_fact(strength),
                    as_of_date=strength.fact.as_of_date,
                )
            ]
            if strength
            else [
                _gap_item(
                    item_id="strengths_gap",
                    title="Strengths",
                    summary="The current local fixture does not include source-backed evidence for competitive advantages, industry tailwinds, or other strengths.",
                    evidence_state=EvidenceState.unknown,
                    freshness_state=FreshnessState.unknown,
                )
            ],
            evidence_state=EvidenceState.supported if strength else EvidenceState.unknown,
        ),
        _section(
            section_id="financial_quality",
            title="Financial Quality",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=(
                "The fixture supports one multi-year net sales trend, while earnings, margins, cash flow, debt, cash, ROE, and ROIC remain unavailable."
            ),
            items=([
                _supported_item(
                    item_id="net_sales_trend",
                    title="Net sales trend",
                    summary=f"The local fixture records Apple net sales moving from {revenue_trend.fact.value}.",
                    binding=bindings.for_fact(revenue_trend),
                    as_of_date=revenue_trend.fact.as_of_date,
                )
            ]
            if revenue_trend
            else [])
            + [
                _gap_item(
                    item_id="financial_quality_detail_gap",
                    title="Additional financial-quality metrics",
                    summary="The local fixture still lacks earnings, margin, cash-flow, debt, cash, ROE, and ROIC metrics.",
                    evidence_state=EvidenceState.unavailable,
                    freshness_state=FreshnessState.unavailable,
                )
            ],
            metrics=[
                _metric_for_fact("net_sales_trend", "Net sales trend", revenue_trend, bindings.for_fact(revenue_trend))
            ]
            if revenue_trend
            else [],
            evidence_state=EvidenceState.mixed if revenue_trend else EvidenceState.unavailable,
            limitations="The local fixture still lacks earnings, margin, cash-flow, debt, cash, ROE, and ROIC metrics.",
        ),
        _section(
            section_id="valuation_context",
            title="Valuation Context",
            section_type=OverviewSectionType.evidence_gap,
            applies_to=[AssetType.stock],
            beginner_summary=(
                str(valuation_limitation.fact.value)
                if valuation_limitation
                else valuation_gap.message if valuation_gap else "No local fixture evidence is available for valuation context."
            ),
            items=([
                _supported_item(
                    item_id="valuation_data_limitation",
                    title="Valuation data limitation",
                    summary=str(valuation_limitation.fact.value),
                    binding=bindings.for_fact(valuation_limitation),
                    freshness_state=valuation_limitation.fact.freshness_state,
                    as_of_date=valuation_limitation.fact.as_of_date,
                )
            ]
            if valuation_limitation
            else [])
            + [
                _gap_item(
                    item_id="valuation_metrics_gap",
                    title="Valuation metrics",
                    summary=valuation_gap.message if valuation_gap else "No local fixture evidence is available for valuation context.",
                    evidence_state=_gap_evidence_state(valuation_gap.evidence_state if valuation_gap else "missing"),
                    freshness_state=valuation_gap.freshness_state if valuation_gap else FreshnessState.unavailable,
                )
            ],
            evidence_state=EvidenceState.mixed if valuation_limitation else _gap_evidence_state(valuation_gap.evidence_state if valuation_gap else "missing"),
            freshness_state=FreshnessState.unavailable if valuation_limitation else valuation_gap.freshness_state if valuation_gap else FreshnessState.unavailable,
            limitations=valuation_gap.message if valuation_gap else None,
        ),
        _risk_section(
            applies_to=[AssetType.stock],
            top_risks=top_risks,
            risk_binding=risk_binding,
        ),
        _recent_section(pack, recent_developments, bindings),
        _section(
            section_id="educational_suitability",
            title="Educational Suitability",
            section_type=OverviewSectionType.educational_suitability,
            applies_to=[AssetType.stock],
            beginner_summary=suitability_summary.may_fit,
            items=[
                _supported_item(
                    item_id="company_specific_risk_context",
                    title="Company-specific risk context",
                    summary=f"{suitability_summary.may_not_fit} {suitability_summary.learn_next}",
                    binding=risk_binding,
                )
            ],
        ),
    ]


def _build_etf_sections(
    *,
    pack: AssetKnowledgePack,
    facts_by_field: dict[str, RetrievedFact],
    bindings: _CitationRegistry,
    top_risks: list[RiskItem],
    recent_developments: list[RecentDevelopment],
    suitability_summary: SuitabilitySummary,
    risk_chunk: RetrievedSourceChunk,
) -> list[OverviewSection]:
    benchmark = _require_fact(facts_by_field, "benchmark")
    expense_ratio = _require_fact(facts_by_field, "expense_ratio")
    holdings_count = _require_fact(facts_by_field, "holdings_count")
    beginner_role = _require_fact(facts_by_field, "beginner_role")
    holdings_exposure = facts_by_field.get("holdings_exposure_detail")
    construction_methodology = facts_by_field.get("construction_methodology")
    trading_data_limitation = facts_by_field.get("trading_data_limitation")
    benchmark_binding = bindings.for_fact(benchmark)
    expense_binding = bindings.for_fact(expense_ratio)
    holdings_binding = bindings.for_fact(holdings_count)
    role_binding = bindings.for_fact(beginner_role)
    risk_binding = bindings.for_chunk(risk_chunk)

    cost_gap_items = _cost_gap_items(pack)
    similar_assets_item = _similar_assets_gap_item(pack)

    return [
        _section(
            section_id="fund_objective_role",
            title="Fund Objective Or Role",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary=f"{pack.asset.ticker} seeks to track {benchmark.fact.value} and is represented as {str(beginner_role.fact.value).lower()} in the local fixture.",
            items=[
                _supported_item(
                    item_id="benchmark",
                    title="Benchmark",
                    summary=f"The fund seeks to track {benchmark.fact.value}.",
                    binding=benchmark_binding,
                    as_of_date=benchmark.fact.as_of_date,
                ),
                _supported_item(
                    item_id="beginner_role",
                    title="Beginner role",
                    summary=str(beginner_role.fact.value),
                    binding=role_binding,
                    as_of_date=beginner_role.fact.as_of_date,
                ),
            ],
            metrics=[
                _metric_for_fact("benchmark", "Benchmark", benchmark, benchmark_binding),
            ],
        ),
        _section(
            section_id="holdings_exposure",
            title="Holdings Or Exposure",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary=(
                f"The local fixture records about {holdings_count.fact.value} holdings and includes a bounded top-holdings exposure note, "
                "but sector, country, concentration, and largest-position data remain incomplete."
            ),
            items=[
                _supported_item(
                    item_id="holdings_count",
                    title="Holdings count",
                    summary=f"The local fixture records about {holdings_count.fact.value} holdings.",
                    binding=holdings_binding,
                    as_of_date=holdings_count.fact.as_of_date,
                ),
                *(
                    [
                        _supported_item(
                            item_id="holdings_exposure_detail",
                            title="Holdings exposure detail",
                            summary=str(holdings_exposure.fact.value),
                            binding=bindings.for_fact(holdings_exposure),
                            as_of_date=holdings_exposure.fact.as_of_date,
                        )
                    ]
                    if holdings_exposure
                    else []
                ),
                _gap_item(
                    item_id="holdings_detail_gap",
                    title="Remaining holdings and exposure gaps",
                    summary="The current local fixture does not include top-10 weights, top-10 concentration, sector exposure, country exposure, or largest-position data.",
                    evidence_state=EvidenceState.unavailable,
                    freshness_state=FreshnessState.unavailable,
                ),
            ],
            metrics=[_metric_for_fact("holdings_count", "Holdings count", holdings_count, holdings_binding)],
            evidence_state=EvidenceState.mixed,
        ),
        _section(
            section_id="construction_methodology",
            title="Construction Or Methodology",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary="The local fixture supports index-tracking and construction context, but not full rebalancing or screening-rule detail.",
            items=[
                _supported_item(
                    item_id="index_tracking",
                    title="Index tracking",
                    summary=f"{pack.asset.ticker} seeks to track {benchmark.fact.value}.",
                    binding=benchmark_binding,
                    as_of_date=benchmark.fact.as_of_date,
                ),
                *(
                    [
                        _supported_item(
                            item_id="construction_methodology",
                            title="Construction methodology",
                            summary=str(construction_methodology.fact.value),
                            binding=bindings.for_fact(construction_methodology),
                            as_of_date=construction_methodology.fact.as_of_date,
                        )
                    ]
                    if construction_methodology
                    else []
                ),
                _gap_item(
                    item_id="methodology_detail_gap",
                    title="Remaining methodology details",
                    summary="The current local fixture does not include rebalancing frequency, complete screening rules, or full methodology evidence.",
                    evidence_state=EvidenceState.unavailable,
                    freshness_state=FreshnessState.unavailable,
                ),
            ],
            evidence_state=EvidenceState.mixed,
        ),
        _section(
            section_id="cost_trading_context",
            title="Cost And Trading Context",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary="Expense ratio is supported by the local fixture; unavailable trading metrics are called out as cited limitations.",
            items=[
                _supported_item(
                    item_id="expense_ratio",
                    title="Expense ratio",
                    summary=f"The local fixture records a {_format_metric(expense_ratio.fact.value, expense_ratio.fact.unit)} expense ratio.",
                    binding=expense_binding,
                    as_of_date=expense_ratio.fact.as_of_date,
                ),
                *(
                    [
                        _supported_item(
                            item_id="trading_data_limitation",
                            title="Trading-data limitation",
                            summary=str(trading_data_limitation.fact.value),
                            binding=bindings.for_fact(trading_data_limitation),
                            freshness_state=trading_data_limitation.fact.freshness_state,
                            as_of_date=trading_data_limitation.fact.as_of_date,
                        )
                    ]
                    if trading_data_limitation
                    else []
                ),
                *cost_gap_items,
            ],
            metrics=[_metric_for_fact("expense_ratio", "Expense ratio", expense_ratio, expense_binding)],
            evidence_state=EvidenceState.mixed if cost_gap_items else EvidenceState.supported,
        ),
        _risk_section(
            applies_to=[AssetType.etf],
            top_risks=top_risks,
            risk_binding=risk_binding,
        ),
        _section(
            section_id="similar_assets_alternatives",
            title="Similar Assets Or Simpler Alternatives",
            section_type=OverviewSectionType.evidence_gap,
            applies_to=[AssetType.etf],
            beginner_summary=similar_assets_item.summary,
            items=[similar_assets_item],
            evidence_state=similar_assets_item.evidence_state,
            freshness_state=similar_assets_item.freshness_state,
            limitations=similar_assets_item.limitations,
        ),
        _recent_section(pack, recent_developments, bindings),
        _section(
            section_id="educational_suitability",
            title="Educational Suitability",
            section_type=OverviewSectionType.educational_suitability,
            applies_to=[AssetType.etf],
            beginner_summary=suitability_summary.may_fit,
            items=[
                _supported_item(
                    item_id="risk_and_role_context",
                    title="Risk and role context",
                    summary=f"{suitability_summary.may_not_fit} {suitability_summary.learn_next}",
                    binding=risk_binding,
                )
            ],
        ),
    ]


def _risk_section(
    *,
    applies_to: list[AssetType],
    top_risks: list[RiskItem],
    risk_binding: CitationBinding,
) -> OverviewSection:
    return _section(
        section_id="top_risks" if AssetType.stock in applies_to else "etf_specific_risks",
        title="Top Risks" if AssetType.stock in applies_to else "ETF-Specific Risks",
        section_type=OverviewSectionType.risk,
        applies_to=applies_to,
        beginner_summary="Exactly three top risks are shown first for beginner readability.",
        items=[
            _supported_item(
                item_id=f"risk_{index}",
                title=risk.title,
                summary=risk.plain_english_explanation,
                binding=risk_binding,
            )
            for index, risk in enumerate(top_risks, start=1)
        ],
    )


def _recent_section(
    pack: AssetKnowledgePack,
    recent_developments: list[RecentDevelopment],
    bindings: _CitationRegistry,
) -> OverviewSection:
    items: list[OverviewSectionItem] = []
    for index, development in enumerate(recent_developments, start=1):
        recent = pack.recent_developments[index - 1]
        binding = bindings.for_recent_development(recent)
        items.append(
            _supported_item(
                item_id=f"recent_{index}",
                title=development.title,
                summary=development.summary,
                binding=binding,
                evidence_state=EvidenceState.no_major_recent_development
                if recent.recent_development.evidence_state == "no_major_recent_development"
                else EvidenceState.supported,
                freshness_state=development.freshness_state,
                event_date=development.event_date,
                as_of_date=recent.source_document.as_of_date or recent.source_document.published_at,
            )
        )

    section_state = EvidenceState.no_major_recent_development if items and all(
        item.evidence_state is EvidenceState.no_major_recent_development for item in items
    ) else EvidenceState.supported
    return _section(
        section_id="recent_developments",
        title="Recent Developments",
        section_type=OverviewSectionType.recent_developments,
        applies_to=[pack.asset.asset_type],
        beginner_summary="Recent context is kept separate from stable asset basics.",
        items=items,
        evidence_state=section_state,
    )


def _section(
    *,
    section_id: str,
    title: str,
    section_type: OverviewSectionType,
    applies_to: list[AssetType],
    beginner_summary: str | None = None,
    items: list[OverviewSectionItem] | None = None,
    metrics: list[OverviewMetric] | None = None,
    evidence_state: EvidenceState | None = None,
    freshness_state: FreshnessState | None = None,
    limitations: str | None = None,
) -> OverviewSection:
    items = items or []
    metrics = metrics or []
    citation_ids = _dedupe(
        [
            *[citation_id for item in items for citation_id in item.citation_ids],
            *[citation_id for metric in metrics for citation_id in metric.citation_ids],
        ]
    )
    source_document_ids = _dedupe(
        [
            *[source_id for item in items for source_id in item.source_document_ids],
            *[source_id for metric in metrics for source_id in metric.source_document_ids],
        ]
    )
    section_freshness = freshness_state or _section_freshness(items, metrics)
    section_evidence = evidence_state or _section_evidence(items, metrics)

    dated_items = [item for item in items if item.as_of_date or item.retrieved_at]
    dated_metrics = [metric for metric in metrics if metric.as_of_date or metric.retrieved_at]
    return OverviewSection(
        section_id=section_id,
        title=title,
        section_type=section_type,
        applies_to=applies_to,
        beginner_summary=beginner_summary,
        items=items,
        metrics=metrics,
        citation_ids=citation_ids,
        source_document_ids=source_document_ids,
        freshness_state=section_freshness,
        evidence_state=section_evidence,
        as_of_date=next((item.as_of_date for item in dated_items if item.as_of_date), None)
        or next((metric.as_of_date for metric in dated_metrics if metric.as_of_date), None),
        retrieved_at=next((item.retrieved_at for item in dated_items if item.retrieved_at), None)
        or next((metric.retrieved_at for metric in dated_metrics if metric.retrieved_at), None),
        limitations=limitations,
    )


def _gap_section(
    *,
    section_id: str,
    title: str,
    applies_to: list[AssetType],
    summary: str,
    evidence_state: EvidenceState,
    freshness_state: FreshnessState,
) -> OverviewSection:
    return _section(
        section_id=section_id,
        title=title,
        section_type=OverviewSectionType.evidence_gap,
        applies_to=applies_to,
        beginner_summary=summary,
        items=[
            _gap_item(
                item_id=f"{section_id}_gap",
                title=title,
                summary=summary,
                evidence_state=evidence_state,
                freshness_state=freshness_state,
            )
        ],
        evidence_state=evidence_state,
        freshness_state=freshness_state,
        limitations=summary,
    )


def _supported_item(
    *,
    item_id: str,
    title: str,
    summary: str,
    binding: CitationBinding,
    evidence_state: EvidenceState = EvidenceState.supported,
    freshness_state: FreshnessState | None = None,
    event_date: str | None = None,
    as_of_date: str | None = None,
) -> OverviewSectionItem:
    return OverviewSectionItem(
        item_id=item_id,
        title=title,
        summary=summary,
        citation_ids=[binding.citation.citation_id],
        source_document_ids=[binding.source_document.source_document_id],
        freshness_state=freshness_state or binding.source_document.freshness_state,
        evidence_state=evidence_state,
        event_date=event_date,
        as_of_date=as_of_date or binding.source_document.as_of_date or binding.source_document.published_at,
        retrieved_at=binding.source_document.retrieved_at,
    )


def _gap_item(
    *,
    item_id: str,
    title: str,
    summary: str,
    evidence_state: EvidenceState,
    freshness_state: FreshnessState,
) -> OverviewSectionItem:
    return OverviewSectionItem(
        item_id=item_id,
        title=title,
        summary=summary,
        citation_ids=[],
        source_document_ids=[],
        freshness_state=freshness_state,
        evidence_state=evidence_state,
        limitations=summary,
    )


def _metric_for_fact(
    metric_id: str,
    label: str,
    retrieved_fact: RetrievedFact,
    binding: CitationBinding,
) -> OverviewMetric:
    return OverviewMetric(
        metric_id=metric_id,
        label=label,
        value=retrieved_fact.fact.value,
        unit=retrieved_fact.fact.unit,
        citation_ids=[binding.citation.citation_id],
        source_document_ids=[binding.source_document.source_document_id],
        freshness_state=retrieved_fact.fact.freshness_state,
        evidence_state=EvidenceState.supported,
        as_of_date=retrieved_fact.fact.as_of_date or binding.source_document.as_of_date,
        retrieved_at=binding.source_document.retrieved_at,
    )


def _cost_gap_items(pack: AssetKnowledgePack) -> list[OverviewSectionItem]:
    items: list[OverviewSectionItem] = []
    bid_ask_gap = _gap_for_field(pack, "bid_ask_spread")
    if bid_ask_gap is not None:
        items.append(
            _gap_item(
                item_id="bid_ask_spread_gap",
                title="Bid-ask spread",
                summary=bid_ask_gap.message,
                evidence_state=_gap_evidence_state(bid_ask_gap.evidence_state),
                freshness_state=bid_ask_gap.freshness_state,
            )
        )
    else:
        items.append(
            _gap_item(
                item_id="trading_metrics_gap",
                title="Trading metrics",
                summary="The current local fixture does not include bid-ask spread, average volume, AUM, or premium/discount evidence.",
                evidence_state=EvidenceState.unavailable,
                freshness_state=FreshnessState.unavailable,
            )
        )

    stale_fee_gap = _gap_for_field(pack, "old_fee_snapshot")
    if stale_fee_gap is not None:
        items.append(
            _gap_item(
                item_id="stale_fee_snapshot_gap",
                title="Stale fee snapshot",
                summary=stale_fee_gap.message,
                evidence_state=EvidenceState.stale,
                freshness_state=stale_fee_gap.freshness_state,
            )
        )
    return items


def _similar_assets_gap_item(pack: AssetKnowledgePack) -> OverviewSectionItem:
    gap = _gap_for_field(pack, "holdings_overlap")
    if gap is not None:
        return _gap_item(
            item_id="similar_assets_gap",
            title="Similar assets and alternatives",
            summary=gap.message,
            evidence_state=_gap_evidence_state(gap.evidence_state),
            freshness_state=gap.freshness_state,
        )
    return _gap_item(
        item_id="similar_assets_gap",
        title="Similar assets and alternatives",
        summary="The current local fixture does not include asset-specific evidence for similar ETFs, simpler alternatives, or holdings overlap.",
        evidence_state=EvidenceState.unknown,
        freshness_state=FreshnessState.unknown,
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


def _section_validation_claims(overview: OverviewResponse) -> list[CitationValidationClaim]:
    claims: list[CitationValidationClaim] = []
    for section in overview.sections:
        claim_type = _claim_type_from_section(section)
        for item in section.items:
            if item.citation_ids and item.evidence_state in {
                EvidenceState.supported,
                EvidenceState.no_major_recent_development,
            }:
                claims.append(
                    CitationValidationClaim(
                        claim_id=f"section_{section.section_id}_{item.item_id}",
                        claim_text=f"{item.title}: {item.summary}",
                        claim_type=claim_type,
                        citation_ids=item.citation_ids,
                        freshness_label=item.freshness_state,
                    )
                )
        for metric in section.metrics:
            if metric.citation_ids and metric.evidence_state is EvidenceState.supported:
                formatted_value = _format_metric(metric.value, metric.unit)
                claims.append(
                    CitationValidationClaim(
                        claim_id=f"section_{section.section_id}_{metric.metric_id}",
                        claim_text=f"{metric.label}: {formatted_value}",
                        claim_type="factual",
                        citation_ids=metric.citation_ids,
                        freshness_label=metric.freshness_state,
                    )
                )
    return claims


def _claim_type_from_section(section: OverviewSection) -> str:
    if section.section_type is OverviewSectionType.risk:
        return "risk"
    if section.section_type is OverviewSectionType.recent_developments:
        return "recent"
    if section.section_type is OverviewSectionType.educational_suitability:
        return "risk"
    return "factual"


def _select_risk_chunk(pack: AssetKnowledgePack) -> RetrievedSourceChunk:
    for item in pack.source_chunks:
        if "risk" in item.chunk.supported_claim_types:
            return item
    raise OverviewGenerationError(f"No risk evidence chunk is available for {pack.asset.ticker}.")


def _select_chunk_by_id(pack: AssetKnowledgePack, chunk_id: str) -> RetrievedSourceChunk:
    for item in pack.source_chunks:
        if item.chunk.chunk_id == chunk_id:
            return item
    raise OverviewGenerationError(f"Required source chunk is missing from retrieval pack: {chunk_id}.")


def _require_fact(facts_by_field: dict[str, RetrievedFact], field_name: str) -> RetrievedFact:
    fact = facts_by_field.get(field_name)
    if fact is None:
        raise OverviewGenerationError(f"Required fact is missing from retrieval pack: {field_name}.")
    return fact


def _metric_from_fact(retrieved_fact: RetrievedFact, citation_id: str) -> MetricValue:
    return MetricValue(value=retrieved_fact.fact.value, unit=retrieved_fact.fact.unit, citation_ids=[citation_id])


def _fact_value(facts_by_field: dict[str, RetrievedFact], field_name: str) -> Any:
    return _require_fact(facts_by_field, field_name).fact.value


def _gap_for_field(pack: AssetKnowledgePack, field_name: str) -> Any | None:
    for gap in pack.evidence_gaps:
        if gap.field_name == field_name:
            return gap
    return None


def _gap_evidence_state(raw_state: str) -> EvidenceState:
    if raw_state == "missing":
        return EvidenceState.unavailable
    if raw_state == "insufficient":
        return EvidenceState.insufficient_evidence
    if raw_state == "stale":
        return EvidenceState.stale
    if raw_state == "unsupported":
        return EvidenceState.unsupported
    if raw_state == "unknown":
        return EvidenceState.unknown
    return EvidenceState.unknown


def _section_freshness(items: list[OverviewSectionItem], metrics: list[OverviewMetric]) -> FreshnessState:
    states = [item.freshness_state for item in items] + [metric.freshness_state for metric in metrics]
    if not states:
        return FreshnessState.unknown
    return _combined_freshness(states)


def _combined_freshness(states: list[FreshnessState] | tuple[FreshnessState, ...]) -> FreshnessState:
    if FreshnessState.stale in states:
        return FreshnessState.stale
    if FreshnessState.unavailable in states:
        return FreshnessState.unavailable
    if FreshnessState.unknown in states:
        return FreshnessState.unknown
    return FreshnessState.fresh


def _section_evidence(items: list[OverviewSectionItem], metrics: list[OverviewMetric]) -> EvidenceState:
    states = [item.evidence_state for item in items] + [metric.evidence_state for metric in metrics]
    if not states:
        return EvidenceState.unknown
    unique_states = set(states)
    supported_states = {EvidenceState.supported, EvidenceState.no_major_recent_development}
    if len(unique_states) == 1:
        return states[0]
    if unique_states & supported_states and unique_states - supported_states:
        return EvidenceState.mixed
    return EvidenceState.mixed


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _format_metric(value: Any, unit: str | None) -> str:
    if unit:
        return f"{value}{unit}"
    return str(value)


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
                allowlist_status=item.source_document.allowlist_status,
                source_use_policy=item.source_document.source_use_policy,
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
                allowlist_status=item.source_document.allowlist_status,
                source_use_policy=item.source_document.source_use_policy,
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
                allowlist_status=item.source_document.allowlist_status,
                source_use_policy=item.source_document.source_use_policy,
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
