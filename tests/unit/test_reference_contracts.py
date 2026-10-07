"""Dormant financial reference contracts retained from the pre-desktop app.

These fixtures never establish desktop readiness. See docs/MIGRATION.md.
"""
from pathlib import Path
import os
import socket

from scripts.run_local_fresh_data_rehearsal import run_rehearsal
from scripts.run_lightweight_mvp_readiness_gate import run_lightweight_mvp_readiness_gate

ROOT = Path(__file__).resolve().parents[2]


def read_file(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_reference_rehearsal_does_not_inherit_live_fetch(monkeypatch):
    # Windows asyncio creates a loopback socket pair even for in-process clients.
    attempts = []
    original_connect, original_lookup = socket.socket.connect, socket.getaddrinfo

    def check_host(host):
        if host not in ("127.0.0.1", "::1", "localhost"):
            attempts.append(host)
            raise AssertionError("Reference rehearsal attempted external networking")

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            check_host(address[0])
        return original_connect(sock, address)

    def guarded_lookup(host, *args, **kwargs):
        check_host(host)
        return original_lookup(host, *args, **kwargs)

    for name in ("CI", "GITHUB_ACTIONS", "BUILDKITE", "JENKINS_URL", "PYTEST_CURRENT_TEST", "LTT_STATIC_EVALS_RUNNING"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIGHTWEIGHT_LIVE_FETCH_ENABLED", "true")
    monkeypatch.setenv("ECONOMIC_INDICATORS_LIVE_FETCH_ENABLED", "true")
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_lookup)
    result = run_rehearsal(env={})
    assert attempts == []
    assert {check["check_id"] for check in result["checks"] if check["status"] == "blocked"} == {
        "local_deployment_env_smoke", "stock_vs_etf_comparison_readiness", "frontend_v04_smoke_markers"
    }, [check for check in result["checks"] if check["status"] == "blocked"]
    assert os.environ["LIGHTWEIGHT_LIVE_FETCH_ENABLED"] == "true"
    assert os.environ["ECONOMIC_INDICATORS_LIVE_FETCH_ENABLED"] == "true"
    assert attempts == []


def test_static_evals_disable_implicit_live_reference_defaults(monkeypatch):
    from backend.settings import build_lightweight_data_settings

    for name in ("CI", "GITHUB_ACTIONS", "BUILDKITE", "JENKINS_URL", "PYTEST_CURRENT_TEST"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LTT_STATIC_EVALS_RUNNING", "true")
    assert build_lightweight_data_settings(env={"DATA_POLICY_MODE": "lightweight"}).live_fetch_enabled is False


def test_retired_codex_operator_cannot_bypass_desktop_runtime():
    assert not (ROOT / "scripts/run_analysis_pack_codex.sh").exists()


def test_t158_lightweight_mvp_readiness_gate_blocks_opted_in_optional_failures_without_secrets():
    result = run_lightweight_mvp_readiness_gate(env={"LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED": "true"})

    assert result["schema_version"] == "lightweight-mvp-readiness-gate-v1"
    assert result["status"] == "blocked"
    assert result["reason_code"] == "lightweight_mvp_local_manual_review_blocked"
    assert result["local_personal_mvp_ready_for_manual_review"] is False
    assert result["production_ready"] is False
    assert result["public_launch_ready"] is False
    blocker_reasons = {blocker["reason_code"] for blocker in result["local_manual_review_blockers"]}
    assert "optional_operator_check_blocked_after_explicit_opt_in" in blocker_reasons
    assert "local_threshold_summary_not_ready" in blocker_reasons
    assert "lightweight_local_slice_gate_not_ready" in blocker_reasons
    optional_blockers = [
        blocker
        for blocker in result["local_manual_review_blockers"]
        if blocker["reason_code"] == "optional_operator_check_blocked_after_explicit_opt_in"
    ]
    assert optional_blockers == [
            {
                "reason_code": "optional_operator_check_blocked_after_explicit_opt_in",
                "check_id": "optional_local_durable_repositories",
                "check_reason_code": "local_durable_repository_prerequisites_missing",
            }
        ]
    assert result["no_secret_diagnostics"]["secret_values_reported"] is False
    assert result["no_secret_diagnostics"]["forbidden_value_marker_hits"] == []
    serialized = str(result)
    for forbidden in ["postgresql://", "Bearer ", "Authorization:", "BEGIN PRIVATE KEY", "sk-"]:
        assert forbidden not in serialized


def test_etf_universe_contract_files_are_local_metadata_only():
    manifest = read_file("data/universes/us_equity_etfs.current.json")
    module = read_file("backend/etf_universe.py")

    assert "us-equity-etf-universe-v1" in manifest
    assert "EQUITY_ETF_UNIVERSE_MANIFEST_URI" in manifest
    assert "no live provider" in manifest
    assert "recognized_unsupported" in manifest
    assert "eligible_not_cached" in manifest
    assert "unavailable" in manifest
    assert "ETFUniverseContractError" in module
    assert "load_etf_universe_manifest" in module

    combined = f"{manifest}\n{module}"
    for forbidden in [
        "BEGIN PRIVATE KEY",
        "OPENROUTER_API_KEY=",
        "FMP_API_KEY=",
        "ALPHA_VANTAGE_API_KEY=",
        "FINNHUB_API_KEY=",
        "TIINGO_API_KEY=",
        "EODHD_API_KEY=",
        "import requests",
        "import httpx",
        "boto3",
        "os.environ",
        "api_key",
    ]:
        assert forbidden not in combined


def test_weekly_news_event_evidence_repository_contract_is_dormant_metadata_only():
    repository = read_file("backend/repositories/weekly_news.py")
    shim = read_file("backend/weekly_news_repository.py")
    migration = read_file("alembic/versions/20260425_0008_weekly_news_event_evidence_contracts.py")

    combined = f"{repository}\n{shim}\n{migration}"

    assert "weekly-news-event-evidence-repository-contract-v1" in combined
    assert "weekly-news-live-acquisition-readiness-boundary-v1" in combined
    assert "weekly-news-official-source-mocked-acquisition-boundary-v1" in combined
    assert "weekly-news-official-source-mocked-fetch-boundary-v1" in combined
    assert "weekly-news-official-source-parser-adapter-boundary-v1" in combined
    assert "weekly_news_market_week_windows" in combined
    assert "weekly_news_event_candidates" in combined
    assert "weekly_news_selected_events" in combined
    assert "weekly_news_ai_thresholds" in combined
    assert "weekly_news_diagnostics" in combined
    assert "compute_weekly_news_window" in repository
    assert "no_live_external_calls" in repository
    assert "provider_or_llm_call_required" in repository
    assert "persisted_evidence_only" in repository
    assert "threshold_metadata_only" in repository

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in combined
    for forbidden in [
        "BEGIN PRIVATE KEY",
        "OPENROUTER_API_KEY=",
        "FMP_API_KEY=",
        "ALPHA_VANTAGE_API_KEY=",
        "FINNHUB_API_KEY=",
        "TIINGO_API_KEY=",
        "EODHD_API_KEY=",
        "import requests",
        "import httpx",
        "boto3",
        "os.environ",
        "api_key",
    ]:
        assert forbidden not in combined


def test_llm_transport_contract_is_backend_only_mock_injected_and_dormant():
    transport = read_file("backend/llm_transport.py")
    models = read_file("backend/models.py")
    combined = f"{transport}\n{models}"

    assert "llm-transport-contract-v1" in combined
    assert "call_openrouter_transport" in transport
    assert "TransportCallable" in transport
    assert "injected_transport_missing" in transport
    assert "explicit_live_transport_opt_in_missing" in transport
    assert "server_side_key_missing" in transport
    assert "openrouter_model_chain_missing" in transport
    assert "validation_not_ready" in transport
    assert "LlmTransportResult" in models
    assert "LlmTransportStatus" in models
    assert "LlmTransportMode" in models

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "openai",
        "anthropic",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
        "Authorization",
        "Bearer ",
    ]:
        assert forbidden not in transport


def test_t154_weekly_news_live_source_smoke_is_optional_in_rehearsal():
    passed = run_rehearsal(env={"LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED": "true"})
    checks = {check["check_id"]: check for check in passed["checks"]}

    assert passed["status"] == "blocked"
    assert checks["optional_weekly_news_live_source_smoke"]["status"] == "pass"
    weekly_details = checks["optional_weekly_news_live_source_smoke"]["details"]
    assert weekly_details["schema_version"] == "weekly-news-live-source-smoke-v1"
    assert weekly_details["normal_ci_requires_live_calls"] is False
    assert weekly_details["case_status_counts"] == {"pass": 5, "blocked": 0, "skipped": 0}
    case_summaries = {case["case_id"]: case for case in weekly_details["case_summaries"]}
    assert case_summaries["source_backed_official_first"]["selected_item_count"] == 3
    assert case_summaries["provider_metadata_adapter"]["selected_item_count"] == 2
    assert case_summaries["limited_verified_set"]["evidence_limited_state"] == "limited_verified_set"
    assert case_summaries["empty_evidence"]["evidence_limited_state"] == "empty"
    assert weekly_details["safe_diagnostics"]["secret_values_reported"] is False
    assert passed["lightweight_local_mvp_slice_manual_readiness_gate"]["decision"] == (
        "deterministic_local_slice_manual_review_ready"
    )

    real_source = run_rehearsal(
        env={
            "LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED": "true",
            "LTT_WEEKLY_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
        }
    )
    real_source_checks = {check["check_id"]: check for check in real_source["checks"]}
    assert real_source["status"] == "blocked"
    assert real_source_checks["optional_weekly_news_live_source_smoke"]["status"] == "pass"
    real_details = real_source_checks["optional_weekly_news_live_source_smoke"]["details"]
    assert real_details["source_retrieval_mode"] == "operator_real_source_document_acquisition"
    assert real_details["case_status_counts"] == {"pass": 5, "blocked": 0, "skipped": 0}
    assert real_details["case_summaries"][0]["case_id"] == "operator_real_source_aapl"
    assert real_source["lightweight_local_mvp_slice_manual_readiness_gate"]["decision"] == (
        "deterministic_local_slice_manual_review_ready"
    )
    serialized = str(real_source)
    for forbidden in ["Bearer ", "Authorization", "BEGIN PRIVATE KEY", "sk-", "raw article body"]:
        assert forbidden not in serialized


def test_sec_stock_acquisition_contract_is_backend_only_fixture_backed_and_sanitized():
    adapter = read_file("backend/provider_adapters/sec_stock.py")
    worker = read_file("backend/ingestion_worker.py")
    combined = f"{adapter}\n{worker}"

    assert "sec-stock-acquisition-boundary-v1" in adapter
    assert "sec-stock-mocked-http-fetch-boundary-v1" in adapter
    assert "sec-stock-parser-adapter-boundary-v1" in adapter
    assert "sec-stock-handoff-gated-execution-boundary-v1" in adapter
    assert "SecStockConfigurationReadiness" in adapter
    assert "build_sec_stock_acquisition_result" in adapter
    assert "execute_sec_stock_handoff_gated_official_source_acquisition" in adapter
    assert "user_agent_configured" in adapter
    assert "rate_limit_ready" in adapter
    assert "live_call_disabled" in adapter
    assert "wrote_source_snapshot: bool = False" in adapter
    assert "wrote_knowledge_pack: bool = False" in adapter
    assert "wrote_generated_output_cache: bool = False" in adapter
    assert "created_generated_asset_page: bool = False" in adapter
    assert "created_generated_chat_answer: bool = False" in adapter
    assert "created_generated_comparison: bool = False" in adapter
    assert "created_generated_risk_summary: bool = False" in adapter

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
        "Authorization",
        "Bearer ",
    ]:
        assert forbidden not in combined


