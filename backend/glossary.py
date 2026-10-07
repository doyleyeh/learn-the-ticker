from __future__ import annotations

from dataclasses import dataclass

from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    EvidenceState,
    FreshnessState,
    GlossaryAssetContext,
    GlossaryAssetContextState,
    GlossaryCitationBinding,
    GlossaryDiagnostics,
    GlossaryEvidenceReference,
    GlossaryEvidenceReferenceType,
    GlossaryGenericDefinition,
    GlossaryResponse,
    GlossaryResponseState,
    GlossarySourceReference,
    GlossaryTermIdentity,
    GlossaryTermResponse,
    KnowledgePackBuildState,
    SearchSupportClassification,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    StateMessage,
)
from backend.retrieval import (
    AssetKnowledgePack,
    EvidenceGap,
    RetrievedFact,
    RetrievedRecentDevelopment,
    RetrievedSourceChunk,
    SourceDocumentFixture,
    build_asset_knowledge_pack,
    build_asset_knowledge_pack_result,
)
from backend.search import search_assets
from backend.source_policy import resolve_source_policy, source_can_support_generated_output


GLOSSARY_SCHEMA_VERSION = "glossary-asset-context-v1"


@dataclass(frozen=True)
class GlossaryCatalogEntry:
    term: str
    slug: str
    beginner_category: str
    simple_definition: str
    why_it_matters: str
    common_beginner_mistake: str
    applies_to: tuple[AssetType, ...]
    aliases: tuple[str, ...] = ()
    fact_fields: tuple[str, ...] = ()
    chunk_terms: tuple[str, ...] = ()
    recent_event_types: tuple[str, ...] = ()
    gap_fields: tuple[str, ...] = ()


