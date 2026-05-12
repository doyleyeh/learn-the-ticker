from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from backend.lightweight_data_fetch import (
    ETF_QUOTE_STAT_ROW_ORDER,
    QUOTE_STAT_LABELS,
    STOCK_QUOTE_STAT_ROW_ORDER,
    build_lightweight_api_fallback_diagnostics,
    fetch_lightweight_asset_data,
)
from backend.market_news_runtime import build_runtime_market_news_response
from backend.models import (
    AssetStatus,
    AssetType,
    BeginnerSummary,
    Citation,
    DetailsResponse,
    EconomicIndicatorsPackResponse,
    EvidenceState,
    FreshnessState,
    LightweightFetchFact,
    LightweightFetchResponse,
    LightweightFetchSource,
    LightweightFetchState,
    MetricValue,
    OverviewChart,
    OverviewChartPoint,
    OverviewMetric,
    OverviewResponse,
    OverviewSection,
    OverviewSectionItem,
    OverviewTable,
    OverviewTableColumn,
    OverviewTableRow,
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
    WeeklyNewsResponse,
)
from backend.generation_evidence import evidence_pack_from_lightweight_response
from backend.settings import LightweightDataSettings, build_lightweight_data_settings
from backend.summary_generation import (
    SummaryGenerationContractError,
    build_default_summary_generation_service,
    deterministic_summary_generation,
)
from backend.weekly_news import build_ai_comprehensive_analysis, compute_weekly_news_window
from backend.weekly_news_sources import build_lightweight_weekly_news_focus


LIGHTWEIGHT_PAGE_SCHEMA_VERSION = "lightweight-local-mvp-page-v1"
LIGHTWEIGHT_DURABLE_PERSISTENCE_SCHEMA_VERSION = "lightweight-durable-persistence-v1"
LIGHTWEIGHT_PAGE_BUILD_CACHE_TTL_SECONDS_ENV = "LIGHTWEIGHT_PAGE_BUILD_CACHE_TTL_SECONDS"
DEFAULT_LIGHTWEIGHT_PAGE_BUILD_CACHE_TTL_SECONDS = 600
_VOLATILE_PAGE_BUILD_CACHE_FIELDS = frozenset(
    {
        "page_last_updated_at",
        "retrieved_at",
        "diagnostics",
        "fallback_diagnostics",
    }
)


@dataclass(frozen=True)
class _LightweightPageBuildCacheKey:
    response_kind: str
    evidence_digest: str
    context_digest: str
    generation_signature: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _LightweightPageBuildCacheEntry:
    response: Any
    stored_at_seconds: float


_LIGHTWEIGHT_PAGE_BUILD_CACHE: dict[_LightweightPageBuildCacheKey, _LightweightPageBuildCacheEntry] = {}


def clear_lightweight_page_build_cache() -> None:
    _LIGHTWEIGHT_PAGE_BUILD_CACHE.clear()


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


def build_lightweight_weekly_news_response(
    response: LightweightFetchResponse,
    *,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    market_news_focus: Any | None = None,
    technical_context: dict[str, Any] | None = None,
) -> WeeklyNewsResponse:
    cache_context = _page_build_cache_context(
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        technical_context=technical_context,
    )
    cached = _page_build_cache_get("weekly_news", response, context_payload=cache_context)
    if cached is not None:
        return cached

    stable_citation_ids = _preferred_citation_ids(response) or [citation.citation_id for citation in response.citations[:1]]
    source_documents = [_source_document_from_lightweight(source, response) for source in response.sources]
    weekly_news_focus = build_lightweight_weekly_news_focus(response) or _empty_weekly_news_focus(response)
    generation_evidence_pack = evidence_pack_from_lightweight_response(
        response,
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        weekly_news_focus=weekly_news_focus,
        technical_context=technical_context,
    )
    ai_analysis = build_ai_comprehensive_analysis(
        response.asset,
        weekly_news_focus,
        canonical_fact_citation_ids=stable_citation_ids,
        canonical_source_document_ids=[source.source_document_id for source in source_documents[:1]],
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        technical_context=technical_context,
        generation_evidence_pack=generation_evidence_pack,
    )
    weekly_response = WeeklyNewsResponse(
        asset=response.asset.model_copy(update={"status": AssetStatus.supported, "supported": True}),
        state=StateMessage(
            status=AssetStatus.supported,
            message=(
                "Live lightweight Weekly News Focus is available when enough source-labeled ticker evidence passes "
                "the selection rules."
            ),
        ),
        weekly_news_focus=weekly_news_focus,
        ai_comprehensive_analysis=ai_analysis,
    )
    _page_build_cache_set("weekly_news", response, weekly_response, context_payload=cache_context)
    return weekly_response


def build_lightweight_overview_response(
    response: LightweightFetchResponse,
    *,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    technical_context: dict[str, Any] | None = None,
) -> OverviewResponse:
    cache_context = _page_build_cache_context(
        economic_indicators=economic_indicators,
        technical_context=technical_context,
    )
    cached = _page_build_cache_get("overview", response, context_payload=cache_context)
    if cached is not None:
        return cached

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
    with deterministic_summary_generation():
        weekly_news_focus = build_lightweight_weekly_news_focus(response) or _empty_weekly_news_focus(response)
        market_news_kwargs: dict[str, Any] = {"cache_only": True}
        if economic_indicators is not None:
            market_news_kwargs["economic_indicators"] = economic_indicators
        market_news = build_runtime_market_news_response(**market_news_kwargs)
        generation_evidence_pack = evidence_pack_from_lightweight_response(
            response,
            economic_indicators=economic_indicators,
            market_news_focus=market_news.market_news_focus,
            weekly_news_focus=weekly_news_focus,
            technical_context=technical_context,
        )
        sections = (
            _stock_sections(
                response,
                stable_citation_ids,
                provider_citation_ids,
                generation_evidence_pack=generation_evidence_pack,
            )
            if response.asset.asset_type is AssetType.stock
            else _etf_sections(
                response,
                stable_citation_ids,
                provider_citation_ids,
                generation_evidence_pack=generation_evidence_pack,
            )
        )
        claims = _claims(response, stable_citation_ids, provider_citation_ids)
        ai_analysis = build_ai_comprehensive_analysis(
            response.asset,
            weekly_news_focus,
            canonical_fact_citation_ids=stable_citation_ids,
            canonical_source_document_ids=[source.source_document_id for source in sources[:1]],
            economic_indicators=economic_indicators,
            market_news_focus=market_news.market_news_focus,
            technical_context=technical_context,
            generation_evidence_pack=generation_evidence_pack,
        )

        overview = OverviewResponse(
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
            beginner_summary=_beginner_summary(response, generation_evidence_pack=generation_evidence_pack),
            top_risks=_top_risks(
                response,
                stable_citation_ids,
                provider_citation_ids,
                generation_evidence_pack=generation_evidence_pack,
            ),
            recent_developments=[],
            market_news_focus=market_news.market_news_focus,
            market_ai_comprehensive_analysis=market_news.market_ai_comprehensive_analysis,
            weekly_news_focus=weekly_news_focus,
            ai_comprehensive_analysis=ai_analysis,
            suitability_summary=_suitability_summary(response, stable_citation_ids),
            claims=claims,
            citations=citations,
            source_documents=sources,
            sections=sections,
            section_freshness_validation=[],
            fallback_diagnostics=_fallback_diagnostics(response),
        )
    _page_build_cache_set("overview", response, overview, context_payload=cache_context)
    return overview


def persist_lightweight_evidence_if_configured(
    response: LightweightFetchResponse,
    *,
    source_snapshot_repository: Any | None = None,
    knowledge_pack_repository: Any | None = None,
    generated_output_cache_repository: Any | None = None,
    allow_generated_output_cache_promotion: bool = False,
) -> dict[str, Any]:
    """Persist rights-safe lightweight metadata when optional durable repositories are injected."""

    promotion = evaluate_lightweight_generated_output_promotion(
        response,
        allow_generated_output_cache_promotion=allow_generated_output_cache_promotion,
    )
    diagnostics: dict[str, Any] = {
        "schema_version": LIGHTWEIGHT_DURABLE_PERSISTENCE_SCHEMA_VERSION,
        "ticker": response.asset.ticker,
        "attempted": source_snapshot_repository is not None
        or knowledge_pack_repository is not None
        or generated_output_cache_repository is not None,
        "source_snapshot_persisted": False,
        "knowledge_pack_persisted": False,
        "generated_output_cache_repository_configured": generated_output_cache_repository is not None,
        "strict_audit_quality_source_approval_granted": False,
        "generated_output_cache_promoted": promotion["promotion_allowed"],
        "generated_output_promotion": promotion,
        "raw_payload_exposed": False,
        "secret_values_exposed": False,
        "status": "not_configured",
        "reason_codes": [],
    }
    if source_snapshot_repository is None and knowledge_pack_repository is None and generated_output_cache_repository is None:
        diagnostics["reason_codes"].append("durable_repository_not_configured")
        return diagnostics
    if not _can_render_lightweight_page(response):
        diagnostics["status"] = "skipped"
        diagnostics["reason_codes"].append("lightweight_response_not_renderable")
        return diagnostics

    try:
        snapshot_records = None
        if source_snapshot_repository is not None:
            from backend.source_snapshot_repository import source_snapshot_records_from_lightweight_response

            snapshot_records = source_snapshot_records_from_lightweight_response(response)
            source_snapshot_repository.persist(snapshot_records)
            diagnostics["source_snapshot_persisted"] = True
            diagnostics["source_snapshot_artifact_count"] = len(snapshot_records.artifacts)
        if knowledge_pack_repository is not None:
            from backend.knowledge_pack_repository import knowledge_pack_records_from_lightweight_response

            knowledge_records = knowledge_pack_records_from_lightweight_response(response)
            knowledge_pack_repository.persist(knowledge_records)
            diagnostics["knowledge_pack_persisted"] = True
            diagnostics["normalized_fact_count"] = len(knowledge_records.normalized_facts)
            diagnostics["source_document_count"] = len(knowledge_records.source_documents)
            diagnostics["citation_count"] = len(knowledge_records.envelope.citation_ids)
        if generated_output_cache_repository is not None and not promotion["promotion_allowed"]:
            diagnostics["reason_codes"].append("generated_output_cache_promotion_blocked")
        diagnostics["status"] = "persisted"
        return diagnostics
    except Exception as exc:
        diagnostics["status"] = "blocked"
        diagnostics["reason_codes"].append(f"durable_persistence_contract_error:{exc.__class__.__name__}")
        diagnostics["source_snapshot_persisted"] = False
        diagnostics["knowledge_pack_persisted"] = False
        return diagnostics


def evaluate_lightweight_generated_output_promotion(
    response: LightweightFetchResponse,
    *,
    allow_generated_output_cache_promotion: bool = False,
) -> dict[str, Any]:
    """Evaluate whether a lightweight response may promote generated-output cache metadata."""

    from backend.source_policy import SourcePolicyAction, validate_source_handoff

    reason_codes: list[str] = []
    source_documents = [_source_document_from_lightweight(source, response) for source in response.sources]
    handoff_results = [
        validate_source_handoff(source, action=SourcePolicyAction.cacheable_generated_output)
        for source in source_documents
    ]
    if not allow_generated_output_cache_promotion:
        reason_codes.append("explicit_promotion_opt_in_missing")
    if response.raw_payload_exposed:
        reason_codes.append("raw_payload_exposed")
    if not response.generated_output_eligible:
        reason_codes.append("lightweight_response_not_generated_output_eligible")
    if response.diagnostics.get("strict_audit_quality_approval") is not True:
        reason_codes.append("strict_audit_quality_source_approval_not_granted")
    if response.fetch_state not in {LightweightFetchState.supported, LightweightFetchState.partial}:
        reason_codes.append(f"fetch_state_{response.fetch_state.value}")
    if not response.citations:
        reason_codes.append("citation_support_missing")
    if any(not result.allowed for result in handoff_results):
        reason_codes.append("source_handoff_not_approved_for_cacheable_generated_output")
    if response.freshness.freshness_state in {FreshnessState.unknown, FreshnessState.unavailable}:
        reason_codes.append(f"freshness_{response.freshness.freshness_state.value}")
    if response.page_render_state in {EvidenceState.unknown, EvidenceState.unavailable, EvidenceState.insufficient_evidence}:
        reason_codes.append(f"evidence_{response.page_render_state.value}")

    return {
        "schema_version": "lightweight-generated-output-promotion-gate-v1",
        "promotion_allowed": not reason_codes,
        "source_count": len(source_documents),
        "citation_count": len(response.citations),
        "source_handoff_checked": bool(source_documents),
        "handoff_allowed_source_count": sum(1 for result in handoff_results if result.allowed),
        "handoff_blocked_source_count": sum(1 for result in handoff_results if not result.allowed),
        "reason_codes": sorted(dict.fromkeys(reason_codes)),
        "raw_payload_exposed": response.raw_payload_exposed,
        "secret_values_exposed": False,
    }


