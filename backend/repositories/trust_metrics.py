from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.models import (
    FreshnessState,
    TrustMetricAssetSupportState,
    TrustMetricEvent,
    TrustMetricEventType,
    TrustMetricKind,
    TrustMetricOutputKind,
    TrustMetricSafetyStatus,
    TrustMetricValidationStatus,
    TrustMetricWorkflowArea,
)
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow
from backend.trust_metrics import (
    FORBIDDEN_EVENT_FIELD_NAMES,
    get_trust_metric_event_catalog,
    summarize_trust_metric_events,
    validate_trust_metric_event,
)


TRUST_METRIC_EVENT_REPOSITORY_BOUNDARY = "trust-metric-event-repository-contract-v1"
TRUST_METRIC_EVENT_REPOSITORY_SCHEMA_VERSION = "trust-metric-event-repository-v1"
TRUST_METRIC_EVENT_REPOSITORY_TABLES = (
    "trust_metric_event_envelopes",
    "trust_metric_validation_statuses",
    "trust_metric_aggregate_counters",
    "trust_metric_latency_summaries",
    "trust_metric_state_snapshots",
    "trust_metric_diagnostics",
)

_BLOCKED_GENERATED_SUPPORT_STATES = {
    TrustMetricAssetSupportState.eligible_not_cached.value,
    TrustMetricAssetSupportState.recognized_unsupported.value,
    TrustMetricAssetSupportState.unknown.value,
    TrustMetricAssetSupportState.unavailable.value,
    "out_of_scope",
}
_BLOCKED_GENERATED_STATE_CODES = {
    "unsupported",
    "out_of_scope",
    "eligible_not_cached",
    "unknown",
    "unavailable",
    "validation_failed",
    "stale_without_label",
    "partial_without_label",
    "source_policy_blocked",
    "insufficient_evidence_without_label",
}
_ALLOWED_FRESHNESS_AND_EVIDENCE_STATES = {
    *(state.value for state in FreshnessState),
    "partial",
    "insufficient_evidence",
    "supported",
    "mixed",
    "stale",
}
_FORBIDDEN_METADATA_MARKERS = tuple(
    sorted(
        {
            *FORBIDDEN_EVENT_FIELD_NAMES,
            "authorization",
            "bearer ",
            "private key",
            "raw_prompt",
            "hidden_prompt",
            "reasoning_payload",
            "raw_article_text",
            "raw_provider_payload",
            "raw_source_text",
            "raw_user_text",
            "user_question",
            "submitted_question",
            "question_text",
            "raw_answer",
            "answer_text",
            "direct_answer",
            "why_it_matters",
            "chat_transcript",
            "transcript",
            "portfolio",
            "allocation",
            "position_size",
            "signed_url",
            "public_url",
            "source_url",
            "source_urls",
            "external_analytics_id",
            "ga_client_id",
            "amplitude_id",
            "segment_anonymous_id",
            "api" + "_key",
        }
    )
)


class TrustMetricEventRepositoryContractError(ValueError):
    """Raised when dormant trust-metric rows would violate product or privacy contracts."""


class TrustMetricAggregateKind(str, Enum):
    event_count = "event_count"
    rate = "rate"


class TrustMetricLatencyScope(str, Enum):
    event_type = "event_type"
    workflow_area = "workflow_area"
    all_accepted_events = "all_accepted_events"


class TrustMetricDiagnosticCategory(str, Enum):
    validation = "validation"
    freshness = "freshness"
    safety = "safety"
    source_policy = "source_policy"
    generated_output_state = "generated_output_state"
    privacy = "privacy"


