#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.chat import generate_asset_chat
from backend.comparison import generate_comparison
from backend.etf_universe import (
    build_etf500_issuer_source_pack_batch_plan,
    build_etf_issuer_source_pack_readiness_packet,
    build_etf_launch_review_packet,
)
from backend.generated_output_cache_repository import InMemoryGeneratedOutputCacheRepository
from backend.ingestion import build_local_ingestion_priority_plan, get_pre_cache_job_status
from backend.knowledge_pack_repository import AssetKnowledgePackRepository, InMemoryAssetKnowledgePackRepository
from backend.lightweight_data_fetch import fetch_lightweight_asset_data
from backend.main import app
from backend.models import (
    FreshnessState,
    SourceAllowlistStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceUsePolicy,
    Top500CandidateDiffReport,
    Top500CandidateManifest,
    WeeklyNewsEventType,
)
from backend.overview import (
    _asset_knowledge_pack_from_repository_records,
    _maybe_write_overview_generated_output_cache,
    generate_overview_from_pack,
)
from backend.persistence import BackendReadDependencies, configure_backend_read_dependencies
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.safety import find_forbidden_output_phrases
from backend.settings import build_lightweight_data_settings, build_live_acquisition_settings, build_local_durable_repository_settings
from backend.source_policy import SourcePolicyAction, source_handoff_fields_from_policy, validate_source_handoff
from backend.source_policy import resolve_source_policy
from backend.source_snapshot_repository import (
    InMemorySourceSnapshotArtifactRepository,
    SourceSnapshotArtifactCategory,
    SourceSnapshotRepositoryRecords,
    artifact_from_knowledge_pack_source,
)
from backend.testing import TestClient
from backend.top500_candidate_manifest import inspect_top500_candidate_review_packet
from backend.top500_candidate_manifest import build_stock_sec_source_pack_readiness_packet
from backend.top500_candidate_manifest import build_top500_sec_source_pack_batch_plan
from backend.weekly_news_repository import (
    InMemoryWeeklyNewsEventEvidenceRepository,
    WeeklyNewsEventCandidateRow,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
)
from scripts.run_local_fresh_data_slice_smoke import run_slice_smoke


SCHEMA_VERSION = "local-fresh-data-mvp-rehearsal-v1"
BROWSER_OPT_IN_ENV = "LTT_REHEARSAL_BROWSER_SERVICES_ENABLED"
DURABLE_OPT_IN_ENV = "LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED"
OFFICIAL_RETRIEVAL_OPT_IN_ENV = "LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED"
LIVE_AI_OPT_IN_ENV = "LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED"
WEB_BASE_ENV = "LEARN_TICKER_LOCAL_WEB_BASE"
API_BASE_ENV = "LEARN_TICKER_LOCAL_API_BASE"
REQUIRED_THRESHOLD_CHECK_IDS = (
    "deterministic_default_boundary",
    "source_handoff_approval_gate",
    "governed_golden_api_rendering",
    "local_fresh_data_mvp_slice_smoke",
    "stock_vs_etf_comparison_readiness",
    "launch_manifest_review_packets",
    "stock_sec_source_pack_readiness",
    "etf_issuer_source_pack_readiness",
    "local_ingestion_priority_planner",
    "frontend_v04_smoke_markers",
)
OPTIONAL_THRESHOLD_CHECK_IDS = (
    "optional_browser_services",
    "optional_local_durable_repositories",
    "optional_official_source_retrieval",
    "optional_live_ai_review",
)
ALLOWED_FAILED_ASSET_COUNT = 1
ALLOWED_UNAVAILABLE_ASSET_COUNT = 1


@dataclass(frozen=True)
class RehearsalCheck:
    check_id: str
    status: str
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "check_id": self.check_id,
            "status": self.status,
            "reason_code": self.reason_code,
        }
        if self.details:
            payload["details"] = self.details
        return payload


def run_rehearsal(env: dict[str, str] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    source_env = dict(os.environ if env is None else env)
    checks = [
        _guarded("deterministic_default_boundary", lambda: _check_default_boundary(source_env)),
        _guarded("source_handoff_approval_gate", _check_source_handoff_approval_gate),
        _guarded("governed_golden_api_rendering", _check_governed_golden_api_rendering),
        _guarded("local_fresh_data_mvp_slice_smoke", _check_local_fresh_data_mvp_slice_smoke),
        _guarded("stock_vs_etf_comparison_readiness", lambda: _check_stock_vs_etf_comparison_readiness(root)),
        _guarded("launch_manifest_review_packets", lambda: _check_launch_manifest_review_packets(root)),
        _guarded("stock_sec_source_pack_readiness", lambda: _check_stock_sec_source_pack_readiness(root)),
        _guarded("etf_issuer_source_pack_readiness", _check_etf_issuer_source_pack_readiness),
        _guarded("local_ingestion_priority_planner", lambda: _check_local_ingestion_priority_planner(root)),
        _guarded("frontend_v04_smoke_markers", lambda: _check_frontend_markers(root)),
        _guarded("optional_browser_services", lambda: _check_optional_browser_services(source_env)),
        _guarded("optional_local_durable_repositories", lambda: _check_optional_durable_repositories(source_env)),
        _guarded("optional_official_source_retrieval", lambda: _check_optional_official_source_retrieval(source_env)),
        _guarded("optional_live_ai_review", lambda: _check_optional_live_ai_review(source_env)),
    ]
    threshold_summary = _build_local_mvp_threshold_summary(checks)
    manual_readiness_gate = _build_manual_fresh_data_readiness_gate(checks, threshold_summary)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": _rollup_status(checks),
        "default_mode": "deterministic_fixture_backed",
        "normal_ci_requires_live_calls": False,
        "production_services_started": False,
        "manifests_promoted": False,
        "sources_approved_by_rehearsal": False,
        "local_mvp_threshold_summary": threshold_summary,
        "manual_fresh_data_readiness_gate": manual_readiness_gate,
        "checks": [check.to_dict() for check in checks],
    }


def _check_default_boundary(env: dict[str, str]) -> RehearsalCheck:
    optional_flags = {
        BROWSER_OPT_IN_ENV: _bool_env(env.get(BROWSER_OPT_IN_ENV)),
        DURABLE_OPT_IN_ENV: _bool_env(env.get(DURABLE_OPT_IN_ENV)),
        OFFICIAL_RETRIEVAL_OPT_IN_ENV: _bool_env(env.get(OFFICIAL_RETRIEVAL_OPT_IN_ENV)),
        LIVE_AI_OPT_IN_ENV: _bool_env(env.get(LIVE_AI_OPT_IN_ENV)),
    }
    return _pass(
        "deterministic_default_boundary",
        "fixture_backed_no_live_services_by_default",
        {
            "optional_flags": optional_flags,
            "default_uses_browser_service": False,
            "default_uses_production_database": False,
            "default_uses_production_storage": False,
            "default_uses_live_provider": False,
            "default_uses_live_llm": False,
        },
    )


def _check_source_handoff_approval_gate() -> RehearsalCheck:
    approved_policy = resolve_source_policy(url="https://www.sec.gov/Archives/example")
    approved_source = {
        **source_handoff_fields_from_policy(
            approved_policy,
            source_identity="https://www.sec.gov/Archives/example",
            approval_rationale="Reviewed official SEC source for deterministic rehearsal evidence.",
        ),
        "source_document_id": "src_sec_rehearsal_fixture",
        "source_type": "sec_filing",
        "is_official": True,
        "source_quality": SourceQuality.official,
        "allowlist_status": approved_policy.allowlist_status,
        "source_use_policy": approved_policy.source_use_policy,
        "permitted_operations": approved_policy.permitted_operations,
        "freshness_state": FreshnessState.fresh,
        "as_of_date": "2026-04-01",
        "retrieved_at": "2026-04-25T00:00:00Z",
    }
    actions = [
        SourcePolicyAction.generated_claim_support,
        SourcePolicyAction.cacheable_generated_output,
        SourcePolicyAction.markdown_json_section_export,
    ]
    action_results = {
        action.value: validate_source_handoff(approved_source, action=action).allowed for action in actions
    }
    blocked_cases = {
        "pending_review": validate_source_handoff(
            {**approved_source, "review_status": SourceReviewStatus.pending_review},
            action=SourcePolicyAction.generated_claim_support,
        ).reason_codes,
        "parser_failed": validate_source_handoff(
            {
                **approved_source,
                "parser_status": "failed",
                "parser_failure_diagnostics": "deterministic parser failure",
            },
            action=SourcePolicyAction.generated_claim_support,
        ).reason_codes,
        "metadata_only": validate_source_handoff(
            {**approved_source, "source_use_policy": SourceUsePolicy.metadata_only},
            action=SourcePolicyAction.generated_claim_support,
        ).reason_codes,
        "hidden_internal": validate_source_handoff(
            {**approved_source, "source_identity": "private://internal/source", "source_type": "internal_feed"},
            action=SourcePolicyAction.generated_claim_support,
        ).reason_codes,
    }
    expected_reasons = {
        "pending_review": "review_pending_review",
        "parser_failed": "parser_failed",
        "metadata_only": "metadata_only_content_omitted",
        "hidden_internal": "hidden_or_internal_source",
    }
    if not all(action_results.values()):
        return _blocked("source_handoff_approval_gate", "approved_source_handoff_action_blocked", action_results)
    for case_id, reason in expected_reasons.items():
        if reason not in blocked_cases[case_id]:
            return _blocked(
                "source_handoff_approval_gate",
                "blocked_source_handoff_case_not_enforced",
                {"case_id": case_id, "reason_codes": list(blocked_cases[case_id])},
            )
    return _pass(
        "source_handoff_approval_gate",
        "approved_sources_feed_evidence_and_unapproved_sources_block",
        {
            "validated_actions": sorted(action_results),
            "blocked_case_count": len(blocked_cases),
            "retrieval_alone_approves_evidence": False,
        },
    )