TERM_CATALOG: tuple[GlossaryCatalogEntry, ...] = (
    GlossaryCatalogEntry(
        term="market cap",
        slug="market-cap",
        beginner_category="stock snapshot",
        simple_definition="Market cap is the total market value of a company's common stock.",
        why_it_matters="It helps beginners understand company size and compare companies at a high level.",
        common_beginner_mistake="Treating a bigger market cap as proof that a stock is safer or better.",
        applies_to=(AssetType.stock,),
        aliases=("market capitalization",),
        fact_fields=("market_cap",),
    ),
    GlossaryCatalogEntry(
        term="revenue",
        slug="revenue",
        beginner_category="stock financial quality",
        simple_definition="Revenue is the money a company records from selling products or services before expenses.",
        why_it_matters="It shows the scale of customer demand before looking at costs and profit.",
        common_beginner_mistake="Assuming revenue growth automatically means profit growth.",
        applies_to=(AssetType.stock,),
        fact_fields=("financial_quality_revenue_trend", "revenue"),
        chunk_terms=("revenue", "net sales"),
    ),
    GlossaryCatalogEntry(
        term="operating margin",
        slug="operating-margin",
        beginner_category="stock financial quality",
        simple_definition="Operating margin compares operating income with revenue.",
        why_it_matters="It helps show how much of each sales dollar remains after normal operating costs.",
        common_beginner_mistake="Comparing operating margin across very different industries without context.",
        applies_to=(AssetType.stock,),
        fact_fields=("operating_margin",),
    ),
    GlossaryCatalogEntry(
        term="EPS",
        slug="eps",
        beginner_category="stock financial quality",
        simple_definition="EPS means earnings per share, or profit divided across shares.",
        why_it_matters="It is a common building block for valuation ratios and profit trends.",
        common_beginner_mistake="Reading one quarter of EPS as the whole business story.",
        applies_to=(AssetType.stock,),
        aliases=("earnings per share",),
        fact_fields=("eps", "diluted_eps"),
    ),
    GlossaryCatalogEntry(
        term="free cash flow",
        slug="free-cash-flow",
        beginner_category="stock financial quality",
        simple_definition="Free cash flow is cash from operations after capital spending.",
        why_it_matters="It can show how much cash a business has left for flexibility after reinvesting.",
        common_beginner_mistake="Treating free cash flow as guaranteed cash available every year.",
        applies_to=(AssetType.stock,),
        aliases=("FCF",),
        fact_fields=("free_cash_flow",),
        chunk_terms=("free-cash-flow", "free cash flow"),
    ),
    GlossaryCatalogEntry(
        term="debt",
        slug="debt",
        beginner_category="stock balance sheet",
        simple_definition="Debt is money a company has borrowed and generally must repay.",
        why_it_matters="It affects financial flexibility and can increase risk when business conditions worsen.",
        common_beginner_mistake="Assuming all debt is bad without considering cash flow and maturity timing.",
        applies_to=(AssetType.stock,),
        fact_fields=("debt", "total_debt"),
    ),
    GlossaryCatalogEntry(
        term="P/E ratio",
        slug="pe-ratio",
        beginner_category="valuation",
        simple_definition="P/E ratio compares a stock price with earnings per share.",
        why_it_matters="It is one way to understand what investors are paying for current earnings.",
        common_beginner_mistake="Calling a stock cheap or expensive from P/E alone.",
        applies_to=(AssetType.stock,),
        aliases=("price earnings ratio", "price-to-earnings ratio"),
        fact_fields=("pe_ratio", "valuation_data_limitation"),
        chunk_terms=("P/E",),
        gap_fields=("valuation_context",),
    ),
    GlossaryCatalogEntry(
        term="forward P/E",
        slug="forward-pe",
        beginner_category="valuation",
        simple_definition="Forward P/E compares price with expected future earnings.",
        why_it_matters="It shows how the market may be valuing estimated earnings, which can change.",
        common_beginner_mistake="Forgetting that forward earnings are estimates, not verified results.",
        applies_to=(AssetType.stock,),
        aliases=("forward price earnings",),
        fact_fields=("forward_pe", "valuation_data_limitation"),
        chunk_terms=("forward P/E",),
        gap_fields=("valuation_context",),
    ),
    GlossaryCatalogEntry(
        term="expense ratio",
        slug="expense-ratio",
        beginner_category="ETF cost",
        simple_definition="Expense ratio is the annual fund fee shown as a percentage of fund assets.",
        why_it_matters="Lower fees leave more of the fund's return for shareholders before other costs.",
        common_beginner_mistake="Ignoring that a low fee does not remove market risk.",
        applies_to=(AssetType.etf,),
        fact_fields=("expense_ratio",),
    ),
    GlossaryCatalogEntry(
        term="AUM",
        slug="aum",
        beginner_category="ETF size",
        simple_definition="AUM means assets under management, or how much money is in the fund.",
        why_it_matters="It can help beginners understand fund scale and trading context.",
        common_beginner_mistake="Assuming high AUM always means the fund is the right educational comparison.",
        applies_to=(AssetType.etf,),
        aliases=("assets under management",),
        fact_fields=("aum",),
    ),
    GlossaryCatalogEntry(
        term="benchmark",
        slug="benchmark",
        beginner_category="ETF objective",
        simple_definition="A benchmark is the index or reference a fund tries to track or compare against.",
        why_it_matters="It explains what the ETF is trying to represent.",
        common_beginner_mistake="Assuming two funds with similar names track the same benchmark.",
        applies_to=(AssetType.etf,),
        fact_fields=("benchmark",),
    ),
    GlossaryCatalogEntry(
        term="index",
        slug="index",
        beginner_category="ETF objective",
        simple_definition="An index is a rules-based list of securities used to represent a market segment.",
        why_it_matters="For index ETFs, the index largely determines what the fund owns.",
        common_beginner_mistake="Thinking an index ETF manager freely picks stocks each day.",
        applies_to=(AssetType.etf,),
        fact_fields=("benchmark", "construction_methodology"),
        chunk_terms=("Index", "indexing"),
    ),
    GlossaryCatalogEntry(
        term="holdings",
        slug="holdings",
        beginner_category="ETF exposure",
        simple_definition="Holdings are the securities a fund owns.",
        why_it_matters="They show what exposure a fund actually gives, beyond the fund name.",
        common_beginner_mistake="Assuming an ETF name fully explains everything inside the fund.",
        applies_to=(AssetType.etf,),
        fact_fields=("holdings_count", "holdings_exposure_detail"),
    ),
    GlossaryCatalogEntry(
        term="top 10 concentration",
        slug="top-10-concentration",
        beginner_category="ETF exposure",
        simple_definition="Top 10 concentration is how much of a fund sits in its ten largest holdings.",
        why_it_matters="It helps show whether a few companies drive a large share of results.",
        common_beginner_mistake="Counting the number of holdings without checking how heavily weighted the largest ones are.",
        applies_to=(AssetType.etf,),
        fact_fields=("top_10_concentration",),
    ),
    GlossaryCatalogEntry(
        term="sector exposure",
        slug="sector-exposure",
        beginner_category="ETF exposure",
        simple_definition="Sector exposure shows how much of a fund is tied to industries such as technology or health care.",
        why_it_matters="It helps beginners see whether a fund is broad or tilted toward certain parts of the market.",
        common_beginner_mistake="Assuming a fund is diversified just because it owns many stocks.",
        applies_to=(AssetType.etf,),
        fact_fields=("sector_exposure", "holdings_exposure_detail"),
        chunk_terms=("across sectors", "technology"),
    ),
    GlossaryCatalogEntry(
        term="country exposure",
        slug="country-exposure",
        beginner_category="ETF exposure",
        simple_definition="Country exposure shows where the fund's holdings are economically or listing-related exposed.",
        why_it_matters="It helps identify whether a fund is mainly U.S.-focused or international.",
        common_beginner_mistake="Assuming every ETF has meaningful international exposure.",
        applies_to=(AssetType.etf,),
        fact_fields=("country_exposure",),
    ),
    GlossaryCatalogEntry(
        term="bid-ask spread",
        slug="bid-ask-spread",
        beginner_category="ETF trading",
        simple_definition="Bid-ask spread is the difference between the price buyers bid and sellers ask.",
        why_it_matters="It is one trading-cost signal, especially for less liquid ETFs.",
        common_beginner_mistake="Looking only at expense ratio and ignoring trading costs.",
        applies_to=(AssetType.etf,),
        fact_fields=("bid_ask_spread", "trading_data_limitation"),
        gap_fields=("bid_ask_spread",),
    ),
    GlossaryCatalogEntry(
        term="premium/discount",
        slug="premium-discount",
        beginner_category="ETF trading",
        simple_definition="Premium or discount compares an ETF's market price with its net asset value.",
        why_it_matters="It helps show whether shares trade above or below the value of the holdings.",
        common_beginner_mistake="Assuming ETF market price always exactly equals the holdings value.",
        applies_to=(AssetType.etf,),
        aliases=("premium discount",),
        fact_fields=("premium_discount", "trading_data_limitation"),
    ),
    GlossaryCatalogEntry(
        term="NAV",
        slug="nav",
        beginner_category="ETF trading",
        simple_definition="NAV means net asset value, the value of a fund's holdings minus liabilities per share.",
        why_it_matters="It is a reference point for understanding ETF premium or discount.",
        common_beginner_mistake="Treating NAV as the same thing as the live market price.",
        applies_to=(AssetType.etf,),
        aliases=("net asset value",),
        fact_fields=("nav",),
    ),
    GlossaryCatalogEntry(
        term="liquidity",
        slug="liquidity",
        beginner_category="ETF trading",
        simple_definition="Liquidity describes how easily something can be bought or sold without a large price impact.",
        why_it_matters="For ETFs, it affects trading-cost context and how smoothly shares may trade.",
        common_beginner_mistake="Assuming all ETFs trade equally easily.",
        applies_to=(AssetType.etf,),
        fact_fields=("trading_data_limitation", "liquidity"),
        chunk_terms=("Trading context", "bid-ask spread", "average daily volume"),
    ),
    GlossaryCatalogEntry(
        term="tracking error",
        slug="tracking-error",
        beginner_category="ETF tracking",
        simple_definition="Tracking error is how much a fund's returns vary from its benchmark over time.",
        why_it_matters="It helps beginners understand how closely an ETF follows its intended index.",
        common_beginner_mistake="Assuming every index ETF tracks perfectly.",
        applies_to=(AssetType.etf,),
        fact_fields=("tracking_error", "construction_methodology"),
    ),
    GlossaryCatalogEntry(
        term="tracking difference",
        slug="tracking-difference",
        beginner_category="ETF tracking",
        simple_definition="Tracking difference is the return gap between a fund and its benchmark.",
        why_it_matters="It can reflect fees, trading, cash drag, and implementation details.",
        common_beginner_mistake="Confusing tracking difference with tracking error.",
        applies_to=(AssetType.etf,),
        fact_fields=("tracking_difference", "construction_methodology"),
    ),
    GlossaryCatalogEntry(
        term="market risk",
        slug="market-risk",
        beginner_category="risk",
        simple_definition="Market risk is the chance that broad market moves reduce the value of an investment.",
        why_it_matters="It reminds beginners that diversified funds and single stocks can still fall.",
        common_beginner_mistake="Assuming diversification removes all risk.",
        applies_to=(AssetType.stock, AssetType.etf),
        fact_fields=("company_specific_risk",),
        chunk_terms=("market risk", "stocks decline", "less diversified"),
    ),
    GlossaryCatalogEntry(
        term="concentration risk",
        slug="concentration-risk",
        beginner_category="risk",
        simple_definition="Concentration risk means a smaller set of holdings, sectors, or business drivers can matter a lot.",
        why_it_matters="It helps beginners understand why narrow exposure can move differently from broad exposure.",
        common_beginner_mistake="Counting holdings without checking weights, sectors, or single-company exposure.",
        applies_to=(AssetType.stock, AssetType.etf),
        fact_fields=("company_specific_risk", "holdings_exposure_detail"),
        chunk_terms=("less diversified", "top holdings", "concentrated"),
    ),
)


