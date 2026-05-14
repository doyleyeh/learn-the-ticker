from __future__ import annotations

from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from backend.models import (
    AIComprehensiveAnalysisResponse,
    AssetIdentity,
    Citation,
    EconomicIndicatorsPackResponse,
    EvidenceState,
    FreshnessState,
    SourceAllowlistStatus,
    SourceDocument,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsDeduplicationMetadata,
    WeeklyNewsEvidenceLimitedState,
    WeeklyNewsEmptyState,
    WeeklyNewsEventType,
    WeeklyNewsFocusResponse,
    WeeklyNewsItem,
    WeeklyNewsPeriodBucket,
    WeeklyNewsSelectionRationale,
    WeeklyNewsSourceMetadata,
    WeeklyNewsWindow,
    MarketNewsFocusResponse,
    MarketWeekPeriod,
)
from backend.generation_evidence import evidence_pack_from_weekly_news
from backend.news_quality import publisher_tier, score_ticker_weekly_news
from backend.retrieval import AssetKnowledgePack, RetrievedRecentDevelopment
from backend.safety import find_forbidden_output_phrases
from backend.source_policy import resolve_source_policy, source_handoff_fields_from_policy
from backend.summary_generation import (
    HybridSummaryGenerationService,
    SummaryGenerationContractError,
    SummaryGenerationService,
    build_default_summary_generation_service,
    summary_generation_diagnostics,
)


DEFAULT_WEEKLY_NEWS_AS_OF = "2026-04-23"
MINIMUM_DISPLAY_SCORE = 7
MINIMUM_AI_ANALYSIS_ITEMS = 2
MAX_WEEKLY_ITEMS = 8
WEEKLY_NEWS_PERSISTED_READ_BOUNDARY = "weekly-news-persisted-read-boundary-v1"

_EASTERN = ZoneInfo("America/New_York")


class WeeklyNewsContractError(ValueError):
    """Raised when deterministic Weekly News Focus contracts are violated."""


class WeeklyNewsEventEvidenceRecordReader(Protocol):
    def read_weekly_news_event_evidence_records(self, ticker: str) -> Any | None:
        ...


@dataclass(frozen=True)
class PersistedWeeklyNewsReadResult:
    status: str
    ticker: str
    weekly_news_focus: WeeklyNewsFocusResponse | None = None
    minimum_ai_analysis_item_count: int = MINIMUM_AI_ANALYSIS_ITEMS
    high_signal_selected_item_count: int = 0
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found(self) -> bool:
        return self.status == "found" and self.weekly_news_focus is not None


class WeeklyNewsCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    asset_ticker: str
    event_type: WeeklyNewsEventType
    title: str
    summary: str
    event_date: str
    published_at: str | None = None
    retrieved_at: str
    source_document_id: str
    source_chunk_id: str | None = None
    source_type: str
    source_rank: int = 999
    source_title: str
    publisher: str
    url: str
    source_quality: SourceQuality
    allowlist_status: SourceAllowlistStatus
    source_use_policy: SourceUsePolicy
    freshness_state: FreshnessState = FreshnessState.fresh
    is_official: bool = False
    supporting_text: str
    asset_relevance: str = "exact"
    duplicate_group_id: str | None = None
    duplicate_of_event_id: str | None = None
    is_duplicate: bool = False
    promotional: bool = False
    irrelevant: bool = False
    license_allowed: bool = True


def compute_weekly_news_window(as_of: str | date | datetime, *, include_current_day: bool = False) -> WeeklyNewsWindow:
    """Return the deterministic Eastern market-week window for an explicit as-of date."""

    as_of_date = _eastern_date(as_of)
    current_monday = as_of_date - timedelta(days=as_of_date.weekday())
    previous_monday = current_monday - timedelta(days=7)
    previous_sunday = current_monday - timedelta(days=1)
    yesterday = as_of_date - timedelta(days=1)

    current_window_end = as_of_date if include_current_day else yesterday

    if current_window_end >= current_monday:
        current_period = MarketWeekPeriod(start=current_monday.isoformat(), end=current_window_end.isoformat())
        news_window_end = current_window_end
        includes_current = True
    else:
        current_period = MarketWeekPeriod(start=None, end=None)
        news_window_end = previous_sunday
        includes_current = False

    return WeeklyNewsWindow(
        as_of_date=as_of_date.isoformat(),
        previous_market_week=MarketWeekPeriod(start=previous_monday.isoformat(), end=previous_sunday.isoformat()),
        current_week_to_date=current_period,
        news_window_start=previous_monday.isoformat(),
        news_window_end=news_window_end.isoformat(),
        includes_current_week_to_date=includes_current,
        includes_current_day=include_current_day,
        window_policy="local_live_current_day" if include_current_day else "strict_completed_day",
    )


def build_weekly_news_focus_from_pack(
    pack: AssetKnowledgePack,
    *,
    as_of: str | date | datetime,
    persisted_event_reader: WeeklyNewsEventEvidenceRecordReader | Any | None = None,
) -> WeeklyNewsFocusResponse:
    persisted = read_persisted_weekly_news_focus(
        pack.asset,
        as_of=as_of,
        persisted_event_reader=persisted_event_reader,
    )
    if persisted.found and persisted.weekly_news_focus is not None:
        return persisted.weekly_news_focus

    candidates = [_candidate_from_recent_development(item) for item in pack.recent_developments]
    return select_weekly_news_focus(pack.asset, candidates, as_of=as_of)


