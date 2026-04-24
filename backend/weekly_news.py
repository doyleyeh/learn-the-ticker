from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from backend.models import (
    AIComprehensiveAnalysisResponse,
    AIComprehensiveAnalysisSection,
    AssetIdentity,
    Citation,
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
    MarketWeekPeriod,
)
from backend.retrieval import AssetKnowledgePack, RetrievedRecentDevelopment
from backend.safety import find_forbidden_output_phrases


DEFAULT_WEEKLY_NEWS_AS_OF = "2026-04-23"
MINIMUM_DISPLAY_SCORE = 7
MINIMUM_AI_ANALYSIS_ITEMS = 2
MAX_WEEKLY_ITEMS = 8

_EASTERN = ZoneInfo("America/New_York")


class WeeklyNewsContractError(ValueError):
    """Raised when deterministic Weekly News Focus contracts are violated."""


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


def compute_weekly_news_window(as_of: str | date | datetime) -> WeeklyNewsWindow:
    """Return the deterministic Eastern market-week window for an explicit as-of date."""

    as_of_date = _eastern_date(as_of)
    current_monday = as_of_date - timedelta(days=as_of_date.weekday())
    previous_monday = current_monday - timedelta(days=7)
    previous_sunday = current_monday - timedelta(days=1)
    yesterday = as_of_date - timedelta(days=1)

    if yesterday >= current_monday:
        current_period = MarketWeekPeriod(start=current_monday.isoformat(), end=yesterday.isoformat())
        news_window_end = yesterday
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
    )


def build_weekly_news_focus_from_pack(
    pack: AssetKnowledgePack,
    *,
    as_of: str | date | datetime,
) -> WeeklyNewsFocusResponse:
    candidates = [_candidate_from_recent_development(item) for item in pack.recent_developments]
    return select_weekly_news_focus(pack.asset, candidates, as_of=as_of)


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

    ranked_selected_candidates = sorted(
        selected_candidates,
        key=lambda item: (
            item.selection_rationale.source_priority,
            -item.importance_score,
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


def build_ai_comprehensive_analysis(
    asset: AssetIdentity,
    weekly_news_focus: WeeklyNewsFocusResponse,
    *,
    canonical_fact_citation_ids: list[str] | None = None,
    canonical_source_document_ids: list[str] | None = None,
) -> AIComprehensiveAnalysisResponse:
    canonical_fact_citation_ids = sorted(set(canonical_fact_citation_ids or []))
    canonical_source_document_ids = sorted(set(canonical_source_document_ids or []))

    if len(weekly_news_focus.items) < MINIMUM_AI_ANALYSIS_ITEMS:
        return AIComprehensiveAnalysisResponse(
            asset=asset,
            state=WeeklyNewsContractState.suppressed,
            analysis_available=False,
            minimum_weekly_news_item_count=MINIMUM_AI_ANALYSIS_ITEMS,
            weekly_news_selected_item_count=weekly_news_focus.selected_item_count,
            suppression_reason="AI Comprehensive Analysis is suppressed because fewer than two high-signal Weekly News Focus items are available.",
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
    first_titles = "; ".join(item.title for item in weekly_news_focus.items[:2])
    asset_kind = "fund" if asset.asset_type.value == "etf" else "business"

    sections = [
        AIComprehensiveAnalysisSection(
            section_id="what_changed_this_week",
            label="What Changed This Week",
            analysis=f"The local Weekly News Focus pack selected these high-signal items for {asset.ticker}: {first_titles}.",
            bullets=["The analysis is limited to selected Weekly News Focus items and cited canonical facts."],
            citation_ids=all_citations,
            uncertainty=["This is deterministic fixture context, not live news coverage."],
        ),
        AIComprehensiveAnalysisSection(
            section_id="market_context",
            label="Market Context",
            analysis="The selected items provide timely context for understanding the asset, while stable facts remain the source for identity and structure.",
            bullets=["Recent context is kept outside the canonical asset facts."],
            citation_ids=weekly_citations,
            uncertainty=[],
        ),
        AIComprehensiveAnalysisSection(
            section_id="business_or_fund_context",
            label="Business/Fund Context",
            analysis=f"For a beginner, the items should be read beside the cited stable {asset_kind} facts rather than as a replacement for them.",
            bullets=["Canonical facts and Weekly News Focus use separate citation sets."],
            citation_ids=all_citations,
            uncertainty=[],
        ),
        AIComprehensiveAnalysisSection(
            section_id="risk_context",
            label="Risk Context",
            analysis="The items can highlight what to review next, but they do not predict returns or provide a personal decision.",
            bullets=["Use this context to inspect risks and source evidence, not as a trading instruction."],
            citation_ids=weekly_citations,
            uncertainty=["The fixture may omit other high-signal items that are not represented locally."],
        ),
    ]
    response = AIComprehensiveAnalysisResponse(
        asset=asset,
        state=WeeklyNewsContractState.available,
        analysis_available=True,
        minimum_weekly_news_item_count=MINIMUM_AI_ANALYSIS_ITEMS,
        weekly_news_selected_item_count=weekly_news_focus.selected_item_count,
        sections=sections,
        citation_ids=all_citations,
        source_document_ids=source_ids,
        weekly_news_event_ids=event_ids,
        canonical_fact_citation_ids=canonical_fact_citation_ids,
    )
    validate_ai_comprehensive_analysis(response, weekly_news_focus)
    return response


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


def _selection_rationale(
    asset: AssetIdentity,
    candidate: WeeklyNewsCandidate,
    window: WeeklyNewsWindow,
    minimum_display_score: int,
) -> WeeklyNewsSelectionRationale:
    exclusion_reasons: list[str] = []
    source_quality_weight = _source_quality_weight(candidate)
    event_type_weight = _event_type_weight(candidate.event_type)
    recency_weight = _recency_weight(candidate, window)
    asset_relevance_weight = _asset_relevance_weight(asset, candidate)
    duplicate_penalty = 5 if candidate.is_duplicate or candidate.duplicate_of_event_id else 0
    total_score = source_quality_weight + event_type_weight + recency_weight + asset_relevance_weight - duplicate_penalty

    if _normalize_ticker(candidate.asset_ticker) != _normalize_ticker(asset.ticker):
        exclusion_reasons.append("wrong_asset")
    if candidate.event_type is WeeklyNewsEventType.no_major_recent_development:
        exclusion_reasons.append("no_major_recent_development_marker")
    if not _date_in_window(candidate.event_date, window):
        exclusion_reasons.append("outside_market_week_window")
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