def test_etf_issuer_acquisition_contract_is_backend_only_fixture_backed_and_sanitized():
    adapter = read_file("backend/provider_adapters/etf_issuer.py")
    worker = read_file("backend/ingestion_worker.py")
    combined = f"{adapter}\n{worker}"

    assert "etf-issuer-acquisition-boundary-v1" in adapter
    assert "etf-issuer-mocked-http-fetch-boundary-v1" in adapter
    assert "etf-issuer-parser-adapter-boundary-v1" in adapter
    assert "etf-issuer-handoff-gated-execution-boundary-v1" in adapter
    assert "EtfIssuerConfigurationReadiness" in adapter
    assert "build_etf_issuer_acquisition_result" in adapter
    assert "execute_etf_issuer_handoff_gated_official_source_acquisition" in adapter
    assert "issuer_source_configured" in adapter
    assert "rate_limit_ready" in adapter
    assert "live_call_disabled" in adapter
    assert "wrote_source_snapshot: bool = False" in adapter
    assert "wrote_knowledge_pack: bool = False" in adapter
    assert "wrote_generated_output_cache: bool = False" in adapter
    assert "created_generated_asset_page: bool = False" in adapter
    assert "created_generated_chat_answer: bool = False" in adapter
    assert "created_generated_comparison: bool = False" in adapter
    assert "created_generated_risk_summary: bool = False" in adapter

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
        "Authorization",
        "Bearer ",
    ]:
        assert forbidden not in combined


