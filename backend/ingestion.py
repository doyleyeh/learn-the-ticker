from __future__ import annotations

from backend.data import (
    ASSETS,
    ELIGIBLE_NOT_CACHED_ASSETS,
    OUT_OF_SCOPE_COMMON_STOCKS,
    STUB_TIMESTAMP,
    UNSUPPORTED_ASSETS,
    normalize_ticker,
)
from backend.models import (
    AssetIdentity,
    AssetType,
    IngestionCapabilities,
    IngestionErrorMetadata,
    IngestionJobResponse,
    IngestionJobState,
    IngestionJobType,
    IngestionWorkerStatus,
    PreCacheBatchResponse,
    PreCacheBatchSummary,
    PreCacheJobResponse,
)
from backend.repositories.ingestion_jobs import (
    IngestionJobLedgerRecords,
    IngestionLedgerJobState,
    validate_ingestion_job_ledger_records,
    serialize_ingestion_job_response,
)
from backend.ingestion_worker import (
    DeterministicIngestionWorker,
    IngestionWorkerExecutionResult,
    IngestionWorkerFixtureOutcome,
    IngestionWorkerLedgerBoundary,
    execute_ingestion_worker_record,
)

LAUNCH_PRE_CACHE_BATCH_ID = "pre-cache-launch-universe-v1"
LAUNCH_PRE_CACHE_STATUS_URL = "/api/admin/pre-cache/launch-universe"

_CACHED_LAUNCH_GROUPS: dict[str, str] = {
    "AAPL": "large_stock",
    "QQQ": "broad_etf",
    "VOO": "broad_etf",
}


def request_ingestion(
    ticker: str,
    *,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None = None,
) -> IngestionJobResponse:
    normalized = normalize_ticker(ticker)

    cached_asset = ASSETS.get(normalized)
    if cached_asset:
        identity: AssetIdentity = cached_asset["identity"]
        return IngestionJobResponse(
            ticker=identity.ticker,
            asset_type=identity.asset_type,
            job_state=IngestionJobState.no_ingestion_needed,
            generated_route=f"/assets/{identity.ticker}",
            capabilities=_capabilities(
                can_open_generated_page=True,
                can_answer_chat=True,
                can_compare=True,
                can_request_ingestion=False,
            ),
            message="This asset already has a local cached knowledge pack; no ingestion job is needed.",
        )

    eligible_asset = ELIGIBLE_NOT_CACHED_ASSETS.get(normalized)
    if eligible_asset:
        job_id = _on_demand_job_id(normalized)
        existing = _configured_ingestion_job_response(ingestion_job_ledger, job_id, expected_ticker=normalized)
        if existing:
            return existing
        job = _STATUS_FIXTURES.get(job_id)
        if job:
            return _save_ingestion_job_response(job.model_copy(deep=True), ingestion_job_ledger)
        return _save_ingestion_job_response(
            _eligible_on_demand_job_response(normalized, eligible_asset),
            ingestion_job_ledger,
        )

    if normalized in UNSUPPORTED_ASSETS:
        return IngestionJobResponse(
            ticker=normalized,
            asset_type=AssetType.unsupported,
            job_state=IngestionJobState.unsupported,
            retryable=False,
            capabilities=_capabilities(),
            message=f"{UNSUPPORTED_ASSETS[normalized]} No ingestion job was created.",
        )

    out_of_scope = OUT_OF_SCOPE_COMMON_STOCKS.get(normalized)
    if out_of_scope:
        return IngestionJobResponse(
            ticker=normalized,
            asset_type=AssetType(str(out_of_scope.get("asset_type") or AssetType.stock.value)),
            job_state=IngestionJobState.out_of_scope,
            retryable=False,
            capabilities=_capabilities(),
            message=f"{out_of_scope['reason']} No ingestion job was created.",
        )

    return IngestionJobResponse(
        ticker=normalized,
        asset_type=AssetType.unknown,
        job_state=IngestionJobState.unknown,
        retryable=False,
        capabilities=_capabilities(),
        message="Unknown or unavailable in local deterministic data; no asset facts are invented and no ingestion job was created.",
    )