def read_persisted_weekly_news_focus(
    asset: AssetIdentity,
    *,
    as_of: str | date | datetime,
    persisted_event_reader: WeeklyNewsEventEvidenceRecordReader | Any | None = None,
) -> PersistedWeeklyNewsReadResult:
    normalized_ticker = _normalize_ticker(asset.ticker)
    if persisted_event_reader is None:
        return PersistedWeeklyNewsReadResult(
            status="not_configured",
            ticker=normalized_ticker,
            diagnostics=("weekly_news_reader:not_configured",),
        )

    try:
        from backend.weekly_news_repository import (
            WeeklyNewsEventEvidenceContractError,
            WeeklyNewsEventEvidenceRepositoryRecords,
            validate_weekly_news_event_evidence_records,
        )

        raw_records = persisted_event_reader.read_weekly_news_event_evidence_records(normalized_ticker)
        if raw_records is None:
            return PersistedWeeklyNewsReadResult(
                status="miss",
                ticker=normalized_ticker,
                diagnostics=("weekly_news_reader:miss",),
            )
        records = (
            raw_records
            if isinstance(raw_records, WeeklyNewsEventEvidenceRepositoryRecords)
            else WeeklyNewsEventEvidenceRepositoryRecords.model_validate(raw_records)
        )
        validated = validate_weekly_news_event_evidence_records(records)
        return _weekly_news_focus_from_persisted_records(asset, validated, as_of=as_of)
    except (WeeklyNewsEventEvidenceContractError, WeeklyNewsContractError) as exc:
        return PersistedWeeklyNewsReadResult(
            status="contract_error",
            ticker=normalized_ticker,
            diagnostics=(f"weekly_news:{exc.__class__.__name__}",),
        )
    except Exception as exc:
        return PersistedWeeklyNewsReadResult(
            status="reader_error",
            ticker=normalized_ticker,
            diagnostics=(f"weekly_news:{exc.__class__.__name__}",),
        )


def select_weekly_news_focus(
    asset: AssetIdentity,
    candidates: list[WeeklyNewsCandidate],
    *,
    as_of: str | date | datetime,
    minimum_display_score: int = MINIMUM_DISPLAY_SCORE,
) -> WeeklyNewsFocusResponse:
    window = compute_weekly_news_window(as_of)
    selected_candidates: list[WeeklyNewsItem] = []
    rejected_candidate_count = 0

    for candidate in candidates:
        rationale = _selection_rationale(asset, candidate, window, minimum_display_score)
        if not rationale.selected:
            rejected_candidate_count += 1
            continue
        selected_candidates.append(_item_from_candidate(candidate, window, rationale))

    if selected_candidates and not any(publisher_tier(item.source.publisher) != "demoted" for item in selected_candidates):
        rejected_candidate_count += len(selected_candidates)
        selected_candidates = []

    ranked_selected_candidates = sorted(
        selected_candidates,
        key=lambda item: (
            -item.importance_score,
            item.selection_rationale.source_priority,
            item.event_date or "",
            item.event_id,
        ),
    )
    selected = ranked_selected_candidates[:MAX_WEEKLY_ITEMS]
    suppressed_count = rejected_candidate_count + max(0, len(ranked_selected_candidates) - len(selected))
    selected_count = len(selected)

    if selected_count == 0:
        evidence_state = EvidenceState.no_high_signal
        evidence_limited_state = WeeklyNewsEvidenceLimitedState.empty
    elif selected_count < MAX_WEEKLY_ITEMS:
        evidence_state = EvidenceState.partial
        evidence_limited_state = WeeklyNewsEvidenceLimitedState.limited_verified_set
    else:
        evidence_state = EvidenceState.supported
        evidence_limited_state = WeeklyNewsEvidenceLimitedState.full

    citations = [
        Citation(
            citation_id=_weekly_citation_id(item.event_id),
            source_document_id=item.source.source_document_id,
            title=item.source.title,
            publisher=item.source.publisher,
            freshness_state=item.freshness_state,
        )
        for item in selected
    ]
    source_documents = [_source_document_from_item(item) for item in selected]

    if selected:
        state = WeeklyNewsContractState.available
        empty_state = None
    else:
        state = WeeklyNewsContractState.no_high_signal
        empty_state = WeeklyNewsEmptyState(
            state=state,
            message="No major Weekly News Focus items found in the deterministic local fixture window.",
            evidence_state=evidence_state,
            selected_item_count=0,
            suppressed_candidate_count=suppressed_count,
        )

    return WeeklyNewsFocusResponse(
        asset=asset,
        state=state,
        window=window,
        configured_max_item_count=MAX_WEEKLY_ITEMS,
        selected_item_count=selected_count,
        suppressed_candidate_count=suppressed_count,
        evidence_state=evidence_state,
        evidence_limited_state=evidence_limited_state,
        items=selected,
        empty_state=empty_state,
        citations=citations,
        source_documents=source_documents,
    )


