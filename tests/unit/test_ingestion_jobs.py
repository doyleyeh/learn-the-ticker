from backend.data import ASSETS, ELIGIBLE_NOT_CACHED_ASSETS
from backend.ingestion import (
    build_local_ingestion_priority_plan,
    execute_ingestion_job_through_ledger,
    get_ingestion_job_status,
    get_pre_cache_job_status,
    request_ingestion,
    request_launch_universe_pre_cache,
    request_pre_cache_for_asset,
)
from backend.ingestion_worker import InMemoryIngestionWorkerLedger
from backend.models import IngestionJobResponse, PreCacheBatchResponse, PreCacheJobResponse
from backend.repositories.ingestion_jobs import IngestionJobLedgerRecords, serialize_ingestion_job_response


class FailingLedger:
    def get(self, job_id: str) -> IngestionJobLedgerRecords | None:
        raise RuntimeError("configured ledger unavailable")

    def save(self, records: IngestionJobLedgerRecords) -> None:
        raise RuntimeError("configured ledger unavailable")


def test_eligible_not_cached_asset_requests_deterministic_on_demand_job():
    first = request_ingestion("SPY")
    second = request_ingestion("spy")

    assert first == second
    validated = IngestionJobResponse.model_validate(first.model_dump(mode="json"))
    assert validated.ticker == "SPY"
    assert validated.asset_type.value == "etf"
    assert validated.job_type.value == "on_demand"
    assert validated.job_id == "ingest-on-demand-spy"
    assert validated.job_state.value == "pending"
    assert validated.worker_status.value == "queued"
    assert validated.status_url == "/api/jobs/ingest-on-demand-spy"
    assert validated.retryable is True
    assert validated.generated_route is None
    assert validated.capabilities.can_request_ingestion is True
    assert validated.capabilities.can_open_generated_page is False
    assert validated.capabilities.can_answer_chat is False
    assert validated.capabilities.can_compare is False


def test_configured_ledger_backs_on_demand_creation_status_and_worker_execution():
    ledger = InMemoryIngestionWorkerLedger()

    created = request_ingestion("SPY", ingestion_job_ledger=ledger)
    queued_status = get_ingestion_job_status("ingest-on-demand-spy", ingestion_job_ledger=ledger)
    execution = execute_ingestion_job_through_ledger("ingest-on-demand-spy", ingestion_job_ledger=ledger)
    completed_status = get_ingestion_job_status("ingest-on-demand-spy", ingestion_job_ledger=ledger)

    assert created.job_id == "ingest-on-demand-spy"
    assert queued_status.job_state.value == "pending"
    assert execution.summary.transitions == ["pending", "running", "succeeded"]
    assert completed_status.job_state.value == "succeeded"
    assert completed_status.generated_route is None
    assert completed_status.capabilities.can_open_generated_page is False
    assert completed_status.capabilities.can_answer_chat is False
    assert completed_status.capabilities.can_compare is False


def test_configured_ledger_backs_pre_cache_creation_status_and_worker_execution():
    ledger = InMemoryIngestionWorkerLedger()

    created = request_pre_cache_for_asset("SPY", ingestion_job_ledger=ledger)
    queued_status = get_pre_cache_job_status("pre-cache-launch-spy", ingestion_job_ledger=ledger)
    execution = execute_ingestion_job_through_ledger("pre-cache-launch-spy", ingestion_job_ledger=ledger)
    completed_status = get_pre_cache_job_status("pre-cache-launch-spy", ingestion_job_ledger=ledger)

    assert created.job_id == "pre-cache-launch-spy"
    assert queued_status.job_state.value == "pending"
    assert execution.summary.transitions == ["pending", "running", "succeeded"]
    assert completed_status.job_state.value == "succeeded"
    assert completed_status.generated_route is None
    assert completed_status.generated_output_available is False
    assert completed_status.capabilities.can_open_generated_page is False
    assert completed_status.capabilities.can_answer_chat is False
    assert completed_status.capabilities.can_compare is False


def test_configured_ledger_failure_falls_back_to_fixture_status():
    failing = FailingLedger()

    created = request_ingestion("SPY", ingestion_job_ledger=failing)
    status = get_ingestion_job_status("ingest-on-demand-spy", ingestion_job_ledger=failing)
    pre_cache = request_pre_cache_for_asset("SPY", ingestion_job_ledger=failing)
    pre_cache_status = get_pre_cache_job_status("pre-cache-launch-spy", ingestion_job_ledger=failing)

    assert created.job_state.value == "pending"
    assert status.job_state.value == "pending"
    assert pre_cache.job_state.value == "pending"
    assert pre_cache_status.job_state.value == "pending"


