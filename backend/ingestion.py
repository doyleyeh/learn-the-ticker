from __future__ import annotations

from backend.data import (
    ASSETS,
    ELIGIBLE_NOT_CACHED_ASSETS,
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
)


def request_ingestion(ticker: str) -> IngestionJobResponse:
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
        job = _STATUS_FIXTURES.get(_on_demand_job_id(normalized))
        if job:
            return job.model_copy(deep=True)

    if normalized in UNSUPPORTED_ASSETS:
        return IngestionJobResponse(
            ticker=normalized,
            asset_type=AssetType.unsupported,
            job_state=IngestionJobState.unsupported,
            retryable=False,
            capabilities=_capabilities(),
            message=f"{UNSUPPORTED_ASSETS[normalized]} No ingestion job was created.",
        )

    return IngestionJobResponse(
        ticker=normalized,
        asset_type=AssetType.unknown,
        job_state=IngestionJobState.unknown,
        retryable=False,
        capabilities=_capabilities(),
        message="Unknown or unavailable in local deterministic data; no asset facts are invented and no ingestion job was created.",
    )


def get_ingestion_job_status(job_id: str) -> IngestionJobResponse:
    job = _STATUS_FIXTURES.get(job_id)
    if job:
        return job.model_copy(deep=True)

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


def _on_demand_job_id(ticker: str) -> str:
    return f"ingest-on-demand-{ticker.lower()}"


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