def _weekly_news_focus_from_persisted_records(
    asset: AssetIdentity,
    records: Any,
    *,
    as_of: str | date | datetime,
) -> PersistedWeeklyNewsReadResult:
    normalized_ticker = _normalize_ticker(asset.ticker)
    as_of_date = _eastern_date(as_of).isoformat()
    window = next(
        (
            row
            for row in records.windows
            if _normalize_ticker(row.asset_ticker) == normalized_ticker and row.as_of_date == as_of_date
        ),
        None,
    )
    if window is None:
        return PersistedWeeklyNewsReadResult(
            status="miss",
            ticker=normalized_ticker,
            diagnostics=("weekly_news_records:matching_window_miss",),
        )

    selected_rows = sorted(
        [row for row in records.selected_events if row.window_id == window.window_id],
        key=lambda row: (row.rank_position, row.selected_event_id),
    )
    evidence_state = next((row for row in records.evidence_states if row.window_id == window.window_id), None)
    threshold = next((row for row in records.ai_thresholds if row.window_id == window.window_id), None)
    if evidence_state is None or threshold is None:
        raise WeeklyNewsContractError("Persisted Weekly News Focus records require evidence state and AI threshold metadata.")
    if set(threshold.selected_event_ids) != {row.selected_event_id for row in selected_rows}:
        raise WeeklyNewsContractError("Persisted AI threshold metadata must stay connected to selected events.")

    candidates_by_id = {row.candidate_event_id: row for row in records.candidates}
    rank_inputs_by_id = {row.candidate_event_id: row for row in records.source_rank_inputs}
    items = [
        _item_from_persisted_selected_event(
            selected,
            candidate=candidates_by_id[selected.candidate_event_id],
            rank_input=rank_inputs_by_id.get(selected.candidate_event_id),
        )
        for selected in selected_rows
    ]

    citations = [
        Citation(
            citation_id=citation_id,
            source_document_id=item.source.source_document_id,
            title=item.source.title,
            publisher=item.source.publisher,
            freshness_state=item.freshness_state,
        )
        for item in items
        for citation_id in item.citation_ids
    ]
    source_documents = _dedupe_weekly_source_documents([_source_document_from_item(item) for item in items])

    state = WeeklyNewsContractState(evidence_state.state)
    evidence_label = EvidenceState(evidence_state.evidence_state)
    empty_state = None
    if not items:
        empty_state = WeeklyNewsEmptyState(
            state=state,
            message=f"No major Weekly News Focus items found in validated persisted evidence for {normalized_ticker}.",
            evidence_state=evidence_label,
            selected_item_count=evidence_state.selected_item_count,
            suppressed_candidate_count=evidence_state.suppressed_candidate_count,
        )

    focus = WeeklyNewsFocusResponse(
        asset=asset,
        state=state,
        window=WeeklyNewsWindow(
            as_of_date=window.as_of_date,
            previous_market_week=MarketWeekPeriod(
                start=window.previous_market_week_start,
                end=window.previous_market_week_end,
            ),
            current_week_to_date=MarketWeekPeriod(
                start=window.current_week_to_date_start,
                end=window.current_week_to_date_end,
            ),
            news_window_start=window.news_window_start,
            news_window_end=window.news_window_end,
            includes_current_week_to_date=window.includes_current_week_to_date,
            includes_current_day=getattr(window, "includes_current_day", False),
            window_policy=getattr(window, "window_policy", "strict_completed_day"),
        ),
        configured_max_item_count=window.configured_max_item_count,
        selected_item_count=evidence_state.selected_item_count,
        suppressed_candidate_count=evidence_state.suppressed_candidate_count,
        evidence_state=evidence_label,
        evidence_limited_state=WeeklyNewsEvidenceLimitedState(evidence_state.evidence_limited_state),
        items=items,
        empty_state=empty_state,
        citations=citations,
        source_documents=source_documents,
        selection_diagnostics=_selection_diagnostics_from_records(records, window.window_id),
    )
    return PersistedWeeklyNewsReadResult(
        status="found",
        ticker=normalized_ticker,
        weekly_news_focus=focus,
        minimum_ai_analysis_item_count=threshold.minimum_weekly_news_item_count,
        high_signal_selected_item_count=threshold.high_signal_selected_item_count,
        diagnostics=("weekly_news:persisted_hit",),
    )


