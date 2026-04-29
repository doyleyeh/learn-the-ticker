import json
from dataclasses import replace
from pathlib import Path

import pytest

from backend.data import (
    ELIGIBLE_NOT_CACHED_ASSETS,
    OUT_OF_SCOPE_COMMON_STOCKS,
    UNSUPPORTED_ASSETS,
    load_top500_stock_universe_manifest,
    top500_stock_universe_entry,
)
from backend.etf_universe import (
    ETFUniverseContractError,
    blocked_etf_entries,
    build_etf500_issuer_source_pack_batch_plan,
    build_etf_issuer_source_pack_readiness_packet,
    build_etf_launch_review_packet,
    cached_supported_etf_entries,
    can_generate_output_for_etf_entry,
    eligible_not_cached_etf_entries,
    etf_universe_entry,
    load_recognition_etf_universe_manifest,
    load_etf_universe_manifest,
    load_supported_etf_universe_manifest,
    validate_etf_universe_manifest,
)
from backend.models import ETFUniverseSupportState
from backend.models import FreshnessState, SourceParserStatus
from backend.models import SearchResponse
from backend.models import Top500CandidateManifest
from backend.provider_adapters.etf_issuer import ETF_ISSUER_FIXTURES
from backend.search import search_assets


def test_cached_supported_assets_resolve_by_ticker_and_name():
    ticker = search_assets("VOO")
    name = search_assets("Apple")

    for response, expected_ticker in [(ticker, "VOO"), (name, "AAPL")]:
        validated = SearchResponse.model_validate(response.model_dump(mode="json"))
        result = validated.results[0]
        assert validated.state.status.value == "supported"
        assert validated.state.support_classification.value == "cached_supported"
        assert validated.state.can_open_generated_page is True
        assert validated.state.generated_route == f"/assets/{expected_ticker}"
        assert validated.state.can_request_ingestion is False
        assert validated.state.ingestion_request_route is None
        assert result.ticker == expected_ticker
        assert result.supported is True
        assert result.support_classification.value == "cached_supported"
        assert result.can_open_generated_page is True
        assert result.can_answer_chat is True
        assert result.can_compare is True
        assert result.generated_route == f"/assets/{expected_ticker}"
        assert result.can_request_ingestion is False
        assert result.ingestion_request_route is None


def test_ambiguous_search_requires_disambiguation_without_selecting_one_result():
    response = search_assets("S&P 500 ETF")

    assert response.state.status.value == "ambiguous"
    assert response.state.requires_disambiguation is True
    assert response.state.can_open_generated_page is False
    assert response.state.generated_route is None
    assert response.state.can_request_ingestion is False
    assert response.state.ingestion_request_route is None
    assert {result.ticker for result in response.results} >= {"VOO", "SPY"}
    assert any(result.support_classification.value == "cached_supported" for result in response.results)
    assert any(result.support_classification.value == "eligible_not_cached" for result in response.results)
    spy_result = next(result for result in response.results if result.ticker == "SPY")
    assert spy_result.can_request_ingestion is True
    assert spy_result.ingestion_request_route == "/api/admin/ingest/SPY"


def test_recognized_unsupported_assets_are_blocked_from_generated_outputs():
    cases = [
        ("BTC", "Crypto assets", "crypto_assets"),
        ("TQQQ", "Leveraged ETFs", "leveraged_etf"),
        ("SQQQ", "Inverse ETFs", "inverse_etf"),
        ("ARKK", "Active ETFs", "active_etf"),
        ("BND", "Fixed-income ETFs", "fixed_income_etf"),
        ("GLD", "Commodity ETFs", "commodity_etf"),
        ("AOR", "Multi-asset ETFs", "multi_asset_etf"),
    ]

    for query, expected_reason, expected_category in cases:
        response = search_assets(query)
        result = response.results[0]
        assert response.state.status.value == "unsupported"
        assert response.state.support_classification.value == "recognized_unsupported"
        assert result.status.value == "unsupported"
        assert result.supported is False
        assert result.support_classification.value == "recognized_unsupported"
        assert result.can_open_generated_page is False
        assert result.can_answer_chat is False
        assert result.can_compare is False
        assert result.generated_route is None
        assert result.can_request_ingestion is False
        assert result.ingestion_request_route is None
        assert expected_reason in (result.message or "")
        assert response.state.blocked_explanation is not None
        assert result.blocked_explanation is not None
        assert response.state.blocked_explanation.model_dump(mode="json") == result.blocked_explanation.model_dump(
            mode="json"
        )
        assert result.blocked_explanation.schema_version == "search-blocked-explanation-v1"
        assert result.blocked_explanation.status.value == "unsupported"
        assert result.blocked_explanation.support_classification.value == "recognized_unsupported"
        assert result.blocked_explanation.explanation_kind == "scope_blocked_search_result"
        assert result.blocked_explanation.explanation_category == expected_category
        assert "supported MVP coverage" in result.blocked_explanation.summary
        assert result.blocked_explanation.scope_rationale == result.message
        assert "U.S.-listed common stocks" in result.blocked_explanation.supported_v1_scope
        assert result.blocked_explanation.blocked_capabilities.can_open_generated_page is False
        assert result.blocked_explanation.blocked_capabilities.can_answer_chat is False
        assert result.blocked_explanation.blocked_capabilities.can_compare is False
        assert result.blocked_explanation.blocked_capabilities.can_request_ingestion is False
        assert result.blocked_explanation.ingestion_eligible is False
        assert result.blocked_explanation.ingestion_request_route is None
        assert result.blocked_explanation.diagnostics.deterministic_contract is True
        assert result.blocked_explanation.diagnostics.generated_asset_analysis is False
        assert result.blocked_explanation.diagnostics.includes_citations is False
        assert result.blocked_explanation.diagnostics.includes_source_documents is False
        assert result.blocked_explanation.diagnostics.includes_freshness is False
        assert result.blocked_explanation.diagnostics.uses_live_calls is False