def test_invalid_configured_ledger_record_falls_back_to_matching_fixture():
    valid = serialize_ingestion_job_response(request_ingestion("SPY"))
    wrong_ticker = valid.model_copy(update={"ledger": valid.ledger.model_copy(update={"ticker": "QQQ"})})
    ledger = InMemoryIngestionWorkerLedger(records_by_job_id={"ingest-on-demand-spy": wrong_ticker})

    status = get_ingestion_job_status("ingest-on-demand-spy", ingestion_job_ledger=ledger)

    assert status.ticker == "SPY"
    assert status.job_state.value == "pending"


def test_all_launch_universe_eligible_not_cached_assets_get_stable_non_generated_jobs():
    for ticker, metadata in sorted(ELIGIBLE_NOT_CACHED_ASSETS.items()):
        response = request_ingestion(ticker)
        status = get_ingestion_job_status(f"ingest-on-demand-{ticker.lower()}")

        assert response.model_dump(mode="json") == status.model_dump(mode="json")
        assert response.ticker == ticker
        assert response.asset_type.value == metadata["asset_type"]
        assert response.job_type.value == "on_demand"
        assert response.job_id == f"ingest-on-demand-{ticker.lower()}"
        assert response.status_url == f"/api/jobs/ingest-on-demand-{ticker.lower()}"
        assert response.generated_route is None
        assert response.capabilities.can_open_generated_page is False
        assert response.capabilities.can_answer_chat is False
        assert response.capabilities.can_compare is False
        assert response.capabilities.can_request_ingestion is True
        assert "buy" not in response.message.lower()
        assert "sell" not in response.message.lower()
        assert "hold" not in response.message.lower()


def test_cached_supported_asset_returns_no_ingestion_needed_with_existing_capabilities():
    response = request_ingestion("AAPL")

    assert response.ticker == "AAPL"
    assert response.asset_type.value == "stock"
    assert response.job_id is None
    assert response.job_type is None
    assert response.job_state.value == "no_ingestion_needed"
    assert response.worker_status is None
    assert response.status_url is None
    assert response.generated_route == "/assets/AAPL"
    assert response.capabilities.can_open_generated_page is True
    assert response.capabilities.can_answer_chat is True
    assert response.capabilities.can_compare is True
    assert response.capabilities.can_request_ingestion is False


def test_unsupported_assets_do_not_create_jobs_or_generated_outputs():
    for ticker, expected_state in [
        ("BTC", "unsupported"),
        ("TQQQ", "unsupported"),
        ("SQQQ", "unsupported"),
        ("ARKK", "unsupported"),
        ("BND", "unsupported"),
        ("GLD", "unsupported"),
        ("AOR", "unsupported"),
    ]:
        response = request_ingestion(ticker)

        assert response.ticker == ticker
        assert response.asset_type.value == "unsupported"
        assert response.job_id is None
        assert response.job_type is None
        assert response.job_state.value == expected_state
        assert response.generated_route is None
        assert response.capabilities.can_open_generated_page is False
        assert response.capabilities.can_answer_chat is False
        assert response.capabilities.can_compare is False
        assert response.capabilities.can_request_ingestion is False


def test_unknown_asset_returns_unknown_without_invented_facts_or_job():
    response = request_ingestion("ZZZZ")

    assert response.ticker == "ZZZZ"
    assert response.asset_type.value == "unknown"
    assert response.job_id is None
    assert response.job_type is None
    assert response.job_state.value == "unknown"
    assert response.generated_route is None
    assert response.error_metadata is None
    assert response.capabilities.can_open_generated_page is False
    assert response.capabilities.can_answer_chat is False
    assert response.capabilities.can_compare is False
    assert "no asset facts are invented" in response.message.lower()


