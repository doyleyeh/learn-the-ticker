from __future__ import annotations

from pathlib import Path

from backend.ingestion import get_pre_cache_job_status, request_ingestion
from backend.ingestion_job_repository import (
    IngestionJobCategory,
    IngestionLedgerJobState,
    serialize_ingestion_job_response,
)
from backend.ingestion_worker import (
    DeterministicIngestionWorker,
    INGESTION_WORKER_EXECUTION_BOUNDARY,
    InMemoryIngestionWorkerLedger,
    IngestionWorkerFixtureOutcome,
    execute_ingestion_worker_record,
)
from backend.repositories.ingestion_jobs import SanitizedErrorCategory


ROOT = Path(__file__).resolve().parents[2]


def test_pending_approved_on_demand_job_transitions_without_generated_output():
    records = serialize_ingestion_job_response(request_ingestion("SPY"))
    result = execute_ingestion_worker_record(records)

    assert result.summary.boundary == INGESTION_WORKER_EXECUTION_BOUNDARY
    assert result.summary.job_id == "ingest-on-demand-spy"
    assert result.summary.transitions == ["pending", "running", "succeeded"]
    assert result.summary.terminal_state == "succeeded"
    assert result.summary.generated_output_available is False
    assert result.summary.generated_output_cacheable is False
    assert result.summary.blocked_from_generated_outputs is True
    assert result.records.ledger.can_open_generated_page is False
    assert result.records.ledger.can_answer_chat is False
    assert result.records.ledger.can_compare is False
    assert result.records.ledger.compact_metadata["fixture_only"] is True


def test_worker_uses_injected_in_memory_ledger_boundary_only():
    records = serialize_ingestion_job_response(request_ingestion("SPY"))
    boundary = InMemoryIngestionWorkerLedger.from_records([records])
    worker = DeterministicIngestionWorker(ledger_boundary=boundary)

    result = worker.execute("ingest-on-demand-spy")
    persisted = boundary.get("ingest-on-demand-spy")

    assert persisted is not None
    assert result.records == persisted
    assert persisted.ledger.job_state == "succeeded"
    assert result.summary.no_live_external_calls is True
    assert result.summary.opened_database_connection is False
    assert result.summary.called_live_provider is False


def test_manual_pre_cache_cached_asset_is_terminal_and_idempotent():
    records = serialize_ingestion_job_response(get_pre_cache_job_status("pre-cache-launch-voo"))
    first = execute_ingestion_worker_record(records)
    second = execute_ingestion_worker_record(first.records)

    assert first.summary.transitions == ["succeeded"]
    assert second.summary.transitions == ["succeeded"]
    assert first.records == second.records
    assert first.summary.generated_output_available is True
    assert first.summary.generated_output_cacheable is True
    assert first.summary.blocked_from_generated_outputs is False
    assert first.records.ledger.generated_route == "/assets/VOO"


def test_manual_pre_cache_pending_asset_can_finish_stale_with_sanitized_diagnostic():
    records = serialize_ingestion_job_response(get_pre_cache_job_status("pre-cache-launch-spy"))
    outcome = IngestionWorkerFixtureOutcome(
        terminal_state=IngestionLedgerJobState.stale,
        error_category=SanitizedErrorCategory.source_unavailable,
        error_code="fixture_source_stale",
        sanitized_message="Fixture evidence is stale; no source snapshot was written.",
        retryable=True,
        source_policy_ref="source-use-policy-v1",
        checksum="sha256:fixture",
    )

    result = execute_ingestion_worker_record(records, fixture_outcome=outcome)

    assert result.summary.transitions == ["pending", "running", "stale"]
    assert result.summary.retryable is True
    assert result.summary.generated_output_available is False
    assert result.summary.blocked_from_generated_outputs is True
    assert result.records.ledger.compact_metadata["source_policy_ref"] == "source-use-policy-v1"
    assert result.records.ledger.compact_metadata["checksum"] == "sha256:fixture"
    assert result.records.diagnostics[0].category == "source_unavailable"
    assert result.records.diagnostics[0].stores_provider_payload is False
    assert result.records.diagnostics[0].stores_raw_source_text is False


