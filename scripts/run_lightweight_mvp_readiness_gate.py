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

from scripts.run_local_fresh_data_rehearsal import run_rehearsal
from scripts.run_full_manifest_support_smoke import run_full_manifest_support_smoke
from scripts.run_lightweight_data_fetch_smoke import run_current_supported_etf_manifest_fetch_smoke


SCHEMA_VERSION = "lightweight-mvp-readiness-gate-v1"
DETERMINISTIC_REHEARSAL_ENV = {
    "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "false",
    "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "false",
    "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "false",
    "MARKET_NEWS_FETCH_ENABLED": "false",
    "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "false",
    "LLM_LIVE_GENERATION_ENABLED": "false",
}

LOCAL_REQUIRED_CHECK_IDS = (
    "deterministic_default_boundary",
    "source_handoff_approval_gate",
    "governed_golden_api_rendering",
    "local_fresh_data_mvp_slice_smoke",
    "local_fresh_data_mvp_slice_comparison_export_parity",
    "local_deployment_env_smoke",
    "stock_vs_etf_comparison_readiness",
    "frontend_v04_smoke_markers",
)

STRICT_AUDIT_GATE_IDS = (
    "etf500_full_supported_manifest_validation",
    "top500_current_manifest_refresh_approval",
    "full_golden_asset_source_handoff_approval",
    "stock_sec_source_pack_approval",
    "etf_issuer_source_pack_approval",
    "launch_sized_source_artifacts",
    "launch_manifest_promotion",
    "generated_output_cache_promotion",
    "live_provider_execution",
    "live_ai_review",
    "production_deployment",
    "recurring_jobs",
    "broad_paid_provider_news_integrations",
)

STRICT_AUDIT_REASON_CODES = {
    "etf500_full_supported_manifest_validation": "audit_only_etf500_not_required_for_local_personal_mvp",
    "top500_current_manifest_refresh_approval": "audit_only_top500_refresh_not_promoted_by_gate",
    "full_golden_asset_source_handoff_approval": "audit_only_full_handoff_not_granted_by_gate",
    "stock_sec_source_pack_approval": "audit_only_stock_source_packs_need_review",
    "etf_issuer_source_pack_approval": "audit_only_etf_source_packs_need_review",
    "launch_sized_source_artifacts": "audit_only_launch_sized_artifacts_not_required_for_local_manual_review",
    "launch_manifest_promotion": "audit_only_launch_manifest_not_promoted",
    "generated_output_cache_promotion": "audit_only_generated_output_cache_not_promoted",
    "live_provider_execution": "audit_only_live_provider_not_executed",
    "live_ai_review": "audit_only_live_ai_not_required_by_default",
    "production_deployment": "audit_only_production_deploy_not_created",
    "recurring_jobs": "audit_only_recurring_jobs_not_created",
    "broad_paid_provider_news_integrations": "audit_only_broad_paid_integrations_not_approved",
}

FORBIDDEN_VALUE_MARKERS = (
    "postgresql://",
    "postgresql+psycopg://",
    "Bearer ",
    "Authorization:",
    "BEGIN PRIVATE KEY",
    "sk-",
    "xoxb-",
    "ghp_",
    "raw provider payload value",
    "raw source text value",
    "raw model output",
    "raw model reasoning",
    "hidden prompt text",
    "service account json",
    "signed url",
)