def _item_from_persisted_selected_event(
    selected: Any,
    *,
    candidate: Any,
    rank_input: Any | None,
) -> WeeklyNewsItem:
    event_type = WeeklyNewsEventType(selected.event_type)
    source_quality = SourceQuality(selected.source_quality)
    allowlist_status = SourceAllowlistStatus(selected.allowlist_status)
    source_use_policy = SourceUsePolicy(selected.source_use_policy)
    freshness_state = FreshnessState(selected.freshness_state)
    source_priority = getattr(candidate, "source_rank", selected.rank_position)
    total_score = getattr(rank_input, "total_score", selected.importance_score)
    title = _persisted_event_title(event_type, selected)
    summary = _persisted_event_summary(event_type, selected)

    return WeeklyNewsItem(
        event_id=selected.candidate_event_id,
        asset_ticker=_normalize_ticker(selected.asset_ticker),
        event_type=event_type,
        title=title,
        summary=summary,
        event_date=selected.event_date,
        published_at=selected.published_at,
        period_bucket=WeeklyNewsPeriodBucket(selected.period_bucket),
        citation_ids=list(selected.citation_ids),
        source=WeeklyNewsSourceMetadata(
            source_document_id=selected.source_document_id,
            source_type=getattr(candidate, "source_type", "persisted_weekly_news_evidence"),
            title=_persisted_source_title(selected),
            publisher=_persisted_source_publisher(source_quality, selected),
            url=(
                str(selected.source_url)
                if getattr(selected, "source_url", None)
                else f"local://weekly-news-evidence/{_normalize_ticker(selected.asset_ticker)}/{selected.source_document_id}"
            ),
            published_at=selected.published_at,
            as_of_date=selected.event_date or (selected.published_at[:10] if selected.published_at else None),
            retrieved_at=selected.retrieved_at,
            freshness_state=freshness_state,
            is_official=source_quality in {SourceQuality.official, SourceQuality.issuer},
            source_quality=source_quality,
            allowlist_status=allowlist_status,
            source_use_policy=source_use_policy,
        ),
        freshness_state=freshness_state,
        importance_score=selected.importance_score,
        deduplication=WeeklyNewsDeduplicationMetadata(
            canonical_event_key=selected.canonical_event_key,
            duplicate_group_id=selected.dedupe_group_id,
            duplicate_of_event_id=None,
            is_duplicate=False,
        ),
        selection_rationale=WeeklyNewsSelectionRationale(
            source_priority=source_priority,
            source_quality_weight=getattr(rank_input, "source_quality_weight", 0),
            event_type_weight=getattr(rank_input, "event_type_weight", 0),
            recency_weight=getattr(rank_input, "recency_weight", 0),
            asset_relevance_weight=getattr(rank_input, "asset_relevance_weight", 0),
            duplicate_penalty=getattr(rank_input, "duplicate_penalty", 0),
            total_score=total_score,
            minimum_display_score=getattr(rank_input, "minimum_display_score", MINIMUM_DISPLAY_SCORE),
            selected=True,
            exclusion_reasons=[],
        ),
    )


def _persisted_event_title(event_type: WeeklyNewsEventType, selected: Any) -> str:
    if getattr(selected, "event_title", None):
        return str(selected.event_title)
    label = event_type.value.replace("_", " ").title()
    period = WeeklyNewsPeriodBucket(selected.period_bucket).value.replace("_", " ")
    return f"{label} evidence in {period}"


def _persisted_event_summary(event_type: WeeklyNewsEventType, selected: Any) -> str:
    if getattr(selected, "event_summary", None):
        return str(selected.event_summary)
    label = event_type.value.replace("_", " ")
    period = WeeklyNewsPeriodBucket(selected.period_bucket).value.replace("_", " ")
    return (
        f"Validated persisted Weekly News Focus metadata for {_normalize_ticker(selected.asset_ticker)} "
        f"selected a {label} item in the {period} window."
    )


def _persisted_source_title(selected: Any) -> str:
    if getattr(selected, "source_title", None):
        return str(selected.source_title)
    source_type = str(getattr(selected, "source_type", "weekly_news_evidence")).replace("_", " ")
    return f"Persisted {source_type} source {selected.source_document_id}"


def _persisted_source_publisher(source_quality: SourceQuality, selected: Any | None = None) -> str:
    if selected is not None and getattr(selected, "source_publisher", None):
        return str(selected.source_publisher)
    return f"{source_quality.value.replace('_', ' ').title()} source"


def _dedupe_weekly_source_documents(source_documents: list[SourceDocument]) -> list[SourceDocument]:
    by_id: dict[str, SourceDocument] = {}
    for source in source_documents:
        by_id.setdefault(source.source_document_id, source)
    return [by_id[source_id] for source_id in sorted(by_id)]


def _selection_diagnostics_from_records(records: Any, window_id: str) -> dict[str, Any]:
    candidates = [row for row in records.candidates if row.window_id == window_id]
    selected = [row for row in records.selected_events if row.window_id == window_id]
    candidates_by_id = {row.candidate_event_id: row for row in candidates}
    candidate_tier_counts: dict[str, int] = {}
    selected_tier_counts: dict[str, int] = {}
    candidate_publisher_tier_counts: dict[str, int] = {}
    selected_publisher_tier_counts: dict[str, int] = {}
    candidate_acquisition_counts: dict[str, int] = {}
    selected_acquisition_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}

    for candidate in candidates:
        candidate_tier_counts[candidate.source_rank_tier] = candidate_tier_counts.get(candidate.source_rank_tier, 0) + 1
        publisher_label = publisher_tier(getattr(candidate, "source_publisher", None))
        candidate_publisher_tier_counts[publisher_label] = candidate_publisher_tier_counts.get(publisher_label, 0) + 1
        acquisition_label = _weekly_news_acquisition_source(candidate.source_rank_tier, getattr(candidate, "source_type", ""))
        candidate_acquisition_counts[acquisition_label] = candidate_acquisition_counts.get(acquisition_label, 0) + 1
        for reason in candidate.suppression_reason_codes:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    for selected_event in selected:
        candidate = candidates_by_id.get(selected_event.candidate_event_id)
        tier = candidate.source_rank_tier if candidate is not None else selected_event.source_type
        selected_tier_counts[tier] = selected_tier_counts.get(tier, 0) + 1
        publisher_label = publisher_tier(
            getattr(candidate, "source_publisher", None) if candidate is not None else selected_event.source_publisher
        )
        selected_publisher_tier_counts[publisher_label] = selected_publisher_tier_counts.get(publisher_label, 0) + 1
        acquisition_label = _weekly_news_acquisition_source(
            tier,
            getattr(candidate, "source_type", selected_event.source_type) if candidate is not None else selected_event.source_type,
        )
        selected_acquisition_counts[acquisition_label] = selected_acquisition_counts.get(acquisition_label, 0) + 1

    return {
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "candidate_counts_by_source_tier": candidate_tier_counts,
        "selected_counts_by_source_tier": selected_tier_counts,
        "candidate_counts_by_acquisition_source": candidate_acquisition_counts,
        "selected_counts_by_acquisition_source": selected_acquisition_counts,
        "candidate_counts_by_publisher_tier": candidate_publisher_tier_counts,
        "selected_counts_by_publisher_tier": selected_publisher_tier_counts,
        "suppression_reason_counts": reason_counts,
        "raw_article_text_collected": False,
        "raw_provider_payload_exposed": False,
        "secrets_exposed": False,
    }


