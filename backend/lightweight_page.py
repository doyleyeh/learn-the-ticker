from __future__ import annotations

from typing import Any

from backend.lightweight_data_fetch import fetch_lightweight_asset_data
from backend.models import (
    AssetStatus,
    AssetType,
    BeginnerSummary,
    Citation,
    DetailsResponse,
    EvidenceState,
    FreshnessState,
    LightweightFetchFact,
    LightweightFetchResponse,
    LightweightFetchSource,
    LightweightFetchState,
    MetricValue,
    OverviewMetric,
    OverviewResponse,
    OverviewSection,
    OverviewSectionItem,
    OverviewSectionType,
    RiskItem,
    SourceDocument,
    SourceDrawerCitationBinding,
    SourceDrawerDiagnostics,
    SourceDrawerExcerpt,
    SourceDrawerRelatedClaim,
    SourceDrawerSectionReference,
    SourceDrawerSourceGroup,
    SourceDrawerState,
    SourceExportRights,
    SourceOperationPermissions,
    SourceParserStatus,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    SourcesResponse,
    StateMessage,
    SuitabilitySummary,
    WeeklyNewsContractState,
    WeeklyNewsEmptyState,
    WeeklyNewsEvidenceLimitedState,
    WeeklyNewsFocusResponse,
)
from backend.settings import LightweightDataSettings, build_lightweight_data_settings
from backend.weekly_news import build_ai_comprehensive_analysis, compute_weekly_news_window


LIGHTWEIGHT_PAGE_SCHEMA_VERSION = "lightweight-local-mvp-page-v1"


def fetch_lightweight_page_data_if_enabled(
    ticker: str,
    *,
    settings: LightweightDataSettings | None = None,
) -> LightweightFetchResponse | None:
    active_settings = settings or build_lightweight_data_settings()
    if not active_settings.can_fetch_fresh_data:
        return None
    response = fetch_lightweight_asset_data(ticker, settings=active_settings)
    if not _can_render_lightweight_page(response):
        return None
    return response


def build_lightweight_overview_response_if_enabled(ticker: str) -> OverviewResponse | None:
    response = fetch_lightweight_page_data_if_enabled(ticker)
    return build_lightweight_overview_response(response) if response is not None else None


def build_lightweight_details_response_if_enabled(ticker: str) -> DetailsResponse | None:
    response = fetch_lightweight_page_data_if_enabled(ticker)
    return build_lightweight_details_response(response) if response is not None else None


def build_lightweight_sources_response_if_enabled(
    ticker: str,
    *,
    citation_id: str | None = None,
    source_document_id: str | None = None,
) -> SourcesResponse | None:
    response = fetch_lightweight_page_data_if_enabled(ticker)
    if response is None:
        return None
    return build_lightweight_sources_response(
        response,
        citation_id=citation_id,
        source_document_id=source_document_id,
    )


def build_lightweight_overview_response(response: LightweightFetchResponse) -> OverviewResponse:
    sources = [_source_document_from_lightweight(source, response) for source in response.sources]
    citations = [
        Citation(
            citation_id=citation.citation_id,
            source_document_id=citation.source_document_id,
            title=citation.title,
            publisher=citation.publisher,
            freshness_state=citation.freshness_state,
        )
        for citation in response.citations
    ]
    default_citation_ids = [citation.citation_id for citation in citations[:1]]
    provider_citation_ids = _citation_ids_for_source_label(response, "provider_derived") or default_citation_ids
    stable_citation_ids = _preferred_citation_ids(response) or default_citation_ids
    sections = _stock_sections(response, stable_citation_ids, provider_citation_ids) if response.asset.asset_type is AssetType.stock else _etf_sections(response, stable_citation_ids, provider_citation_ids)
    claims = _claims(response, stable_citation_ids, provider_citation_ids)
    weekly_news_focus = _empty_weekly_news_focus(response)
    ai_analysis = build_ai_comprehensive_analysis(
        response.asset,
        weekly_news_focus,
        canonical_fact_citation_ids=stable_citation_ids,
        canonical_source_document_ids=[source.source_document_id for source in sources[:1]],
    )

    return OverviewResponse(
        asset=response.asset.model_copy(update={"status": AssetStatus.supported, "supported": True}),
        state=StateMessage(
            status=AssetStatus.supported,
            message=(
                "Live lightweight local-MVP data is available. Official sources are preferred and provider-derived "
                "fallbacks are labeled; this is not strict audit-quality source approval."
            ),
        ),
        freshness=response.freshness,
        snapshot=_snapshot(response, stable_citation_ids, provider_citation_ids),
        beginner_summary=_beginner_summary(response),
        top_risks=_top_risks(response, stable_citation_ids, provider_citation_ids),
        recent_developments=[],
        weekly_news_focus=weekly_news_focus,
        ai_comprehensive_analysis=ai_analysis,
        suitability_summary=_suitability_summary(response, stable_citation_ids),
        claims=claims,
        citations=citations,
        source_documents=sources,
        sections=sections,
        section_freshness_validation=[],
    )


