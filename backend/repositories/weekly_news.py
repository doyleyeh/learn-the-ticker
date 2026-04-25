from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.models import (
    EvidenceState,
    FreshnessState,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsEventType,
    WeeklyNewsEvidenceLimitedState,
    WeeklyNewsPeriodBucket,
)
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow
from backend.weekly_news import compute_weekly_news_window


WEEKLY_NEWS_EVENT_EVIDENCE_REPOSITORY_BOUNDARY = "weekly-news-event-evidence-repository-contract-v1"
WEEKLY_NEWS_EVENT_EVIDENCE_SCHEMA_VERSION = "weekly-news-event-evidence-repository-v1"
WEEKLY_NEWS_EVENT_EVIDENCE_TABLES = (
    "weekly_news_market_week_windows",
    "weekly_news_event_candidates",
    "weekly_news_source_rank_inputs",
    "weekly_news_dedupe_groups",
    "weekly_news_selected_events",
    "weekly_news_evidence_states",
    "weekly_news_ai_thresholds",
    "weekly_news_validation_statuses",
    "weekly_news_diagnostics",
)

_SELECTABLE_SOURCE_POLICIES = {
    SourceUsePolicy.summary_allowed.value,
    SourceUsePolicy.full_text_allowed.value,
}
_SOURCE_POLICY_BLOCKED_REASONS = {
    "source_policy_blocked",
    "license_disallowed",
    "non_allowlisted_source",
    "rejected_source",
    "rights_incompatible",
    "unrecognized_source",
}
_CANDIDATE_BLOCKED_REASONS = {
    *_SOURCE_POLICY_BLOCKED_REASONS,
    "duplicate",
    "promotional",
    "irrelevant",
    "outside_market_week_window",
    "wrong_asset",
}
_ALLOWED_EVIDENCE_STATES = {
    EvidenceState.supported.value,
    EvidenceState.partial.value,
    EvidenceState.no_high_signal.value,
    EvidenceState.unavailable.value,
    EvidenceState.unknown.value,
    EvidenceState.stale.value,
    EvidenceState.insufficient_evidence.value,
}
_FORBIDDEN_DIAGNOSTIC_MARKERS = {
    "raw_article",
    "article_body",
    "raw_source_text",
    "source_passage",
    "full_text",
    "raw_provider_payload",
    "provider_payload",
    "hidden_prompt",
    "raw_prompt",
    "model_reasoning",
    "raw_user_text",
    "user_question",
    "raw_answer",
    "chat_transcript",
    "api" + "_key",
    "secret",
    "bearer ",
    "authorization",
    "signed_url",
    "public_url",
    "http://",
    "https://",
    "portfolio",
    "allocation",
    "position_size",
}


class WeeklyNewsEventEvidenceContractError(ValueError):
    """Raised when persisted Weekly News Focus evidence rows violate dormant contracts."""


class WeeklyNewsCandidateDecision(str, Enum):
    candidate = "candidate"
    selected = "selected"
    suppressed = "suppressed"


class WeeklyNewsSourceRankTier(str, Enum):
    official_filing = "official_filing"
    investor_relations_release = "investor_relations_release"
    etf_issuer_announcement = "etf_issuer_announcement"
    prospectus_update = "prospectus_update"
    fact_sheet_change = "fact_sheet_change"
    allowlisted_news = "allowlisted_news"
    provider_context = "provider_context"
    unknown = "unknown"


class WeeklyNewsValidationStatus(str, Enum):
    accepted = "accepted"
    rejected = "rejected"


class WeeklyNewsDiagnosticCategory(str, Enum):
    windowing = "windowing"
    ranking = "ranking"
    dedupe = "dedupe"
    source_policy = "source_policy"
    freshness = "freshness"
    citation_binding = "citation_binding"
    ai_threshold = "ai_threshold"
    privacy = "privacy"


class WeeklyNewsMarketWeekWindowRow(StrictRow):
    window_id: str
    asset_ticker: str
    schema_version: str = WEEKLY_NEWS_EVENT_EVIDENCE_SCHEMA_VERSION
    as_of_date: str
    timezone: str = "America/New_York"
    previous_market_week_start: str
    previous_market_week_end: str
    current_week_to_date_start: str | None = None
    current_week_to_date_end: str | None = None
    news_window_start: str
    news_window_end: str
    includes_current_week_to_date: bool
    configured_max_item_count: int = 8
    minimum_ai_analysis_item_count: int = 2
    no_live_external_calls: bool = True
    live_database_execution: bool = False
    provider_or_llm_call_required: bool = False
    generated_output_changed: bool = False
    stable_facts_are_separate: bool = True
    created_at: str


