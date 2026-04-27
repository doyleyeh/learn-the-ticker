from __future__ import annotations

from backend.models import (
    AssetIdentity,
    EvidenceState,
    FreshnessState,
    KnowledgePackBuildState,
    MetricValue,
    OverviewResponse,
    OverviewSectionType,
    SourceAllowlistStatus,
    SourceDocument,
    SourceDrawerCitationBinding,
    SourceDrawerDiagnostics,
    SourceDrawerExcerpt,
    SourceDrawerRelatedClaim,
    SourceDrawerSectionReference,
    SourceDrawerSourceGroup,
    SourceDrawerState,
    SourceUsePolicy,
    SourcesResponse,
    StateMessage,
)
from backend.overview import generate_asset_overview
from backend.retrieval import AssetKnowledgePack, build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.search import search_assets
from backend.source_policy import SourcePolicyAction, resolve_source_policy, validate_source_handoff


SOURCE_DRAWER_SCHEMA_VERSION = "asset-source-drawer-v1"
_RECENT_SECTION_TYPES = {
    OverviewSectionType.recent_developments,
    OverviewSectionType.weekly_news_focus,
    OverviewSectionType.ai_comprehensive_analysis,
}


def build_asset_source_drawer_response(
    ticker: str,
    *,
    citation_id: str | None = None,
    source_document_id: str | None = None,
    persisted_pack_reader: object | None = None,
    generated_output_cache_reader: object | None = None,
    persisted_weekly_news_reader: object | None = None,
) -> SourcesResponse:
    """Shape existing local overview evidence into the source drawer API contract."""

    normalized = ticker.strip().upper()
    filters = _filters(citation_id=citation_id, source_document_id=source_document_id)
    pack_result = build_asset_knowledge_pack_result(normalized, persisted_reader=persisted_pack_reader)
    if pack_result.build_state is not KnowledgePackBuildState.available:
        return _non_generated_response(
            asset=_asset_for_non_generated_state(normalized, pack_result.asset),
            state=pack_result.state,
            drawer_state=_drawer_state_for_non_generated_ticker(normalized, pack_result.build_state),
            message=pack_result.message,
            filters=filters,
        )

    pack = build_asset_knowledge_pack(normalized)
    overview = generate_asset_overview(
        normalized,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
        persisted_weekly_news_reader=persisted_weekly_news_reader,
    )
    source_fixture_by_id = {source.source_document_id: source for source in pack.source_documents}
    if not overview.asset.supported:
        return _non_generated_response(
            asset=overview.asset,
            state=overview.state,
            drawer_state=SourceDrawerState.unavailable,
            message=overview.state.message,
            filters=filters,
        )

    contexts = _related_claims_from_overview(overview)
    section_references = _section_references_from_overview(overview)
    bindings = _citation_bindings(overview, pack, contexts)

    source_groups = _source_groups(overview, pack, contexts, section_references, bindings)
    source_groups, bindings, contexts, section_references, diagnostics = _apply_filters(
        source_groups=source_groups,
        citation_bindings=bindings,
        related_claims=contexts,
        section_references=section_references,
        filters=filters,
    )

    return SourcesResponse(
        schema_version=SOURCE_DRAWER_SCHEMA_VERSION,
        asset=overview.asset,
        state=overview.state,
        sources=_filtered_legacy_sources(overview.source_documents, source_groups),
        selected_asset=overview.asset,
        drawer_state=SourceDrawerState.available if source_groups else SourceDrawerState.unavailable,
        source_groups=source_groups,
        citation_bindings=bindings,
        related_claims=contexts,
        section_references=section_references,
        diagnostics=diagnostics,
    )


def _non_generated_response(
    *,
    asset: AssetIdentity,
    state: StateMessage,
    drawer_state: SourceDrawerState,
    message: str,
    filters: dict[str, str],
) -> SourcesResponse:
    return SourcesResponse(
        schema_version=SOURCE_DRAWER_SCHEMA_VERSION,
        asset=asset,
        state=state,
        sources=[],
        selected_asset=asset,
        drawer_state=drawer_state,
        source_groups=[],
        citation_bindings=[],
        related_claims=[],
        section_references=[],
        diagnostics=SourceDrawerDiagnostics(
            filters_applied=filters,
            unavailable_reasons=[message],
        ),
    )


def _asset_for_non_generated_state(ticker: str, fallback: AssetIdentity) -> AssetIdentity:
    result = search_assets(ticker).results[0]
    return AssetIdentity(
        ticker=result.ticker,
        name=result.name,
        asset_type=result.asset_type,
        exchange=result.exchange,
        issuer=result.issuer,
        status=fallback.status,
        supported=False,
    )