def test_out_of_scope_assets_do_not_create_ingestion_or_pre_cache_output():
    ingestion = request_ingestion("GME")
    pre_cache = request_pre_cache_for_asset("GME")
    pre_cache_status = get_pre_cache_job_status("pre-cache-out-of-scope-gme")
    etn_ingestion = request_ingestion("VXX")
    etn_pre_cache = request_pre_cache_for_asset("VXX")
    etn_pre_cache_status = get_pre_cache_job_status("pre-cache-out-of-scope-vxx")

    assert ingestion.ticker == "GME"
    assert ingestion.asset_type.value == "stock"
    assert ingestion.job_id is None
    assert ingestion.job_type is None
    assert ingestion.job_state.value == "out_of_scope"
    assert ingestion.generated_route is None
    assert ingestion.capabilities.can_open_generated_page is False
    assert ingestion.capabilities.can_answer_chat is False
    assert ingestion.capabilities.can_compare is False
    assert ingestion.capabilities.can_request_ingestion is False
    assert "outside the local Top-500 manifest" in ingestion.message

    assert pre_cache == pre_cache_status
    assert pre_cache.ticker == "GME"
    assert pre_cache.asset_type.value == "stock"
    assert pre_cache.job_state.value == "out_of_scope"
    assert pre_cache.generated_route is None
    assert pre_cache.generated_output_available is False
    assert pre_cache.citation_ids == []
    assert pre_cache.source_document_ids == []
    assert pre_cache.capabilities.can_open_generated_page is False
    assert pre_cache.capabilities.can_answer_chat is False
    assert pre_cache.capabilities.can_compare is False
    assert pre_cache.capabilities.can_request_ingestion is False

    assert etn_ingestion.ticker == "VXX"
    assert etn_ingestion.asset_type.value == "etf"
    assert etn_ingestion.job_id is None
    assert etn_ingestion.job_type is None
    assert etn_ingestion.job_state.value == "out_of_scope"
    assert etn_ingestion.generated_route is None
    assert etn_ingestion.capabilities.can_open_generated_page is False
    assert etn_ingestion.capabilities.can_answer_chat is False
    assert etn_ingestion.capabilities.can_compare is False
    assert etn_ingestion.capabilities.can_request_ingestion is False

    assert etn_pre_cache == etn_pre_cache_status
    assert etn_pre_cache.ticker == "VXX"
    assert etn_pre_cache.asset_type.value == "etf"
    assert etn_pre_cache.job_state.value == "out_of_scope"
    assert etn_pre_cache.generated_route is None
    assert etn_pre_cache.generated_output_available is False
    assert etn_pre_cache.citation_ids == []
    assert etn_pre_cache.source_document_ids == []
    assert etn_pre_cache.capabilities.can_open_generated_page is False
    assert etn_pre_cache.capabilities.can_answer_chat is False
    assert etn_pre_cache.capabilities.can_compare is False
    assert etn_pre_cache.capabilities.can_request_ingestion is False


def test_status_lookup_covers_running_succeeded_refresh_needed_failed_and_unavailable_states():
    cases = {
        "ingest-on-demand-msft": ("MSFT", "running", "running", None),
        "pre-cache-succeeded-voo": ("VOO", "succeeded", "succeeded", "/assets/VOO"),
        "refresh-needed-aapl": ("AAPL", "refresh_needed", None, "/assets/AAPL"),
        "ingest-on-demand-msft-failed": ("MSFT", "failed", "failed", None),
    }

    for job_id, (ticker, job_state, worker_status, generated_route) in cases.items():
        response = get_ingestion_job_status(job_id)
        actual_worker_status = response.worker_status.value if response.worker_status else None
        assert response.job_id == job_id
        assert response.ticker == ticker
        assert response.job_state.value == job_state
        assert actual_worker_status == worker_status
        assert response.status_url == f"/api/jobs/{job_id}"
        assert response.generated_route == generated_route

    failed = get_ingestion_job_status("ingest-on-demand-msft-failed")
    assert failed.error_metadata is not None
    assert failed.error_metadata.code == "fixture_ingestion_failed"
    assert failed.error_metadata.retryable is True

    missing = get_ingestion_job_status("missing-job")
    assert missing.ticker == "UNKNOWN"
    assert missing.asset_type.value == "unknown"
    assert missing.job_state.value == "unavailable"
    assert missing.generated_route is None