def build_glossary_response(
    ticker: str,
    *,
    term: str | None = None,
    persisted_pack_reader: object | None = None,
) -> GlossaryResponse:
    normalized = ticker.strip().upper()
    filters = _filters(term)
    pack_result = build_asset_knowledge_pack_result(normalized, persisted_reader=persisted_pack_reader)

    if pack_result.build_state is not KnowledgePackBuildState.available:
        response_state = _response_state_for_non_generated_ticker(normalized, pack_result.build_state)
        asset = _asset_for_response(normalized, pack_result.asset)
        terms = _generic_terms_for_asset(asset, term_filter=term)
        reason = _non_generated_reason(response_state, pack_result.message)
        return GlossaryResponse(
            selected_asset=asset,
            state=pack_result.state,
            glossary_state=response_state,
            terms=terms,
            evidence_references=[],
            citation_bindings=[],
            source_references=[],
            diagnostics=GlossaryDiagnostics(
                filters_applied=filters,
                unavailable_reasons=[reason],
            ),
        )

    pack = _asset_knowledge_pack_for_glossary(normalized, persisted_pack_reader=persisted_pack_reader)
    selected_entries = _catalog_entries_for_asset(pack.asset, term_filter=term)
    evidence_references: list[GlossaryEvidenceReference] = []
    citation_bindings: list[GlossaryCitationBinding] = []
    source_references_by_id: dict[str, GlossarySourceReference] = {}
    term_responses: list[GlossaryTermResponse] = []

    for entry in selected_entries:
        refs = _evidence_references_for_entry(entry, pack)
        bindings = _citation_bindings_for_refs(entry, refs, pack)
        references_by_id = {reference.reference_id: reference for reference in refs}
        allowed_bindings = [
            binding
            for binding in bindings
            if binding.source_use_policy not in {
                SourceUsePolicy.metadata_only,
                SourceUsePolicy.link_only,
                SourceUsePolicy.rejected,
            }
            and binding.allowlist_status is SourceAllowlistStatus.allowed
            and binding.permitted_operations.can_support_citations
        ]

        for binding in allowed_bindings:
            source = _source_by_id(pack, binding.source_document_id)
            if source and source.asset_ticker == pack.asset.ticker:
                source_references_by_id[source.source_document_id] = _source_reference(source)

        evidence_references.extend(refs)
        citation_bindings.extend(allowed_bindings)
        term_responses.append(
            GlossaryTermResponse(
                term_identity=_term_identity(entry),
                generic_definition=_generic_definition(entry),
                asset_context=_asset_context(entry, refs, allowed_bindings, references_by_id),
            )
        )

    omitted = sorted({entry.slug for entry in _catalog_entries_for_asset(pack.asset, term_filter=None)} - {entry.term_identity.slug for entry in term_responses})
    glossary_state = GlossaryResponseState.available if term_responses else GlossaryResponseState.insufficient_evidence
    unavailable_reasons = [] if term_responses else ["No curated glossary term matched the requested filter."]

    return GlossaryResponse(
        selected_asset=pack.asset,
        state=StateMessage(
            status=AssetStatus.supported,
            message="Glossary asset-context contract is shaped from deterministic local knowledge-pack evidence.",
        ),
        glossary_state=glossary_state,
        terms=term_responses,
        evidence_references=sorted(evidence_references, key=lambda item: item.reference_id),
        citation_bindings=sorted(citation_bindings, key=lambda item: item.binding_id),
        source_references=sorted(source_references_by_id.values(), key=lambda item: item.source_document_id),
        diagnostics=GlossaryDiagnostics(
            filters_applied=filters,
            unavailable_reasons=unavailable_reasons,
            omitted_term_slugs=omitted,
        ),
    )