def _drawer_state_for_non_generated_ticker(ticker: str, build_state: KnowledgePackBuildState) -> SourceDrawerState:
    search_status = search_assets(ticker).state.status.value
    if search_status == "out_of_scope":
        return SourceDrawerState.out_of_scope
    if build_state is KnowledgePackBuildState.eligible_not_cached:
        return SourceDrawerState.eligible_not_cached
    if build_state is KnowledgePackBuildState.unsupported:
        return SourceDrawerState.unsupported
    if build_state is KnowledgePackBuildState.unknown:
        return SourceDrawerState.unknown
    return SourceDrawerState.unavailable


def _filters(*, citation_id: str | None, source_document_id: str | None) -> dict[str, str]:
    filters: dict[str, str] = {}
    if citation_id:
        filters["citation_id"] = citation_id.strip()
    if source_document_id:
        filters["source_document_id"] = source_document_id.strip()
    return filters


def _related_claims_from_overview(overview: OverviewResponse) -> list[SourceDrawerRelatedClaim]:
    claims: list[SourceDrawerRelatedClaim] = []
    for claim in overview.claims:
        claims.append(
            SourceDrawerRelatedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                claim_type=_claim_type_from_id(claim.claim_id),
                citation_ids=claim.citation_ids,
                source_document_ids=_source_ids_for_citations(claim.citation_ids, overview),
                freshness_state=_freshness_for_citations(claim.citation_ids, overview),
                evidence_state=EvidenceState.supported,
            )
        )

    claims.extend(
        SourceDrawerRelatedClaim(
            claim_id=f"snapshot_{field_name}",
            claim_text=f"{field_name}: {_metric_value_text(value)}",
            claim_type="snapshot_metric",
            citation_ids=value.citation_ids,
            source_document_ids=_source_ids_for_citations(value.citation_ids, overview),
            section_id="snapshot",
            section_title="Snapshot",
            freshness_state=_freshness_for_citations(value.citation_ids, overview),
            evidence_state=EvidenceState.supported,
        )
        for field_name, value in overview.snapshot.items()
        if isinstance(value, MetricValue) and value.citation_ids
    )

    claims.extend(
        SourceDrawerRelatedClaim(
            claim_id=f"top_risk_{index}",
            claim_text=f"{risk.title}: {risk.plain_english_explanation}",
            claim_type="risk",
            citation_ids=risk.citation_ids,
            source_document_ids=_source_ids_for_citations(risk.citation_ids, overview),
            section_id="top_risks",
            section_title="Top Risks",
            section_type=OverviewSectionType.risk,
            freshness_state=_freshness_for_citations(risk.citation_ids, overview),
            evidence_state=EvidenceState.supported,
        )
        for index, risk in enumerate(overview.top_risks, start=1)
        if risk.citation_ids
    )

    for section in overview.sections:
        timely_context = section.section_type in _RECENT_SECTION_TYPES
        if section.citation_ids:
            claims.append(
                SourceDrawerRelatedClaim(
                    claim_id=f"section_{section.section_id}",
                    claim_text=section.beginner_summary or section.title,
                    claim_type=section.section_type.value,
                    citation_ids=section.citation_ids,
                    source_document_ids=section.source_document_ids,
                    section_id=section.section_id,
                    section_title=section.title,
                    section_type=section.section_type,
                    freshness_state=section.freshness_state,
                    evidence_state=section.evidence_state,
                    timely_context=timely_context,
                )
            )
        for item in section.items:
            if item.citation_ids:
                claims.append(
                    SourceDrawerRelatedClaim(
                        claim_id=f"{section.section_id}_{item.item_id}",
                        claim_text=f"{item.title}: {item.summary}",
                        claim_type=section.section_type.value,
                        citation_ids=item.citation_ids,
                        source_document_ids=item.source_document_ids,
                        section_id=section.section_id,
                        section_title=section.title,
                        section_type=section.section_type,
                        freshness_state=item.freshness_state,
                        evidence_state=item.evidence_state,
                        timely_context=timely_context,
                    )
                )
        for metric in section.metrics:
            if metric.citation_ids:
                claims.append(
                    SourceDrawerRelatedClaim(
                        claim_id=f"{section.section_id}_{metric.metric_id}",
                        claim_text=f"{metric.label}: {_metric_value_text(metric)}",
                        claim_type="section_metric",
                        citation_ids=metric.citation_ids,
                        source_document_ids=metric.source_document_ids,
                        section_id=section.section_id,
                        section_title=section.title,
                        section_type=section.section_type,
                        freshness_state=metric.freshness_state,
                        evidence_state=metric.evidence_state,
                        timely_context=timely_context,
                    )
                )

    if overview.weekly_news_focus:
        for item in overview.weekly_news_focus.items:
            claims.append(
                SourceDrawerRelatedClaim(
                    claim_id=f"weekly_news_{item.event_id}",
                    claim_text=f"{item.title}: {item.summary}",
                    claim_type="weekly_news_focus",
                    citation_ids=item.citation_ids,
                    source_document_ids=[item.source.source_document_id],
                    section_id="weekly_news_focus",
                    section_title="Weekly News Focus",
                    section_type=OverviewSectionType.weekly_news_focus,
                    freshness_state=item.freshness_state,
                    evidence_state=EvidenceState.supported,
                    timely_context=True,
                )
            )

    if overview.ai_comprehensive_analysis:
        for section in overview.ai_comprehensive_analysis.sections:
            if section.citation_ids:
                claims.append(
                    SourceDrawerRelatedClaim(
                        claim_id=f"ai_comprehensive_analysis_{section.section_id}",
                        claim_text=section.analysis,
                        claim_type="ai_comprehensive_analysis",
                        citation_ids=section.citation_ids,
                        source_document_ids=overview.ai_comprehensive_analysis.source_document_ids,
                        section_id="ai_comprehensive_analysis",
                        section_title=section.label,
                        section_type=OverviewSectionType.ai_comprehensive_analysis,
                        freshness_state=overview.freshness.freshness_state,
                        evidence_state=EvidenceState.supported,
                        timely_context=True,
                    )
                )
    return _dedupe_claims(claims)