def _weekly_news_acquisition_source(source_rank_tier: str, source_type: str) -> str:
    if source_rank_tier in {
        "official_filing",
        "investor_relations_release",
        "etf_issuer_announcement",
        "prospectus_update",
        "fact_sheet_change",
    }:
        return "official"
    if "yahoo" in source_type.lower():
        return "yahoo"
    if source_rank_tier == "allowlisted_news":
        return "provider_api"
    if source_rank_tier == "provider_context":
        return "provider_context"
    return "unknown"


def build_ai_comprehensive_analysis(
    asset: AssetIdentity,
    weekly_news_focus: WeeklyNewsFocusResponse,
    *,
    canonical_fact_citation_ids: list[str] | None = None,
    canonical_source_document_ids: list[str] | None = None,
    minimum_weekly_news_item_count: int = MINIMUM_AI_ANALYSIS_ITEMS,
    approved_weekly_news_item_count: int | None = None,
    high_signal_weekly_news_item_count: int | None = None,
    summary_generation_service: SummaryGenerationService | None = None,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    market_news_focus: MarketNewsFocusResponse | None = None,
    technical_context: dict[str, Any] | None = None,
    generation_evidence_pack: dict[str, Any] | None = None,
) -> AIComprehensiveAnalysisResponse:
    canonical_fact_citation_ids = sorted(set(canonical_fact_citation_ids or []))
    canonical_source_document_ids = sorted(set(canonical_source_document_ids or []))

    if approved_weekly_news_item_count is not None:
        approved_item_count = approved_weekly_news_item_count
    elif high_signal_weekly_news_item_count is not None:
        approved_item_count = high_signal_weekly_news_item_count
    else:
        approved_item_count = len(weekly_news_focus.items)

    if approved_item_count < minimum_weekly_news_item_count:
        return AIComprehensiveAnalysisResponse(
            asset=asset,
            state=WeeklyNewsContractState.suppressed,
            analysis_available=False,
            minimum_weekly_news_item_count=minimum_weekly_news_item_count,
            weekly_news_selected_item_count=weekly_news_focus.selected_item_count,
            suppression_reason="AI Comprehensive Analysis is suppressed because fewer than two approved Weekly News Focus items are available.",
            canonical_fact_citation_ids=canonical_fact_citation_ids,
        )

    weekly_citations = sorted({citation_id for item in weekly_news_focus.items for citation_id in item.citation_ids})
    all_citations = sorted(set([*weekly_citations, *canonical_fact_citation_ids]))
    source_ids = sorted(
        {
            *{source.source_document_id for source in weekly_news_focus.source_documents},
            *canonical_source_document_ids,
        }
    )
    event_ids = [item.event_id for item in weekly_news_focus.items]
    evidence_pack = generation_evidence_pack or evidence_pack_from_weekly_news(
        asset,
        weekly_news_focus,
        canonical_fact_citation_ids=canonical_fact_citation_ids,
        canonical_source_document_ids=canonical_source_document_ids,
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        technical_context=technical_context,
    )
    service = summary_generation_service or build_default_summary_generation_service()
    try:
        response = service.generate_ticker_ai_comprehensive_analysis(
            asset=asset,
            weekly_news_focus=weekly_news_focus,
            canonical_fact_citation_ids=canonical_fact_citation_ids,
            canonical_source_document_ids=canonical_source_document_ids,
            minimum_weekly_news_item_count=minimum_weekly_news_item_count,
            weekly_news_selected_item_count=weekly_news_focus.selected_item_count,
            generation_evidence_pack=evidence_pack,
        )
        validate_ai_comprehensive_analysis(response, weekly_news_focus)
        return response
    except (SummaryGenerationContractError, WeeklyNewsContractError) as exc:
        reason_codes = _ai_validation_reason_codes(exc)
        if "safety_validation_failed" not in reason_codes and "prediction_language" not in reason_codes:
            try:
                repaired = HybridSummaryGenerationService().generate_ticker_ai_comprehensive_analysis(
                    asset=asset,
                    weekly_news_focus=weekly_news_focus,
                    canonical_fact_citation_ids=canonical_fact_citation_ids,
                    canonical_source_document_ids=canonical_source_document_ids,
                    minimum_weekly_news_item_count=minimum_weekly_news_item_count,
                    weekly_news_selected_item_count=weekly_news_focus.selected_item_count,
                    generation_evidence_pack=evidence_pack,
                )
                validate_ai_comprehensive_analysis(repaired, weekly_news_focus)
                return repaired.model_copy(
                    update={
                        "validation_reason_codes": [
                            "live_generation_repaired_with_deterministic_fallback",
                            *reason_codes,
                        ],
                        "generation_diagnostics": summary_generation_diagnostics(
                            service,
                            task_name="ticker_ai_comprehensive_analysis",
                            used_fallback=True,
                            fallback_reason_codes=[
                                "live_generation_repaired_with_deterministic_fallback",
                                *reason_codes,
                            ],
                        ),
                        "no_live_external_calls": True,
                    }
                )
            except (SummaryGenerationContractError, WeeklyNewsContractError) as fallback_exc:
                reason_codes = [*reason_codes, *_ai_validation_reason_codes(fallback_exc), "deterministic_fallback_failed"]
        return AIComprehensiveAnalysisResponse(
            asset=asset,
            state=WeeklyNewsContractState.suppressed,
            analysis_available=False,
            minimum_weekly_news_item_count=minimum_weekly_news_item_count,
            weekly_news_selected_item_count=weekly_news_focus.selected_item_count,
            suppression_reason=(
                "AI Comprehensive Analysis is suppressed because generated analysis failed schema, citation, "
                "freshness, or safety validation."
            ),
            validation_reason_codes=sorted(set(reason_codes)),
            citation_ids=all_citations,
            source_document_ids=source_ids,
            weekly_news_event_ids=event_ids,
            canonical_fact_citation_ids=canonical_fact_citation_ids,
            generation_diagnostics=summary_generation_diagnostics(
                service,
                task_name="ticker_ai_comprehensive_analysis",
                used_fallback=True,
                fallback_reason_codes=sorted(set(reason_codes)),
            ),
        )