def _asset_knowledge_pack_for_glossary(
    ticker: str,
    *,
    persisted_pack_reader: object | None = None,
) -> AssetKnowledgePack:
    if persisted_pack_reader is None:
        return build_asset_knowledge_pack(ticker)

    from backend.retrieval_repository import read_persisted_knowledge_pack_response

    persisted = read_persisted_knowledge_pack_response(ticker, reader=persisted_pack_reader)
    if not persisted.found or persisted.records is None or persisted.response is None:
        return build_asset_knowledge_pack(ticker)
    if not persisted.response.asset.supported or not persisted.response.generated_output_available:
        return build_asset_knowledge_pack(ticker)

    try:
        from backend.overview import _asset_knowledge_pack_from_repository_records

        return _asset_knowledge_pack_from_repository_records(persisted.records)
    except Exception:
        return build_asset_knowledge_pack(ticker)


def _filters(term: str | None) -> dict[str, str]:
    return {"term": _normalize_term(term)} if term and term.strip() else {}


def _catalog_entries_for_asset(asset: AssetIdentity, *, term_filter: str | None) -> list[GlossaryCatalogEntry]:
    entries = [entry for entry in TERM_CATALOG if asset.asset_type in entry.applies_to]
    if term_filter:
        normalized = _normalize_term(term_filter)
        entries = [
            entry
            for entry in entries
            if normalized in {_normalize_term(entry.term), entry.slug, *{_normalize_term(alias) for alias in entry.aliases}}
        ]
    return sorted(entries, key=lambda entry: (entry.beginner_category, entry.term.lower()))


