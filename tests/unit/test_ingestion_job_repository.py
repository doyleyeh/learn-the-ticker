from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from backend.ingestion import (
    get_ingestion_job_status,
    get_pre_cache_job_status,
    request_ingestion,
)
from backend.ingestion_job_repository import (
    INGESTION_JOB_LEDGER_REPOSITORY_BOUNDARY,
    INGESTION_JOB_LEDGER_TABLES,
    IngestionJobCategory,
    IngestionJobLedgerContractError,
    IngestionJobLedgerRecords,
    IngestionJobLedgerRepository,
    IngestionLedgerJobState,
    classify_ingestion_scope,
    ingestion_job_ledger_repository_metadata,
    serialize_ingestion_job_response,
    validate_ingestion_job_ledger_records,
)
from backend.repositories.ingestion_jobs import (
    IngestionJobLedgerDiagnosticRow,
    IngestionJobLedgerRecordRow,
    IngestionJobLedgerSourceRefRow,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeDurableSession:
    def __init__(self):
        self.records = {}
        self.rows = []
        self.commits = 0

    def save_repository_record(self, collection, key, records):
        self.records[(collection, key)] = records

    def get_repository_record(self, collection, key):
        return self.records.get((collection, key))

    def add_all(self, rows):
        self.rows.extend(rows)

    def commit(self):
        self.commits += 1


def test_ingestion_job_ledger_metadata_is_dormant_and_explicit():
    metadata = ingestion_job_ledger_repository_metadata()

    assert metadata.boundary == INGESTION_JOB_LEDGER_REPOSITORY_BOUNDARY
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == INGESTION_JOB_LEDGER_TABLES
    assert set(INGESTION_JOB_LEDGER_TABLES) == {
        "ingestion_job_ledger_records",
        "ingestion_job_ledger_source_refs",
        "ingestion_job_ledger_diagnostics",
    }
    assert "job_category" in metadata.tables["ingestion_job_ledger_records"].columns
    assert "source_use_policy" in metadata.tables["ingestion_job_ledger_source_refs"].columns
    assert "sanitized_message" in metadata.tables["ingestion_job_ledger_diagnostics"].columns
    assert "raw_provider_payload_stored" in metadata.tables["ingestion_job_ledger_records"].columns


def test_ingestion_job_ledger_supports_required_categories_and_states():
    assert {category.value for category in IngestionJobCategory} == {
        "manual_pre_cache",
        "approved_on_demand",
        "refresh",
        "source_revalidation",
    }
    assert {state.value for state in IngestionLedgerJobState} == {
        "pending",
        "running",
        "succeeded",
        "failed",
        "unsupported",
        "out_of_scope",
        "unknown",
        "unavailable",
        "stale",
    }


def test_migration_revision_is_importable_and_limited_to_ingestion_ledger_tables():
    revision_path = ROOT / "alembic" / "versions" / "20260425_0003_ingestion_job_ledger_contracts.py"
    source = revision_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("ingestion_ledger_contract_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0003"
    assert module.down_revision == "20260425_0002"
    assert module.INGESTION_JOB_LEDGER_TABLE_NAMES == INGESTION_JOB_LEDGER_TABLES
    for table_name in INGESTION_JOB_LEDGER_TABLES:
        assert f'"{table_name}"' in source

    forbidden_table_markers = [
        "source_documents",
        "document_chunks",
        "chat_sessions",
        "chat_messages",
        "generated_output_cache",
        "provider_secrets",
        "user_accounts",
        "scheduler",
    ]
    for marker in forbidden_table_markers:
        assert marker not in module.INGESTION_JOB_LEDGER_TABLE_NAMES
        assert f'op.create_table("{marker}"' not in source


def test_scope_classification_preserves_mvp_boundaries():
    supported = classify_ingestion_scope("VOO")
    approved_pending = classify_ingestion_scope("SPY")
    unsupported = classify_ingestion_scope("TQQQ")
    out_of_scope = classify_ingestion_scope("GME")
    unknown = classify_ingestion_scope("ZZZZ")

    assert supported.scope_decision == "cached_supported_asset"
    assert supported.support_status == "supported"
    assert supported.generated_output_allowed is True
    assert supported.approved_for_on_demand_ingestion is False

    assert approved_pending.scope_decision == "approved_pending_ingestion"
    assert approved_pending.support_status == "pending_ingestion"
    assert approved_pending.approved_for_on_demand_ingestion is True
    assert approved_pending.generated_output_allowed is False

    assert unsupported.scope_decision == "blocked_unsupported_asset"
    assert unsupported.support_status == "unsupported"
    assert unsupported.generated_output_allowed is False

    assert out_of_scope.scope_decision == "blocked_out_of_scope_asset"
    assert out_of_scope.support_status == "out_of_scope"
    assert out_of_scope.approval_basis == "outside_top500_manifest_without_approved_on_demand_ingestion"

    assert unknown.scope_decision == "unknown_or_unavailable_asset"
    assert unknown.support_status == "unknown"


def test_ledger_serializes_approved_on_demand_pending_without_generated_output():
    response = request_ingestion("SPY")
    records = IngestionJobLedgerRepository().serialize_response(response)

    assert records.table_names == INGESTION_JOB_LEDGER_TABLES
    assert records.ledger.job_id == "ingest-on-demand-spy"
    assert records.ledger.job_category == "approved_on_demand"
    assert records.ledger.job_state == "pending"
    assert records.scope.support_status == "pending_ingestion"
    assert records.scope.approved_for_on_demand_ingestion is True
    assert records.ledger.generated_route is None
    assert records.ledger.generated_output_available is False
    assert records.ledger.can_open_generated_page is False
    assert records.ledger.can_answer_chat is False
    assert records.ledger.can_compare is False
    assert records.ledger.no_live_external_calls is True
    assert records.ledger.raw_provider_payload_stored is False
    assert records.ledger.raw_article_text_stored is False
    assert records.ledger.raw_user_text_stored is False
    assert records.ledger.secrets_stored is False


def test_durable_ingestion_ledger_save_and_read_preserve_validated_records():
    session = FakeDurableSession()
    repository = IngestionJobLedgerRepository(session=session, commit_on_write=True)
    records = serialize_ingestion_job_response(request_ingestion("SPY"))

    repository.save(records)
    read_back = repository.get(records.ledger.job_id)

    assert read_back == records
    assert session.records[("ingestion_job_ledger", records.ledger.job_id)] == records
    assert session.commits == 1
    assert repository.read(records.ledger.job_id) == records
    assert repository.get("missing") is None


def test_ledger_serializes_manual_pre_cache_blocked_assets_without_generated_output():
    for job_id, state, support_status in [
        ("pre-cache-unsupported-tqqq", "unsupported", "unsupported"),
        ("pre-cache-out-of-scope-gme", "out_of_scope", "out_of_scope"),
        ("pre-cache-unknown-zzzz", "unknown", "unknown"),
        ("missing-pre-cache-job", "unavailable", "unknown"),
    ]:
        response = get_pre_cache_job_status(job_id)
        records = serialize_ingestion_job_response(response)

        assert records.ledger.job_category == "manual_pre_cache"
        assert records.ledger.job_state == state
        assert records.scope.support_status == support_status
        assert records.ledger.generated_route is None
        assert records.ledger.generated_output_available is False
        assert records.ledger.can_open_generated_page is False
        assert records.ledger.can_answer_chat is False
        assert records.ledger.can_compare is False


def test_ledger_maps_refresh_needed_fixture_to_stale_refresh_state():
    response = get_ingestion_job_status("refresh-needed-aapl")
    records = serialize_ingestion_job_response(response)

    assert records.ledger.job_category == "refresh"
    assert records.ledger.job_state == "stale"
    assert records.scope.support_status == "supported"
    assert records.ledger.generated_route == "/assets/AAPL"
    assert records.ledger.generated_output_available is True


def test_ledger_records_failed_sanitized_diagnostics_only():
    response = get_ingestion_job_status("ingest-on-demand-msft-failed")
    records = serialize_ingestion_job_response(response)

    assert records.ledger.job_state == "failed"
    assert len(records.diagnostics) == 1
    diagnostic = records.diagnostics[0]
    assert diagnostic.category == "validation_failed"
    assert diagnostic.error_code == "fixture_ingestion_failed"
    assert diagnostic.retryable is True
    assert diagnostic.stores_secret is False
    assert diagnostic.stores_user_text is False
    assert diagnostic.stores_provider_payload is False
    assert diagnostic.stores_raw_source_text is False


def test_on_demand_ledger_requires_explicit_pending_ingestion_approval():
    response = get_pre_cache_job_status("pre-cache-launch-voo")

    with pytest.raises(IngestionJobLedgerContractError, match="explicit pending-ingestion approval"):
        serialize_ingestion_job_response(response, category="approved_on_demand")


def test_blocked_or_unknown_ledger_rows_cannot_expose_generated_output():
    valid = serialize_ingestion_job_response(get_pre_cache_job_status("pre-cache-unsupported-tqqq"))
    bad_ledger = valid.ledger.model_copy(update={"generated_output_available": True})
    records = IngestionJobLedgerRecords(ledger=bad_ledger, scope=valid.scope)

    with pytest.raises(IngestionJobLedgerContractError, match="cannot expose generated output"):
        validate_ingestion_job_ledger_records(records)


def test_source_refs_and_diagnostics_do_not_store_raw_payloads_or_rejected_sources():
    valid = serialize_ingestion_job_response(request_ingestion("SPY"))
    bad_source_ref = IngestionJobLedgerSourceRefRow(
        job_id=valid.ledger.job_id,
        source_ref_id="source-ref-1",
        source_type="news",
        source_use_policy="rejected",
        allowlist_status="rejected",
        checksum="sha256:fixture",
    )
    bad_source_records = IngestionJobLedgerRecords(
        ledger=valid.ledger,
        scope=valid.scope,
        source_refs=[bad_source_ref],
    )

    with pytest.raises(IngestionJobLedgerContractError, match="Rejected sources"):
        validate_ingestion_job_ledger_records(bad_source_records)

    raw_diagnostic = IngestionJobLedgerDiagnosticRow(
        job_id=valid.ledger.job_id,
        diagnostic_id="diagnostic-raw",
        category="provider_unavailable",
        stores_provider_payload=True,
    )
    raw_diagnostic_records = IngestionJobLedgerRecords(
        ledger=valid.ledger,
        scope=valid.scope,
        diagnostics=[raw_diagnostic],
    )

    with pytest.raises(IngestionJobLedgerContractError, match="sanitized categories only"):
        validate_ingestion_job_ledger_records(raw_diagnostic_records)


def test_repository_imports_do_not_open_database_or_provider_paths():
    repository_source = (ROOT / "backend" / "repositories" / "ingestion_jobs.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "OPENROUTER",
        "api_key",
        "raw_text =",
    ]
    for marker in forbidden:
        assert marker not in repository_source