def request_launch_universe_pre_cache(
    *,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None = None,
) -> PreCacheBatchResponse:
    jobs = [
        request_pre_cache_for_asset(ticker, ingestion_job_ledger=ingestion_job_ledger)
        for ticker in _launch_universe_tickers()
    ]
    return PreCacheBatchResponse(
        batch_id=LAUNCH_PRE_CACHE_BATCH_ID,
        status_url=LAUNCH_PRE_CACHE_STATUS_URL,
        created_at=STUB_TIMESTAMP,
        updated_at=STUB_TIMESTAMP,
        summary=_pre_cache_summary(jobs),
        jobs=jobs,
        message=(
            "Deterministic launch-universe pre-cache contract only. No workers, queues, provider calls, "
            "source facts, citations, or generated outputs are created by this request."
        ),
    )


def request_pre_cache_for_asset(
    ticker: str,
    *,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None = None,
) -> PreCacheJobResponse:
    normalized = normalize_ticker(ticker)
    cached_asset = ASSETS.get(normalized)
    if cached_asset or normalized in ELIGIBLE_NOT_CACHED_ASSETS:
        job_id = _pre_cache_job_id(normalized)
        existing = _configured_pre_cache_job_response(ingestion_job_ledger, job_id, expected_ticker=normalized)
        if existing:
            return existing
        return _save_pre_cache_job_response(_pre_cache_job_for_launch_ticker(normalized), ingestion_job_ledger)
    if normalized in UNSUPPORTED_ASSETS:
        return _save_pre_cache_job_response(_pre_cache_unsupported_job(normalized), ingestion_job_ledger)
    if normalized in OUT_OF_SCOPE_COMMON_STOCKS:
        return _save_pre_cache_job_response(_pre_cache_out_of_scope_job(normalized), ingestion_job_ledger)
    return _save_pre_cache_job_response(_pre_cache_unknown_job(normalized), ingestion_job_ledger)


def get_pre_cache_job_status(
    job_id: str,
    *,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None = None,
) -> PreCacheJobResponse:
    existing = _configured_pre_cache_job_response(ingestion_job_ledger, job_id)
    if existing:
        return existing

    for ticker in _launch_universe_tickers():
        expected = _pre_cache_job_id(ticker)
        if job_id == expected:
            return _pre_cache_job_for_launch_ticker(ticker)

    if job_id.startswith("pre-cache-unsupported-"):
        ticker = job_id.removeprefix("pre-cache-unsupported-").upper()
        if ticker in UNSUPPORTED_ASSETS:
            return _pre_cache_unsupported_job(ticker)

    if job_id.startswith("pre-cache-out-of-scope-"):
        ticker = job_id.removeprefix("pre-cache-out-of-scope-").upper()
        if ticker in OUT_OF_SCOPE_COMMON_STOCKS:
            return _pre_cache_out_of_scope_job(ticker)

    if job_id.startswith("pre-cache-unknown-"):
        ticker = job_id.removeprefix("pre-cache-unknown-").upper()
        return _pre_cache_unknown_job(ticker)

    return PreCacheJobResponse(
        ticker="UNKNOWN",
        asset_type=AssetType.unknown,
        job_id=job_id,
        job_state=IngestionJobState.unavailable,
        status_url=f"/api/admin/pre-cache/jobs/{job_id}",
        retryable=False,
        capabilities=_capabilities(),
        generated_output_available=False,
        message="No deterministic local pre-cache job fixture matched this job ID.",
    )


def get_ingestion_job_status(
    job_id: str,
    *,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None = None,
) -> IngestionJobResponse:
    existing = _configured_ingestion_job_response(ingestion_job_ledger, job_id)
    if existing:
        return existing

    job = _STATUS_FIXTURES.get(job_id)
    if job:
        return job.model_copy(deep=True)

    if job_id.startswith("ingest-on-demand-"):
        ticker = job_id.removeprefix("ingest-on-demand-").upper()
        eligible_asset = ELIGIBLE_NOT_CACHED_ASSETS.get(ticker)
        if eligible_asset:
            return _eligible_on_demand_job_response(ticker, eligible_asset)

    return IngestionJobResponse(
        ticker="UNKNOWN",
        asset_type=AssetType.unknown,
        job_id=job_id,
        job_state=IngestionJobState.unavailable,
        status_url=f"/api/jobs/{job_id}",
        retryable=False,
        capabilities=_capabilities(),
        message="No deterministic local ingestion job fixture matched this job ID.",
    )