def _generic_terms_for_asset(asset: AssetIdentity, *, term_filter: str | None) -> list[GlossaryTermResponse]:
    entries = _catalog_entries_for_asset(asset, term_filter=term_filter)
    if asset.asset_type not in {AssetType.stock, AssetType.etf} and term_filter:
        entries = [entry for entry in TERM_CATALOG if _normalize_term(term_filter) in {_normalize_term(entry.term), entry.slug}]
    elif asset.asset_type not in {AssetType.stock, AssetType.etf}:
        entries = []

    return [
        GlossaryTermResponse(
            term_identity=_term_identity(entry),
            generic_definition=_generic_definition(entry),
            asset_context=GlossaryAssetContext(
                availability_state=GlossaryAssetContextState.generic_only,
                evidence_state=EvidenceState.insufficient_evidence,
                freshness_state=FreshnessState.unknown,
                context_note="Generic beginner definition only; this response does not provide asset-specific evidence.",
                uncertainty_labels=["generic_only"],
                suppression_reasons=["non_generated_asset_state"],
            ),
        )
        for entry in entries
    ]


def _term_identity(entry: GlossaryCatalogEntry) -> GlossaryTermIdentity:
    return GlossaryTermIdentity(
        term=entry.term,
        slug=entry.slug,
        aliases=list(entry.aliases),
        applies_to=list(entry.applies_to),
    )


def _generic_definition(entry: GlossaryCatalogEntry) -> GlossaryGenericDefinition:
    return GlossaryGenericDefinition(
        simple_definition=entry.simple_definition,
        why_it_matters=entry.why_it_matters,
        common_beginner_mistake=entry.common_beginner_mistake,
        beginner_category=entry.beginner_category,
    )


def _evidence_references_for_entry(entry: GlossaryCatalogEntry, pack: AssetKnowledgePack) -> list[GlossaryEvidenceReference]:
    references: list[GlossaryEvidenceReference] = []
    references.extend(_fact_reference(entry, fact, pack) for fact in pack.normalized_facts if fact.fact.field_name in entry.fact_fields)
    references.extend(_chunk_reference(entry, chunk, pack) for chunk in pack.source_chunks if _chunk_matches(entry, chunk))
    references.extend(
        _recent_reference(entry, recent, pack)
        for recent in pack.recent_developments
        if recent.recent_development.event_type in entry.recent_event_types
    )
    references.extend(_gap_reference(entry, gap, pack) for gap in pack.evidence_gaps if gap.field_name in entry.gap_fields)

    deduped: dict[str, GlossaryEvidenceReference] = {}
    for reference in references:
        deduped[reference.reference_id] = reference
    return sorted(deduped.values(), key=lambda item: item.reference_id)


def _fact_reference(entry: GlossaryCatalogEntry, item: RetrievedFact, pack: AssetKnowledgePack) -> GlossaryEvidenceReference:
    citation_id = f"c_{item.fact.fact_id}"
    return GlossaryEvidenceReference(
        reference_id=f"glossary_{entry.slug}_{item.fact.fact_id}",
        reference_type=GlossaryEvidenceReferenceType.normalized_fact,
        term_slug=entry.slug,
        asset_ticker=pack.asset.ticker,
        section_id=_section_id_for_fact(item.fact.field_name),
        field_name=item.fact.field_name,
        fact_id=item.fact.fact_id,
        source_chunk_id=item.fact.source_chunk_id,
        source_document_id=item.fact.source_document_id,
        citation_ids=[citation_id],
        evidence_state=_evidence_state(item.fact.evidence_state, item.fact.freshness_state),
        freshness_state=item.fact.freshness_state,
        as_of_date=item.fact.as_of_date,
        retrieved_at=item.source_document.retrieved_at,
    )