def validate_ai_comprehensive_analysis(
    analysis: AIComprehensiveAnalysisResponse,
    weekly_news_focus: WeeklyNewsFocusResponse,
) -> AIComprehensiveAnalysisResponse:
    if not analysis.analysis_available:
        if analysis.sections:
            raise WeeklyNewsContractError("Suppressed AI Comprehensive Analysis must not include generated sections.")
        return analysis

    expected_order = [
        "what_changed_this_week",
        "market_context",
        "business_or_fund_context",
        "risk_context",
    ]
    actual_order = [section.section_id for section in analysis.sections]
    if actual_order != expected_order:
        raise WeeklyNewsContractError("AI Comprehensive Analysis sections are not in the required order.")

    weekly_citations = {citation_id for item in weekly_news_focus.items for citation_id in item.citation_ids}
    allowed_citations = weekly_citations | set(analysis.canonical_fact_citation_ids)
    if not weekly_citations:
        raise WeeklyNewsContractError("AI Comprehensive Analysis requires Weekly News Focus citations.")
    if analysis.citation_ids and not set(analysis.citation_ids) <= allowed_citations:
        raise WeeklyNewsContractError("AI Comprehensive Analysis cites evidence outside the weekly/canonical packs.")
    weekly_event_ids = {item.event_id for item in weekly_news_focus.items}
    if analysis.weekly_news_event_ids and not set(analysis.weekly_news_event_ids) <= weekly_event_ids:
        raise WeeklyNewsContractError("AI Comprehensive Analysis references events outside the Weekly News Focus pack.")

    for section in analysis.sections:
        if not section.citation_ids:
            raise WeeklyNewsContractError(f"AI analysis section {section.section_id} is missing citations.")
        if not set(section.citation_ids) <= allowed_citations:
            raise WeeklyNewsContractError(f"AI analysis section {section.section_id} cites evidence outside the weekly/canonical packs.")

    combined_text = " ".join(
        [section.analysis for section in analysis.sections]
        + [bullet for section in analysis.sections for bullet in section.bullets]
    )
    forbidden = find_forbidden_output_phrases(combined_text)
    if forbidden:
        raise WeeklyNewsContractError(f"AI Comprehensive Analysis includes forbidden advice-like language: {forbidden}")
    for phrase in ["price target", "guaranteed", "will outperform", "will rise", "will fall", "forecast"]:
        if phrase in combined_text.lower():
            raise WeeklyNewsContractError(f"AI Comprehensive Analysis includes prediction or recommendation language: {phrase}")

    return analysis


def _ai_validation_reason_codes(exc: Exception) -> list[str]:
    text = str(exc).lower()
    codes: list[str] = []
    if "citation" in text or "outside the weekly/canonical packs" in text:
        codes.append("citation_validation_failed")
    if "section" in text or "schema" in text or "object" in text or "json" in text:
        codes.append("schema_validation_failed")
    if "freshness" in text:
        codes.append("freshness_validation_failed")
    if "forbidden" in text or "advice" in text or "generated prose failed validation" in text or "invalid_safety" in text:
        codes.append("safety_validation_failed")
    if "prediction" in text or "price target" in text or "guaranteed" in text or "forecast" in text:
        codes.append("prediction_language")
    if "headline" in text or "repeats" in text:
        codes.append("headline_repetition")
    if not codes:
        codes.append("analysis_contract_validation_failed")
    return sorted(set(codes))