class WeeklyNewsEventCandidateRow(StrictRow):
    candidate_event_id: str
    window_id: str
    asset_ticker: str
    source_asset_ticker: str
    schema_version: str = WEEKLY_NEWS_EVENT_EVIDENCE_SCHEMA_VERSION
    event_type: str
    event_date: str | None = None
    published_at: str | None = None
    retrieved_at: str
    period_bucket: str
    source_document_id: str
    source_chunk_id: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    citation_asset_tickers: dict[str, str] = Field(default_factory=dict)
    source_type: str
    source_rank: int
    source_rank_tier: str
    source_quality: str
    allowlist_status: str
    source_use_policy: str
    freshness_state: str
    evidence_state: str = EvidenceState.supported.value
    importance_score: int
    high_signal: bool = True
    important_event_claim: bool = True
    license_allowed: bool = True
    recognized_source: bool = True
    promotional: bool = False
    irrelevant: bool = False
    duplicate_group_id: str | None = None
    duplicate_of_event_id: str | None = None
    candidate_decision: str = WeeklyNewsCandidateDecision.candidate.value
    suppression_reason_codes: list[str] = Field(default_factory=list)
    title_checksum: str | None = None
    evidence_checksum: str | None = None
    stores_raw_article_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_unrestricted_source_text: bool = False
    stores_secret: bool = False

    @field_validator("event_type")
    @classmethod
    def _valid_event_type(cls, value: str) -> str:
        WeeklyNewsEventType(value)
        return value

    @field_validator("period_bucket")
    @classmethod
    def _valid_period_bucket(cls, value: str) -> str:
        WeeklyNewsPeriodBucket(value)
        return value

    @field_validator("source_rank_tier")
    @classmethod
    def _valid_rank_tier(cls, value: str) -> str:
        WeeklyNewsSourceRankTier(value)
        return value

    @field_validator("source_quality")
    @classmethod
    def _valid_source_quality(cls, value: str) -> str:
        SourceQuality(value)
        return value

    @field_validator("allowlist_status")
    @classmethod
    def _valid_allowlist_status(cls, value: str) -> str:
        SourceAllowlistStatus(value)
        return value

    @field_validator("source_use_policy")
    @classmethod
    def _valid_source_use_policy(cls, value: str) -> str:
        SourceUsePolicy(value)
        return value

    @field_validator("freshness_state")
    @classmethod
    def _valid_freshness_state(cls, value: str) -> str:
        FreshnessState(value)
        return value


class WeeklyNewsSourceRankInputRow(StrictRow):
    candidate_event_id: str
    window_id: str
    asset_ticker: str
    source_rank_tier: str
    source_rank: int
    source_quality_weight: int
    event_type_weight: int
    recency_weight: int
    asset_relevance_weight: int
    duplicate_penalty: int = 0
    total_score: int
    minimum_display_score: int = 7
    selected_by_score: bool
    source_policy_allowed: bool
    created_at: str

    @field_validator("source_rank_tier")
    @classmethod
    def _valid_rank_tier(cls, value: str) -> str:
        WeeklyNewsSourceRankTier(value)
        return value


class WeeklyNewsDedupeGroupRow(StrictRow):
    dedupe_group_id: str
    window_id: str
    asset_ticker: str
    canonical_event_key: str
    retained_candidate_event_id: str | None = None
    duplicate_candidate_event_ids: list[str] = Field(default_factory=list)
    dedupe_status: str = "unique"
    reason_codes: list[str] = Field(default_factory=list)
    created_at: str


class WeeklyNewsSelectedEventRow(StrictRow):
    selected_event_id: str
    candidate_event_id: str
    window_id: str
    asset_ticker: str
    event_type: str
    period_bucket: str
    event_date: str | None = None
    published_at: str | None = None
    retrieved_at: str
    source_document_id: str
    source_chunk_id: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    citation_asset_tickers: dict[str, str] = Field(default_factory=dict)
    source_quality: str
    allowlist_status: str
    source_use_policy: str
    freshness_state: str
    evidence_state: str
    importance_score: int
    rank_position: int
    configured_max_item_count: int
    selected_item_count: int
    suppressed_candidate_count: int
    dedupe_group_id: str | None = None
    canonical_event_key: str
    suppression_reason_codes: list[str] = Field(default_factory=list)
    generated_output_state: str = "persisted_evidence_only"
    no_generated_analysis_change: bool = True

    @field_validator("event_type")
    @classmethod
    def _valid_event_type(cls, value: str) -> str:
        WeeklyNewsEventType(value)
        return value

    @field_validator("period_bucket")
    @classmethod
    def _valid_period_bucket(cls, value: str) -> str:
        WeeklyNewsPeriodBucket(value)
        return value


