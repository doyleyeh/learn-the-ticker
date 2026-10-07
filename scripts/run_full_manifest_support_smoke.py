#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.data import (
    ASSETS,
    TOP500_STOCK_UNIVERSE_MANIFEST_PATH,
    load_top500_stock_universe_manifest,
    top500_stock_universe_entry,
)
from backend.etf_universe import (
    RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH,
    SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH,
    can_generate_output_for_etf_entry,
    load_recognition_etf_universe_manifest,
    load_supported_etf_universe_manifest,
)
from backend.models import ETFUniverseSupportState, SearchSupportClassification
from backend.search import search_assets


SCHEMA_VERSION = "full-manifest-support-smoke-v1"
STOCK_AUTHORITY = "data/universes/us_common_stocks_top500.current.json"
SUPPORTED_ETF_AUTHORITY = "data/universes/us_equity_etfs_supported.current.json"
RECOGNITION_ETF_AUTHORITY = "data/universes/us_etp_recognition.current.json"
GENERATED_SURFACES = (
    "asset_pages",
    "chat_answers",
    "comparisons",
    "weekly_news_focus",
    "ai_comprehensive_analysis",
    "exports",
    "generated_risk_summaries",
    "generated_output_cache_entries",
)
NO_LIVE_ENV = {
    "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "false",
    "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "false",
    "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "false",
    "MARKET_NEWS_FETCH_ENABLED": "false",
    "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "false",
    "LLM_LIVE_GENERATION_ENABLED": "false",
}


def run_full_manifest_support_smoke(*, root: Path = ROOT) -> dict[str, Any]:
    """Run a deterministic manifest-backed support/classification smoke."""

    with _deterministic_no_live_env():
        stock_manifest = load_top500_stock_universe_manifest()
        supported_etf_manifest = load_supported_etf_universe_manifest()
        recognition_etf_manifest = load_recognition_etf_universe_manifest()

        failures: list[dict[str, Any]] = []
        stock_rows = [_stock_row(entry, failures) for entry in stock_manifest.entries]
        supported_etf_rows = [_supported_etf_row(entry, failures) for entry in supported_etf_manifest.entries]
        recognition_rows = [_recognition_etf_row(entry, failures) for entry in recognition_etf_manifest.entries]

    rows = [*stock_rows, *supported_etf_rows, *recognition_rows]
    counts = _counts(rows)
    status = "pass" if not failures else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason_code": "full_manifest_support_smoke_passed"
        if status == "pass"
        else "full_manifest_support_smoke_failed",
        "deterministic": True,
        "normal_ci_requires_live_calls": False,
        "live_provider_calls_attempted": False,
        "news_calls_attempted": False,
        "market_data_calls_attempted": False,
        "sec_calls_attempted": False,
        "issuer_calls_attempted": False,
        "exchange_calls_attempted": False,
        "llm_calls_attempted": False,
        "secret_values_reported": False,
        "manifest_paths": {
            "top500_stock": STOCK_AUTHORITY,
            "supported_etf": SUPPORTED_ETF_AUTHORITY,
            "etp_recognition": RECOGNITION_ETF_AUTHORITY,
        },
        "manifest_file_paths": {
            "top500_stock": str(TOP500_STOCK_UNIVERSE_MANIFEST_PATH.relative_to(root)),
            "supported_etf": str(SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH.relative_to(root)),
            "etp_recognition": str(RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH.relative_to(root)),
        },
        "manifest_checksums": {
            "top500_stock": stock_manifest.generated_checksum,
            "supported_etf": supported_etf_manifest.generated_checksum,
            "etp_recognition": recognition_etf_manifest.generated_checksum,
        },
        "manifest_ids": {
            "top500_stock": stock_manifest.manifest_id,
            "supported_etf": supported_etf_manifest.manifest_id,
            "etp_recognition": recognition_etf_manifest.manifest_id,
        },
        "generated_surfaces": list(GENERATED_SURFACES),
        "recognition_rows_unlock_generated_output": any(row["generated_output_eligible"] for row in recognition_rows),
        "supported_etf_coverage_authority": SUPPORTED_ETF_AUTHORITY,
        "recognition_etf_classification_authority": RECOGNITION_ETF_AUTHORITY,
        "stock_coverage_authority": STOCK_AUTHORITY,
        "counts": counts,
        "summary": _summary(counts),
        "failure_count": len(failures),
        "failure_rows": failures,
        "rows": rows,
    }


