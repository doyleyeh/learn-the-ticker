#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
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
from backend.etf_universe import build_etf_launch_review_packet
from backend.generated_output_cache_repository import InMemoryGeneratedOutputCacheRepository
from backend.knowledge_pack_repository import AssetKnowledgePackRepository, InMemoryAssetKnowledgePackRepository
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
from backend.settings import build_live_acquisition_settings, build_local_durable_repository_settings
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
from backend.weekly_news_repository import (
    InMemoryWeeklyNewsEventEvidenceRepository,
    WeeklyNewsEventCandidateRow,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
)


SCHEMA_VERSION = "local-fresh-data-mvp-rehearsal-v1"
BROWSER_OPT_IN_ENV = "LTT_REHEARSAL_BROWSER_SERVICES_ENABLED"
DURABLE_OPT_IN_ENV = "LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED"
OFFICIAL_RETRIEVAL_OPT_IN_ENV = "LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED"
LIVE_AI_OPT_IN_ENV = "LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED"
WEB_BASE_ENV = "LEARN_TICKER_LOCAL_WEB_BASE"
API_BASE_ENV = "LEARN_TICKER_LOCAL_API_BASE"


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
        _guarded("launch_manifest_review_packets", lambda: _check_launch_manifest_review_packets(root)),
        _guarded("stock_sec_source_pack_readiness", lambda: _check_stock_sec_source_pack_readiness(root)),
        _guarded("frontend_v04_smoke_markers", lambda: _check_frontend_markers(root)),
        _guarded("optional_browser_services", lambda: _check_optional_browser_services(source_env)),
        _guarded("optional_local_durable_repositories", lambda: _check_optional_durable_repositories(source_env)),
        _guarded("optional_official_source_retrieval", lambda: _check_optional_official_source_retrieval(source_env)),
        _guarded("optional_live_ai_review", lambda: _check_optional_live_ai_review(source_env)),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": _rollup_status(checks),
        "default_mode": "deterministic_fixture_backed",
        "normal_ci_requires_live_calls": False,
        "production_services_started": False,
        "manifests_promoted": False,
        "sources_approved_by_rehearsal": False,
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
        },
    )


def _check_stock_sec_source_pack_readiness(root: Path) -> RehearsalCheck:
    packet = build_stock_sec_source_pack_readiness_packet(root=root)
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
    settings = build_live_acquisition_settings(env=env)
    if settings.status != "configured":
        return _blocked(
            "optional_official_source_retrieval",
            "official_source_retrieval_prerequisites_missing",
            settings.safe_diagnostics,
        )
    return _pass(
        "optional_official_source_retrieval",
        "official_source_retrieval_readiness_present_without_execution",
        settings.safe_diagnostics,
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