def execute_ingestion_job_through_ledger(
    job_id: str,
    *,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None = None,
    fixture_outcome: IngestionWorkerFixtureOutcome | None = None,
) -> IngestionWorkerExecutionResult:
    if ingestion_job_ledger is not None:
        try:
            return DeterministicIngestionWorker(
                ledger_boundary=ingestion_job_ledger,
                fixture_outcomes={job_id: fixture_outcome} if fixture_outcome else {},
            ).execute(job_id)
        except Exception:
            pass

    fallback_records = _fallback_records_for_worker(job_id)
    return execute_ingestion_worker_record(fallback_records, fixture_outcome=fixture_outcome)


def _configured_ingestion_job_response(
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None,
    job_id: str,
    *,
    expected_ticker: str | None = None,
) -> IngestionJobResponse | None:
    records = _configured_records(ingestion_job_ledger, job_id, expected_ticker=expected_ticker)
    if records is None:
        return None
    return _ingestion_response_from_ledger_records(records)


def _configured_pre_cache_job_response(
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None,
    job_id: str,
    *,
    expected_ticker: str | None = None,
) -> PreCacheJobResponse | None:
    records = _configured_records(ingestion_job_ledger, job_id, expected_ticker=expected_ticker)
    if records is None or records.ledger.job_category != "manual_pre_cache":
        return None
    return _pre_cache_response_from_ledger_records(records)


def _configured_records(
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None,
    job_id: str,
    *,
    expected_ticker: str | None = None,
) -> IngestionJobLedgerRecords | None:
    if ingestion_job_ledger is None:
        return None
    try:
        records = ingestion_job_ledger.get(job_id)
        if records is None:
            return None
        validate_ingestion_job_ledger_records(records)
    except Exception:
        return None
    if records.ledger.job_id != job_id:
        return None
    if expected_ticker and records.ledger.ticker != expected_ticker:
        return None
    return records


def _save_ingestion_job_response(
    response: IngestionJobResponse,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None,
) -> IngestionJobResponse:
    if ingestion_job_ledger is None or not response.job_id:
        return response
    try:
        ingestion_job_ledger.save(serialize_ingestion_job_response(response))
    except Exception:
        return response
    return response


def _save_pre_cache_job_response(
    response: PreCacheJobResponse,
    ingestion_job_ledger: IngestionWorkerLedgerBoundary | None,
) -> PreCacheJobResponse:
    if ingestion_job_ledger is None:
        return response
    try:
        ingestion_job_ledger.save(serialize_ingestion_job_response(response))
    except Exception:
        return response
    return response


def _fallback_records_for_worker(job_id: str) -> IngestionJobLedgerRecords:
    if job_id.startswith("pre-cache-"):
        return serialize_ingestion_job_response(get_pre_cache_job_status(job_id))
    return serialize_ingestion_job_response(get_ingestion_job_status(job_id))


def _ingestion_response_from_ledger_records(records: IngestionJobLedgerRecords) -> IngestionJobResponse:
    ledger = records.ledger
    return _job_response(
        ticker=ledger.ticker,
        asset_type=AssetType(ledger.asset_type),
        job_type=_job_type_for_ledger_category(ledger.job_category),
        job_id=ledger.job_id,
        job_state=_response_state_for_ledger_state(ledger.job_state),
        worker_status=_response_worker_status(ledger.worker_status),
        retryable=ledger.retryable,
        capabilities=_capabilities(
            can_open_generated_page=ledger.can_open_generated_page,
            can_answer_chat=ledger.can_answer_chat,
            can_compare=ledger.can_compare,
            can_request_ingestion=ledger.can_request_ingestion,
        ),
        message=_ledger_message(records),
        started_at=ledger.started_at,
        finished_at=ledger.finished_at,
        error_metadata=_error_metadata_from_diagnostics(records),
        generated_route=ledger.generated_route,
    ).model_copy(
        update={
            "created_at": ledger.created_at,
            "updated_at": ledger.updated_at,
            "status_url": ledger.status_url or f"/api/jobs/{ledger.job_id}",
        }
    )


