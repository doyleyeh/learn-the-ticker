from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from pydantic import BaseModel

from backend.ingestion import (
    get_ingestion_job_status,
    get_pre_cache_job_status,
    request_ingestion,
    request_launch_universe_pre_cache,
    request_pre_cache_for_asset,
)
from backend.ingestion_worker import DeterministicIngestionWorker
from backend.persistence import BackendReadDependencies, build_backend_read_dependencies_from_local_durable_config


PENDING_JOB_STATES = {"queued", "pending", "running", "refresh_needed"}


class CloudJobConfigurationError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = run_from_args(args)
    except CloudJobConfigurationError as exc:
        print(json.dumps({"status": "blocked", "reason_code": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason_code": "cloud_job_execution_failed",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(payload, sort_keys=True))
    return 0


def run_from_args(args: argparse.Namespace) -> dict[str, Any]:
    dependencies = build_backend_read_dependencies_from_local_durable_config()
    ledger = dependencies.reader("ingestion_job_ledger")
    require_durable = args.require_durable or (
        _is_production() and not args.allow_fixture_fallback
    )
    if require_durable and ledger is None:
        raise CloudJobConfigurationError("durable_ingestion_job_ledger_required")

    if args.operation == "status":
        return _status_payload(args.job_id, ledger=ledger)
    if args.operation == "run-job":
        if args.job_id is None:
            raise CloudJobConfigurationError("job_id_required")
        return _execute_job_payload(args.job_id, dependencies=dependencies, allow_fixture_fallback=args.allow_fixture_fallback)
    if args.operation == "retry-job":
        if args.job_id is None:
            raise CloudJobConfigurationError("job_id_required")
        return _retry_job_payload(args.job_id, dependencies=dependencies)
    if args.operation == "run-ingestion":
        if args.ticker is None:
            raise CloudJobConfigurationError("ticker_required")
        requested = request_ingestion(args.ticker, ingestion_job_ledger=ledger)
        return _maybe_execute_requested_job(
            requested,
            dependencies=dependencies,
            allow_fixture_fallback=args.allow_fixture_fallback,
        )
    if args.operation == "run-pre-cache":
        if args.ticker is None:
            raise CloudJobConfigurationError("ticker_required")
        requested = request_pre_cache_for_asset(args.ticker, ingestion_job_ledger=ledger)
        return _maybe_execute_requested_job(
            requested,
            dependencies=dependencies,
            allow_fixture_fallback=args.allow_fixture_fallback,
        )
    if args.operation == "plan-launch-pre-cache":
        batch = request_launch_universe_pre_cache(ingestion_job_ledger=ledger)
        return {
            "status": "planned",
            "operation": args.operation,
            "durable_ledger_configured": ledger is not None,
            "executed_worker": False,
            "batch": _jsonable(batch),
        }
    raise CloudJobConfigurationError("unknown_operation")


def _maybe_execute_requested_job(
    requested: BaseModel,
    *,
    dependencies: BackendReadDependencies,
    allow_fixture_fallback: bool,
) -> dict[str, Any]:
    job_id = getattr(requested, "job_id", None)
    job_state = _state_value(getattr(requested, "job_state", None))
    if job_id is None or job_state not in PENDING_JOB_STATES:
        return {
            "status": "no_worker_execution_needed",
            "operation": "request",
            "durable_ledger_configured": dependencies.reader("ingestion_job_ledger") is not None,
            "executed_worker": False,
            "requested": _jsonable(requested),
        }
    execution = _execute_job(job_id, dependencies=dependencies, allow_fixture_fallback=allow_fixture_fallback)
    return {
        "status": execution.summary.terminal_state,
        "operation": "request_and_run",
        "durable_ledger_configured": dependencies.reader("ingestion_job_ledger") is not None,
        "executed_worker": True,
        "requested": _jsonable(requested),
        "execution_summary": _jsonable(execution.summary),
    }


def _execute_job_payload(
    job_id: str,
    *,
    dependencies: BackendReadDependencies,
    allow_fixture_fallback: bool,
) -> dict[str, Any]:
    execution = _execute_job(job_id, dependencies=dependencies, allow_fixture_fallback=allow_fixture_fallback)
    return {
        "status": execution.summary.terminal_state,
        "operation": "run-job",
        "durable_ledger_configured": dependencies.reader("ingestion_job_ledger") is not None,
        "executed_worker": True,
        "execution_summary": _jsonable(execution.summary),
    }


def _retry_job_payload(
    job_id: str,
    *,
    dependencies: BackendReadDependencies,
) -> dict[str, Any]:
    ledger = dependencies.reader("ingestion_job_ledger")
    if ledger is None:
        raise CloudJobConfigurationError("durable_ingestion_job_ledger_required")
    retried = DeterministicIngestionWorker(ledger_boundary=ledger).retry(job_id)
    return {
        "status": retried.ledger.job_state,
        "operation": "retry-job",
        "durable_ledger_configured": True,
        "executed_worker": False,
        "ledger_record": _jsonable(retried.ledger),
    }


def _execute_job(
    job_id: str,
    *,
    dependencies: BackendReadDependencies,
    allow_fixture_fallback: bool,
):
    ledger = dependencies.reader("ingestion_job_ledger")
    if ledger is not None:
        return DeterministicIngestionWorker(ledger_boundary=ledger).execute(job_id)
    if not allow_fixture_fallback:
        raise CloudJobConfigurationError("durable_ingestion_job_ledger_required")
    from backend.ingestion import execute_ingestion_job_through_ledger

    return execute_ingestion_job_through_ledger(job_id)


def _status_payload(job_id: str | None, *, ledger: Any | None) -> dict[str, Any]:
    if job_id is None:
        raise CloudJobConfigurationError("job_id_required")
    if job_id.startswith("pre-cache-"):
        status = get_pre_cache_job_status(job_id, ingestion_job_ledger=ledger)
    else:
        status = get_ingestion_job_status(job_id, ingestion_job_ledger=ledger)
    return {
        "status": "inspected",
        "operation": "status",
        "durable_ledger_configured": ledger is not None,
        "executed_worker": False,
        "job": _jsonable(status),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Learn the Ticker Cloud Run Job operations.")
    parser.add_argument(
        "operation",
        choices=("status", "run-job", "retry-job", "run-ingestion", "run-pre-cache", "plan-launch-pre-cache"),
    )
    parser.add_argument("--ticker")
    parser.add_argument("--job-id")
    parser.add_argument("--require-durable", action="store_true")
    parser.add_argument("--allow-fixture-fallback", action="store_true")
    return parser


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _state_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _is_production() -> bool:
    return (os.environ.get("APP_ENV") or "").strip().lower() == "production"


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke.
    raise SystemExit(main())
