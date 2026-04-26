from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from backend.data import STUB_TIMESTAMP
from backend.repositories.ingestion_jobs import (
    IngestionJobLedgerDiagnosticRow,
    IngestionJobLedgerRecords,
    IngestionLedgerJobState,
    SanitizedErrorCategory,
    validate_ingestion_job_ledger_records,
)
from backend.source_snapshot_repository import SourceSnapshotRepositoryRecords


INGESTION_WORKER_EXECUTION_BOUNDARY = "deterministic-ingestion-worker-execution-contract-v1"
_TERMINAL_STATES = {
    IngestionLedgerJobState.succeeded.value,
    IngestionLedgerJobState.failed.value,
    IngestionLedgerJobState.unsupported.value,
    IngestionLedgerJobState.out_of_scope.value,
    IngestionLedgerJobState.unknown.value,
    IngestionLedgerJobState.unavailable.value,
    IngestionLedgerJobState.stale.value,
}
_BLOCKED_OUTPUT_STATES = {
    IngestionLedgerJobState.failed.value,
    IngestionLedgerJobState.unsupported.value,
    IngestionLedgerJobState.out_of_scope.value,
    IngestionLedgerJobState.unknown.value,
    IngestionLedgerJobState.unavailable.value,
}
_BLOCKED_SCOPE_DECISIONS = {
    "blocked_unsupported_asset",
    "blocked_out_of_scope_asset",
    "unknown_or_unavailable_asset",
}
_SENSITIVE_MESSAGE_MARKERS = ("secret", "password", "token", "provider payload", "raw text")


class IngestionWorkerContractError(ValueError):
    """Raised when the deterministic worker boundary is used outside its dormant contract."""


class IngestionWorkerLedgerBoundary(Protocol):
    def get(self, job_id: str) -> IngestionJobLedgerRecords | None:
        ...

    def save(self, records: IngestionJobLedgerRecords) -> None:
        ...


class SourceSnapshotWriterBoundary(Protocol):
    def persist(self, records: SourceSnapshotRepositoryRecords) -> SourceSnapshotRepositoryRecords:
        ...


class IngestionWorkerFixtureOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    terminal_state: IngestionLedgerJobState
    error_category: SanitizedErrorCategory | None = None
    error_code: str | None = None
    sanitized_message: str | None = None
    retryable: bool = False
    source_policy_ref: str | None = None
    checksum: str | None = None
    source_snapshot_records: SourceSnapshotRepositoryRecords | None = None

    @field_validator("terminal_state")
    @classmethod
    def _terminal_state_only(cls, value: IngestionLedgerJobState) -> IngestionLedgerJobState:
        if value.value not in _TERMINAL_STATES:
            raise ValueError("fixture outcome must be a deterministic terminal state")
        return value


class IngestionWorkerExecutionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    boundary: str = INGESTION_WORKER_EXECUTION_BOUNDARY
    job_id: str
    ticker: str
    job_category: str
    initial_state: str
    terminal_state: str
    transitions: list[str]
    retryable: bool
    generated_output_available: bool
    generated_output_cacheable: bool
    blocked_from_generated_outputs: bool
    diagnostics_count: int
    no_live_external_calls: bool = True
    opened_database_connection: bool = False
    called_live_provider: bool = False


@dataclass
class IngestionWorkerExecutionResult:
    summary: IngestionWorkerExecutionSummary
    records: IngestionJobLedgerRecords


@dataclass
class InMemoryIngestionWorkerLedger:
    records_by_job_id: dict[str, IngestionJobLedgerRecords] = field(default_factory=dict)

    @classmethod
    def from_records(cls, records: list[IngestionJobLedgerRecords]) -> InMemoryIngestionWorkerLedger:
        ledger = cls()
        for record in records:
            ledger.save(record)
        return ledger

    def get(self, job_id: str) -> IngestionJobLedgerRecords | None:
        records = self.records_by_job_id.get(job_id)
        return records.model_copy(deep=True) if records else None

    def save(self, records: IngestionJobLedgerRecords) -> None:
        validate_ingestion_job_ledger_records(records)
        self.records_by_job_id[records.ledger.job_id] = records.model_copy(deep=True)


