from __future__ import annotations

from pathlib import Path

from backend.ingestion import execute_ingestion_job_through_ledger, get_pre_cache_job_status, request_ingestion
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
from backend.generated_output_cache_repository import InMemoryGeneratedOutputCacheRepository
from backend.models import (
    EvidenceState,
    FreshnessState,
    IngestionCapabilities,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsEventType,
)
from backend.overview import generate_asset_overview
from backend.provider_adapters.etf_issuer import (
    build_etf_issuer_acquisition_result,
    execute_etf_issuer_handoff_gated_official_source_acquisition,
)
from backend.provider_adapters.sec_stock import (
    build_sec_stock_acquisition_result,
    execute_sec_stock_handoff_gated_official_source_acquisition,
)
from backend.providers import fetch_mock_provider_response, mock_etf_issuer_adapter, mock_sec_stock_adapter
from backend.knowledge_pack_repository import (
    InMemoryAssetKnowledgePackRepository,
    KnowledgePackRepositoryContractError,
    knowledge_pack_records_from_acquisition_result,
)
from backend.repositories.ingestion_jobs import SanitizedErrorCategory
from backend.source_snapshot_repository import (
    InMemorySourceSnapshotArtifactRepository,
    SourceSnapshotContractError,
    source_snapshot_records_from_acquisition_result,
)
from backend.weekly_news_repository import (
    InMemoryWeeklyNewsEventEvidenceRepository,
    WeeklyNewsEventCandidateRow,
    WeeklyNewsEventEvidenceContractError,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
    acquire_weekly_news_event_evidence_from_official_sources,
)


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


def test_server_side_execution_helper_uses_configured_ledger_or_fixture_fallback():
    records = serialize_ingestion_job_response(request_ingestion("SPY"))
    boundary = InMemoryIngestionWorkerLedger.from_records([records])

    configured = execute_ingestion_job_through_ledger("ingest-on-demand-spy", ingestion_job_ledger=boundary)
    fallback = execute_ingestion_job_through_ledger("ingest-on-demand-spy")

    assert configured.summary.transitions == ["pending", "running", "succeeded"]
    assert boundary.get("ingest-on-demand-spy").ledger.job_state == "succeeded"
    assert fallback.summary.transitions == ["pending", "running", "succeeded"]
    assert fallback.summary.generated_output_available is False


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


def test_worker_can_exercise_sec_acquisition_metadata_without_activating_generated_outputs():
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "AAPL").licensing
    acquisition = build_sec_stock_acquisition_result(adapter, adapter.request("AAPL"), licensing)
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    outcome = IngestionWorkerFixtureOutcome(
        terminal_state=IngestionLedgerJobState.succeeded,
        source_policy_ref=acquisition.source_policy_ref,
        checksum=acquisition.checksum,
    )

    result = execute_ingestion_worker_record(records, fixture_outcome=outcome)

    assert result.summary.transitions == ["pending", "running", "succeeded"]
    assert result.summary.terminal_state == "succeeded"
    assert result.summary.generated_output_available is False
    assert result.summary.generated_output_cacheable is False
    assert result.summary.blocked_from_generated_outputs is False
    assert result.summary.no_live_external_calls is True
    assert result.summary.opened_database_connection is False
    assert result.summary.called_live_provider is False
    assert result.records.ledger.compact_metadata["source_policy_ref"] == "source-use-policy-v1"
    assert result.records.ledger.compact_metadata["checksum"] == acquisition.checksum
    assert result.records.ledger.raw_provider_payload_stored is False
    assert result.records.ledger.unrestricted_source_text_stored is False
    assert result.records.ledger.secrets_stored is False


def test_worker_can_exercise_etf_issuer_acquisition_metadata_without_activating_generated_outputs():
    adapter = mock_etf_issuer_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "VOO").licensing
    acquisition = build_etf_issuer_acquisition_result(adapter, adapter.request("VOO"), licensing)
    response = get_pre_cache_job_status("pre-cache-launch-voo").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    outcome = IngestionWorkerFixtureOutcome(
        terminal_state=IngestionLedgerJobState.succeeded,
        source_policy_ref=acquisition.source_policy_ref,
        checksum=acquisition.checksum,
    )

    result = execute_ingestion_worker_record(records, fixture_outcome=outcome)

    assert result.summary.transitions == ["pending", "running", "succeeded"]
    assert result.summary.terminal_state == "succeeded"
    assert result.summary.generated_output_available is False
    assert result.summary.generated_output_cacheable is False
    assert result.summary.blocked_from_generated_outputs is False
    assert result.summary.no_live_external_calls is True
    assert result.summary.opened_database_connection is False
    assert result.summary.called_live_provider is False
    assert result.records.ledger.compact_metadata["source_policy_ref"] == "source-use-policy-v1"
    assert result.records.ledger.compact_metadata["checksum"] == acquisition.checksum
    assert result.records.ledger.raw_provider_payload_stored is False
    assert result.records.ledger.unrestricted_source_text_stored is False
    assert result.records.ledger.secrets_stored is False