def _check_governed_golden_api_rendering() -> RehearsalCheck:
    client = TestClient(app)
    knowledge_repo, generated_repo, weekly_repo, source_snapshot_repo = _configured_golden_repositories()
    configure_backend_read_dependencies(
        app,
        BackendReadDependencies(
            persisted_reads_enabled=True,
            knowledge_pack_reader=knowledge_repo,
            generated_output_cache_reader=generated_repo,
            weekly_news_reader=weekly_repo,
            source_snapshot_repository=source_snapshot_repo,
        ),
    )
    try:
        overview = client.get("/api/assets/QQQ/overview").json()
        empty_weekly = client.get("/api/assets/AAPL/weekly-news").json()
        sources = client.get("/api/assets/VOO/sources").json()
        comparison = client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json()
        chat = client.post("/api/assets/VOO/chat", json={"question": "What does it hold?"}).json()
        asset_export = client.get("/api/assets/VOO/export", params={"export_format": "json"}).json()
        source_export = client.get("/api/assets/VOO/sources/export", params={"export_format": "json"}).json()
        comparison_export = client.get(
            "/api/compare/export",
            params={"left_ticker": "VOO", "right_ticker": "QQQ", "export_format": "json"},
        ).json()
        chat_export = client.post(
            "/api/assets/VOO/chat/export",
            json={"question": "What does it hold?", "export_format": "json"},
        ).json()
        unsupported = client.get("/api/search", params={"q": "ARKK"}).json()
        out_of_scope = client.get("/api/search", params={"q": "GME"}).json()
        pending_ingestion = client.get("/api/search", params={"q": "SPY"}).json()
        unknown = client.get("/api/search", params={"q": "ZZZZ"}).json()
    finally:
        configure_backend_read_dependencies(app, None)

    blocked_searches = {
        "unsupported": unsupported,
        "out_of_scope": out_of_scope,
        "pending_ingestion": pending_ingestion,
        "unknown": unknown,
    }
    for label, payload in blocked_searches.items():
        result = payload["results"][0]
        if result["can_open_generated_page"] or result["can_answer_chat"] or result["can_compare"]:
            return _blocked(
                "governed_golden_api_rendering",
                "blocked_asset_unlocked_generated_capability",
                {"case_id": label, "ticker": result["ticker"]},
            )

    exports = [asset_export, source_export, comparison_export, chat_export]
    if any(export["export_state"] != "available" for export in exports):
        return _blocked("governed_golden_api_rendering", "governed_export_unavailable")
    serialized_exports = json.dumps(exports, sort_keys=True).lower()
    for forbidden in [
        "raw_model_reasoning",
        "hidden_prompt",
        "unrestricted_provider_payload",
        "raw_transcript",
        "secret_value",
    ]:
        if forbidden in serialized_exports:
            return _blocked("governed_golden_api_rendering", "restricted_export_payload_detected", {"marker": forbidden})

    if overview["weekly_news_focus"]["selected_item_count"] != 1:
        return _blocked("governed_golden_api_rendering", "weekly_news_limited_fixture_missing")
    if overview["weekly_news_focus"]["evidence_limited_state"] != "limited_verified_set":
        return _blocked("governed_golden_api_rendering", "weekly_news_limit_state_not_preserved")
    if overview["ai_comprehensive_analysis"]["analysis_available"] is not False:
        return _blocked("governed_golden_api_rendering", "ai_analysis_threshold_not_enforced")
    if empty_weekly["weekly_news_focus"]["evidence_limited_state"] != "empty":
        return _blocked("governed_golden_api_rendering", "weekly_news_empty_state_not_preserved")
    if sources["drawer_state"] != "available" or not sources["source_groups"]:
        return _blocked("governed_golden_api_rendering", "source_drawer_not_available")
    if any(group["allowlist_status"] != "allowed" for group in sources["source_groups"]):
        return _blocked("governed_golden_api_rendering", "source_drawer_unapproved_source_visible")
    if any(not group["allowed_excerpts"] for group in sources["source_groups"]):
        return _blocked("governed_golden_api_rendering", "source_drawer_allowed_excerpt_missing")
    if comparison["evidence_availability"]["availability_state"] != "available":
        return _blocked("governed_golden_api_rendering", "comparison_evidence_unavailable")
    if chat["safety_classification"] != "educational" or not chat["citations"]:
        return _blocked("governed_golden_api_rendering", "grounded_chat_not_cited_or_safe")
    return _pass(
        "governed_golden_api_rendering",
        "governed_evidence_drives_api_surfaces",
        {
            "golden_assets": ["AAPL", "VOO", "QQQ"],
            "weekly_news_limited_count": overview["weekly_news_focus"]["selected_item_count"],
            "ai_analysis_minimum_weekly_items": overview["ai_comprehensive_analysis"][
                "minimum_weekly_news_item_count"
            ],
            "blocked_search_cases": sorted(blocked_searches),
            "export_surfaces": ["asset", "source_list", "comparison", "chat"],
        },
    )


def _check_local_fresh_data_mvp_slice_smoke() -> RehearsalCheck:
    check_id = "local_fresh_data_mvp_slice_smoke"
    result = run_slice_smoke()
    rows = result.get("rows", [])
    row_by_ticker = {row.get("ticker"): row for row in rows if isinstance(row, dict)}
    expected_supported = ["AAPL", "MSFT", "NVDA", "VOO", "SPY", "VTI", "QQQ", "XLK"]
    expected_blocked = ["TQQQ", "ARKK", "BND", "GLD"]
    expected_status_counts = {"pass": 5, "partial": 3, "blocked": 4, "unavailable": 0}
    blockers = list(result.get("blockers") or [])

    if result.get("status") != "pass":
        blockers.append(
            {
                "reason_code": "slice_smoke_status_not_pass",
                "status": result.get("status"),
            }
        )
    if result.get("status_counts") != expected_status_counts:
        blockers.append(
            {
                "reason_code": "slice_smoke_status_counts_mismatch",
                "expected": expected_status_counts,
                "actual": result.get("status_counts"),
            }
        )
    if result.get("supported_renderable_tickers") != expected_supported:
        blockers.append(
            {
                "reason_code": "slice_supported_tickers_mismatch",
                "expected": expected_supported,
                "actual": result.get("supported_renderable_tickers"),
            }
        )
    if result.get("blocked_regression_tickers") != expected_blocked:
        blockers.append(
            {
                "reason_code": "slice_blocked_tickers_mismatch",
                "expected": expected_blocked,
                "actual": result.get("blocked_regression_tickers"),
            }
        )
    if result.get("raw_payload_exposed_count") != 0 or result.get("raw_payload_values_reported"):
        blockers.append(
            {
                "reason_code": "slice_raw_payload_exposed",
                "raw_payload_exposed_count": result.get("raw_payload_exposed_count"),
                "raw_payload_values_reported": result.get("raw_payload_values_reported"),
            }
        )
    if result.get("secret_values_reported"):
        blockers.append({"reason_code": "slice_secret_values_reported"})
    if any(not row.get("no_live_external_calls") for row in rows):
        blockers.append({"reason_code": "slice_live_external_call_required"})
    for ticker in expected_supported:
        row = row_by_ticker.get(ticker)
        if not row or row.get("generated_output_eligible") is not True or row.get("source_count", 0) <= 0:
            blockers.append(
                {
                    "reason_code": "slice_supported_row_not_renderable",
                    "ticker": ticker,
                    "row": row,
                }
            )
    for ticker in ("VOO", "QQQ"):
        row = row_by_ticker.get(ticker)
        if not row or row.get("issuer_backed") is not True or row.get("fetch_state") != "supported":
            blockers.append(
                {
                    "reason_code": "slice_issuer_backed_etf_not_supported",
                    "ticker": ticker,
                    "row": row,
                }
            )
    for ticker in ("SPY", "VTI", "XLK"):
        row = row_by_ticker.get(ticker)
        if not row or row.get("issuer_evidence_state") != "partial" or row.get("fetch_state") != "partial":
            blockers.append(
                {
                    "reason_code": "slice_partial_etf_state_mismatch",
                    "ticker": ticker,
                    "row": row,
                }
            )
    for ticker in expected_blocked:
        row = row_by_ticker.get(ticker)
        if not row or row.get("status") != "blocked" or row.get("generated_output_eligible") is not False:
            blockers.append(
                {
                    "reason_code": "slice_blocked_row_not_blocked",
                    "ticker": ticker,
                    "row": row,
                }
            )
        elif row.get("source_count") or row.get("citation_count") or row.get("fact_count") or row.get("fetch_call_count"):
            blockers.append(
                {
                    "reason_code": "slice_blocked_row_exposed_evidence_or_fetch",
                    "ticker": ticker,
                    "row": row,
                }
            )

    details = {
        "schema_version": result.get("schema_version"),
        "slice_name": result.get("slice_name"),
        "policy": result.get("policy"),
        "normal_ci_requires_live_calls": result.get("normal_ci_requires_live_calls"),
        "browser_startup_required": result.get("browser_startup_required"),
        "local_services_required": result.get("local_services_required"),
        "secret_values_reported": result.get("secret_values_reported"),
        "raw_payload_values_reported": result.get("raw_payload_values_reported"),
        "raw_payload_exposed_count": result.get("raw_payload_exposed_count"),
        "status_definitions": result.get("status_definitions"),
        "supported_renderable_tickers": result.get("supported_renderable_tickers"),
        "issuer_backed_etf_tickers": result.get("issuer_backed_etf_tickers"),
        "partial_etf_tickers": result.get("partial_etf_tickers"),
        "blocked_regression_tickers": result.get("blocked_regression_tickers"),
        "blocked_generated_surfaces": result.get("blocked_generated_surfaces"),
        "status_counts": result.get("status_counts"),
        "rows": rows,
        "blockers": blockers,
    }
    if blockers:
        return _blocked(check_id, "local_fresh_data_mvp_slice_smoke_blocked", details)
    return _pass(check_id, "local_fresh_data_mvp_slice_smoke_passed", details)


def _check_stock_vs_etf_comparison_readiness(root: Path) -> RehearsalCheck:
    check_id = "stock_vs_etf_comparison_readiness"
    client = TestClient(app)

    compare_response = client.post("/api/compare", json={"left_ticker": "AAPL", "right_ticker": "VOO"})
    if compare_response.status_code != 200:
        return _blocked(
            check_id,
            "no_local_pack",
            {"endpoint": "POST /api/compare", "status_code": compare_response.status_code},
        )
    comparison = compare_response.json()
    blocker = _stock_vs_etf_compare_payload_blocker(comparison)
    if blocker:
        return _blocked(check_id, blocker["reason_code"], blocker)

    export_response = client.get(
        "/api/compare/export",
        params={"left_ticker": "AAPL", "right_ticker": "VOO", "export_format": "json"},
    )
    if export_response.status_code != 200:
        return _blocked(
            check_id,
            "unavailable_export",
            {"endpoint": "GET /api/compare/export", "status_code": export_response.status_code},
        )
    comparison_export = export_response.json()
    blocker = _stock_vs_etf_export_payload_blocker(comparison_export)
    if blocker:
        return _blocked(check_id, blocker["reason_code"], blocker)

    chat_response = client.post("/api/assets/VOO/chat", json={"question": "AAPL vs VOO"})
    if chat_response.status_code != 200:
        return _blocked(
            check_id,
            "chat_redirect_mismatch",
            {"endpoint": "POST /api/assets/VOO/chat", "status_code": chat_response.status_code},
        )
    chat = chat_response.json()
    blocker = _stock_vs_etf_chat_redirect_blocker(chat)
    if blocker:
        return _blocked(check_id, blocker["reason_code"], blocker)

    blocked_case_summaries: list[dict[str, Any]] = []
    for left, right, expected_state in (
        ("VOO", "BTC", "unsupported"),
        ("VOO", "GME", "out_of_scope"),
        ("VOO", "SPY", "eligible_not_cached"),
        ("VOO", "ZZZZ", "unknown"),
        ("AAPL", "QQQ", "no_local_pack"),
    ):
        blocked_response = client.post("/api/compare", json={"left_ticker": left, "right_ticker": right})
        if blocked_response.status_code != 200:
            reason_code = "no_local_pack" if expected_state == "no_local_pack" else "unsupported_state_regression"
            return _blocked(
                check_id,
                reason_code,
                {
                    "case_id": f"{left}_{right}",
                    "expected_availability_state": expected_state,
                    "status_code": blocked_response.status_code,
                },
            )
        blocked_payload = blocked_response.json()
        blocker = _blocked_comparison_case_regression(left, right, expected_state, blocked_payload)
        if blocker:
            return _blocked(check_id, blocker["reason_code"], blocker)
        blocked_case_summaries.append(
            {
                "left_ticker": left,
                "right_ticker": right,
                "availability_state": blocked_payload["evidence_availability"]["availability_state"],
                "generated_output_blocked": True,
            }
        )

    etf_baseline = client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json()
    if (
        etf_baseline.get("comparison_type") != "etf_vs_etf"
        or etf_baseline.get("evidence_availability", {}).get("availability_state") != "available"
        or not etf_baseline.get("citations")
        or not etf_baseline.get("source_documents")
    ):
        return _blocked(
            check_id,
            "unsupported_state_regression",
            {
                "case_id": "VOO_QQQ_etf_vs_etf_baseline",
                "comparison_type": etf_baseline.get("comparison_type"),
                "availability_state": etf_baseline.get("evidence_availability", {}).get("availability_state"),
            },
        )

    frontend_alignment = _stock_vs_etf_frontend_alignment(root)
    if frontend_alignment.get("blocked"):
        return _blocked(check_id, frontend_alignment["reason_code"], frontend_alignment)

    comparison_evidence = comparison["evidence_availability"]
    relationship = comparison["stock_etf_relationship"]
    export_validation = comparison_export["export_validation"]
    chat_route = chat["compare_route_suggestion"]
    return _pass(
        check_id,
        "aapl_voo_stock_vs_etf_comparison_ready",
        {
            "schema_version": "stock-vs-etf-comparison-readiness-v1",
            "boundary": "review_only_fixture_backed_no_services_no_live_calls_v1",
            "deterministic_pairs": {
                "stock_vs_etf": ["AAPL", "VOO"],
                "etf_vs_etf_baseline": ["VOO", "QQQ"],
                "broad_coverage_proven": False,
            },
            "backend_compare": {
                "endpoint": "POST /api/compare",
                "state_status": comparison["state"]["status"],
                "comparison_type": comparison["comparison_type"],
                "availability_state": comparison_evidence["availability_state"],
                "relationship_schema_version": relationship["schema_version"],
                "relationship_state": relationship["relationship_state"],
                "basket_structure": "single-company-vs-etf-basket",
                "badge_markers": sorted({badge["marker"] for badge in relationship["badges"]}),
                "citation_count": len(comparison["citations"]),
                "source_document_count": len(comparison["source_documents"]),
                "source_reference_assets": sorted(
                    {reference["asset_ticker"] for reference in comparison_evidence["source_references"]}
                ),
                "old_frontend_only_holding_verified_present": False,
            },
            "comparison_export": {
                "endpoint": "GET /api/compare/export",
                "export_state": comparison_export["export_state"],
                "comparison_type": comparison_export["metadata"]["comparison_type"],
                "binding_scope": export_validation["binding_scope"],
                "same_comparison_pack_citation_bindings_only": export_validation["diagnostics"][
                    "same_comparison_pack_citation_bindings_only"
                ],
                "same_comparison_pack_source_bindings_only": export_validation["diagnostics"][
                    "same_comparison_pack_source_bindings_only"
                ],
                "relationship_context_section_present": True,
                "citation_count": len(comparison_export["citations"]),
                "source_document_count": len(comparison_export["source_documents"]),
                "educational_disclaimer_present": True,
                "forbidden_advice_phrase_hits": [],
            },
            "chat_compare_redirect": {
                "endpoint": "POST /api/assets/VOO/chat",
                "safety_classification": chat["safety_classification"],
                "comparison_availability_state": chat_route["comparison_availability_state"],
                "route": chat_route["route"],
                "generated_multi_asset_chat_answer": chat_route["diagnostics"]["generated_multi_asset_chat_answer"],
                "factual_citation_count": len(chat["citations"]),
                "factual_source_document_count": len(chat["source_documents"]),
            },
            "frontend_api_alignment": frontend_alignment,
            "unsupported_blocking_cases": blocked_case_summaries,
            "etf_vs_etf_baseline": {
                "left_ticker": "VOO",
                "right_ticker": "QQQ",
                "comparison_type": etf_baseline["comparison_type"],
                "availability_state": etf_baseline["evidence_availability"]["availability_state"],
                "independent_of_stock_vs_etf_markers": True,
            },
            "blocker_reason_code_catalog": [
                "no_local_pack",
                "missing_backend_relationship_schema",
                "frontend_only_fallback",
                "unavailable_export",
                "chat_redirect_mismatch",
                "missing_source_citation_metadata",
                "missing_local_smoke_instructions",
                "unsupported_state_regression",
                "live_call_requirement",
            ],
            "review_only_boundaries": {
                "services_started": False,
                "live_provider_calls": False,
                "live_news_calls": False,
                "live_market_data_calls": False,
                "live_llm_calls": False,
                "sources_approved": False,
                "manifests_promoted": False,
                "generated_output_cache_entries_written": False,
                "comparison_coverage_broadened": False,
            },
        },
    )