class WeeklyNewsEvidenceStateRow(StrictRow):
    evidence_state_id: str
    window_id: str
    asset_ticker: str
    state: str
    evidence_state: str
    evidence_limited_state: str
    configured_max_item_count: int
    selected_item_count: int
    suppressed_candidate_count: int
    empty_state_valid: bool = False
    limited_state_valid: bool = False
    missing_evidence_label: str | None = None
    stable_facts_are_separate: bool = True
    created_at: str

    @field_validator("state")
    @classmethod
    def _valid_state(cls, value: str) -> str:
        WeeklyNewsContractState(value)
        return value

    @field_validator("evidence_limited_state")
    @classmethod
    def _valid_limited_state(cls, value: str) -> str:
        WeeklyNewsEvidenceLimitedState(value)
        return value


class WeeklyNewsAIThresholdRow(StrictRow):
    threshold_id: str
    window_id: str
    asset_ticker: str
    minimum_weekly_news_item_count: int = 2
    selected_item_count: int
    high_signal_selected_item_count: int
    analysis_allowed: bool
    analysis_state: str
    suppression_reason_code: str | None = None
    selected_event_ids: list[str] = Field(default_factory=list)
    canonical_fact_citation_ids: list[str] = Field(default_factory=list)
    generated_analysis_state: str = "threshold_metadata_only"
    no_generated_analysis_change: bool = True
    created_at: str

    @field_validator("analysis_state")
    @classmethod
    def _valid_analysis_state(cls, value: str) -> str:
        WeeklyNewsContractState(value)
        return value


class WeeklyNewsValidationStatusRow(StrictRow):
    validation_id: str
    window_id: str
    subject_type: str
    subject_id: str
    validation_status: str = WeeklyNewsValidationStatus.accepted.value
    citation_validation_status: str = "same_asset_ids"
    source_use_status: str = "allowed"
    freshness_status: str = "labeled"
    generated_output_status: str = "unchanged"
    rejection_reason_codes: list[str] = Field(default_factory=list)
    validated_at: str

    @field_validator("validation_status")
    @classmethod
    def _valid_validation_status(cls, value: str) -> str:
        WeeklyNewsValidationStatus(value)
        return value


class WeeklyNewsDiagnosticRow(StrictRow):
    diagnostic_id: str
    window_id: str
    candidate_event_id: str | None = None
    selected_event_id: str | None = None
    category: str
    code: str
    created_at: str
    compact_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    freshness_labels: dict[str, str] = Field(default_factory=dict)
    source_document_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    checksums: list[str] = Field(default_factory=list)
    rank_inputs: dict[str, int | float | bool | str | None] = Field(default_factory=dict)
    suppression_reason_codes: list[str] = Field(default_factory=list)
    validation_status: str = WeeklyNewsValidationStatus.accepted.value
    stores_raw_article_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_unrestricted_source_text: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_raw_user_text: bool = False
    stores_secret: bool = False
    stores_public_or_signed_url: bool = False

    @field_validator("category")
    @classmethod
    def _valid_category(cls, value: str) -> str:
        WeeklyNewsDiagnosticCategory(value)
        return value

    @field_validator("validation_status")
    @classmethod
    def _valid_validation_status(cls, value: str) -> str:
        WeeklyNewsValidationStatus(value)
        return value