def _section_references_from_overview(overview: OverviewResponse) -> list[SourceDrawerSectionReference]:
    references = [
        SourceDrawerSectionReference(
            section_id="snapshot",
            section_title="Snapshot",
            section_type=OverviewSectionType.stable_facts,
            citation_ids=sorted(
                {
                    citation_id
                    for value in overview.snapshot.values()
                    if isinstance(value, MetricValue)
                    for citation_id in value.citation_ids
                }
            ),
            source_document_ids=_source_ids_for_citations(
                [
                    citation_id
                    for value in overview.snapshot.values()
                    if isinstance(value, MetricValue)
                    for citation_id in value.citation_ids
                ],
                overview,
            ),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported,
            as_of_date=overview.freshness.facts_as_of,
            retrieved_at=overview.freshness.page_last_updated_at,
        )
    ]
    references.extend(
        SourceDrawerSectionReference(
            section_id=section.section_id,
            section_title=section.title,
            section_type=section.section_type,
            citation_ids=section.citation_ids,
            source_document_ids=section.source_document_ids,
            freshness_state=section.freshness_state,
            evidence_state=section.evidence_state,
            as_of_date=section.as_of_date,
            retrieved_at=section.retrieved_at,
            timely_context=section.section_type in _RECENT_SECTION_TYPES,
        )
        for section in overview.sections
        if section.citation_ids or section.source_document_ids
    )
    if overview.weekly_news_focus:
        references.append(
            SourceDrawerSectionReference(
                section_id="weekly_news_focus",
                section_title="Weekly News Focus",
                section_type=OverviewSectionType.weekly_news_focus,
                citation_ids=[citation.citation_id for citation in overview.weekly_news_focus.citations],
                source_document_ids=[source.source_document_id for source in overview.weekly_news_focus.source_documents],
                freshness_state=overview.freshness.freshness_state,
                evidence_state=EvidenceState.no_high_signal
                if overview.weekly_news_focus.state.value == "no_high_signal"
                else EvidenceState.supported,
                as_of_date=overview.freshness.recent_events_as_of,
                retrieved_at=overview.freshness.page_last_updated_at,
                timely_context=True,
            )
        )
    if overview.ai_comprehensive_analysis:
        references.append(
            SourceDrawerSectionReference(
                section_id="ai_comprehensive_analysis",
                section_title="AI Comprehensive Analysis",
                section_type=OverviewSectionType.ai_comprehensive_analysis,
                citation_ids=overview.ai_comprehensive_analysis.citation_ids,
                source_document_ids=overview.ai_comprehensive_analysis.source_document_ids,
                freshness_state=overview.freshness.freshness_state,
                evidence_state=EvidenceState.insufficient_evidence
                if not overview.ai_comprehensive_analysis.analysis_available
                else EvidenceState.supported,
                as_of_date=overview.freshness.recent_events_as_of,
                retrieved_at=overview.freshness.page_last_updated_at,
                timely_context=True,
            )
        )
    return [reference for reference in references if reference.citation_ids or reference.source_document_ids]