def run_lightweight_mvp_readiness_gate(env: dict[str, str] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    deterministic_env = {} if env is None else env
    with _deterministic_rehearsal_env():
        rehearsal = run_rehearsal(env=deterministic_env, root=root)
    full_manifest_smoke = run_full_manifest_support_smoke(root=root)
    current_etf_fetch_smoke = run_current_supported_etf_manifest_fetch_smoke()
    checks_by_id = {check["check_id"]: check for check in rehearsal.get("checks", [])}
    threshold = rehearsal.get("local_mvp_threshold_summary", {})
    slice_gate = rehearsal.get("lightweight_local_mvp_slice_manual_readiness_gate", {})
    manual_gate = rehearsal.get("manual_fresh_data_readiness_gate", {})
    local_checks = [_local_check_summary(checks_by_id[check_id]) for check_id in LOCAL_REQUIRED_CHECK_IDS]
    optional_checks = [
        _local_check_summary(check)
        for check in rehearsal.get("checks", [])
        if check.get("check_id", "").startswith("optional_")
    ]
    local_blockers = _build_local_manual_review_blockers(
        rehearsal=rehearsal,
        local_checks=local_checks,
        optional_checks=optional_checks,
        threshold=threshold,
        slice_gate=slice_gate,
    )
    if full_manifest_smoke.get("status") != "pass":
        local_blockers.append(
            {
                "reason_code": "full_manifest_support_smoke_not_passed",
                "smoke_reason_code": full_manifest_smoke.get("reason_code"),
                "failure_rows": full_manifest_smoke.get("failure_rows", []),
            }
        )
    if current_etf_fetch_smoke.get("status") != "pass":
        local_blockers.append(
            {
                "reason_code": "current_supported_etf_fetch_smoke_not_passed",
                "failure_rows": current_etf_fetch_smoke.get("failure_rows", []),
            }
        )
    local_ready = not local_blockers
    status_counts = Counter(check["status"] for check in rehearsal.get("checks", []))

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if local_ready else "blocked",
        "reason_code": (
            "lightweight_mvp_ready_for_local_manual_review"
            if local_ready
            else "lightweight_mvp_local_manual_review_blocked"
        ),
        "default_mode": "deterministic_fixture_backed_no_services_no_live_calls",
        "normal_ci_requires_live_calls": False,
        "production_services_started": False,
        "deployments_created": False,
        "live_provider_calls_attempted": False,
        "database_connections_opened": False,
        "secret_values_reported": False,
        "production_ready": False,
        "public_launch_ready": False,
        "strict_audit_ready": False,
        "launch_or_public_deployment_approved": False,
        "sources_approved_by_readiness_gate": False,
        "manifests_promoted": False,
        "generated_output_cache_promoted": False,
        "local_personal_mvp_ready_for_manual_review": local_ready,
        "manual_review_boundary": {
            "scope": "local_personal_mvp",
            "ready_state": "ready_for_local_manual_review" if local_ready else "blocked_for_local_manual_review",
            "strict_public_launch_checks_block_local_manual_review": False,
            "operator_action": (
                "run_explicit_manual_browser_api_review_for_lightweight_local_mvp_slice"
                if local_ready
                else "fix_deterministic_local_readiness_blockers_before_manual_review"
            ),
        },
        "rehearsal_integration": {
            "schema_version": rehearsal.get("schema_version"),
            "status": rehearsal.get("status"),
            "reason_code": "local_fresh_data_rehearsal_consumed",
            "embedded_local_deployment_env_smoke_consumed": True,
            "threshold_schema_version": threshold.get("schema_version"),
            "slice_gate_schema_version": slice_gate.get("schema_version"),
            "manual_gate_schema_version": manual_gate.get("schema_version"),
        },
        "status_counts": {
            "pass": int(status_counts.get("pass", 0)),
            "blocked": int(status_counts.get("blocked", 0)),
            "skipped": int(status_counts.get("skipped", 0)),
        },
        "local_manual_review_checks": local_checks,
        "optional_operator_checks": optional_checks,
        "local_manual_review_blockers": local_blockers,
        "strict_public_launch_audit_only_gates": _build_strict_audit_only_gates(manual_gate),
        "readiness_summaries": _build_readiness_summaries(checks_by_id, threshold, slice_gate, manual_gate),
        "full_manifest_support_smoke": _full_manifest_smoke_summary(full_manifest_smoke),
        "current_supported_etf_manifest_fetch": _current_supported_etf_fetch_summary(current_etf_fetch_smoke),
        "weekly_news_and_ai_boundaries": _build_weekly_news_ai_boundaries(checks_by_id),
        "unsupported_blocked_ticker_boundaries": _build_unsupported_blocked_ticker_boundaries(checks_by_id),
        "no_secret_diagnostics": _build_no_secret_diagnostics(checks_by_id, slice_gate, manual_gate),
    }

    forbidden_hits = _forbidden_value_marker_hits(payload)
    payload["no_secret_diagnostics"]["forbidden_value_marker_hits"] = forbidden_hits
    if forbidden_hits:
        payload["status"] = "blocked"
        payload["reason_code"] = "lightweight_mvp_readiness_gate_forbidden_value_marker_detected"
        payload["local_personal_mvp_ready_for_manual_review"] = False
        payload["manual_review_boundary"]["ready_state"] = "blocked_for_local_manual_review"
        payload["local_manual_review_blockers"].append(
            {"reason_code": "forbidden_value_marker_detected", "markers": forbidden_hits}
        )
    return payload