def test_worker_persists_golden_acquisition_snapshots_through_injected_mocked_writer_only():
    adapter = mock_etf_issuer_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "QQQ").licensing
    acquisition = build_etf_issuer_acquisition_result(adapter, adapter.request("QQQ"), licensing)
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-qqq",
    )
    response = get_pre_cache_job_status("pre-cache-launch-qqq").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    snapshot_repository = InMemorySourceSnapshotArtifactRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        source_snapshot_repository=snapshot_repository,
        fixture_outcomes={
            "pre-cache-launch-qqq": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                source_snapshot_records=snapshot_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-qqq")
    persisted = snapshot_repository.records()

    assert result.summary.terminal_state == "succeeded"
    assert result.summary.generated_output_available is False
    assert result.summary.generated_output_cacheable is False
    assert result.records.ledger.compact_metadata["source_snapshot_persistence_configured"] is True
    assert result.records.ledger.compact_metadata["source_snapshot_artifact_count"] == len(snapshot_records.artifacts)
    assert persisted == snapshot_records
    assert all(artifact.generated_output_available is False for artifact in persisted.artifacts)
    assert all(artifact.raw_provider_payload_stored is False for artifact in persisted.artifacts)


def test_worker_blocks_live_acquisition_records_without_explicit_readiness_and_writers():
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "AAPL").licensing
    acquisition = build_sec_stock_acquisition_result(adapter, adapter.request("AAPL"), licensing)
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-aapl",
    )
    knowledge_pack_records = knowledge_pack_records_from_acquisition_result(acquisition, snapshot_records)
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        fixture_outcomes={
            "pre-cache-launch-aapl": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                source_snapshot_records=snapshot_records,
                knowledge_pack_records=knowledge_pack_records,
                live_acquisition_attempted=True,
                live_acquisition_readiness_passed=False,
                live_repository_writers_required=True,
            )
        },
    )

    result = worker.execute("pre-cache-launch-aapl")

    assert result.summary.terminal_state == "failed"
    assert result.records.diagnostics[0].error_code == "live_acquisition_readiness_failed"
    assert result.records.ledger.generated_output_available is False
    assert result.records.ledger.raw_provider_payload_stored is False
    assert result.records.ledger.unrestricted_source_text_stored is False
    assert result.records.ledger.secrets_stored is False


def test_worker_routes_ready_live_acquisition_records_through_existing_mocked_writer_boundaries():
    adapter = mock_etf_issuer_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "VOO").licensing
    acquisition = build_etf_issuer_acquisition_result(adapter, adapter.request("VOO"), licensing)
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-voo",
    )
    knowledge_pack_records = knowledge_pack_records_from_acquisition_result(acquisition, snapshot_records)
    response = get_pre_cache_job_status("pre-cache-launch-voo").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    snapshot_repository = InMemorySourceSnapshotArtifactRepository()
    knowledge_pack_repository = InMemoryAssetKnowledgePackRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        source_snapshot_repository=snapshot_repository,
        knowledge_pack_repository=knowledge_pack_repository,
        fixture_outcomes={
            "pre-cache-launch-voo": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                source_snapshot_records=snapshot_records,
                knowledge_pack_records=knowledge_pack_records,
                live_acquisition_attempted=True,
                live_acquisition_readiness_passed=True,
                live_repository_writers_required=True,
                official_source_handoff_passed=True,
            )
        },
    )

    result = worker.execute("pre-cache-launch-voo")

    assert result.summary.terminal_state == "succeeded"
    assert result.summary.no_live_external_calls is True
    assert result.summary.called_live_provider is False
    assert snapshot_repository.records().artifacts
    assert knowledge_pack_repository.read_knowledge_pack_records("VOO") is not None
    assert result.records.ledger.compact_metadata["live_acquisition_attempted"] is True
    assert result.records.ledger.compact_metadata["live_acquisition_readiness_passed"] is True
    assert result.records.ledger.compact_metadata["source_snapshot_persistence_configured"] is True
    assert result.records.ledger.compact_metadata["knowledge_pack_persistence_configured"] is True