@dataclass
class DeterministicIngestionWorker:
    ledger_boundary: IngestionWorkerLedgerBoundary
    fixture_outcomes: Mapping[str, IngestionWorkerFixtureOutcome] = field(default_factory=dict)
    source_snapshot_repository: SourceSnapshotWriterBoundary | None = None
    timestamp: str = STUB_TIMESTAMP

    def execute(self, job_id: str) -> IngestionWorkerExecutionResult:
        records = self.ledger_boundary.get(job_id)
        if records is None:
            raise IngestionWorkerContractError("Injected in-memory ingestion ledger has no record for job_id.")
        outcome = self.fixture_outcomes.get(job_id)
        result = execute_ingestion_worker_record(records, fixture_outcome=outcome, timestamp=self.timestamp)
        if _should_persist_source_snapshots(result, outcome, self.source_snapshot_repository):
            snapshot_repository = self.source_snapshot_repository
            snapshot_records = outcome.source_snapshot_records if outcome else None
            if snapshot_repository is None or snapshot_records is None:
                raise IngestionWorkerContractError("Source snapshot persistence was requested without a mocked writer.")
            try:
                snapshot_repository.persist(snapshot_records)
            except Exception:
                failed_outcome = IngestionWorkerFixtureOutcome(
                    terminal_state=IngestionLedgerJobState.failed,
                    error_category=SanitizedErrorCategory.validation_failed,
                    error_code="source_snapshot_persistence_failed",
                    sanitized_message="Source snapshot persistence failed closed through the configured mocked writer.",
                    retryable=True,
                    source_policy_ref=outcome.source_policy_ref,
                    checksum=outcome.checksum,
                )
                result = execute_ingestion_worker_record(records, fixture_outcome=failed_outcome, timestamp=self.timestamp)
        self.ledger_boundary.save(result.records)
        return result


def execute_ingestion_worker_record(
    records: IngestionJobLedgerRecords,
    *,
    fixture_outcome: IngestionWorkerFixtureOutcome | None = None,
    timestamp: str = STUB_TIMESTAMP,
) -> IngestionWorkerExecutionResult:
    validate_ingestion_job_ledger_records(records)

    initial_state = records.ledger.job_state
    if initial_state in _TERMINAL_STATES:
        return _result(records, initial_state=initial_state, transitions=[initial_state])

    outcome = fixture_outcome or _default_fixture_outcome(records)
    transitions = _transitions(initial_state, outcome.terminal_state.value)
    updated = _apply_terminal_outcome(records, outcome, timestamp=timestamp)
    validate_ingestion_job_ledger_records(updated)
    return _result(updated, initial_state=initial_state, transitions=transitions)


def _default_fixture_outcome(records: IngestionJobLedgerRecords) -> IngestionWorkerFixtureOutcome:
    scope_decision = records.scope.scope_decision
    if scope_decision == "blocked_unsupported_asset":
        return IngestionWorkerFixtureOutcome(terminal_state=IngestionLedgerJobState.unsupported)
    if scope_decision == "blocked_out_of_scope_asset":
        return IngestionWorkerFixtureOutcome(terminal_state=IngestionLedgerJobState.out_of_scope)
    if scope_decision == "unknown_or_unavailable_asset":
        return IngestionWorkerFixtureOutcome(terminal_state=IngestionLedgerJobState.unknown)
    if records.ledger.job_category in {"refresh", "source_revalidation"}:
        return IngestionWorkerFixtureOutcome(
            terminal_state=IngestionLedgerJobState.stale,
            error_category=SanitizedErrorCategory.source_unavailable,
            error_code="fixture_freshness_not_revalidated",
            sanitized_message="Fixture-only worker did not revalidate sources; freshness remains stale.",
            retryable=True,
        )
    return IngestionWorkerFixtureOutcome(terminal_state=IngestionLedgerJobState.succeeded)


def _apply_terminal_outcome(
    records: IngestionJobLedgerRecords,
    outcome: IngestionWorkerFixtureOutcome,
    *,
    timestamp: str,
) -> IngestionJobLedgerRecords:
    terminal_state = outcome.terminal_state.value
    generated_output_allowed = _generated_output_allowed(records, terminal_state)
    metadata = {
        **records.ledger.compact_metadata,
        "worker_execution_boundary": INGESTION_WORKER_EXECUTION_BOUNDARY,
        "terminal_state": terminal_state,
        "fixture_only": True,
    }
    if outcome.source_policy_ref:
        metadata["source_policy_ref"] = outcome.source_policy_ref
    if outcome.checksum:
        metadata["checksum"] = outcome.checksum
    if outcome.source_snapshot_records:
        metadata["source_snapshot_persistence_configured"] = True
        metadata["source_snapshot_artifact_count"] = len(outcome.source_snapshot_records.artifacts)
        metadata["source_snapshot_diagnostic_count"] = len(outcome.source_snapshot_records.diagnostics)
        metadata["source_snapshot_boundary"] = "source-snapshot-artifact-repository-contract-v1"

    ledger = records.ledger.model_copy(
        update={
            "job_state": terminal_state,
            "worker_status": _worker_status_for_terminal_state(terminal_state),
            "retryable": outcome.retryable,
            "generated_route": records.ledger.generated_route if generated_output_allowed else None,
            "generated_output_available": records.ledger.generated_output_available if generated_output_allowed else False,
            "can_open_generated_page": records.ledger.can_open_generated_page if generated_output_allowed else False,
            "can_answer_chat": records.ledger.can_answer_chat if generated_output_allowed else False,
            "can_compare": records.ledger.can_compare if generated_output_allowed else False,
            "can_request_ingestion": records.ledger.can_request_ingestion if terminal_state != "succeeded" else False,
            "updated_at": timestamp,
            "started_at": records.ledger.started_at or timestamp,
            "finished_at": timestamp,
            "compact_metadata": metadata,
        }
    )
    diagnostics = [*records.diagnostics]
    diagnostic = _diagnostic_for_outcome(ledger.job_id, outcome, timestamp=timestamp)
    if diagnostic:
        diagnostics.append(diagnostic)
    return IngestionJobLedgerRecords(
        ledger=ledger,
        scope=records.scope,
        source_refs=records.source_refs,
        diagnostics=diagnostics,
    )