@contextmanager
def _deterministic_rehearsal_env() -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in DETERMINISTIC_REHEARSAL_ENV}
    os.environ.update(DETERMINISTIC_REHEARSAL_ENV)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _local_check_summary(check: dict[str, Any]) -> dict[str, Any]:
    return {
        "check_id": check.get("check_id"),
        "status": check.get("status"),
        "reason_code": check.get("reason_code"),
    }


def _build_local_manual_review_blockers(
    *,
    rehearsal: dict[str, Any],
    local_checks: list[dict[str, Any]],
    optional_checks: list[dict[str, Any]],
    threshold: dict[str, Any],
    slice_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for check in local_checks:
        if check["status"] != "pass":
            blockers.append(
                {
                    "reason_code": "required_local_check_not_passed",
                    "check_id": check["check_id"],
                    "status": check["status"],
                    "check_reason_code": check["reason_code"],
                }
            )
    for check in optional_checks:
        if check["status"] == "blocked":
            blockers.append(
                {
                    "reason_code": "optional_operator_check_blocked_after_explicit_opt_in",
                    "check_id": check["check_id"],
                    "check_reason_code": check["reason_code"],
                }
            )
    if threshold.get("local_operator_review_ready") is not True:
        blockers.append(
            {
                "reason_code": "local_threshold_summary_not_ready",
                "threshold_blockers": threshold.get("threshold_blockers", []),
            }
        )
    if slice_gate.get("deterministic_local_slice_manual_review_ready") is not True:
        blockers.append(
            {
                "reason_code": "lightweight_local_slice_gate_not_ready",
                "decision": slice_gate.get("decision"),
                "blockers": slice_gate.get("blockers", []),
            }
        )
    if rehearsal.get("production_services_started") is not False:
        blockers.append({"reason_code": "production_services_started_regression"})
    if rehearsal.get("normal_ci_requires_live_calls") is not False:
        blockers.append({"reason_code": "normal_ci_live_call_requirement_regression"})
    return blockers


def _build_strict_audit_only_gates(manual_gate: dict[str, Any]) -> list[dict[str, Any]]:
    stop_conditions = manual_gate.get("stop_conditions", [])
    stop_reason_counts = Counter(condition.get("reason_code") for condition in stop_conditions)
    gates: list[dict[str, Any]] = []
    for gate_id in STRICT_AUDIT_GATE_IDS:
        gates.append(
            {
                "gate_id": gate_id,
                "status": "audit_only",
                "reason_code": STRICT_AUDIT_REASON_CODES[gate_id],
                "blocking_for_local_personal_mvp_manual_review": False,
                "promoted_or_approved_by_gate": False,
                "related_stop_reason_count": _related_stop_reason_count(gate_id, stop_reason_counts),
            }
        )
    return gates


def _related_stop_reason_count(gate_id: str, stop_reason_counts: Counter[str]) -> int:
    prefixes = {
        "etf500_full_supported_manifest_validation": ("etf500_",),
        "top500_current_manifest_refresh_approval": ("top500_",),
        "full_golden_asset_source_handoff_approval": ("etf500_handoff", "top500_sec_source_handoff"),
        "stock_sec_source_pack_approval": ("top500_sec_",),
        "etf_issuer_source_pack_approval": ("etf500_issuer_", "etf500_source_pack"),
        "launch_sized_source_artifacts": ("etf500_review_fixture_only",),
        "launch_manifest_promotion": ("etf500_review_fixture_only",),
        "generated_output_cache_promotion": ("local_ingestion_priority_plan",),
        "live_provider_execution": ("optional_mode_blocked",),
        "live_ai_review": ("optional_mode_blocked",),
        "production_deployment": ("production_",),
        "recurring_jobs": ("production_",),
        "broad_paid_provider_news_integrations": ("optional_mode_blocked",),
    }[gate_id]
    return sum(count for reason, count in stop_reason_counts.items() if reason and reason.startswith(prefixes))


def _build_readiness_summaries(
    checks_by_id: dict[str, dict[str, Any]],
    threshold: dict[str, Any],
    slice_gate: dict[str, Any],
    manual_gate: dict[str, Any],
) -> dict[str, Any]:
    slice_smoke = checks_by_id["local_fresh_data_mvp_slice_smoke"].get("details", {})
    parity = checks_by_id["local_fresh_data_mvp_slice_comparison_export_parity"].get("details", {})
    deployment = checks_by_id["local_deployment_env_smoke"].get("details", {})
    stock_source = checks_by_id["stock_sec_source_pack_readiness"].get("details", {})
    etf_source = checks_by_id["etf_issuer_source_pack_readiness"].get("details", {})
    launch = checks_by_id["launch_manifest_review_packets"].get("details", {})
    ingestion = checks_by_id["local_ingestion_priority_planner"].get("details", {})
    source_handoff = checks_by_id["source_handoff_approval_gate"].get("details", {})
    return {
        "local_fresh_data_mvp_slice_smoke": {
            "status": checks_by_id["local_fresh_data_mvp_slice_smoke"].get("status"),
            "reason_code": checks_by_id["local_fresh_data_mvp_slice_smoke"].get("reason_code"),
            "status_counts": slice_smoke.get("status_counts"),
            "supported_renderable_tickers": slice_smoke.get("supported_renderable_tickers"),
            "blocked_regression_tickers": slice_smoke.get("blocked_regression_tickers"),
            "raw_payload_exposed_count": slice_smoke.get("raw_payload_exposed_count"),
        },
        "comparison_export_parity": {
            "status": checks_by_id["local_fresh_data_mvp_slice_comparison_export_parity"].get("status"),
            "reason_code": checks_by_id["local_fresh_data_mvp_slice_comparison_export_parity"].get("reason_code"),
            "representative_comparison_pairs": [
                row.get("pair") for row in parity.get("representative_comparison_pairs", [])
            ],
            "export_surfaces": parity.get("export_surfaces"),
            "forbidden_marker_hits": (parity.get("sanitized_diagnostics") or {}).get("forbidden_marker_hits"),
        },
        "stock_vs_etf_readiness": {
            "status": checks_by_id["stock_vs_etf_comparison_readiness"].get("status"),
            "reason_code": checks_by_id["stock_vs_etf_comparison_readiness"].get("reason_code"),
            "backend_compare": checks_by_id["stock_vs_etf_comparison_readiness"].get("details", {}).get("backend_compare"),
            "chat_compare_redirect": checks_by_id["stock_vs_etf_comparison_readiness"].get("details", {}).get("chat_compare_redirect"),
        },
        "local_deployment_env_smoke": {
            "status": checks_by_id["local_deployment_env_smoke"].get("status"),
            "reason_code": checks_by_id["local_deployment_env_smoke"].get("reason_code"),
            "schema_version": deployment.get("schema_version"),
            "normal_ci_requires_live_calls": deployment.get("normal_ci_requires_live_calls"),
            "production_services_started": deployment.get("production_services_started"),
            "deployments_created": deployment.get("deployments_created"),
            "database_connections_opened": deployment.get("database_connections_opened"),
            "secret_values_reported": deployment.get("secret_values_reported"),
            "status_counts": deployment.get("status_counts"),
        },
        "frontend_workflow_markers": {
            "status": checks_by_id["frontend_v04_smoke_markers"].get("status"),
            "reason_code": checks_by_id["frontend_v04_smoke_markers"].get("reason_code"),
            "checked_file_count": checks_by_id["frontend_v04_smoke_markers"].get("details", {}).get("checked_file_count"),
        },
        "source_handoff_readiness": {
            "status": checks_by_id["source_handoff_approval_gate"].get("status"),
            "reason_code": checks_by_id["source_handoff_approval_gate"].get("reason_code"),
            "retrieval_alone_approves_evidence": source_handoff.get("retrieval_alone_approves_evidence"),
            "blocked_case_count": source_handoff.get("blocked_case_count"),
        },
        "launch_manifest_review_packets": {
            "status": checks_by_id["launch_manifest_review_packets"].get("status"),
            "reason_code": checks_by_id["launch_manifest_review_packets"].get("reason_code"),
            "etf_readiness_counts": launch.get("etf_readiness_counts"),
            "etf500_current_fixture_not_launch_coverage": launch.get("etf500_current_fixture_not_launch_coverage"),
            "etf500_source_pack_readiness": launch.get("etf500_source_pack_readiness"),
        },
        "source_pack_planning": {
            "stock_sec_source_pack_readiness": {
                "status": checks_by_id["stock_sec_source_pack_readiness"].get("status"),
                "reason_code": checks_by_id["stock_sec_source_pack_readiness"].get("reason_code"),
                "readiness_counts": stock_source.get("readiness_counts"),
            },
            "etf_issuer_source_pack_readiness": {
                "status": checks_by_id["etf_issuer_source_pack_readiness"].get("status"),
                "reason_code": checks_by_id["etf_issuer_source_pack_readiness"].get("reason_code"),
                "readiness_counts": etf_source.get("readiness_counts"),
            },
        },
        "local_ingestion_priority_planning": {
            "status": checks_by_id["local_ingestion_priority_planner"].get("status"),
            "reason_code": checks_by_id["local_ingestion_priority_planner"].get("reason_code"),
            "summary": ingestion.get("summary"),
        },
        "manual_gate_stop_conditions_audit_only": {
            "manual_gate_decision": manual_gate.get("decision"),
            "stop_condition_count": len(manual_gate.get("stop_conditions", [])),
            "stop_reason_codes": sorted(
                {
                    condition.get("reason_code")
                    for condition in manual_gate.get("stop_conditions", [])
                    if condition.get("reason_code")
                }
            ),
        },
        "local_threshold_summary": {
            "overall_local_approval_status": threshold.get("overall_local_approval_status"),
            "local_operator_review_ready": threshold.get("local_operator_review_ready"),
            "threshold_blocker_count": len(threshold.get("threshold_blockers", [])),
        },
        "slice_manual_review_gate": {
            "decision": slice_gate.get("decision"),
            "manual_slice_review_ready": slice_gate.get("manual_slice_review_ready"),
            "blocker_count": len(slice_gate.get("blockers", [])),
        },
    }


def _full_manifest_smoke_summary(smoke: dict[str, Any]) -> dict[str, Any]:
    counts = smoke.get("counts", {})
    return {
        "schema_version": smoke.get("schema_version"),
        "status": smoke.get("status"),
        "reason_code": smoke.get("reason_code"),
        "normal_ci_requires_live_calls": smoke.get("normal_ci_requires_live_calls"),
        "live_provider_calls_attempted": smoke.get("live_provider_calls_attempted"),
        "secret_values_reported": smoke.get("secret_values_reported"),
        "manifest_paths": smoke.get("manifest_paths"),
        "manifest_checksums": smoke.get("manifest_checksums"),
        "total_rows": counts.get("total_rows"),
        "stock_manifest_rows": counts.get("stock_manifest_rows"),
        "supported_etf_manifest_rows": counts.get("supported_etf_manifest_rows"),
        "recognition_manifest_rows": counts.get("recognition_manifest_rows"),
        "supported_count": counts.get("supported_count"),
        "partial_count": counts.get("partial_count"),
        "pending_ingestion_count": counts.get("pending_ingestion_count"),
        "unavailable_count": counts.get("unavailable_count"),
        "blocked_count": counts.get("blocked_count"),
        "recognition_only_count": counts.get("recognition_only_count"),
        "generated_output_eligible_count": counts.get("generated_output_eligible_count"),
        "generated_output_eligible_by_manifest": counts.get("generated_output_eligible_by_manifest"),
        "recognition_rows_unlock_generated_output": smoke.get("recognition_rows_unlock_generated_output"),
        "failure_count": smoke.get("failure_count"),
        "failure_rows": smoke.get("failure_rows", []),
    }


def _current_supported_etf_fetch_summary(smoke: dict[str, Any]) -> dict[str, Any]:
    counts = smoke.get("counts", {})
    return {
        "schema_version": smoke.get("schema_version"),
        "status": smoke.get("status"),
        "normal_ci_requires_live_calls": smoke.get("normal_ci_requires_live_calls"),
        "supported_runtime_authority": smoke.get("supported_runtime_authority"),
        "recognition_runtime_authority": smoke.get("recognition_runtime_authority"),
        "supported_manifest_checksum": smoke.get("supported_manifest_checksum"),
        "recognition_manifest_checksum": smoke.get("recognition_manifest_checksum"),
        "recognition_rows_unlock_generated_output": smoke.get("recognition_rows_unlock_generated_output"),
        "current_supported_etf_manifest_rows": counts.get("current_supported_etf_manifest_rows"),
        "issuer_backed_supported_count": counts.get("issuer_backed_supported_count"),
        "provider_fallback_partial_count": counts.get("provider_fallback_partial_count"),
        "unavailable_count": counts.get("unavailable_count"),
        "blocked_recognition_count": counts.get("blocked_recognition_count"),
        "generated_output_eligible_count": counts.get("generated_output_eligible_count"),
        "strict_manifest_generated_output_eligible_count": counts.get("strict_manifest_generated_output_eligible_count"),
        "failure_count": counts.get("failure_count"),
        "failure_rows": smoke.get("failure_rows", []),
    }


def _build_weekly_news_ai_boundaries(checks_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    golden = checks_by_id["governed_golden_api_rendering"].get("details", {})
    return {
        "weekly_news_focus_configured_max_requires_evidence": True,
        "weekly_news_focus_smaller_or_empty_sets_valid": True,
        "weekly_news_limited_count": golden.get("weekly_news_limited_count"),
        "ai_comprehensive_analysis_suppressed_without_two_items": True,
        "ai_analysis_minimum_weekly_items": golden.get("ai_analysis_minimum_weekly_items"),
        "canonical_facts_separate_from_timely_context": True,
        "reason_codes": [
            checks_by_id["governed_golden_api_rendering"].get("reason_code"),
            checks_by_id["frontend_v04_smoke_markers"].get("reason_code"),
        ],
    }


def _build_unsupported_blocked_ticker_boundaries(checks_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    slice_smoke = checks_by_id["local_fresh_data_mvp_slice_smoke"].get("details", {})
    asset_summary = checks_by_id["stock_sec_source_pack_readiness"].get("details", {})
    threshold_rows = slice_smoke.get("rows", [])
    blocked_rows = [
        row
        for row in threshold_rows
        if row.get("ticker") in {"TQQQ", "ARKK", "BND", "GLD"}
    ]
    return {
        "blocked_regression_tickers": slice_smoke.get("blocked_regression_tickers"),
        "blocked_generated_surfaces": slice_smoke.get("blocked_generated_surfaces"),
        "blocked_rows_have_no_generated_output": all(
            row.get("generated_output_eligible") is False
            and not row.get("source_count")
            and not row.get("citation_count")
            and not row.get("fact_count")
            and not row.get("fetch_call_count")
            for row in blocked_rows
        ),
        "review_packet_unlocks_generated_output": (asset_summary.get("readiness_counts") or {}).get(
            "review_packet_unlocks_generated_output"
        ),
    }


def _build_no_secret_diagnostics(
    checks_by_id: dict[str, dict[str, Any]],
    slice_gate: dict[str, Any],
    manual_gate: dict[str, Any],
) -> dict[str, Any]:
    deployment = checks_by_id["local_deployment_env_smoke"].get("details", {})
    deployment_safe = deployment.get("safe_diagnostics") or {}
    slice_safe = slice_gate.get("sanitized_diagnostics") or {}
    manual_safe = manual_gate.get("no_secret_diagnostics") or {}
    return {
        "safe_diagnostics_only": True,
        "env_var_names_reported_without_values": True,
        "secret_values_reported": bool(
            deployment.get("secret_values_reported")
            or deployment_safe.get("secret_values_reported")
            or slice_safe.get("secret_values_reported")
            or manual_safe.get("secret_values_reported")
        ),
        "database_dsn_values_reported": False,
        "provider_payloads_reported": False,
        "raw_source_text_reported": False,
        "raw_model_output_reported": False,
        "raw_model_reasoning_reported": False,
        "hidden_prompts_reported": False,
        "service_account_json_reported": False,
        "opt_in_env_names_reported_without_values": manual_safe.get("opt_in_env_names_reported_without_values", []),
    }


def _forbidden_value_marker_hits(payload: dict[str, Any]) -> list[str]:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    lower = serialized.lower()
    return sorted({marker for marker in FORBIDDEN_VALUE_MARKERS if marker.lower() in lower})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic lightweight MVP readiness gate.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON diagnostics.")
    args = parser.parse_args(argv)
    result = run_lightweight_mvp_readiness_gate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"lightweight MVP readiness gate: {result['status']} ({result['reason_code']})")
        print(
            "local personal MVP manual review ready: "
            f"{str(result['local_personal_mvp_ready_for_manual_review']).lower()}"
        )
        print("strict/public-launch gates: audit_only")
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
