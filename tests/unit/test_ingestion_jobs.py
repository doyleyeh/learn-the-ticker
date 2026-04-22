from backend.ingestion import get_ingestion_job_status, request_ingestion
from backend.models import IngestionJobResponse


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
    for ticker, expected_state in [("BTC", "unsupported"), ("TQQQ", "unsupported"), ("SQQQ", "unsupported")]:
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