def _chunk_reference(entry: GlossaryCatalogEntry, item: RetrievedSourceChunk, pack: AssetKnowledgePack) -> GlossaryEvidenceReference:
    citation_id = f"c_{item.chunk.chunk_id}"
    return GlossaryEvidenceReference(
        reference_id=f"glossary_{entry.slug}_{item.chunk.chunk_id}",
        reference_type=GlossaryEvidenceReferenceType.source_chunk,
        term_slug=entry.slug,
        asset_ticker=pack.asset.ticker,
        section_id=_section_id_for_chunk(item.chunk.section_name),
        source_chunk_id=item.chunk.chunk_id,
        source_document_id=item.chunk.source_document_id,
        citation_ids=[citation_id],
        evidence_state=EvidenceState.supported,
        freshness_state=item.source_document.freshness_state,
        as_of_date=item.source_document.as_of_date,
        retrieved_at=item.source_document.retrieved_at,
    )


def _recent_reference(
    entry: GlossaryCatalogEntry,
    item: RetrievedRecentDevelopment,
    pack: AssetKnowledgePack,
) -> GlossaryEvidenceReference:
    citation_id = f"c_{item.recent_development.event_id}"
    return GlossaryEvidenceReference(
        reference_id=f"glossary_{entry.slug}_{item.recent_development.event_id}",
        reference_type=GlossaryEvidenceReferenceType.recent_development,
        term_slug=entry.slug,
        asset_ticker=pack.asset.ticker,
        section_id="recent_developments",
        recent_event_id=item.recent_development.event_id,
        source_chunk_id=item.recent_development.source_chunk_id,
        source_document_id=item.recent_development.source_document_id,
        citation_ids=[citation_id],
        evidence_state=_evidence_state(item.recent_development.evidence_state, item.recent_development.freshness_state),
        freshness_state=item.recent_development.freshness_state,
        as_of_date=item.recent_development.event_date,
        retrieved_at=item.source_document.retrieved_at,
    )


def _gap_reference(entry: GlossaryCatalogEntry, gap: EvidenceGap, pack: AssetKnowledgePack) -> GlossaryEvidenceReference:
    return GlossaryEvidenceReference(
        reference_id=f"glossary_{entry.slug}_{gap.gap_id}",
        reference_type=GlossaryEvidenceReferenceType.evidence_gap,
        term_slug=entry.slug,
        asset_ticker=pack.asset.ticker,
        section_id=_section_id_for_fact(gap.field_name),
        field_name=gap.field_name,
        evidence_gap_id=gap.gap_id,
        source_document_id=gap.source_document_id,
        source_chunk_id=gap.source_chunk_id,
        evidence_state=_evidence_state(gap.evidence_state, gap.freshness_state),
        freshness_state=gap.freshness_state,
        unavailable_reason=gap.message,
    )


def _citation_bindings_for_refs(
    entry: GlossaryCatalogEntry,
    references: list[GlossaryEvidenceReference],
    pack: AssetKnowledgePack,
) -> list[GlossaryCitationBinding]:
    bindings: list[GlossaryCitationBinding] = []
    for reference in references:
        if not reference.source_document_id or not reference.citation_ids:
            continue
        source = _source_by_id(pack, reference.source_document_id)
        if source is None or source.asset_ticker != pack.asset.ticker:
            continue
        decision = resolve_source_policy(url=source.url, source_identifier=source.source_document_id)
        supports_context = source_can_support_generated_output(decision)
        for citation_id in reference.citation_ids:
            bindings.append(
                GlossaryCitationBinding(
                    binding_id=f"glossary_binding_{entry.slug}_{citation_id}",
                    term_slug=entry.slug,
                    citation_id=citation_id,
                    source_document_id=source.source_document_id,
                    asset_ticker=pack.asset.ticker,
                    evidence_reference_id=reference.reference_id,
                    evidence_reference_type=reference.reference_type,
                    freshness_state=reference.freshness_state,
                    source_quality=decision.source_quality,
                    allowlist_status=decision.allowlist_status,
                    source_use_policy=decision.source_use_policy,
                    permitted_operations=decision.permitted_operations,
                    supports_asset_specific_context=supports_context,
                )
            )
    return bindings