def _stock_row(entry: Any, failures: list[dict[str, Any]]) -> dict[str, Any]:
    result = search_assets(entry.ticker).results[0]
    cached_supported = result.support_classification is SearchSupportClassification.cached_supported
    eligible_not_cached = result.support_classification is SearchSupportClassification.eligible_not_cached
    generated_output_eligible = bool(
        result.can_open_generated_page
        and result.can_answer_chat
        and result.can_compare
        and cached_supported
        and entry.ticker in ASSETS
    )
    state = "supported" if generated_output_eligible else "pending_ingestion"
    row = {
        "ticker": entry.ticker,
        "name": entry.name,
        "asset_type": "stock",
        "manifest_kind": "top500_stock",
        "runtime_authority": STOCK_AUTHORITY,
        "resolved_authority": STOCK_AUTHORITY if top500_stock_universe_entry(entry.ticker) else None,
        "search_status": result.status.value,
        "support_classification": result.support_classification.value,
        "support_state": "cached_supported" if cached_supported else "eligible_not_cached",
        "classification_state": state,
        "generated_output_eligible": generated_output_eligible,
        "surface_eligibility": _surface_eligibility(generated_output_eligible),
        "rank": entry.rank,
        "rank_basis": entry.rank_basis,
        "source_provenance": entry.source_provenance,
        "snapshot_date": entry.snapshot_date,
        "generated_checksum": entry.generated_checksum,
    }
    if not (cached_supported or eligible_not_cached):
        _failure(failures, row, "top500_stock_row_resolved_to_wrong_classification")
    if row["resolved_authority"] != STOCK_AUTHORITY:
        _failure(failures, row, "top500_stock_row_missing_manifest_authority")
    if generated_output_eligible and row["runtime_authority"] != STOCK_AUTHORITY:
        _failure(failures, row, "stock_generated_output_wrong_authority")
    if generated_output_eligible != bool(result.generated_route):
        _failure(failures, row, "stock_generated_route_and_eligibility_mismatch")
    return row


def _supported_etf_row(entry: Any, failures: list[dict[str, Any]]) -> dict[str, Any]:
    result = search_assets(entry.ticker).results[0]
    generated_output_eligible = can_generate_output_for_etf_entry(entry)
    state = "supported" if generated_output_eligible else "pending_ingestion"
    row = {
        "ticker": entry.ticker,
        "name": entry.fund_name,
        "asset_type": "etf",
        "manifest_kind": "supported_etf",
        "runtime_authority": SUPPORTED_ETF_AUTHORITY,
        "resolved_authority": SUPPORTED_ETF_AUTHORITY,
        "recognition_authority_used_for_generated_output": False,
        "search_status": result.status.value,
        "support_classification": result.support_classification.value,
        "support_state": entry.support_state.value,
        "launch_cache_state": entry.launch_cache_state.value,
        "classification_state": state,
        "generated_output_eligible": generated_output_eligible,
        "surface_eligibility": _surface_eligibility(generated_output_eligible),
        "source_provenance": entry.source_provenance,
        "snapshot_date": entry.snapshot_date,
        "generated_checksum": entry.generated_checksum,
    }
    if entry.support_state is ETFUniverseSupportState.cached_supported:
        expected = SearchSupportClassification.cached_supported
    else:
        expected = SearchSupportClassification.eligible_not_cached
    if result.support_classification is not expected:
        _failure(failures, row, "supported_etf_row_resolved_to_wrong_classification")
    if bool(result.can_open_generated_page) != generated_output_eligible:
        _failure(failures, row, "supported_etf_generated_route_and_eligibility_mismatch")
    if row["recognition_authority_used_for_generated_output"]:
        _failure(failures, row, "supported_etf_used_recognition_authority_for_generated_output")
    return row