def build_lightweight_details_response(response: LightweightFetchResponse) -> DetailsResponse:
    citation_ids = _preferred_citation_ids(response)
    provider_citation_ids = _citation_ids_for_source_label(response, "provider_derived")
    if response.asset.asset_type is AssetType.stock:
        facts: dict[str, Any] = {
            "business_model": _stock_business_model(response),
            "diversification_context": (
                f"{response.asset.ticker} is a single-company stock, so beginner research should separate the "
                "company's SEC-reported facts from broad market or ETF-basket context."
            ),
            "latest_sec_filing": _latest_filing_summary(response),
            "latest_revenue_fact": _metric_from_gaap_fact(response, "latest_revenue_fact", citation_ids),
            "latest_net_income_fact": _metric_from_gaap_fact(response, "latest_net_income_fact", citation_ids),
            "provider_market_price": _metric_from_market_price(response, provider_citation_ids),
        }
    else:
        facts = {
            "role": _etf_role(response),
            "holdings": _etf_holdings_context(response),
            "benchmark": _metric_from_etf_fact(response, "benchmark", citation_ids),
            "cost_context": _metric_from_etf_expense_ratio(response, citation_ids),
            "prospectus_reference": _etf_prospectus_reference(response, citation_ids),
            "provider_market_price": _metric_from_market_price(response, provider_citation_ids),
            "manifest_scope_signal": _etf_scope_summary(response),
        }

    return DetailsResponse(
        asset=response.asset.model_copy(update={"status": AssetStatus.supported, "supported": True}),
        state=StateMessage(
            status=AssetStatus.supported,
            message="Live lightweight details are source-labeled and may include partial or provider-derived fields.",
        ),
        freshness=response.freshness,
        facts=facts,
        citations=[
            Citation(
                citation_id=citation.citation_id,
                source_document_id=citation.source_document_id,
                title=citation.title,
                publisher=citation.publisher,
                freshness_state=citation.freshness_state,
            )
            for citation in response.citations
        ],
    )


def build_lightweight_sources_response(
    response: LightweightFetchResponse,
    *,
    citation_id: str | None = None,
    source_document_id: str | None = None,
) -> SourcesResponse:
    overview = build_lightweight_overview_response(response)
    source_groups = [_source_group(source, overview) for source in overview.source_documents]
    bindings = [_citation_binding(citation, response, overview) for citation in overview.citations]
    related_claims = _related_claims(overview)
    section_references = _section_references(overview)
    source_groups, bindings, related_claims, section_references = _filter_sources(
        source_groups,
        bindings,
        related_claims,
        section_references,
        citation_id=(citation_id or "").strip(),
        source_document_id=(source_document_id or "").strip(),
    )
    return SourcesResponse(
        schema_version="asset-source-drawer-v1",
        asset=overview.asset,
        state=overview.state,
        sources=[source for source in overview.source_documents if source.source_document_id in {group.source_document_id for group in source_groups}],
        selected_asset=overview.asset,
        drawer_state=SourceDrawerState.available if source_groups else SourceDrawerState.unavailable,
        source_groups=source_groups,
        citation_bindings=bindings,
        related_claims=related_claims,
        section_references=section_references,
        diagnostics=SourceDrawerDiagnostics(
            no_live_external_calls=response.no_live_external_calls,
            generated_output_created=True,
            filters_applied={
                key: value
                for key, value in {"citation_id": citation_id, "source_document_id": source_document_id}.items()
                if value
            },
            unavailable_reasons=[] if source_groups else ["No lightweight source matched the selected filter."],
        ),
    )


def _can_render_lightweight_page(response: LightweightFetchResponse) -> bool:
    return (
        response.generated_output_eligible
        and response.asset.supported
        and response.fetch_state in {LightweightFetchState.supported, LightweightFetchState.partial}
        and bool(response.sources)
        and bool(response.facts)
        and not response.raw_payload_exposed
    )


def _source_document_from_lightweight(source: LightweightFetchSource, response: LightweightFetchResponse) -> SourceDocument:
    return SourceDocument(
        source_document_id=source.source_document_id,
        source_type=source.source_type,
        title=source.title,
        publisher=source.publisher,
        url=source.url or "",
        published_at=source.published_at,
        as_of_date=source.as_of_date,
        retrieved_at=source.retrieved_at,
        freshness_state=source.freshness_state,
        is_official=source.is_official,
        supporting_passage=_supporting_passage(source, response),
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        permitted_operations=_permitted_operations(source.source_use_policy),
        source_identity=source.publisher,
        storage_rights=_storage_rights(source.source_use_policy),
        export_rights=_export_rights(source.source_use_policy),
        review_status=SourceReviewStatus.approved,
        approval_rationale=(
            "Official public source used by the lightweight local-MVP pipeline."
            if source.is_official
            else "Reviewed lightweight local-MVP fallback; provider-derived, source-labeled, and limited by rights policy."
        ),
        parser_status=SourceParserStatus.parsed if source.is_official else SourceParserStatus.partial,
        parser_failure_diagnostics=source.fallback_reason,
    )


def _permitted_operations(policy: SourceUsePolicy) -> SourceOperationPermissions:
    if policy is SourceUsePolicy.full_text_allowed:
        return SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=True,
            can_display_metadata=True,
            can_display_excerpt=True,
            can_summarize=True,
            can_cache=True,
            can_export_metadata=True,
            can_export_excerpt=True,
            can_export_full_text=False,
            can_support_generated_output=True,
            can_support_citations=True,
            can_support_canonical_facts=True,
            can_support_recent_developments=False,
        )
    if policy is SourceUsePolicy.summary_allowed:
        return SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=False,
            can_display_metadata=True,
            can_display_excerpt=True,
            can_summarize=True,
            can_cache=True,
            can_export_metadata=True,
            can_export_excerpt=False,
            can_export_full_text=False,
            can_support_generated_output=True,
            can_support_citations=True,
            can_support_canonical_facts=True,
            can_support_recent_developments=False,
        )
    return SourceOperationPermissions(
        can_store_metadata=True,
        can_store_raw_text=False,
        can_display_metadata=True,
        can_display_excerpt=False,
        can_summarize=False,
        can_cache=False,
        can_export_metadata=True,
        can_export_excerpt=False,
        can_export_full_text=False,
        can_support_generated_output=True,
        can_support_citations=True,
        can_support_canonical_facts=False,
        can_support_recent_developments=False,
    )


def _storage_rights(policy: SourceUsePolicy) -> SourceStorageRights:
    if policy is SourceUsePolicy.full_text_allowed:
        return SourceStorageRights.raw_snapshot_allowed
    if policy is SourceUsePolicy.summary_allowed:
        return SourceStorageRights.summary_allowed
    if policy is SourceUsePolicy.link_only:
        return SourceStorageRights.link_only
    return SourceStorageRights.metadata_only


