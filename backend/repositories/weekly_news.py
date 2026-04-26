from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.data import ASSETS, OUT_OF_SCOPE_COMMON_STOCKS, UNSUPPORTED_ASSETS, normalize_ticker
from backend.models import (
    AssetStatus,
    AssetType,
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
WEEKLY_NEWS_FIXTURE_ACQUISITION_BOUNDARY = "weekly-news-fixture-acquisition-boundary-v1"
WEEKLY_NEWS_LIVE_ACQUISITION_READINESS_BOUNDARY = "weekly-news-live-acquisition-readiness-boundary-v1"
WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY = "weekly-news-official-source-mocked-acquisition-boundary-v1"
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
_OFFICIAL_SOURCE_RANK_TIERS = {
    "official_filing",
    "investor_relations_release",
    "etf_issuer_announcement",
    "prospectus_update",
    "fact_sheet_change",
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


@dataclass(frozen=True)
class WeeklyNewsLiveAcquisitionReadiness:
    boundary: str
    ticker: str
    status: str
    can_attempt_live_acquisition: bool
    blocked_reasons: tuple[str, ...]
    opt_in_enabled: bool
    official_source_configured: bool
    rate_limit_ready: bool
    repository_writer_ready: bool
    same_asset_support_state_valid: bool
    source_use_ready: bool
    market_week_window_ready: bool
    golden_asset_supported: bool
    no_live_external_calls: bool = True
    sanitized_diagnostics: dict[str, object] | None = None


@dataclass(frozen=True)
class WeeklyNewsOfficialSourceAcquisitionResult:
    boundary: str
    ticker: str
    status: str
    readiness: WeeklyNewsLiveAcquisitionReadiness
    records: WeeklyNewsEventEvidenceRepositoryRecords | None = None
    selected_event_count: int = 0
    candidate_count: int = 0
    configured_max_item_count: int = 8
    evidence_limited_state: str | None = None
    ai_analysis_allowed: bool = False
    sanitized_diagnostics: dict[str, object] | None = None
    no_live_external_calls: bool = True


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
    commit_on_write: bool = False

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
        tickers = sorted({_normalize_ticker(window.asset_ticker) for window in validated.windows})
        for ticker in tickers:
            _persist_records(
                self.session,
                collection="weekly_news_event_evidence",
                key=ticker,
                records=_records_for_ticker(validated, ticker),
                rows=records_to_row_list(validated),
                commit_on_write=self.commit_on_write,
            )
        return validated

    def read_weekly_news_event_evidence_records(
        self,
        ticker: str,
    ) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        if self.session is None:
            return None
        raw = _read_records(self.session, "weekly_news_event_evidence", _normalize_ticker(ticker))
        if raw is None:
            return None
        records = (
            raw
            if isinstance(raw, WeeklyNewsEventEvidenceRepositoryRecords)
            else WeeklyNewsEventEvidenceRepositoryRecords.model_validate(raw)
        )
        return validate_weekly_news_event_evidence_records(records)

    def read(self, ticker: str) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        return self.read_weekly_news_event_evidence_records(ticker)

    def get(self, ticker: str) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        return self.read_weekly_news_event_evidence_records(ticker)


@dataclass
class InMemoryWeeklyNewsEventEvidenceRepository:
    records_by_ticker: dict[str, WeeklyNewsEventEvidenceRepositoryRecords] = field(default_factory=dict)

    def persist(
        self,
        records: WeeklyNewsEventEvidenceRepositoryRecords,
    ) -> WeeklyNewsEventEvidenceRepositoryRecords:
        validated = validate_weekly_news_event_evidence_records(records)
        for ticker in sorted({_normalize_ticker(window.asset_ticker) for window in validated.windows}):
            ticker_records = _records_for_ticker(validated, ticker)
            self.records_by_ticker[ticker] = ticker_records.model_copy(deep=True)
        return validated

    def read_weekly_news_event_evidence_records(
        self,
        ticker: str,
    ) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        records = self.records_by_ticker.get(_normalize_ticker(ticker))
        return records.model_copy(deep=True) if records else None

    def read(self, ticker: str) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        return self.read_weekly_news_event_evidence_records(ticker)

    def get(self, ticker: str) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        return self.read_weekly_news_event_evidence_records(ticker)

    def records(self) -> list[WeeklyNewsEventEvidenceRepositoryRecords]:
        return [record.model_copy(deep=True) for record in self.records_by_ticker.values()]


@dataclass(frozen=True)
class WeeklyNewsFixtureAcquisitionBoundary:
    """Deterministic fixture-only selector for future Weekly News Focus acquisition workers."""

    configured_max_item_count: int = 8
    minimum_ai_analysis_item_count: int = 2
    minimum_display_score: int = 7

    def select(
        self,
        *,
        asset_ticker: str,
        as_of: str,
        created_at: str,
        candidates: list[WeeklyNewsEventCandidateRow],
    ) -> WeeklyNewsEventEvidenceRepositoryRecords:
        return acquire_weekly_news_event_evidence_from_fixtures(
            asset_ticker=asset_ticker,
            as_of=as_of,
            created_at=created_at,
            candidates=candidates,
            configured_max_item_count=self.configured_max_item_count,
            minimum_ai_analysis_item_count=self.minimum_ai_analysis_item_count,
            minimum_display_score=self.minimum_display_score,
        )


def acquire_weekly_news_event_evidence_from_fixtures(
    *,
    asset_ticker: str,
    as_of: str,
    created_at: str,
    candidates: list[WeeklyNewsEventCandidateRow],
    configured_max_item_count: int = 8,
    minimum_ai_analysis_item_count: int = 2,
    minimum_display_score: int = 7,
) -> WeeklyNewsEventEvidenceRepositoryRecords:
    """Transform local candidate rows into selected Weekly News Focus evidence rows."""

    normalized_ticker = _normalize_ticker(asset_ticker)
    window = build_market_week_window_row(
        asset_ticker=normalized_ticker,
        as_of=as_of,
        created_at=created_at,
        configured_max_item_count=configured_max_item_count,
        minimum_ai_analysis_item_count=minimum_ai_analysis_item_count,
    )

    candidate_rows: list[WeeklyNewsEventCandidateRow] = []
    rank_rows: list[WeeklyNewsSourceRankInputRow] = []
    skipped_wrong_asset_count = 0

    for candidate in candidates:
        if _normalize_ticker(candidate.asset_ticker) != normalized_ticker:
            skipped_wrong_asset_count += 1
            continue

        prepared, rank_input = _prepare_candidate_for_fixture_selection(
            candidate,
            window=window,
            created_at=created_at,
            minimum_display_score=minimum_display_score,
        )
        candidate_rows.append(prepared)
        rank_rows.append(rank_input)

    dedupe_groups, dedupe_suppressed_ids = _build_fixture_dedupe_groups(
        window=window,
        candidates=candidate_rows,
        created_at=created_at,
    )
    candidate_rows = [
        _mark_candidate_suppressed(candidate, "duplicate") if candidate.candidate_event_id in dedupe_suppressed_ids else candidate
        for candidate in candidate_rows
    ]
    rank_rows = [
        rank.model_copy(update={"duplicate_penalty": 5, "total_score": max(0, rank.total_score - 5), "selected_by_score": False})
        if rank.candidate_event_id in dedupe_suppressed_ids
        else rank
        for rank in rank_rows
    ]

    selectable = [
        candidate
        for candidate in candidate_rows
        if not _candidate_block_reasons(candidate)
        and _rank_input_by_candidate_id(rank_rows, candidate.candidate_event_id).selected_by_score
    ]
    ranked = sorted(
        selectable,
        key=lambda row: (
            source_rank_tier_priority(row.source_rank_tier),
            row.source_rank,
            -row.importance_score,
            row.event_date or row.published_at or "",
            row.candidate_event_id,
        ),
    )
    selected_candidates = ranked[:configured_max_item_count]
    selected_ids = {row.candidate_event_id for row in selected_candidates}

    final_candidates = [
        candidate.model_copy(
            update={
                "candidate_decision": WeeklyNewsCandidateDecision.selected.value
                if candidate.candidate_event_id in selected_ids
                else WeeklyNewsCandidateDecision.suppressed.value,
                "suppression_reason_codes": []
                if candidate.candidate_event_id in selected_ids
                else sorted(set(candidate.suppression_reason_codes or ["not_selected"])),
            }
        )
        for candidate in candidate_rows
    ]

    suppressed_count = len(final_candidates) - len(selected_candidates) + skipped_wrong_asset_count
    selected_events = [
        _selected_event_from_candidate(
            candidate,
            rank_position=index,
            selected_item_count=len(selected_candidates),
            suppressed_candidate_count=suppressed_count,
            configured_max_item_count=configured_max_item_count,
        )
        for index, candidate in enumerate(selected_candidates, start=1)
    ]
    evidence_state = _evidence_state_row(
        window=window,
        selected_count=len(selected_candidates),
        suppressed_count=suppressed_count,
        created_at=created_at,
    )
    threshold = _ai_threshold_row(
        window=window,
        selected_events=selected_events,
        selected_candidates=selected_candidates,
        created_at=created_at,
    )
    diagnostics = _fixture_acquisition_diagnostics(
        window=window,
        candidates=final_candidates,
        selected_events=selected_events,
        suppressed_count=suppressed_count,
        skipped_wrong_asset_count=skipped_wrong_asset_count,
        created_at=created_at,
    )

    records = WeeklyNewsEventEvidenceRepositoryRecords(
        windows=[window],
        candidates=final_candidates,
        source_rank_inputs=rank_rows,
        dedupe_groups=dedupe_groups,
        selected_events=selected_events,
        evidence_states=[evidence_state],
        ai_thresholds=[threshold],
        validation_statuses=[
            WeeklyNewsValidationStatusRow(
                validation_id=f"validation:{window.window_id}:fixture_acquisition",
                window_id=window.window_id,
                subject_type="fixture_acquisition",
                subject_id=window.window_id,
                validated_at=created_at,
            )
        ],
        diagnostics=diagnostics,
    )
    return validate_weekly_news_event_evidence_records(records)


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


def evaluate_weekly_news_live_acquisition_readiness(
    ticker: str,
    *,
    settings=None,
    opt_in_enabled: bool | None = None,
    official_source_configured: bool | None = None,
    rate_limit_ready: bool | None = None,
    repository_writer_ready: bool | None = None,
    as_of: str = "2026-04-23",
    candidates: list[WeeklyNewsEventCandidateRow] | None = None,
) -> WeeklyNewsLiveAcquisitionReadiness:
    normalized = _normalize_ticker(ticker)
    opt_in = _setting_bool(settings, "weekly_news_enabled", opt_in_enabled, False)
    source_configured = _setting_bool(
        settings,
        "weekly_news_official_source_configured",
        official_source_configured,
        False,
    )
    rate_ready = _setting_bool(settings, "rate_limit_ready", rate_limit_ready, False)
    writer_ready = _setting_bool(settings, "weekly_news_evidence_writer_ready", repository_writer_ready, False)
    support_valid = _same_asset_support_state_valid(normalized)
    golden_supported = normalized in {"AAPL", "VOO", "QQQ"} and support_valid
    window_ready = _market_week_window_ready(as_of)
    source_ready = _official_source_candidates_ready(normalized, candidates or [])

    blocked: list[str] = []
    if not opt_in:
        blocked.append("explicit_live_weekly_news_acquisition_opt_in_missing")
    if not source_configured:
        blocked.append("weekly_news_official_source_configuration_missing")
    if not rate_ready:
        blocked.append("source_rate_limit_not_ready")
    if not writer_ready:
        blocked.append("weekly_news_evidence_repository_writer_not_ready")
    if not support_valid:
        if normalized in UNSUPPORTED_ASSETS:
            blocked.append("unsupported_asset")
        elif normalized in OUT_OF_SCOPE_COMMON_STOCKS:
            blocked.append("out_of_scope_asset")
        else:
            blocked.append("same_asset_support_state_validation_failed")
    if not golden_supported:
        blocked.append("golden_asset_scope_validation_failed")
    if not window_ready:
        blocked.append("market_week_window_validation_failed")
    if candidates is not None and not source_ready:
        blocked.append("official_source_use_validation_failed")

    can_attempt = not blocked
    diagnostics = {
        "boundary": WEEKLY_NEWS_LIVE_ACQUISITION_READINESS_BOUNDARY,
        "status": "ready" if can_attempt else "blocked",
        "blocked_reasons": list(blocked),
        "ticker": normalized,
        "candidate_count": len(candidates or []),
        "no_live_external_calls": True,
    }
    return WeeklyNewsLiveAcquisitionReadiness(
        boundary=WEEKLY_NEWS_LIVE_ACQUISITION_READINESS_BOUNDARY,
        ticker=normalized,
        status="ready" if can_attempt else "blocked",
        can_attempt_live_acquisition=can_attempt,
        blocked_reasons=tuple(blocked),
        opt_in_enabled=opt_in,
        official_source_configured=source_configured,
        rate_limit_ready=rate_ready,
        repository_writer_ready=writer_ready,
        same_asset_support_state_valid=support_valid,
        source_use_ready=source_ready,
        market_week_window_ready=window_ready,
        golden_asset_supported=golden_supported,
        sanitized_diagnostics=diagnostics,
    )


def acquire_weekly_news_event_evidence_from_official_sources(
    *,
    asset_ticker: str,
    as_of: str,
    created_at: str,
    candidates: list[WeeklyNewsEventCandidateRow],
    settings=None,
    opt_in_enabled: bool | None = None,
    official_source_configured: bool | None = None,
    rate_limit_ready: bool | None = None,
    repository_writer_ready: bool | None = None,
    configured_max_item_count: int = 8,
    minimum_ai_analysis_item_count: int = 2,
    minimum_display_score: int = 7,
) -> WeeklyNewsOfficialSourceAcquisitionResult:
    normalized = _normalize_ticker(asset_ticker)
    readiness = evaluate_weekly_news_live_acquisition_readiness(
        normalized,
        settings=settings,
        opt_in_enabled=opt_in_enabled,
        official_source_configured=official_source_configured,
        rate_limit_ready=rate_limit_ready,
        repository_writer_ready=repository_writer_ready,
        as_of=as_of,
        candidates=candidates,
    )
    if not readiness.can_attempt_live_acquisition:
        return WeeklyNewsOfficialSourceAcquisitionResult(
            boundary=WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY,
            ticker=normalized,
            status="blocked",
            readiness=readiness,
            candidate_count=len(candidates),
            configured_max_item_count=configured_max_item_count,
            sanitized_diagnostics=readiness.sanitized_diagnostics,
        )

    official_candidates = [
        candidate
        for candidate in candidates
        if candidate.source_rank_tier in _OFFICIAL_SOURCE_RANK_TIERS
    ]
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker=normalized,
        as_of=as_of,
        created_at=created_at,
        candidates=official_candidates,
        configured_max_item_count=configured_max_item_count,
        minimum_ai_analysis_item_count=minimum_ai_analysis_item_count,
        minimum_display_score=minimum_display_score,
    )
    evidence_state = records.evidence_states[0] if records.evidence_states else None
    threshold = records.ai_thresholds[0] if records.ai_thresholds else None
    diagnostics = {
        "boundary": WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY,
        "status": "acquired",
        "ticker": normalized,
        "candidate_count": len(records.candidates),
        "selected_event_count": len(records.selected_events),
        "configured_max_item_count": configured_max_item_count,
        "evidence_limited_state": evidence_state.evidence_limited_state if evidence_state else None,
        "ai_analysis_allowed": threshold.analysis_allowed if threshold else False,
        "no_live_external_calls": True,
    }
    return WeeklyNewsOfficialSourceAcquisitionResult(
        boundary=WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY,
        ticker=normalized,
        status="acquired",
        readiness=readiness,
        records=records,
        selected_event_count=len(records.selected_events),
        candidate_count=len(records.candidates),
        configured_max_item_count=configured_max_item_count,
        evidence_limited_state=evidence_state.evidence_limited_state if evidence_state else None,
        ai_analysis_allowed=threshold.analysis_allowed if threshold else False,
        sanitized_diagnostics=diagnostics,
    )


def _prepare_candidate_for_fixture_selection(
    candidate: WeeklyNewsEventCandidateRow,
    *,
    window: WeeklyNewsMarketWeekWindowRow,
    created_at: str,
    minimum_display_score: int,
) -> tuple[WeeklyNewsEventCandidateRow, WeeklyNewsSourceRankInputRow]:
    period_bucket = _period_bucket_for_candidate(candidate, window)
    source_rank = max(candidate.source_rank, source_rank_tier_priority(candidate.source_rank_tier))
    source_quality_weight = _source_quality_weight(candidate)
    event_type_weight = _event_type_weight(candidate.event_type)
    recency_weight = _recency_weight(candidate, window)
    asset_relevance_weight = 3
    total_score = source_quality_weight + event_type_weight + recency_weight + asset_relevance_weight
    evidence_state = _freshness_labeled_evidence_state(candidate.freshness_state, candidate.evidence_state)
    source_policy_allowed = source_policy_allows_weekly_news_selection(candidate)
    reasons = _fixture_suppression_reasons(
        candidate,
        window=window,
        total_score=total_score,
        minimum_display_score=minimum_display_score,
    )

    prepared = candidate.model_copy(
        update={
            "window_id": window.window_id,
            "asset_ticker": window.asset_ticker,
            "source_asset_ticker": _normalize_ticker(candidate.source_asset_ticker),
            "period_bucket": period_bucket,
            "source_rank": source_rank,
            "evidence_state": evidence_state,
            "importance_score": total_score,
            "candidate_decision": WeeklyNewsCandidateDecision.suppressed.value
            if reasons
            else WeeklyNewsCandidateDecision.candidate.value,
            "suppression_reason_codes": reasons,
        }
    )
    return prepared, WeeklyNewsSourceRankInputRow(
        candidate_event_id=prepared.candidate_event_id,
        window_id=window.window_id,
        asset_ticker=window.asset_ticker,
        source_rank_tier=prepared.source_rank_tier,
        source_rank=source_rank,
        source_quality_weight=source_quality_weight,
        event_type_weight=event_type_weight,
        recency_weight=recency_weight,
        asset_relevance_weight=asset_relevance_weight,
        duplicate_penalty=0,
        total_score=total_score,
        minimum_display_score=minimum_display_score,
        selected_by_score=total_score >= minimum_display_score and source_policy_allowed and not reasons,
        source_policy_allowed=source_policy_allowed,
        created_at=created_at,
    )


def _build_fixture_dedupe_groups(
    *,
    window: WeeklyNewsMarketWeekWindowRow,
    candidates: list[WeeklyNewsEventCandidateRow],
    created_at: str,
) -> tuple[list[WeeklyNewsDedupeGroupRow], set[str]]:
    grouped: dict[str, list[WeeklyNewsEventCandidateRow]] = {}
    for candidate in candidates:
        key = candidate.duplicate_group_id or _canonical_event_key(candidate)
        grouped.setdefault(key, []).append(candidate)

    dedupe_rows: list[WeeklyNewsDedupeGroupRow] = []
    suppressed_ids: set[str] = set()
    for group_id, rows in grouped.items():
        ranked = sorted(
            rows,
            key=lambda row: (
                bool(_candidate_block_reasons(row)),
                source_rank_tier_priority(row.source_rank_tier),
                row.source_rank,
                -row.importance_score,
                row.candidate_event_id,
            ),
        )
        retained = ranked[0]
        duplicates = [row.candidate_event_id for row in ranked[1:]]
        suppressed_ids.update(duplicates)
        dedupe_rows.append(
            WeeklyNewsDedupeGroupRow(
                dedupe_group_id=group_id,
                window_id=window.window_id,
                asset_ticker=window.asset_ticker,
                canonical_event_key=_canonical_event_key(retained),
                retained_candidate_event_id=retained.candidate_event_id,
                duplicate_candidate_event_ids=duplicates,
                dedupe_status="deduped" if duplicates else "unique",
                reason_codes=["duplicate"] if duplicates else [],
                created_at=created_at,
            )
        )
    return dedupe_rows, suppressed_ids


def _mark_candidate_suppressed(candidate: WeeklyNewsEventCandidateRow, reason: str) -> WeeklyNewsEventCandidateRow:
    reasons = sorted({*candidate.suppression_reason_codes, reason})
    return candidate.model_copy(
        update={
            "candidate_decision": WeeklyNewsCandidateDecision.suppressed.value,
            "duplicate_of_event_id": candidate.duplicate_of_event_id or candidate.duplicate_group_id,
            "suppression_reason_codes": reasons,
        }
    )


def _rank_input_by_candidate_id(
    rows: list[WeeklyNewsSourceRankInputRow],
    candidate_event_id: str,
) -> WeeklyNewsSourceRankInputRow:
    for row in rows:
        if row.candidate_event_id == candidate_event_id:
            return row
    raise WeeklyNewsEventEvidenceContractError("Fixture acquisition rank inputs must reference every candidate.")


def _selected_event_from_candidate(
    candidate: WeeklyNewsEventCandidateRow,
    *,
    rank_position: int,
    selected_item_count: int,
    suppressed_candidate_count: int,
    configured_max_item_count: int,
) -> WeeklyNewsSelectedEventRow:
    return WeeklyNewsSelectedEventRow(
        selected_event_id=f"selected:{candidate.candidate_event_id}",
        candidate_event_id=candidate.candidate_event_id,
        window_id=candidate.window_id,
        asset_ticker=candidate.asset_ticker,
        event_type=candidate.event_type,
        period_bucket=candidate.period_bucket,
        event_date=candidate.event_date,
        published_at=candidate.published_at,
        retrieved_at=candidate.retrieved_at,
        source_document_id=candidate.source_document_id,
        source_chunk_id=candidate.source_chunk_id,
        citation_ids=candidate.citation_ids,
        citation_asset_tickers=candidate.citation_asset_tickers,
        source_quality=candidate.source_quality,
        allowlist_status=candidate.allowlist_status,
        source_use_policy=candidate.source_use_policy,
        freshness_state=candidate.freshness_state,
        evidence_state=candidate.evidence_state,
        importance_score=candidate.importance_score,
        rank_position=rank_position,
        configured_max_item_count=configured_max_item_count,
        selected_item_count=selected_item_count,
        suppressed_candidate_count=suppressed_candidate_count,
        dedupe_group_id=candidate.duplicate_group_id,
        canonical_event_key=_canonical_event_key(candidate),
    )


def _evidence_state_row(
    *,
    window: WeeklyNewsMarketWeekWindowRow,
    selected_count: int,
    suppressed_count: int,
    created_at: str,
) -> WeeklyNewsEvidenceStateRow:
    if selected_count == 0:
        state = WeeklyNewsContractState.no_high_signal.value
        evidence_state = EvidenceState.no_high_signal.value
        limited_state = WeeklyNewsEvidenceLimitedState.empty.value
        missing_label = EvidenceState.no_high_signal.value
    elif selected_count < window.configured_max_item_count:
        state = WeeklyNewsContractState.available.value
        evidence_state = EvidenceState.partial.value
        limited_state = WeeklyNewsEvidenceLimitedState.limited_verified_set.value
        missing_label = EvidenceState.partial.value
    else:
        state = WeeklyNewsContractState.available.value
        evidence_state = EvidenceState.supported.value
        limited_state = WeeklyNewsEvidenceLimitedState.full.value
        missing_label = None

    return WeeklyNewsEvidenceStateRow(
        evidence_state_id=f"evidence:{window.window_id}",
        window_id=window.window_id,
        asset_ticker=window.asset_ticker,
        state=state,
        evidence_state=evidence_state,
        evidence_limited_state=limited_state,
        configured_max_item_count=window.configured_max_item_count,
        selected_item_count=selected_count,
        suppressed_candidate_count=suppressed_count,
        empty_state_valid=selected_count == 0,
        limited_state_valid=0 < selected_count < window.configured_max_item_count,
        missing_evidence_label=missing_label,
        created_at=created_at,
    )


def _ai_threshold_row(
    *,
    window: WeeklyNewsMarketWeekWindowRow,
    selected_events: list[WeeklyNewsSelectedEventRow],
    selected_candidates: list[WeeklyNewsEventCandidateRow],
    created_at: str,
) -> WeeklyNewsAIThresholdRow:
    high_signal_count = len([candidate for candidate in selected_candidates if candidate.high_signal])
    analysis_allowed = high_signal_count >= window.minimum_ai_analysis_item_count
    return WeeklyNewsAIThresholdRow(
        threshold_id=f"threshold:{window.window_id}",
        window_id=window.window_id,
        asset_ticker=window.asset_ticker,
        minimum_weekly_news_item_count=window.minimum_ai_analysis_item_count,
        selected_item_count=len(selected_events),
        high_signal_selected_item_count=high_signal_count,
        analysis_allowed=analysis_allowed,
        analysis_state=WeeklyNewsContractState.available.value if analysis_allowed else WeeklyNewsContractState.suppressed.value,
        suppression_reason_code=None if analysis_allowed else "fewer_than_two_high_signal_items",
        selected_event_ids=[event.selected_event_id for event in selected_events],
        created_at=created_at,
    )


def _fixture_acquisition_diagnostics(
    *,
    window: WeeklyNewsMarketWeekWindowRow,
    candidates: list[WeeklyNewsEventCandidateRow],
    selected_events: list[WeeklyNewsSelectedEventRow],
    suppressed_count: int,
    skipped_wrong_asset_count: int,
    created_at: str,
) -> list[WeeklyNewsDiagnosticRow]:
    reason_codes = sorted({reason for candidate in candidates for reason in candidate.suppression_reason_codes})
    source_ids = sorted({candidate.source_document_id for candidate in candidates})
    event_ids = sorted({candidate.candidate_event_id for candidate in candidates})
    checksums = sorted({checksum for candidate in candidates for checksum in [candidate.title_checksum, candidate.evidence_checksum] if checksum})
    return [
        WeeklyNewsDiagnosticRow(
            diagnostic_id=f"diag:{window.window_id}:fixture_selection",
            window_id=window.window_id,
            category=WeeklyNewsDiagnosticCategory.ranking.value,
            code="fixture_selection_completed",
            created_at=created_at,
            compact_metadata={
                "candidate_count": len(candidates),
                "selected_count": len(selected_events),
                "suppressed_count": suppressed_count,
                "skipped_wrong_asset_count": skipped_wrong_asset_count,
                "configured_max_item_count": window.configured_max_item_count,
            },
            freshness_labels={candidate.candidate_event_id: candidate.freshness_state for candidate in candidates},
            source_document_ids=source_ids,
            event_ids=event_ids,
            checksums=checksums,
            rank_inputs={"minimum_ai_analysis_item_count": window.minimum_ai_analysis_item_count},
            suppression_reason_codes=reason_codes,
        )
    ]


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


def _records_for_ticker(
    records: WeeklyNewsEventEvidenceRepositoryRecords,
    ticker: str,
) -> WeeklyNewsEventEvidenceRepositoryRecords:
    normalized_ticker = _normalize_ticker(ticker)
    window_ids = {
        window.window_id
        for window in records.windows
        if _normalize_ticker(window.asset_ticker) == normalized_ticker
    }
    candidate_ids = {
        candidate.candidate_event_id
        for candidate in records.candidates
        if candidate.window_id in window_ids
    }
    selected_ids = {
        selected.selected_event_id
        for selected in records.selected_events
        if selected.window_id in window_ids
    }
    ticker_records = WeeklyNewsEventEvidenceRepositoryRecords(
        windows=[row for row in records.windows if row.window_id in window_ids],
        candidates=[row for row in records.candidates if row.window_id in window_ids],
        source_rank_inputs=[
            row
            for row in records.source_rank_inputs
            if row.window_id in window_ids and row.candidate_event_id in candidate_ids
        ],
        dedupe_groups=[row for row in records.dedupe_groups if row.window_id in window_ids],
        selected_events=[row for row in records.selected_events if row.window_id in window_ids],
        evidence_states=[row for row in records.evidence_states if row.window_id in window_ids],
        ai_thresholds=[row for row in records.ai_thresholds if row.window_id in window_ids],
        validation_statuses=[row for row in records.validation_statuses if row.window_id in window_ids],
        diagnostics=[
            row
            for row in records.diagnostics
            if row.window_id in window_ids
            and (row.candidate_event_id is None or row.candidate_event_id in candidate_ids)
            and (row.selected_event_id is None or row.selected_event_id in selected_ids)
        ],
    )
    return validate_weekly_news_event_evidence_records(ticker_records)


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
    if row.title_checksum is not None and not row.title_checksum.startswith("sha256:"):
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus title checksums must use sha256 metadata.")
    if row.evidence_checksum is None or not row.evidence_checksum.startswith("sha256:"):
        raise WeeklyNewsEventEvidenceContractError("Weekly News Focus evidence checksums must use sha256 metadata.")
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


def _fixture_suppression_reasons(
    candidate: WeeklyNewsEventCandidateRow,
    *,
    window: WeeklyNewsMarketWeekWindowRow,
    total_score: int,
    minimum_display_score: int,
) -> list[str]:
    reasons = set(candidate.suppression_reason_codes)
    reasons.update(_candidate_source_policy_reasons(candidate))
    if not _candidate_date_in_window(candidate, window):
        reasons.add("outside_market_week_window")
    if candidate.promotional:
        reasons.add("promotional")
    if candidate.irrelevant:
        reasons.add("irrelevant")
    if candidate.duplicate_of_event_id:
        reasons.add("duplicate")
    if candidate.event_type == WeeklyNewsEventType.no_major_recent_development.value:
        reasons.add("no_major_recent_development_marker")
    if total_score < minimum_display_score:
        reasons.add("below_minimum_display_score")
    return sorted(reasons)


def _setting_bool(settings, name: str, explicit: bool | None, default: bool) -> bool:
    if explicit is not None:
        return bool(explicit)
    if settings is not None and hasattr(settings, name):
        return bool(getattr(settings, name))
    return default


def _same_asset_support_state_valid(ticker: str) -> bool:
    asset = ASSETS.get(_normalize_ticker(ticker))
    if asset is None:
        return False
    identity = asset["identity"]
    asset_type = getattr(getattr(identity, "asset_type", None), "value", None)
    status = getattr(getattr(identity, "status", None), "value", None)
    return (
        getattr(identity, "ticker", None) == _normalize_ticker(ticker)
        and status == AssetStatus.supported.value
        and asset_type in {AssetType.stock.value, AssetType.etf.value}
    )


def _market_week_window_ready(as_of: str) -> bool:
    try:
        window = compute_weekly_news_window(as_of)
    except Exception:
        return False
    return (
        window.timezone == "America/New_York"
        and bool(window.news_window_start)
        and bool(window.news_window_end)
        and window.news_window_start <= window.news_window_end
    )


def _official_source_candidates_ready(ticker: str, candidates: list[WeeklyNewsEventCandidateRow]) -> bool:
    normalized = _normalize_ticker(ticker)
    try:
        for candidate in candidates:
            if _normalize_ticker(candidate.asset_ticker) != normalized:
                return False
            if _normalize_ticker(candidate.source_asset_ticker) != normalized:
                return False
            if candidate.source_rank_tier not in _OFFICIAL_SOURCE_RANK_TIERS:
                return False
            if candidate.source_quality not in {SourceQuality.official.value, SourceQuality.issuer.value}:
                return False
            if candidate.title_checksum is not None and not candidate.title_checksum.startswith("sha256:"):
                return False
            if candidate.evidence_checksum is None or not candidate.evidence_checksum.startswith("sha256:"):
                return False
            if candidate.stores_raw_article_text or candidate.stores_raw_provider_payload or candidate.stores_unrestricted_source_text:
                return False
        return True
    except Exception:
        return False


def _period_bucket_for_candidate(
    candidate: WeeklyNewsEventCandidateRow,
    window: WeeklyNewsMarketWeekWindowRow,
) -> str:
    event_date = _candidate_event_date(candidate)
    current_start = window.current_week_to_date_start
    current_end = window.current_week_to_date_end
    if current_start and current_end and date.fromisoformat(current_start) <= event_date <= date.fromisoformat(current_end):
        return WeeklyNewsPeriodBucket.current_week_to_date.value
    return WeeklyNewsPeriodBucket.previous_market_week.value


def _candidate_date_in_window(
    candidate: WeeklyNewsEventCandidateRow,
    window: WeeklyNewsMarketWeekWindowRow,
) -> bool:
    event_date = _candidate_event_date(candidate)
    return date.fromisoformat(window.news_window_start) <= event_date <= date.fromisoformat(window.news_window_end)


def _candidate_event_date(candidate: WeeklyNewsEventCandidateRow) -> date:
    value = candidate.event_date or (candidate.published_at or "")[:10]
    return date.fromisoformat(value)


def _source_quality_weight(candidate: WeeklyNewsEventCandidateRow) -> int:
    if candidate.source_quality in {SourceQuality.official.value, SourceQuality.issuer.value}:
        return 5
    if candidate.source_quality in {SourceQuality.allowlisted.value, SourceQuality.fixture.value}:
        return 3
    if candidate.source_quality == SourceQuality.provider.value:
        return 1
    return 0


def _event_type_weight(event_type: str) -> int:
    return {
        WeeklyNewsEventType.earnings.value: 5,
        WeeklyNewsEventType.guidance.value: 5,
        WeeklyNewsEventType.fee_change.value: 5,
        WeeklyNewsEventType.methodology_change.value: 5,
        WeeklyNewsEventType.index_change.value: 4,
        WeeklyNewsEventType.fund_merger.value: 4,
        WeeklyNewsEventType.fund_liquidation.value: 4,
        WeeklyNewsEventType.sponsor_update.value: 3,
        WeeklyNewsEventType.product_announcement.value: 3,
        WeeklyNewsEventType.regulatory_event.value: 3,
        WeeklyNewsEventType.legal_event.value: 3,
        WeeklyNewsEventType.capital_allocation.value: 3,
        WeeklyNewsEventType.large_flow_event.value: 2,
        WeeklyNewsEventType.merger_acquisition.value: 2,
        WeeklyNewsEventType.leadership_change.value: 2,
        WeeklyNewsEventType.other.value: 1,
    }.get(event_type, 0)


def _recency_weight(candidate: WeeklyNewsEventCandidateRow, window: WeeklyNewsMarketWeekWindowRow) -> int:
    if not _candidate_date_in_window(candidate, window):
        return 0
    return 3 if _period_bucket_for_candidate(candidate, window) == WeeklyNewsPeriodBucket.current_week_to_date.value else 2


def _freshness_labeled_evidence_state(freshness_state: str, evidence_state: str) -> str:
    if freshness_state == FreshnessState.stale.value:
        return EvidenceState.stale.value
    if freshness_state == FreshnessState.unavailable.value:
        return EvidenceState.unavailable.value
    return evidence_state


def _canonical_event_key(candidate: WeeklyNewsEventCandidateRow) -> str:
    event_date = candidate.event_date or (candidate.published_at or "")[:10]
    evidence_key = candidate.title_checksum or candidate.evidence_checksum or candidate.candidate_event_id
    return f"{_normalize_ticker(candidate.asset_ticker)}:{candidate.event_type}:{event_date}:{evidence_key}"


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


def _persist_records(
    session: Any,
    *,
    collection: str,
    key: str,
    records: WeeklyNewsEventEvidenceRepositoryRecords,
    rows: list[StrictRow],
    commit_on_write: bool,
) -> None:
    if hasattr(session, "save_repository_record"):
        session.save_repository_record(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "save"):
        session.save(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "add_all"):
        session.add_all(rows)
    else:
        raise WeeklyNewsEventEvidenceContractError(
            "Injected Weekly News Focus session must expose save_repository_record(collection, key, records), save(...), or add_all(records)."
        )
    if commit_on_write and hasattr(session, "commit"):
        session.commit()


def _read_records(session: Any, collection: str, key: str) -> Any | None:
    if hasattr(session, "get_repository_record"):
        return session.get_repository_record(collection, key)
    if hasattr(session, "read_repository_record"):
        return session.read_repository_record(collection, key)
    if hasattr(session, "get"):
        return session.get(collection, key)
    return None