class TrustMetricEventEnvelopeRow(StrictRow):
    event_id: str
    batch_id: str
    schema_version: str = TRUST_METRIC_EVENT_REPOSITORY_SCHEMA_VERSION
    event_schema_version: str
    event_type: str
    workflow_area: str
    metric_kind: str
    occurred_at: str
    client_event_id: str | None = None
    asset_ticker: str | None = None
    asset_support_state: str | None = None
    comparison_left_ticker: str | None = None
    comparison_right_ticker: str | None = None
    generated_output_available: bool = False
    output_kind: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    citation_count: int = 0
    source_document_count: int = 0
    unsupported_claim_count: int = 0
    weak_citation_count: int = 0
    stale_source_count: int = 0
    latency_ms: int | None = None
    citation_coverage_rate: float | None = None
    freshness_state: str | None = None
    evidence_state: str | None = None
    safety_status: str | None = None
    sanitized_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    validation_only: bool = True
    persistence_enabled: bool = False
    external_analytics_enabled: bool = False
    analytics_emitted: bool = False
    no_live_external_calls: bool = True
    live_database_execution: bool = False
    provider_or_llm_call_required: bool = False
    user_identity_stored: bool = False
    stores_raw_user_text: bool = False
    stores_raw_answer_text: bool = False
    stores_raw_query_text: bool = False
    stores_raw_source_text: bool = False
    stores_source_url: bool = False
    stores_raw_provider_payload: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_secret: bool = False

    @field_validator("event_type")
    @classmethod
    def _valid_event_type(cls, value: str) -> str:
        TrustMetricEventType(value)
        return value

    @field_validator("workflow_area")
    @classmethod
    def _valid_workflow_area(cls, value: str) -> str:
        TrustMetricWorkflowArea(value)
        return value

    @field_validator("metric_kind")
    @classmethod
    def _valid_metric_kind(cls, value: str) -> str:
        TrustMetricKind(value)
        return value

    @field_validator("output_kind")
    @classmethod
    def _valid_output_kind(cls, value: str | None) -> str | None:
        if value is not None:
            TrustMetricOutputKind(value)
        return value

    @field_validator("safety_status")
    @classmethod
    def _valid_safety_status(cls, value: str | None) -> str | None:
        if value is not None:
            TrustMetricSafetyStatus(value)
        return value


class TrustMetricValidationStatusRow(StrictRow):
    event_id: str
    batch_id: str
    validation_status: str = TrustMetricValidationStatus.accepted.value
    schema_valid: bool = True
    catalog_valid: bool = True
    citation_validation_status: str = "ids_only"
    source_use_status: str = "ids_only"
    freshness_status: str = "labeled_or_not_required"
    safety_status: str = TrustMetricSafetyStatus.educational.value
    generated_output_state: str = "metadata_only"
    rejection_reason_codes: list[str] = Field(default_factory=list)
    validated_at: str

    @field_validator("validation_status")
    @classmethod
    def _valid_validation_status(cls, value: str) -> str:
        TrustMetricValidationStatus(value)
        return value


class TrustMetricAggregateCounterRow(StrictRow):
    aggregate_id: str
    batch_id: str
    aggregate_kind: str
    event_type: str | None = None
    workflow_area: str | None = None
    metric_kind: str | None = None
    count: int = 0
    numerator: int | None = None
    denominator: int | None = None
    rate: float | None = None
    created_at: str
    stores_raw_event_payload: bool = False
    stores_raw_user_text: bool = False

    @field_validator("aggregate_kind")
    @classmethod
    def _valid_aggregate_kind(cls, value: str) -> str:
        TrustMetricAggregateKind(value)
        return value


class TrustMetricLatencySummaryRow(StrictRow):
    summary_id: str
    batch_id: str
    latency_scope: str
    event_type: str | None = None
    workflow_area: str | None = None
    count: int
    min_ms: int | None = None
    max_ms: int | None = None
    average_ms: float | None = None
    created_at: str
    stores_raw_event_payload: bool = False
    stores_raw_user_text: bool = False

    @field_validator("latency_scope")
    @classmethod
    def _valid_latency_scope(cls, value: str) -> str:
        TrustMetricLatencyScope(value)
        return value