def test_etf_launch_review_packet_preserves_supported_and_recognition_split():
    packet = build_etf_launch_review_packet()

    assert packet["schema_version"] == "etf-launch-review-packet-v1"
    assert packet["boundary"] == "etf-launch-manifest-review-only-v1"
    assert packet["review_only"] is True
    assert packet["no_live_external_calls"] is True
    assert packet["launch_approved"] is False
    assert packet["manual_promotion_required"] is True
    assert packet["review_status"] == "review_needed"
    assert packet["supported_runtime_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert packet["recognition_runtime_authority"] == "data/universes/us_etp_recognition.current.json"
    assert packet["recognition_rows_unlock_generated_output"] is False
    assert packet["golden_set_is_coverage_limit"] is False
    assert packet["current_fixture_not_launch_coverage"] is True
    assert packet["golden_precache_tickers"] == ["QQQ", "VOO"]
    assert "XLE" in packet["regression_reference_tickers"]
    assert packet["eligible_universe_policy"]["coverage_limit"] == "manifest_defined_reviewed_eligible_universe"
    assert "factor_style" in packet["eligible_universe_policy"]["included_categories"]
    assert "low_volatility" in packet["eligible_universe_policy"]["included_factor_styles"]
    assert "international_or_global_primary_exposure" in packet["eligible_universe_policy"]["excluded_products"]
    assert "issuer_page" in packet["required_issuer_source_pack"]
    assert packet["fixture_or_local_only_contract"] is True
    assert packet["eligible_supported_entry_count"] == 13
    assert packet["generated_output_eligible_count"] == 2
    assert packet["pending_ingestion_count"] == 11
    assert packet["excluded_product_count"] >= 1
    assert packet["readiness_counts"] == {
        "supported": 13,
        "recognition_only": 9,
        "excluded": 7,
        "pending_review": 22,
        "unavailable": 1,
        "pending_ingestion": 11,
        "source_pack_ready": 0,
        "generated_output_eligible": 2,
        "golden_precache_regression": 2,
        "full_eligible_universe": 13,
    }
    golden_regression = packet["golden_precache_regression"]
    assert golden_regression["golden_precache_tickers"] == ["QQQ", "VOO"]
    assert golden_regression["full_eligible_universe_count"] == 13
    assert golden_regression["non_golden_eligible_supported_count"] == 11
    assert golden_regression["eligible_supported_count_exceeds_golden_precache_count"] is True
    assert golden_regression["golden_set_is_coverage_limit"] is False
    assert "sector" in golden_regression["represented_categories_beyond_golden"]
    assert "industry_or_theme" in golden_regression["represented_categories_beyond_golden"]
    assert "fixture_or_local_only_provenance_not_launch_approved" in packet["stop_conditions"]
    assert "fixture_source_quality_not_launch_approved" in packet["stop_conditions"]
    assert "issuer_source_pack_review_not_complete" in packet["stop_conditions"]
    assert "missing_golden_ticker" not in packet["stop_conditions"]
    assert "fixture_sized_supported_manifest_not_launch_approved" not in packet["stop_conditions"]

    target = packet["etf500_target_metadata"]
    assert target["contract_version"] == "etf500-candidate-manifest-review-contract-v1"
    assert target["practical_supported_row_range"] == {"minimum": 475, "maximum": 525}
    assert [milestone["batch"] for milestone in target["batch_milestones"]] == [
        "ETF-50",
        "ETF-150",
        "ETF-300",
        "ETF-500",
    ]
    assert target["candidate_artifact_path_conventions"] == [
        "data/universes/us_equity_etfs_supported.candidate.YYYY-MM.etf500.json",
        "data/universes/us_etp_recognition.candidate.YYYY-MM.json",
        "data/universes/us_equity_etfs.candidate.YYYY-MM.etf500.promotion-packet.json",
    ]
    buckets = {bucket["bucket_id"]: bucket for bucket in target["category_target_buckets"]}
    assert buckets["broad_core_us_equity_beta"]["target_count"] == 45
    assert buckets["market_cap_and_size_style"]["target_count"] == 95
    assert buckets["sector_etfs"]["target_count"] == 120
    assert buckets["industry_theme_passive_us_equity"]["target_count"] == 105
    assert buckets["dividend_and_shareholder_yield_index"]["target_count"] == 55
    assert buckets["factor_smart_beta_and_equal_weight"]["target_count"] == 60
    assert buckets["esg_values_screened_us_equity_index"]["target_count"] == 20

    etf500 = packet["etf500_review_contract"]
    assert etf500["review_only"] is True
    assert etf500["current_manifest_status"]["supported_row_count"] == 13
    assert etf500["current_manifest_status"]["within_etf500_practical_range"] is False
    assert etf500["current_manifest_status"]["current_fixture_not_launch_coverage"] is True
    assert etf500["current_manifest_status"]["runtime_supported_authority_preserved"] is True
    assert etf500["current_manifest_status"]["runtime_recognition_authority_preserved"] is True
    diagnostics = etf500["diagnostics"]
    assert diagnostics["supported_row_count"] == 13
    assert diagnostics["recognition_row_count"] == 9
    assert diagnostics["pending_review_row_count"] >= 13
    assert diagnostics["source_pack_readiness"]["ready_count"] == 0
    assert diagnostics["source_pack_readiness"]["incomplete_count"] == 13
    assert diagnostics["parser_handoff_readiness"]["handoff_not_ready_count"] >= 13
    assert diagnostics["checksum_status"] == {
        "supported_checksum_matches": True,
        "recognition_checksum_matches": True,
    }
    assert diagnostics["disqualifier_counts"]["leveraged_etf"] >= 1
    assert diagnostics["disqualifier_counts"]["inverse_etf"] >= 1
    assert diagnostics["disqualifier_counts"]["active_etf"] >= 1
    assert diagnostics["disqualifier_counts"]["fixed_income_etf"] >= 1
    assert diagnostics["disqualifier_counts"]["commodity_etf"] >= 1
    assert diagnostics["disqualifier_counts"]["crypto_product"] == 0
    assert diagnostics["disqualifier_counts"]["single_stock_etf"] == 0
    assert diagnostics["disqualifier_counts"]["option_income_or_buffer_etf"] == 0
    assert diagnostics["disqualifier_counts"]["etn"] >= 1
    assert diagnostics["disqualifier_counts"]["etv"] == 0
    assert diagnostics["disqualifier_counts"]["cef"] == 0
    assert diagnostics["disqualifier_counts"]["international_equity"] == 0
    assert diagnostics["category_coverage_gaps"]
    bucket_diagnostics = {row["bucket_id"]: row for row in diagnostics["category_bucket_diagnostics"]}
    assert bucket_diagnostics["broad_core_us_equity_beta"]["current_supported_count"] == 7
    assert bucket_diagnostics["market_cap_and_size_style"]["current_supported_count"] == 7
    assert bucket_diagnostics["sector_etfs"]["current_supported_count"] == 4
    assert bucket_diagnostics["industry_theme_passive_us_equity"]["current_supported_count"] == 2
    assert bucket_diagnostics["dividend_and_shareholder_yield_index"]["current_supported_count"] == 0
    blocking = etf500["generated_output_blocking_rules"]
    assert blocking["recognition_only_rows_unlock_generated_output"] is False
    assert blocking["candidate_rows_that_fail_scope_gates_unlock_generated_output"] is False
    assert blocking["pending_review_rows_unlock_generated_output"] is False
    assert blocking["unavailable_rows_unlock_generated_output"] is False
    assert blocking["parser_invalid_rows_unlock_generated_output"] is False
    assert blocking["unclear_rights_rows_unlock_generated_output"] is False
    assert blocking["source_pack_incomplete_rows_unlock_generated_output"] is False
    assert "generated_output_cache_entries" in blocking["blocked_generated_surfaces"]
    assert "do_not_pad_with_leveraged_etf" in etf500["no_padding_stop_conditions"]
    assert "do_not_pad_with_option_income_or_buffer_etf" in etf500["no_padding_stop_conditions"]
    assert "do_not_pad_with_cef" in etf500["no_padding_stop_conditions"]

    eligible_scope = packet["eligible_universe_scope"]
    assert eligible_scope["scope_version"] == "etf-eligible-universe-review-scope-v1"
    assert eligible_scope["review_contract"] == "manifest_defined_eligible_universe_not_golden_ceiling"
    assert eligible_scope["represented_category_count"] == 5
    assert set(eligible_scope["required_category_names"]) == {
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
    scope_rows = {row["category"]: row for row in eligible_scope["required_categories"]}
    assert scope_rows["broad_us_index"]["supported_ticker_count"] == 7
    assert scope_rows["total_market_or_large_cap"]["supported_ticker_count"] == 6
    assert scope_rows["size_style"]["tickers"] == ["IWM"]
    assert scope_rows["sector"]["supported_ticker_count"] == 4
    assert scope_rows["industry_or_theme"]["tickers"] == ["SOXX", "SMH"]
    assert scope_rows["dividend"]["coverage_status"] == "scope_defined_no_current_manifest_rows"

    supported = packet["supported_manifest"]
    recognition = packet["recognition_manifest"]
    assert supported["local_path"] == "data/universes/us_equity_etfs_supported.current.json"
    assert recognition["local_path"] == "data/universes/us_etp_recognition.current.json"
    assert supported["checksum_matches"] is True
    assert recognition["checksum_matches"] is True
    assert supported["support_state_counts"]["cached_supported"] == 2
    assert supported["support_state_counts"]["eligible_not_cached"] == 11
    assert supported["generated_output_eligible_count"] == 2
    assert supported["source_pack_ready_count"] == 0
    assert supported["pending_ingestion_count"] == 11
    assert supported["pending_review_count"] == 13
    assert recognition["support_state_counts"]["recognized_unsupported"] >= 1
    assert recognition["source_pack_ready_count"] == 0

    supported_rows = {entry["ticker"]: entry for entry in packet["supported_entries"]}
    recognition_rows = {entry["ticker"]: entry for entry in packet["recognition_entries"]}
    assert supported_rows["VOO"]["generated_output_eligible"] is True
    assert supported_rows["VOO"]["source_pack_ready"] is False
    assert supported_rows["VOO"]["eligible_universe_categories"] == ["broad_us_index", "total_market_or_large_cap"]
    assert supported_rows["SPY"]["blocked_state_reason"] == "supported_but_not_cached_pending_ingestion"
    assert supported_rows["SPY"]["source_pack_ready"] is False
    assert recognition_rows["TQQQ"]["generated_output_eligible"] is False
    assert recognition_rows["TQQQ"]["source_pack_ready"] is False
    assert recognition_rows["TQQQ"]["eligible_universe_categories"] == []
    assert recognition_rows["TQQQ"]["blocked_state_reason"] == "blocked_by_exclusion_flags:leveraged"
    assert recognition_rows["TQQQ"]["handoff_status"] == "fixture_metadata_only_review_needed"


def test_etf_issuer_source_pack_readiness_packet_is_supported_manifest_keyed_and_review_only():
    packet = build_etf_issuer_source_pack_readiness_packet()

    assert packet["schema_version"] == "etf-issuer-source-pack-readiness-v1"
    assert packet["boundary"] == "etf-issuer-source-pack-readiness-review-only-v1"
    assert packet["review_only"] is True
    assert packet["no_live_external_calls"] is True
    assert packet["supported_runtime_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert packet["recognition_runtime_authority"] == "data/universes/us_etp_recognition.current.json"
    assert packet["readiness_keyed_from_supported_manifest_only"] is True
    assert packet["recognition_rows_unlock_generated_output"] is False
    assert packet["retrieval_alone_approves_evidence"] is False
    assert packet["sources_approved_by_packet"] is False
    assert packet["launch_approved"] is False
    assert packet["manifests_promoted"] is False
    assert packet["review_status"] == "review_needed"
    assert "etf_issuer_source_pack_review_not_complete" in packet["stop_conditions"]
    assert "partial_issuer_source_pack" in packet["stop_conditions"]
    assert "insufficient_issuer_evidence" in packet["stop_conditions"]

    component_ids = [component["component_id"] for component in packet["required_issuer_source_components"]]
    assert component_ids == [
        "issuer_page",
        "fact_sheet",
        "prospectus_or_summary_prospectus",
        "holdings",
        "exposures",
        "methodology_shareholder_or_risk_source",
        "sponsor_announcements_when_relevant",
    ]

    counts = packet["readiness_counts"]
    assert counts == {
        "supported_manifest_rows": 13,
        "recognition_only_rows": 9,
        "cached_golden_supported": 2,
        "eligible_not_cached_supported": 11,
        "pass": 0,
        "partial": 2,
        "stale": 0,
        "unknown": 0,
        "unavailable": 0,
        "insufficient_evidence": 11,
        "blocked": 0,
        "source_backed_partial_rendering_ready": 2,
        "blocked_recognition_only": 9,
        "readiness_packet_unlocks_generated_output": 0,
    }

    supported_rows = {row["ticker"]: row for row in packet["supported_rows"]}
    recognition_rows = {row["ticker"]: row for row in packet["recognition_only_rows"]}

    voo = supported_rows["VOO"]
    assert voo["source_pack_status"] == "partial"
    assert voo["source_backed_partial_rendering_ready"] is True
    assert voo["readiness_packet_unlocks_generated_output"] is False
    components = {component["component_id"]: component for component in voo["components"]}
    for component_id in [
        "issuer_page",
        "fact_sheet",
        "prospectus_or_summary_prospectus",
        "holdings",
        "exposures",
    ]:
        component = components[component_id]
        assert component["status"] == "pass"
        assert component["same_asset_or_same_fund_validation"] is True
        assert component["official_source_status"] is True
        assert component["source_quality"] == "issuer"
        assert component["source_use_policy"] == "full_text_allowed"
        assert component["storage_rights"] == "raw_snapshot_allowed"
        assert component["export_rights"] == "excerpts_allowed"
        assert component["parser_status"] == "parsed"
        assert component["freshness_state"] == "fresh"
        assert component["citation_ready"] is True
        assert component["golden_asset_source_handoff_status"] == "approved"
        assert component["action_readiness"]["generated_claim_support"]["allowed"] is True
        assert component["action_readiness"]["cacheable_generated_output"]["allowed"] is True
        assert component["action_readiness"]["markdown_json_section_export"]["allowed"] is True
    assert components["methodology_shareholder_or_risk_source"]["status"] == "partial"
    assert components["sponsor_announcements_when_relevant"]["status"] == "partial"

    spy = supported_rows["SPY"]
    assert spy["support_state"] == "eligible_not_cached"
    assert spy["source_pack_status"] == "insufficient_evidence"
    assert spy["source_backed_partial_rendering_ready"] is False
    assert all(component["citation_ready"] is False for component in spy["components"])
    assert all(component["golden_asset_source_handoff_status"] != "approved" for component in spy["components"])

    tqqq = recognition_rows["TQQQ"]
    assert tqqq["manifest_kind"] == "recognition_only"
    assert tqqq["source_pack_status"] == "blocked"
    assert tqqq["authoritative_for_generated_output"] is False
    assert tqqq["generated_output_eligible"] is False
    assert tqqq["readiness_keyed_from_supported_manifest"] is False
    assert tqqq["recognition_only_non_authoritative"] is True
    assert tqqq["blocked_state_reason"] == "blocked_by_exclusion_flags:leveraged"


def test_etf_issuer_source_pack_readiness_reports_stale_parser_failed_and_wrong_fund_states():
    fixture = ETF_ISSUER_FIXTURES["VOO"]
    stale_sources = tuple(
        replace(source, freshness_state=FreshnessState.stale)
        if source.source_document_id == "provider_issuer_voo_holdings_2026"
        else source
        for source in fixture.sources
    )
    stale_packet = build_etf_issuer_source_pack_readiness_packet(
        issuer_fixture_by_ticker={"VOO": replace(fixture, sources=stale_sources)}
    )
    stale_voo = next(row for row in stale_packet["supported_rows"] if row["ticker"] == "VOO")
    stale_components = {component["component_id"]: component for component in stale_voo["components"]}
    assert stale_voo["source_pack_status"] == "stale"
    assert stale_components["holdings"]["status"] == "stale"
    assert stale_components["holdings"]["evidence_state"] == "stale"

    parser_failed_packet = build_etf_issuer_source_pack_readiness_packet(
        parser_status_by_source_document_id={"provider_issuer_voo_exposure_2026": SourceParserStatus.failed}
    )
    parser_failed_voo = next(row for row in parser_failed_packet["supported_rows"] if row["ticker"] == "VOO")
    parser_failed_exposures = next(
        component for component in parser_failed_voo["components"] if component["component_id"] == "exposures"
    )
    assert parser_failed_voo["source_pack_status"] == "blocked"
    assert parser_failed_exposures["status"] == "blocked"
    assert "parser_failed" in parser_failed_exposures["reason_codes"]
    assert parser_failed_exposures["golden_asset_source_handoff_status"] == "blocked"

    wrong_identity = replace(fixture.identity, ticker="QQQ", fund_name="Invesco QQQ Trust", issuer="Invesco")
    wrong_fund_packet = build_etf_issuer_source_pack_readiness_packet(
        issuer_fixture_by_ticker={"VOO": replace(fixture, identity=wrong_identity)}
    )
    wrong_fund_voo = next(row for row in wrong_fund_packet["supported_rows"] if row["ticker"] == "VOO")
    assert wrong_fund_voo["source_pack_status"] == "blocked"
    assert all(
        component["same_asset_or_same_fund_validation"] is False
        for component in wrong_fund_voo["components"]
        if component["source_document_id"]
    )
    assert all(
        "wrong_fund_issuer_source" in component["reason_codes"]
        for component in wrong_fund_voo["components"]
        if component["source_document_id"]
    )


def test_etf500_issuer_source_pack_batch_plan_groups_fixture_rows_without_unlocking_output():
    plan = build_etf500_issuer_source_pack_batch_plan()

    assert plan["schema_version"] == "etf500-issuer-source-pack-batch-plan-v1"
    assert plan["boundary"] == "etf500-issuer-source-pack-batch-planning-review-only-v1"
    assert plan["review_only"] is True
    assert plan["deterministic"] is True
    assert plan["no_live_external_calls"] is True
    assert plan["candidate_review_metadata_consumed"] is True
    assert plan["candidate_artifacts_available"] is False
    assert plan["fallback_to_current_fixture_review_metadata"] is True
    assert plan["fallback_not_launch_coverage"] is True
    assert plan["sources_approved_by_plan"] is False
    assert plan["manifests_promoted"] is False
    assert plan["planner_started_ingestion"] is False
    assert plan["generated_output_unlocked_by_plan"] is False
    assert plan["generated_output_cache_entries_written"] is False
    assert plan["supported_runtime_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert plan["recognition_runtime_authority"] == "data/universes/us_etp_recognition.current.json"
    assert plan["recognition_rows_unlock_generated_output"] is False

    target = plan["target_context"]
    assert target["target_name"] == "ETF-500"
    assert target["practical_supported_row_range"] == {"minimum": 475, "maximum": 525}
    assert [milestone["batch"] for milestone in target["batch_milestones"]] == [
        "ETF-50",
        "ETF-150",
        "ETF-300",
        "ETF-500",
    ]
    assert len(target["category_target_buckets"]) == 7
    assert len(target["category_gaps"]) == 7
    assert target["current_fixture_not_launch_coverage"] is True
    assert target["source_pack_readiness"]["incomplete_count"] == 13
    assert target["parser_handoff_readiness"]["handoff_not_ready_count"] >= 13
    assert target["checksum_status"] == {
        "supported_checksum_matches": True,
        "recognition_checksum_matches": True,
    }
    assert "do_not_pad_with_leveraged_etf" in target["no_padding_stop_conditions"]

    assert plan["planning_summary"] == {
        "planned_row_count": 13,
        "batch_count": 4,
        "issuer_count": 5,
        "category_bucket_count": 7,
        "source_pack_ready_count": 0,
        "source_pack_partial_count": 2,
        "source_pack_incomplete_count": 11,
        "blocked_generated_surface_count": 9,
    }
    batch_groups = {group["batch"]: group for group in plan["batch_groups"]}
    assert batch_groups["ETF-50"]["planned_row_count"] == 13
    assert batch_groups["ETF-150"]["planned_row_count"] == 0
    assert batch_groups["ETF-300"]["planned_row_count"] == 0
    assert batch_groups["ETF-500"]["planned_row_count"] == 0

    issuers = {group["issuer"]: group["planned_row_count"] for group in plan["issuer_groups"]}
    assert issuers["Vanguard"] == 3
    assert issuers["iShares"] == 3
    assert issuers["State Street Global Advisors"] == 5

    priorities = {
        group["source_pack_readiness_priority"]: group["planned_row_count"]
        for group in plan["source_pack_readiness_priority_groups"]
    }
    assert priorities == {
        "missing_required_issuer_sources": 11,
        "source_backed_partial_review": 2,
    }
    support_states = {
        group["support_review_state"]: group["planned_row_count"]
        for group in plan["support_review_state_groups"]
    }
    assert support_states["pending_review_source_backed_partial"] == 2
    assert support_states["pending_ingestion_source_pack_incomplete"] == 11

    category_groups = {group["bucket_id"]: group for group in plan["category_bucket_groups"]}
    assert category_groups["broad_core_us_equity_beta"]["planned_row_count"] == 7
    assert category_groups["market_cap_and_size_style"]["planned_row_count"] == 7
    assert category_groups["sector_etfs"]["planned_row_count"] == 4
    assert category_groups["industry_theme_passive_us_equity"]["planned_row_count"] == 2
    assert category_groups["dividend_and_shareholder_yield_index"]["planned_row_count"] == 0

    rows = {row["ticker"]: row for row in plan["planned_rows"]}
    voo = rows["VOO"]
    assert voo["batch_milestone"] == "ETF-50"
    assert "broad_core_us_equity_beta" in voo["category_buckets"]
    assert voo["source_pack_readiness_priority"] == "source_backed_partial_review"
    assert voo["plan_unlocks_generated_output"] is False
    assert voo["missing_required_components"] == []
    voo_components = {component["component_id"]: component for component in voo["required_issuer_source_components"]}
    assert voo_components["issuer_page"]["label"] == "issuer page"
    assert voo_components["fact_sheet"]["component_status"] == "pass"
    assert voo_components["methodology_shareholder_or_risk_source"]["component_status"] == "partial"
    assert voo_components["fact_sheet"]["same_fund_check"] == {"required": True, "passed": True}
    assert voo_components["fact_sheet"]["source_use_policy_need"]["current_policy"] == "full_text_allowed"
    assert voo_components["fact_sheet"]["storage_export_rights_need"]["storage_rights"] == "raw_snapshot_allowed"
    assert voo_components["fact_sheet"]["storage_export_rights_need"]["export_rights"] == "excerpts_allowed"
    assert voo_components["fact_sheet"]["parser_readiness"]["parser_ready"] is True
    assert voo_components["fact_sheet"]["freshness_as_of_checksum_placeholders"]["source_checksum"] == (
        "required_before_source_approval"
    )
    assert voo_components["fact_sheet"]["golden_asset_source_handoff"]["plan_approves_handoff"] is False

    spy = rows["SPY"]
    assert spy["source_pack_readiness_priority"] == "missing_required_issuer_sources"
    assert spy["support_review_state"] == "pending_ingestion_source_pack_incomplete"
    assert "issuer_page" in spy["missing_required_components"]
    assert "generated_output_cache_entries" in spy["blocked_generated_surfaces"]
    assert "generated_chat_answers" in spy["diagnostics"]["blocked_generated_surfaces"]


def test_unknown_search_returns_no_generated_route_or_invented_asset_facts():
    response = search_assets("ZZZZ")
    result = response.results[0]

    assert response.state.status.value == "unknown"
    assert response.state.support_classification.value == "unknown"
    assert "no facts are invented" in response.state.message.lower()
    assert result.ticker == "ZZZZ"
    assert result.name == "ZZZZ"
    assert result.asset_type.value == "unknown"
    assert result.can_open_generated_page is False
    assert result.can_answer_chat is False
    assert result.can_compare is False
    assert result.generated_route is None
    assert result.can_request_ingestion is False
    assert result.ingestion_request_route is None
    assert response.state.blocked_explanation is None
    assert result.blocked_explanation is None


def test_eligible_not_cached_assets_require_future_ingestion_only():
    response = search_assets("SPY")
    result = response.results[0]

    assert response.state.status.value == "ingestion_needed"
    assert response.state.support_classification.value == "eligible_not_cached"
    assert response.state.requires_ingestion is True
    assert response.state.can_request_ingestion is True
    assert response.state.ingestion_request_route == "/api/admin/ingest/SPY"
    assert result.ticker == "SPY"
    assert result.asset_type.value == "etf"
    assert result.supported is False
    assert result.eligible_for_ingestion is True
    assert result.requires_ingestion is True
    assert result.can_open_generated_page is False
    assert result.can_answer_chat is False
    assert result.can_compare is False
    assert result.generated_route is None
    assert result.can_request_ingestion is True
    assert result.ingestion_request_route == "/api/admin/ingest/SPY"
    assert response.state.blocked_explanation is None
    assert result.blocked_explanation is None


def test_launch_universe_assets_without_local_packs_are_eligible_not_cached_not_unknown():
    expected_tickers = {
        "SPY",
        "VTI",
        "IVV",
        "IWM",
        "DIA",
        "VGT",
        "XLK",
        "SOXX",
        "SMH",
        "XLF",
        "XLV",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "BRK.B",
        "JPM",
        "UNH",
    }
    assert set(ELIGIBLE_NOT_CACHED_ASSETS) == expected_tickers

    for ticker in sorted(expected_tickers):
        response = search_assets(ticker)
        validated = SearchResponse.model_validate(response.model_dump(mode="json"))
        result = validated.results[0]

        assert validated.state.status.value == "ingestion_needed"
        assert validated.state.support_classification.value == "eligible_not_cached"
        assert validated.state.can_open_generated_page is False
        assert validated.state.requires_ingestion is True
        assert validated.state.can_request_ingestion is True
        assert validated.state.ingestion_request_route == f"/api/admin/ingest/{ticker}"
        assert result.ticker == ticker
        assert result.supported is False
        assert result.status.value == "ingestion_needed"
        assert result.support_classification.value == "eligible_not_cached"
        assert result.eligible_for_ingestion is True
        assert result.requires_ingestion is True
        assert result.can_open_generated_page is False
        assert result.can_answer_chat is False
        assert result.can_compare is False
        assert result.generated_route is None
        assert result.can_request_ingestion is True
        assert result.ingestion_request_route == f"/api/admin/ingest/{ticker}"


def test_top500_manifest_backs_cached_and_eligible_not_cached_stocks_only():
    manifest = load_top500_stock_universe_manifest()
    manifest_tickers = {entry.ticker for entry in manifest.entries}

    assert manifest.local_path == "data/universes/us_common_stocks_top500.current.json"
    assert manifest.rank_limit == 500
    assert "not a recommendation" in manifest.policy_note
    assert {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"} <= manifest_tickers
    assert "GME" not in manifest_tickers

    assert top500_stock_universe_entry("aapl") is not None
    assert top500_stock_universe_entry("gme") is None
    for ticker in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"]:
        response = search_assets(ticker)
        assert response.results[0].asset_type.value == "stock"
        assert response.results[0].support_classification.value in {"cached_supported", "eligible_not_cached"}


def test_candidate_manifest_and_diff_do_not_change_runtime_stock_or_etf_classification():
    with Path("data/universes/us_common_stocks_top500.candidate.2026-04.json").open("r", encoding="utf-8") as handle:
        candidate = Top500CandidateManifest.model_validate(json.load(handle))

    assert candidate.local_path == "data/universes/us_common_stocks_top500.candidate.2026-04.json"
    assert candidate.approved_current_manifest_path == "data/universes/us_common_stocks_top500.current.json"
    assert candidate.manual_approval_required is True

    for ticker in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"]:
        assert search_assets(ticker).results[0].support_classification.value in {
            "cached_supported",
            "eligible_not_cached",
        }
    assert search_assets("GME").state.support_classification.value == "out_of_scope"
    assert search_assets("VOO").state.support_classification.value == "cached_supported"
    assert search_assets("SPY").state.support_classification.value == "eligible_not_cached"
    assert search_assets("TQQQ").state.support_classification.value == "recognized_unsupported"


def test_etf_universe_manifest_contract_distinguishes_cached_eligible_blocked_and_gap_states():
    manifest = load_supported_etf_universe_manifest()
    recognition_manifest = load_recognition_etf_universe_manifest()
    entries = {entry.ticker: entry for entry in manifest.entries}
    recognition_entries = {entry.ticker: entry for entry in recognition_manifest.entries}

    assert manifest.schema_version == "us-equity-etf-universe-v1"
    assert manifest.local_path == "data/universes/us_equity_etfs_supported.current.json"
    assert recognition_manifest.local_path == "data/universes/us_etp_recognition.current.json"
    assert manifest.production_mirror_env_var == "EQUITY_ETF_UNIVERSE_MANIFEST_URI"
    assert recognition_manifest.production_mirror_env_var == "EQUITY_ETF_UNIVERSE_MANIFEST_URI"
    assert "not a recommendation" in manifest.policy_note
    assert manifest.checksum_input
    assert manifest.generated_checksum.startswith("sha256:")
    assert recognition_manifest.checksum_input
    assert recognition_manifest.generated_checksum.startswith("sha256:")

    assert set(cached_supported_etf_entries()) == {"VOO", "QQQ"}
    assert {entry.support_state for entry in cached_supported_etf_entries().values()} == {
        ETFUniverseSupportState.cached_supported
    }
    assert {ticker for ticker, entry in entries.items() if can_generate_output_for_etf_entry(entry)} == {
        "VOO",
        "QQQ",
    }

    expected_eligible = {"SPY", "VTI", "IVV", "IWM", "DIA", "VGT", "XLK", "SOXX", "SMH", "XLF", "XLV"}
    assert set(eligible_not_cached_etf_entries()) == expected_eligible
    for ticker in expected_eligible:
        entry = entries[ticker]
        assert entry.support_state.value == "eligible_not_cached"
        assert entry.launch_cache_state.value == "not_cached"
        assert entry.evidence.evidence_state.value in {"partial", "unknown", "insufficient_evidence"}
        assert can_generate_output_for_etf_entry(entry) is False

    blocked = blocked_etf_entries()
    for ticker, flag_name in [
        ("TQQQ", "leveraged"),
        ("SQQQ", "inverse"),
        ("ARKK", "active"),
        ("BND", "fixed_income"),
        ("GLD", "commodity"),
        ("AOR", "multi_asset"),
        ("VXX", "etn"),
    ]:
        entry = blocked[ticker]
        assert entry.launch_cache_state.value == "blocked"
        assert getattr(entry.exclusion_flags, flag_name) is True
        assert can_generate_output_for_etf_entry(entry) is False

    assert recognition_entries["LTTU"].support_state.value == "unknown"
    assert recognition_entries["LTTU"].evidence.evidence_state.value == "unknown"
    assert recognition_entries["LTTX"].support_state.value == "unavailable"
    assert recognition_entries["LTTX"].evidence.unavailable_reason

    assert load_etf_universe_manifest().local_path == "data/universes/us_equity_etfs_supported.current.json"


def test_etf_universe_lookup_normalizes_tickers_and_preserves_current_search_behavior():
    assert etf_universe_entry("spy") is etf_universe_entry("SPY")
    assert etf_universe_entry("SPY").support_state.value == "eligible_not_cached"  # type: ignore[union-attr]
    assert etf_universe_entry("VOO").support_state.value == "cached_supported"  # type: ignore[union-attr]

    assert search_assets("VOO").state.support_classification.value == "cached_supported"
    assert search_assets("QQQ").state.support_classification.value == "cached_supported"
    assert search_assets("SPY").state.support_classification.value == "eligible_not_cached"
    assert search_assets("VTI").results[0].can_open_generated_page is False
    assert search_assets("TQQQ").state.support_classification.value == "recognized_unsupported"
    assert search_assets("ARKK").state.support_classification.value == "recognized_unsupported"
    assert search_assets("VXX").state.support_classification.value == "out_of_scope"
    assert search_assets("LTTU").state.support_classification.value == "unknown"
    assert search_assets("LTTX").state.support_classification.value == "unknown"


def test_search_uses_etf_manifest_for_blocked_and_gap_states_without_generated_outputs():
    assert {"TQQQ", "SQQQ", "ARKK", "BND", "GLD", "AOR"} <= set(UNSUPPORTED_ASSETS)
    assert "VXX" in OUT_OF_SCOPE_COMMON_STOCKS

    for ticker, expected_state, expected_status, expected_type in [
        ("TQQQ", "recognized_unsupported", "unsupported", "unsupported"),
        ("ARKK", "recognized_unsupported", "unsupported", "unsupported"),
        ("BND", "recognized_unsupported", "unsupported", "unsupported"),
        ("GLD", "recognized_unsupported", "unsupported", "unsupported"),
        ("AOR", "recognized_unsupported", "unsupported", "unsupported"),
        ("VXX", "out_of_scope", "out_of_scope", "etf"),
        ("LTTU", "unknown", "unknown", "etf"),
        ("LTTX", "unknown", "unknown", "etf"),
    ]:
        response = search_assets(ticker)
        result = response.results[0]

        assert result.ticker == ticker
        assert result.asset_type.value == expected_type
        assert response.state.status.value == expected_status
        assert response.state.support_classification.value == expected_state
        assert result.support_classification.value == expected_state
        assert result.supported is False
        assert result.can_open_generated_page is False
        assert result.can_answer_chat is False
        assert result.can_compare is False
        assert result.generated_route is None
        assert result.can_request_ingestion is False
        assert result.ingestion_request_route is None


def test_etf_universe_contract_rejects_duplicate_conflicting_checksum_and_advice_language():
    manifest = load_etf_universe_manifest()
    duplicate = manifest.model_copy(update={"entries": [*manifest.entries, manifest.entries[0]]})
    with pytest.raises(ETFUniverseContractError, match="unique tickers"):
        validate_etf_universe_manifest(duplicate)

    wrong_checksum_entry = manifest.entries[0].model_copy(update={"generated_checksum": "sha256:bad"})
    wrong_checksum = manifest.model_copy(update={"entries": [wrong_checksum_entry, *manifest.entries[1:]]})
    with pytest.raises(ETFUniverseContractError, match="generated checksum"):
        validate_etf_universe_manifest(wrong_checksum)

    conflicting = manifest.entries[2].model_copy(update={"launch_cache_state": "cached"})
    wrong_state = manifest.model_copy(update={"entries": [*manifest.entries[:2], conflicting, *manifest.entries[3:]]})
    with pytest.raises(ETFUniverseContractError, match="conflicting cache state"):
        validate_etf_universe_manifest(wrong_state)

    advice = manifest.model_copy(update={"policy_note": "Users should buy this ETF list."})
    with pytest.raises(ETFUniverseContractError, match="advice-like language"):
        validate_etf_universe_manifest(advice)


def test_recognized_common_stock_outside_manifest_is_out_of_scope_not_eligible():
    response = search_assets("GME")
    result = response.results[0]

    assert response.state.status.value == "out_of_scope"
    assert response.state.support_classification.value == "out_of_scope"
    assert result.ticker == "GME"
    assert result.asset_type.value == "stock"
    assert result.supported is False
    assert result.status.value == "out_of_scope"
    assert result.support_classification.value == "out_of_scope"
    assert result.eligible_for_ingestion is False
    assert result.requires_ingestion is False
    assert result.can_open_generated_page is False
    assert result.can_answer_chat is False
    assert result.can_compare is False
    assert result.generated_route is None
    assert result.can_request_ingestion is False
    assert result.ingestion_request_route is None
    assert response.state.blocked_explanation is not None
    assert result.blocked_explanation is not None
    assert response.state.blocked_explanation.model_dump(mode="json") == result.blocked_explanation.model_dump(
        mode="json"
    )
    assert result.blocked_explanation.schema_version == "search-blocked-explanation-v1"
    assert result.blocked_explanation.status.value == "out_of_scope"
    assert result.blocked_explanation.support_classification.value == "out_of_scope"
    assert result.blocked_explanation.explanation_category == "top500_manifest_scope"
    assert "Top-500 manifest-backed" in result.blocked_explanation.summary
    assert "supported MVP" in result.blocked_explanation.summary
    assert result.blocked_explanation.scope_rationale == result.message
    assert "approved supported ETF manifest" in result.blocked_explanation.supported_v1_scope
    assert result.blocked_explanation.blocked_capabilities.can_open_generated_page is False
    assert result.blocked_explanation.blocked_capabilities.can_answer_chat is False
    assert result.blocked_explanation.blocked_capabilities.can_compare is False
    assert result.blocked_explanation.blocked_capabilities.can_request_ingestion is False
    assert result.blocked_explanation.ingestion_eligible is False
    assert result.blocked_explanation.ingestion_request_route is None