def _export_rights(policy: SourceUsePolicy) -> SourceExportRights:
    if policy is SourceUsePolicy.full_text_allowed:
        return SourceExportRights.excerpts_allowed
    if policy is SourceUsePolicy.summary_allowed:
        return SourceExportRights.metadata_only
    if policy is SourceUsePolicy.link_only:
        return SourceExportRights.link_only
    return SourceExportRights.metadata_only


def _supporting_passage(source: LightweightFetchSource, response: LightweightFetchResponse) -> str:
    facts = [fact for fact in response.facts if source.source_document_id in fact.source_document_ids]
    if facts:
        first = facts[0]
        return f"{first.field_name}: {_short_value(first.value)}"
    return source.fallback_reason or source.rights_note


def _beginner_summary(response: LightweightFetchResponse) -> BeginnerSummary:
    if response.asset.asset_type is AssetType.stock:
        return BeginnerSummary(
            what_it_is=(
                f"{response.asset.name} ({response.asset.ticker}) is a U.S.-listed common stock resolved through "
                "the lightweight SEC-first fetch pipeline."
            ),
            why_people_consider_it=(
                "Beginners may study it to understand a single company's SEC filings, reported financial facts, "
                "and current provider-labeled market-reference context."
            ),
            main_catch=(
                "A stock is one company, so the page separates source-backed company facts from provider-derived "
                "market reference data and does not make buy, sell, hold, or allocation recommendations."
            ),
        )
    if _has_official_etf_issuer_evidence(response):
        return BeginnerSummary(
            what_it_is=(
                f"{response.asset.name} ({response.asset.ticker}) is a U.S.-listed ETF with deterministic official "
                "issuer evidence in the lightweight local-MVP fetch pipeline."
            ),
            why_people_consider_it=(
                "Beginners may study it to understand the fund's benchmark, cost, holdings or exposure examples, "
                "and separately labeled provider market-reference context."
            ),
            main_catch=(
                "Issuer facts are point-in-time and do not make the ETF suitable for any specific person; provider-derived "
                "fields stay separately labeled and complex products remain blocked."
            ),
        )
    return BeginnerSummary(
        what_it_is=(
            f"{response.asset.name} ({response.asset.ticker}) is a U.S.-listed ETF rendered through the "
            "lightweight local-MVP fetch pipeline."
        ),
        why_people_consider_it=(
            "Beginners may study it to understand the fund's role, broad scope, current market-reference context, "
            "and where issuer evidence is still partial."
        ),
        main_catch=(
            "ETF issuer holdings, fee, and methodology fields may be partial in lightweight mode; provider-derived "
            "fields are labeled and complex products remain blocked."
        ),
    )