def _pre_cache_response_from_ledger_records(records: IngestionJobLedgerRecords) -> PreCacheJobResponse:
    ledger = records.ledger
    return _pre_cache_job_response(
        ticker=ledger.ticker,
        name=records.scope.asset_name or ledger.ticker,
        asset_type=AssetType(ledger.asset_type),
        launch_group=ledger.launch_group,
        job_id=ledger.job_id,
        job_state=_response_state_for_ledger_state(ledger.job_state),
        worker_status=_response_worker_status(ledger.worker_status),
        retryable=ledger.retryable,
        capabilities=_capabilities(
            can_open_generated_page=ledger.can_open_generated_page,
            can_answer_chat=ledger.can_answer_chat,
            can_compare=ledger.can_compare,
            can_request_ingestion=ledger.can_request_ingestion,
        ),
        message=_ledger_message(records),
        started_at=ledger.started_at,
        finished_at=ledger.finished_at,
        error_metadata=_error_metadata_from_diagnostics(records),
        generated_route=ledger.generated_route,
        generated_output_available=ledger.generated_output_available,
    ).model_copy(
        update={
            "batch_id": ledger.batch_id or LAUNCH_PRE_CACHE_BATCH_ID,
            "created_at": ledger.created_at,
            "updated_at": ledger.updated_at,
            "status_url": ledger.status_url or f"/api/admin/pre-cache/jobs/{ledger.job_id}",
        }
    )


def _response_state_for_ledger_state(job_state: str) -> IngestionJobState:
    if job_state == IngestionLedgerJobState.stale.value:
        return IngestionJobState.refresh_needed
    return IngestionJobState(job_state)


def _response_worker_status(worker_status: str | None) -> IngestionWorkerStatus | None:
    if not worker_status:
        return None
    try:
        return IngestionWorkerStatus(worker_status)
    except ValueError:
        return None


def _job_type_for_ledger_category(job_category: str) -> IngestionJobType:
    if job_category == "manual_pre_cache":
        return IngestionJobType.pre_cache
    if job_category == "approved_on_demand":
        return IngestionJobType.on_demand
    if job_category == "refresh":
        return IngestionJobType.refresh
    return IngestionJobType.repair


def _error_metadata_from_diagnostics(records: IngestionJobLedgerRecords) -> IngestionErrorMetadata | None:
    if not records.diagnostics:
        return None
    diagnostic = records.diagnostics[-1]
    return IngestionErrorMetadata(
        code=diagnostic.error_code or diagnostic.category,
        message=diagnostic.sanitized_message or "Sanitized deterministic ingestion diagnostic.",
        retryable=diagnostic.retryable,
    )


def _ledger_message(records: IngestionJobLedgerRecords) -> str:
    message = records.ledger.compact_metadata.get("message")
    if isinstance(message, str) and message:
        return message
    return (
        "Deterministic ingestion ledger record. No live provider call, source snapshot, "
        "knowledge-pack write, generated page, chat answer, comparison, risk summary, or generated-output cache write was created."
    )


def _launch_universe_tickers() -> list[str]:
    return sorted({*ASSETS, *ELIGIBLE_NOT_CACHED_ASSETS})