def _asset_context(
    entry: GlossaryCatalogEntry,
    references: list[GlossaryEvidenceReference],
    bindings: list[GlossaryCitationBinding],
    references_by_id: dict[str, GlossaryEvidenceReference],
) -> GlossaryAssetContext:
    citation_ids = sorted({binding.citation_id for binding in bindings if binding.supports_asset_specific_context})
    source_document_ids = sorted({binding.source_document_id for binding in bindings if binding.supports_asset_specific_context})
    evidence_reference_ids = sorted({binding.evidence_reference_id for binding in bindings if binding.supports_asset_specific_context})
    cited_refs = [references_by_id[reference_id] for reference_id in evidence_reference_ids if reference_id in references_by_id]
    gap_refs = [reference for reference in references if reference.reference_type is GlossaryEvidenceReferenceType.evidence_gap]

    if citation_ids and cited_refs:
        evidence_state = _combined_evidence_state(cited_refs)
        freshness_state = _combined_freshness([reference.freshness_state for reference in cited_refs])
        availability = _availability_from_states(evidence_state, freshness_state)
        return GlossaryAssetContext(
            availability_state=availability,
            evidence_state=evidence_state,
            freshness_state=freshness_state,
            context_note="Existing same-asset evidence can support optional asset-specific glossary context for this term.",
            evidence_reference_ids=evidence_reference_ids,
            citation_ids=citation_ids,
            source_document_ids=source_document_ids,
            uncertainty_labels=_uncertainty_labels(availability, evidence_state, freshness_state),
        )

    if gap_refs:
        evidence_state = _combined_evidence_state(gap_refs)
        freshness_state = _combined_freshness([reference.freshness_state for reference in gap_refs])
        availability = GlossaryAssetContextState.stale if freshness_state is FreshnessState.stale else GlossaryAssetContextState.insufficient_evidence
        return GlossaryAssetContext(
            availability_state=availability,
            evidence_state=evidence_state,
            freshness_state=freshness_state,
            context_note="The local knowledge pack has an explicit evidence gap for asset-specific glossary context.",
            evidence_reference_ids=[reference.reference_id for reference in gap_refs],
            uncertainty_labels=_uncertainty_labels(availability, evidence_state, freshness_state),
            suppression_reasons=[reference.unavailable_reason for reference in gap_refs if reference.unavailable_reason],
        )

    suppressed_reasons = []
    if references and not bindings:
        suppressed_reasons.append("source_policy_or_citation_binding_unavailable")
    return GlossaryAssetContext(
        availability_state=GlossaryAssetContextState.generic_only,
        evidence_state=EvidenceState.insufficient_evidence,
        freshness_state=FreshnessState.unknown,
        context_note="Generic beginner definition only; no same-asset citation-backed context is available in the local knowledge pack.",
        uncertainty_labels=["generic_only"],
        suppression_reasons=suppressed_reasons,
    )


def _source_reference(source: SourceDocumentFixture) -> GlossarySourceReference:
    decision = resolve_source_policy(url=source.url, source_identifier=source.source_document_id)
    return GlossarySourceReference(
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
        source_quality=decision.source_quality,
        allowlist_status=decision.allowlist_status,
        source_use_policy=decision.source_use_policy,
        permitted_operations=decision.permitted_operations,
    )


def _source_by_id(pack: AssetKnowledgePack, source_document_id: str) -> SourceDocumentFixture | None:
    return next((source for source in pack.source_documents if source.source_document_id == source_document_id), None)


def _chunk_matches(entry: GlossaryCatalogEntry, item: RetrievedSourceChunk) -> bool:
    if not entry.chunk_terms:
        return False
    text = f"{item.chunk.section_name} {item.chunk.text}".lower()
    return any(term.lower() in text for term in entry.chunk_terms)


def _evidence_state(state: str, freshness_state: FreshnessState) -> EvidenceState:
    if freshness_state is FreshnessState.stale:
        return EvidenceState.stale
    if freshness_state is FreshnessState.unavailable:
        return EvidenceState.unavailable
    mapping = {
        "supported": EvidenceState.supported,
        "missing": EvidenceState.insufficient_evidence,
        "insufficient": EvidenceState.insufficient_evidence,
        "stale": EvidenceState.stale,
        "unsupported": EvidenceState.unsupported,
        "unknown": EvidenceState.unknown,
        "unavailable": EvidenceState.unavailable,
        "no_major_recent_development": EvidenceState.no_major_recent_development,
    }
    return mapping.get(state, EvidenceState.unknown)