def _recognition_etf_row(entry: Any, failures: list[dict[str, Any]]) -> dict[str, Any]:
    result = search_assets(entry.ticker).results[0]
    state = _blocked_state_for_recognition(entry.support_state)
    row = {
        "ticker": entry.ticker,
        "name": entry.fund_name,
        "asset_type": "etf",
        "manifest_kind": "etp_recognition",
        "runtime_authority": RECOGNITION_ETF_AUTHORITY,
        "resolved_authority": RECOGNITION_ETF_AUTHORITY,
        "authoritative_for_generated_output": False,
        "recognition_only": True,
        "search_status": result.status.value,
        "support_classification": result.support_classification.value,
        "support_state": entry.support_state.value,
        "launch_cache_state": entry.launch_cache_state.value,
        "classification_state": state,
        "generated_output_eligible": False,
        "surface_eligibility": _surface_eligibility(False),
        "source_provenance": entry.source_provenance,
        "snapshot_date": entry.snapshot_date,
        "generated_checksum": entry.generated_checksum,
        "exclusion_flags": entry.exclusion_flags.model_dump(mode="json"),
    }
    if result.can_open_generated_page or result.can_answer_chat or result.can_compare or result.generated_route:
        _failure(failures, row, "recognition_row_unlocked_generated_search_capability")
    if any(row["surface_eligibility"].values()):
        _failure(failures, row, "recognition_row_unlocked_generated_surface")
    return row


def _blocked_state_for_recognition(support_state: ETFUniverseSupportState) -> str:
    if support_state is ETFUniverseSupportState.unavailable:
        return "unavailable"
    if support_state in {
        ETFUniverseSupportState.recognized_unsupported,
        ETFUniverseSupportState.out_of_scope,
        ETFUniverseSupportState.unknown,
    }:
        return "blocked"
    return "blocked"


def _surface_eligibility(generated_output_eligible: bool) -> dict[str, bool]:
    return {surface: generated_output_eligible for surface in GENERATED_SURFACES}


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    state_counts = Counter(row["classification_state"] for row in rows)
    manifest_counts = Counter(row["manifest_kind"] for row in rows)
    support_state_counts = Counter(row["support_state"] for row in rows)
    generated_by_manifest = Counter(
        row["manifest_kind"] for row in rows if row["generated_output_eligible"]
    )
    return {
        "total_rows": len(rows),
        "stock_manifest_rows": int(manifest_counts["top500_stock"]),
        "supported_etf_manifest_rows": int(manifest_counts["supported_etf"]),
        "recognition_manifest_rows": int(manifest_counts["etp_recognition"]),
        "supported_count": int(state_counts["supported"]),
        "partial_count": int(state_counts["partial"]),
        "pending_ingestion_count": int(state_counts["pending_ingestion"]),
        "unavailable_count": int(state_counts["unavailable"]),
        "blocked_count": int(state_counts["blocked"]),
        "recognition_only_count": int(manifest_counts["etp_recognition"]),
        "generated_output_eligible_count": sum(1 for row in rows if row["generated_output_eligible"]),
        "generated_output_eligible_by_manifest": dict(sorted(generated_by_manifest.items())),
        "state_counts": dict(sorted(state_counts.items())),
        "support_state_counts": dict(sorted(support_state_counts.items())),
    }


def _summary(counts: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_rows": counts["total_rows"],
        "stock_manifest_rows": counts["stock_manifest_rows"],
        "supported_etf_manifest_rows": counts["supported_etf_manifest_rows"],
        "recognition_manifest_rows": counts["recognition_manifest_rows"],
        "supported_count": counts["supported_count"],
        "pending_ingestion_count": counts["pending_ingestion_count"],
        "unavailable_count": counts["unavailable_count"],
        "blocked_count": counts["blocked_count"],
        "recognition_only_count": counts["recognition_only_count"],
        "generated_output_eligible_count": counts["generated_output_eligible_count"],
    }


def _failure(failures: list[dict[str, Any]], row: dict[str, Any], reason_code: str) -> None:
    failures.append(
        {
            "reason_code": reason_code,
            "ticker": row["ticker"],
            "manifest_kind": row["manifest_kind"],
            "runtime_authority": row["runtime_authority"],
            "support_state": row["support_state"],
            "support_classification": row["support_classification"],
            "generated_output_eligible": row["generated_output_eligible"],
        }
    )


@contextmanager
def _deterministic_no_live_env() -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in NO_LIVE_ENV}
    os.environ.update(NO_LIVE_ENV)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic full-manifest support smoke.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON diagnostics.")
    args = parser.parse_args(argv)
    result = run_full_manifest_support_smoke()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        summary = result["summary"]
        print(f"full manifest support smoke: {result['status']} ({result['reason_code']})")
        print(
            "rows: "
            f"stocks={summary['stock_manifest_rows']} "
            f"supported_etfs={summary['supported_etf_manifest_rows']} "
            f"recognition={summary['recognition_manifest_rows']} "
            f"generated_eligible={summary['generated_output_eligible_count']}"
        )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