def test_worker_requires_handoff_gated_official_source_execution_before_live_writes():
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "AAPL").licensing
    acquisition = execute_sec_stock_handoff_gated_official_source_acquisition(
        adapter,
        adapter.request("AAPL"),
        licensing,
    )
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-aapl",
    )
    knowledge_pack_records = knowledge_pack_records_from_acquisition_result(acquisition, snapshot_records)
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    worker = DeterministicIngestionWorker(
        ledger_boundary=InMemoryIngestionWorkerLedger.from_records([records]),
        source_snapshot_repository=InMemorySourceSnapshotArtifactRepository(),
        knowledge_pack_repository=InMemoryAssetKnowledgePackRepository(),
        fixture_outcomes={
            "pre-cache-launch-aapl": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                source_snapshot_records=snapshot_records,
                knowledge_pack_records=knowledge_pack_records,
                live_acquisition_attempted=True,
                live_acquisition_readiness_passed=True,
                live_repository_writers_required=True,
                retrieval_outcome="mocked_fetch_completed",
                parser_outcome="parsed",
                source_handoff_outcome="approved",
            )
        },
    )

    result = worker.execute("pre-cache-launch-aapl")

    assert result.summary.terminal_state == "failed"
    assert result.records.diagnostics[0].error_code == "live_acquisition_readiness_failed"
    assert result.records.ledger.generated_output_available is False
    assert result.records.ledger.raw_provider_payload_stored is False
    assert result.records.ledger.unrestricted_source_text_stored is False


def test_worker_persists_handoff_gated_sec_stock_records_with_retrieval_parser_metadata():
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "AAPL").licensing
    acquisition = execute_sec_stock_handoff_gated_official_source_acquisition(
        adapter,
        adapter.request("AAPL"),
        licensing,
    )
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-aapl",
    )
    knowledge_pack_records = knowledge_pack_records_from_acquisition_result(acquisition, snapshot_records)
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    snapshot_repository = InMemorySourceSnapshotArtifactRepository()
    knowledge_pack_repository = InMemoryAssetKnowledgePackRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=InMemoryIngestionWorkerLedger.from_records([records]),
        source_snapshot_repository=snapshot_repository,
        knowledge_pack_repository=knowledge_pack_repository,
        fixture_outcomes={
            "pre-cache-launch-aapl": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                source_snapshot_records=snapshot_records,
                knowledge_pack_records=knowledge_pack_records,
                live_acquisition_attempted=True,
                live_acquisition_readiness_passed=True,
                live_repository_writers_required=True,
                official_source_handoff_passed=True,
                retrieval_outcome="mocked_fetch_completed",
                parser_outcome="parsed",
                source_handoff_outcome="approved",
            )
        },
    )

    result = worker.execute("pre-cache-launch-aapl")

    assert result.summary.terminal_state == "succeeded"
    assert snapshot_repository.records().artifacts
    assert knowledge_pack_repository.read_knowledge_pack_records("AAPL") is not None
    metadata = result.records.ledger.compact_metadata
    assert metadata["official_source_handoff_passed"] is True
    assert metadata["retrieval_outcome"] == "mocked_fetch_completed"
    assert metadata["parser_outcome"] == "parsed"
    assert metadata["source_handoff_outcome"] == "approved"