def test_blocked_unsupported_out_of_scope_unknown_and_unavailable_jobs_stay_non_generated():
    cases = [
        ("pre-cache-unsupported-tqqq", "unsupported"),
        ("pre-cache-out-of-scope-gme", "out_of_scope"),
        ("pre-cache-unknown-zzzz", "unknown"),
        ("missing-pre-cache-job", "unavailable"),
    ]

    for job_id, state in cases:
        records = serialize_ingestion_job_response(get_pre_cache_job_status(job_id))
        result = execute_ingestion_worker_record(records)

        assert result.summary.terminal_state == state
        assert result.summary.transitions == [state]
        assert result.summary.generated_output_available is False
        assert result.summary.generated_output_cacheable is False
        assert result.summary.blocked_from_generated_outputs is True
        assert result.records.ledger.generated_route is None
        assert result.records.ledger.can_open_generated_page is False
        assert result.records.ledger.can_answer_chat is False
        assert result.records.ledger.can_compare is False


def test_retryable_failure_is_sanitized_and_repeat_execution_is_stable():
    records = serialize_ingestion_job_response(request_ingestion("SPY"))
    outcome = IngestionWorkerFixtureOutcome(
        terminal_state=IngestionLedgerJobState.failed,
        error_category=SanitizedErrorCategory.validation_failed,
        error_code="fixture_validation_failed",
        sanitized_message="validation failed with password and raw text details",
        retryable=True,
    )

    first = execute_ingestion_worker_record(records, fixture_outcome=outcome)
    second = execute_ingestion_worker_record(first.records, fixture_outcome=outcome)

    assert first.summary.transitions == ["pending", "running", "failed"]
    assert second.summary.transitions == ["failed"]
    assert first.records == second.records
    assert first.summary.retryable is True
    assert first.summary.generated_output_available is False
    assert first.records.diagnostics[0].category == "validation_failed"
    assert first.records.diagnostics[0].sanitized_message == "Sanitized deterministic ingestion worker diagnostic."
    assert "password" not in first.records.diagnostics[0].sanitized_message.lower()
    assert first.records.diagnostics[0].stores_secret is False
    assert first.records.diagnostics[0].stores_user_text is False
    assert first.records.diagnostics[0].stores_provider_payload is False


def test_source_policy_blocked_fixture_fails_without_generated_output_or_raw_source_storage():
    records = serialize_ingestion_job_response(request_ingestion("SPY"))
    outcome = IngestionWorkerFixtureOutcome(
        terminal_state=IngestionLedgerJobState.failed,
        error_category=SanitizedErrorCategory.source_policy_blocked,
        error_code="fixture_source_policy_blocked",
        sanitized_message="Source policy blocked generated output.",
        retryable=False,
        source_policy_ref="source-use-policy-v1",
    )

    result = execute_ingestion_worker_record(records, fixture_outcome=outcome)

    assert result.summary.terminal_state == "failed"
    assert result.summary.blocked_from_generated_outputs is True
    assert result.summary.generated_output_cacheable is False
    assert result.records.ledger.generated_output_available is False
    assert result.records.ledger.can_open_generated_page is False
    assert result.records.diagnostics[0].category == "source_policy_blocked"
    assert result.records.diagnostics[0].stores_raw_source_text is False


def test_refresh_and_source_revalidation_categories_preserve_future_state_space_as_stale():
    refresh_records = serialize_ingestion_job_response(
        get_pre_cache_job_status("pre-cache-launch-voo"),
        category=IngestionJobCategory.refresh,
    )
    source_revalidation_records = serialize_ingestion_job_response(
        get_pre_cache_job_status("pre-cache-launch-voo"),
        category=IngestionJobCategory.source_revalidation,
    )
    refresh_records = refresh_records.model_copy(
        update={"ledger": refresh_records.ledger.model_copy(update={"job_state": "pending"})}
    )
    source_revalidation_records = source_revalidation_records.model_copy(
        update={"ledger": source_revalidation_records.ledger.model_copy(update={"job_state": "running"})}
    )

    refresh_result = execute_ingestion_worker_record(refresh_records)
    revalidation_result = execute_ingestion_worker_record(source_revalidation_records)

    assert refresh_result.summary.transitions == ["pending", "running", "stale"]
    assert revalidation_result.summary.transitions == ["running", "stale"]
    assert refresh_result.summary.terminal_state == "stale"
    assert revalidation_result.summary.terminal_state == "stale"
    assert refresh_result.summary.generated_output_available is True
    assert revalidation_result.summary.generated_output_available is True


def test_ingestion_worker_import_surface_has_no_live_database_or_provider_markers():
    source = (ROOT / "backend" / "ingestion_worker.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "OPENROUTER",
        "api_key",
        "CloudScheduler",
        "object_storage",
    ]
    for marker in forbidden:
        assert marker not in source