def _citation_bindings(
    overview: OverviewResponse,
    pack: AssetKnowledgePack,
    related_claims: list[SourceDrawerRelatedClaim],
) -> list[SourceDrawerCitationBinding]:
    source_by_id = {source.source_document_id: source for source in overview.source_documents}
    fact_by_citation = {f"c_{item.fact.fact_id}": item for item in pack.normalized_facts}
    chunk_by_citation = {f"c_{item.chunk.chunk_id}": item for item in pack.source_chunks}
    recent_by_citation = {f"c_{item.recent_development.event_id}": item for item in pack.recent_developments}
    claims_by_citation = _claim_ids_by_citation(related_claims)
    sections_by_citation = _section_ids_by_citation(related_claims)
    bindings: list[SourceDrawerCitationBinding] = []
    for citation in sorted(overview.citations, key=lambda item: item.citation_id):
        source = source_by_id.get(citation.source_document_id)
        if source is None:
            continue
        chunk_id: str | None = None
        evidence_layer = "unknown"
        if citation.citation_id in fact_by_citation:
            chunk_id = fact_by_citation[citation.citation_id].fact.source_chunk_id
            evidence_layer = "canonical_fact"
        elif citation.citation_id in chunk_by_citation:
            chunk_id = chunk_by_citation[citation.citation_id].chunk.chunk_id
            evidence_layer = "source_chunk"
        elif citation.citation_id in recent_by_citation:
            chunk_id = recent_by_citation[citation.citation_id].recent_development.source_chunk_id
            evidence_layer = "timely_context"
        bindings.append(
            SourceDrawerCitationBinding(
                citation_id=citation.citation_id,
                source_document_id=citation.source_document_id,
                asset_ticker=overview.asset.ticker,
                source_type=source.source_type,
                claim_ids=claims_by_citation.get(citation.citation_id, []),
                section_ids=sections_by_citation.get(citation.citation_id, []),
                chunk_id=chunk_id,
                freshness_state=citation.freshness_state,
                source_use_policy=source.source_use_policy,
                allowlist_status=source.allowlist_status,
                excerpt_id=f"excerpt_{citation.citation_id}",
                evidence_layer=evidence_layer,  # type: ignore[arg-type]
                supports_generated_claim=_supports_generated_claim(source),
            )
        )
    return bindings


def _source_groups(
    overview: OverviewResponse,
    pack: AssetKnowledgePack,
    related_claims: list[SourceDrawerRelatedClaim],
    section_references: list[SourceDrawerSectionReference],
    citation_bindings: list[SourceDrawerCitationBinding],
) -> list[SourceDrawerSourceGroup]:
    fixture_by_source_id = {source.source_document_id: source for source in pack.source_documents}
    claims_by_source = _claim_ids_by_source(related_claims)
    sections_by_source = _section_ids_by_source(section_references)
    bindings_by_source = _bindings_by_source(citation_bindings)
    groups: list[SourceDrawerSourceGroup] = []
    for source in sorted(overview.source_documents, key=lambda item: item.source_document_id):
        source_fixture = fixture_by_source_id.get(source.source_document_id)
        if source_fixture is None or source_fixture.asset_ticker != overview.asset.ticker:
            continue
        decision = resolve_source_policy(
            url=source.url,
            source_identifier=source.url if source.url.startswith("local://") else None,
        )
        handoff = validate_source_handoff(source, action=SourcePolicyAction.diagnostics)
        if not handoff.allowed:
            continue
        excerpts = [
            _drawer_excerpt(source, binding.citation_id, binding.chunk_id)
            for binding in bindings_by_source.get(source.source_document_id, [])
        ]
        suppression_reasons = sorted(
            {excerpt.suppression_reason for excerpt in excerpts if excerpt.suppression_reason}
        )
        groups.append(
            SourceDrawerSourceGroup(
                group_id=f"source_group_{source.source_document_id}",
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
                source_quality=source.source_quality,
                allowlist_status=source.allowlist_status,
                source_use_policy=source.source_use_policy,
                permitted_operations=decision.permitted_operations,
                source_identity=source.source_identity or source.url,
                storage_rights=source.storage_rights,
                export_rights=source.export_rights,
                review_status=source.review_status,
                approval_rationale=source.approval_rationale,
                parser_status=source.parser_status,
                parser_failure_diagnostics=source.parser_failure_diagnostics,
                citation_ids=[binding.citation_id for binding in bindings_by_source.get(source.source_document_id, [])],
                related_claim_ids=claims_by_source.get(source.source_document_id, []),
                section_ids=sections_by_source.get(source.source_document_id, []),
                allowed_excerpts=excerpts,
                excerpt_suppression_reasons=suppression_reasons,
            )
        )
    return groups