def _top_risks(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> list[RiskItem]:
    if response.asset.asset_type is AssetType.stock:
        return [
            RiskItem(
                title="Single-company risk",
                plain_english_explanation=(
                    f"{response.asset.ticker} represents one company, so company-specific results, filings, "
                    "competition, and execution can matter a lot."
                ),
                citation_ids=stable_citation_ids,
            ),
            RiskItem(
                title="Reported results can change",
                plain_english_explanation=(
                    "SEC/XBRL facts are point-in-time reported data. Beginners should check the filing date and "
                    "period before treating any metric as current."
                ),
                citation_ids=stable_citation_ids,
            ),
            RiskItem(
                title="Market-reference data is not a recommendation",
                plain_english_explanation=(
                    "Provider-derived price fields are useful context for local testing, but they are not trading "
                    "instructions or a valuation conclusion."
                ),
                citation_ids=provider_citation_ids,
            ),
        ]
    if _has_official_etf_issuer_evidence(response):
        issuer_risk = RiskItem(
            title="Issuer facts are point-in-time",
            plain_english_explanation=(
                "Official issuer fact-sheet, prospectus, holdings, and exposure fields are dated evidence; beginners "
                "should check as-of dates before treating them as current."
            ),
            citation_ids=stable_citation_ids,
        )
    else:
        issuer_risk = RiskItem(
            title="Issuer evidence may be partial",
            plain_english_explanation=(
                "The lightweight ETF path can use manifest and provider fallback while exact issuer holdings, fee, "
                "or methodology evidence is still incomplete."
            ),
            citation_ids=stable_citation_ids,
        )
    return [
        RiskItem(
            title="Market basket risk",
            plain_english_explanation=(
                f"{response.asset.ticker} is still exposed to the market or index segment it tracks; diversification "
                "does not remove the risk of losses."
            ),
            citation_ids=stable_citation_ids,
        ),
        issuer_risk,
        RiskItem(
            title="Provider fallback limits",
            plain_english_explanation=(
                "Provider-derived ETF fields are source-labeled local-test data and should not be confused with "
                "official issuer fact sheets or prospectuses."
            ),
            citation_ids=provider_citation_ids,
        ),
    ]


def _stock_sections(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> list[OverviewSection]:
    retrieved_at = response.freshness.page_last_updated_at
    sections = [
        OverviewSection(
            section_id="business_overview",
            title="Business Overview",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=_stock_business_model(response),
            items=[
                _item(
                    "sec_identity",
                    "SEC identity",
                    _sec_identity_summary(response),
                    stable_citation_ids,
                    response,
                ),
                _item(
                    "latest_sec_filing",
                    "Latest SEC filing",
                    _latest_filing_summary(response),
                    stable_citation_ids,
                    response,
                    as_of_date=_fact_as_of(response, "latest_sec_filing"),
                ),
            ],
            metrics=_stock_metrics(response, stable_citation_ids, provider_citation_ids),
            citation_ids=stable_citation_ids,
            source_document_ids=_source_ids_for_citations(response, stable_citation_ids),
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            as_of_date=response.freshness.facts_as_of,
            retrieved_at=retrieved_at,
        ),
        OverviewSection(
            section_id="market_reference",
            title="Market Reference",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary="Provider-derived market reference fields are displayed as context, not advice.",
            items=[
                _item(
                    "provider_reference",
                    "Provider reference",
                    _provider_reference_summary(response),
                    provider_citation_ids,
                    response,
                    evidence_state=EvidenceState.partial,
                    as_of_date=_fact_as_of(response, "provider_market_price"),
                )
            ],
            metrics=[_market_metric(response, provider_citation_ids)],
            citation_ids=provider_citation_ids,
            source_document_ids=_source_ids_for_citations(response, provider_citation_ids),
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.partial,
            as_of_date=_fact_as_of(response, "provider_market_price"),
            retrieved_at=retrieved_at,
            limitations="Provider-derived market reference is not official company evidence.",
        ),
    ]
    return [*sections, *_gap_sections(response)]


def _etf_sections(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> list[OverviewSection]:
    retrieved_at = response.freshness.page_last_updated_at
    has_issuer = _has_official_etf_issuer_evidence(response)
    issuer_state = EvidenceState.supported if has_issuer else EvidenceState.partial
    holdings_state = EvidenceState.supported if _has_official_etf_holdings_evidence(response) else EvidenceState.partial
    expense_metric = _expense_ratio_metric(response, stable_citation_ids)
    return [
        OverviewSection(
            section_id="fund_objective_role",
            title="Fund Objective And Role",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary=_etf_role(response),
            items=[
                _item(
                    "etf_scope_signal",
                    "Lightweight scope signal",
                    _etf_scope_summary(response),
                    stable_citation_ids,
                    response,
                    evidence_state=issuer_state,
                ),
                _item(
                    "etf_benchmark",
                    "Benchmark",
                    _etf_benchmark_summary(response),
                    stable_citation_ids,
                    response,
                    evidence_state=EvidenceState.supported if _fact(response, "benchmark") else EvidenceState.unavailable,
                    as_of_date=_fact_as_of(response, "benchmark"),
                )
            ],
            metrics=[],
            citation_ids=stable_citation_ids,
            source_document_ids=_source_ids_for_citations(response, stable_citation_ids),
            freshness_state=FreshnessState.fresh,
            evidence_state=issuer_state,
            as_of_date=response.freshness.facts_as_of,
            retrieved_at=retrieved_at,
            limitations=(
                "Official issuer fixture evidence supports this local-MVP ETF row."
                if has_issuer
                else "Manifest/scope metadata is enough for local MVP rendering but not strict issuer evidence."
            ),
        ),
        OverviewSection(
            section_id="holdings_exposure",
            title="Holdings And Exposure",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary=" ".join(_etf_holdings_context(response)),
            items=[
                _item(
                    "holdings_status",
                    "Holdings status",
                    "; ".join(_etf_holdings_context(response)),
                    stable_citation_ids,
                    response,
                    evidence_state=holdings_state,
                    as_of_date=response.freshness.holdings_as_of or response.freshness.facts_as_of,
                    limitations=(
                        "Official issuer holdings or exposure fixture metadata supports this section."
                        if holdings_state is EvidenceState.supported
                        else "Full issuer holdings are unavailable in this lightweight response."
                    ),
                )
            ],
            metrics=[],
            citation_ids=stable_citation_ids,
            source_document_ids=_source_ids_for_citations(response, stable_citation_ids),
            freshness_state=FreshnessState.fresh,
            evidence_state=holdings_state,
            as_of_date=response.freshness.holdings_as_of or response.freshness.facts_as_of,
            retrieved_at=retrieved_at,
            limitations=(
                "Official issuer holdings or exposure fixture metadata is present."
                if holdings_state is EvidenceState.supported
                else "Full issuer holdings are unavailable in this lightweight response."
            ),
        ),
        OverviewSection(
            section_id="cost_trading_context",
            title="Cost And Trading Context",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary=(
                "Official issuer expense-ratio evidence is shown when available; provider-derived market fields "
                "remain separate local-test context."
            ),
            items=[
                _item(
                    "provider_reference",
                    "Provider reference",
                    _provider_reference_summary(response),
                    provider_citation_ids,
                    response,
                    evidence_state=EvidenceState.partial,
                    as_of_date=_fact_as_of(response, "provider_market_price"),
                )
            ],
            metrics=[
                _market_metric(response, provider_citation_ids),
                expense_metric,
            ],
            citation_ids=[*provider_citation_ids, *stable_citation_ids],
            source_document_ids=_source_ids_for_citations(response, [*provider_citation_ids, *stable_citation_ids]),
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.partial,
            as_of_date=_fact_as_of(response, "provider_market_price"),
            retrieved_at=retrieved_at,
            limitations="Provider-derived market reference is not official issuer evidence.",
        ),
        *_gap_sections(response),
    ]


def _gap_sections(response: LightweightFetchResponse) -> list[OverviewSection]:
    if not response.gaps:
        return []
    return [
        OverviewSection(
            section_id="lightweight_evidence_gaps",
            title="Evidence Gaps",
            section_type=OverviewSectionType.evidence_gap,
            applies_to=[response.asset.asset_type],
            beginner_summary="These fields were not fully verified by the lightweight fetch pipeline.",
            items=[
                OverviewSectionItem(
                    item_id=gap.field_name,
                    title=gap.field_name.replace("_", " ").title(),
                    summary=str(gap.value),
                    citation_ids=[],
                    source_document_ids=[],
                    freshness_state=FreshnessState.unavailable,
                    evidence_state=EvidenceState.partial,
                    as_of_date=gap.as_of_date,
                    retrieved_at=gap.retrieved_at,
                    limitations=gap.limitations,
                )
                for gap in response.gaps
            ],
            metrics=[],
            citation_ids=[],
            source_document_ids=[],
            freshness_state=FreshnessState.unavailable,
            evidence_state=EvidenceState.partial,
            retrieved_at=response.freshness.page_last_updated_at,
        )
    ]


def _item(
    item_id: str,
    title: str,
    summary: str,
    citation_ids: list[str],
    response: LightweightFetchResponse,
    *,
    evidence_state: EvidenceState = EvidenceState.supported,
    as_of_date: str | None = None,
    limitations: str | None = None,
) -> OverviewSectionItem:
    return OverviewSectionItem(
        item_id=item_id,
        title=title,
        summary=summary,
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh if evidence_state is not EvidenceState.unavailable else FreshnessState.unavailable,
        evidence_state=evidence_state,
        as_of_date=as_of_date or response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=limitations,
    )


def _stock_metrics(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> list[OverviewMetric]:
    metrics: list[OverviewMetric] = []
    for field_name, label in (
        ("latest_revenue_fact", "Latest reported revenue"),
        ("latest_net_income_fact", "Latest reported net income"),
        ("latest_assets_fact", "Latest reported assets"),
    ):
        value = _fact_value(response, field_name)
        if isinstance(value, dict) and value.get("value") is not None:
            metrics.append(
                OverviewMetric(
                    metric_id=field_name,
                    label=label,
                    value=value.get("value"),
                    unit=value.get("unit"),
                    citation_ids=stable_citation_ids,
                    source_document_ids=_source_ids_for_citations(response, stable_citation_ids),
                    freshness_state=FreshnessState.fresh,
                    evidence_state=EvidenceState.supported,
                    as_of_date=value.get("end"),
                    retrieved_at=response.freshness.page_last_updated_at,
                )
            )
    metrics.append(_market_metric(response, provider_citation_ids))
    return metrics


def _market_metric(response: LightweightFetchResponse, citation_ids: list[str]) -> OverviewMetric:
    metric = _metric_from_market_price(response, citation_ids)
    return OverviewMetric(
        metric_id="provider_market_price",
        label="Provider market price",
        value=metric.value,
        unit=metric.unit,
        citation_ids=metric.citation_ids,
        source_document_ids=_source_ids_for_citations(response, metric.citation_ids),
        freshness_state=FreshnessState.fresh if metric.value not in (None, "Unavailable") else FreshnessState.unavailable,
        evidence_state=EvidenceState.partial if metric.value not in (None, "Unavailable") else EvidenceState.unavailable,
        as_of_date=_fact_as_of(response, "provider_market_price"),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="Provider-derived local-test market reference, not trading advice.",
    )


def _expense_ratio_metric(response: LightweightFetchResponse, citation_ids: list[str]) -> OverviewMetric:
    metric = _metric_from_etf_expense_ratio(response, citation_ids)
    supported = metric.value not in (None, "Unavailable")
    return OverviewMetric(
        metric_id="expense_ratio",
        label="Expense ratio",
        value=metric.value,
        unit=metric.unit,
        citation_ids=metric.citation_ids,
        source_document_ids=_source_ids_for_citations(response, metric.citation_ids),
        freshness_state=FreshnessState.fresh if supported else FreshnessState.unavailable,
        evidence_state=EvidenceState.supported if supported else EvidenceState.unavailable,
        as_of_date=_fact_as_of(response, "expense_ratio"),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=(
            "Official issuer fact-sheet fixture evidence."
            if supported
            else "Expense ratio requires issuer evidence or another reviewed provider field."
        ),
    )


def _metric_from_market_price(response: LightweightFetchResponse, citation_ids: list[str]) -> MetricValue:
    value = _fact_value(response, "provider_market_price")
    if isinstance(value, dict):
        price = value.get("regularMarketPrice") or value.get("chartPreviousClose")
        if price is not None:
            return MetricValue(value=price, unit=value.get("currency"), citation_ids=citation_ids)
    return MetricValue(value="Unavailable", unit=None, citation_ids=citation_ids)


def _metric_from_etf_expense_ratio(response: LightweightFetchResponse, citation_ids: list[str]) -> MetricValue:
    value = _fact_value(response, "expense_ratio")
    if value is not None:
        return MetricValue(value=value, unit="%", citation_ids=citation_ids)
    return MetricValue(value="Unavailable", unit=None, citation_ids=citation_ids)


def _metric_from_etf_fact(
    response: LightweightFetchResponse,
    field_name: str,
    citation_ids: list[str],
) -> MetricValue:
    value = _fact_value(response, field_name)
    if value is not None:
        return MetricValue(value=value, unit=None, citation_ids=citation_ids)
    return MetricValue(value="Unavailable", unit=None, citation_ids=citation_ids)


def _metric_from_gaap_fact(response: LightweightFetchResponse, field_name: str, citation_ids: list[str]) -> MetricValue:
    value = _fact_value(response, field_name)
    if isinstance(value, dict) and value.get("value") is not None:
        return MetricValue(value=value.get("value"), unit=value.get("unit"), citation_ids=citation_ids)
    return MetricValue(value="Unavailable", unit=None, citation_ids=citation_ids)


def _snapshot(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> dict[str, MetricValue | str | int | float | None]:
    source_labels = sorted({source.source_label.value for source in response.sources})
    snapshot: dict[str, MetricValue | str | int | float | None] = {
        "data_policy_mode": response.data_policy_mode.value,
        "fetch_state": response.fetch_state.value,
        "source_labels": ", ".join(source_labels),
        "source_count": len(response.sources),
        "fact_count": len(response.facts),
        "latest_market_price": _metric_from_market_price(response, provider_citation_ids),
    }
    filing = _fact_value(response, "latest_sec_filing")
    if isinstance(filing, dict) and filing.get("form_type"):
        snapshot["latest_sec_filing"] = f"{filing.get('form_type')} filed {filing.get('filing_date') or 'unknown date'}"
    revenue = _fact_value(response, "latest_revenue_fact")
    if isinstance(revenue, dict) and revenue.get("value") is not None:
        snapshot["latest_revenue"] = MetricValue(
            value=revenue.get("value"),
            unit=revenue.get("unit"),
            citation_ids=stable_citation_ids,
        )
    benchmark = _fact_value(response, "benchmark")
    if benchmark is not None:
        snapshot["benchmark"] = MetricValue(value=benchmark, unit=None, citation_ids=stable_citation_ids)
    expense_ratio = _fact_value(response, "expense_ratio")
    if expense_ratio is not None:
        snapshot["expense_ratio"] = MetricValue(value=expense_ratio, unit="%", citation_ids=stable_citation_ids)
    holdings_count = _fact_value(response, "holdings_count")
    if holdings_count is not None:
        snapshot["holdings_count"] = MetricValue(
            value=holdings_count,
            unit="approximate holdings",
            citation_ids=stable_citation_ids,
        )
    return snapshot


def _claims(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> list[Any]:
    from backend.models import Claim

    return [
        Claim(
            claim_id="claim_lightweight_identity",
            claim_text=(
                f"{response.asset.ticker} is rendered as a supported {response.asset.asset_type.value} in "
                "the lightweight local-MVP pipeline."
            ),
            citation_ids=stable_citation_ids,
        ),
        Claim(
            claim_id="claim_lightweight_freshness",
            claim_text=(
                f"The page was refreshed at {response.freshness.page_last_updated_at}; source as-of dates may be "
                "newer, older, partial, or unavailable by section."
            ),
            citation_ids=[*stable_citation_ids, *provider_citation_ids],
        ),
        Claim(
            claim_id="claim_lightweight_source_boundary",
            claim_text=(
                "Provider-derived fallback fields are labeled and do not represent strict audit-quality source approval."
            ),
            citation_ids=provider_citation_ids or stable_citation_ids,
        ),
    ]


def _suitability_summary(response: LightweightFetchResponse, citation_ids: list[str]) -> SuitabilitySummary:
    kind = "ETF structure" if response.asset.asset_type is AssetType.etf else "single-company stock fundamentals"
    return SuitabilitySummary(
        may_fit=f"May fit a beginner learning exercise about {kind}, source labels, and freshness.",
        may_not_fit="May not fit if the user wants personalized advice, exact allocation guidance, tax advice, or trading signals.",
        learn_next=(
            "Check the source drawer, compare official and provider-derived labels, and review unavailable fields before "
            "drawing conclusions."
        ),
    )


def _empty_weekly_news_focus(response: LightweightFetchResponse) -> WeeklyNewsFocusResponse:
    window = compute_weekly_news_window(response.freshness.page_last_updated_at)
    empty_state = WeeklyNewsEmptyState(
        state=WeeklyNewsContractState.no_high_signal,
        message="Live lightweight canonical fetching is available, but Weekly News Focus is not fetched in this pipeline yet.",
        evidence_state=EvidenceState.no_high_signal,
    )
    return WeeklyNewsFocusResponse(
        asset=response.asset,
        state=WeeklyNewsContractState.no_high_signal,
        window=window,
        configured_max_item_count=8,
        selected_item_count=0,
        suppressed_candidate_count=0,
        evidence_state=EvidenceState.no_high_signal,
        evidence_limited_state=WeeklyNewsEvidenceLimitedState.empty,
        items=[],
        empty_state=empty_state,
        citations=[],
        source_documents=[],
        no_live_external_calls=response.no_live_external_calls,
    )


def _source_group(source: SourceDocument, overview: OverviewResponse) -> SourceDrawerSourceGroup:
    citation_ids = [citation.citation_id for citation in overview.citations if citation.source_document_id == source.source_document_id]
    allowed_excerpt = (
        [
            SourceDrawerExcerpt(
                excerpt_id=f"lw_excerpt_{source.source_document_id}",
                source_document_id=source.source_document_id,
                citation_id=citation_ids[0] if citation_ids else None,
                text=source.supporting_passage,
                source_use_policy=source.source_use_policy,
                allowlist_status=source.allowlist_status,
                freshness_state=source.freshness_state,
                excerpt_allowed=True,
                note="Short lightweight supporting passage; unrestricted raw payload is not exposed.",
            )
        ]
        if source.permitted_operations.can_display_excerpt
        else []
    )
    return SourceDrawerSourceGroup(
        group_id=f"group_{source.source_document_id}",
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
        permitted_operations=source.permitted_operations,
        source_identity=source.source_identity,
        storage_rights=source.storage_rights,
        export_rights=source.export_rights,
        review_status=source.review_status,
        approval_rationale=source.approval_rationale,
        parser_status=source.parser_status,
        parser_failure_diagnostics=source.parser_failure_diagnostics,
        citation_ids=citation_ids,
        related_claim_ids=[
            claim.claim_id
            for claim in overview.claims
            if any(citation_id in claim.citation_ids for citation_id in citation_ids)
        ],
        section_ids=[
            section.section_id
            for section in overview.sections
            if source.source_document_id in section.source_document_ids
        ],
        allowed_excerpts=allowed_excerpt,
        excerpt_suppression_reasons=[] if allowed_excerpt else ["source_policy_allows_metadata_only"],
    )


def _citation_binding(
    citation: Citation,
    response: LightweightFetchResponse,
    overview: OverviewResponse,
) -> SourceDrawerCitationBinding:
    source = next(source for source in overview.source_documents if source.source_document_id == citation.source_document_id)
    return SourceDrawerCitationBinding(
        citation_id=citation.citation_id,
        source_document_id=citation.source_document_id,
        asset_ticker=response.asset.ticker,
        source_type=source.source_type,
        claim_ids=[
            claim.claim_id
            for claim in overview.claims
            if citation.citation_id in claim.citation_ids
        ],
        section_ids=[
            section.section_id
            for section in overview.sections
            if citation.citation_id in section.citation_ids
        ],
        freshness_state=citation.freshness_state,
        source_use_policy=source.source_use_policy,
        allowlist_status=source.allowlist_status,
        excerpt_id=f"lw_excerpt_{source.source_document_id}" if source.permitted_operations.can_display_excerpt else None,
        evidence_layer="canonical_fact",
        supports_generated_claim=True,
    )


def _related_claims(overview: OverviewResponse) -> list[SourceDrawerRelatedClaim]:
    claims = [
        SourceDrawerRelatedClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type="lightweight_claim",
            citation_ids=claim.citation_ids,
            source_document_ids=_source_ids_for_overview_citations(overview, claim.citation_ids),
            freshness_state=_freshness_for_overview_citations(overview, claim.citation_ids),
            evidence_state=EvidenceState.supported,
        )
        for claim in overview.claims
    ]
    for section in overview.sections:
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
            )
        )
    return claims


def _section_references(overview: OverviewResponse) -> list[SourceDrawerSectionReference]:
    return [
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
        )
        for section in overview.sections
    ]


def _filter_sources(
    source_groups: list[SourceDrawerSourceGroup],
    bindings: list[SourceDrawerCitationBinding],
    related_claims: list[SourceDrawerRelatedClaim],
    section_references: list[SourceDrawerSectionReference],
    *,
    citation_id: str,
    source_document_id: str,
) -> tuple[
    list[SourceDrawerSourceGroup],
    list[SourceDrawerCitationBinding],
    list[SourceDrawerRelatedClaim],
    list[SourceDrawerSectionReference],
]:
    if citation_id:
        source_ids = {binding.source_document_id for binding in bindings if binding.citation_id == citation_id}
        source_groups = [group for group in source_groups if group.source_document_id in source_ids]
        bindings = [binding for binding in bindings if binding.citation_id == citation_id]
        related_claims = [claim for claim in related_claims if citation_id in claim.citation_ids]
        section_references = [section for section in section_references if citation_id in section.citation_ids]
    if source_document_id:
        source_groups = [group for group in source_groups if group.source_document_id == source_document_id]
        bindings = [binding for binding in bindings if binding.source_document_id == source_document_id]
        related_claims = [claim for claim in related_claims if source_document_id in claim.source_document_ids]
        section_references = [section for section in section_references if source_document_id in section.source_document_ids]
    return source_groups, bindings, related_claims, section_references


def _stock_business_model(response: LightweightFetchResponse) -> str:
    filing = _latest_filing_summary(response)
    return (
        f"SEC metadata identifies {response.asset.name} as {response.asset.ticker}"
        f"{_exchange_phrase(response)}. {filing} The lightweight page uses SEC facts first and labels provider fallback."
    )


def _sec_identity_summary(response: LightweightFetchResponse) -> str:
    identity = _fact_value(response, "sec_identity")
    if isinstance(identity, dict):
        return (
            f"SEC company metadata lists ticker {identity.get('ticker') or response.asset.ticker}, "
            f"CIK {identity.get('cik') or 'unknown'}, and exchange {identity.get('exchange') or response.asset.exchange or 'unknown'}."
        )
    return f"{response.asset.ticker} identity was resolved with lightweight source-labeled fallback."


def _latest_filing_summary(response: LightweightFetchResponse) -> str:
    filing = _fact_value(response, "latest_sec_filing")
    if isinstance(filing, dict) and filing:
        return (
            f"Latest parsed SEC filing reference is {filing.get('form_type') or 'unknown form'} filed "
            f"{filing.get('filing_date') or 'unknown filing date'} for report date "
            f"{filing.get('report_date') or 'unknown report date'}."
        )
    return "Latest SEC filing metadata is unavailable in the lightweight response."


def _provider_reference_summary(response: LightweightFetchResponse) -> str:
    reference = _fact_value(response, "provider_identity_or_market_reference")
    if isinstance(reference, dict) and reference:
        price = _fact_value(response, "provider_market_price")
        price_text = ""
        if isinstance(price, dict) and (price.get("regularMarketPrice") or price.get("chartPreviousClose")):
            price_text = (
                f" Provider price reference: {price.get('regularMarketPrice') or price.get('chartPreviousClose')} "
                f"{price.get('currency') or ''}."
            )
        return (
            f"Provider fallback identifies {reference.get('symbol') or response.asset.ticker} as "
            f"{reference.get('quoteType') or reference.get('instrumentType') or response.asset.asset_type.value} "
            f"on {reference.get('fullExchangeName') or reference.get('exchangeName') or reference.get('exchange') or 'an exchange'}."
            f"{price_text}"
        )
    return "Provider market-reference fallback is unavailable."


def _etf_role(response: LightweightFetchResponse) -> str:
    identity = _fact_value(response, "etf_identity")
    benchmark = _fact_value(response, "benchmark")
    expense_ratio = _fact_value(response, "expense_ratio")
    if isinstance(identity, dict):
        return (
            f"Official issuer fixture evidence identifies {identity.get('fund_name') or response.asset.name} as a "
            f"{identity.get('etf_classification') or 'U.S.-listed ETF'} from "
            f"{identity.get('issuer') or response.asset.issuer or 'the issuer'}"
            f"{f' tracking {benchmark}' if benchmark else ''}"
            f"{f' with an expense ratio of {expense_ratio}%' if expense_ratio is not None else ''}."
        )
    signal = _fact_value(response, "etf_manifest_scope_signal")
    if isinstance(signal, dict):
        return (
            f"{response.asset.ticker} is treated as a lightweight in-scope ETF based on local scope metadata for "
            f"{signal.get('fund_name') or response.asset.name} from {signal.get('issuer') or response.asset.issuer or 'the issuer'}."
        )
    return f"{response.asset.ticker} is treated as a lightweight ETF candidate with provider-derived context."


def _etf_scope_summary(response: LightweightFetchResponse) -> str:
    identity = _fact_value(response, "etf_identity")
    if isinstance(identity, dict):
        return (
            f"Issuer-backed support state: {identity.get('support_state')}; classification: "
            f"{identity.get('etf_classification')}; issuer: {identity.get('issuer') or response.asset.issuer or 'unknown'}."
        )
    signal = _fact_value(response, "etf_manifest_scope_signal")
    if isinstance(signal, dict):
        return (
            f"Support state: {signal.get('support_state')}; category: {signal.get('etf_category')}; "
            f"issuer: {signal.get('issuer') or response.asset.issuer or 'unknown'}."
        )
    return "ETF support/scope metadata is partial; unsupported complex products remain blocked by the fetch boundary."


def _etf_holdings_context(response: LightweightFetchResponse) -> list[str]:
    holdings_count = _fact_value(response, "holdings_count")
    holding_summaries = [
        fact.value
        for fact in response.facts
        if (
            fact.field_name.startswith("top_holding_")
            or fact.field_name.endswith("_exposure")
            or fact.field_name == "equity_exposure"
        )
    ]
    if holdings_count is not None or holding_summaries:
        lines = [
            f"Official issuer fixture evidence lists {holdings_count or 'available'} holdings or exposure metadata for {response.asset.ticker}."
        ]
        for item in holding_summaries[:3]:
            if isinstance(item, dict):
                name = item.get("name") or item.get("holding_ticker") or "exposure"
                weight = item.get("weight")
                unit = item.get("unit") or "weight"
                if weight is not None:
                    lines.append(f"{name}: {weight} {unit}.")
                else:
                    lines.append(str(name))
        return lines
    signal = _fact_value(response, "etf_manifest_scope_signal")
    issuer = response.asset.issuer or (signal.get("issuer") if isinstance(signal, dict) else None) or "issuer"
    return [
        f"{response.asset.ticker} is displayed as an ETF from {issuer}.",
        "Full issuer holdings are unavailable in the lightweight response.",
        "Use the source labels before treating any provider field as official issuer evidence.",
    ]


def _etf_benchmark_summary(response: LightweightFetchResponse) -> str:
    benchmark = _fact_value(response, "benchmark")
    if benchmark is not None:
        return f"Official issuer fact-sheet fixture metadata lists benchmark/index: {benchmark}."
    return "Benchmark is unavailable until deterministic issuer evidence is present."


def _etf_prospectus_reference(response: LightweightFetchResponse, citation_ids: list[str]) -> MetricValue:
    value = _fact_value(response, "prospectus_reference")
    if isinstance(value, dict):
        document_type = value.get("document_type") or "prospectus"
        publication_date = value.get("publication_date") or value.get("effective_date") or "unknown date"
        return MetricValue(value=f"{document_type} published {publication_date}", unit=None, citation_ids=citation_ids)
    return MetricValue(value="Unavailable", unit=None, citation_ids=citation_ids)


def _has_official_etf_issuer_evidence(response: LightweightFetchResponse) -> bool:
    if response.asset.asset_type is not AssetType.etf:
        return False
    return bool(_citation_ids_for_source_label(response, "official")) and _fact(response, "etf_fact_sheet_metadata") is not None


def _has_official_etf_holdings_evidence(response: LightweightFetchResponse) -> bool:
    if response.asset.asset_type is not AssetType.etf:
        return False
    return _fact(response, "holdings_count") is not None and any(
        fact.source_document_ids and (
            fact.field_name.startswith("top_holding_")
            or fact.field_name.endswith("_exposure")
            or fact.field_name == "equity_exposure"
        )
        for fact in response.facts
    )


def _exchange_phrase(response: LightweightFetchResponse) -> str:
    return f" on {response.asset.exchange}" if response.asset.exchange else ""


def _fact(response: LightweightFetchResponse, field_name: str) -> LightweightFetchFact | None:
    return next((fact for fact in response.facts if fact.field_name == field_name), None)


def _fact_value(response: LightweightFetchResponse, field_name: str) -> Any:
    fact = _fact(response, field_name)
    return fact.value if fact is not None else None


def _fact_as_of(response: LightweightFetchResponse, field_name: str) -> str | None:
    fact = _fact(response, field_name)
    return fact.as_of_date if fact is not None else None


def _preferred_citation_ids(response: LightweightFetchResponse) -> list[str]:
    official_ids = _citation_ids_for_source_label(response, "official")
    partial_ids = _citation_ids_for_source_label(response, "partial")
    provider_ids = _citation_ids_for_source_label(response, "provider_derived")
    return official_ids or partial_ids or provider_ids or [citation.citation_id for citation in response.citations[:1]]


def _citation_ids_for_source_label(response: LightweightFetchResponse, label: str) -> list[str]:
    source_ids = {source.source_document_id for source in response.sources if source.source_label.value == label}
    return [citation.citation_id for citation in response.citations if citation.source_document_id in source_ids]


def _source_ids_for_citations(response: LightweightFetchResponse, citation_ids: list[str]) -> list[str]:
    citation_source = {citation.citation_id: citation.source_document_id for citation in response.citations}
    return sorted({citation_source[citation_id] for citation_id in citation_ids if citation_id in citation_source})


def _source_ids_for_overview_citations(overview: OverviewResponse, citation_ids: list[str]) -> list[str]:
    citation_source = {citation.citation_id: citation.source_document_id for citation in overview.citations}
    return sorted({citation_source[citation_id] for citation_id in citation_ids if citation_id in citation_source})


def _freshness_for_overview_citations(overview: OverviewResponse, citation_ids: list[str]) -> FreshnessState:
    freshness = [citation.freshness_state for citation in overview.citations if citation.citation_id in citation_ids]
    return freshness[0] if freshness else FreshnessState.unknown


def _short_value(value: Any) -> str:
    if isinstance(value, dict):
        compact = {key: value[key] for key in list(value)[:5]}
        return ", ".join(f"{key}={item}" for key, item in compact.items())
    if isinstance(value, list):
        return "; ".join(str(item) for item in value[:3])
    text = str(value)
    return text if len(text) <= 220 else text[:217] + "..."