def _diagnostic_for_outcome(
    job_id: str,
    outcome: IngestionWorkerFixtureOutcome,
    *,
    timestamp: str,
) -> IngestionJobLedgerDiagnosticRow | None:
    if outcome.error_category is None and outcome.terminal_state not in {
        IngestionLedgerJobState.failed,
        IngestionLedgerJobState.unavailable,
        IngestionLedgerJobState.stale,
    }:
        return None
    category = outcome.error_category or SanitizedErrorCategory.unknown
    return IngestionJobLedgerDiagnosticRow(
        job_id=job_id,
        diagnostic_id=f"{job_id}-worker-diagnostic-1",
        category=category.value,
        error_code=outcome.error_code or f"fixture_worker_{outcome.terminal_state.value}",
        sanitized_message=_sanitize_diagnostic_message(
            outcome.sanitized_message
            or "Deterministic fixture-only ingestion worker reached a non-generated terminal state."
        ),
        retryable=outcome.retryable,
        occurred_at=timestamp,
    )


def _generated_output_allowed(records: IngestionJobLedgerRecords, terminal_state: str) -> bool:
    if terminal_state in _BLOCKED_OUTPUT_STATES:
        return False
    if records.scope.scope_decision in _BLOCKED_SCOPE_DECISIONS:
        return False
    if records.scope.scope_decision == "approved_pending_ingestion":
        return False
    return records.scope.generated_output_allowed


def _worker_status_for_terminal_state(terminal_state: str) -> str | None:
    if terminal_state == "succeeded":
        return "succeeded"
    if terminal_state == "failed":
        return "failed"
    return None


def _transitions(initial_state: str, terminal_state: str) -> list[str]:
    if initial_state == "pending":
        return ["pending", "running", terminal_state]
    if initial_state == "running":
        return ["running", terminal_state]
    return [initial_state, terminal_state]


def _result(
    records: IngestionJobLedgerRecords,
    *,
    initial_state: str,
    transitions: list[str],
) -> IngestionWorkerExecutionResult:
    terminal_state = records.ledger.job_state
    blocked = (
        terminal_state in _BLOCKED_OUTPUT_STATES
        or records.scope.scope_decision in _BLOCKED_SCOPE_DECISIONS
        or (records.scope.scope_decision == "approved_pending_ingestion" and not records.ledger.generated_output_available)
    )
    summary = IngestionWorkerExecutionSummary(
        job_id=records.ledger.job_id,
        ticker=records.ledger.ticker,
        job_category=records.ledger.job_category,
        initial_state=initial_state,
        terminal_state=terminal_state,
        transitions=transitions,
        retryable=records.ledger.retryable,
        generated_output_available=records.ledger.generated_output_available,
        generated_output_cacheable=records.ledger.generated_output_available and terminal_state == "succeeded",
        blocked_from_generated_outputs=blocked,
        diagnostics_count=len(records.diagnostics),
    )
    return IngestionWorkerExecutionResult(summary=summary, records=records)


def _should_persist_source_snapshots(
    result: IngestionWorkerExecutionResult,
    outcome: IngestionWorkerFixtureOutcome | None,
    repository: SourceSnapshotWriterBoundary | None,
) -> bool:
    return (
        repository is not None
        and outcome is not None
        and outcome.source_snapshot_records is not None
        and result.summary.initial_state not in _TERMINAL_STATES
        and result.summary.terminal_state == IngestionLedgerJobState.succeeded.value
    )


def _sanitize_diagnostic_message(message: str) -> str:
    normalized = message.lower()
    if any(marker in normalized for marker in _SENSITIVE_MESSAGE_MARKERS):
        return "Sanitized deterministic ingestion worker diagnostic."
    return message[:240]