def _drawer_excerpt(source: SourceDocument, citation_id: str | None, chunk_id: str | None) -> SourceDrawerExcerpt:
    decision = resolve_source_policy(
        url=source.url,
        source_identifier=source.url if source.url.startswith("local://") else None,
    )
    excerpt_allowed = (
        decision.allowlist_status is SourceAllowlistStatus.allowed
        and validate_source_handoff(source, action=SourcePolicyAction.allowed_excerpt_export).allowed
        and decision.allowed_excerpt.allowed
        and decision.permitted_operations.can_display_excerpt
        and source.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
    )
    text = _short_excerpt(source.supporting_passage, decision.allowed_excerpt.max_words) if excerpt_allowed else None
    suppression_reason = None
    if not excerpt_allowed:
        suppression_reason = _suppression_reason(source.source_use_policy, source.allowlist_status)
    elif not text:
        suppression_reason = "allowed_excerpt_unavailable"
        excerpt_allowed = False
    return SourceDrawerExcerpt(
        excerpt_id=f"excerpt_{citation_id or source.source_document_id}",
        source_document_id=source.source_document_id,
        citation_id=citation_id,
        chunk_id=chunk_id,
        text=text,
        source_use_policy=source.source_use_policy,
        allowlist_status=source.allowlist_status,
        freshness_state=source.freshness_state,
        excerpt_allowed=excerpt_allowed,
        suppression_reason=suppression_reason,
        note=decision.allowed_excerpt.note,
    )


def _apply_filters(
    *,
    source_groups: list[SourceDrawerSourceGroup],
    citation_bindings: list[SourceDrawerCitationBinding],
    related_claims: list[SourceDrawerRelatedClaim],
    section_references: list[SourceDrawerSectionReference],
    filters: dict[str, str],
) -> tuple[
    list[SourceDrawerSourceGroup],
    list[SourceDrawerCitationBinding],
    list[SourceDrawerRelatedClaim],
    list[SourceDrawerSectionReference],
    SourceDrawerDiagnostics,
]:
    if not filters:
        return (
            source_groups,
            citation_bindings,
            related_claims,
            section_references,
            SourceDrawerDiagnostics(filters_applied={}),
        )

    selected_citations = {binding.citation_id for binding in citation_bindings}
    selected_sources = {group.source_document_id for group in source_groups}
    if citation_id := filters.get("citation_id"):
        selected_citations &= {citation_id}
        selected_sources &= {
            binding.source_document_id for binding in citation_bindings if binding.citation_id == citation_id
        }
    if source_document_id := filters.get("source_document_id"):
        selected_sources &= {source_document_id}
        selected_citations &= {
            binding.citation_id
            for binding in citation_bindings
            if binding.source_document_id == source_document_id
        }

    filtered_bindings = [binding for binding in citation_bindings if binding.citation_id in selected_citations]
    filtered_groups = [
        group.model_copy(
            update={
                "citation_ids": [citation for citation in group.citation_ids if citation in selected_citations],
                "allowed_excerpts": [
                    excerpt
                    for excerpt in group.allowed_excerpts
                    if excerpt.citation_id is None or excerpt.citation_id in selected_citations
                ],
            }
        )
        for group in source_groups
        if group.source_document_id in selected_sources
    ]
    selected_claims = {claim_id for binding in filtered_bindings for claim_id in binding.claim_ids}
    selected_sections = {section_id for binding in filtered_bindings for section_id in binding.section_ids}
    filtered_claims = [claim for claim in related_claims if claim.claim_id in selected_claims]
    filtered_sections = [section for section in section_references if section.section_id in selected_sections]
    diagnostics = SourceDrawerDiagnostics(
        filters_applied=filters,
        unavailable_reasons=[] if filtered_groups else ["No source drawer entries matched the requested filter."],
        omitted_source_document_ids=sorted({group.source_document_id for group in source_groups} - selected_sources),
        omitted_citation_ids=sorted({binding.citation_id for binding in citation_bindings} - selected_citations),
    )
    return filtered_groups, filtered_bindings, filtered_claims, filtered_sections, diagnostics