def _pre_cache_job_for_launch_ticker(ticker: str) -> PreCacheJobResponse:
    cached_asset = ASSETS.get(ticker)
    if cached_asset:
        identity: AssetIdentity = cached_asset["identity"]
        return _pre_cache_job_response(
            ticker=identity.ticker,
            name=identity.name,
            asset_type=identity.asset_type,
            launch_group=_CACHED_LAUNCH_GROUPS[identity.ticker],
            job_state=IngestionJobState.succeeded,
            worker_status=IngestionWorkerStatus.succeeded,
            retryable=False,
            generated_route=f"/assets/{identity.ticker}",
            capabilities=_capabilities(
                can_open_generated_page=True,
                can_answer_chat=True,
                can_compare=True,
                can_request_ingestion=False,
            ),
            generated_output_available=True,
            finished_at=STUB_TIMESTAMP,
            message=(
                f"{identity.ticker} is already available from the existing local cached knowledge pack. "
                "The pre-cache contract preserves its generated page, chat, and comparison capabilities."
            ),
        )

    metadata = ELIGIBLE_NOT_CACHED_ASSETS[ticker]
    if ticker == "MSFT":
        return _pre_cache_job_response(
            ticker=ticker,
            name=str(metadata["name"]),
            asset_type=AssetType(str(metadata["asset_type"])),
            launch_group=str(metadata["launch_group"]),
            job_state=IngestionJobState.running,
            worker_status=IngestionWorkerStatus.running,
            retryable=False,
            capabilities=_capabilities(can_request_ingestion=True),
            started_at=STUB_TIMESTAMP,
            message=(
                "MSFT has a deterministic running pre-cache fixture. No generated page, chat answer, "
                "comparison, citations, source documents, or reusable generated-output cache hit is available yet."
            ),
        )
    if ticker == "AMZN":
        return _pre_cache_job_response(
            ticker=ticker,
            name=str(metadata["name"]),
            asset_type=AssetType(str(metadata["asset_type"])),
            launch_group=str(metadata["launch_group"]),
            job_state=IngestionJobState.failed,
            worker_status=IngestionWorkerStatus.failed,
            retryable=True,
            capabilities=_capabilities(can_request_ingestion=True),
            started_at=STUB_TIMESTAMP,
            finished_at=STUB_TIMESTAMP,
            error_metadata=IngestionErrorMetadata(
                code="fixture_pre_cache_failed",
                message="Deterministic fixture for a failed pre-cache job; no provider call was attempted.",
                retryable=True,
            ),
            message=(
                "AMZN has a deterministic failed pre-cache fixture. No generated page, chat answer, "
                "comparison, citations, source documents, or reusable generated-output cache hit is available."
            ),
        )

    return _pre_cache_job_response(
        ticker=ticker,
        name=str(metadata["name"]),
        asset_type=AssetType(str(metadata["asset_type"])),
        launch_group=str(metadata["launch_group"]),
        job_state=IngestionJobState.pending,
        worker_status=IngestionWorkerStatus.queued,
        retryable=True,
        capabilities=_capabilities(can_request_ingestion=True),
        message=(
            f"{ticker} is planned for deterministic fixture-backed launch pre-cache. No generated page, chat answer, "
            "comparison, citations, source documents, or reusable generated-output cache hit is available yet."
        ),
    )


def _pre_cache_unsupported_job(ticker: str) -> PreCacheJobResponse:
    return _pre_cache_job_response(
        ticker=ticker,
        name=ticker,
        asset_type=AssetType.unsupported,
        launch_group="unsupported",
        job_id=f"pre-cache-unsupported-{ticker.lower()}",
        job_state=IngestionJobState.unsupported,
        worker_status=None,
        retryable=False,
        capabilities=_capabilities(),
        message=f"{UNSUPPORTED_ASSETS[ticker]} No pre-cache job can create generated output for this asset.",
    )


def _pre_cache_out_of_scope_job(ticker: str) -> PreCacheJobResponse:
    metadata = OUT_OF_SCOPE_COMMON_STOCKS[ticker]
    return _pre_cache_job_response(
        ticker=ticker,
        name=str(metadata["name"]),
        asset_type=AssetType(str(metadata.get("asset_type") or AssetType.stock.value)),
        launch_group="out_of_scope_common_stock" if metadata.get("asset_type") == "stock" else "out_of_scope_etf_like_product",
        job_id=f"pre-cache-out-of-scope-{ticker.lower()}",
        job_state=IngestionJobState.out_of_scope,
        worker_status=None,
        retryable=False,
        capabilities=_capabilities(),
        message=f"{metadata['reason']} No pre-cache job can create generated output for this asset.",
    )