class TrustMetricStateSnapshotRow(StrictRow):
    event_id: str
    batch_id: str
    asset_support_state: str | None = None
    generated_output_available: bool = False
    output_kind: str | None = None
    freshness_state: str | None = None
    evidence_state: str | None = None
    safety_status: str | None = None
    citation_coverage_status: str = "not_applicable"
    source_use_status: str = "ids_only"
    state_consistency_status: str = "passed"
    blocked_reason_codes: list[str] = Field(default_factory=list)
    created_at: str


class TrustMetricDiagnosticRow(StrictRow):
    diagnostic_id: str
    batch_id: str
    event_id: str | None = None
    category: str
    code: str
    event_type: str | None = None
    workflow_area: str | None = None
    freshness_states: dict[str, str] = Field(default_factory=dict)
    compact_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: str
    stores_secret: bool = False
    stores_user_text: bool = False
    stores_answer_text: bool = False
    stores_query_text: bool = False
    stores_provider_payload: bool = False
    stores_raw_source_text: bool = False
    stores_source_url: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False

    @field_validator("category")
    @classmethod
    def _valid_category(cls, value: str) -> str:
        TrustMetricDiagnosticCategory(value)
        return value


class TrustMetricRepositoryRecords(StrictRow):
    events: list[TrustMetricEventEnvelopeRow] = Field(default_factory=list)
    validation_statuses: list[TrustMetricValidationStatusRow] = Field(default_factory=list)
    aggregate_counters: list[TrustMetricAggregateCounterRow] = Field(default_factory=list)
    latency_summaries: list[TrustMetricLatencySummaryRow] = Field(default_factory=list)
    state_snapshots: list[TrustMetricStateSnapshotRow] = Field(default_factory=list)
    diagnostics: list[TrustMetricDiagnosticRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return TRUST_METRIC_EVENT_REPOSITORY_TABLES


def trust_metric_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=TRUST_METRIC_EVENT_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="trust_metric_event_envelopes",
                primary_key=("event_id",),
                columns=tuple(TrustMetricEventEnvelopeRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="trust_metric_validation_statuses",
                primary_key=("event_id",),
                columns=tuple(TrustMetricValidationStatusRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="trust_metric_aggregate_counters",
                primary_key=("aggregate_id",),
                columns=tuple(TrustMetricAggregateCounterRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="trust_metric_latency_summaries",
                primary_key=("summary_id",),
                columns=tuple(TrustMetricLatencySummaryRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="trust_metric_state_snapshots",
                primary_key=("event_id",),
                columns=tuple(TrustMetricStateSnapshotRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="trust_metric_diagnostics",
                primary_key=("diagnostic_id",),
                columns=tuple(TrustMetricDiagnosticRow.model_fields),
            ),
        ),
    )


@dataclass
class TrustMetricRepository:
    session: Any | None = None

    def validate(self, records: TrustMetricRepositoryRecords) -> TrustMetricRepositoryRecords:
        return validate_trust_metric_repository_records(records)

    def persist(self, records: TrustMetricRepositoryRecords) -> TrustMetricRepositoryRecords:
        validated = validate_trust_metric_repository_records(records)
        if self.session is None:
            return validated
        if not hasattr(self.session, "add_all"):
            raise TrustMetricEventRepositoryContractError("Injected trust-metric session must expose add_all(records).")
        self.session.add_all(records_to_row_list(validated))
        return validated


def build_trust_metric_repository_records(
    events: list[TrustMetricEvent],
    *,
    batch_id: str,
    created_at: str,
) -> TrustMetricRepositoryRecords:
    catalog_by_type = _catalog_by_event_type()
    summary = summarize_trust_metric_events(events)
    rows: list[TrustMetricEventEnvelopeRow] = []
    validation_rows: list[TrustMetricValidationStatusRow] = []
    state_rows: list[TrustMetricStateSnapshotRow] = []

    for index, event in enumerate(events, start=1):
        event_id = event.client_event_id or f"{batch_id}:event:{index}"
        catalog_event = catalog_by_type[event.event_type]
        row = _event_row(event, event_id, batch_id, catalog_event.metric_kind.value)
        rows.append(row)
        validation_rows.append(_validation_row(row, batch_id, created_at))
        state_rows.append(_state_row(row, batch_id, created_at))

    records = TrustMetricRepositoryRecords(
        events=rows,
        validation_statuses=validation_rows,
        aggregate_counters=_aggregate_rows(summary, batch_id, created_at),
        latency_summaries=_latency_rows(summary, batch_id, created_at),
        state_snapshots=state_rows,
    )
    return validate_trust_metric_repository_records(records)


def build_trust_metric_repository_records_from_payloads(
    payloads: list[dict[str, Any]],
    *,
    batch_id: str,
    created_at: str,
) -> TrustMetricRepositoryRecords:
    validated = [validate_trust_metric_event(payload) for payload in payloads]
    rejected = [item for item in validated if item.validation_status is not TrustMetricValidationStatus.accepted]
    if rejected:
        raise TrustMetricEventRepositoryContractError("Trust-metric repository rows require pre-validated accepted compact events.")
    return build_trust_metric_repository_records(
        [item.normalized_event for item in validated if item.normalized_event is not None],
        batch_id=batch_id,
        created_at=created_at,
    )


def validate_trust_metric_repository_records(records: TrustMetricRepositoryRecords) -> TrustMetricRepositoryRecords:
    event_ids = _unique("trust-metric event IDs", [row.event_id for row in records.events])
    _unique("trust-metric aggregate IDs", [row.aggregate_id for row in records.aggregate_counters])
    _unique("trust-metric latency summary IDs", [row.summary_id for row in records.latency_summaries])
    _unique("trust-metric diagnostic IDs", [row.diagnostic_id for row in records.diagnostics])

    validation_event_ids = _unique("trust-metric validation event IDs", [row.event_id for row in records.validation_statuses])
    state_event_ids = _unique("trust-metric state event IDs", [row.event_id for row in records.state_snapshots])
    if validation_event_ids != event_ids:
        raise TrustMetricEventRepositoryContractError("Trust-metric validation rows must match accepted event envelopes.")
    if state_event_ids != event_ids:
        raise TrustMetricEventRepositoryContractError("Trust-metric state rows must match accepted event envelopes.")

    events_by_id = {row.event_id: row for row in records.events}
    for event in records.events:
        _validate_event_row(event)
    for validation in records.validation_statuses:
        _validate_validation_row(validation, events_by_id[validation.event_id])
    for state in records.state_snapshots:
        _validate_state_row(state, events_by_id[state.event_id])
    for aggregate in records.aggregate_counters:
        _validate_aggregate_row(aggregate)
    for latency in records.latency_summaries:
        _validate_latency_row(latency)
    for diagnostic in records.diagnostics:
        if diagnostic.event_id and diagnostic.event_id not in event_ids:
            raise TrustMetricEventRepositoryContractError("Trust-metric diagnostics must reference accepted event envelopes.")
        _validate_diagnostic_row(diagnostic)
    return records


def records_to_row_list(records: TrustMetricRepositoryRecords) -> list[StrictRow]:
    return [
        *records.events,
        *records.validation_statuses,
        *records.aggregate_counters,
        *records.latency_summaries,
        *records.state_snapshots,
        *records.diagnostics,
    ]


def _event_row(
    event: TrustMetricEvent,
    event_id: str,
    batch_id: str,
    metric_kind: str,
) -> TrustMetricEventEnvelopeRow:
    output = event.output_metadata
    metadata = _sanitized_metadata(event.metadata)
    return TrustMetricEventEnvelopeRow(
        event_id=event_id,
        batch_id=batch_id,
        event_schema_version=event.schema_version,
        event_type=event.event_type.value,
        workflow_area=event.workflow_area.value,
        metric_kind=metric_kind,
        occurred_at=event.occurred_at,
        client_event_id=event.client_event_id,
        asset_ticker=event.asset_ticker,
        asset_support_state=event.asset_support_state.value if event.asset_support_state else None,
        comparison_left_ticker=event.comparison_left_ticker,
        comparison_right_ticker=event.comparison_right_ticker,
        generated_output_available=event.generated_output_available,
        output_kind=output.output_kind.value if output else _optional_metadata_text(metadata, "output_kind"),
        citation_ids=list(output.citation_ids) if output else [],
        source_document_ids=list(output.source_document_ids) if output else [],
        citation_count=int(metadata.get("citation_count") or len(output.citation_ids) if output else metadata.get("citation_count") or 0),
        source_document_count=int(
            metadata.get("source_document_count") or len(output.source_document_ids) if output else metadata.get("source_document_count") or 0
        ),
        unsupported_claim_count=int(output.unsupported_claim_count if output else metadata.get("unsupported_claim_count") or 0),
        weak_citation_count=int(output.weak_citation_count if output else metadata.get("weak_citation_count") or 0),
        stale_source_count=int(output.stale_source_count if output else metadata.get("stale_source_count") or 0),
        latency_ms=output.latency_ms if output and output.latency_ms is not None else _optional_metadata_int(metadata, "latency_ms"),
        citation_coverage_rate=(
            output.citation_coverage_rate
            if output and output.citation_coverage_rate is not None
            else _optional_metadata_float(metadata, "citation_coverage_rate")
        ),
        freshness_state=(
            output.freshness_state.value
            if output and output.freshness_state
            else _optional_metadata_text(metadata, "freshness_state")
        ),
        evidence_state=_optional_metadata_text(metadata, "evidence_state"),
        safety_status=(
            output.safety_status.value
            if output and output.safety_status
            else _optional_metadata_text(metadata, "safety_classification")
        ),
        sanitized_metadata=metadata,
    )


def _validation_row(row: TrustMetricEventEnvelopeRow, batch_id: str, created_at: str) -> TrustMetricValidationStatusRow:
    safety_status = row.safety_status or TrustMetricSafetyStatus.educational.value
    return TrustMetricValidationStatusRow(
        event_id=row.event_id,
        batch_id=batch_id,
        safety_status=safety_status,
        generated_output_state="available_metadata" if row.generated_output_available else "not_available",
        freshness_status="labeled" if row.freshness_state else "not_required",
        validated_at=created_at,
    )


def _state_row(row: TrustMetricEventEnvelopeRow, batch_id: str, created_at: str) -> TrustMetricStateSnapshotRow:
    blocked_reasons = _state_blocked_reasons(row)
    return TrustMetricStateSnapshotRow(
        event_id=row.event_id,
        batch_id=batch_id,
        asset_support_state=row.asset_support_state,
        generated_output_available=row.generated_output_available,
        output_kind=row.output_kind,
        freshness_state=row.freshness_state,
        evidence_state=row.evidence_state,
        safety_status=row.safety_status,
        citation_coverage_status="tracked" if row.citation_coverage_rate is not None else "not_applicable",
        state_consistency_status="blocked" if blocked_reasons else "passed",
        blocked_reason_codes=blocked_reasons,
        created_at=created_at,
    )


def _aggregate_rows(summary: Any, batch_id: str, created_at: str) -> list[TrustMetricAggregateCounterRow]:
    rows: list[TrustMetricAggregateCounterRow] = []
    for event_type, count in summary.event_type_counts.items():
        rows.append(
            TrustMetricAggregateCounterRow(
                aggregate_id=f"{batch_id}:event_type:{event_type}",
                batch_id=batch_id,
                aggregate_kind=TrustMetricAggregateKind.event_count.value,
                event_type=event_type,
                count=count,
                created_at=created_at,
            )
        )
    for workflow_area, count in summary.workflow_area_counts.items():
        rows.append(
            TrustMetricAggregateCounterRow(
                aggregate_id=f"{batch_id}:workflow_area:{workflow_area}",
                batch_id=batch_id,
                aggregate_kind=TrustMetricAggregateKind.event_count.value,
                workflow_area=workflow_area,
                count=count,
                created_at=created_at,
            )
        )
    for rate_name, rate in summary.rates.items():
        rows.append(
            TrustMetricAggregateCounterRow(
                aggregate_id=f"{batch_id}:rate:{rate_name}",
                batch_id=batch_id,
                aggregate_kind=TrustMetricAggregateKind.rate.value,
                count=0,
                numerator=None,
                denominator=summary.accepted_event_count,
                rate=rate,
                created_at=created_at,
            )
        )
    return rows


def _latency_rows(summary: Any, batch_id: str, created_at: str) -> list[TrustMetricLatencySummaryRow]:
    latency = summary.latency_ms
    return [
        TrustMetricLatencySummaryRow(
            summary_id=f"{batch_id}:latency:all",
            batch_id=batch_id,
            latency_scope=TrustMetricLatencyScope.all_accepted_events.value,
            count=int(latency.get("count") or 0),
            min_ms=latency.get("min"),
            max_ms=latency.get("max"),
            average_ms=latency.get("average"),
            created_at=created_at,
        )
    ]


def _validate_event_row(row: TrustMetricEventEnvelopeRow) -> None:
    _validate_no_live_raw_or_identity_surface(row)
    _validate_compact_metadata(row.sanitized_metadata)
    _validate_ids(row.citation_ids, "citation IDs")
    _validate_ids(row.source_document_ids, "source document IDs")
    if row.generated_output_available and row.asset_support_state in _BLOCKED_GENERATED_SUPPORT_STATES:
        raise TrustMetricEventRepositoryContractError("Trust-metric rows cannot imply generated output for blocked support states.")
    if row.latency_ms is not None and row.latency_ms < 0:
        raise TrustMetricEventRepositoryContractError("Trust-metric latency metadata cannot be negative.")
    for label, value in [
        ("citation count", row.citation_count),
        ("source document count", row.source_document_count),
        ("unsupported claim count", row.unsupported_claim_count),
        ("weak citation count", row.weak_citation_count),
        ("stale source count", row.stale_source_count),
    ]:
        if value < 0:
            raise TrustMetricEventRepositoryContractError(f"Trust-metric {label} cannot be negative.")
    if row.citation_coverage_rate is not None and not 0 <= row.citation_coverage_rate <= 1:
        raise TrustMetricEventRepositoryContractError("Trust-metric citation coverage rate must be between 0 and 1.")
    if row.citation_ids and not row.generated_output_available:
        raise TrustMetricEventRepositoryContractError("Citation IDs are valid only for available generated-output metadata.")
    if row.source_document_ids and not row.generated_output_available:
        raise TrustMetricEventRepositoryContractError("Source document IDs are valid only for available generated-output metadata.")
    if row.freshness_state and row.freshness_state not in _ALLOWED_FRESHNESS_AND_EVIDENCE_STATES:
        raise TrustMetricEventRepositoryContractError("Freshness metadata must use explicit allowed states.")
    if row.evidence_state and row.evidence_state not in _ALLOWED_FRESHNESS_AND_EVIDENCE_STATES:
        raise TrustMetricEventRepositoryContractError("Evidence metadata must use explicit allowed states.")


def _validate_validation_row(
    validation: TrustMetricValidationStatusRow,
    event: TrustMetricEventEnvelopeRow,
) -> None:
    if validation.batch_id != event.batch_id:
        raise TrustMetricEventRepositoryContractError("Trust-metric validation rows must preserve batch identity.")
    if validation.validation_status != TrustMetricValidationStatus.accepted.value:
        raise TrustMetricEventRepositoryContractError("Repository rows are accepted-event metadata only.")
    if validation.rejection_reason_codes:
        raise TrustMetricEventRepositoryContractError("Rejected trust-metric events are not persisted as accepted rows.")
    blocked_statuses = {
        "failed",
        "validation_failed",
        "source_policy_blocked",
        "rejected",
        "rejected_source",
        "unlabeled_stale",
        "unlabeled_partial",
    }
    for status in (
        validation.citation_validation_status,
        validation.source_use_status,
        validation.freshness_status,
        validation.generated_output_state,
    ):
        if status in blocked_statuses:
            raise TrustMetricEventRepositoryContractError("Trust-metric validation metadata must not preserve blocked states as accepted rows.")
    if validation.safety_status not in {status.value for status in TrustMetricSafetyStatus}:
        raise TrustMetricEventRepositoryContractError("Trust-metric safety status must use the compact catalog values.")


def _validate_state_row(state: TrustMetricStateSnapshotRow, event: TrustMetricEventEnvelopeRow) -> None:
    if state.batch_id != event.batch_id:
        raise TrustMetricEventRepositoryContractError("Trust-metric state rows must preserve batch identity.")
    if state.generated_output_available != event.generated_output_available:
        raise TrustMetricEventRepositoryContractError("Trust-metric state rows must match generated-output availability.")
    if state.asset_support_state != event.asset_support_state:
        raise TrustMetricEventRepositoryContractError("Trust-metric state rows must match support state.")
    blocked = _state_blocked_reasons(event)
    if blocked:
        raise TrustMetricEventRepositoryContractError(
            "Trust-metric rows must not imply generated output for unsupported, stale, partial, or insufficient-evidence states."
        )
    if state.blocked_reason_codes:
        raise TrustMetricEventRepositoryContractError("Accepted trust-metric state rows cannot carry blocked reason codes.")


def _validate_aggregate_row(row: TrustMetricAggregateCounterRow) -> None:
    if row.count < 0:
        raise TrustMetricEventRepositoryContractError("Trust-metric aggregate counts cannot be negative.")
    if row.rate is not None and not 0 <= row.rate <= 1:
        raise TrustMetricEventRepositoryContractError("Trust-metric aggregate rates must be between 0 and 1.")
    if row.denominator is not None and row.denominator < 0:
        raise TrustMetricEventRepositoryContractError("Trust-metric aggregate denominators cannot be negative.")
    if row.stores_raw_event_payload or row.stores_raw_user_text:
        raise TrustMetricEventRepositoryContractError("Trust-metric aggregate rows must store counters only.")


def _validate_latency_row(row: TrustMetricLatencySummaryRow) -> None:
    if row.count < 0:
        raise TrustMetricEventRepositoryContractError("Trust-metric latency counts cannot be negative.")
    values = [value for value in [row.min_ms, row.max_ms, row.average_ms] if value is not None]
    if any(value < 0 for value in values):
        raise TrustMetricEventRepositoryContractError("Trust-metric latency summaries cannot be negative.")
    if row.min_ms is not None and row.max_ms is not None and row.min_ms > row.max_ms:
        raise TrustMetricEventRepositoryContractError("Trust-metric latency summaries must preserve min/max order.")
    if row.stores_raw_event_payload or row.stores_raw_user_text:
        raise TrustMetricEventRepositoryContractError("Trust-metric latency rows must store compact summaries only.")


def _validate_diagnostic_row(row: TrustMetricDiagnosticRow) -> None:
    _validate_compact_metadata(row.compact_metadata)
    for state in row.freshness_states.values():
        if state not in _ALLOWED_FRESHNESS_AND_EVIDENCE_STATES:
            raise TrustMetricEventRepositoryContractError("Trust-metric diagnostics must use explicit freshness/evidence states.")
    if (
        row.stores_secret
        or row.stores_user_text
        or row.stores_answer_text
        or row.stores_query_text
        or row.stores_provider_payload
        or row.stores_raw_source_text
        or row.stores_source_url
        or row.stores_hidden_prompt
        or row.stores_raw_model_reasoning
    ):
        raise TrustMetricEventRepositoryContractError("Trust-metric diagnostics must be compact and sanitized.")


def _validate_no_live_raw_or_identity_surface(row: TrustMetricEventEnvelopeRow) -> None:
    if (
        not row.validation_only
        or row.persistence_enabled
        or row.external_analytics_enabled
        or row.analytics_emitted
        or not row.no_live_external_calls
        or row.live_database_execution
        or row.provider_or_llm_call_required
    ):
        raise TrustMetricEventRepositoryContractError("Trust-metric event repository contracts must stay dormant.")
    if (
        row.user_identity_stored
        or row.stores_raw_user_text
        or row.stores_raw_answer_text
        or row.stores_raw_query_text
        or row.stores_raw_source_text
        or row.stores_source_url
        or row.stores_raw_provider_payload
        or row.stores_hidden_prompt
        or row.stores_raw_model_reasoning
        or row.stores_secret
    ):
        raise TrustMetricEventRepositoryContractError("Trust-metric event rows may store compact metadata only.")


def _state_blocked_reasons(row: TrustMetricEventEnvelopeRow) -> list[str]:
    reasons: list[str] = []
    if row.generated_output_available and row.asset_support_state in _BLOCKED_GENERATED_SUPPORT_STATES:
        reasons.append("blocked_support_state")
    metadata_values = {str(value) for value in row.sanitized_metadata.values() if value is not None}
    for code in _BLOCKED_GENERATED_STATE_CODES:
        if code in metadata_values:
            reasons.append(code)
    if row.freshness_state == FreshnessState.stale.value and row.sanitized_metadata.get("freshness_labeled") is False:
        reasons.append("stale_without_label")
    if row.evidence_state == "partial" and row.sanitized_metadata.get("uncertainty_labeled") is False:
        reasons.append("partial_without_label")
    if row.evidence_state == "insufficient_evidence" and row.sanitized_metadata.get("uncertainty_labeled") is False:
        reasons.append("insufficient_evidence_without_label")
    return sorted(set(reasons))


def _sanitized_metadata(metadata: dict[str, str | int | float | bool | None]) -> dict[str, str | int | float | bool | None]:
    sanitized = dict(metadata)
    _validate_compact_metadata(sanitized)
    return sanitized


def _validate_compact_metadata(metadata: dict[str, Any]) -> None:
    text = repr(metadata).lower()
    if "http://" in text or "https://" in text:
        raise TrustMetricEventRepositoryContractError("Trust-metric metadata must not contain source URLs.")
    if any(marker in text for marker in _FORBIDDEN_METADATA_MARKERS):
        raise TrustMetricEventRepositoryContractError("Trust-metric metadata must be compact and sanitized.")
    if "source_use_policy': 'rejected" in text or 'source_use_policy": "rejected' in text:
        raise TrustMetricEventRepositoryContractError("Rejected or license-disallowed source policy cannot support trust-metric rows.")
    if "source_policy_blocked" in text or "license_disallowed" in text:
        raise TrustMetricEventRepositoryContractError("Source-policy-blocked evidence cannot support trust-metric rows.")


def _validate_ids(values: list[str], label: str) -> None:
    for value in values:
        lowered = value.lower()
        if "http://" in lowered or "https://" in lowered or "signed_url" in lowered or "public_url" in lowered:
            raise TrustMetricEventRepositoryContractError(f"Trust-metric {label} must remain IDs only.")


def _optional_metadata_text(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) else None


def _optional_metadata_int(metadata: dict[str, Any], key: str) -> int | None:
    value = metadata.get(key)
    return int(value) if isinstance(value, int) else None


def _optional_metadata_float(metadata: dict[str, Any], key: str) -> float | None:
    value = metadata.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _catalog_by_event_type() -> dict[TrustMetricEventType, Any]:
    catalog = get_trust_metric_event_catalog()
    return {event.event_type: event for event in [*catalog.product_events, *catalog.trust_events]}


def _unique(label: str, values: list[str]) -> set[str]:
    seen = set(values)
    if len(seen) != len(values):
        raise TrustMetricEventRepositoryContractError(f"{label} must be unique.")
    return seen