def _filtered_legacy_sources(
    sources: list[SourceDocument],
    source_groups: list[SourceDrawerSourceGroup],
) -> list[SourceDocument]:
    selected = {group.source_document_id for group in source_groups}
    return [source for source in sources if source.source_document_id in selected]


def _source_ids_for_citations(citation_ids: list[str], overview: OverviewResponse) -> list[str]:
    source_by_citation = {citation.citation_id: citation.source_document_id for citation in overview.citations}
    return sorted({source_by_citation[citation_id] for citation_id in citation_ids if citation_id in source_by_citation})


def _freshness_for_citations(citation_ids: list[str], overview: OverviewResponse) -> FreshnessState:
    freshness_by_citation = {citation.citation_id: citation.freshness_state for citation in overview.citations}
    states = [freshness_by_citation[citation_id] for citation_id in citation_ids if citation_id in freshness_by_citation]
    if not states:
        return FreshnessState.unavailable
    for state in [FreshnessState.unavailable, FreshnessState.unknown, FreshnessState.stale]:
        if state in states:
            return state
    return FreshnessState.fresh


def _claim_ids_by_citation(claims: list[SourceDrawerRelatedClaim]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for claim in claims:
        for citation_id in claim.citation_ids:
            mapping.setdefault(citation_id, []).append(claim.claim_id)
    return {key: sorted(set(value)) for key, value in mapping.items()}


def _section_ids_by_citation(claims: list[SourceDrawerRelatedClaim]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for claim in claims:
        if not claim.section_id:
            continue
        for citation_id in claim.citation_ids:
            mapping.setdefault(citation_id, []).append(claim.section_id)
    return {key: sorted(set(value)) for key, value in mapping.items()}


def _claim_ids_by_source(claims: list[SourceDrawerRelatedClaim]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for claim in claims:
        for source_id in claim.source_document_ids:
            mapping.setdefault(source_id, []).append(claim.claim_id)
    return {key: sorted(set(value)) for key, value in mapping.items()}


def _section_ids_by_source(references: list[SourceDrawerSectionReference]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for reference in references:
        for source_id in reference.source_document_ids:
            mapping.setdefault(source_id, []).append(reference.section_id)
    return {key: sorted(set(value)) for key, value in mapping.items()}


def _bindings_by_source(
    bindings: list[SourceDrawerCitationBinding],
) -> dict[str, list[SourceDrawerCitationBinding]]:
    mapping: dict[str, list[SourceDrawerCitationBinding]] = {}
    for binding in bindings:
        mapping.setdefault(binding.source_document_id, []).append(binding)
    return {key: sorted(value, key=lambda item: item.citation_id) for key, value in mapping.items()}


def _supports_generated_claim(source: SourceDocument) -> bool:
    return (
        source.allowlist_status is SourceAllowlistStatus.allowed
        and source.source_use_policy not in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}
        and source.permitted_operations.can_support_generated_output
        and source.permitted_operations.can_support_citations
    )


def _suppression_reason(policy: SourceUsePolicy, status: SourceAllowlistStatus) -> str:
    if status is not SourceAllowlistStatus.allowed:
        return f"allowlist_status_{status.value}"
    if policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}:
        return f"source_use_policy_{policy.value}"
    return "excerpt_not_permitted"


def _short_excerpt(text: str, max_words: int) -> str | None:
    words = text.split()
    if not words:
        return None
    if max_words and len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def _claim_type_from_id(claim_id: str) -> str:
    lowered = claim_id.lower()
    if "risk" in lowered:
        return "risk"
    if "recent" in lowered:
        return "recent"
    if "suitability" in lowered:
        return "educational_suitability"
    return "factual"


def _metric_value_text(value: Any) -> str:
    if isinstance(value, MetricValue):
        return f"{value.value}{value.unit or ''}"
    raw_value = getattr(value, "value", None)
    unit = getattr(value, "unit", None)
    return f"{raw_value}{unit or ''}"


def _dedupe_claims(claims: list[SourceDrawerRelatedClaim]) -> list[SourceDrawerRelatedClaim]:
    seen: set[str] = set()
    deduped: list[SourceDrawerRelatedClaim] = []
    for claim in claims:
        if claim.claim_id in seen:
            continue
        seen.add(claim.claim_id)
        deduped.append(claim)
    return deduped