def build_lightweight_details_response(response: LightweightFetchResponse) -> DetailsResponse:
    cached = _page_build_cache_get("details", response)
    if cached is not None:
        return cached

    citation_ids = _preferred_citation_ids(response)
    provider_citation_ids = _citation_ids_for_source_label(response, "provider_derived")
    if response.asset.asset_type is AssetType.stock:
        facts: dict[str, Any] = {
            "business_model": _stock_business_model(response),
            "products_services_context": _stock_products_services_context(response),
            "financial_quality_context": _stock_financial_quality_context(response),
            "valuation_context": _stock_valuation_context(response),
            "risk_context": _stock_risk_context(response),
            "educational_suitability": _suitability_summary(response, citation_ids).learn_next,
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
            "construction_methodology": _etf_construction_context(response),
            "benchmark": _metric_from_etf_fact(response, "benchmark", citation_ids),
            "cost_context": _metric_from_etf_expense_ratio(response, citation_ids),
            "prospectus_reference": _etf_prospectus_reference(response, citation_ids),
            "provider_market_price": _metric_from_market_price(response, provider_citation_ids),
            "manifest_scope_signal": _etf_scope_summary(response),
            "risk_context": _etf_risk_context(response),
            "comparison_overlap_context": _etf_comparison_overlap_context(response),
            "educational_suitability": _suitability_summary(response, citation_ids).learn_next,
        }

    details = DetailsResponse(
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
        fallback_diagnostics=_fallback_diagnostics(response),
    )
    _page_build_cache_set("details", response, details)
    return details


def build_lightweight_sources_response(
    response: LightweightFetchResponse,
    *,
    citation_id: str | None = None,
    source_document_id: str | None = None,
) -> SourcesResponse:
    response_kind = f"sources:{(citation_id or '').strip()}:{(source_document_id or '').strip()}"
    cached = _page_build_cache_get(response_kind, response)
    if cached is not None:
        return cached

    with deterministic_summary_generation():
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
    sources_response = SourcesResponse(
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
        fallback_diagnostics=_fallback_diagnostics(response),
    )
    _page_build_cache_set(response_kind, response, sources_response)
    return sources_response


def _page_build_cache_get(
    response_kind: str,
    response: LightweightFetchResponse,
    *,
    context_payload: Any | None = None,
) -> Any | None:
    ttl = _page_build_cache_ttl_seconds()
    if ttl <= 0:
        return None
    key = _page_build_cache_key(response_kind, response, context_payload=context_payload)
    entry = _LIGHTWEIGHT_PAGE_BUILD_CACHE.get(key)
    if entry is None:
        return None
    if time.monotonic() - entry.stored_at_seconds > ttl:
        _LIGHTWEIGHT_PAGE_BUILD_CACHE.pop(key, None)
        return None
    return entry.response.model_copy(deep=True)


def _page_build_cache_set(
    response_kind: str,
    response: LightweightFetchResponse,
    rendered_response: Any,
    *,
    context_payload: Any | None = None,
) -> None:
    ttl = _page_build_cache_ttl_seconds()
    if ttl <= 0:
        return
    _LIGHTWEIGHT_PAGE_BUILD_CACHE[
        _page_build_cache_key(response_kind, response, context_payload=context_payload)
    ] = _LightweightPageBuildCacheEntry(response=rendered_response.model_copy(deep=True), stored_at_seconds=time.monotonic())