def test_worker_persists_golden_knowledge_pack_through_injected_mocked_writer_only():
    adapter = mock_etf_issuer_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "VOO").licensing
    acquisition = build_etf_issuer_acquisition_result(adapter, adapter.request("VOO"), licensing)
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-voo",
    )
    knowledge_pack_records = knowledge_pack_records_from_acquisition_result(acquisition, snapshot_records)
    response = get_pre_cache_job_status("pre-cache-launch-voo").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    knowledge_pack_repository = InMemoryAssetKnowledgePackRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        knowledge_pack_repository=knowledge_pack_repository,
        fixture_outcomes={
            "pre-cache-launch-voo": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                knowledge_pack_records=knowledge_pack_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-voo")
    persisted = knowledge_pack_repository.read_knowledge_pack_records("VOO")

    assert result.summary.terminal_state == "succeeded"
    assert result.summary.generated_output_available is False
    assert result.summary.generated_output_cacheable is False
    assert result.records.ledger.compact_metadata["knowledge_pack_persistence_configured"] is True
    assert result.records.ledger.compact_metadata["knowledge_pack_source_document_count"] == len(
        knowledge_pack_records.source_documents
    )
    assert persisted == knowledge_pack_records
    assert persisted.envelope.generated_output_available is False
    assert persisted.envelope.reusable_generated_output_cache_hit is False
    assert persisted.envelope.generated_route is None


def test_worker_persists_weekly_news_evidence_through_injected_mocked_writer_only():
    weekly_news_records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="VOO",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[
            _weekly_news_candidate("issuer_announcement", "VOO", WeeklyNewsSourceRankTier.etf_issuer_announcement),
            _weekly_news_candidate("fact_sheet_change", "VOO", WeeklyNewsSourceRankTier.fact_sheet_change),
        ],
    )
    response = get_pre_cache_job_status("pre-cache-launch-voo").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    weekly_news_repository = InMemoryWeeklyNewsEventEvidenceRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        weekly_news_repository=weekly_news_repository,
        fixture_outcomes={
            "pre-cache-launch-voo": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref="source-use-policy-v1",
                checksum="sha256:weekly-news-voo",
                weekly_news_records=weekly_news_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-voo")
    persisted = weekly_news_repository.read_weekly_news_event_evidence_records("voo")

    assert result.summary.terminal_state == "succeeded"
    assert result.summary.generated_output_available is False
    assert result.summary.generated_output_cacheable is False
    assert result.records.ledger.compact_metadata["weekly_news_persistence_configured"] is True
    assert result.records.ledger.compact_metadata["weekly_news_window_count"] == 1
    assert result.records.ledger.compact_metadata["weekly_news_candidate_count"] == len(weekly_news_records.candidates)
    assert result.records.ledger.compact_metadata["weekly_news_selected_event_count"] == 2
    assert result.records.ledger.compact_metadata["weekly_news_ai_threshold_count"] == 1
    assert persisted == weekly_news_records
    assert persisted.ai_thresholds[0].analysis_allowed is True
    assert all(row.no_generated_analysis_change is True for row in persisted.selected_events)
    assert all(row.stores_raw_article_text is False for row in persisted.candidates)


def test_worker_blocks_ready_live_weekly_news_acquisition_without_weekly_writer():
    weekly_news_records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="VOO",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[
            _weekly_news_candidate("issuer_announcement", "VOO", WeeklyNewsSourceRankTier.etf_issuer_announcement),
        ],
    )
    response = get_pre_cache_job_status("pre-cache-launch-voo").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    worker = DeterministicIngestionWorker(
        ledger_boundary=InMemoryIngestionWorkerLedger.from_records([records]),
        fixture_outcomes={
            "pre-cache-launch-voo": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref="source-use-policy-v1",
                checksum="sha256:weekly-news-voo",
                weekly_news_records=weekly_news_records,
                live_acquisition_attempted=True,
                live_acquisition_readiness_passed=True,
                live_repository_writers_required=True,
                official_source_handoff_passed=True,
            )
        },
    )

    result = worker.execute("pre-cache-launch-voo")

    assert result.summary.terminal_state == "failed"
    assert result.records.diagnostics[0].error_code == "live_acquisition_readiness_failed"
    assert result.records.ledger.generated_output_available is False
    assert result.records.ledger.raw_provider_payload_stored is False
    assert result.records.ledger.secrets_stored is False


def test_worker_routes_ready_live_weekly_news_acquisition_through_mocked_writer():
    weekly_news_records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[
            _weekly_news_candidate("prospectus", "QQQ", WeeklyNewsSourceRankTier.prospectus_update),
            _weekly_news_candidate("fact_sheet", "QQQ", WeeklyNewsSourceRankTier.fact_sheet_change),
        ],
    )
    response = get_pre_cache_job_status("pre-cache-launch-qqq").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    repository = InMemoryWeeklyNewsEventEvidenceRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=InMemoryIngestionWorkerLedger.from_records([records]),
        weekly_news_repository=repository,
        fixture_outcomes={
            "pre-cache-launch-qqq": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref="source-use-policy-v1",
                checksum="sha256:weekly-news-qqq",
                weekly_news_records=weekly_news_records,
                live_acquisition_attempted=True,
                live_acquisition_readiness_passed=True,
                live_repository_writers_required=True,
                official_source_handoff_passed=True,
            )
        },
    )

    result = worker.execute("pre-cache-launch-qqq")
    persisted = repository.read_weekly_news_event_evidence_records("QQQ")

    assert result.summary.terminal_state == "succeeded"
    assert persisted == weekly_news_records
    assert result.records.ledger.compact_metadata["live_acquisition_attempted"] is True
    assert result.records.ledger.compact_metadata["live_acquisition_readiness_passed"] is True
    assert result.records.ledger.compact_metadata["weekly_news_persistence_configured"] is True