def _pre_cache_unknown_job(ticker: str) -> PreCacheJobResponse:
    return _pre_cache_job_response(
        ticker=ticker,
        name=ticker,
        asset_type=AssetType.unknown,
        launch_group="unknown",
        job_id=f"pre-cache-unknown-{ticker.lower()}",
        job_state=IngestionJobState.unknown,
        worker_status=None,
        retryable=False,
        capabilities=_capabilities(),
        message=(
            "Unknown or unavailable in local deterministic data; no pre-cache source facts, citations, "
            "generated output, or reusable generated-output cache hit was created."
        ),
    )


def _pre_cache_summary(jobs: list[PreCacheJobResponse]) -> PreCacheBatchSummary:
    return PreCacheBatchSummary(
        total_launch_assets=len(jobs),
        cached_or_already_available_assets=sum(1 for job in jobs if job.generated_output_available),
        queued_or_pending_assets=sum(
            1
            for job in jobs
            if job.job_state is IngestionJobState.pending or job.worker_status is IngestionWorkerStatus.queued
        ),
        running_assets=sum(1 for job in jobs if job.job_state is IngestionJobState.running),
        failed_assets=sum(1 for job in jobs if job.job_state is IngestionJobState.failed),
        unsupported_assets=sum(1 for job in jobs if job.job_state is IngestionJobState.unsupported),
        unknown_assets=sum(1 for job in jobs if job.job_state is IngestionJobState.unknown),
        generated_output_available_assets=sum(1 for job in jobs if job.generated_output_available),
    )


def _pre_cache_job_id(ticker: str) -> str:
    return f"pre-cache-launch-{ticker.lower()}"


def _pre_cache_job_response(
    *,
    ticker: str,
    name: str | None,
    asset_type: AssetType,
    launch_group: str | None,
    job_state: IngestionJobState,
    worker_status: IngestionWorkerStatus | None,
    retryable: bool,
    capabilities: IngestionCapabilities,
    message: str,
    job_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    error_metadata: IngestionErrorMetadata | None = None,
    generated_route: str | None = None,
    generated_output_available: bool = False,
) -> PreCacheJobResponse:
    job_id = job_id or _pre_cache_job_id(ticker)
    return PreCacheJobResponse(
        batch_id=LAUNCH_PRE_CACHE_BATCH_ID,
        ticker=ticker,
        name=name,
        asset_type=asset_type,
        launch_group=launch_group,
        job_id=job_id,
        job_state=job_state,
        worker_status=worker_status,
        created_at=STUB_TIMESTAMP,
        updated_at=finished_at or started_at or STUB_TIMESTAMP,
        started_at=started_at,
        finished_at=finished_at,
        status_url=f"/api/admin/pre-cache/jobs/{job_id}",
        retryable=retryable,
        error_metadata=error_metadata,
        generated_route=generated_route,
        capabilities=capabilities,
        generated_output_available=generated_output_available,
        message=message,
    )


def _on_demand_job_id(ticker: str) -> str:
    return f"ingest-on-demand-{ticker.lower()}"


def _eligible_on_demand_job_response(ticker: str, metadata: dict[str, str | list[str] | None]) -> IngestionJobResponse:
    return _job_response(
        ticker=ticker,
        asset_type=AssetType(str(metadata["asset_type"])),
        job_type=IngestionJobType.on_demand,
        job_id=_on_demand_job_id(ticker),
        job_state=IngestionJobState.pending,
        worker_status=IngestionWorkerStatus.queued,
        retryable=True,
        capabilities=_capabilities(can_request_ingestion=True),
        message=(
            f"{ticker} is eligible-not-cached and queued for deterministic fixture-backed on-demand ingestion. "
            "No generated asset page, chat answer, or comparison is available yet."
        ),
    )


def _capabilities(
    *,
    can_open_generated_page: bool = False,
    can_answer_chat: bool = False,
    can_compare: bool = False,
    can_request_ingestion: bool = False,
) -> IngestionCapabilities:
    return IngestionCapabilities(
        can_open_generated_page=can_open_generated_page,
        can_answer_chat=can_answer_chat,
        can_compare=can_compare,
        can_request_ingestion=can_request_ingestion,
    )