def _page_build_cache_key(
    response_kind: str,
    response: LightweightFetchResponse,
    *,
    context_payload: Any | None = None,
) -> _LightweightPageBuildCacheKey:
    evidence_payload = _stable_page_build_evidence_payload(response.model_dump(mode="json"))
    evidence_digest = hashlib.sha256(
        json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    context_digest = hashlib.sha256(
        json.dumps(
            _stable_page_build_evidence_payload(_jsonable_page_build_context(context_payload)),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return _LightweightPageBuildCacheKey(
        response_kind=response_kind,
        evidence_digest=evidence_digest,
        context_digest=context_digest,
        generation_signature=_page_build_generation_signature(),
    )


def _page_build_cache_context(**values: Any) -> dict[str, Any] | None:
    context = {key: _jsonable_page_build_context(value) for key, value in values.items() if value is not None}
    return context or None


def _jsonable_page_build_context(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable_page_build_context(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable_page_build_context(child) for child in value]
    return str(value)


def _page_build_generation_signature() -> tuple[tuple[str, str], ...]:
    names = (
        "LLM_PROVIDER",
        "LLM_LIVE_GENERATION_ENABLED",
        "LLM_LIVE_TASK_ALLOWLIST",
        "LLM_VALIDATION_RETRY_COUNT",
        "OPENROUTER_FREE_MODEL_ORDER",
        "OPENROUTER_MODEL",
        "OPENROUTER_PAID_FALLBACK_ENABLED",
        "OPENROUTER_PAID_FALLBACK_MODEL",
    )
    values = [(name, os.environ.get(name, "")) for name in names]
    values.append(("summary_generation_service_id", str(id(build_default_summary_generation_service))))
    values.append(("market_news_builder_id", str(id(build_runtime_market_news_response))))
    return tuple(values)


def _page_build_cache_ttl_seconds() -> int:
    raw = os.environ.get(LIGHTWEIGHT_PAGE_BUILD_CACHE_TTL_SECONDS_ENV)
    if raw is None:
        return DEFAULT_LIGHTWEIGHT_PAGE_BUILD_CACHE_TTL_SECONDS
    try:
        return max(0, int(raw.strip()))
    except ValueError:
        return DEFAULT_LIGHTWEIGHT_PAGE_BUILD_CACHE_TTL_SECONDS


def _stable_page_build_evidence_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _stable_page_build_evidence_payload(child)
            for key, child in value.items()
            if key not in _VOLATILE_PAGE_BUILD_CACHE_FIELDS
        }
    if isinstance(value, list):
        return [_stable_page_build_evidence_payload(item) for item in value]
    return value


def _can_render_lightweight_page(response: LightweightFetchResponse) -> bool:
    return (
        response.generated_output_eligible
        and response.asset.supported
        and response.fetch_state in {LightweightFetchState.supported, LightweightFetchState.partial}
        and bool(response.sources)
        and bool(response.facts)
        and not response.raw_payload_exposed
    )


def _fallback_diagnostics(response: LightweightFetchResponse):
    return response.fallback_diagnostics or build_lightweight_api_fallback_diagnostics(response)


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


def _beginner_summary(
    response: LightweightFetchResponse,
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> BeginnerSummary:
    if response.asset.asset_type is AssetType.stock:
        return _generated_beginner_summary(
            response,
            BeginnerSummary(
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
            ),
            generation_evidence_pack=generation_evidence_pack,
        )
    if _has_official_etf_issuer_evidence(response):
        return _generated_beginner_summary(
            response,
            BeginnerSummary(
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
            ),
            generation_evidence_pack=generation_evidence_pack,
        )
    return _generated_beginner_summary(
        response,
        BeginnerSummary(
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
        ),
        generation_evidence_pack=generation_evidence_pack,
    )


def _generated_beginner_summary(
    response: LightweightFetchResponse,
    base_summary: BeginnerSummary,
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> BeginnerSummary:
    evidence_pack = generation_evidence_pack or evidence_pack_from_lightweight_response(response)
    try:
        return build_default_summary_generation_service().generate_beginner_summary(
            asset=response.asset,
            base_summary=base_summary,
            citation_ids=[
                str(item["citation_id"])
                for item in evidence_pack.get("citation_evidence", [])
                if isinstance(item, dict) and item.get("citation_id")
            ]
            or _preferred_citation_ids(response)
            or [citation.citation_id for citation in response.citations[:1]],
            evidence_notes=[diagnostic for diagnostic in _lightweight_evidence_note_candidates(response) if diagnostic],
            generation_evidence_pack=evidence_pack,
        )
    except SummaryGenerationContractError:
        return base_summary


def _lightweight_evidence_note_candidates(response: LightweightFetchResponse) -> list[str]:
    notes = [
        f"fetch_state={response.fetch_state.value}",
        f"source_count={len(response.sources)}",
        f"fact_count={len(response.facts)}",
    ]
    for field_name in (
        "benchmark",
        "holdings_count",
        "expense_ratio",
        "provider_market_price",
        "provider_quote_stats",
        "provider_profile_overview",
        "latest_revenue_fact",
        "latest_net_income_fact",
        "latest_assets_fact",
    ):
        fact = _fact(response, field_name)
        if fact is not None and fact.value not in (None, ""):
            notes.append(f"{field_name}={_compact_evidence_value(fact.value)}")
    if response.gaps:
        notes.append("evidence_gaps=" + ",".join(gap.field_name for gap in response.gaps[:3]))
    if response.fallback_diagnostics is not None:
        notes.append("source_path=" + response.fallback_diagnostics.source_path)
    return notes


def _compact_evidence_value(value: Any) -> str:
    if isinstance(value, dict):
        parts: list[str] = []
        for key in (
            "regularMarketPrice",
            "currency",
            "sector",
            "industry",
            "business_summary",
            "market_cap",
            "trailing_pe",
            "forward_pe",
        ):
            if value.get(key) not in (None, ""):
                parts.append(f"{key}: {_short_value(value.get(key))}")
        rows = value.get("rows")
        if isinstance(rows, list):
            labels = [
                str(row.get("label") or row.get("metric_id"))
                for row in rows
                if isinstance(row, dict) and row.get("value") not in (None, "")
            ][:5]
            if labels:
                parts.append("rows: " + _join_human(labels))
        if not parts:
            parts = [f"{key}: {_short_value(item)}" for key, item in list(value.items())[:4]]
        return "; ".join(parts)[:360]
    if isinstance(value, list):
        return "; ".join(_short_value(item) for item in value[:4])[:360]
    return _short_value(value)[:360]


def _top_risks(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[RiskItem]:
    allowed_citation_ids = _dedupe([*stable_citation_ids, *provider_citation_ids])
    if response.asset.asset_type is AssetType.stock:
        profile = _fact_value(response, "provider_profile_overview")
        sector = profile.get("sector") if isinstance(profile, dict) else None
        industry = profile.get("industry") if isinstance(profile, dict) else None
        valuation_labels = _provider_metric_labels(response, "valuation_ratios", limit=4)
        fallback = [
            RiskItem(
                title="Single-company risk",
                plain_english_explanation=(
                    f"{response.asset.ticker} represents one company, so its filings, execution, customer demand, and "
                    "company-specific news can matter much more than they would inside a diversified ETF."
                ),
                citation_ids=stable_citation_ids,
            ),
            RiskItem(
                title="Business and competition risk",
                plain_english_explanation=(
                    (
                        f"Provider profile fields place {response.asset.ticker} in {sector}"
                        + (f" / {industry}" if industry else "")
                        + ", so beginners should connect the company profile with demand, competition, regulation, and execution risk."
                    )
                    if sector
                    else (
                        "A company's products, services, customer demand, competitors, and execution can change, so "
                        "source-backed business facts should be read as a starting point for understanding the company."
                    )
                ),
                citation_ids=provider_citation_ids or stable_citation_ids,
            ),
            RiskItem(
                title="Financial and valuation risk",
                plain_english_explanation=(
                    (
                        f"Provider-derived valuation rows include {_join_human(valuation_labels)}; those fields can change with price and fundamentals and do not by themselves prove whether the stock is cheap or expensive."
                    )
                    if valuation_labels
                    else (
                        "Reported financial results and valuation context can change over time, and market expectations "
                        "can move faster than the latest filing or provider snapshot."
                    )
                ),
                citation_ids=allowed_citation_ids or stable_citation_ids,
            ),
        ]
        candidates = [
            *fallback,
            RiskItem(
                title="Provider-data limitation",
                plain_english_explanation=(
                    "Some market, profile, and valuation fields are provider-derived local-test context, so unsupported or stale fields should stay labeled instead of becoming conclusions."
                ),
                citation_ids=provider_citation_ids or stable_citation_ids,
            ),
        ]
        return _generated_top_risks(
            response,
            candidates,
            fallback,
            allowed_citation_ids,
            generation_evidence_pack=generation_evidence_pack,
        )
    narrow_or_specialized = _is_narrow_or_specialized_etf(response)
    benchmark = _fact_value(response, "benchmark")
    holdings_count = _fact_value(response, "holdings_count")
    expense_ratio = _fact_value(response, "expense_ratio")
    concentration_summary = (
        f"{response.asset.ticker} tracks {benchmark or 'a narrower or more specialized index segment'}, so a smaller set of companies "
        "or sectors can drive more of the fund's results."
        if narrow_or_specialized
        else (
            f"{response.asset.ticker} may hold {holdings_count or 'many'} stocks, but large companies and larger index weights can still "
            "have an outsized effect on what investors experience."
        )
    )
    concentration_risk = RiskItem(
        title="Concentration risk",
        plain_english_explanation=concentration_summary,
        citation_ids=stable_citation_ids,
    )
    fallback: list[RiskItem] = []
    if narrow_or_specialized:
        fallback.append(concentration_risk)
    fallback.append(
        RiskItem(
            title="Market risk",
            plain_english_explanation=(
                f"{response.asset.ticker} owns a basket of stocks tied to {benchmark or 'its index segment'}, so it can lose value when that market exposure declines."
            ),
            citation_ids=stable_citation_ids,
        )
    )
    if not narrow_or_specialized:
        fallback.append(concentration_risk)
    fallback.append(
        RiskItem(
            title="Tracking risk",
            plain_english_explanation=(
                (
                    f"The fund reports an expense ratio of {expense_ratio}%, and fees, trading, cash, and implementation details can make results differ from the benchmark."
                    if expense_ratio not in (None, "")
                    else "An index ETF tries to follow its benchmark, but fees, trading, cash, and implementation details can make fund results differ from the index."
                )
            ),
            citation_ids=allowed_citation_ids or stable_citation_ids,
        )
    )
    candidates = [
        *fallback,
        RiskItem(
            title="Trading and liquidity context",
            plain_english_explanation=(
                "Quote and volume fields are provider-derived reference data; beginners should keep them separate from issuer facts and avoid treating them as trading instructions."
            ),
            citation_ids=provider_citation_ids or stable_citation_ids,
        ),
        RiskItem(
            title="Methodology evidence limit",
            plain_english_explanation=(
                "Benchmark and prospectus metadata identify the index-tracking context, but complete rebalancing, screening, and methodology details may remain partial in lightweight mode."
            ),
            citation_ids=stable_citation_ids,
        ),
    ]
    return _generated_top_risks(
        response,
        candidates,
        fallback,
        allowed_citation_ids,
        generation_evidence_pack=generation_evidence_pack,
    )


def _generated_top_risks(
    response: LightweightFetchResponse,
    candidates: list[RiskItem],
    fallback: list[RiskItem],
    allowed_citation_ids: list[str],
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[RiskItem]:
    if len(fallback) != 3 or not allowed_citation_ids:
        return fallback[:3]
    try:
        return build_default_summary_generation_service().generate_top_risks(
            asset=response.asset,
            candidate_risks=candidates,
            fallback_risks=fallback,
            allowed_citation_ids=allowed_citation_ids,
            evidence_notes=[diagnostic for diagnostic in _lightweight_evidence_note_candidates(response) if diagnostic],
            generation_evidence_pack=generation_evidence_pack or evidence_pack_from_lightweight_response(response),
        )
    except SummaryGenerationContractError:
        return fallback[:3]


def _is_narrow_or_specialized_etf(response: LightweightFetchResponse) -> bool:
    searchable = " ".join(
        str(value or "")
        for value in [
            response.asset.ticker,
            response.asset.name,
            response.asset.issuer,
            _fact_value(response, "benchmark"),
            _fact_value(response, "etf_manifest_scope_signal"),
            _fact_value(response, "provider_profile_overview"),
        ]
    ).lower()
    narrow_markers = (
        "nasdaq-100",
        "nasdaq 100",
        "sector",
        "technology",
        "semiconductor",
        "xlk",
        "qqq",
        "specialized",
        "theme",
    )
    return any(marker in searchable for marker in narrow_markers)


def _stock_sections(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[OverviewSection]:
    retrieved_at = response.freshness.page_last_updated_at
    filing_citations = _citation_ids_for_fact(response, "latest_sec_filing", stable_citation_ids)
    identity_citations = _citation_ids_for_fact(response, "sec_identity", stable_citation_ids)
    financial_metrics = _stock_metrics(response, stable_citation_ids)
    has_market_reference = bool(provider_citation_ids)
    risks = _top_risks(
        response,
        stable_citation_ids,
        provider_citation_ids,
        generation_evidence_pack=generation_evidence_pack,
    )
    suitability = _suitability_summary(response, stable_citation_ids)
    profile_table = _stock_profile_table(response, provider_citation_ids)
    financial_table = _stock_financial_table(response, stable_citation_ids, provider_citation_ids)
    valuation_table = _stock_valuation_table(response, provider_citation_ids)
    products_items = _stock_products_services_items(response, filing_citations, provider_citation_ids)
    strength_items = _stock_strength_items(response, provider_citation_ids)
    financial_items = _stock_financial_quality_items(
        response,
        stable_citation_ids,
        provider_citation_ids,
        has_provider_snapshot=financial_table is not None,
    )
    valuation_items = _stock_valuation_items(
        response,
        provider_citation_ids,
        has_valuation_table=valuation_table is not None,
        has_market_reference=has_market_reference,
    )
    business_citation_ids = _dedupe([*stable_citation_ids, *((profile_table.citation_ids if profile_table else []))])
    products_citation_ids = _dedupe(citation_id for item in products_items for citation_id in item.citation_ids)
    strength_citation_ids = _dedupe(citation_id for item in strength_items for citation_id in item.citation_ids)
    financial_citation_ids = _dedupe(
        [
            *[citation_id for metric in financial_metrics for citation_id in metric.citation_ids],
            *((financial_table.citation_ids if financial_table else [])),
        ]
    )
    valuation_citation_ids = _dedupe([*provider_citation_ids, *((valuation_table.citation_ids if valuation_table else []))])
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
                    identity_citations,
                    response,
                    as_of_date=_fact_as_of(response, "sec_identity"),
                ),
                _item(
                    "latest_sec_filing",
                    "Latest SEC filing",
                    _latest_filing_summary(response),
                    filing_citations,
                    response,
                    as_of_date=_fact_as_of(response, "latest_sec_filing"),
                ),
            ],
            metrics=[],
            table=profile_table,
            citation_ids=business_citation_ids,
            source_document_ids=_source_ids_for_citations(response, business_citation_ids),
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported,
            as_of_date=response.freshness.facts_as_of,
            retrieved_at=retrieved_at,
        ),
        OverviewSection(
            section_id="products_services",
            title="Products Or Services",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=_stock_products_services_context(response),
            items=products_items,
            metrics=[],
            citation_ids=products_citation_ids,
            source_document_ids=_source_ids_for_citations(response, products_citation_ids),
            freshness_state=FreshnessState.fresh if products_citation_ids else FreshnessState.unknown,
            evidence_state=EvidenceState.mixed,
            as_of_date=_fact_as_of(response, "latest_sec_filing"),
            retrieved_at=retrieved_at,
            limitations="Detailed segment, geography, customer, and competitor evidence is tracked in Evidence Limits when unavailable.",
        ),
        OverviewSection(
            section_id="strengths",
            title="Strengths To Investigate",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=(
                "This section avoids unsupported competitive-advantage claims, but provider-normalized profile, "
                "financial, margin, return, and ownership fields can give beginners concrete questions to investigate."
            ),
            items=strength_items,
            metrics=[],
            citation_ids=strength_citation_ids,
            source_document_ids=_source_ids_for_citations(response, strength_citation_ids),
            freshness_state=FreshnessState.fresh if strength_citation_ids else FreshnessState.unavailable,
            evidence_state=EvidenceState.partial if strength_citation_ids else EvidenceState.insufficient_evidence,
            retrieved_at=retrieved_at,
            limitations="This section avoids moat or strength claims; it lists provider-labeled context for learning questions.",
        ),
        OverviewSection(
            section_id="financial_quality",
            title="Financial Quality",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=_stock_financial_quality_context(response),
            items=financial_items,
            metrics=financial_metrics,
            table=financial_table,
            citation_ids=financial_citation_ids,
            source_document_ids=_source_ids_for_citations(response, financial_citation_ids),
            freshness_state=FreshnessState.fresh if financial_metrics else FreshnessState.unavailable,
            evidence_state=EvidenceState.mixed if financial_metrics else EvidenceState.unavailable,
            as_of_date=_latest_fact_as_of(response, ("latest_revenue_fact", "latest_net_income_fact", "latest_assets_fact")),
            retrieved_at=retrieved_at,
            limitations="Single latest SEC facts plus provider-labeled snapshot rows are shown; audited multi-year trends remain partial.",
        ),
        OverviewSection(
            section_id="valuation_context",
            title="Valuation Context",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.stock],
            beginner_summary=_stock_valuation_context(response),
            items=valuation_items,
            metrics=[_market_metric(response, provider_citation_ids)],
            table=valuation_table,
            citation_ids=valuation_citation_ids,
            source_document_ids=_source_ids_for_citations(response, valuation_citation_ids),
            freshness_state=FreshnessState.fresh if has_market_reference else FreshnessState.unavailable,
            evidence_state=EvidenceState.mixed if has_market_reference else EvidenceState.insufficient_evidence,
            as_of_date=_fact_as_of(response, "provider_market_price"),
            retrieved_at=retrieved_at,
            limitations="Valuation context is intentionally limited to sourced availability and does not label the stock cheap or expensive.",
        ),
        *_stock_provider_metric_sections(response, provider_citation_ids),
        _price_chart_section(response, stable_citation_ids, provider_citation_ids, applies_to=[AssetType.stock]),
        _risk_section(response, risks, applies_to=[AssetType.stock], section_id="top_risks", title="Top Risks"),
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
        _evidence_limits_section(
            response,
            stable_citation_ids,
            provider_citation_ids,
            applies_to=[AssetType.stock],
            generation_evidence_pack=generation_evidence_pack,
        ),
        _educational_suitability_section(
            response,
            suitability,
            citation_ids=stable_citation_ids,
            applies_to=[AssetType.stock],
        ),
    ]
    return _generated_section_summaries(
        response,
        [*sections, *_gap_sections(response)],
        generation_evidence_pack=generation_evidence_pack,
    )


def _etf_sections(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[OverviewSection]:
    retrieved_at = response.freshness.page_last_updated_at
    has_issuer = _has_official_etf_issuer_evidence(response)
    issuer_state = EvidenceState.supported if has_issuer else EvidenceState.partial
    holdings_state = EvidenceState.supported if _has_official_etf_holdings_evidence(response) else EvidenceState.partial
    expense_metric = _expense_ratio_metric(response, stable_citation_ids)
    benchmark_metric = _etf_metric(response, "benchmark", "Benchmark", stable_citation_ids)
    holdings_count_metric = _etf_metric(response, "holdings_count", "Holdings count", stable_citation_ids)
    prospectus_citations = _citation_ids_for_fact(response, "prospectus_reference", stable_citation_ids)
    risks = _top_risks(
        response,
        stable_citation_ids,
        provider_citation_ids,
        generation_evidence_pack=generation_evidence_pack,
    )
    suitability = _suitability_summary(response, stable_citation_ids)
    overview_table = _etf_overview_table(response, stable_citation_ids, provider_citation_ids)
    holdings_table = _etf_holdings_table(response, stable_citation_ids, provider_citation_ids)
    overview_citation_ids = _dedupe([*stable_citation_ids, *((overview_table.citation_ids if overview_table else []))])
    holdings_citation_ids = _dedupe([*stable_citation_ids, *((holdings_table.citation_ids if holdings_table else []))])
    sections = [
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
            metrics=[benchmark_metric] if benchmark_metric.evidence_state is not EvidenceState.unavailable else [],
            table=overview_table,
            citation_ids=overview_citation_ids,
            source_document_ids=_source_ids_for_citations(response, overview_citation_ids),
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
            items=_etf_holdings_items(response, stable_citation_ids, holdings_state),
            metrics=[holdings_count_metric] if holdings_count_metric.evidence_state is not EvidenceState.unavailable else [],
            table=holdings_table,
            citation_ids=holdings_citation_ids,
            source_document_ids=_source_ids_for_citations(response, holdings_citation_ids),
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
        _etf_sector_weightings_section(response, stable_citation_ids, provider_citation_ids),
        _etf_performance_section(response, provider_citation_ids),
        _price_chart_section(response, stable_citation_ids, provider_citation_ids, applies_to=[AssetType.etf]),
        OverviewSection(
            section_id="construction_methodology",
            title="Construction Or Methodology",
            section_type=OverviewSectionType.stable_facts,
            applies_to=[AssetType.etf],
            beginner_summary=_etf_construction_context(response),
            items=_etf_methodology_items(response, stable_citation_ids, prospectus_citations),
            metrics=[],
            citation_ids=_dedupe([*_citation_ids_for_fact(response, "benchmark", stable_citation_ids), *prospectus_citations]),
            source_document_ids=_source_ids_for_citations(
                response,
                _dedupe([*_citation_ids_for_fact(response, "benchmark", stable_citation_ids), *prospectus_citations]),
            ),
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.mixed if has_issuer else EvidenceState.partial,
            as_of_date=response.freshness.facts_as_of,
            retrieved_at=retrieved_at,
            limitations="Full rebalancing, screening, and methodology-document evidence is tracked in Evidence Limits when unavailable.",
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
            items=_etf_cost_trading_items(response, stable_citation_ids, provider_citation_ids),
            metrics=[
                expense_metric,
                _market_metric(response, provider_citation_ids),
            ],
            citation_ids=[*provider_citation_ids, *stable_citation_ids],
            source_document_ids=_source_ids_for_citations(response, [*provider_citation_ids, *stable_citation_ids]),
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.mixed,
            as_of_date=_fact_as_of(response, "provider_market_price"),
            retrieved_at=retrieved_at,
            limitations="Provider-derived market reference is not official issuer evidence.",
        ),
        _risk_section(
            response,
            risks,
            applies_to=[AssetType.etf],
            section_id="etf_specific_risks",
            title="ETF-Specific Risks",
        ),
        OverviewSection(
            section_id="similar_assets_alternatives",
            title="Similar Assets Or Simpler Alternatives",
            section_type=OverviewSectionType.evidence_gap,
            applies_to=[AssetType.etf],
            beginner_summary=_etf_comparison_overlap_context(response),
            items=[
                _gap_item(
                    "similar_assets_gap",
                    "Similar assets and overlap",
                    "Similar ETF, simpler-alternative, and broad-market overlap evidence is unavailable for this page build.",
                    response,
                    evidence_state=EvidenceState.insufficient_evidence,
                )
            ],
            metrics=[],
            citation_ids=[],
            source_document_ids=[],
            freshness_state=FreshnessState.unavailable,
            evidence_state=EvidenceState.insufficient_evidence,
            retrieved_at=retrieved_at,
            limitations="Comparison and overlap context requires verified comparison packs or issuer holdings overlap evidence.",
        ),
        _evidence_limits_section(
            response,
            stable_citation_ids,
            provider_citation_ids,
            applies_to=[AssetType.etf],
            generation_evidence_pack=generation_evidence_pack,
        ),
        _educational_suitability_section(
            response,
            suitability,
            citation_ids=stable_citation_ids,
            applies_to=[AssetType.etf],
        ),
        *_gap_sections(response),
    ]
    return _generated_section_summaries(response, sections, generation_evidence_pack=generation_evidence_pack)


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


def _evidence_limits_section(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
    *,
    applies_to: list[AssetType],
    generation_evidence_pack: dict[str, Any] | None = None,
) -> OverviewSection:
    if response.asset.asset_type is AssetType.stock:
        summary = (
            "Evidence limits are separated from the main risk cards so beginners can distinguish asset risk from "
            "source freshness, provider fallback, and missing-detail warnings."
        )
        items = [
            _item(
                "reported_facts_are_point_in_time",
                "Reported facts are point-in-time",
                (
                    "SEC identity, filing, and XBRL fields are dated evidence. Check filing and period dates before "
                    "treating a metric as the latest full picture."
                ),
                stable_citation_ids,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=response.freshness.facts_as_of,
            ),
            _item(
                "provider_reference_limits",
                "Provider reference limits",
                (
                    "Provider-derived price, profile, valuation, and quote fields are reference context for learning; "
                    "they are not official company filings or a valuation conclusion."
                ),
                provider_citation_ids,
                response,
                evidence_state=EvidenceState.partial if provider_citation_ids else EvidenceState.unavailable,
                as_of_date=_fact_as_of(response, "provider_market_price"),
            ),
        ]
    else:
        issuer_summary = (
            "Official issuer fact-sheet, prospectus, holdings, and exposure fields are dated evidence; check as-of "
            "dates before treating them as current."
            if _has_official_etf_issuer_evidence(response)
            else (
                "Issuer evidence is partial in this lightweight response, so manifest and provider fallback fields "
                "are labeled instead of being blended into the ETF's asset-risk cards."
            )
        )
        summary = (
            "Evidence limits are separated from ETF risks so beginners can see what the fund risks are before reading "
            "source freshness, issuer-coverage, and provider-fallback warnings."
        )
        items = [
            _item(
                "issuer_facts_are_point_in_time",
                "Issuer facts are point-in-time",
                issuer_summary,
                stable_citation_ids,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=response.freshness.holdings_as_of or response.freshness.facts_as_of,
            ),
            _item(
                "provider_fallback_limits",
                "Provider fallback limits",
                (
                    "Provider-derived ETF fields are source-labeled local-test data and should not be confused with "
                    "official issuer fact sheets, holdings files, or prospectuses."
                ),
                provider_citation_ids,
                response,
                evidence_state=EvidenceState.partial if provider_citation_ids else EvidenceState.unavailable,
                as_of_date=_fact_as_of(response, "provider_market_price"),
            ),
        ]

    if response.gaps:
        gap_names = ", ".join(gap.field_name.replace("_", " ") for gap in response.gaps[:3])
        items.append(
            _gap_item(
                "remaining_evidence_gaps",
                "Remaining evidence gaps",
                f"The lightweight response still labels these missing or partial fields separately: {gap_names}.",
                response,
                evidence_state=EvidenceState.partial,
            )
        )

    citation_ids = _dedupe(citation_id for item in items for citation_id in item.citation_ids)
    section_freshness = FreshnessState.fresh if citation_ids else FreshnessState.unavailable
    summary = _generated_deep_dive_summary(
        response,
        section_id="evidence_limits",
        title="Evidence Limits",
        base_summary=summary,
        citation_ids=citation_ids,
        evidence_state=EvidenceState.partial,
        generation_evidence_pack=generation_evidence_pack,
    )
    return OverviewSection(
        section_id="evidence_limits",
        title="Evidence Limits",
        section_type=OverviewSectionType.evidence_gap,
        applies_to=applies_to,
        beginner_summary=summary,
        items=items,
        metrics=[],
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=section_freshness,
        evidence_state=EvidenceState.partial,
        as_of_date=response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="This section explains source and freshness limits; it is not one of the asset's Top 3 Risks.",
    )


def _generated_deep_dive_summary(
    response: LightweightFetchResponse,
    *,
    section_id: str,
    title: str,
    base_summary: str | None,
    citation_ids: list[str],
    evidence_state: EvidenceState,
    evidence_notes: list[str] | None = None,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> str | None:
    evidence_pack = generation_evidence_pack or evidence_pack_from_lightweight_response(response)
    try:
        return build_default_summary_generation_service().generate_deep_dive_summary(
            asset=response.asset,
            section_id=section_id,
            title=title,
            base_summary=base_summary,
            citation_ids=citation_ids,
            evidence_state=evidence_state.value,
            evidence_notes=evidence_notes or [],
            generation_evidence_pack=evidence_pack,
        )
    except SummaryGenerationContractError:
        return base_summary


def _generated_section_summaries(
    response: LightweightFetchResponse,
    sections: list[OverviewSection],
    *,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[OverviewSection]:
    refined: list[OverviewSection] = []
    for section in sections:
        if section.section_type in {OverviewSectionType.risk, OverviewSectionType.educational_suitability}:
            refined.append(section)
            continue
        summary = _generated_deep_dive_summary(
            response,
            section_id=section.section_id,
            title=section.title,
            base_summary=section.beginner_summary,
            citation_ids=section.citation_ids,
            evidence_state=section.evidence_state,
            evidence_notes=_section_evidence_notes(section),
            generation_evidence_pack=generation_evidence_pack,
        )
        refined.append(section.model_copy(update={"beginner_summary": summary}))
    return refined


def _section_evidence_notes(section: OverviewSection) -> list[str]:
    notes: list[str] = [
        f"section_id={section.section_id}",
        f"evidence_state={section.evidence_state.value}",
    ]
    if section.items:
        notes.append(
            "items="
            + "; ".join(
                f"{item.title}: {_short_value(item.summary)}"
                for item in section.items[:4]
                if item.summary
            )
        )
    if section.metrics:
        metric_text = "; ".join(
            f"{metric.label}: {_short_value(metric.value)}"
            for metric in section.metrics[:4]
            if metric.value not in (None, "")
        )
        if metric_text:
            notes.append(f"metrics={metric_text}")
    if section.table is not None:
        row_text = "; ".join(
            f"{row.label or row.row_id}: {_short_value(row.values.get('value'))}"
            for row in section.table.rows[:5]
            if row.values.get("value") not in (None, "")
        )
        if row_text:
            notes.append(f"table={section.table.title}: {row_text}")
    if section.chart is not None and section.chart.points:
        first = section.chart.points[0]
        last = section.chart.points[-1]
        notes.append(
            f"chart={section.chart.range} {section.chart.interval}: first close {first.close}, latest close {last.close}"
        )
    if section.limitations and section.section_id == "evidence_limits":
        notes.append(f"limitations={section.limitations}")
    return notes


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


def _gap_item(
    item_id: str,
    title: str,
    summary: str,
    response: LightweightFetchResponse,
    *,
    evidence_state: EvidenceState = EvidenceState.unavailable,
    freshness_state: FreshnessState = FreshnessState.unavailable,
    limitations: str | None = None,
) -> OverviewSectionItem:
    return OverviewSectionItem(
        item_id=item_id,
        title=title,
        summary=summary,
        citation_ids=[],
        source_document_ids=[],
        freshness_state=freshness_state,
        evidence_state=evidence_state,
        as_of_date=None,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=limitations or summary,
    )


def _stock_financial_item(
    response: LightweightFetchResponse,
    field_name: str,
    title: str,
    stable_citation_ids: list[str],
) -> OverviewSectionItem:
    value = _fact_value(response, field_name)
    if isinstance(value, dict) and value.get("value") is not None:
        citation_ids = _citation_ids_for_fact(response, field_name, stable_citation_ids)
        label = value.get("label") or title
        period = value.get("end") or value.get("filed") or "unknown period"
        return _item(
            field_name,
            title,
            f"SEC/XBRL reports {label} of {_format_fact_number(value.get('value'))} {value.get('unit') or ''} for period {period}.",
            citation_ids,
            response,
            as_of_date=value.get("end") or _fact_as_of(response, field_name),
        )
    return _gap_item(
        field_name,
        title,
        f"{title} is unavailable in the lightweight SEC/XBRL response.",
        response,
    )


def _stock_metrics(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
) -> list[OverviewMetric]:
    metrics: list[OverviewMetric] = []
    for field_name, label in (
        ("latest_revenue_fact", "Latest reported revenue"),
        ("latest_net_income_fact", "Latest reported net income"),
        ("latest_assets_fact", "Latest reported assets"),
    ):
        value = _fact_value(response, field_name)
        if isinstance(value, dict) and value.get("value") is not None:
            citation_ids = _citation_ids_for_fact(response, field_name, stable_citation_ids)
            metrics.append(
                OverviewMetric(
                    metric_id=field_name,
                    label=label,
                    value=value.get("value"),
                    unit=value.get("unit"),
                    citation_ids=citation_ids,
                    source_document_ids=_source_ids_for_citations(response, citation_ids),
                    freshness_state=FreshnessState.fresh,
                    evidence_state=EvidenceState.supported,
                    as_of_date=value.get("end"),
                    retrieved_at=response.freshness.page_last_updated_at,
                )
            )
    return metrics


def _etf_metric(
    response: LightweightFetchResponse,
    field_name: str,
    label: str,
    stable_citation_ids: list[str],
) -> OverviewMetric:
    fact = _fact(response, field_name)
    citation_ids = _citation_ids_for_fact(response, field_name, stable_citation_ids)
    if fact is not None:
        return OverviewMetric(
            metric_id=field_name,
            label=label,
            value=fact.value,
            unit="approximate holdings" if field_name == "holdings_count" else getattr(fact, "unit", None),
            citation_ids=citation_ids,
            source_document_ids=_source_ids_for_citations(response, citation_ids),
            freshness_state=fact.freshness_state,
            evidence_state=fact.evidence_state,
            as_of_date=fact.as_of_date,
            retrieved_at=fact.retrieved_at or response.freshness.page_last_updated_at,
            limitations=fact.limitations,
        )
    return OverviewMetric(
        metric_id=field_name,
        label=label,
        value="Unavailable",
        unit=None,
        citation_ids=[],
        source_document_ids=[],
        freshness_state=FreshnessState.unavailable,
        evidence_state=EvidenceState.unavailable,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=f"{label} is unavailable in the lightweight response.",
    )


def _etf_holdings_items(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    holdings_state: EvidenceState,
) -> list[OverviewSectionItem]:
    items = [
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
    ]
    holdings_count = _fact(response, "holdings_count")
    if holdings_count is not None:
        citation_ids = _citation_ids_for_fact(response, "holdings_count", stable_citation_ids)
        items.append(
            _item(
                "holdings_count",
                "Holdings count",
                f"Official issuer metadata lists about {holdings_count.value} holdings.",
                citation_ids,
                response,
                as_of_date=holdings_count.as_of_date,
            )
        )
    for fact in response.facts:
        if not (
            fact.field_name.startswith("top_holding_")
            or fact.field_name.endswith("_exposure")
            or fact.field_name == "equity_exposure"
        ):
            continue
        items.append(
            _item(
                fact.field_name,
                fact.field_name.replace("_", " ").title(),
                _etf_holding_or_exposure_summary(fact.value),
                _citation_ids_for_fact(response, fact.field_name, stable_citation_ids),
                response,
                as_of_date=fact.as_of_date,
            )
        )
    items.append(
        _gap_item(
            "remaining_holdings_exposure_gap",
            "Remaining holdings and exposure gaps",
            "Top-10 weights, top-10 concentration, complete sector or country breakdowns, and largest-position verification remain incomplete in the lightweight response.",
            response,
            evidence_state=EvidenceState.partial,
        )
    )
    return items


def _stock_products_services_items(
    response: LightweightFetchResponse,
    filing_citations: list[str],
    provider_citation_ids: list[str],
) -> list[OverviewSectionItem]:
    items = [
        _item(
            "filing_narrative_pointer",
            "Filing narrative pointer",
            (
                "The SEC filing reference anchors the official company source trail. Use it with the provider profile "
                "context to separate the company's stable business description from recent headlines."
            ),
            filing_citations,
            response,
            evidence_state=EvidenceState.partial,
            as_of_date=_fact_as_of(response, "latest_sec_filing"),
            limitations="Detailed segment, revenue-driver, geography, customer, and competitor parsing may remain incomplete.",
        )
    ]
    provider_summary = _provider_profile_context_summary(response)
    if provider_summary:
        items.append(
            _item(
                "provider_profile_context",
                "Provider profile context",
                provider_summary,
                provider_citation_ids,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=_fact_as_of(response, "provider_profile_overview"),
                limitations="Provider-derived profile context is labeled fallback and should be checked against official company filings when available.",
            )
        )
    else:
        items.append(
            _gap_item(
                "products_services_gap",
                "Products and services detail",
                "Source-backed product, segment, revenue-driver, geographic-exposure, and competitor detail is unavailable for this page build.",
                response,
            )
        )
    return items


def _stock_strength_items(
    response: LightweightFetchResponse,
    provider_citation_ids: list[str],
) -> list[OverviewSectionItem]:
    items: list[OverviewSectionItem] = []
    metric_titles = _provider_metric_group_titles(
        response,
        ("price_performance", "income_statement", "balance_sheet", "cash_flow", "margins_returns_ownership"),
    )
    if metric_titles:
        items.append(
            _item(
                "provider_learning_context",
                "Provider learning context",
                (
                    "The dashboard includes provider-normalized "
                    + _join_human(metric_titles)
                    + " rows. Treat them as learning context for questions about scale, profitability, cash generation, "
                    "balance-sheet position, and ownership, not as claims that the company has durable strengths."
                ),
                provider_citation_ids,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=_fact_as_of(response, "provider_stock_metric_groups"),
                limitations="Provider-derived metrics are educational context only and are not a recommendation signal.",
            )
        )
    profile_summary = _provider_profile_context_summary(response)
    if profile_summary:
        items.append(
            _item(
                "provider_profile_checkpoints",
                "Profile checkpoints",
                profile_summary,
                provider_citation_ids,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=_fact_as_of(response, "provider_profile_overview"),
                limitations="Profile fields are fallback context and should be checked against official company sources when available.",
            )
        )
    if not items:
        items.append(
            _gap_item(
                "strengths_gap",
                "Strengths evidence",
                "No source-backed strengths are generated from the lightweight facts; this section stays unavailable instead of filling gaps with model memory.",
                response,
                evidence_state=EvidenceState.insufficient_evidence,
            )
        )
    return items


def _stock_financial_quality_items(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
    *,
    has_provider_snapshot: bool,
) -> list[OverviewSectionItem]:
    items = [
        _stock_financial_item(response, "latest_revenue_fact", "Latest reported revenue", stable_citation_ids),
        _stock_financial_item(response, "latest_net_income_fact", "Latest reported net income", stable_citation_ids),
        _stock_financial_item(response, "latest_assets_fact", "Latest reported assets", stable_citation_ids),
    ]
    if has_provider_snapshot:
        group_titles = _provider_metric_group_titles(
            response,
            ("income_statement", "balance_sheet", "cash_flow", "margins_returns_ownership"),
        )
        if group_titles:
            items.append(
                _item(
                    "provider_financial_snapshot",
                    "Provider financial snapshot",
                    (
                        "The dashboard adds provider-normalized "
                        + _join_human(group_titles)
                        + " rows alongside SEC latest facts. These rows help fill the local lightweight view while audited "
                        "multi-year trend analysis remains partial."
                    ),
                    provider_citation_ids,
                    response,
                    evidence_state=EvidenceState.partial,
                    as_of_date=_fact_as_of(response, "provider_stock_metric_groups"),
                    limitations="Provider-derived financial rows are labeled fallback and may be incomplete.",
                )
            )
    else:
        items.append(
            _gap_item(
                "financial_quality_trend_gap",
                "Remaining financial-quality trend gaps",
                "The lightweight response has latest SEC/XBRL facts, but it does not yet build multi-year revenue, EPS, margins, cash-flow, debt, cash, ROE, or ROIC trends.",
                response,
                evidence_state=EvidenceState.partial,
            )
        )
    return items


def _stock_valuation_items(
    response: LightweightFetchResponse,
    provider_citation_ids: list[str],
    *,
    has_valuation_table: bool,
    has_market_reference: bool,
) -> list[OverviewSectionItem]:
    items = [
        _item(
            "provider_market_reference",
            "Provider market reference",
            _provider_reference_summary(response),
            provider_citation_ids,
            response,
            evidence_state=EvidenceState.partial if has_market_reference else EvidenceState.unavailable,
            as_of_date=_fact_as_of(response, "provider_market_price"),
            limitations="Provider-derived market reference is not a valuation conclusion or recommendation.",
        )
    ]
    if has_valuation_table:
        labels = _provider_metric_labels(response, "valuation_ratios", limit=5)
        label_text = _join_human(labels) if labels else "valuation ratio"
        items.append(
            _item(
                "provider_valuation_ratios",
                "Provider valuation ratios",
                (
                    f"Provider-derived valuation rows include {label_text}. They are shown as context for learning "
                    "how valuation vocabulary works, not as cheap-or-expensive labels."
                ),
                provider_citation_ids,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=_fact_as_of(response, "provider_stock_metric_groups"),
                limitations="Provider-derived ratios are context only and do not include peer or own-history judgment.",
            )
        )
    else:
        items.append(
            _gap_item(
                "valuation_metrics_gap",
                "Valuation metrics",
                "P/E, forward P/E, price/sales, price/free-cash-flow, peer context, and own-history context are unavailable in this lightweight response.",
                response,
                evidence_state=EvidenceState.insufficient_evidence,
            )
        )
    return items


def _provider_profile_context_summary(response: LightweightFetchResponse) -> str | None:
    profile = _fact_value(response, "provider_profile_overview")
    if not isinstance(profile, dict):
        return None
    parts: list[str] = []
    sector = profile.get("sector")
    industry = profile.get("industry")
    ceo = profile.get("ceo")
    if sector and industry:
        parts.append(f"Provider profile fields place {response.asset.ticker} in the {sector} sector and {industry} industry")
    elif sector:
        parts.append(f"Provider profile fields place {response.asset.ticker} in the {sector} sector")
    elif industry:
        parts.append(f"Provider profile fields place {response.asset.ticker} in the {industry} industry")
    if ceo:
        parts.append(f"Provider profile fields list {ceo} as CEO")
    business_summary = (
        profile.get("business_summary")
        or profile.get("long_business_summary")
        or profile.get("longBusinessSummary")
    )
    if business_summary:
        parts.append("Provider profile summary says " + _short_value(business_summary))
    available_metrics = [
        label
        for key, label in (
            ("market_cap", "market cap"),
            ("enterprise_value", "enterprise value"),
            ("revenue_ttm", "revenue TTM"),
            ("free_cash_flow", "free cash flow"),
        )
        if profile.get(key) not in (None, "")
    ]
    if available_metrics:
        parts.append("The dashboard also normalizes " + _join_human(available_metrics) + " when available")
    if not parts:
        return None
    return ". ".join(parts) + "."


def _provider_metric_group_titles(response: LightweightFetchResponse, group_ids: tuple[str, ...]) -> list[str]:
    groups = _provider_metric_groups(response)
    titles: list[str] = []
    for group_id in group_ids:
        group = next((item for item in groups if item.get("group_id") == group_id), None)
        if not group:
            continue
        has_metric = any(
            isinstance(metric, dict) and metric.get("value") not in (None, "")
            for metric in group.get("metrics") or []
        )
        if has_metric:
            titles.append(str(group.get("title") or group_id.replace("_", " ").title()))
    return titles


def _provider_metric_labels(response: LightweightFetchResponse, group_id: str, *, limit: int) -> list[str]:
    group = next((item for item in _provider_metric_groups(response) if item.get("group_id") == group_id), None)
    if not group:
        return []
    labels: list[str] = []
    for metric in group.get("metrics") or []:
        if isinstance(metric, dict) and metric.get("value") not in (None, ""):
            labels.append(str(metric.get("label") or metric.get("metric_id") or "metric"))
        if len(labels) >= limit:
            break
    return labels


def _join_human(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _etf_methodology_items(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    prospectus_citations: list[str],
) -> list[OverviewSectionItem]:
    benchmark_citations = _citation_ids_for_fact(response, "benchmark", stable_citation_ids)
    citations = _dedupe([*benchmark_citations, *prospectus_citations])
    return [
        _item(
            "index_tracking",
            "Index tracking",
            _etf_benchmark_summary(response),
            benchmark_citations,
            response,
            evidence_state=EvidenceState.supported if _fact(response, "benchmark") else EvidenceState.unavailable,
            as_of_date=_fact_as_of(response, "benchmark"),
        ),
        _item(
            "prospectus_reference",
            "Prospectus reference",
            _etf_prospectus_reference(response, prospectus_citations).value,
            prospectus_citations,
            response,
            evidence_state=EvidenceState.supported if _fact(response, "prospectus_reference") else EvidenceState.unavailable,
            as_of_date=_fact_as_of(response, "prospectus_reference"),
        ),
        _item(
            "methodology_scope_note",
            "Methodology scope note",
            (
                "Benchmark and prospectus metadata explain the fund's core index-tracking context. Rebalancing "
                "frequency, screening rules, and methodology documents need a dedicated issuer methodology source "
                "before this section can go deeper."
            ),
            citations,
            response,
            evidence_state=EvidenceState.partial,
            as_of_date=response.freshness.facts_as_of,
            limitations="Detailed methodology depth depends on issuer methodology evidence beyond benchmark and prospectus metadata.",
        ),
    ]


def _etf_cost_trading_items(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> list[OverviewSectionItem]:
    items = [
        _item(
            "provider_reference",
            "Provider reference",
            _provider_reference_summary(response),
            provider_citation_ids,
            response,
            evidence_state=EvidenceState.partial,
            as_of_date=_fact_as_of(response, "provider_market_price"),
        )
    ]
    quote_labels = _quote_stat_metric_labels(response, limit=6)
    if quote_labels:
        citations = _dedupe([*provider_citation_ids, *_citation_ids_for_fact(response, "expense_ratio", stable_citation_ids)])
        items.append(
            _item(
                "quote_stats_context",
                "Quote stats context",
                (
                    "The dashboard includes "
                    + _join_human(quote_labels)
                    + " rows from normalized quote and fund stats. Official expense-ratio facts override provider "
                    "fallback where available."
                ),
                citations,
                response,
                evidence_state=EvidenceState.partial,
                as_of_date=_fact_as_of(response, "provider_quote_stats") or response.freshness.facts_as_of,
                limitations="Provider-derived quote stats are reference data and not trading guidance.",
            )
        )
    else:
        items.append(
            _gap_item(
                "premium_discount_or_spread",
                "Premium, discount, or spread",
                _gap_message(response, "premium_discount_or_spread")
                or "Premium, discount, bid-ask spread, and average-volume fields are unavailable in this lightweight response.",
                response,
            )
        )
    return items


def _quote_stat_metric_labels(response: LightweightFetchResponse, *, limit: int) -> list[str]:
    provider_rows = _merged_quote_stat_rows(response)
    labels: list[str] = []
    for row in provider_rows:
        if not isinstance(row, dict) or row.get("value") in (None, ""):
            continue
        label = str(row.get("label") or row.get("metric_id") or "quote stat")
        if label not in labels:
            labels.append(label)
        if len(labels) >= limit:
            break
    if _fact_value(response, "expense_ratio") not in (None, "") and "Expense Ratio (net)" not in labels:
        labels.append("Expense Ratio (net)")
    return labels[:limit]


def _stock_profile_table(response: LightweightFetchResponse, provider_citation_ids: list[str]) -> OverviewTable | None:
    profile = _fact_value(response, "provider_profile_overview")
    if not isinstance(profile, dict):
        return None
    rows = [
        _simple_table_row(response, "sector", "Sector", profile.get("sector"), provider_citation_ids),
        _simple_table_row(response, "industry", "Industry", profile.get("industry"), provider_citation_ids),
        _simple_table_row(response, "ceo", "CEO", profile.get("ceo"), provider_citation_ids),
        _simple_table_row(response, "market_cap", "Market cap", _metric_display(profile.get("market_cap")), provider_citation_ids),
        _simple_table_row(
            response,
            "enterprise_value",
            "Enterprise value",
            _metric_display(profile.get("enterprise_value")),
            provider_citation_ids,
        ),
        _simple_table_row(response, "trailing_pe", "P/E", _metric_display(profile.get("trailing_pe")), provider_citation_ids),
        _simple_table_row(response, "forward_pe", "Forward P/E", _metric_display(profile.get("forward_pe")), provider_citation_ids),
        _simple_table_row(response, "eps_ttm", "EPS TTM", _metric_display(profile.get("eps_ttm")), provider_citation_ids),
        _simple_table_row(
            response,
            "dividend_yield",
            "Dividend yield",
            _metric_display(profile.get("dividend_yield")),
            provider_citation_ids,
        ),
    ]
    rows = [row for row in rows if row.values.get("value") not in (None, "")]
    return _overview_table(
        response,
        table_id="stock_profile_snapshot",
        title="Stock Profile Snapshot",
        rows=rows,
        citation_ids=provider_citation_ids,
        evidence_state=EvidenceState.partial,
        limitations="Provider-derived profile fields are labeled fallback; SEC identity and filing facts remain the official backbone.",
    )


def _stock_financial_table(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> OverviewTable | None:
    rows: list[OverviewTableRow] = []
    for field_name, label in (
        ("latest_revenue_fact", "SEC latest revenue"),
        ("latest_net_income_fact", "SEC latest net income"),
        ("latest_assets_fact", "SEC latest assets"),
    ):
        value = _fact_value(response, field_name)
        if isinstance(value, dict) and value.get("value") is not None:
            rows.append(
                _simple_table_row(
                    response,
                    field_name,
                    label,
                    _format_fact_number(value.get("value")) + (f" {value.get('unit')}" if value.get("unit") else ""),
                    _citation_ids_for_fact(response, field_name, stable_citation_ids),
                    as_of_date=value.get("end"),
                    evidence_state=EvidenceState.supported,
                )
            )
    for group_id in ("income_statement", "balance_sheet", "cash_flow", "margins_returns_ownership"):
        rows.extend(_metric_rows_from_provider_group(response, group_id, provider_citation_ids))
    if not rows:
        return None
    citation_ids = _dedupe(citation_id for row in rows for citation_id in row.citation_ids)
    return _overview_table(
        response,
        table_id="stock_financial_snapshot",
        title="Stock Financial Snapshot",
        rows=rows,
        citation_ids=citation_ids,
        evidence_state=EvidenceState.mixed,
        limitations="Combines SEC latest facts with provider-labeled fallback metrics where available.",
    )


def _stock_valuation_table(response: LightweightFetchResponse, provider_citation_ids: list[str]) -> OverviewTable | None:
    rows = _metric_rows_from_provider_group(response, "valuation_ratios", provider_citation_ids)
    if not rows:
        return None
    return _overview_table(
        response,
        table_id="stock_valuation_ratios",
        title="Valuation Ratios",
        rows=rows,
        citation_ids=_dedupe(citation_id for row in rows for citation_id in row.citation_ids),
        evidence_state=EvidenceState.partial,
        limitations="Provider-derived ratios are context only and are not cheap/expensive labels or recommendations.",
    )


def _stock_provider_metric_sections(
    response: LightweightFetchResponse,
    provider_citation_ids: list[str],
) -> list[OverviewSection]:
    sections: list[OverviewSection] = []
    for group in _provider_metric_groups(response):
        group_id = str(group.get("group_id") or "")
        if group_id in {"profile", "valuation_ratios"}:
            continue
        rows = _metric_rows_from_provider_group(response, group_id, provider_citation_ids)
        if not rows:
            continue
        citation_ids = _dedupe(citation_id for row in rows for citation_id in row.citation_ids)
        title = str(group.get("title") or group_id.replace("_", " ").title())
        sections.append(
            OverviewSection(
                section_id=f"provider_{group_id}",
                title=title,
                section_type=OverviewSectionType.stable_facts,
                applies_to=[AssetType.stock],
                beginner_summary=f"{title} is shown from provider-derived normalized fields when available, with SEC facts kept separate.",
                items=[],
                metrics=[],
                table=_overview_table(
                    response,
                    table_id=f"provider_{group_id}",
                    title=title,
                    rows=rows,
                    citation_ids=citation_ids,
                    evidence_state=EvidenceState.partial,
                    limitations="Provider-derived stock metrics are labeled fallback and may be incomplete.",
                ),
                citation_ids=citation_ids,
                source_document_ids=_source_ids_for_citations(response, citation_ids),
                freshness_state=FreshnessState.fresh,
                evidence_state=EvidenceState.partial,
                as_of_date=_fact_as_of(response, "provider_stock_metric_groups"),
                retrieved_at=response.freshness.page_last_updated_at,
                limitations="Provider-derived metrics are displayed for education only, not as decision rules.",
            )
        )
    return sections


def _etf_overview_table(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> OverviewTable | None:
    profile = _fact_value(response, "provider_profile_overview")
    profile = profile if isinstance(profile, dict) else {}
    rows = [
        _simple_table_row(response, "benchmark", "Benchmark", _fact_value(response, "benchmark"), _citation_ids_for_fact(response, "benchmark", stable_citation_ids), evidence_state=EvidenceState.supported),
        _simple_table_row(response, "expense_ratio", "Expense ratio", _percent_text(_fact_value(response, "expense_ratio")), _citation_ids_for_fact(response, "expense_ratio", stable_citation_ids), evidence_state=EvidenceState.supported),
        _simple_table_row(response, "holdings_count", "Holdings count", _fact_value(response, "holdings_count"), _citation_ids_for_fact(response, "holdings_count", stable_citation_ids), evidence_state=EvidenceState.supported),
        _simple_table_row(response, "category", "Category", profile.get("category"), provider_citation_ids, evidence_state=EvidenceState.partial),
        _simple_table_row(response, "fund_family", "Fund family", profile.get("fund_family") or response.asset.issuer, provider_citation_ids, evidence_state=EvidenceState.partial),
        _simple_table_row(response, "net_assets", "Net assets / AUM", _metric_display(profile.get("net_assets")), provider_citation_ids, evidence_state=EvidenceState.partial),
        _simple_table_row(response, "ytd_return", "YTD daily total return", _metric_display(profile.get("ytd_return")), provider_citation_ids, evidence_state=EvidenceState.partial),
        _simple_table_row(response, "yield", "Yield", _metric_display(profile.get("yield")), provider_citation_ids, evidence_state=EvidenceState.partial),
        _simple_table_row(response, "legal_type", "Legal type", profile.get("legal_type"), provider_citation_ids, evidence_state=EvidenceState.partial),
    ]
    rows = [row for row in rows if row.values.get("value") not in (None, "")]
    if not rows:
        return None
    citation_ids = _dedupe(citation_id for row in rows for citation_id in row.citation_ids)
    return _overview_table(
        response,
        table_id="etf_overview",
        title="ETF Overview",
        rows=rows,
        citation_ids=citation_ids,
        evidence_state=EvidenceState.mixed,
        limitations="Official issuer facts are preferred; provider fields fill overview gaps with labels.",
    )


def _etf_holdings_table(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> OverviewTable | None:
    rows: list[OverviewTableRow] = []
    official_holdings: list[dict[str, Any]] = []
    official_by_symbol: dict[str, dict[str, Any]] = {}
    seen_symbols: set[str] = set()
    for fact in response.facts:
        if not fact.field_name.startswith("top_holding_") or not isinstance(fact.value, dict):
            continue
        symbol = str(fact.value.get("holding_ticker") or "").strip().upper()
        name = str(fact.value.get("name") or symbol or fact.field_name).strip()
        official_holding = {
            "row_id": fact.field_name,
            "symbol": symbol,
            "name": name,
            "weight": fact.value.get("weight"),
            "citation_ids": _citation_ids_for_fact(response, fact.field_name, stable_citation_ids),
            "as_of_date": fact.as_of_date,
        }
        official_holdings.append(official_holding)
        if symbol:
            official_by_symbol[symbol] = official_holding
    provider_holdings = _fact_value(response, "provider_top_holdings")
    if isinstance(provider_holdings, list):
        for item in provider_holdings:
            if not isinstance(item, dict) or len(rows) >= 10:
                continue
            symbol = str(item.get("symbol") or "").strip().upper()
            if symbol and symbol in seen_symbols:
                continue
            official_holding = official_by_symbol.get(symbol)
            if symbol:
                seen_symbols.add(symbol)
            row_rank = int(item.get("rank") or len(rows) + 1)
            if official_holding:
                rows.append(
                    _holding_table_row(
                        response,
                        row_id=str(official_holding["row_id"]),
                        rank=row_rank,
                        symbol=str(official_holding["symbol"]),
                        name=str(official_holding["name"]),
                        weight=official_holding["weight"],
                        citation_ids=list(official_holding["citation_ids"]),
                        as_of_date=official_holding["as_of_date"],
                        evidence_state=EvidenceState.supported,
                    )
                )
                continue
            rows.append(
                _holding_table_row(
                    response,
                    row_id=f"provider_holding_{len(rows) + 1}",
                    rank=row_rank,
                    symbol=symbol,
                    name=str(item.get("name") or symbol or f"Holding {len(rows) + 1}"),
                    weight=item.get("weight"),
                    citation_ids=provider_citation_ids,
                    as_of_date=_fact_as_of(response, "provider_top_holdings"),
                    evidence_state=EvidenceState.partial,
                    limitations="Provider-derived fallback row.",
                )
            )
    for official_holding in official_holdings:
        if len(rows) >= 10:
            break
        symbol = str(official_holding["symbol"])
        if symbol and symbol in seen_symbols:
            continue
        if symbol:
            seen_symbols.add(symbol)
        rows.append(
            _holding_table_row(
                response,
                row_id=str(official_holding["row_id"]),
                rank=len(rows) + 1,
                symbol=symbol,
                name=str(official_holding["name"]),
                weight=official_holding["weight"],
                citation_ids=list(official_holding["citation_ids"]),
                as_of_date=official_holding["as_of_date"],
                evidence_state=EvidenceState.supported,
            )
        )
    if not rows:
        return None
    total = sum(float(row.values.get("weight") or 0) for row in rows if isinstance(row.values.get("weight"), (int, float)))
    title = f"Top Holdings ({round(total, 2)}% shown)" if total else "Top Holdings"
    citation_ids = _dedupe(citation_id for row in rows for citation_id in row.citation_ids)
    return OverviewTable(
        table_id="top_holdings",
        title=title,
        columns=[
            OverviewTableColumn(column_id="rank", label="#", value_type="number", align="right"),
            OverviewTableColumn(column_id="symbol", label="Symbol"),
            OverviewTableColumn(column_id="name", label="Company"),
            OverviewTableColumn(column_id="weight", label="% Assets", value_type="percent", align="right"),
        ],
        rows=rows,
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.supported if len(rows) >= 10 and all(row.evidence_state is EvidenceState.supported for row in rows) else EvidenceState.mixed,
        as_of_date=response.freshness.holdings_as_of or _fact_as_of(response, "provider_top_holdings"),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="Official issuer holdings win by symbol; provider rows fill missing top-holding slots and stay labeled fallback.",
    )


def _etf_sector_weightings_section(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> OverviewSection:
    table = _etf_sector_weightings_table(response, stable_citation_ids, provider_citation_ids)
    citation_ids = table.citation_ids if table else []
    return OverviewSection(
        section_id="sector_weightings",
        title="Sector Weightings",
        section_type=OverviewSectionType.stable_facts,
        applies_to=[AssetType.etf],
        beginner_summary=(
            f"{response.asset.ticker} sector weights are shown when issuer exposure rows or provider fallback sectors are available."
        ),
        items=[],
        metrics=[],
        table=table,
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh if table else FreshnessState.unavailable,
        evidence_state=table.evidence_state if table else EvidenceState.unavailable,
        as_of_date=table.as_of_date if table else None,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=table.limitations if table else "Sector weighting evidence is unavailable in the lightweight response.",
    )


def _etf_sector_weightings_table(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> OverviewTable | None:
    rows: list[OverviewTableRow] = []
    seen: set[str] = set()
    for fact in response.facts:
        if not isinstance(fact.value, dict) or fact.value.get("exposure_category") != "sector":
            continue
        sector = str(fact.value.get("name") or fact.field_name).replace(" sector exposure", "").title()
        seen.add(sector.lower())
        rows.append(
            _sector_table_row(
                response,
                row_id=fact.field_name,
                sector=sector,
                weight=fact.value.get("weight"),
                citation_ids=_citation_ids_for_fact(response, fact.field_name, stable_citation_ids),
                as_of_date=fact.as_of_date,
                evidence_state=EvidenceState.supported,
            )
        )
    provider_sectors = _fact_value(response, "provider_sector_weightings")
    if isinstance(provider_sectors, list):
        for item in provider_sectors:
            if not isinstance(item, dict):
                continue
            sector = str(item.get("sector") or "").strip()
            if not sector or sector.lower() in seen:
                continue
            seen.add(sector.lower())
            rows.append(
                _sector_table_row(
                    response,
                    row_id=f"provider_sector_{len(rows) + 1}",
                    sector=sector,
                    weight=item.get("weight"),
                    citation_ids=provider_citation_ids,
                    as_of_date=_fact_as_of(response, "provider_sector_weightings"),
                    evidence_state=EvidenceState.partial,
                    limitations="Provider-derived fallback row.",
                )
            )
    if not rows:
        return None
    citation_ids = _dedupe(citation_id for row in rows for citation_id in row.citation_ids)
    return OverviewTable(
        table_id="sector_weightings",
        title="Sector Weightings",
        columns=[
            OverviewTableColumn(column_id="sector", label="Sector"),
            OverviewTableColumn(column_id="weight", label=f"{response.asset.ticker}", value_type="percent", align="right"),
        ],
        rows=rows,
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.supported if all(row.evidence_state is EvidenceState.supported for row in rows) else EvidenceState.mixed,
        as_of_date=response.freshness.holdings_as_of or _fact_as_of(response, "provider_sector_weightings"),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="Official issuer sector rows are preferred; provider sector rows are labeled fallback.",
    )


def _etf_performance_section(response: LightweightFetchResponse, provider_citation_ids: list[str]) -> OverviewSection:
    table = _etf_performance_table(response, provider_citation_ids)
    citation_ids = table.citation_ids if table else []
    return OverviewSection(
        section_id="performance",
        title=f"Performance Overview: {response.asset.ticker}",
        section_type=OverviewSectionType.stable_facts,
        applies_to=[AssetType.etf],
        beginner_summary="Trailing and annual returns are shown only when provider-derived performance fields are available.",
        items=[],
        metrics=[],
        table=table,
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh if table else FreshnessState.unavailable,
        evidence_state=EvidenceState.partial if table else EvidenceState.unavailable,
        as_of_date=table.as_of_date if table else None,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=table.limitations if table else "Performance fields are unavailable in this lightweight response.",
    )


def _etf_performance_table(response: LightweightFetchResponse, provider_citation_ids: list[str]) -> OverviewTable | None:
    performance = _fact_value(response, "provider_fund_performance")
    if not isinstance(performance, dict):
        return None
    rows: list[OverviewTableRow] = []
    for item in performance.get("trailing_returns") or []:
        if isinstance(item, dict):
            rows.append(
                _performance_table_row(
                    response,
                    row_id=f"trailing_{len(rows) + 1}",
                    label=str(item.get("period") or "Trailing return"),
                    value=item.get("return"),
                    return_type="Trailing",
                    citation_ids=provider_citation_ids,
                )
            )
    for item in performance.get("annual_returns") or []:
        if isinstance(item, dict):
            rows.append(
                _performance_table_row(
                    response,
                    row_id=f"annual_{item.get('year') or len(rows) + 1}",
                    label=str(item.get("year") or "Annual return"),
                    value=item.get("return"),
                    return_type="Annual",
                    citation_ids=provider_citation_ids,
                )
            )
    if not rows:
        return None
    return OverviewTable(
        table_id="performance_returns",
        title=f"Performance Overview: {response.asset.ticker}",
        columns=[
            OverviewTableColumn(column_id="type", label="Type"),
            OverviewTableColumn(column_id="period", label="Period"),
            OverviewTableColumn(column_id="return", label=response.asset.ticker, value_type="percent", align="right"),
        ],
        rows=rows,
        citation_ids=provider_citation_ids,
        source_document_ids=_source_ids_for_citations(response, provider_citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.partial,
        as_of_date=str(performance.get("as_of_date") or _fact_as_of(response, "provider_fund_performance") or ""),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="Provider-derived return fields are historical context, not return forecasts.",
    )


def _price_chart_section(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
    *,
    applies_to: list[AssetType],
) -> OverviewSection:
    chart = _price_chart(response, provider_citation_ids)
    table = _quote_stats_table(response, stable_citation_ids, provider_citation_ids)
    citation_ids = _dedupe([*((chart.citation_ids if chart else [])), *((table.citation_ids if table else []))])
    source_document_ids = _dedupe(
        [*((chart.source_document_ids if chart else [])), *((table.source_document_ids if table else []))]
    )
    return OverviewSection(
        section_id="price_chart",
        title="Price Chart",
        section_type=OverviewSectionType.stable_facts,
        applies_to=applies_to,
        beginner_summary="A basic provider-derived price line and quote-stat grid are shown when normalized chart or market fields are available.",
        items=[],
        metrics=[],
        table=table,
        chart=chart,
        citation_ids=citation_ids,
        source_document_ids=source_document_ids,
        freshness_state=FreshnessState.fresh if chart or table else FreshnessState.unavailable,
        evidence_state=EvidenceState.mixed if chart and table else EvidenceState.partial if chart or table else EvidenceState.unavailable,
        as_of_date=(chart.as_of_date if chart else None) or (table.as_of_date if table else None),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=(
            "Provider-derived chart and quote stats are source-labeled reference data, not trading guidance."
            if chart or table
            else "Price chart points and quote stats are unavailable in this lightweight response."
        ),
    )


def _merged_quote_stat_rows(response: LightweightFetchResponse) -> list[dict[str, Any]]:
    rows_by_metric: dict[str, dict[str, Any]] = {}
    for fact in response.facts:
        if fact.field_name != "provider_quote_stats" or not isinstance(fact.value, dict):
            continue
        rows = fact.value.get("rows")
        if not isinstance(rows, list):
            continue
        for item in rows:
            if not isinstance(item, dict):
                continue
            metric_id = str(item.get("metric_id") or "").strip()
            if not metric_id or item.get("value") in (None, "") or metric_id in rows_by_metric:
                continue
            rows_by_metric[metric_id] = {
                **item,
                "citation_ids": list(fact.citation_ids),
                "source_document_ids": list(fact.source_document_ids),
                "as_of_date": fact.as_of_date,
            }
    contract = STOCK_QUOTE_STAT_ROW_ORDER if response.asset.asset_type is AssetType.stock else ETF_QUOTE_STAT_ROW_ORDER
    return [rows_by_metric[metric_id] for metric_id in contract if metric_id in rows_by_metric]


def _quote_stats_table(
    response: LightweightFetchResponse,
    stable_citation_ids: list[str],
    provider_citation_ids: list[str],
) -> OverviewTable | None:
    provider_rows = _merged_quote_stat_rows(response)
    rows_by_id: dict[str, OverviewTableRow] = {}
    row_order = list(STOCK_QUOTE_STAT_ROW_ORDER if response.asset.asset_type is AssetType.stock else ETF_QUOTE_STAT_ROW_ORDER)
    for item in provider_rows:
        metric_id = str(item.get("metric_id") or "").strip()
        value = item.get("value")
        if not metric_id or metric_id not in row_order or value in (None, ""):
            continue
        citation_ids = item.get("citation_ids") if isinstance(item.get("citation_ids"), list) else provider_citation_ids
        source_document_ids = item.get("source_document_ids") if isinstance(item.get("source_document_ids"), list) else []
        row = _simple_table_row(
            response,
            metric_id,
            str(item.get("label") or QUOTE_STAT_LABELS.get(metric_id) or metric_id.replace("_", " ").title()),
            value,
            [str(citation_id) for citation_id in citation_ids],
            as_of_date=str(item.get("as_of_date")) if item.get("as_of_date") else _fact_as_of(response, "provider_quote_stats"),
            evidence_state=EvidenceState.partial,
            limitations="Provider-derived quote-stat row.",
        )
        rows_by_id[metric_id] = row.model_copy(update={"source_document_ids": [str(source_id) for source_id in source_document_ids]})

    official_expense_ratio = _fact_value(response, "expense_ratio")
    if response.asset.asset_type is AssetType.etf and official_expense_ratio not in (None, ""):
        official_ids = _citation_ids_for_fact(response, "expense_ratio", stable_citation_ids)
        rows_by_id["expense_ratio"] = _simple_table_row(
            response,
            "expense_ratio",
            "Expense Ratio (net)",
            _percent_text(official_expense_ratio),
            official_ids,
            as_of_date=_fact_as_of(response, "expense_ratio"),
            evidence_state=EvidenceState.supported,
            limitations="Official issuer expense ratio overrides provider fallback for this dashboard stat.",
        )

    for metric_id in row_order:
        if metric_id in rows_by_id:
            continue
        rows_by_id[metric_id] = _simple_table_row(
            response,
            metric_id,
            QUOTE_STAT_LABELS.get(metric_id) or metric_id.replace("_", " ").title(),
            None,
            [],
            as_of_date=response.freshness.facts_as_of,
            evidence_state=EvidenceState.unavailable,
            limitations="Unavailable after official, configured provider API, and Yahoo/yfinance fallback attempts.",
        )

    ordered_rows = [rows_by_id[row_id] for row_id in row_order]
    citation_ids = _dedupe(citation_id for row in ordered_rows for citation_id in row.citation_ids)
    usable_rows = [row for row in ordered_rows if row.evidence_state is not EvidenceState.unavailable]
    all_official = bool(usable_rows) and all(row.evidence_state is EvidenceState.supported for row in usable_rows)
    return OverviewTable(
        table_id="quote_stats",
        title="Quote And Stock Stats" if response.asset.asset_type is AssetType.stock else "Quote And Fund Stats",
        columns=[
            OverviewTableColumn(column_id="label", label="Metric"),
            OverviewTableColumn(column_id="value", label="Value", align="right"),
        ],
        rows=ordered_rows,
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.supported if all_official else EvidenceState.mixed if usable_rows else EvidenceState.unavailable,
        as_of_date=_fact_as_of(response, "provider_quote_stats") or response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="Official facts override provider fallback where available; remaining rows are provider-derived normalized display fields.",
    )


def _price_chart(response: LightweightFetchResponse, provider_citation_ids: list[str]) -> OverviewChart | None:
    value = _fact_value(response, "provider_price_chart")
    if not isinstance(value, dict):
        return None
    points = [
        OverviewChartPoint(timestamp=str(point.get("timestamp")), close=float(point.get("close")), volume=point.get("volume"))
        for point in value.get("points") or []
        if isinstance(point, dict) and point.get("timestamp") and isinstance(point.get("close"), (int, float))
    ]
    if not points:
        return None
    return OverviewChart(
        chart_id="provider_price_chart",
        title=f"{response.asset.ticker} Price Chart",
        range=str(value.get("range") or "1mo"),
        interval=str(value.get("interval") or "1d"),
        points=points,
        currency=value.get("currency"),
        citation_ids=provider_citation_ids,
        source_document_ids=_source_ids_for_citations(response, provider_citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.partial,
        as_of_date=str(value.get("as_of_date") or _fact_as_of(response, "provider_price_chart") or ""),
        retrieved_at=response.freshness.page_last_updated_at,
        delayed_or_best_effort_label=str(value.get("delayed_or_best_effort_label") or "Provider-derived delayed or best-effort chart points"),
        limitations="Basic server-normalized chart; not an advanced trading chart and not trading guidance.",
    )


def _risk_section(
    response: LightweightFetchResponse,
    risks: list[RiskItem],
    *,
    applies_to: list[AssetType],
    section_id: str,
    title: str,
) -> OverviewSection:
    citation_ids = _dedupe(citation_id for risk in risks for citation_id in risk.citation_ids)
    return OverviewSection(
        section_id=section_id,
        title=title,
        section_type=OverviewSectionType.risk,
        applies_to=applies_to,
        beginner_summary="Exactly three top risks are shown first for beginner readability.",
        items=[
            _item(
                f"risk_{index}",
                risk.title,
                risk.plain_english_explanation,
                risk.citation_ids,
                response,
            )
            for index, risk in enumerate(risks, start=1)
        ],
        metrics=[],
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.supported,
        as_of_date=response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
    )


def _educational_suitability_section(
    response: LightweightFetchResponse,
    suitability: SuitabilitySummary,
    *,
    citation_ids: list[str],
    applies_to: list[AssetType],
) -> OverviewSection:
    return OverviewSection(
        section_id="educational_suitability",
        title="Educational Suitability",
        section_type=OverviewSectionType.educational_suitability,
        applies_to=applies_to,
        beginner_summary=suitability.may_fit,
        items=[
            _item("may_fit", "May fit as a learning topic", suitability.may_fit, citation_ids, response),
            _item("may_not_fit", "May not fit", suitability.may_not_fit, citation_ids, response),
            _item("learn_next", "Learn next", suitability.learn_next, citation_ids, response),
        ],
        metrics=[],
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.supported,
        as_of_date=response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
    )



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


def _overview_table(
    response: LightweightFetchResponse,
    *,
    table_id: str,
    title: str,
    rows: list[OverviewTableRow],
    citation_ids: list[str],
    evidence_state: EvidenceState,
    limitations: str,
) -> OverviewTable | None:
    if not rows:
        return None
    return OverviewTable(
        table_id=table_id,
        title=title,
        columns=[
            OverviewTableColumn(column_id="label", label="Metric"),
            OverviewTableColumn(column_id="value", label="Value", align="right"),
        ],
        rows=rows,
        citation_ids=_dedupe(citation_ids),
        source_document_ids=_source_ids_for_citations(response, _dedupe(citation_ids)),
        freshness_state=FreshnessState.fresh,
        evidence_state=evidence_state,
        as_of_date=response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=limitations,
    )


def _simple_table_row(
    response: LightweightFetchResponse,
    row_id: str,
    label: str,
    value: Any,
    citation_ids: list[str],
    *,
    as_of_date: str | None = None,
    evidence_state: EvidenceState = EvidenceState.partial,
    limitations: str | None = None,
) -> OverviewTableRow:
    return OverviewTableRow(
        row_id=row_id,
        label=label,
        values={"label": label, "value": _display_table_value(value)},
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh if value not in (None, "") else FreshnessState.unavailable,
        evidence_state=evidence_state if value not in (None, "") else EvidenceState.unavailable,
        as_of_date=as_of_date or response.freshness.facts_as_of,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=limitations,
    )


def _metric_rows_from_provider_group(
    response: LightweightFetchResponse,
    group_id: str,
    provider_citation_ids: list[str],
) -> list[OverviewTableRow]:
    group = next((item for item in _provider_metric_groups(response) if item.get("group_id") == group_id), None)
    if not group:
        return []
    rows: list[OverviewTableRow] = []
    for metric in group.get("metrics") or []:
        if not isinstance(metric, dict) or metric.get("value") in (None, ""):
            continue
        rows.append(
            _simple_table_row(
                response,
                str(metric.get("metric_id") or f"{group_id}_{len(rows) + 1}"),
                str(metric.get("label") or "Metric"),
                metric.get("value"),
                provider_citation_ids,
                as_of_date=_fact_as_of(response, "provider_stock_metric_groups"),
                evidence_state=EvidenceState.partial,
            )
        )
    return rows


def _provider_metric_groups(response: LightweightFetchResponse) -> list[dict[str, Any]]:
    value = _fact_value(response, "provider_stock_metric_groups")
    if not isinstance(value, dict):
        return []
    groups = value.get("groups")
    return [group for group in groups if isinstance(group, dict)] if isinstance(groups, list) else []


def _holding_table_row(
    response: LightweightFetchResponse,
    *,
    row_id: str,
    rank: int,
    symbol: str,
    name: str,
    weight: Any,
    citation_ids: list[str],
    as_of_date: str | None,
    evidence_state: EvidenceState,
    limitations: str | None = None,
) -> OverviewTableRow:
    return OverviewTableRow(
        row_id=row_id,
        label=name,
        values={"rank": rank, "symbol": symbol, "name": name, "weight": _number_or_text(weight)},
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=evidence_state,
        as_of_date=as_of_date,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=limitations,
    )


def _sector_table_row(
    response: LightweightFetchResponse,
    *,
    row_id: str,
    sector: str,
    weight: Any,
    citation_ids: list[str],
    as_of_date: str | None,
    evidence_state: EvidenceState,
    limitations: str | None = None,
) -> OverviewTableRow:
    return OverviewTableRow(
        row_id=row_id,
        label=sector,
        values={"sector": sector, "weight": _number_or_text(weight)},
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=evidence_state,
        as_of_date=as_of_date,
        retrieved_at=response.freshness.page_last_updated_at,
        limitations=limitations,
    )


def _performance_table_row(
    response: LightweightFetchResponse,
    *,
    row_id: str,
    label: str,
    value: Any,
    return_type: str,
    citation_ids: list[str],
) -> OverviewTableRow:
    return OverviewTableRow(
        row_id=row_id,
        label=label,
        values={"type": return_type, "period": label, "return": _number_or_text(value)},
        citation_ids=citation_ids,
        source_document_ids=_source_ids_for_citations(response, citation_ids),
        freshness_state=FreshnessState.fresh,
        evidence_state=EvidenceState.partial,
        as_of_date=_fact_as_of(response, "provider_fund_performance"),
        retrieved_at=response.freshness.page_last_updated_at,
        limitations="Provider-derived performance row.",
    )


def _metric_display(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("display") or value.get("value")
    return value


def _display_table_value(value: Any) -> str | float | int | None:
    if isinstance(value, dict):
        value = _metric_display(value)
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)) or value is None:
        return value
    return str(value)


def _number_or_text(value: Any) -> str | float | int | None:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)) or value is None:
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _percent_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return f"{value}%"
    return str(value)


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
        message="No source-governed Weekly News Focus items passed the local MVP evidence rules for this asset.",
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


def _stock_products_services_context(response: LightweightFetchResponse) -> str:
    if _provider_profile_context_summary(response):
        return (
            f"{response.asset.ticker}'s products-or-services discussion starts with SEC identity and filing-reference "
            "metadata, then adds provider-normalized profile context for sector, industry, leadership, scale, and "
            "business-description clues."
        )
    return (
        f"{response.asset.ticker}'s products-or-services discussion has SEC identity and filing-reference metadata, "
        "but lacks enough source-backed narrative detail for a product, segment, revenue-driver, geography, or competitor snapshot."
    )


def _stock_financial_quality_context(response: LightweightFetchResponse) -> str:
    available = [
        label
        for field_name, label in (
            ("latest_revenue_fact", "revenue"),
            ("latest_net_income_fact", "net income"),
            ("latest_assets_fact", "assets"),
        )
        if _fact(response, field_name) is not None
    ]
    if available:
        provider_titles = _provider_metric_group_titles(
            response,
            ("income_statement", "balance_sheet", "cash_flow", "margins_returns_ownership"),
        )
        provider_phrase = (
            " Provider-normalized " + _join_human(provider_titles) + " rows fill out the dashboard context."
            if provider_titles
            else ""
        )
        return (
            "SEC/XBRL supports latest "
            + ", ".join(available)
            + " facts in this lightweight page."
            + provider_phrase
        )
    return "SEC/XBRL financial-quality facts are unavailable in this lightweight response."


def _stock_valuation_context(response: LightweightFetchResponse) -> str:
    valuation_labels = _provider_metric_labels(response, "valuation_ratios", limit=4)
    if valuation_labels:
        return (
            "Provider-derived valuation rows such as "
            + _join_human(valuation_labels)
            + " are available as labeled fallback context. They explain valuation vocabulary but do not judge whether the stock is cheap or expensive."
        )
    price = _metric_from_market_price(response, _citation_ids_for_source_label(response, "provider_derived"))
    if price.value not in (None, "Unavailable"):
        return (
            f"Provider-derived local-test market reference is available at {price.value} {price.unit or ''}. "
            "The lightweight page does not calculate P/E, forward P/E, price/sales, price/free-cash-flow, peer context, or own-history context."
        )
    return "Valuation context is unavailable because the lightweight response has no supported valuation ratios or provider price reference."


def _stock_risk_context(response: LightweightFetchResponse) -> str:
    return (
        f"{response.asset.ticker} is a single-company stock, so risks are framed around company-specific exposure, "
        "point-in-time SEC facts, and provider fallback limits rather than trading signals."
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


def _etf_construction_context(response: LightweightFetchResponse) -> str:
    benchmark = _fact_value(response, "benchmark")
    prospectus = _fact_value(response, "prospectus_reference")
    if benchmark or prospectus:
        return (
            f"{response.asset.ticker} construction is explained from available benchmark and prospectus metadata, "
            "with the focus on what index the fund tracks and which issuer source can be checked next."
        )
    return "Construction and methodology evidence is unavailable until issuer benchmark or prospectus metadata is present."


def _etf_risk_context(response: LightweightFetchResponse) -> str:
    return (
        f"{response.asset.ticker} risks are framed around market exposure, point-in-time issuer evidence, and provider "
        "fallback limits; the page does not assign a personalized portfolio role."
    )


def _etf_comparison_overlap_context(response: LightweightFetchResponse) -> str:
    return (
        f"{response.asset.ticker} can only discuss similar ETFs or overlap when verified comparison-pack or holdings-overlap "
        "evidence is available, so this section avoids naming alternatives from memory."
    )


def _etf_holding_or_exposure_summary(value: Any) -> str:
    if isinstance(value, dict):
        name = value.get("name") or value.get("holding_ticker") or "Exposure"
        weight = value.get("weight")
        unit = value.get("unit") or "weight"
        category = value.get("exposure_category")
        if weight is not None:
            return f"{name} is listed as {weight} {unit}{f' in {category}' if category else ''}."
        return f"{name}{f' is listed as {category}' if category else ' is listed'}."
    return str(value)


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


def _latest_fact_as_of(response: LightweightFetchResponse, field_names: tuple[str, ...]) -> str | None:
    for field_name in field_names:
        as_of = _fact_as_of(response, field_name)
        if as_of:
            return as_of
    return response.freshness.facts_as_of


def _gap_message(response: LightweightFetchResponse, field_name: str) -> str | None:
    gap = next((item for item in response.gaps if item.field_name == field_name), None)
    if gap is None:
        return None
    return str(gap.value)


def _preferred_citation_ids(response: LightweightFetchResponse) -> list[str]:
    official_ids = _citation_ids_for_source_label(response, "official")
    partial_ids = _citation_ids_for_source_label(response, "partial")
    provider_ids = _citation_ids_for_source_label(response, "provider_derived")
    return official_ids or partial_ids or provider_ids or [citation.citation_id for citation in response.citations[:1]]


def _citation_ids_for_source_label(response: LightweightFetchResponse, label: str) -> list[str]:
    source_ids = {source.source_document_id for source in response.sources if source.source_label.value == label}
    return [citation.citation_id for citation in response.citations if citation.source_document_id in source_ids]


def _citation_ids_for_fact(
    response: LightweightFetchResponse,
    field_name: str,
    fallback_citation_ids: list[str],
) -> list[str]:
    fact = _fact(response, field_name)
    if fact is None:
        return fallback_citation_ids
    if fact.citation_ids:
        return fact.citation_ids
    source_ids = set(fact.source_document_ids)
    citation_ids = [
        citation.citation_id
        for citation in response.citations
        if citation.source_document_id in source_ids
    ]
    return citation_ids or fallback_citation_ids


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


def _format_fact_number(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