def _combined_evidence_state(references: list[GlossaryEvidenceReference]) -> EvidenceState:
    states = {reference.evidence_state for reference in references}
    if not states:
        return EvidenceState.insufficient_evidence
    if EvidenceState.supported in states and len(states) == 1:
        return EvidenceState.supported
    for state in [EvidenceState.stale, EvidenceState.unavailable, EvidenceState.insufficient_evidence, EvidenceState.unknown]:
        if state in states:
            return state
    return EvidenceState.mixed


def _combined_freshness(states: list[FreshnessState]) -> FreshnessState:
    if not states:
        return FreshnessState.unknown
    for state in [FreshnessState.unavailable, FreshnessState.unknown, FreshnessState.stale]:
        if state in states:
            return state
    return FreshnessState.fresh


def _availability_from_states(
    evidence_state: EvidenceState,
    freshness_state: FreshnessState,
) -> GlossaryAssetContextState:
    if freshness_state is FreshnessState.stale or evidence_state is EvidenceState.stale:
        return GlossaryAssetContextState.stale
    if freshness_state is FreshnessState.unavailable or evidence_state is EvidenceState.unavailable:
        return GlossaryAssetContextState.unavailable
    if evidence_state is EvidenceState.supported:
        return GlossaryAssetContextState.available
    if evidence_state is EvidenceState.mixed:
        return GlossaryAssetContextState.partial
    if evidence_state is EvidenceState.unknown:
        return GlossaryAssetContextState.unknown
    return GlossaryAssetContextState.insufficient_evidence


def _uncertainty_labels(
    availability: GlossaryAssetContextState,
    evidence_state: EvidenceState,
    freshness_state: FreshnessState,
) -> list[str]:
    labels: set[str] = set()
    if availability is not GlossaryAssetContextState.available:
        labels.add(availability.value)
    if evidence_state is not EvidenceState.supported:
        labels.add(evidence_state.value)
    if freshness_state is not FreshnessState.fresh:
        labels.add(freshness_state.value)
    return sorted(labels)


def _section_id_for_fact(field_name: str) -> str:
    if "valuation" in field_name or "pe" in field_name:
        return "valuation_context"
    if field_name in {"financial_quality_revenue_trend", "revenue", "operating_margin", "eps", "free_cash_flow", "debt"}:
        return "financial_quality"
    if field_name in {"expense_ratio", "aum", "bid_ask_spread", "premium_discount", "nav", "liquidity", "trading_data_limitation"}:
        return "cost_trading_context"
    if field_name in {"holdings_count", "holdings_exposure_detail", "sector_exposure", "country_exposure", "top_10_concentration"}:
        return "holdings_exposure"
    if field_name in {"benchmark", "construction_methodology", "tracking_error", "tracking_difference"}:
        return "construction_methodology"
    if "risk" in field_name:
        return "top_risks"
    return "canonical_facts"


def _section_id_for_chunk(section_name: str) -> str:
    normalized = section_name.lower()
    if "risk" in normalized:
        return "top_risks"
    if "holding" in normalized:
        return "holdings_exposure"
    if "trading" in normalized or "cost" in normalized:
        return "cost_trading_context"
    if "methodology" in normalized:
        return "construction_methodology"
    if "financial" in normalized:
        return "financial_quality"
    if "valuation" in normalized:
        return "valuation_context"
    return "canonical_facts"


def _asset_for_response(ticker: str, fallback: AssetIdentity) -> AssetIdentity:
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


def _response_state_for_non_generated_ticker(
    ticker: str,
    build_state: KnowledgePackBuildState,
) -> GlossaryResponseState:
    search = search_assets(ticker)
    support = search.state.support_classification
    if support is SearchSupportClassification.out_of_scope:
        return GlossaryResponseState.out_of_scope
    if build_state is KnowledgePackBuildState.eligible_not_cached:
        return GlossaryResponseState.eligible_not_cached
    if build_state is KnowledgePackBuildState.unsupported:
        return GlossaryResponseState.unsupported
    if build_state is KnowledgePackBuildState.unknown:
        return GlossaryResponseState.unknown
    return GlossaryResponseState.unavailable


def _non_generated_reason(state: GlossaryResponseState, message: str) -> str:
    return (
        f"{state.value}: no asset-specific glossary evidence, citations, source documents, generated page, "
        f"chat answer, comparison, live provider call, or live LLM call is created. {message}"
    )


def _normalize_term(term: str) -> str:
    return term.strip().lower().replace("/", "-").replace(" ", "-")