def test_launch_universe_pre_cache_batch_is_deterministic_and_covers_control_set():
    first = request_launch_universe_pre_cache()
    second = request_launch_universe_pre_cache()

    assert first == second
    validated = PreCacheBatchResponse.model_validate(first.model_dump(mode="json"))
    expected_tickers = {*ASSETS, *ELIGIBLE_NOT_CACHED_ASSETS}
    jobs_by_ticker = {job.ticker: job for job in validated.jobs}

    assert validated.batch_id == "pre-cache-launch-universe-v1"
    assert validated.status_url == "/api/admin/pre-cache/launch-universe"
    assert validated.deterministic is True
    assert validated.no_live_external_calls is True
    assert set(jobs_by_ticker) == expected_tickers
    assert validated.summary.total_launch_assets == len(expected_tickers)
    assert validated.summary.cached_or_already_available_assets == 3
    assert validated.summary.generated_output_available_assets == 3
    assert validated.summary.running_assets == 1
    assert validated.summary.failed_assets == 1
    assert validated.summary.unsupported_assets == 0
    assert validated.summary.unknown_assets == 0

    for ticker, job in jobs_by_ticker.items():
        assert job.batch_id == validated.batch_id
        assert job.job_type.value == "pre_cache"
        assert job.job_id == f"pre-cache-launch-{ticker.lower()}"
        assert job.status_url == f"/api/admin/pre-cache/jobs/pre-cache-launch-{ticker.lower()}"
        assert job.launch_group