def _selection_rationale(
    asset: AssetIdentity,
    candidate: WeeklyNewsCandidate,
    window: WeeklyNewsWindow,
    minimum_display_score: int,
) -> WeeklyNewsSelectionRationale:
    exclusion_reasons: list[str] = []
    quality = score_ticker_weekly_news(
        ticker=asset.ticker,
        asset_type=asset.asset_type.value,
        asset_name=asset.name,
        title=candidate.title,
        summary=candidate.summary,
        publisher=candidate.publisher,
        source_rank_tier=_source_rank_tier_for_candidate(candidate),
        source_type=candidate.source_type,
        event_type=candidate.event_type.value,
        is_official=candidate.is_official,
    )
    quality_reasons = set(quality.suppression_reasons)
    if candidate.asset_relevance == "exact":
        quality_reasons.discard("weak_ticker_relevance")
    if candidate.asset_relevance == "exact" and candidate.source_quality in {SourceQuality.allowlisted, SourceQuality.fixture}:
        quality_reasons.discard("low_source_quality")

    source_quality_weight = _source_quality_weight(candidate) + quality.publisher_score + quality.acquisition_score
    event_type_weight = _event_type_weight(candidate.event_type) + quality.beginner_utility_score
    recency_weight = _recency_weight(candidate, window)
    asset_relevance_weight = max(_asset_relevance_weight(asset, candidate), quality.ticker_relevance_score)
    duplicate_penalty = 5 if candidate.is_duplicate or candidate.duplicate_of_event_id else 0
    total_score = source_quality_weight + event_type_weight + recency_weight + asset_relevance_weight - duplicate_penalty
    exclusion_reasons.extend(sorted(quality_reasons))

    if _normalize_ticker(candidate.asset_ticker) != _normalize_ticker(asset.ticker):
        exclusion_reasons.append("wrong_asset")
    if candidate.event_type is WeeklyNewsEventType.no_major_recent_development:
        exclusion_reasons.append("no_major_recent_development_marker")
    if not _date_in_window(candidate.event_date, window):
        exclusion_reasons.append("outside_market_week_window")
        if not window.includes_current_day:
            exclusion_reasons.append("outside_strict_window")
    if candidate.allowlist_status is not SourceAllowlistStatus.allowed:
        exclusion_reasons.append("non_allowlisted_source")
    if candidate.source_use_policy in {SourceUsePolicy.metadata_only, SourceUsePolicy.link_only, SourceUsePolicy.rejected}:
        exclusion_reasons.append("license_disallowed_source_policy")
    if not candidate.license_allowed:
        exclusion_reasons.append("license_disallowed")
    if candidate.source_quality is SourceQuality.rejected:
        exclusion_reasons.append("rejected_source")
    if candidate.promotional:
        exclusion_reasons.append("promotional")
    if candidate.irrelevant:
        exclusion_reasons.append("irrelevant")
    if candidate.is_duplicate or candidate.duplicate_of_event_id:
        exclusion_reasons.append("duplicate")
    if total_score < minimum_display_score:
        exclusion_reasons.append("below_minimum_display_score")

    return WeeklyNewsSelectionRationale(
        source_priority=candidate.source_rank,
        source_quality_weight=source_quality_weight,
        event_type_weight=event_type_weight,
        recency_weight=recency_weight,
        asset_relevance_weight=asset_relevance_weight,
        duplicate_penalty=duplicate_penalty,
        total_score=total_score,
        minimum_display_score=minimum_display_score,
        selected=not exclusion_reasons,
        exclusion_reasons=exclusion_reasons,
    )


def _item_from_candidate(
    candidate: WeeklyNewsCandidate,
    window: WeeklyNewsWindow,
    rationale: WeeklyNewsSelectionRationale,
) -> WeeklyNewsItem:
    return WeeklyNewsItem(
        event_id=candidate.event_id,
        asset_ticker=_normalize_ticker(candidate.asset_ticker),
        event_type=candidate.event_type,
        title=candidate.title,
        summary=candidate.summary,
        event_date=candidate.event_date,
        published_at=candidate.published_at,
        period_bucket=_period_bucket(candidate.event_date, window),
        citation_ids=[_weekly_citation_id(candidate.event_id)],
        source=WeeklyNewsSourceMetadata(
            source_document_id=candidate.source_document_id,
            source_type=candidate.source_type,
            title=candidate.source_title,
            publisher=candidate.publisher,
            url=candidate.url,
            published_at=candidate.published_at,
            as_of_date=candidate.event_date,
            retrieved_at=candidate.retrieved_at,
            freshness_state=candidate.freshness_state,
            is_official=candidate.is_official,
            source_quality=candidate.source_quality,
            allowlist_status=candidate.allowlist_status,
            source_use_policy=candidate.source_use_policy,
        ),
        freshness_state=candidate.freshness_state,
        importance_score=rationale.total_score,
        deduplication=WeeklyNewsDeduplicationMetadata(
            canonical_event_key=_canonical_event_key(candidate),
            duplicate_group_id=candidate.duplicate_group_id,
            duplicate_of_event_id=candidate.duplicate_of_event_id,
            is_duplicate=candidate.is_duplicate,
        ),
        selection_rationale=rationale,
    )