class WeeklyNewsEventEvidenceRepositoryRecords(StrictRow):
    windows: list[WeeklyNewsMarketWeekWindowRow] = Field(default_factory=list)
    candidates: list[WeeklyNewsEventCandidateRow] = Field(default_factory=list)
    source_rank_inputs: list[WeeklyNewsSourceRankInputRow] = Field(default_factory=list)
    dedupe_groups: list[WeeklyNewsDedupeGroupRow] = Field(default_factory=list)
    selected_events: list[WeeklyNewsSelectedEventRow] = Field(default_factory=list)
    evidence_states: list[WeeklyNewsEvidenceStateRow] = Field(default_factory=list)
    ai_thresholds: list[WeeklyNewsAIThresholdRow] = Field(default_factory=list)
    validation_statuses: list[WeeklyNewsValidationStatusRow] = Field(default_factory=list)
    diagnostics: list[WeeklyNewsDiagnosticRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return WEEKLY_NEWS_EVENT_EVIDENCE_TABLES


def weekly_news_event_evidence_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=WEEKLY_NEWS_EVENT_EVIDENCE_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="weekly_news_market_week_windows",
                primary_key=("window_id",),
                columns=tuple(WeeklyNewsMarketWeekWindowRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_event_candidates",
                primary_key=("candidate_event_id",),
                columns=tuple(WeeklyNewsEventCandidateRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_source_rank_inputs",
                primary_key=("candidate_event_id",),
                columns=tuple(WeeklyNewsSourceRankInputRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_dedupe_groups",
                primary_key=("dedupe_group_id",),
                columns=tuple(WeeklyNewsDedupeGroupRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_selected_events",
                primary_key=("selected_event_id",),
                columns=tuple(WeeklyNewsSelectedEventRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_evidence_states",
                primary_key=("evidence_state_id",),
                columns=tuple(WeeklyNewsEvidenceStateRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_ai_thresholds",
                primary_key=("threshold_id",),
                columns=tuple(WeeklyNewsAIThresholdRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_validation_statuses",
                primary_key=("validation_id",),
                columns=tuple(WeeklyNewsValidationStatusRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="weekly_news_diagnostics",
                primary_key=("diagnostic_id",),
                columns=tuple(WeeklyNewsDiagnosticRow.model_fields),
            ),
        ),
    )


@dataclass
class WeeklyNewsEventEvidenceRepository:
    session: Any | None = None

    def validate(
        self,
        records: WeeklyNewsEventEvidenceRepositoryRecords,
    ) -> WeeklyNewsEventEvidenceRepositoryRecords:
        return validate_weekly_news_event_evidence_records(records)

    def persist(
        self,
        records: WeeklyNewsEventEvidenceRepositoryRecords,
    ) -> WeeklyNewsEventEvidenceRepositoryRecords:
        validated = validate_weekly_news_event_evidence_records(records)
        if self.session is None:
            return validated
        if not hasattr(self.session, "add_all"):
            raise WeeklyNewsEventEvidenceContractError("Injected Weekly News Focus session must expose add_all(records).")
        self.session.add_all(records_to_row_list(validated))
        return validated


def build_market_week_window_row(
    *,
    asset_ticker: str,
    as_of: str,
    created_at: str,
    configured_max_item_count: int = 8,
    minimum_ai_analysis_item_count: int = 2,
    window_id: str | None = None,
) -> WeeklyNewsMarketWeekWindowRow:
    window = compute_weekly_news_window(as_of)
    normalized_ticker = _normalize_ticker(asset_ticker)
    return WeeklyNewsMarketWeekWindowRow(
        window_id=window_id or f"wnf_window:{normalized_ticker}:{window.as_of_date}",
        asset_ticker=normalized_ticker,
        as_of_date=window.as_of_date,
        previous_market_week_start=window.previous_market_week.start or "",
        previous_market_week_end=window.previous_market_week.end or "",
        current_week_to_date_start=window.current_week_to_date.start,
        current_week_to_date_end=window.current_week_to_date.end,
        news_window_start=window.news_window_start,
        news_window_end=window.news_window_end,
        includes_current_week_to_date=window.includes_current_week_to_date,
        configured_max_item_count=configured_max_item_count,
        minimum_ai_analysis_item_count=minimum_ai_analysis_item_count,
        created_at=created_at,
    )


def source_rank_tier_priority(source_rank_tier: str) -> int:
    return {
        WeeklyNewsSourceRankTier.official_filing.value: 1,
        WeeklyNewsSourceRankTier.investor_relations_release.value: 2,
        WeeklyNewsSourceRankTier.etf_issuer_announcement.value: 3,
        WeeklyNewsSourceRankTier.prospectus_update.value: 4,
        WeeklyNewsSourceRankTier.fact_sheet_change.value: 5,
        WeeklyNewsSourceRankTier.allowlisted_news.value: 20,
        WeeklyNewsSourceRankTier.provider_context.value: 30,
        WeeklyNewsSourceRankTier.unknown.value: 99,
    }[source_rank_tier]


def source_policy_allows_weekly_news_selection(candidate: WeeklyNewsEventCandidateRow) -> bool:
    return not _candidate_source_policy_reasons(candidate)


def records_to_row_list(records: WeeklyNewsEventEvidenceRepositoryRecords) -> list[StrictRow]:
    return [
        *records.windows,
        *records.candidates,
        *records.source_rank_inputs,
        *records.dedupe_groups,
        *records.selected_events,
        *records.evidence_states,
        *records.ai_thresholds,
        *records.validation_statuses,
        *records.diagnostics,
    ]


def validate_weekly_news_event_evidence_records(
    records: WeeklyNewsEventEvidenceRepositoryRecords,
) -> WeeklyNewsEventEvidenceRepositoryRecords:
    window_ids = _unique("market-week window IDs", [row.window_id for row in records.windows])
    candidate_ids = _unique("candidate event IDs", [row.candidate_event_id for row in records.candidates])
    selected_ids = _unique("selected event IDs", [row.selected_event_id for row in records.selected_events])
    _unique("source rank input candidate IDs", [row.candidate_event_id for row in records.source_rank_inputs])
    _unique("dedupe group IDs", [row.dedupe_group_id for row in records.dedupe_groups])
    _unique("evidence state IDs", [row.evidence_state_id for row in records.evidence_states])
    _unique("AI threshold IDs", [row.threshold_id for row in records.ai_thresholds])
    _unique("validation IDs", [row.validation_id for row in records.validation_statuses])
    _unique("diagnostic IDs", [row.diagnostic_id for row in records.diagnostics])

    windows_by_id = {row.window_id: row for row in records.windows}
    candidates_by_id = {row.candidate_event_id: row for row in records.candidates}
    selected_by_candidate: dict[str, WeeklyNewsSelectedEventRow] = {}

    for window in records.windows:
        _validate_window_row(window)
    for candidate in records.candidates:
        if candidate.window_id not in window_ids:
            raise WeeklyNewsEventEvidenceContractError("Candidate events must reference a persisted market-week window.")
        _validate_candidate_row(candidate, windows_by_id[candidate.window_id])
    for rank_input in records.source_rank_inputs:
        if rank_input.window_id not in window_ids or rank_input.candidate_event_id not in candidate_ids:
            raise WeeklyNewsEventEvidenceContractError("Source-rank inputs must reference persisted windows and candidates.")
        _validate_rank_input(rank_input, candidates_by_id[rank_input.candidate_event_id])
    for dedupe in records.dedupe_groups:
        if dedupe.window_id not in window_ids:
            raise WeeklyNewsEventEvidenceContractError("Dedupe groups must reference a persisted market-week window.")
        _validate_dedupe_group(dedupe, candidate_ids)
    for selected in records.selected_events:
        if selected.window_id not in window_ids or selected.candidate_event_id not in candidate_ids:
            raise WeeklyNewsEventEvidenceContractError("Selected events must reference persisted windows and candidates.")
        if selected.candidate_event_id in selected_by_candidate:
            raise WeeklyNewsEventEvidenceContractError("Duplicate selected Weekly News Focus candidates are not allowed.")
        selected_by_candidate[selected.candidate_event_id] = selected
        _validate_selected_event(selected, candidates_by_id[selected.candidate_event_id], windows_by_id[selected.window_id])
    _validate_selected_event_set(records.selected_events, windows_by_id)

    for state in records.evidence_states:
        if state.window_id not in window_ids:
            raise WeeklyNewsEventEvidenceContractError("Evidence states must reference a persisted market-week window.")
        _validate_evidence_state(state, windows_by_id[state.window_id], records.selected_events)
    for threshold in records.ai_thresholds:
        if threshold.window_id not in window_ids:
            raise WeeklyNewsEventEvidenceContractError("AI threshold rows must reference a persisted market-week window.")
        _validate_ai_threshold(threshold, records.selected_events)
    for validation in records.validation_statuses:
        if validation.window_id not in window_ids:
            raise WeeklyNewsEventEvidenceContractError("Validation rows must reference a persisted market-week window.")
        if validation.validation_status != WeeklyNewsValidationStatus.accepted.value:
            raise WeeklyNewsEventEvidenceContractError("Dormant Weekly News Focus records persist accepted contract rows only.")
        if validation.rejection_reason_codes:
            raise WeeklyNewsEventEvidenceContractError("Accepted validation rows cannot preserve rejected evidence.")
    for diagnostic in records.diagnostics:
        if diagnostic.window_id not in window_ids:
            raise WeeklyNewsEventEvidenceContractError("Diagnostics must reference a persisted market-week window.")
        if diagnostic.candidate_event_id and diagnostic.candidate_event_id not in candidate_ids:
            raise WeeklyNewsEventEvidenceContractError("Diagnostics must reference known candidate IDs.")
        if diagnostic.selected_event_id and diagnostic.selected_event_id not in selected_ids:
            raise WeeklyNewsEventEvidenceContractError("Diagnostics must reference known selected event IDs.")
        _validate_diagnostic(diagnostic)
    return records


def _validate_window_row(row: WeeklyNewsMarketWeekWindowRow) -> None:
    if row.timezone != "America/New_York":
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus windows must use U.S. Eastern dates.")
    expected = compute_weekly_news_window(row.as_of_date)
    if (
        row.previous_market_week_start != expected.previous_market_week.start
        or row.previous_market_week_end != expected.previous_market_week.end
        or row.current_week_to_date_start != expected.current_week_to_date.start
        or row.current_week_to_date_end != expected.current_week_to_date.end
        or row.news_window_start != expected.news_window_start
        or row.news_window_end != expected.news_window_end
        or row.includes_current_week_to_date != expected.includes_current_week_to_date
    ):
        raise WeeklyNewsEventEvidenceContractError(
            "Market-week metadata must match last completed Monday-Sunday plus current week-to-date through yesterday."
        )
    if row.configured_max_item_count < 0 or row.minimum_ai_analysis_item_count < 2:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus count thresholds are malformed.")
    if (
        not row.no_live_external_calls
        or row.live_database_execution
        or row.provider_or_llm_call_required
        or row.generated_output_changed
        or not row.stable_facts_are_separate
    ):
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus evidence repository contracts must stay dormant.")


def _validate_candidate_row(row: WeeklyNewsEventCandidateRow, window: WeeklyNewsMarketWeekWindowRow) -> None:
    _validate_same_asset(row.asset_ticker, window.asset_ticker, "Candidate")
    _validate_same_asset(row.source_asset_ticker, window.asset_ticker, "Candidate source")
    _validate_citation_assets(row.citation_asset_tickers, window.asset_ticker)
    _validate_ids([row.source_document_id, *(row.citation_ids), *(row.citation_asset_tickers)], "candidate source/citation")
    _validate_freshness_label(row.freshness_state, row.evidence_state)
    if row.important_event_claim and (not row.source_document_id or not row.citation_ids):
        raise WeeklyNewsEventEvidenceContractError("Important Weekly News Focus event claims require source and citation IDs.")
    if row.event_date is None and row.published_at is None:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus candidates need an event date or published timestamp.")
    if row.stores_raw_article_text or row.stores_raw_provider_payload or row.stores_unrestricted_source_text or row.stores_secret:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus candidates may store compact metadata only.")
    if row.importance_score < 0:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus importance scores cannot be negative.")
    reasons = _candidate_block_reasons(row)
    if row.candidate_decision == WeeklyNewsCandidateDecision.selected.value and reasons:
        raise WeeklyNewsEventEvidenceContractError("Selected candidate rows cannot carry source-policy, duplicate, or relevance blocks.")


def _validate_rank_input(row: WeeklyNewsSourceRankInputRow, candidate: WeeklyNewsEventCandidateRow) -> None:
    if row.window_id != candidate.window_id or _normalize_ticker(row.asset_ticker) != _normalize_ticker(candidate.asset_ticker):
        raise WeeklyNewsEventEvidenceContractError("Source-rank inputs must preserve candidate identity.")
    if row.source_rank_tier != candidate.source_rank_tier:
        raise WeeklyNewsEventEvidenceContractError("Source-rank inputs must preserve candidate source tier.")
    if row.source_rank < source_rank_tier_priority(row.source_rank_tier):
        raise WeeklyNewsEventEvidenceContractError("Source ranks must preserve official-first ordering metadata.")
    if row.selected_by_score and row.total_score < row.minimum_display_score:
        raise WeeklyNewsEventEvidenceContractError("Selected ranking inputs must meet the minimum display score.")
    if row.source_policy_allowed != source_policy_allows_weekly_news_selection(candidate):
        raise WeeklyNewsEventEvidenceContractError("Source-use policy must win over rank or recency.")


def _validate_dedupe_group(row: WeeklyNewsDedupeGroupRow, candidate_ids: set[str]) -> None:
    refs = [ref for ref in [row.retained_candidate_event_id, *row.duplicate_candidate_event_ids] if ref]
    if any(ref not in candidate_ids for ref in refs):
        raise WeeklyNewsEventEvidenceContractError("Dedupe groups must reference known candidate events.")
    if row.retained_candidate_event_id and row.retained_candidate_event_id in row.duplicate_candidate_event_ids:
        raise WeeklyNewsEventEvidenceContractError("A retained Weekly News Focus event cannot also be marked duplicate.")


def _validate_selected_event(
    selected: WeeklyNewsSelectedEventRow,
    candidate: WeeklyNewsEventCandidateRow,
    window: WeeklyNewsMarketWeekWindowRow,
) -> None:
    _validate_same_asset(selected.asset_ticker, window.asset_ticker, "Selected event")
    _validate_same_asset(selected.asset_ticker, candidate.asset_ticker, "Selected candidate")
    _validate_citation_assets(selected.citation_asset_tickers, window.asset_ticker)
    _validate_ids([selected.source_document_id, *(selected.citation_ids), *(selected.citation_asset_tickers)], "selected source/citation")
    _validate_freshness_label(selected.freshness_state, selected.evidence_state)
    if _candidate_block_reasons(candidate):
        raise WeeklyNewsEventEvidenceContractError("Source-policy-blocked, duplicate, promotional, irrelevant, or wrong-asset events cannot be selected.")
    if selected.source_document_id != candidate.source_document_id:
        raise WeeklyNewsEventEvidenceContractError("Selected events must preserve candidate source binding.")
    if selected.source_use_policy not in _SELECTABLE_SOURCE_POLICIES or selected.allowlist_status != SourceAllowlistStatus.allowed.value:
        raise WeeklyNewsEventEvidenceContractError("Selected events must use license-compatible allowlisted source evidence.")
    if selected.citation_ids != candidate.citation_ids:
        raise WeeklyNewsEventEvidenceContractError("Selected events must preserve candidate citation bindings.")
    if selected.configured_max_item_count != window.configured_max_item_count:
        raise WeeklyNewsEventEvidenceContractError("Selected-vs-configured item counts must match the market-week window.")
    if selected.selected_item_count < 0 or selected.selected_item_count > selected.configured_max_item_count:
        raise WeeklyNewsEventEvidenceContractError("Selected-vs-configured item counts are malformed.")
    if selected.rank_position < 1 or selected.rank_position > selected.selected_item_count:
        raise WeeklyNewsEventEvidenceContractError("Selected event rank positions must fit selected item counts.")
    if selected.generated_output_state != "persisted_evidence_only" or not selected.no_generated_analysis_change:
        raise WeeklyNewsEventEvidenceContractError("Dormant selected events cannot change generated output state.")


def _validate_selected_event_set(
    selected_events: list[WeeklyNewsSelectedEventRow],
    windows_by_id: dict[str, WeeklyNewsMarketWeekWindowRow],
) -> None:
    by_window: dict[str, list[WeeklyNewsSelectedEventRow]] = {}
    for row in selected_events:
        by_window.setdefault(row.window_id, []).append(row)
    for window_id, rows in by_window.items():
        window = windows_by_id[window_id]
        if len(rows) > window.configured_max_item_count:
            raise WeeklyNewsEventEvidenceContractError("Weekly News Focus must not exceed the configured maximum item count.")
        keys = [row.canonical_event_key for row in rows]
        if len(set(keys)) != len(keys):
            raise WeeklyNewsEventEvidenceContractError("Duplicate selected Weekly News Focus items are not allowed.")
        expected_count = len(rows)
        if any(row.selected_item_count != expected_count for row in rows):
            raise WeeklyNewsEventEvidenceContractError("Selected event rows must preserve selected-vs-configured counts.")


def _validate_evidence_state(
    row: WeeklyNewsEvidenceStateRow,
    window: WeeklyNewsMarketWeekWindowRow,
    selected_events: list[WeeklyNewsSelectedEventRow],
) -> None:
    selected_count = len([event for event in selected_events if event.window_id == row.window_id])
    if row.selected_item_count != selected_count or row.configured_max_item_count != window.configured_max_item_count:
        raise WeeklyNewsEventEvidenceContractError("Evidence-limited states must preserve selected-vs-configured counts.")
    if row.selected_item_count > row.configured_max_item_count:
        raise WeeklyNewsEventEvidenceContractError("Evidence state selected counts cannot exceed configured maximums.")
    if row.evidence_state not in _ALLOWED_EVIDENCE_STATES:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus evidence states must use explicit uncertainty labels.")
    if row.selected_item_count == 0 and not row.empty_state_valid:
        raise WeeklyNewsEventEvidenceContractError("Empty Weekly News Focus states are valid only with explicit empty-state metadata.")
    if 0 < row.selected_item_count < row.configured_max_item_count and not row.limited_state_valid:
        raise WeeklyNewsEventEvidenceContractError("Limited Weekly News Focus states must be explicitly labeled.")
    if not row.stable_facts_are_separate:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus evidence cannot overwrite canonical asset facts.")


def _validate_ai_threshold(row: WeeklyNewsAIThresholdRow, selected_events: list[WeeklyNewsSelectedEventRow]) -> None:
    selected_ids = {event.selected_event_id for event in selected_events if event.window_id == row.window_id}
    if not set(row.selected_event_ids) <= selected_ids:
        raise WeeklyNewsEventEvidenceContractError("AI threshold metadata must reference selected Weekly News Focus events only.")
    if row.selected_item_count != len(selected_ids) or row.high_signal_selected_item_count > row.selected_item_count:
        raise WeeklyNewsEventEvidenceContractError("AI threshold selected item counts are malformed.")
    enough_evidence = row.high_signal_selected_item_count >= row.minimum_weekly_news_item_count
    if row.analysis_allowed != enough_evidence:
        raise WeeklyNewsEventEvidenceContractError("AI Comprehensive Analysis threshold metadata must enforce the two-item rule.")
    if not enough_evidence and (row.analysis_state != WeeklyNewsContractState.suppressed.value or not row.suppression_reason_code):
        raise WeeklyNewsEventEvidenceContractError("AI Comprehensive Analysis must be suppressed with a reason when evidence is insufficient.")
    if row.generated_analysis_state != "threshold_metadata_only" or not row.no_generated_analysis_change:
        raise WeeklyNewsEventEvidenceContractError("AI threshold rows cannot introduce generated analysis output.")


def _validate_diagnostic(row: WeeklyNewsDiagnosticRow) -> None:
    text = repr(
        {
            "compact_metadata": row.compact_metadata,
            "freshness_labels": row.freshness_labels,
            "source_document_ids": row.source_document_ids,
            "event_ids": row.event_ids,
            "checksums": row.checksums,
            "rank_inputs": row.rank_inputs,
            "suppression_reason_codes": row.suppression_reason_codes,
        }
    ).lower()
    if any(marker in text for marker in _FORBIDDEN_DIAGNOSTIC_MARKERS):
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus diagnostics must be compact and sanitized.")
    if any(state not in {*(item.value for item in FreshnessState), *_ALLOWED_EVIDENCE_STATES} for state in row.freshness_labels.values()):
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus diagnostics must use explicit freshness labels.")
    if (
        row.stores_raw_article_text
        or row.stores_raw_provider_payload
        or row.stores_unrestricted_source_text
        or row.stores_hidden_prompt
        or row.stores_raw_model_reasoning
        or row.stores_raw_user_text
        or row.stores_secret
        or row.stores_public_or_signed_url
    ):
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus diagnostics may store sanitized compact metadata only.")


def _candidate_block_reasons(row: WeeklyNewsEventCandidateRow) -> list[str]:
    reasons = list(row.suppression_reason_codes)
    reasons.extend(_candidate_source_policy_reasons(row))
    if row.promotional:
        reasons.append("promotional")
    if row.irrelevant:
        reasons.append("irrelevant")
    if row.duplicate_of_event_id:
        reasons.append("duplicate")
    if _normalize_ticker(row.asset_ticker) != _normalize_ticker(row.source_asset_ticker):
        reasons.append("wrong_asset")
    return sorted(set(reasons))


def _candidate_source_policy_reasons(row: WeeklyNewsEventCandidateRow) -> list[str]:
    reasons: list[str] = []
    if not row.license_allowed:
        reasons.append("license_disallowed")
    if not row.recognized_source:
        reasons.append("unrecognized_source")
    if row.allowlist_status != SourceAllowlistStatus.allowed.value:
        reasons.append("non_allowlisted_source")
    if row.source_use_policy not in _SELECTABLE_SOURCE_POLICIES:
        reasons.append("source_policy_blocked")
    if row.source_quality == SourceQuality.rejected.value or row.source_use_policy == SourceUsePolicy.rejected.value:
        reasons.append("rejected_source")
    if set(row.suppression_reason_codes) & _SOURCE_POLICY_BLOCKED_REASONS:
        reasons.append("source_policy_blocked")
    return sorted(set(reasons))


def _validate_freshness_label(freshness_state: str, evidence_state: str) -> None:
    if freshness_state == FreshnessState.stale.value and evidence_state != EvidenceState.stale.value:
        raise WeeklyNewsEventEvidenceContractError("Stale Weekly News Focus evidence must carry a stale label.")
    if freshness_state == FreshnessState.unavailable.value and evidence_state != EvidenceState.unavailable.value:
        raise WeeklyNewsEventEvidenceContractError("Unavailable Weekly News Focus evidence must carry an unavailable label.")
    if evidence_state not in _ALLOWED_EVIDENCE_STATES:
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus evidence must use explicit uncertainty labels.")


def _validate_same_asset(left: str, right: str, label: str) -> None:
    if _normalize_ticker(left) != _normalize_ticker(right):
        raise WeeklyNewsEventEvidenceContractError(f"{label} rows must preserve same-asset binding.")


def _validate_citation_assets(citation_asset_tickers: dict[str, str], expected_ticker: str) -> None:
    for citation_id, ticker in citation_asset_tickers.items():
        _validate_ids([citation_id], "citation")
        _validate_same_asset(ticker, expected_ticker, "Citation")


def _validate_ids(values: list[str], label: str) -> None:
    for value in values:
        lowered = value.lower()
        if "http://" in lowered or "https://" in lowered or "signed_url" in lowered or "public_url" in lowered:
            raise WeeklyNewsEventEvidenceContractError(f"Weekly News Focus {label} references must remain opaque IDs.")


def _unique(label: str, values: list[str]) -> set[str]:
    seen = set(values)
    if len(seen) != len(values):
        raise WeeklyNewsEventEvidenceContractError(f"{label} must be unique.")
    return seen


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()