def test_local_fresh_data_rehearsal_default_is_deterministic_and_review_only():
    result = run_rehearsal(env={})

    assert result["schema_version"] == "local-fresh-data-mvp-rehearsal-v1"
    assert result["status"] == "blocked"
    assert result["normal_ci_requires_live_calls"] is False
    assert result["production_services_started"] is False
    assert result["launch_or_public_deployment_approved"] is False
    assert result["production_ready"] is False
    assert result["manifests_promoted"] is False
    assert result["sources_approved_by_rehearsal"] is False
    threshold = result["local_mvp_threshold_summary"]
    assert threshold["schema_version"] == "local-fresh-data-mvp-threshold-summary-v1"
    assert threshold["threshold_contract"] == "review_only_no_launch_approval_v1"
    assert threshold["overall_local_approval_status"] == "blocked_for_local_operator_review"
    assert threshold["local_operator_review_ready"] is False
    assert threshold["launch_or_public_deployment_approved"] is False
    assert threshold["required_blockers"] == [
        {"check_id": "local_deployment_env_smoke", "status": "blocked", "reason_code": "local_deployment_env_smoke_blocked"},
        {"check_id": "stock_vs_etf_comparison_readiness", "status": "blocked", "reason_code": "legacy_web_runtime_retired"},
        {"check_id": "frontend_v04_smoke_markers", "status": "blocked", "reason_code": "legacy_web_runtime_retired"},
    ]
    assert threshold["optional_blockers"] == []
    assert len(threshold["required_checks"]) == 12
    assert {check["check_id"] for check in threshold["required_checks"] if check["status"] != "pass"} == {
        "local_deployment_env_smoke", "stock_vs_etf_comparison_readiness", "frontend_v04_smoke_markers"
    }
    assert len(threshold["optional_skipped_modes"]) == 5
    assert threshold["thresholds"] == {
        "required_blockers_allowed": 0,
        "optional_blockers_allowed": 0,
        "failed_assets_allowed": 1,
        "unavailable_assets_allowed": 1,
        "generated_surface_violations_allowed": 0,
    }
    assert threshold["review_only_boundaries"] == {
        "sources_approved": False,
        "top500_manifest_promoted": False,
        "etf_supported_manifest_promoted": False,
        "etp_recognition_manifest_promoted": False,
        "ingestion_started": False,
        "generated_output_cache_entries_written": False,
        "production_services_started": False,
        "normal_ci_requires_live_calls": False,
    }
    statuses = {check["check_id"]: check["status"] for check in result["checks"]}
    assert statuses["deterministic_default_boundary"] == "pass"
    assert statuses["source_handoff_approval_gate"] == "pass"
    assert statuses["governed_golden_api_rendering"] == "pass"
    assert statuses["local_fresh_data_mvp_slice_smoke"] == "pass"
    assert statuses["local_deployment_env_smoke"] == "blocked"
    assert statuses["stock_vs_etf_comparison_readiness"] == "blocked"
    assert statuses["launch_manifest_review_packets"] == "pass"
    assert statuses["stock_sec_source_pack_readiness"] == "pass"
    assert statuses["local_ingestion_priority_planner"] == "pass"
    assert statuses["frontend_v04_smoke_markers"] == "blocked"
    assert statuses["optional_browser_services"] == "skipped"
    assert statuses["optional_local_durable_repositories"] == "skipped"
    assert statuses["optional_official_source_retrieval"] == "skipped"
    assert statuses["optional_weekly_news_live_source_smoke"] == "skipped"
    assert statuses["optional_live_ai_review"] == "skipped"
    slice_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "local_fresh_data_mvp_slice_smoke"
    )
    assert slice_details["schema_version"] == "local-fresh-data-mvp-slice-smoke-v1"
    assert slice_details["normal_ci_requires_live_calls"] is False
    assert slice_details["browser_startup_required"] is False
    assert slice_details["local_services_required"] is False
    assert slice_details["secret_values_reported"] is False
    assert slice_details["raw_payload_values_reported"] is False
    assert slice_details["raw_payload_exposed_count"] == 0
    assert slice_details["status_counts"] == {"pass": 8, "partial": 0, "blocked": 4, "unavailable": 0}
    assert slice_details["issuer_backed_etf_tickers"] == ["VOO", "QQQ", "SPY", "VTI", "XLK"]
    assert slice_details["partial_etf_tickers"] == []
    assert slice_details["supported_renderable_tickers"] == [
        "AAPL",
        "MSFT",
        "NVDA",
        "VOO",
        "SPY",
        "VTI",
        "QQQ",
        "XLK",
    ]
    assert slice_details["blocked_regression_tickers"] == ["TQQQ", "ARKK", "BND", "GLD"]
    slice_rows = {row["ticker"]: row for row in slice_details["rows"]}
    assert slice_rows["AAPL"]["source_labels"] == ["official", "provider_derived"]
    assert slice_rows["VOO"]["source_labels"] == ["official", "partial", "provider_derived"]
    assert slice_rows["VOO"]["issuer_backed"] is True
    assert slice_rows["QQQ"]["issuer_backed"] is True
    assert slice_rows["SPY"]["issuer_backed"] is True
    assert slice_rows["SPY"]["issuer_evidence_state"] == "supported"
    assert slice_rows["TQQQ"]["fetch_call_count"] == 0
    assert all(row["raw_payload_exposed"] is False for row in slice_rows.values())
    launch_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "launch_manifest_review_packets"
    )
    assert launch_details["etf_eligible_universe_scope_version"] == "etf-eligible-universe-review-scope-v1"
    assert launch_details["etf_readiness_counts"]["supported"] == 13
    assert launch_details["etf_readiness_counts"]["recognition_only"] == 9
    assert launch_details["etf_readiness_counts"]["source_pack_ready"] == 0
    assert launch_details["etf_readiness_counts"]["generated_output_eligible"] == 2
    assert launch_details["etf_full_eligible_universe_count"] == 13
    assert launch_details["etf_non_golden_eligible_supported_count"] == 11
    assert "sector" in launch_details["etf_represented_categories_beyond_golden"]
    assert launch_details["etf500_review_contract_version"] == "etf500-candidate-manifest-review-contract-v1"
    assert launch_details["etf500_practical_supported_row_range"] == {"minimum": 475, "maximum": 525}
    assert [milestone["batch"] for milestone in launch_details["etf500_batch_milestones"]] == [
        "ETF-50",
        "ETF-150",
        "ETF-300",
        "ETF-500",
    ]
    assert launch_details["etf500_candidate_artifact_path_conventions"] == [
        "data/universes/us_equity_etfs_supported.candidate.YYYY-MM.etf500.json",
        "data/universes/us_etp_recognition.candidate.YYYY-MM.json",
        "data/universes/us_equity_etfs.candidate.YYYY-MM.etf500.promotion-packet.json",
    ]
    target_buckets = {bucket["bucket_id"]: bucket for bucket in launch_details["etf500_category_target_buckets"]}
    assert target_buckets["broad_core_us_equity_beta"]["target_count"] == 45
    assert target_buckets["market_cap_and_size_style"]["target_count"] == 95
    assert target_buckets["sector_etfs"]["target_count"] == 120
    assert target_buckets["industry_theme_passive_us_equity"]["target_count"] == 105
    assert target_buckets["dividend_and_shareholder_yield_index"]["target_count"] == 55
    assert target_buckets["factor_smart_beta_and_equal_weight"]["target_count"] == 60
    assert target_buckets["esg_values_screened_us_equity_index"]["target_count"] == 20
    assert launch_details["etf500_current_fixture_not_launch_coverage"] is True
    assert launch_details["etf500_category_coverage_gap_count"] == 7
    assert launch_details["etf500_disqualifier_counts"]["leveraged_etf"] >= 1
    assert launch_details["etf500_disqualifier_counts"]["option_income_or_buffer_etf"] == 0
    assert launch_details["etf500_source_pack_readiness"]["ready_count"] == 0
    assert launch_details["etf500_source_pack_readiness"]["incomplete_count"] == 13
    assert launch_details["etf500_parser_handoff_readiness"]["handoff_not_ready_count"] >= 13
    assert launch_details["etf500_checksum_status"] == {
        "supported_checksum_matches": True,
        "recognition_checksum_matches": True,
    }
    blocked_matrix = {row["condition"]: row for row in launch_details["etf500_blocked_generated_surface_matrix"]}
    assert set(blocked_matrix) == {
        "recognition_only",
        "pending_review",
        "unavailable",
        "parser_invalid",
        "unclear_rights",
        "source_pack_incomplete",
        "leveraged_etf",
        "inverse_etf",
        "active_etf",
        "fixed_income_etf",
        "commodity_etf",
        "crypto_product",
        "single_stock_etf",
        "option_income_or_buffer_etf",
        "multi_asset_etf",
        "etn",
        "etv",
        "cef",
        "international_or_global_primary_exposure",
    }
    assert blocked_matrix["recognition_only"]["row_count"] == 9
    assert blocked_matrix["source_pack_incomplete"]["row_count"] == 13
    assert blocked_matrix["leveraged_etf"]["row_count"] >= 1
    assert blocked_matrix["international_or_global_primary_exposure"]["row_count"] == 0
    assert all(row["generated_output_unlocked"] is False for row in blocked_matrix.values())
    assert all("generated_output_cache_entries" in row["blocked_generated_surfaces"] for row in blocked_matrix.values())
    assert "do_not_pad_with_leveraged_etf" in launch_details["etf500_no_padding_stop_conditions"]
    assert "do_not_pad_with_option_income_or_buffer_etf" in launch_details["etf500_no_padding_stop_conditions"]
    assert "do_not_pad_with_cef" in launch_details["etf500_no_padding_stop_conditions"]
    assert launch_details["etf500_generated_output_blocking_rules"][
        "recognition_only_rows_unlock_generated_output"
    ] is False
    assert "generated_output_cache_entries" in launch_details["etf500_generated_output_blocking_rules"][
        "blocked_generated_surfaces"
    ]
    stock_sec_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "stock_sec_source_pack_readiness"
    )
    assert stock_sec_details["review_status"] == "review_needed"
    assert stock_sec_details["runtime_manifest_authority"] == "data/universes/us_common_stocks_top500.current.json"
    assert stock_sec_details["candidate_manifest_paths"] == [
        "data/universes/us_common_stocks_top500.candidate.2026-04.json"
    ]
    assert stock_sec_details["required_sec_components"] == [
        "sec_submissions",
        "latest_annual_filing",
        "latest_quarterly_filing_when_available",
        "xbrl_company_facts",
    ]
    assert stock_sec_details["readiness_counts"]["current_manifest_rows"] == 10
    assert stock_sec_details["readiness_counts"]["candidate_manifest_rows"] == 10
    assert stock_sec_details["readiness_counts"]["partial"] == 2
    assert stock_sec_details["readiness_counts"]["insufficient_evidence"] == 18
    assert stock_sec_details["readiness_counts"]["review_packet_unlocks_generated_output"] == 0
    top500_planning = stock_sec_details["top500_sec_source_pack_batch_planning"]
    assert top500_planning["schema_version"] == "top500-sec-source-pack-batch-plan-v1"
    assert top500_planning["boundary"] == "top500-sec-source-pack-batch-planning-review-only-v1"
    assert top500_planning["current_manifest_path"] == "data/universes/us_common_stocks_top500.current.json"
    assert top500_planning["support_resolved_from_current_manifest_only"] is True
    assert top500_planning["candidate_or_priority_data_resolves_runtime_support"] is False
    assert top500_planning["live_provider_or_exchange_data_resolves_runtime_support"] is False
    assert top500_planning["candidate_relationship_diagnostics"]["candidate_artifacts_available"] is True
    assert top500_planning["candidate_relationship_diagnostics"]["candidate_data_used_for_runtime_support"] is False
    assert top500_planning["planning_summary"] == {
        "planned_row_count": 10,
        "batch_count": 5,
        "high_demand_pre_cache_count": 1,
        "top500_review_count": 9,
        "source_backed_partial_ready_count": 1,
        "local_lightweight_generated_surface_eligible_count": 10,
        "human_review_required_for_lightweight_count": 0,
        "insufficient_evidence_count": 9,
        "blocked_generated_surface_count": 9,
    }
    assert top500_planning["manifest_rank_ordering"][:3] == [
        {"rank": 1, "ticker": "AAPL"},
        {"rank": 2, "ticker": "MSFT"},
        {"rank": 3, "ticker": "NVDA"},
    ]
    top500_batches = {group["batch_name"]: group for group in top500_planning["batch_groups"]}
    assert top500_batches["high-demand-pre-cache"]["tickers"] == ["AAPL"]
    assert top500_batches["TOP500-50"]["planned_row_count"] == 9
    top500_priorities = {
        group["readiness_priority"]: group["planned_row_count"]
        for group in top500_planning["readiness_priority_groups"]
    }
    assert top500_priorities == {
        "approved_partial_ready_needs_quarterly_or_full_review": 1,
        "missing_required_sec_sources": 9,
    }
    assert top500_planning["source_handoff_readiness"]["approved_component_count"] == 3
    assert top500_planning["parser_readiness"]["parser_status_counts"]["pending_review"] == 37
    assert top500_planning["freshness_as_of_checksum_placeholder_status"]["checksum_present_count"] == 0
    assert "candidate_artifacts_are_diagnostic_only" in top500_planning["stop_conditions"]
    assert "generated_pages" in top500_planning["blocked_generated_surfaces"]
    assert "generated_chat_answers" in stock_sec_details["blocked_generated_surfaces"]
    etf_readiness_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "etf_issuer_source_pack_readiness"
    )
    etf500_planning = etf_readiness_details["etf500_source_pack_batch_planning"]
    assert etf500_planning["schema_version"] == "etf500-issuer-source-pack-batch-plan-v1"
    assert etf500_planning["boundary"] == "etf500-issuer-source-pack-batch-planning-review-only-v1"
    assert etf500_planning["candidate_review_metadata_consumed"] is True
    assert etf500_planning["candidate_artifacts_available"] is False
    assert etf500_planning["fallback_to_current_fixture_review_metadata"] is True
    assert etf500_planning["fallback_not_launch_coverage"] is True
    assert etf500_planning["planning_summary"] == {
        "planned_row_count": 13,
        "batch_count": 4,
        "issuer_count": 5,
        "category_bucket_count": 7,
        "source_pack_ready_count": 0,
        "source_pack_partial_count": 2,
        "source_pack_incomplete_count": 11,
        "local_lightweight_generated_surface_eligible_count": 13,
        "human_review_required_for_lightweight_count": 0,
        "blocked_generated_surface_count": 9,
    }
    assert [group["batch"] for group in etf500_planning["batch_groups"]] == [
        "ETF-50",
        "ETF-150",
        "ETF-300",
        "ETF-500",
    ]
    assert etf500_planning["batch_groups"][0]["planned_row_count"] == 13
    assert etf500_planning["batch_groups"][1]["planned_row_count"] == 0
    planning_priorities = {
        group["source_pack_readiness_priority"]: group["planned_row_count"]
        for group in etf500_planning["source_pack_readiness_priority_groups"]
    }
    assert planning_priorities == {
        "missing_required_issuer_sources": 11,
        "source_backed_partial_review": 2,
    }
    category_groups = {group["bucket_id"]: group for group in etf500_planning["category_bucket_groups"]}
    assert category_groups["broad_core_us_equity_beta"]["planned_row_count"] == 7
    assert category_groups["sector_etfs"]["planned_row_count"] == 4
    assert category_groups["dividend_and_shareholder_yield_index"]["planned_row_count"] == 0
    assert etf500_planning["target_context"]["practical_supported_row_range"] == {"minimum": 475, "maximum": 525}
    assert etf500_planning["target_context"]["current_fixture_not_launch_coverage"] is True
    assert "generated_output_cache_entries" in etf500_planning["blocked_generated_surfaces"]
    planner_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "local_ingestion_priority_planner"
    )
    assert planner_details["schema_version"] == "local-ingestion-priority-plan-v1"
    assert planner_details["boundary"] == "local-ingestion-priority-planner-review-only-v1"
    assert planner_details["summary"] == {
        "planned_asset_count": 23,
        "batch_count": 6,
        "ready_to_inspect_count": 3,
        "blocked_or_not_ready_count": 20,
        "high_demand_pre_cache_count": 3,
        "supported_etf_manifest_count": 11,
        "top500_stock_manifest_count": 9,
        "blocked_diagnostic_count": 4,
    }
    assert planner_details["first_batch_tickers"] == ["AAPL", "VOO", "QQQ"]
    assert planner_details["supported_etf_runtime_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert planner_details["recognition_manifest_used_for_priority_order"] is False
    assert planner_details["recognition_rows_unlock_generated_output"] is False
    assert planner_details["top500_runtime_authority"] == "data/universes/us_common_stocks_top500.current.json"
    assert planner_details["state_diagnostics"]["states"]["pending"] == 18
    assert planner_details["state_diagnostics"]["states"]["running"] == 1
    assert planner_details["state_diagnostics"]["states"]["succeeded"] == 3
    assert planner_details["state_diagnostics"]["states"]["failed"] == 1
    assert planner_details["state_diagnostics"]["states"]["unsupported"] == 1
    assert planner_details["state_diagnostics"]["states"]["out_of_scope"] == 1
    assert planner_details["state_diagnostics"]["states"]["unknown"] == 1
    assert planner_details["state_diagnostics"]["states"]["unavailable"] == 1
    assert planner_details["state_diagnostics"]["states"]["partial"] == 3
    assert planner_details["state_diagnostics"]["states"]["stale"] == 0
    assert planner_details["state_diagnostics"]["states"]["insufficient_evidence"] == 20
    assert "generated_output_cache_entries" in planner_details["blocked_generated_surfaces"]
    stock_vs_etf_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "stock_vs_etf_comparison_readiness"
    )
    assert stock_vs_etf_details["schema_version"] == "stock-vs-etf-comparison-readiness-v1"
    assert stock_vs_etf_details["boundary"] == "review_only_fixture_backed_no_services_no_live_calls_v1"
    assert stock_vs_etf_details["deterministic_pairs"] == {
        "stock_vs_etf": ["AAPL", "VOO"],
        "etf_vs_etf_baseline": ["VOO", "QQQ"],
        "broad_coverage_proven": False,
    }
    assert stock_vs_etf_details["backend_compare"]["state_status"] == "supported"
    assert stock_vs_etf_details["backend_compare"]["comparison_type"] == "stock_vs_etf"
    assert stock_vs_etf_details["backend_compare"]["availability_state"] == "available"
    assert stock_vs_etf_details["backend_compare"]["relationship_schema_version"] == "stock-etf-relationship-v1"
    assert stock_vs_etf_details["backend_compare"]["relationship_state"] == "direct_holding"
    assert stock_vs_etf_details["backend_compare"]["basket_structure"] == "single-company-vs-etf-basket"
    assert stock_vs_etf_details["backend_compare"]["source_reference_assets"] == ["AAPL", "VOO"]
    assert stock_vs_etf_details["backend_compare"]["old_frontend_only_holding_verified_present"] is False
    assert {"relationship_state", "evidence_boundary"} <= set(
        stock_vs_etf_details["backend_compare"]["badge_markers"]
    )
    assert stock_vs_etf_details["comparison_export"]["export_state"] == "available"
    assert stock_vs_etf_details["comparison_export"]["comparison_type"] == "stock_vs_etf"
    assert stock_vs_etf_details["comparison_export"]["binding_scope"] == "same_comparison_pack"
    assert stock_vs_etf_details["comparison_export"]["same_comparison_pack_citation_bindings_only"] is True
    assert stock_vs_etf_details["comparison_export"]["same_comparison_pack_source_bindings_only"] is True
    assert stock_vs_etf_details["comparison_export"]["relationship_context_section_present"] is True
    assert stock_vs_etf_details["comparison_export"]["educational_disclaimer_present"] is True
    assert stock_vs_etf_details["comparison_export"]["forbidden_advice_phrase_hits"] == []
    assert stock_vs_etf_details["chat_compare_redirect"] == {
        "endpoint": "POST /api/assets/VOO/chat",
        "safety_classification": "compare_route_redirect",
        "comparison_availability_state": "available",
        "route": "/compare?left=AAPL&right=VOO",
        "generated_multi_asset_chat_answer": False,
        "factual_citation_count": 0,
        "factual_source_document_count": 0,
    }
    assert stock_vs_etf_details["frontend_api_alignment"] == {
        "blocked": True, "reason_code": "legacy_web_runtime_retired"
    }
    assert {
        (case["left_ticker"], case["right_ticker"], case["availability_state"])
        for case in stock_vs_etf_details["unsupported_blocking_cases"]
    } == {
        ("VOO", "BTC", "unsupported"),
        ("VOO", "GME", "out_of_scope"),
        ("VOO", "SPY", "eligible_not_cached"),
        ("VOO", "ZZZZ", "unknown"),
        ("AAPL", "QQQ", "no_local_pack"),
    }
    assert stock_vs_etf_details["etf_vs_etf_baseline"] == {
        "left_ticker": "VOO",
        "right_ticker": "QQQ",
        "comparison_type": "etf_vs_etf",
        "availability_state": "available",
        "independent_of_stock_vs_etf_markers": True,
    }
    assert {
        "no_local_pack",
        "missing_backend_relationship_schema",
        "frontend_only_fallback",
        "unavailable_export",
        "chat_redirect_mismatch",
        "missing_source_citation_metadata",
        "missing_local_smoke_instructions",
        "unsupported_state_regression",
        "live_call_requirement",
    } == set(stock_vs_etf_details["blocker_reason_code_catalog"])
    assert stock_vs_etf_details["review_only_boundaries"]["services_started"] is False
    assert stock_vs_etf_details["review_only_boundaries"]["live_llm_calls"] is False
    assert stock_vs_etf_details["review_only_boundaries"]["comparison_coverage_broadened"] is False
    parity_details = next(
        check["details"]
        for check in result["checks"]
        if check["check_id"] == "local_fresh_data_mvp_slice_comparison_export_parity"
    )
    assert parity_details["schema_version"] == "local-fresh-data-mvp-slice-comparison-export-parity-v1"
    assert parity_details["boundary"] == "deterministic_fixture_backed_no_services_no_live_calls_v1"
    assert [asset["ticker"] for asset in parity_details["representative_assets"]] == [
        "AAPL",
        "MSFT",
        "VOO",
        "QQQ",
        "SPY",
        "TQQQ",
        "ARKK",
        "BND",
        "GLD",
    ]
    pair_by_key = {tuple(pair["pair"]): pair for pair in parity_details["representative_comparison_pairs"]}
    assert set(pair_by_key) == {("VOO", "QQQ"), ("AAPL", "VOO"), ("AAPL", "MSFT")}
    assert pair_by_key[("VOO", "QQQ")]["comparison_type"] == "etf_vs_etf"
    assert pair_by_key[("VOO", "QQQ")]["availability_state"] == "available"
    assert pair_by_key[("VOO", "QQQ")]["source_backed"] is True
    assert pair_by_key[("VOO", "QQQ")]["same_comparison_pack_sources_only"] is True
    assert pair_by_key[("AAPL", "VOO")]["comparison_type"] == "stock_vs_etf"
    assert pair_by_key[("AAPL", "VOO")]["stock_etf_relationship_schema"] == "stock-etf-relationship-v1"
    assert pair_by_key[("AAPL", "VOO")]["relationship_state"] == "direct_holding"
    assert pair_by_key[("AAPL", "VOO")]["basket_structure"] == "single-company-vs-etf-basket"
    assert pair_by_key[("AAPL", "MSFT")]["comparison_type"] == "stock_vs_stock"
    assert pair_by_key[("AAPL", "MSFT")]["availability_state"] == "available"
    assert pair_by_key[("AAPL", "MSFT")]["source_backed"] is True
    assert pair_by_key[("AAPL", "MSFT")]["source_reference_assets"] == ["AAPL", "MSFT"]
    assert pair_by_key[("AAPL", "MSFT")]["stock_vs_stock_copy_avoids_etf_only_markers"] is True
    assert all(pair["educational_disclaimer_present_in_exports"] is True for pair in pair_by_key.values())
    assert all(pair["old_frontend_only_holding_verified_present"] is False for pair in pair_by_key.values())
    for pair in pair_by_key.values():
        assert {export["export_format"] for export in pair["exports"]} == {"json", "markdown"}
        assert all(export["export_state"] == "available" for export in pair["exports"])
        assert all(export["binding_scope"] == "same_comparison_pack" for export in pair["exports"])
        assert all(export["source_use_policy_present"] is True for export in pair["exports"])
        assert all(export["source_freshness_metadata_present"] is True for export in pair["exports"])
    assert {
        tuple(case["pair"]): case["availability_state"]
        for case in parity_details["unavailable_or_blocked_comparison_cases"]
    } == {
        ("VOO", "SPY"): "eligible_not_cached",
        ("SPY", "VTI"): "eligible_not_cached",
        ("VOO", "TQQQ"): "unsupported",
        ("AAPL", "TQQQ"): "unsupported",
    }
    assert all(case["generated_output_blocked"] is True for case in parity_details["unavailable_or_blocked_comparison_cases"])
    asset_export_by_ticker = {case["ticker"]: case for case in parity_details["asset_export_cases"]}
    assert asset_export_by_ticker["AAPL"]["slice_status"] == "pass"
    assert asset_export_by_ticker["VOO"]["issuer_evidence_state"] == "supported"
    assert asset_export_by_ticker["QQQ"]["issuer_evidence_state"] == "supported"
    assert asset_export_by_ticker["SPY"]["slice_status"] == "pass"
    assert asset_export_by_ticker["SPY"]["issuer_evidence_state"] == "supported"
    assert asset_export_by_ticker["SPY"]["provider_fallback_not_audit_quality_approval"] is True
    for ticker in ["TQQQ", "ARKK", "BND", "GLD"]:
        assert asset_export_by_ticker[ticker]["slice_status"] == "blocked"
        assert all(export["export_state"] == "unsupported" for export in asset_export_by_ticker[ticker]["exports"])
        assert all(export["empty_factual_evidence_export"] is True for export in asset_export_by_ticker[ticker]["exports"])
    assert parity_details["chat_compare_redirect"]["route"] == "/compare?left=AAPL&right=VOO"
    assert parity_details["chat_compare_redirect"]["generated_multi_asset_chat_answer"] is False
    assert parity_details["blocker_reason_codes"] == []
    assert parity_details["sanitized_diagnostics"]["forbidden_marker_hits"] == []
    assert parity_details["review_only_boundaries"]["comparison_coverage_broadened"] is False
    deployment_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "local_deployment_env_smoke"
    )
    assert deployment_details["schema_version"] == "local-deployment-env-smoke-v1"
    assert deployment_details["normal_ci_requires_live_calls"] is False
    assert deployment_details["production_services_started"] is False
    assert deployment_details["deployments_created"] is False
    assert deployment_details["live_provider_calls_attempted"] is False
    assert deployment_details["database_connections_opened"] is False
    assert deployment_details["secret_values_reported"] is False
    assert deployment_details["launch_or_public_deployment_approved"] is False
    assert deployment_details["production_ready"] is False
    deployment_checks = {check["check_id"]: check for check in deployment_details["checks"]}
    assert deployment_checks["browser_env_secret_separation"]["status"] == "blocked"
    assert all(not item["unsafe_env_names"] and item["missing_safe_env_names"] for item in deployment_checks["browser_env_secret_separation"]["blockers"])
    assert deployment_checks["repo_local_deployment_scaffolding"]["apps_web_is_vercel_project_root"] is False
    assert deployment_checks["repo_local_deployment_scaffolding"]["reason_code"] == "legacy_web_runtime_retired"
    asset_summary = threshold["asset_state_summary"]
    assert asset_summary["failed_asset_count"] == 1
    assert asset_summary["unavailable_asset_count"] == 1
    assert asset_summary["partial_count"] == 4
    assert asset_summary["stale_count"] == 0
    assert asset_summary["unknown_count"] == 1
    assert asset_summary["insufficient_evidence_count"] == 29
    assert asset_summary["source_backed_partial_ready_count"] == 4
    assert asset_summary["generated_surface_violation_count"] == 0
    assert asset_summary["reason_codes_by_state"]["failed"] == ["fixture_pre_cache_failed"]
    assert asset_summary["reason_codes_by_state"]["unavailable"] == ["unavailable"]
    assert all(not row["generated_surface_exposed"] for row in asset_summary["non_generated_assets"])
    assert all(row["citation_count"] == 0 and row["source_document_count"] == 0 for row in asset_summary["non_generated_assets"])
    for surface in [
        "generated_claims",
        "generated_chat_answers",
        "generated_comparisons",
        "weekly_news_focus",
        "ai_comprehensive_analysis",
        "exports",
        "generated_risk_summaries",
        "generated_output_cache_entries",
    ]:
        assert surface in asset_summary["blocked_generated_surfaces"]
    fallback = threshold["live_generation_validation_failure_fallback"]
    assert fallback["generated_claims_allowed_after_failed_validation"] is False
    assert fallback["generated_chat_answers_allowed_after_failed_validation"] is False
    assert fallback["generated_comparisons_allowed_after_failed_validation"] is False
    assert fallback["weekly_news_focus_allowed_after_failed_validation"] is False
    assert fallback["ai_comprehensive_analysis_allowed_after_failed_validation"] is False
    assert fallback["exports_allowed_after_failed_validation"] is False
    assert fallback["generated_output_cache_entries_allowed_after_failed_validation"] is False
    assert fallback["fallback_section_states"] == [
        "partial",
        "stale",
        "unknown",
        "unavailable",
        "insufficient_evidence",
    ]
    gate = result["manual_fresh_data_readiness_gate"]
    assert gate["schema_version"] == "local-manual-fresh-data-readiness-gate-v1"
    assert gate["decision"] == "agent_work_remaining"
    assert gate["task_ready_vs_manual_test_ready_decision"] == "agent_work_remaining"
    assert gate["task_ready_for_manual_testing"] is False
    assert gate["manual_test_ready"] is False
    assert gate["agent_work_remaining"] is True
    assert gate["next_operator_action"] == "finish_deterministic_agent_work_before_manual_fresh_data_testing"
    assert gate["sanitized_operator_report"] is True
    assert gate["review_only"] is True
    assert gate["production_services_started"] is False
    assert gate["live_sources_fetched"] is False
    assert gate["live_llms_called"] is False
    assert gate["sources_approved"] is False
    assert gate["manifests_promoted"] is False
    assert gate["ingestion_started"] is False
    assert gate["generated_output_cache_entries_written"] is False
    assert gate["generated_output_unlocked_for_unsupported_or_incomplete_assets"] is False
    assert gate["human_review_required_for_lightweight"] is False
    assert gate["strict_audit_review_required"] is True
    assert gate["strict_audit_stop_conditions_block_local_lightweight"] is False
    assert {item["check_id"] for item in gate["stop_conditions"] if "check_id" in item} == {
        "local_deployment_env_smoke", "stock_vs_etf_comparison_readiness", "frontend_v04_smoke_markers"
    }
    assert {item["reason_code"] for item in gate["stop_conditions"]} == {
        "required_deterministic_check_not_passed", "required_check_blocked"
    }
    stop_reasons = {condition["reason_code"] for condition in gate["strict_audit_stop_conditions"]}
    assert {
        "etf500_review_fixture_only_not_launch_coverage",
        "etf500_source_pack_incomplete",
        "etf500_handoff_not_ready_or_unclear_rights",
        "etf500_source_pack_batch_uses_fixture_fallback",
        "etf500_issuer_source_pack_batch_incomplete",
        "top500_sec_source_pack_insufficient_evidence",
        "top500_sec_source_handoff_not_ready",
        "top500_sec_parser_not_ready",
        "top500_sec_freshness_or_checksum_not_ready",
        "local_ingestion_priority_plan_has_blocked_or_not_ready_assets",
    } <= stop_reasons
    prerequisite_ids = {item["prerequisite_id"] for item in gate["prerequisite_summaries"]}
    assert {
        "t136_etf500_candidate_review",
        "t137_etf_source_pack_batch_planning",
        "t138_top500_sec_source_pack_batch_planning",
        "local_mvp_thresholds",
        "local_ingestion_priority_planning",
        "governed_golden_rendering",
        "t144_local_fresh_data_mvp_slice_smoke",
        "t149_local_fresh_data_mvp_slice_comparison_export_parity",
        "t157_local_deployment_env_smoke",
        "stock_vs_etf_comparison_readiness",
        "frontend_workflow_smoke_markers",
    } == prerequisite_ids
    assert [mode["status"] for mode in gate["optional_mode_statuses"]] == ["skipped"] * 5
    assert gate["no_secret_diagnostics"] == {
        "secret_values_reported": False,
        "secret_values_requested": False,
        "safe_diagnostics_only": True,
        "opt_in_env_names_reported_without_values": [
            "LTT_REHEARSAL_BROWSER_SERVICES_ENABLED",
            "LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED",
            "LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED",
            "LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED",
            "LTT_WEEKLY_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED",
            "LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED",
            "LEARN_TICKER_LOCAL_WEB_BASE",
            "LEARN_TICKER_LOCAL_API_BASE",
        ],
    }
    assert "generated_output_cache_entries" in gate["blocked_generated_surfaces"]
    checklist_ids = {item["check_id"] for item in gate["manual_test_checklist"]}
    assert {
        "local_web_api_startup",
        "api_base_proxy_cors",
        "local_deployment_env_smoke",
        "home_single_asset_search",
        "a_vs_b_compare_redirect",
        "source_drawer",
        "citation_chips",
        "freshness_labels",
        "exports",
        "comparison",
        "stock_etf_relationship_badges",
        "contextual_glossary",
        "asset_chat_mobile_behavior",
        "weekly_news_focus_limited_empty_states",
        "ai_comprehensive_analysis_threshold",
        "unsupported_recognition_only_blocking",
        "optional_durable_repositories",
        "optional_official_source_retrieval",
        "optional_weekly_news_live_source_smoke",
        "optional_live_ai_validation",
    } == checklist_ids