class FailingWeeklyNewsRepository:
    def persist(self, records):
        raise WeeklyNewsEventEvidenceContractError("mocked writer rejected weekly news records")


def test_worker_fails_closed_when_configured_weekly_news_writer_rejects_records():
    weekly_news_records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="AAPL",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[_weekly_news_candidate("official_filing", "AAPL", WeeklyNewsSourceRankTier.official_filing)],
    )
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        weekly_news_repository=FailingWeeklyNewsRepository(),
        fixture_outcomes={
            "pre-cache-launch-aapl": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref="source-use-policy-v1",
                checksum="sha256:weekly-news-aapl",
                weekly_news_records=weekly_news_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-aapl")

    assert result.summary.transitions == ["pending", "running", "failed"]
    assert result.summary.terminal_state == "failed"
    assert result.summary.generated_output_available is False
    assert result.records.ledger.can_open_generated_page is False
    assert result.records.diagnostics[0].category == "validation_failed"
    assert result.records.diagnostics[0].error_code == "weekly_news_persistence_failed"
    assert result.records.diagnostics[0].stores_raw_source_text is False


class FailingKnowledgePackRepository:
    def persist(self, records):
        raise KnowledgePackRepositoryContractError("mocked writer rejected knowledge-pack records")


def test_worker_fails_closed_when_configured_knowledge_pack_writer_rejects_records():
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "AAPL").licensing
    acquisition = build_sec_stock_acquisition_result(adapter, adapter.request("AAPL"), licensing)
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-aapl",
    )
    knowledge_pack_records = knowledge_pack_records_from_acquisition_result(acquisition, snapshot_records)
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        knowledge_pack_repository=FailingKnowledgePackRepository(),
        fixture_outcomes={
            "pre-cache-launch-aapl": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                knowledge_pack_records=knowledge_pack_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-aapl")

    assert result.summary.transitions == ["pending", "running", "failed"]
    assert result.summary.terminal_state == "failed"
    assert result.summary.generated_output_available is False
    assert result.records.ledger.can_open_generated_page is False
    assert result.records.diagnostics[0].category == "validation_failed"
    assert result.records.diagnostics[0].error_code == "knowledge_pack_persistence_failed"
    assert result.records.diagnostics[0].stores_raw_source_text is False


class FailingSourceSnapshotRepository:
    def persist(self, records):
        raise SourceSnapshotContractError("mocked writer rejected source snapshot records")


def test_worker_fails_closed_when_configured_source_snapshot_writer_rejects_records():
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(adapter.provider_kind, "AAPL").licensing
    acquisition = build_sec_stock_acquisition_result(adapter, adapter.request("AAPL"), licensing)
    snapshot_records = source_snapshot_records_from_acquisition_result(
        acquisition,
        ingestion_job_id="pre-cache-launch-aapl",
    )
    response = get_pre_cache_job_status("pre-cache-launch-aapl").model_copy(
        update={
            "job_state": IngestionLedgerJobState.pending,
            "worker_status": None,
            "generated_route": None,
            "generated_output_available": False,
            "capabilities": IngestionCapabilities(),
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    records = serialize_ingestion_job_response(response)
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        source_snapshot_repository=FailingSourceSnapshotRepository(),
        fixture_outcomes={
            "pre-cache-launch-aapl": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                source_policy_ref=acquisition.source_policy_ref,
                checksum=acquisition.checksum,
                source_snapshot_records=snapshot_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-aapl")

    assert result.summary.transitions == ["pending", "running", "failed"]
    assert result.summary.terminal_state == "failed"
    assert result.summary.generated_output_available is False
    assert result.records.ledger.can_open_generated_page is False
    assert result.records.diagnostics[0].category == "validation_failed"
    assert result.records.diagnostics[0].error_code == "source_snapshot_persistence_failed"
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


def test_worker_can_persist_generated_output_cache_metadata_with_mocked_writer():
    generated_writer = InMemoryGeneratedOutputCacheRepository()
    generate_asset_overview("VOO", generated_output_cache_writer=generated_writer)
    generated_records = generated_writer.read_asset_overview_records("VOO")
    assert generated_records is not None

    records = serialize_ingestion_job_response(get_pre_cache_job_status("pre-cache-launch-voo"))
    records = records.model_copy(update={"ledger": records.ledger.model_copy(update={"job_state": "pending"})})
    ledger = InMemoryIngestionWorkerLedger.from_records([records])
    cache_repository = InMemoryGeneratedOutputCacheRepository()
    worker = DeterministicIngestionWorker(
        ledger_boundary=ledger,
        generated_output_cache_repository=cache_repository,
        fixture_outcomes={
            "pre-cache-launch-voo": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                generated_output_cache_records=generated_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-voo")
    persisted_cache = cache_repository.read_asset_overview_records("VOO")

    assert result.summary.transitions == ["pending", "running", "succeeded"]
    assert result.summary.generated_output_cacheable is True
    assert persisted_cache is not None
    assert result.records.ledger.compact_metadata["generated_output_cache_persistence_configured"] is True
    assert result.records.ledger.compact_metadata["generated_output_cache_entry_count"] == 1


def test_worker_generated_output_cache_writer_failure_fails_closed():
    generated_writer = InMemoryGeneratedOutputCacheRepository()
    generate_asset_overview("VOO", generated_output_cache_writer=generated_writer)
    generated_records = generated_writer.read_asset_overview_records("VOO")
    assert generated_records is not None

    class FailingGeneratedOutputCacheWriter:
        def persist(self, records):
            raise RuntimeError("controlled generated-output cache failure")

    records = serialize_ingestion_job_response(get_pre_cache_job_status("pre-cache-launch-voo"))
    records = records.model_copy(update={"ledger": records.ledger.model_copy(update={"job_state": "pending"})})
    worker = DeterministicIngestionWorker(
        ledger_boundary=InMemoryIngestionWorkerLedger.from_records([records]),
        generated_output_cache_repository=FailingGeneratedOutputCacheWriter(),
        fixture_outcomes={
            "pre-cache-launch-voo": IngestionWorkerFixtureOutcome(
                terminal_state=IngestionLedgerJobState.succeeded,
                generated_output_cache_records=generated_records,
            )
        },
    )

    result = worker.execute("pre-cache-launch-voo")

    assert result.summary.transitions == ["pending", "running", "failed"]
    assert result.summary.generated_output_available is False
    assert result.records.diagnostics[0].error_code == "generated_output_cache_persistence_failed"
    assert result.records.diagnostics[0].stores_raw_source_text is False


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


def _weekly_news_candidate(
    event_id: str,
    ticker: str,
    tier: WeeklyNewsSourceRankTier,
) -> WeeklyNewsEventCandidateRow:
    ticker = ticker.upper()
    issuer_tiers = {
        WeeklyNewsSourceRankTier.etf_issuer_announcement,
        WeeklyNewsSourceRankTier.prospectus_update,
        WeeklyNewsSourceRankTier.fact_sheet_change,
    }
    source_quality = SourceQuality.issuer if tier in issuer_tiers else SourceQuality.official
    return WeeklyNewsEventCandidateRow(
        candidate_event_id=event_id,
        window_id=f"wnf_window:{ticker}:2026-04-23",
        asset_ticker=ticker,
        source_asset_ticker=ticker,
        event_type=WeeklyNewsEventType.methodology_change.value,
        event_date="2026-04-21",
        published_at="2026-04-21T12:00:00Z",
        retrieved_at="2026-04-23T12:00:00Z",
        period_bucket="current_week_to_date",
        source_document_id=f"src_{ticker.lower()}_{event_id}",
        source_chunk_id=f"chk_{ticker.lower()}_{event_id}",
        citation_ids=[f"c_weekly_{ticker.lower()}_{event_id}"],
        citation_asset_tickers={f"c_weekly_{ticker.lower()}_{event_id}": ticker},
        source_type=tier.value,
        source_rank=1,
        source_rank_tier=tier.value,
        source_quality=source_quality.value,
        allowlist_status=SourceAllowlistStatus.allowed.value,
        source_use_policy=SourceUsePolicy.summary_allowed.value,
        freshness_state=FreshnessState.fresh.value,
        evidence_state=EvidenceState.supported.value,
        importance_score=10,
        duplicate_group_id=event_id,
        title_checksum=f"sha256:title:{ticker}:{event_id}",
        evidence_checksum=f"sha256:evidence:{ticker}:{event_id}",
    )