def _stock_vs_etf_compare_payload_blocker(payload: dict[str, Any]) -> dict[str, Any] | None:
    evidence = payload.get("evidence_availability") or {}
    diagnostics = evidence.get("diagnostics") or {}
    if diagnostics.get("live_provider_calls_attempted") or diagnostics.get("live_llm_calls_attempted"):
        return {
            "reason_code": "live_call_requirement",
            "surface": "compare",
            "diagnostics": diagnostics,
        }
    if (
        payload.get("state", {}).get("status") != "supported"
        or payload.get("comparison_type") != "stock_vs_etf"
        or evidence.get("availability_state") != "available"
    ):
        return {
            "reason_code": "no_local_pack",
            "surface": "compare",
            "state_status": payload.get("state", {}).get("status"),
            "comparison_type": payload.get("comparison_type"),
            "availability_state": evidence.get("availability_state"),
        }
    relationship = payload.get("stock_etf_relationship")
    if not isinstance(relationship, dict):
        return {"reason_code": "missing_backend_relationship_schema", "surface": "compare"}
    if "holding_verified" in json.dumps(relationship, sort_keys=True):
        return {"reason_code": "frontend_only_fallback", "surface": "compare"}
    badges = relationship.get("badges") or []
    badge_markers = {badge.get("marker") for badge in badges if isinstance(badge, dict)}
    basket = relationship.get("basket_structure") or {}
    expected_dimensions = {"Structure", "Basket membership", "Breadth", "Cost model", "Educational role"}
    basket_dimension = next(
        (
            dimension
            for dimension in evidence.get("required_evidence_dimensions", [])
            if dimension.get("dimension") == "Basket membership"
        ),
        {},
    )
    relationship_contract_ok = (
        relationship.get("schema_version") == "stock-etf-relationship-v1"
        and relationship.get("comparison_type") == "stock_vs_etf"
        and relationship.get("stock_ticker") == "AAPL"
        and relationship.get("etf_ticker") == "VOO"
        and relationship.get("relationship_state") == "direct_holding"
        and {"relationship_state", "evidence_boundary"} <= badge_markers
        and basket.get("stock_ticker") == "AAPL"
        and basket.get("etf_ticker") == "VOO"
        and basket.get("overlap_or_membership_state") == "direct_holding"
        and basket.get("evidence_state") == "partial"
        and set(evidence.get("required_dimensions") or []) == expected_dimensions
        and basket_dimension.get("evidence_state") == "partial"
    )
    if not relationship_contract_ok:
        return {
            "reason_code": "missing_backend_relationship_schema",
            "surface": "compare",
            "relationship": {
                "schema_version": relationship.get("schema_version"),
                "comparison_type": relationship.get("comparison_type"),
                "relationship_state": relationship.get("relationship_state"),
                "badge_markers": sorted(marker for marker in badge_markers if marker),
                "basket_overlap_state": basket.get("overlap_or_membership_state"),
                "required_dimensions": evidence.get("required_dimensions"),
            },
        }
    citation_ids = {citation.get("citation_id") for citation in payload.get("citations", [])}
    source_document_ids = {source.get("source_document_id") for source in payload.get("source_documents", [])}
    source_reference_assets = {reference.get("asset_ticker") for reference in evidence.get("source_references", [])}
    citation_binding_assets = {binding.get("asset_ticker") for binding in evidence.get("citation_bindings", [])}
    source_metadata_ok = (
        bool(citation_ids)
        and bool(source_document_ids)
        and {"AAPL", "VOO"} <= source_reference_assets
        and {"AAPL", "VOO"} <= citation_binding_assets
        and diagnostics.get("same_comparison_pack_sources_only") is True
        and all(
            source.get("url") and source.get("source_use_policy") and source.get("supporting_passage")
            for source in payload.get("source_documents", [])
        )
        and all(
            reference.get("url") and reference.get("source_use_policy") and reference.get("permitted_operations")
            for reference in evidence.get("source_references", [])
        )
    )
    if not source_metadata_ok:
        return {
            "reason_code": "missing_source_citation_metadata",
            "surface": "compare",
            "citation_count": len(citation_ids),
            "source_document_count": len(source_document_ids),
            "source_reference_assets": sorted(asset for asset in source_reference_assets if asset),
            "citation_binding_assets": sorted(asset for asset in citation_binding_assets if asset),
        }
    return None


def _stock_vs_etf_export_payload_blocker(payload: dict[str, Any]) -> dict[str, Any] | None:
    validation = payload.get("export_validation") or {}
    diagnostics = validation.get("diagnostics") or {}
    if diagnostics.get("no_live_external_calls") is not True:
        return {"reason_code": "live_call_requirement", "surface": "export", "diagnostics": diagnostics}
    section_ids = {section.get("section_id") for section in payload.get("sections", [])}
    disclaimer = payload.get("disclaimer") or ""
    forbidden_hits = find_forbidden_output_phrases(json.dumps(payload, sort_keys=True))
    export_ok = (
        payload.get("content_type") == "comparison"
        and payload.get("export_state") == "available"
        and payload.get("left_asset", {}).get("ticker") == "AAPL"
        and payload.get("right_asset", {}).get("ticker") == "VOO"
        and payload.get("metadata", {}).get("comparison_type") == "stock_vs_etf"
        and validation.get("binding_scope") == "same_comparison_pack"
        and diagnostics.get("same_comparison_pack_citation_bindings_only") is True
        and diagnostics.get("same_comparison_pack_source_bindings_only") is True
        and "stock_etf_relationship_context" in section_ids
        and bool(payload.get("citations"))
        and bool(payload.get("source_documents"))
        and bool(validation.get("citation_bindings"))
        and bool(validation.get("source_bindings"))
        and "not investment, financial, legal, or tax advice" in disclaimer.lower()
        and "not a recommendation to buy, sell, or hold" in disclaimer.lower()
        and not forbidden_hits
        and all(
            source.get("url")
            and source.get("source_use_policy")
            and source.get("retrieved_at")
            and source.get("freshness_state")
            and source.get("allowed_excerpt", {}).get("text")
            for source in payload.get("source_documents", [])
        )
    )
    if not export_ok:
        return {
            "reason_code": "unavailable_export",
            "surface": "export",
            "export_state": payload.get("export_state"),
            "comparison_type": payload.get("metadata", {}).get("comparison_type"),
            "binding_scope": validation.get("binding_scope"),
            "section_ids": sorted(section_id for section_id in section_ids if section_id),
            "citation_count": len(payload.get("citations", [])),
            "source_document_count": len(payload.get("source_documents", [])),
            "forbidden_advice_phrase_hits": forbidden_hits,
        }
    return None


def _stock_vs_etf_chat_redirect_blocker(payload: dict[str, Any]) -> dict[str, Any] | None:
    route = payload.get("compare_route_suggestion") or {}
    diagnostics = route.get("diagnostics") or {}
    redirect_ok = (
        payload.get("safety_classification") == "compare_route_redirect"
        and route.get("schema_version") == "chat-compare-route-v1"
        and route.get("left_ticker") == "AAPL"
        and route.get("right_ticker") == "VOO"
        and route.get("route") == "/compare?left=AAPL&right=VOO"
        and route.get("comparison_availability_state") == "available"
        and diagnostics.get("generated_multi_asset_chat_answer") is False
        and payload.get("citations") == []
        and payload.get("source_documents") == []
        and not find_forbidden_output_phrases(json.dumps(payload, sort_keys=True))
    )
    if not redirect_ok:
        return {
            "reason_code": "chat_redirect_mismatch",
            "surface": "chat",
            "safety_classification": payload.get("safety_classification"),
            "route": route.get("route"),
            "comparison_availability_state": route.get("comparison_availability_state"),
            "generated_multi_asset_chat_answer": diagnostics.get("generated_multi_asset_chat_answer"),
            "citation_count": len(payload.get("citations", [])),
            "source_document_count": len(payload.get("source_documents", [])),
        }
    return None