def _job_response(
    *,
    ticker: str,
    asset_type: AssetType,
    job_type: IngestionJobType,
    job_id: str,
    job_state: IngestionJobState,
    worker_status: IngestionWorkerStatus | None,
    retryable: bool,
    capabilities: IngestionCapabilities,
    message: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    error_metadata: IngestionErrorMetadata | None = None,
    generated_route: str | None = None,
) -> IngestionJobResponse:
    return IngestionJobResponse(
        ticker=ticker,
        asset_type=asset_type,
        job_type=job_type,
        job_id=job_id,
        job_state=job_state,
        worker_status=worker_status,
        created_at=STUB_TIMESTAMP,
        updated_at=finished_at or started_at or STUB_TIMESTAMP,
        started_at=started_at,
        finished_at=finished_at,
        status_url=f"/api/jobs/{job_id}",
        retryable=retryable,
        error_metadata=error_metadata,
        generated_route=generated_route,
        capabilities=capabilities,
        message=message,
    )


_STATUS_FIXTURES: dict[str, IngestionJobResponse] = {
    "ingest-on-demand-spy": _job_response(
        ticker="SPY",
        asset_type=AssetType.etf,
        job_type=IngestionJobType.on_demand,
        job_id="ingest-on-demand-spy",
        job_state=IngestionJobState.pending,
        worker_status=IngestionWorkerStatus.queued,
        retryable=True,
        capabilities=_capabilities(can_request_ingestion=True),
        message=(
            "SPY is queued for deterministic fixture-backed on-demand ingestion. "
            "No generated asset output is available yet."
        ),
    ),
    "ingest-on-demand-msft": _job_response(
        ticker="MSFT",
        asset_type=AssetType.stock,
        job_type=IngestionJobType.on_demand,
        job_id="ingest-on-demand-msft",
        job_state=IngestionJobState.running,
        worker_status=IngestionWorkerStatus.running,
        retryable=False,
        capabilities=_capabilities(can_request_ingestion=True),
        started_at=STUB_TIMESTAMP,
        message=(
            "MSFT has a deterministic running on-demand ingestion fixture. "
            "Generated pages, chat, and comparisons remain unavailable until success."
        ),
    ),
    "pre-cache-succeeded-voo": _job_response(
        ticker="VOO",
        asset_type=AssetType.etf,
        job_type=IngestionJobType.pre_cache,
        job_id="pre-cache-succeeded-voo",
        job_state=IngestionJobState.succeeded,
        worker_status=IngestionWorkerStatus.succeeded,
        retryable=False,
        capabilities=_capabilities(
            can_open_generated_page=True,
            can_answer_chat=True,
            can_compare=True,
            can_request_ingestion=False,
        ),
        finished_at=STUB_TIMESTAMP,
        generated_route="/assets/VOO",
        message="VOO has a succeeded pre-cache fixture and can use its existing local generated outputs.",
    ),
    "refresh-needed-aapl": _job_response(
        ticker="AAPL",
        asset_type=AssetType.stock,
        job_type=IngestionJobType.refresh,
        job_id="refresh-needed-aapl",
        job_state=IngestionJobState.refresh_needed,
        worker_status=None,
        retryable=True,
        capabilities=_capabilities(
            can_open_generated_page=True,
            can_answer_chat=True,
            can_compare=True,
            can_request_ingestion=True,
        ),
        generated_route="/assets/AAPL",
        message="AAPL has cached local output, but this fixture marks it as needing a future refresh job.",
    ),
    "ingest-on-demand-msft-failed": _job_response(
        ticker="MSFT",
        asset_type=AssetType.stock,
        job_type=IngestionJobType.on_demand,
        job_id="ingest-on-demand-msft-failed",
        job_state=IngestionJobState.failed,
        worker_status=IngestionWorkerStatus.failed,
        retryable=True,
        capabilities=_capabilities(can_request_ingestion=True),
        started_at=STUB_TIMESTAMP,
        finished_at=STUB_TIMESTAMP,
        error_metadata=IngestionErrorMetadata(
            code="fixture_ingestion_failed",
            message="Deterministic fixture for a failed ingestion job; no provider call was attempted.",
            retryable=True,
        ),
        message=(
            "MSFT has a deterministic failed ingestion fixture. "
            "No generated asset output is available from this failed job."
        ),
    ),
}