def test_local_ingestion_priority_plan_is_review_only_batchable_and_manifest_ordered():
    first = build_local_ingestion_priority_plan(batch_size=5)
    second = build_local_ingestion_priority_plan(batch_size=5)

    assert first == second
    assert first["schema_version"] == "local-ingestion-priority-plan-v1"
    assert first["boundary"] == "local-ingestion-priority-planner-review-only-v1"
    assert first["review_only"] is True
    assert first["deterministic"] is True
    assert first["batchable"] is True
    assert first["resumable"] is True
    assert first["no_live_external_calls"] is True
    assert first["planner_started_ingestion"] is False
    assert first["sources_approved_by_planner"] is False
    assert first["manifests_promoted"] is False
    assert first["generated_output_cache_entries_written"] is False
    assert first["generated_output_unlocked_for_blocked_assets"] is False
    assert first["supported_etf_runtime_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert first["recognition_manifest_used_for_priority_order"] is False
    assert first["recognition_rows_unlock_generated_output"] is False
    assert first["top500_runtime_authority"] == "data/universes/us_common_stocks_top500.current.json"

    planned_tickers = [row["ticker"] for batch in first["batches"] for row in batch["items"]]
    assert planned_tickers[:3] == ["AAPL", "VOO", "QQQ"]
    assert planned_tickers[3:8] == ["SPY", "VGT", "SOXX", "VTI", "IVV"]
    assert planned_tickers[-9:] == ["MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"]
    assert "TQQQ" not in planned_tickers

    assert first["summary"] == {
        "planned_asset_count": 23,
        "batch_count": 6,
        "ready_to_inspect_count": 3,
        "blocked_or_not_ready_count": 20,
        "high_demand_pre_cache_count": 3,
        "supported_etf_manifest_count": 11,
        "top500_stock_manifest_count": 9,
        "blocked_diagnostic_count": 4,
    }
    ready_tickers = [row["ticker"] for row in first["ready_to_inspect"]]
    assert ready_tickers == ["AAPL", "VOO", "QQQ"]
    assert all(row["generated_output_unlocked_by_planner"] is False for row in first["blocked_or_not_ready"])
    assert all(batch["review_only"] is True and batch["can_start_ingestion"] is False for batch in first["batches"])
    assert {row["state"] for row in first["blocked_diagnostic_rows"]} == {
        "unsupported",
        "out_of_scope",
        "unknown",
        "unavailable",
    }
    state_counts = first["state_diagnostics"]["states"]
    for state in [
        "pending",
        "running",
        "succeeded",
        "failed",
        "unsupported",
        "out_of_scope",
        "unknown",
        "unavailable",
        "partial",
        "stale",
        "insufficient_evidence",
    ]:
        assert state in state_counts
    assert state_counts["stale"] == 0
    assert state_counts["insufficient_evidence"] == 20


def test_pre_cache_cached_assets_preserve_existing_generated_capabilities_only():
    batch = request_launch_universe_pre_cache()

    for ticker in ["AAPL", "VOO", "QQQ"]:
        job = next(job for job in batch.jobs if job.ticker == ticker)
        assert job.job_state.value == "succeeded"
        assert job.worker_status.value == "succeeded"
        assert job.generated_route == f"/assets/{ticker}"
        assert job.generated_output_available is True
        assert job.capabilities.can_open_generated_page is True
        assert job.capabilities.can_answer_chat is True
        assert job.capabilities.can_compare is True
        assert job.capabilities.can_request_ingestion is False


def test_pre_cache_eligible_not_cached_assets_have_no_generated_output_or_sources():
    batch = request_launch_universe_pre_cache()
    jobs_by_ticker = {job.ticker: job for job in batch.jobs}

    for ticker, metadata in ELIGIBLE_NOT_CACHED_ASSETS.items():
        job = jobs_by_ticker[ticker]
        assert job.asset_type.value == metadata["asset_type"]
        assert job.launch_group == metadata["launch_group"]
        assert job.generated_route is None
        assert job.generated_output_available is False
        assert job.citation_ids == []
        assert job.source_document_ids == []
        assert job.capabilities.can_open_generated_page is False
        assert job.capabilities.can_answer_chat is False
        assert job.capabilities.can_compare is False
        assert job.capabilities.can_request_ingestion is True
        assert "no generated" in job.message.lower()


def test_pre_cache_status_lookup_covers_required_deterministic_states():
    cases = {
        "pre-cache-launch-voo": ("VOO", "etf", "succeeded", "succeeded", "/assets/VOO", True),
        "pre-cache-launch-aapl": ("AAPL", "stock", "succeeded", "succeeded", "/assets/AAPL", True),
        "pre-cache-launch-spy": ("SPY", "etf", "pending", "queued", None, False),
        "pre-cache-launch-nvda": ("NVDA", "stock", "pending", "queued", None, False),
        "pre-cache-launch-msft": ("MSFT", "stock", "running", "running", None, False),
        "pre-cache-launch-amzn": ("AMZN", "stock", "failed", "failed", None, False),
        "pre-cache-unsupported-tqqq": ("TQQQ", "unsupported", "unsupported", None, None, False),
        "pre-cache-unsupported-arkk": ("ARKK", "unsupported", "unsupported", None, None, False),
        "pre-cache-out-of-scope-vxx": ("VXX", "etf", "out_of_scope", None, None, False),
        "pre-cache-unknown-zzzz": ("ZZZZ", "unknown", "unknown", None, None, False),
        "missing-pre-cache-job": ("UNKNOWN", "unknown", "unavailable", None, None, False),
    }

    for job_id, (ticker, asset_type, job_state, worker_status, generated_route, output_available) in cases.items():
        response = get_pre_cache_job_status(job_id)
        validated = PreCacheJobResponse.model_validate(response.model_dump(mode="json"))
        actual_worker_status = validated.worker_status.value if validated.worker_status else None
        assert validated.job_id == job_id
        assert validated.ticker == ticker
        assert validated.asset_type.value == asset_type
        assert validated.job_type.value == "pre_cache"
        assert validated.job_state.value == job_state
        assert actual_worker_status == worker_status
        assert validated.status_url == f"/api/admin/pre-cache/jobs/{job_id}"
        assert validated.generated_route == generated_route
        assert validated.generated_output_available is output_available

    failed = get_pre_cache_job_status("pre-cache-launch-amzn")
    assert failed.error_metadata is not None
    assert failed.error_metadata.code == "fixture_pre_cache_failed"
    assert failed.error_metadata.retryable is True


def test_pre_cache_asset_helper_returns_unsupported_out_of_scope_or_unknown_without_generated_output():
    for ticker, expected_type, expected_state in [
        ("TQQQ", "unsupported", "unsupported"),
        ("ARKK", "unsupported", "unsupported"),
        ("VXX", "etf", "out_of_scope"),
        ("BTC", "unsupported", "unsupported"),
        ("ZZZZ", "unknown", "unknown"),
    ]:
        response = request_pre_cache_for_asset(ticker)

        assert response.ticker == ticker
        assert response.asset_type.value == expected_type
        assert response.job_state.value == expected_state
        assert response.generated_route is None
        assert response.generated_output_available is False
        assert response.citation_ids == []
        assert response.source_document_ids == []
        assert response.capabilities.can_open_generated_page is False
        assert response.capabilities.can_answer_chat is False
        assert response.capabilities.can_compare is False