def _candidate_from_recent_development(item: RetrievedRecentDevelopment) -> WeeklyNewsCandidate:
    source = item.source_document
    recent = item.recent_development
    return WeeklyNewsCandidate(
        event_id=recent.event_id,
        asset_ticker=recent.asset_ticker,
        event_type=WeeklyNewsEventType(recent.event_type) if recent.event_type in WeeklyNewsEventType._value2member_map_ else WeeklyNewsEventType.other,
        title=recent.title,
        summary=recent.summary,
        event_date=recent.event_date or source.as_of_date or source.published_at or "1970-01-01",
        published_at=source.published_at,
        retrieved_at=source.retrieved_at,
        source_document_id=source.source_document_id,
        source_chunk_id=recent.source_chunk_id,
        source_type=source.source_type,
        source_rank=source.source_rank,
        source_title=source.title,
        publisher=source.publisher,
        url=source.url,
        source_quality=source.source_quality,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        freshness_state=recent.freshness_state,
        is_official=source.is_official,
        supporting_text=item.source_chunk.text,
        asset_relevance="exact",
    )


def _source_document_from_item(item: WeeklyNewsItem) -> SourceDocument:
    decision = resolve_source_policy(
        url=item.source.url,
        source_identifier=item.source.url if item.source.url.startswith("local://") else None,
    )
    return SourceDocument(
        source_document_id=item.source.source_document_id,
        source_type=item.source.source_type,
        title=item.source.title,
        publisher=item.source.publisher,
        url=item.source.url,
        published_at=item.source.published_at,
        as_of_date=item.source.as_of_date,
        retrieved_at=item.source.retrieved_at,
        freshness_state=item.source.freshness_state,
        is_official=item.source.is_official,
        supporting_passage=item.summary,
        source_quality=item.source.source_quality,
        allowlist_status=item.source.allowlist_status,
        source_use_policy=item.source.source_use_policy,
        permitted_operations=decision.permitted_operations,
        **source_handoff_fields_from_policy(
            decision,
            source_identity=item.source.url or item.source.source_document_id,
            approval_rationale="Weekly News Focus source passed local source-use policy review.",
        ),
    )


def _weekly_citation_id(event_id: str) -> str:
    return f"c_weekly_{event_id}"


def _source_quality_weight(candidate: WeeklyNewsCandidate) -> int:
    if candidate.is_official or candidate.source_quality in {SourceQuality.official, SourceQuality.issuer}:
        return 5
    if candidate.source_quality in {SourceQuality.allowlisted, SourceQuality.fixture}:
        return 3
    if candidate.source_quality is SourceQuality.provider:
        return 1
    return 0


def _source_rank_tier_for_candidate(candidate: WeeklyNewsCandidate) -> str:
    if candidate.is_official or candidate.source_quality in {SourceQuality.official, SourceQuality.issuer}:
        return "investor_relations_release" if candidate.source_type == "issuer_press_release" else "official_filing"
    if candidate.source_quality in {SourceQuality.allowlisted, SourceQuality.fixture}:
        return "allowlisted_news"
    if candidate.source_quality is SourceQuality.provider:
        return "provider_context"
    return "unknown"


def _event_type_weight(event_type: WeeklyNewsEventType) -> int:
    return {
        WeeklyNewsEventType.earnings: 5,
        WeeklyNewsEventType.guidance: 5,
        WeeklyNewsEventType.fee_change: 5,
        WeeklyNewsEventType.methodology_change: 5,
        WeeklyNewsEventType.index_change: 4,
        WeeklyNewsEventType.fund_merger: 4,
        WeeklyNewsEventType.fund_liquidation: 4,
        WeeklyNewsEventType.sponsor_update: 3,
        WeeklyNewsEventType.product_announcement: 3,
        WeeklyNewsEventType.regulatory_event: 3,
        WeeklyNewsEventType.legal_event: 3,
        WeeklyNewsEventType.capital_allocation: 3,
        WeeklyNewsEventType.large_flow_event: 2,
        WeeklyNewsEventType.other: 1,
    }.get(event_type, 0)


def _recency_weight(candidate: WeeklyNewsCandidate, window: WeeklyNewsWindow) -> int:
    if not _date_in_window(candidate.event_date, window):
        return 0
    return 3 if _period_bucket(candidate.event_date, window) is WeeklyNewsPeriodBucket.current_week_to_date else 2


def _asset_relevance_weight(asset: AssetIdentity, candidate: WeeklyNewsCandidate) -> int:
    if _normalize_ticker(candidate.asset_ticker) != _normalize_ticker(asset.ticker):
        return 0
    if candidate.asset_relevance == "exact":
        return 3
    if candidate.asset_relevance == "strong":
        return 2
    return 1


def _date_in_window(value: str, window: WeeklyNewsWindow) -> bool:
    event_date = date.fromisoformat(value)
    return date.fromisoformat(window.news_window_start) <= event_date <= date.fromisoformat(window.news_window_end)


def _period_bucket(value: str, window: WeeklyNewsWindow) -> WeeklyNewsPeriodBucket:
    event_date = date.fromisoformat(value)
    current_start = window.current_week_to_date.start
    current_end = window.current_week_to_date.end
    if current_start and current_end and date.fromisoformat(current_start) <= event_date <= date.fromisoformat(current_end):
        return WeeklyNewsPeriodBucket.current_week_to_date
    return WeeklyNewsPeriodBucket.previous_market_week


def _canonical_event_key(candidate: WeeklyNewsCandidate) -> str:
    title = " ".join(candidate.title.lower().split())
    return f"{candidate.asset_ticker.upper()}:{candidate.event_type.value}:{candidate.event_date}:{title}"


def _eastern_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=_EASTERN)
        return aware.astimezone(_EASTERN).date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()