def _blocked_comparison_case_regression(
    left: str,
    right: str,
    expected_state: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    evidence = payload.get("evidence_availability") or {}
    generated_output_present = bool(
        payload.get("key_differences")
        or payload.get("bottom_line_for_beginners")
        or payload.get("citations")
        or payload.get("source_documents")
        or evidence.get("evidence_items")
        or evidence.get("claim_bindings")
        or evidence.get("citation_bindings")
        or evidence.get("source_references")
    )
    if (
        payload.get("comparison_type") != "unavailable"
        or evidence.get("availability_state") != expected_state
        or generated_output_present
    ):
        reason_code = "no_local_pack" if expected_state == "no_local_pack" else "unsupported_state_regression"
        return {
            "reason_code": reason_code,
            "case_id": f"{left}_{right}",
            "expected_availability_state": expected_state,
            "actual_availability_state": evidence.get("availability_state"),
            "comparison_type": payload.get("comparison_type"),
            "generated_output_present": generated_output_present,
        }
    return None


def _stock_vs_etf_frontend_alignment(root: Path) -> dict[str, Any]:
    source_markers = {
        "apps/web/app/page.tsx": [
            "data-home-primary-workflow=\"single-supported-stock-or-etf-search\"",
            "data-home-workflow-card=\"separate-comparison\"",
        ],
        "apps/web/components/SearchBox.tsx": [
            "data-search-comparison-route",
            "data-search-open-comparison-route",
        ],
        "apps/web/app/compare/page.tsx": [
            "separate-comparison-workflow-v1",
            "data-compare-comparison-type",
            "data-stock-etf-relationship-schema",
            "data-stock-etf-relationship-state",
            "data-relationship-badge",
            "data-stock-etf-basket-structure=\"single-company-vs-etf-basket\"",
        ],
        "apps/web/components/ComparisonSourceDetails.tsx": [
            "data-comparison-source-asset",
        ],
        "apps/web/next.config.mjs": [
            "NEXT_PUBLIC_API_BASE_URL",
            "API_BASE_URL",
            "source: \"/api/:path*\"",
            "destination: `${apiBaseUrl}/api/:path*`",
        ],
    }
    smoke_markers = {
        "tests/frontend/smoke.mjs": [
            "AAPL vs VOO search pattern routes to compare without changing home into a comparison builder",
            "assertAaplVooComparePayload",
            "assertAaplVooExportPayload",
            "assertAaplVooChatRedirectPayload",
            "LEARN_TICKER_LOCAL_BROWSER_SMOKE",
            "LEARN_TICKER_LOCAL_WEB_BASE",
            "LEARN_TICKER_LOCAL_API_BASE",
            "NEXT_PUBLIC_API_BASE_URL",
            "API_BASE_URL",
            "/api/:path*",
            "/compare?left=AAPL&right=VOO",
            "stock-etf-relationship-v1",
            "direct_holding",
            "single-company-vs-etf-basket",
        ],
        "docs/local_fresh_data_ingest_to_render_runbook.md": [
            "LEARN_TICKER_LOCAL_BROWSER_SMOKE=1",
            "LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000",
            "LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000",
            "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000",
            "API_BASE_URL=http://127.0.0.1:8000",
            "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000",
            "Next `/api/:path*`",
            "`AAPL` vs `VOO` returns `comparison_type = stock_vs_etf`",
            "`POST /api/assets/VOO/chat` with `AAPL vs VOO` redirects",
            "existing `VOO` vs `QQQ` ETF-vs-ETF comparison behavior remains available",
        ],
    }
    missing_source_markers = _missing_text_markers(root, source_markers)
    if missing_source_markers:
        return {
            "blocked": True,
            "reason_code": "frontend_only_fallback",
            "missing": missing_source_markers,
        }

    frontend_payload_sources = [
        (root / "apps/web/app/compare/page.tsx").read_text(encoding="utf-8"),
        (root / "apps/web/lib/compare.ts").read_text(encoding="utf-8"),
    ]
    if any("holding_verified" in source for source in frontend_payload_sources):
        return {
            "blocked": True,
            "reason_code": "frontend_only_fallback",
            "legacy_marker": "holding_verified",
        }

    missing_smoke_markers = _missing_text_markers(root, smoke_markers)
    if missing_smoke_markers:
        return {
            "blocked": True,
            "reason_code": "missing_local_smoke_instructions",
            "missing": missing_smoke_markers,
        }

    return {
        "blocked": False,
        "source_marker_file_count": len(source_markers),
        "local_smoke_marker_file_count": len(smoke_markers),
        "a_vs_b_search_routes_to_separate_compare_workflow": True,
        "aapl_voo_opt_in_smoke_covered": True,
        "next_api_proxy_documented": True,
        "operator_local_env_vars_documented": [
            "LEARN_TICKER_LOCAL_BROWSER_SMOKE",
            "LEARN_TICKER_LOCAL_WEB_BASE",
            "LEARN_TICKER_LOCAL_API_BASE",
            "NEXT_PUBLIC_API_BASE_URL",
            "API_BASE_URL",
            "CORS_ALLOWED_ORIGINS",
        ],
    }


def _missing_text_markers(root: Path, markers_by_path: dict[str, list[str]]) -> list[str]:
    missing: list[str] = []
    for relative, markers in markers_by_path.items():
        text = (root / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                missing.append(f"{relative}:{marker}")
    return missing


def _check_launch_manifest_review_packets(root: Path) -> RehearsalCheck:
    candidate_path = root / "data/universes/us_common_stocks_top500.candidate.2026-04.json"
    diff_path = root / "data/universes/us_common_stocks_top500.diff.2026-04.json"
    candidate = Top500CandidateManifest.model_validate(_read_json(candidate_path))
    diff = Top500CandidateDiffReport.model_validate(_read_json(diff_path))
    top500 = inspect_top500_candidate_review_packet(candidate_manifest=candidate, diff_report=diff)
    etf = build_etf_launch_review_packet()
    if top500["launch_approved"] or not top500["manual_promotion_required"]:
        return _blocked("launch_manifest_review_packets", "top500_packet_improperly_launch_approved")
    if etf["launch_approved"] or not etf["manual_promotion_required"]:
        return _blocked("launch_manifest_review_packets", "etf_packet_improperly_launch_approved")
    if etf["recognition_rows_unlock_generated_output"]:
        return _blocked("launch_manifest_review_packets", "recognition_rows_unlock_generated_output")
    readiness_counts = etf["readiness_counts"]
    eligible_scope = etf["eligible_universe_scope"]
    golden_regression = etf["golden_precache_regression"]
    etf500_review = etf["etf500_review_contract"]
    etf500_diagnostics = etf500_review["diagnostics"]
    required_categories = set(eligible_scope["required_category_names"])
    expected_categories = {
        "broad_us_index",
        "total_market_or_large_cap",
        "size_style",
        "sector",
        "industry_or_theme",
        "dividend",
        "value_growth",
        "quality",
        "momentum",
        "low_volatility",
        "equal_weight",
        "esg_index",
    }
    if required_categories != expected_categories:
        return _blocked(
            "launch_manifest_review_packets",
            "etf_eligible_universe_scope_categories_incomplete",
            {"required_categories": sorted(required_categories)},
        )
    if not golden_regression["eligible_supported_count_exceeds_golden_precache_count"]:
        return _blocked("launch_manifest_review_packets", "etf_golden_set_treated_as_coverage_limit")
    if readiness_counts["source_pack_ready"] != 0 or etf["review_status"] != "review_needed":
        return _blocked("launch_manifest_review_packets", "etf_fixture_manifest_improperly_marked_source_ready")
    if not etf["current_fixture_not_launch_coverage"]:
        return _blocked("launch_manifest_review_packets", "etf_current_fixture_improperly_marked_launch_coverage")
    if etf500_review["generated_output_blocking_rules"]["recognition_only_rows_unlock_generated_output"]:
        return _blocked("launch_manifest_review_packets", "etf500_recognition_only_rows_unblocked_generated_output")
    return _pass(
        "launch_manifest_review_packets",
        "manifest_packets_are_review_only",
        {
            "top500_review_status": top500["review_status"],
            "etf_review_status": etf["review_status"],
            "top500_fixture_or_local_only": top500["fixture_or_local_only_contract"],
            "etf_supported_authority": etf["supported_runtime_authority"],
            "etf_recognition_authority": etf["recognition_runtime_authority"],
            "etf_golden_set_is_coverage_limit": etf["golden_set_is_coverage_limit"],
            "etf_eligible_supported_entry_count": etf["eligible_supported_entry_count"],
            "etf_generated_output_eligible_count": etf["generated_output_eligible_count"],
            "etf_pending_ingestion_count": etf["pending_ingestion_count"],
            "etf_excluded_product_count": etf["excluded_product_count"],
            "etf_readiness_counts": readiness_counts,
            "etf_eligible_universe_scope_version": eligible_scope["scope_version"],
            "etf_represented_eligible_category_count": eligible_scope["represented_category_count"],
            "etf_scope_defined_no_current_rows": eligible_scope["scope_defined_no_current_rows"],
            "etf_full_eligible_universe_count": golden_regression["full_eligible_universe_count"],
            "etf_non_golden_eligible_supported_count": golden_regression["non_golden_eligible_supported_count"],
            "etf_represented_categories_beyond_golden": golden_regression["represented_categories_beyond_golden"],
            "etf500_review_contract_version": etf500_review["contract_version"],
            "etf500_practical_supported_row_range": etf["etf500_target_metadata"][
                "practical_supported_row_range"
            ],
            "etf500_batch_milestones": etf["etf500_target_metadata"]["batch_milestones"],
            "etf500_candidate_artifact_path_conventions": etf["etf500_target_metadata"][
                "candidate_artifact_path_conventions"
            ],
            "etf500_category_target_buckets": etf["etf500_target_metadata"]["category_target_buckets"],
            "etf500_current_fixture_not_launch_coverage": etf["current_fixture_not_launch_coverage"],
            "etf500_category_coverage_gap_count": len(etf500_diagnostics["category_coverage_gaps"]),
            "etf500_disqualifier_counts": etf500_diagnostics["disqualifier_counts"],
            "etf500_source_pack_readiness": etf500_diagnostics["source_pack_readiness"],
            "etf500_parser_handoff_readiness": etf500_diagnostics["parser_handoff_readiness"],
            "etf500_checksum_status": etf500_diagnostics["checksum_status"],
            "etf500_no_padding_stop_conditions": etf500_review["no_padding_stop_conditions"],
            "etf500_generated_output_blocking_rules": etf500_review["generated_output_blocking_rules"],
        },
    )


def _check_stock_sec_source_pack_readiness(root: Path) -> RehearsalCheck:
    packet = build_stock_sec_source_pack_readiness_packet(root=root)
    planning = build_top500_sec_source_pack_batch_plan(root=root, stock_readiness_packet=packet)
    counts = packet["readiness_counts"]
    if packet["manifests_promoted"] or packet["sources_approved_by_packet"] or packet["launch_approved"]:
        return _blocked("stock_sec_source_pack_readiness", "stock_sec_readiness_improperly_approved")
    if counts["review_packet_unlocks_generated_output"]:
        return _blocked("stock_sec_source_pack_readiness", "stock_sec_readiness_unlocked_generated_output")
    if counts["current_manifest_rows"] == 0 or counts["candidate_manifest_rows"] == 0:
        return _blocked("stock_sec_source_pack_readiness", "stock_sec_readiness_manifest_rows_missing", counts)
    if counts["source_backed_partial_rendering_ready"] == 0:
        return _blocked("stock_sec_source_pack_readiness", "stock_sec_partial_rendering_ready_row_missing", counts)
    if packet["review_status"] not in {"pass", "review_needed", "blocked"}:
        return _blocked(
            "stock_sec_source_pack_readiness",
            "stock_sec_readiness_status_invalid",
            {"review_status": packet["review_status"]},
        )
    if not planning["review_only"] or planning["runtime_manifest_authority"] != packet["runtime_manifest_authority"]:
        return _blocked(
            "stock_sec_source_pack_readiness",
            "top500_sec_batch_plan_boundary_invalid",
            {
                "review_only": planning["review_only"],
                "runtime_manifest_authority": planning["runtime_manifest_authority"],
            },
        )
    if (
        planning["generated_output_unlocked_by_plan"]
        or planning["sources_approved_by_plan"]
        or planning["planner_started_ingestion"]
        or planning["top500_manifest_promoted"]
    ):
        return _blocked(
            "stock_sec_source_pack_readiness",
            "top500_sec_batch_plan_mutated_state",
            {
                "generated_output_unlocked_by_plan": planning["generated_output_unlocked_by_plan"],
                "sources_approved_by_plan": planning["sources_approved_by_plan"],
                "planner_started_ingestion": planning["planner_started_ingestion"],
                "top500_manifest_promoted": planning["top500_manifest_promoted"],
            },
        )
    return _pass(
        "stock_sec_source_pack_readiness",
        "stock_sec_readiness_packet_is_review_only",
        {
            "review_status": packet["review_status"],
            "runtime_manifest_authority": packet["runtime_manifest_authority"],
            "candidate_manifest_paths": packet["candidate_manifest_paths"],
            "required_sec_components": packet["required_sec_components"],
            "readiness_counts": counts,
            "blocked_generated_surfaces": packet["blocked_generated_surfaces"],
            "top500_sec_source_pack_batch_planning": {
                "schema_version": planning["schema_version"],
                "boundary": planning["boundary"],
                "current_manifest_path": planning["current_manifest_path"],
                "support_resolved_from_current_manifest_only": planning[
                    "support_resolved_from_current_manifest_only"
                ],
                "candidate_or_priority_data_resolves_runtime_support": planning[
                    "candidate_or_priority_data_resolves_runtime_support"
                ],
                "live_provider_or_exchange_data_resolves_runtime_support": planning[
                    "live_provider_or_exchange_data_resolves_runtime_support"
                ],
                "candidate_relationship_diagnostics": planning["candidate_relationship_diagnostics"],
                "planning_summary": planning["planning_summary"],
                "manifest_rank_ordering": planning["manifest_rank_ordering"],
                "batch_groups": planning["batch_groups"],
                "source_pack_status_groups": planning["source_pack_status_groups"],
                "readiness_priority_groups": planning["readiness_priority_groups"],
                "source_handoff_readiness": planning["source_handoff_readiness"],
                "parser_readiness": planning["parser_readiness"],
                "freshness_as_of_checksum_placeholder_status": planning[
                    "freshness_as_of_checksum_placeholder_status"
                ],
                "stop_conditions": planning["stop_conditions"],
                "blocked_generated_surfaces": planning["blocked_generated_surfaces"],
            },
        },
    )


def _check_etf_issuer_source_pack_readiness() -> RehearsalCheck:
    packet = build_etf_issuer_source_pack_readiness_packet()
    planning = build_etf500_issuer_source_pack_batch_plan(issuer_readiness_packet=packet)
    counts = packet["readiness_counts"]
    if packet["manifests_promoted"] or packet["sources_approved_by_packet"] or packet["launch_approved"]:
        return _blocked("etf_issuer_source_pack_readiness", "etf_issuer_readiness_improperly_approved")
    if counts["readiness_packet_unlocks_generated_output"]:
        return _blocked("etf_issuer_source_pack_readiness", "etf_issuer_readiness_unlocked_generated_output")
    if packet["recognition_rows_unlock_generated_output"]:
        return _blocked("etf_issuer_source_pack_readiness", "etf_recognition_rows_unlocked_generated_output")
    if not packet["readiness_keyed_from_supported_manifest_only"]:
        return _blocked("etf_issuer_source_pack_readiness", "etf_readiness_not_keyed_from_supported_manifest")
    if counts["supported_manifest_rows"] == 0 or counts["recognition_only_rows"] == 0:
        return _blocked("etf_issuer_source_pack_readiness", "etf_readiness_rows_missing", counts)
    if counts["source_backed_partial_rendering_ready"] == 0:
        return _blocked("etf_issuer_source_pack_readiness", "etf_source_backed_partial_ready_row_missing", counts)
    if counts["blocked_recognition_only"] != counts["recognition_only_rows"]:
        return _blocked("etf_issuer_source_pack_readiness", "etf_recognition_only_rows_not_blocked", counts)
    if packet["review_status"] not in {"pass", "review_needed", "blocked"}:
        return _blocked(
            "etf_issuer_source_pack_readiness",
            "etf_issuer_readiness_status_invalid",
            {"review_status": packet["review_status"]},
        )
    if not planning["review_only"] or not planning["fallback_not_launch_coverage"]:
        return _blocked(
            "etf_issuer_source_pack_readiness",
            "etf500_source_pack_batch_plan_boundary_invalid",
            {
                "review_only": planning["review_only"],
                "fallback_not_launch_coverage": planning["fallback_not_launch_coverage"],
            },
        )
    if planning["generated_output_unlocked_by_plan"] or planning["sources_approved_by_plan"]:
        return _blocked(
            "etf_issuer_source_pack_readiness",
            "etf500_source_pack_batch_plan_mutated_state",
            {
                "generated_output_unlocked_by_plan": planning["generated_output_unlocked_by_plan"],
                "sources_approved_by_plan": planning["sources_approved_by_plan"],
            },
        )
    return _pass(
        "etf_issuer_source_pack_readiness",
        "etf_issuer_readiness_packet_is_review_only",
        {
            "review_status": packet["review_status"],
            "supported_runtime_authority": packet["supported_runtime_authority"],
            "recognition_runtime_authority": packet["recognition_runtime_authority"],
            "required_issuer_source_components": packet["required_issuer_source_components"],
            "readiness_counts": counts,
            "blocked_generated_surfaces": packet["blocked_generated_surfaces"],
            "etf500_source_pack_batch_planning": {
                "schema_version": planning["schema_version"],
                "boundary": planning["boundary"],
                "candidate_review_metadata_consumed": planning["candidate_review_metadata_consumed"],
                "candidate_artifacts_available": planning["candidate_artifacts_available"],
                "fallback_to_current_fixture_review_metadata": planning[
                    "fallback_to_current_fixture_review_metadata"
                ],
                "fallback_not_launch_coverage": planning["fallback_not_launch_coverage"],
                "planning_summary": planning["planning_summary"],
                "batch_groups": planning["batch_groups"],
                "category_bucket_groups": planning["category_bucket_groups"],
                "issuer_groups": planning["issuer_groups"],
                "support_review_state_groups": planning["support_review_state_groups"],
                "source_pack_readiness_priority_groups": planning["source_pack_readiness_priority_groups"],
                "target_context": planning["target_context"],
                "blocked_generated_surfaces": planning["blocked_generated_surfaces"],
            },
        },
    )


def _check_local_ingestion_priority_planner(root: Path) -> RehearsalCheck:
    plan = build_local_ingestion_priority_plan(root=str(root))
    if plan["schema_version"] != "local-ingestion-priority-plan-v1":
        return _blocked("local_ingestion_priority_planner", "local_ingestion_priority_plan_schema_invalid")
    for boundary_key in (
        "review_only",
        "deterministic",
        "batchable",
        "resumable",
        "no_live_external_calls",
    ):
        if plan[boundary_key] is not True:
            return _blocked(
                "local_ingestion_priority_planner",
                "local_ingestion_priority_plan_boundary_invalid",
                {"boundary_key": boundary_key, "value": plan[boundary_key]},
            )
    for mutation_key in (
        "planner_started_ingestion",
        "sources_approved_by_planner",
        "manifests_promoted",
        "generated_output_cache_entries_written",
        "generated_output_unlocked_for_blocked_assets",
        "recognition_manifest_used_for_priority_order",
        "recognition_rows_unlock_generated_output",
    ):
        if plan[mutation_key] is not False:
            return _blocked(
                "local_ingestion_priority_planner",
                "local_ingestion_priority_plan_mutated_state",
                {"mutation_key": mutation_key, "value": plan[mutation_key]},
            )
    first_batch = plan["batches"][0]  # type: ignore[index]
    first_tickers = [row["ticker"] for row in first_batch["items"]]  # type: ignore[index]
    if first_tickers != ["AAPL", "VOO", "QQQ"]:
        return _blocked(
            "local_ingestion_priority_planner",
            "local_ingestion_priority_plan_high_demand_order_invalid",
            {"first_tickers": first_tickers},
        )
    state_keys = set(plan["state_diagnostics"]["states"])  # type: ignore[index]
    required_states = {
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
    }
    if not required_states.issubset(state_keys):
        return _blocked(
            "local_ingestion_priority_planner",
            "local_ingestion_priority_plan_state_keys_missing",
            {"state_keys": sorted(state_keys)},
        )
    if any(row["generated_output_unlocked_by_planner"] for row in plan["blocked_or_not_ready"]):  # type: ignore[index]
        return _blocked("local_ingestion_priority_planner", "local_ingestion_priority_plan_unlocked_blocked_output")
    return _pass(
        "local_ingestion_priority_planner",
        "local_ingestion_priority_plan_is_review_only_and_resumable",
        {
            "schema_version": plan["schema_version"],
            "boundary": plan["boundary"],
            "summary": plan["summary"],
            "first_batch_tickers": first_tickers,
            "state_diagnostics": plan["state_diagnostics"],
            "supported_etf_runtime_authority": plan["supported_etf_runtime_authority"],
            "recognition_runtime_authority": plan["recognition_runtime_authority"],
            "recognition_manifest_used_for_priority_order": plan["recognition_manifest_used_for_priority_order"],
            "recognition_rows_unlock_generated_output": plan["recognition_rows_unlock_generated_output"],
            "top500_runtime_authority": plan["top500_runtime_authority"],
            "blocked_generated_surfaces": plan["blocked_generated_surfaces"],
        },
    )


def _check_frontend_markers(root: Path) -> RehearsalCheck:
    markers = {
        "apps/web/app/page.tsx": [
            "data-home-primary-workflow=\"single-supported-stock-or-etf-search\"",
            "data-home-workflow-card=\"separate-comparison\"",
        ],
        "apps/web/components/SearchBox.tsx": [
            "data-home-primary-action=\"single-asset-search\"",
            "data-search-comparison-route",
        ],
        "apps/web/components/SourceDrawer.tsx": [
            "data-source-drawer-mobile-presentation=\"bottom-sheet\"",
            "data-governed-golden-source-drawer=\"api-backed-source-groups\"",
        ],
        "apps/web/components/GlossaryPopover.tsx": [
            "data-glossary-desktop-interaction=\"hover-click-focus-escape\"",
            "data-glossary-mobile-presentation=\"bottom-sheet\"",
        ],
        "apps/web/components/AssetChatPanel.tsx": [
            "data-asset-chat-mobile-presentation=\"bottom-sheet-or-full-screen\"",
            "data-asset-chat-comparison-redirect=\"/compare\"",
        ],
        "apps/web/components/WeeklyNewsPanel.tsx": [
            "data-weekly-news-configured-max",
            "data-weekly-news-limited-verified-set",
        ],
        "apps/web/components/AIComprehensiveAnalysisPanel.tsx": [
            "data-ai-analysis-minimum-weekly-news-items",
            "What Changed This Week",
        ],
        "apps/web/app/compare/page.tsx": [
            "separate-comparison-workflow-v1",
            "data-stock-etf-basket-structure=\"single-company-vs-etf-basket\"",
        ],
        "apps/web/components/ExportControls.tsx": [
            "data-export-supported-scope=\"markdown-json-citations-sources-freshness-disclaimer\"",
            "data-export-raw-model-reasoning=\"false\"",
        ],
    }
    missing: list[str] = []
    for relative, required_markers in markers.items():
        text = (root / relative).read_text(encoding="utf-8")
        for marker in required_markers:
            if marker not in text:
                missing.append(f"{relative}:{marker}")
    if missing:
        return _blocked("frontend_v04_smoke_markers", "frontend_marker_missing", {"missing": missing})
    return _pass(
        "frontend_v04_smoke_markers",
        "single_search_compare_glossary_source_chat_markers_preserved",
        {"checked_file_count": len(markers)},
    )


def _check_optional_browser_services(env: dict[str, str]) -> RehearsalCheck:
    if not _bool_env(env.get(BROWSER_OPT_IN_ENV)):
        return _skipped("optional_browser_services", "browser_services_opt_in_missing")
    web_base = _base_url(env.get(WEB_BASE_ENV), "3000")
    api_base = _base_url(env.get(API_BASE_ENV), "8000")
    try:
        home = _http_text(f"{web_base}/")
        search = _http_text(f"{api_base}/api/search?q=VOO%20vs%20QQQ", origin=web_base)
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _blocked("optional_browser_services", "localhost_web_or_api_unreachable", {"error_type": type(exc).__name__})
    if "data-home-workflow-baseline" not in home:
        return _blocked("optional_browser_services", "home_single_search_marker_missing")
    if "comparison_route" not in search and "can_compare" not in search:
        return _blocked("optional_browser_services", "api_comparison_route_marker_missing")
    return _pass("optional_browser_services", "already_running_localhost_services_passed", {"web_base": web_base, "api_base": api_base})


def _check_optional_durable_repositories(env: dict[str, str]) -> RehearsalCheck:
    if not _bool_env(env.get(DURABLE_OPT_IN_ENV)):
        return _skipped("optional_local_durable_repositories", "durable_repository_opt_in_missing")
    settings = build_local_durable_repository_settings(env=env)
    if not settings.can_construct:
        return _blocked(
            "optional_local_durable_repositories",
            "local_durable_repository_prerequisites_missing",
            settings.safe_diagnostics,
        )
    return _pass(
        "optional_local_durable_repositories",
        "local_durable_repository_prerequisites_present",
        settings.safe_diagnostics,
    )


def _check_optional_official_source_retrieval(env: dict[str, str]) -> RehearsalCheck:
    if not _bool_env(env.get(OFFICIAL_RETRIEVAL_OPT_IN_ENV)):
        return _skipped("optional_official_source_retrieval", "official_source_retrieval_opt_in_missing")
    lightweight_settings = build_lightweight_data_settings(env=env)
    strict_settings = build_live_acquisition_settings(env=env)
    if not lightweight_settings.can_fetch_fresh_data:
        return _blocked(
            "optional_official_source_retrieval",
            "lightweight_fresh_data_fetch_prerequisites_missing",
            {
                "lightweight_settings": lightweight_settings.safe_diagnostics,
                "strict_audit_settings": strict_settings.safe_diagnostics,
                "required_env_names_without_values": [
                    "DATA_POLICY_MODE",
                    "LIGHTWEIGHT_LIVE_FETCH_ENABLED",
                    "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED",
                    "SEC_EDGAR_USER_AGENT",
                ],
            },
        )
    smoke_tickers = ["AAPL", "VOO"]
    responses = [fetch_lightweight_asset_data(ticker, settings=lightweight_settings) for ticker in smoke_tickers]
    blocked = [
        {
            "ticker": response.ticker,
            "fetch_state": response.fetch_state.value,
            "source_count": len(response.sources),
            "fact_count": len(response.facts),
        }
        for response in responses
        if response.fetch_state.value not in {"supported", "partial"} or not response.sources or not response.facts
    ]
    if blocked:
        return _blocked(
            "optional_official_source_retrieval",
            "lightweight_fresh_data_fetch_blocked",
            {
                "blocked": blocked,
                "settings": lightweight_settings.safe_diagnostics,
                "raw_payload_exposed": any(response.raw_payload_exposed for response in responses),
            },
        )
    return _pass(
        "optional_official_source_retrieval",
        "lightweight_fresh_data_fetch_passed",
        {
            "settings": lightweight_settings.safe_diagnostics,
            "smoke_tickers": smoke_tickers,
            "responses": [
                {
                    "ticker": response.ticker,
                    "fetch_state": response.fetch_state.value,
                    "asset_type": response.asset.asset_type.value,
                    "source_labels": sorted({source.source_label.value for source in response.sources}),
                    "official_source_count": response.diagnostics.get("official_source_count", 0),
                    "provider_fallback_source_count": response.diagnostics.get("provider_fallback_source_count", 0),
                    "fact_count": len(response.facts),
                    "gap_count": len(response.gaps),
                    "raw_payload_exposed": response.raw_payload_exposed,
                }
                for response in responses
            ],
            "strict_audit_quality_approval": False,
        },
    )


def _check_optional_live_ai_review(env: dict[str, str]) -> RehearsalCheck:
    if not _bool_env(env.get(LIVE_AI_OPT_IN_ENV)):
        return _skipped("optional_live_ai_review", "live_ai_review_opt_in_missing")
    from scripts.run_live_ai_validation_smoke import SMOKE_OPT_IN_ENV, run_live_ai_validation_smoke

    smoke_env = dict(env)
    smoke_env[SMOKE_OPT_IN_ENV] = "true"
    result = run_live_ai_validation_smoke(smoke_env)
    if result["status"] == "blocked":
        return _blocked(
            "optional_live_ai_review",
            "live_ai_validation_smoke_blocked",
            _scrub_live_ai_result(result),
        )
    return _pass("optional_live_ai_review", "live_ai_validation_smoke_passed", _scrub_live_ai_result(result))


def _configured_golden_repositories():
    knowledge_repo = InMemoryAssetKnowledgePackRepository()
    generated_repo = InMemoryGeneratedOutputCacheRepository()
    weekly_repo = InMemoryWeeklyNewsEventEvidenceRepository()
    source_snapshot_repo = InMemorySourceSnapshotArtifactRepository()

    for ticker in ["AAPL", "VOO", "QQQ"]:
        _persist_fixture_knowledge_pack(knowledge_repo, ticker)
        _persist_fixture_source_snapshots(source_snapshot_repo, ticker)
        persisted_pack = _asset_knowledge_pack_from_repository_records(knowledge_repo.read_knowledge_pack_records(ticker))
        persisted_overview = generate_overview_from_pack(persisted_pack)
        _maybe_write_overview_generated_output_cache(persisted_overview, persisted_pack, generated_repo)
        generate_asset_chat(ticker, "What is this asset?", generated_output_cache_writer=generated_repo)
        _persist_weekly_news(
            weekly_repo,
            ticker,
            [_weekly_candidate(ticker, "official_fixture_update")] if ticker == "QQQ" else [],
        )
    generate_comparison("VOO", "QQQ", generated_output_cache_writer=generated_repo)
    return knowledge_repo, generated_repo, weekly_repo, source_snapshot_repo


def _persist_fixture_knowledge_pack(repository: InMemoryAssetKnowledgePackRepository, ticker: str) -> None:
    repository.persist(
        AssetKnowledgePackRepository().serialize(
            build_asset_knowledge_pack_result(ticker),
            retrieval_pack=build_asset_knowledge_pack(ticker),
        )
    )


def _persist_fixture_source_snapshots(repository: InMemorySourceSnapshotArtifactRepository, ticker: str) -> None:
    response = build_asset_knowledge_pack_result(ticker)
    records = SourceSnapshotRepositoryRecords(
        artifacts=[
            artifact_from_knowledge_pack_source(
                source,
                artifact_id=f"rehearsal-{ticker.lower()}-{source.source_document_id}",
                artifact_category=(
                    SourceSnapshotArtifactCategory.raw_source
                    if source.source_use_policy is SourceUsePolicy.full_text_allowed
                    else SourceSnapshotArtifactCategory.summary
                ),
                checksum=f"sha256:rehearsal:{ticker.lower()}:{source.source_document_id}",
                byte_size=0,
                content_type="text/plain",
                created_at="2026-04-25T18:04:25Z",
                storage_key=f"snapshots/rehearsal/{ticker.lower()}/{source.source_document_id}.json",
                ingestion_job_id=f"pre-cache-launch-{ticker.lower()}",
            )
            for source in response.source_documents
        ]
    )
    repository.persist(records)


def _weekly_candidate(ticker: str, event_id: str) -> WeeklyNewsEventCandidateRow:
    citation_id = f"c_weekly_{ticker.lower()}_{event_id}"
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
        citation_ids=[citation_id],
        citation_asset_tickers={citation_id: ticker},
        source_type=WeeklyNewsSourceRankTier.official_filing.value,
        source_rank=1,
        source_rank_tier=WeeklyNewsSourceRankTier.official_filing.value,
        source_quality=SourceQuality.official.value,
        allowlist_status=SourceAllowlistStatus.allowed.value,
        source_use_policy=SourceUsePolicy.summary_allowed.value,
        freshness_state=FreshnessState.fresh.value,
        evidence_state="supported",
        importance_score=10,
        duplicate_group_id=event_id,
        candidate_decision="selected",
        title_checksum=f"sha256:title:{ticker}:{event_id}",
        evidence_checksum=f"sha256:evidence:{ticker}:{event_id}",
    )


def _persist_weekly_news(
    repository: InMemoryWeeklyNewsEventEvidenceRepository,
    ticker: str,
    candidates: list[WeeklyNewsEventCandidateRow],
) -> None:
    repository.persist(
        acquire_weekly_news_event_evidence_from_fixtures(
            asset_ticker=ticker,
            as_of="2026-04-23",
            created_at="2026-04-23T12:00:00Z",
            candidates=candidates,
        )
    )


def _http_text(url: str, *, origin: str | None = None) -> str:
    headers = {"Origin": origin} if origin else {}
    request = Request(url, headers=headers)
    with urlopen(request, timeout=7) as response:
        return response.read().decode("utf-8", errors="replace")


def _base_url(value: str | None, fallback_port: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return f"http://127.0.0.1:{fallback_port}"
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    return cleaned.rstrip("/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scrub_live_ai_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status"),
        "provider_kind": result.get("provider_kind"),
        "readiness_status": result.get("readiness_status"),
        "live_generation_enabled": result.get("live_generation_enabled"),
        "server_side_key_present": result.get("server_side_key_present"),
        "cases": result.get("cases", []),
        "sanitized_diagnostics": result.get("sanitized_diagnostics", {}),
    }


def _build_local_mvp_threshold_summary(checks: list[RehearsalCheck]) -> dict[str, Any]:
    check_by_id = {check.check_id: check for check in checks}
    required_checks = [_threshold_check_summary(check_by_id[check_id]) for check_id in REQUIRED_THRESHOLD_CHECK_IDS]
    optional_checks = [_threshold_check_summary(check_by_id[check_id]) for check_id in OPTIONAL_THRESHOLD_CHECK_IDS]
    required_blockers = [check for check in required_checks if check["status"] != "pass"]
    optional_skipped_modes = [check for check in optional_checks if check["status"] == "skipped"]
    optional_blockers = [check for check in optional_checks if check["status"] == "blocked"]
    asset_state_summary = _build_threshold_asset_state_summary(check_by_id)

    threshold_blockers: list[dict[str, Any]] = []
    if required_blockers:
        threshold_blockers.append(
            {
                "reason_code": "required_check_blocked",
                "count": len(required_blockers),
                "check_ids": [check["check_id"] for check in required_blockers],
            }
        )
    if optional_blockers:
        threshold_blockers.append(
            {
                "reason_code": "optional_mode_blocked_after_explicit_opt_in",
                "count": len(optional_blockers),
                "check_ids": [check["check_id"] for check in optional_blockers],
            }
        )
    if asset_state_summary["failed_asset_count"] > ALLOWED_FAILED_ASSET_COUNT:
        threshold_blockers.append(
            {
                "reason_code": "failed_asset_count_exceeds_local_threshold",
                "count": asset_state_summary["failed_asset_count"],
                "allowed_count": ALLOWED_FAILED_ASSET_COUNT,
            }
        )
    if asset_state_summary["unavailable_asset_count"] > ALLOWED_UNAVAILABLE_ASSET_COUNT:
        threshold_blockers.append(
            {
                "reason_code": "unavailable_asset_count_exceeds_local_threshold",
                "count": asset_state_summary["unavailable_asset_count"],
                "allowed_count": ALLOWED_UNAVAILABLE_ASSET_COUNT,
            }
        )
    if asset_state_summary["generated_surface_violation_count"]:
        threshold_blockers.append(
            {
                "reason_code": "non_generated_asset_exposed_generated_surface",
                "count": asset_state_summary["generated_surface_violation_count"],
            }
        )

    local_status = "blocked_for_local_operator_review" if threshold_blockers else "ready_for_local_operator_review"
    return {
        "schema_version": "local-fresh-data-mvp-threshold-summary-v1",
        "threshold_contract": "review_only_no_launch_approval_v1",
        "overall_local_approval_status": local_status,
        "local_operator_review_ready": not threshold_blockers,
        "launch_or_public_deployment_approved": False,
        "required_checks": required_checks,
        "required_blockers": required_blockers,
        "optional_skipped_modes": optional_skipped_modes,
        "optional_blockers": optional_blockers,
        "threshold_blockers": threshold_blockers,
        "thresholds": {
            "required_blockers_allowed": 0,
            "optional_blockers_allowed": 0,
            "failed_assets_allowed": ALLOWED_FAILED_ASSET_COUNT,
            "unavailable_assets_allowed": ALLOWED_UNAVAILABLE_ASSET_COUNT,
            "generated_surface_violations_allowed": 0,
        },
        "asset_state_summary": asset_state_summary,
        "review_only_boundaries": {
            "sources_approved": False,
            "top500_manifest_promoted": False,
            "etf_supported_manifest_promoted": False,
            "etp_recognition_manifest_promoted": False,
            "ingestion_started": False,
            "generated_output_cache_entries_written": False,
            "production_services_started": False,
            "normal_ci_requires_live_calls": False,
        },
        "live_generation_validation_failure_fallback": {
            "generated_claims_allowed_after_failed_validation": False,
            "generated_chat_answers_allowed_after_failed_validation": False,
            "generated_comparisons_allowed_after_failed_validation": False,
            "weekly_news_focus_allowed_after_failed_validation": False,
            "ai_comprehensive_analysis_allowed_after_failed_validation": False,
            "exports_allowed_after_failed_validation": False,
            "generated_output_cache_entries_allowed_after_failed_validation": False,
            "fallback_section_states": [
                "partial",
                "stale",
                "unknown",
                "unavailable",
                "insufficient_evidence",
            ],
            "source_backed_partial_ready_count": asset_state_summary["source_backed_partial_ready_count"],
        },
    }


def _build_manual_fresh_data_readiness_gate(
    checks: list[RehearsalCheck],
    threshold_summary: dict[str, Any],
) -> dict[str, Any]:
    check_by_id = {check.check_id: check for check in checks}
    stop_conditions = _manual_readiness_stop_conditions(check_by_id, threshold_summary)
    decision = "agent_work_remaining" if stop_conditions else "manual_test_ready"
    return {
        "schema_version": "local-manual-fresh-data-readiness-gate-v1",
        "decision": decision,
        "task_ready_vs_manual_test_ready_decision": decision,
        "task_ready_for_manual_testing": decision == "manual_test_ready",
        "manual_test_ready": decision == "manual_test_ready",
        "agent_work_remaining": decision == "agent_work_remaining",
        "next_operator_action": (
            "finish_deterministic_agent_work_before_manual_fresh_data_testing"
            if stop_conditions
            else "run_manual_local_fresh_data_testing_with_explicit_opt_ins"
        ),
        "sanitized_operator_report": True,
        "review_only": True,
        "production_services_started": False,
        "live_sources_fetched": False,
        "live_llms_called": False,
        "sources_approved": False,
        "manifests_promoted": False,
        "ingestion_started": False,
        "generated_output_cache_entries_written": False,
        "generated_output_unlocked_for_unsupported_or_incomplete_assets": False,
        "prerequisite_summaries": _manual_readiness_prerequisite_summaries(check_by_id, threshold_summary),
        "stop_conditions": stop_conditions,
        "optional_mode_statuses": [
            _threshold_check_summary(check_by_id[check_id]) for check_id in OPTIONAL_THRESHOLD_CHECK_IDS
        ],
        "no_secret_diagnostics": {
            "secret_values_reported": False,
            "secret_values_requested": False,
            "safe_diagnostics_only": True,
            "opt_in_env_names_reported_without_values": [
                BROWSER_OPT_IN_ENV,
                DURABLE_OPT_IN_ENV,
                OFFICIAL_RETRIEVAL_OPT_IN_ENV,
                LIVE_AI_OPT_IN_ENV,
                WEB_BASE_ENV,
                API_BASE_ENV,
            ],
        },
        "blocked_generated_surfaces": threshold_summary["asset_state_summary"]["blocked_generated_surfaces"],
        "manual_test_checklist": _manual_fresh_data_test_checklist(),
        "decision_boundary": {
            "agent_work_remaining_when": [
                "required deterministic checks are absent or blocked",
                "ETF-500 review remains fixture-only or below reviewed target coverage",
                "ETF issuer source packs are incomplete or parser/handoff readiness is not clear",
                "Top-500 SEC source packs are incomplete, parser-not-ready, handoff-not-ready, or checksum-missing",
                "local ingestion priority planning still reports blocked or not-ready assets",
                "optional modes are explicitly enabled but blocked by safe prerequisite diagnostics",
                "unsupported, recognition-only, or incomplete assets expose any generated-output surface",
            ],
            "manual_test_ready_when": [
                "all deterministic prerequisite checks pass",
                "review packets and batch plans no longer report fixture-only or incomplete source-pack state",
                "parser, Golden Asset Source Handoff, freshness/as-of, and checksum prerequisites are ready",
                "generated-output blocking remains enforced for unsupported, recognition-only, and incomplete assets",
                "manual local browser/API testing is the next explicit operator action",
            ],
        },
    }


def _manual_readiness_prerequisite_summaries(
    check_by_id: dict[str, RehearsalCheck],
    threshold_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    launch = check_by_id["launch_manifest_review_packets"].details
    stock = check_by_id["stock_sec_source_pack_readiness"].details
    stock_plan = stock.get("top500_sec_source_pack_batch_planning", {})
    etf = check_by_id["etf_issuer_source_pack_readiness"].details
    etf_plan = etf.get("etf500_source_pack_batch_planning", {})
    ingestion = check_by_id["local_ingestion_priority_planner"].details
    frontend = check_by_id["frontend_v04_smoke_markers"]
    golden = check_by_id["governed_golden_api_rendering"]
    slice_smoke = check_by_id["local_fresh_data_mvp_slice_smoke"]
    stock_vs_etf = check_by_id["stock_vs_etf_comparison_readiness"]
    return [
        {
            "prerequisite_id": "t136_etf500_candidate_review",
            "check_id": "launch_manifest_review_packets",
            "status": check_by_id["launch_manifest_review_packets"].status,
            "review_status": launch.get("etf_review_status"),
            "fixture_only": launch.get("etf500_current_fixture_not_launch_coverage"),
            "category_gap_count": launch.get("etf500_category_coverage_gap_count"),
            "source_pack_readiness": launch.get("etf500_source_pack_readiness"),
            "parser_handoff_readiness": launch.get("etf500_parser_handoff_readiness"),
            "checksum_status": launch.get("etf500_checksum_status"),
        },
        {
            "prerequisite_id": "t137_etf_source_pack_batch_planning",
            "check_id": "etf_issuer_source_pack_readiness",
            "status": check_by_id["etf_issuer_source_pack_readiness"].status,
            "review_status": etf.get("review_status"),
            "readiness_counts": etf.get("readiness_counts"),
            "candidate_artifacts_available": etf_plan.get("candidate_artifacts_available"),
            "fallback_not_launch_coverage": etf_plan.get("fallback_not_launch_coverage"),
            "planning_summary": etf_plan.get("planning_summary"),
        },
        {
            "prerequisite_id": "t138_top500_sec_source_pack_batch_planning",
            "check_id": "stock_sec_source_pack_readiness",
            "status": check_by_id["stock_sec_source_pack_readiness"].status,
            "review_status": stock.get("review_status"),
            "readiness_counts": stock.get("readiness_counts"),
            "planning_summary": stock_plan.get("planning_summary"),
            "source_handoff_readiness": stock_plan.get("source_handoff_readiness"),
            "parser_readiness": stock_plan.get("parser_readiness"),
            "freshness_as_of_checksum_placeholder_status": stock_plan.get(
                "freshness_as_of_checksum_placeholder_status"
            ),
        },
        {
            "prerequisite_id": "local_mvp_thresholds",
            "status": threshold_summary["overall_local_approval_status"],
            "threshold_blocker_count": len(threshold_summary["threshold_blockers"]),
            "asset_state_summary": threshold_summary["asset_state_summary"],
        },
        {
            "prerequisite_id": "local_ingestion_priority_planning",
            "check_id": "local_ingestion_priority_planner",
            "status": check_by_id["local_ingestion_priority_planner"].status,
            "summary": ingestion.get("summary"),
            "state_diagnostics": ingestion.get("state_diagnostics"),
        },
        {
            "prerequisite_id": "governed_golden_rendering",
            "check_id": "governed_golden_api_rendering",
            "status": golden.status,
            "reason_code": golden.reason_code,
            "blocked_search_cases": golden.details.get("blocked_search_cases", []),
        },
        {
            "prerequisite_id": "t144_local_fresh_data_mvp_slice_smoke",
            "check_id": "local_fresh_data_mvp_slice_smoke",
            "status": slice_smoke.status,
            "reason_code": slice_smoke.reason_code,
            "status_counts": slice_smoke.details.get("status_counts"),
            "supported_renderable_tickers": slice_smoke.details.get("supported_renderable_tickers"),
            "blocked_regression_tickers": slice_smoke.details.get("blocked_regression_tickers"),
            "raw_payload_exposed_count": slice_smoke.details.get("raw_payload_exposed_count"),
            "secret_values_reported": slice_smoke.details.get("secret_values_reported"),
            "normal_ci_requires_live_calls": slice_smoke.details.get("normal_ci_requires_live_calls"),
        },
        {
            "prerequisite_id": "stock_vs_etf_comparison_readiness",
            "check_id": "stock_vs_etf_comparison_readiness",
            "status": stock_vs_etf.status,
            "reason_code": stock_vs_etf.reason_code,
            "deterministic_pairs": stock_vs_etf.details.get("deterministic_pairs"),
            "backend_compare": stock_vs_etf.details.get("backend_compare"),
            "comparison_export": stock_vs_etf.details.get("comparison_export"),
            "chat_compare_redirect": stock_vs_etf.details.get("chat_compare_redirect"),
            "frontend_api_alignment": stock_vs_etf.details.get("frontend_api_alignment"),
            "unsupported_blocking_cases": stock_vs_etf.details.get("unsupported_blocking_cases"),
        },
        {
            "prerequisite_id": "frontend_workflow_smoke_markers",
            "check_id": "frontend_v04_smoke_markers",
            "status": frontend.status,
            "reason_code": frontend.reason_code,
            "checked_file_count": frontend.details.get("checked_file_count"),
        },
    ]


def _manual_readiness_stop_conditions(
    check_by_id: dict[str, RehearsalCheck],
    threshold_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    stop_conditions: list[dict[str, Any]] = []
    for check in check_by_id.values():
        if check.check_id in OPTIONAL_THRESHOLD_CHECK_IDS:
            continue
        if check.status != "pass":
            stop_conditions.append(
                {
                    "reason_code": "required_deterministic_check_not_passed",
                    "check_id": check.check_id,
                    "status": check.status,
                    "check_reason_code": check.reason_code,
                }
            )
    for blocker in threshold_summary["threshold_blockers"]:
        stop_conditions.append({"reason_code": blocker["reason_code"], "details": blocker})

    launch = check_by_id["launch_manifest_review_packets"].details
    _append_if(
        stop_conditions,
        bool(launch.get("etf500_current_fixture_not_launch_coverage")),
        "etf500_review_fixture_only_not_launch_coverage",
        "launch_manifest_review_packets",
        {"current_fixture_not_launch_coverage": launch.get("etf500_current_fixture_not_launch_coverage")},
    )
    _append_if(
        stop_conditions,
        int(launch.get("etf500_category_coverage_gap_count") or 0) > 0,
        "etf500_category_review_gaps_remaining",
        "launch_manifest_review_packets",
        {"category_coverage_gap_count": launch.get("etf500_category_coverage_gap_count")},
    )
    etf500_source_pack = launch.get("etf500_source_pack_readiness", {})
    _append_if(
        stop_conditions,
        int(etf500_source_pack.get("incomplete_count") or 0) > 0 or int(etf500_source_pack.get("ready_count") or 0) == 0,
        "etf500_source_pack_incomplete",
        "launch_manifest_review_packets",
        etf500_source_pack,
    )
    etf500_parser_handoff = launch.get("etf500_parser_handoff_readiness", {})
    _append_if(
        stop_conditions,
        int(etf500_parser_handoff.get("handoff_not_ready_count") or 0) > 0
        or int(etf500_parser_handoff.get("unclear_rights_count") or 0) > 0,
        "etf500_handoff_not_ready_or_unclear_rights",
        "launch_manifest_review_packets",
        etf500_parser_handoff,
    )
    _append_if(
        stop_conditions,
        int(etf500_parser_handoff.get("parser_invalid_count") or 0) > 0,
        "etf500_parser_invalid",
        "launch_manifest_review_packets",
        etf500_parser_handoff,
    )
    etf500_checksums = launch.get("etf500_checksum_status", {})
    _append_if(
        stop_conditions,
        not all(bool(value) for value in etf500_checksums.values()),
        "etf500_checksum_missing_or_mismatched",
        "launch_manifest_review_packets",
        etf500_checksums,
    )

    etf = check_by_id["etf_issuer_source_pack_readiness"].details
    etf_plan = etf.get("etf500_source_pack_batch_planning", {})
    etf_plan_summary = etf_plan.get("planning_summary", {})
    _append_if(
        stop_conditions,
        not bool(etf_plan.get("candidate_artifacts_available")) or bool(etf_plan.get("fallback_not_launch_coverage")),
        "etf500_source_pack_batch_uses_fixture_fallback",
        "etf_issuer_source_pack_readiness",
        {
            "candidate_artifacts_available": etf_plan.get("candidate_artifacts_available"),
            "fallback_not_launch_coverage": etf_plan.get("fallback_not_launch_coverage"),
        },
    )
    _append_if(
        stop_conditions,
        int(etf_plan_summary.get("source_pack_incomplete_count") or 0) > 0
        or int(etf_plan_summary.get("source_pack_ready_count") or 0) == 0,
        "etf500_issuer_source_pack_batch_incomplete",
        "etf_issuer_source_pack_readiness",
        etf_plan_summary,
    )

    stock = check_by_id["stock_sec_source_pack_readiness"].details
    stock_counts = stock.get("readiness_counts", {})
    stock_plan = stock.get("top500_sec_source_pack_batch_planning", {})
    stock_plan_summary = stock_plan.get("planning_summary", {})
    _append_if(
        stop_conditions,
        int(stock_counts.get("insufficient_evidence") or 0) > 0
        or int(stock_plan_summary.get("insufficient_evidence_count") or 0) > 0,
        "top500_sec_source_pack_insufficient_evidence",
        "stock_sec_source_pack_readiness",
        {"readiness_counts": stock_counts, "planning_summary": stock_plan_summary},
    )
    stock_handoff = stock_plan.get("source_handoff_readiness", {})
    _append_if(
        stop_conditions,
        int(stock_handoff.get("pending_or_missing_component_count") or 0) > 0
        or int(stock_handoff.get("rejected_or_unclear_rights_component_count") or 0) > 0
        or int(stock_handoff.get("wrong_asset_component_count") or 0) > 0,
        "top500_sec_source_handoff_not_ready",
        "stock_sec_source_pack_readiness",
        stock_handoff,
    )
    stock_parser = stock_plan.get("parser_readiness", {})
    _append_if(
        stop_conditions,
        int(stock_parser.get("parser_not_ready_component_count") or 0) > 0,
        "top500_sec_parser_not_ready",
        "stock_sec_source_pack_readiness",
        stock_parser,
    )
    stock_freshness = stock_plan.get("freshness_as_of_checksum_placeholder_status", {})
    checksum_required = int(stock_freshness.get("checksum_required_count") or 0)
    checksum_present = int(stock_freshness.get("checksum_present_count") or 0)
    _append_if(
        stop_conditions,
        bool(stock_freshness.get("freshness_as_of_checksum_review_required"))
        or checksum_present < checksum_required,
        "top500_sec_freshness_or_checksum_not_ready",
        "stock_sec_source_pack_readiness",
        stock_freshness,
    )

    ingestion = check_by_id["local_ingestion_priority_planner"].details
    ingestion_summary = ingestion.get("summary", {})
    _append_if(
        stop_conditions,
        int(ingestion_summary.get("blocked_or_not_ready_count") or 0) > 0,
        "local_ingestion_priority_plan_has_blocked_or_not_ready_assets",
        "local_ingestion_priority_planner",
        ingestion_summary,
    )

    for optional in threshold_summary["optional_blockers"]:
        stop_conditions.append(
            {
                "reason_code": "optional_mode_blocked_after_explicit_opt_in",
                "check_id": optional["check_id"],
                "status": optional["status"],
                "check_reason_code": optional["reason_code"],
            }
        )
    return stop_conditions


def _append_if(
    stop_conditions: list[dict[str, Any]],
    condition: bool,
    reason_code: str,
    check_id: str,
    details: dict[str, Any],
) -> None:
    if condition:
        stop_conditions.append({"reason_code": reason_code, "check_id": check_id, "details": details})


def _manual_fresh_data_test_checklist() -> list[dict[str, str]]:
    return [
        {
            "check_id": "local_web_api_startup",
            "guidance": "Start the local web and FastAPI services manually; this gate does not start services.",
        },
        {
            "check_id": "api_base_proxy_cors",
            "guidance": "Verify NEXT_PUBLIC_API_BASE_URL, API_BASE_URL, CORS_ALLOWED_ORIGINS, and the Next /api/:path* rewrite path.",
        },
        {
            "check_id": "home_single_asset_search",
            "guidance": "Verify home remains one primary search for a single supported stock or ETF.",
        },
        {
            "check_id": "a_vs_b_compare_redirect",
            "guidance": "Verify clear A vs B searches route to /compare instead of turning home into a comparison builder.",
        },
        {
            "check_id": "source_drawer",
            "guidance": "Verify source drawer metadata on desktop and mobile bottom-sheet behavior.",
        },
        {
            "check_id": "citation_chips",
            "guidance": "Verify citation chips remain visible near supported factual claims.",
        },
        {
            "check_id": "freshness_labels",
            "guidance": "Verify freshness, stale, unknown, unavailable, partial, and insufficient-evidence labels.",
        },
        {
            "check_id": "exports",
            "guidance": "Verify Markdown and JSON exports include citations, source metadata, freshness, uncertainty labels, and the educational disclaimer.",
        },
        {
            "check_id": "comparison",
            "guidance": "Verify supported comparison flows for stock-vs-stock, ETF-vs-ETF, and stock-vs-ETF pairs.",
        },
        {
            "check_id": "stock_etf_relationship_badges",
            "guidance": "Verify stock-vs-ETF relationship badges and the single-company-vs-ETF-basket structure.",
        },
        {
            "check_id": "contextual_glossary",
            "guidance": "Verify desktop glossary hover/click/focus popovers and mobile tap bottom-sheet behavior.",
        },
        {
            "check_id": "asset_chat_mobile_behavior",
            "guidance": "Verify asset chat stays grounded and uses mobile bottom-sheet or full-screen behavior.",
        },
        {
            "check_id": "weekly_news_focus_limited_empty_states",
            "guidance": "Verify Weekly News Focus renders a smaller verified set or empty state when evidence is thin.",
        },
        {
            "check_id": "ai_comprehensive_analysis_threshold",
            "guidance": "Verify AI Comprehensive Analysis appears only when at least two approved Weekly News Focus items exist.",
        },
        {
            "check_id": "unsupported_recognition_only_blocking",
            "guidance": "Verify unsupported, out-of-scope, recognition-only, and incomplete assets cannot open generated pages, chat, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, or generated-output cache entries.",
        },
        {
            "check_id": "optional_durable_repositories",
            "guidance": "If explicitly opted in, validate local durable repository reads/writes using safe diagnostics only.",
        },
        {
            "check_id": "optional_official_source_retrieval",
            "guidance": "If explicitly opted in, validate official-source retrieval readiness without treating retrieval as evidence approval.",
        },
        {
            "check_id": "optional_live_ai_validation",
            "guidance": "If explicitly opted in, validate live AI with server-side configuration and sanitized diagnostics only.",
        },
    ]


def _threshold_check_summary(check: RehearsalCheck) -> dict[str, Any]:
    return {
        "check_id": check.check_id,
        "status": check.status,
        "reason_code": check.reason_code,
    }


def _build_threshold_asset_state_summary(check_by_id: dict[str, RehearsalCheck]) -> dict[str, Any]:
    non_generated_assets = _non_generated_asset_threshold_rows()
    job_state_counts = Counter(row["state"] for row in non_generated_assets)
    reason_codes_by_state: dict[str, list[str]] = {}
    for row in non_generated_assets:
        reason_codes_by_state.setdefault(row["state"], [])
        if row["reason_code"] not in reason_codes_by_state[row["state"]]:
            reason_codes_by_state[row["state"]].append(row["reason_code"])

    readiness_counts = _combined_readiness_counts(check_by_id)
    generated_surface_violations = [row for row in non_generated_assets if row["generated_surface_exposed"]]
    blocked_surfaces = _combined_blocked_generated_surfaces(check_by_id)
    return {
        "failed_asset_count": job_state_counts.get("failed", 0),
        "unavailable_asset_count": job_state_counts.get("unavailable", 0),
        "partial_count": readiness_counts.get("partial", 0),
        "stale_count": readiness_counts.get("stale", 0),
        "unknown_count": readiness_counts.get("unknown", 0) + job_state_counts.get("unknown", 0),
        "insufficient_evidence_count": readiness_counts.get("insufficient_evidence", 0),
        "source_backed_partial_ready_count": readiness_counts.get("source_backed_partial_rendering_ready", 0),
        "generated_surface_violation_count": len(generated_surface_violations),
        "reason_codes_by_state": {key: sorted(value) for key, value in sorted(reason_codes_by_state.items())},
        "non_generated_assets": non_generated_assets,
        "blocked_generated_surfaces": blocked_surfaces,
        "readiness_packet_counts": readiness_counts,
    }


def _non_generated_asset_threshold_rows() -> list[dict[str, Any]]:
    cases = (
        ("pre-cache-launch-spy", "pending_ingestion_supported_etf"),
        ("pre-cache-launch-nvda", "pending_ingestion_supported_stock"),
        ("pre-cache-launch-msft", "running_pre_cache_fixture"),
        ("pre-cache-launch-amzn", "failed_pre_cache_fixture"),
        ("pre-cache-unsupported-tqqq", "unsupported_complex_etf"),
        ("pre-cache-out-of-scope-gme", "out_of_scope_stock"),
        ("pre-cache-unknown-zzzz", "unknown_asset"),
        ("missing-pre-cache-job", "unavailable_job_fixture"),
    )
    rows: list[dict[str, Any]] = []
    for job_id, case_id in cases:
        job = get_pre_cache_job_status(job_id)
        reason_code = job.error_metadata.code if job.error_metadata else job.job_state.value
        capabilities = job.capabilities
        generated_surface_exposed = bool(
            job.generated_route
            or job.generated_output_available
            or job.citation_ids
            or job.source_document_ids
            or capabilities.can_open_generated_page
            or capabilities.can_answer_chat
            or capabilities.can_compare
        )
        rows.append(
            {
                "case_id": case_id,
                "ticker": job.ticker,
                "asset_type": job.asset_type.value,
                "state": job.job_state.value,
                "reason_code": reason_code,
                "generated_surface_exposed": generated_surface_exposed,
                "generated_route": job.generated_route,
                "generated_output_available": job.generated_output_available,
                "citation_count": len(job.citation_ids),
                "source_document_count": len(job.source_document_ids),
                "can_open_generated_page": capabilities.can_open_generated_page,
                "can_answer_chat": capabilities.can_answer_chat,
                "can_compare": capabilities.can_compare,
            }
        )
    return rows


def _combined_readiness_counts(check_by_id: dict[str, RehearsalCheck]) -> dict[str, int]:
    combined: Counter[str] = Counter()
    for check_id in ("stock_sec_source_pack_readiness", "etf_issuer_source_pack_readiness"):
        readiness = check_by_id[check_id].details.get("readiness_counts", {})
        for key in (
            "partial",
            "stale",
            "unknown",
            "insufficient_evidence",
            "source_backed_partial_rendering_ready",
        ):
            combined[key] += int(readiness.get(key, 0) or 0)
    return dict(sorted(combined.items()))


def _combined_blocked_generated_surfaces(check_by_id: dict[str, RehearsalCheck]) -> list[str]:
    surfaces: set[str] = set()
    for check_id in ("stock_sec_source_pack_readiness", "etf_issuer_source_pack_readiness"):
        surfaces.update(check_by_id[check_id].details.get("blocked_generated_surfaces", []))
    return sorted(surfaces)


def _guarded(check_id: str, fn: Callable[[], RehearsalCheck]) -> RehearsalCheck:
    try:
        return fn()
    except Exception as exc:
        return _blocked(check_id, "rehearsal_check_exception", {"error_type": type(exc).__name__, "message": str(exc)})


def _rollup_status(checks: list[RehearsalCheck]) -> str:
    if any(check.status == "blocked" for check in checks):
        return "blocked"
    if any(check.status == "pass" for check in checks):
        return "pass"
    return "skipped"


def _pass(check_id: str, reason_code: str, details: dict[str, Any] | None = None) -> RehearsalCheck:
    return RehearsalCheck(check_id=check_id, status="pass", reason_code=reason_code, details=details or {})


def _skipped(check_id: str, reason_code: str, details: dict[str, Any] | None = None) -> RehearsalCheck:
    return RehearsalCheck(check_id=check_id, status="skipped", reason_code=reason_code, details=details or {})


def _blocked(check_id: str, reason_code: str, details: dict[str, Any] | None = None) -> RehearsalCheck:
    return RehearsalCheck(check_id=check_id, status="blocked", reason_code=reason_code, details=details or {})


def _bool_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local fresh-data MVP rehearsal.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON diagnostics.")
    args = parser.parse_args(argv)
    result = run_rehearsal()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"local fresh-data MVP rehearsal: {result['status']}")
        for check in result["checks"]:
            print(f"- {check['status']}: {check['check_id']} ({check['reason_code']})")
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
