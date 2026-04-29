import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from backend.models import FreshnessState, SourceParserStatus
from backend.provider_adapters.sec_stock import SEC_STOCK_FIXTURES
from backend.models import Top500CandidateManifest
from backend.source_policy import SourceHandoffContractError
from backend.top500_candidate_manifest import (
    TOP500_APPROVED_CURRENT_MANIFEST_PATH,
    Top500CandidateManifestContractError,
    assert_manual_approval_for_promotion,
    build_stock_sec_source_pack_readiness_packet,
    build_top500_sec_source_pack_batch_plan,
    build_top500_operator_review_summary,
    generate_top500_candidate_manifest,
    generate_top500_candidate_manifest_from_fixture_paths,
    inspect_top500_candidate_review_packet,
    promotion_requires_manual_approval,
    validate_top500_candidate_manifest,
)


FIXTURE_DIR = Path("tests/fixtures/top500_refresh")


def _load_fixture(name: str) -> dict:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _primary_result(rank_limit: int = 10):
    return generate_top500_candidate_manifest_from_fixture_paths(
        primary_fixture_path=FIXTURE_DIR / "official_iwb_holdings.json",
        fallback_fixture_paths=[
            FIXTURE_DIR / "official_spy_holdings.json",
            FIXTURE_DIR / "official_ivv_holdings.json",
            FIXTURE_DIR / "official_voo_holdings.json",
        ],
        sec_company_fixture_path=FIXTURE_DIR / "sec_company_tickers_exchange.json",
        nasdaq_symbol_fixture_path=FIXTURE_DIR / "nasdaq_symbol_directory.json",
        candidate_month="2026-04",
        rank_limit=rank_limit,
    )


def test_iwb_primary_candidate_manifest_preserves_review_contract_and_never_points_at_current_path():
    result = _primary_result()
    manifest = validate_top500_candidate_manifest(result.candidate_manifest)
    diff = result.diff_report

    assert result.boundary == "top500-reviewed-candidate-refresh-v1"
    assert manifest.local_path == "data/universes/us_common_stocks_top500.candidate.2026-04.json"
    assert manifest.approved_current_manifest_path == TOP500_APPROVED_CURRENT_MANIFEST_PATH
    assert manifest.rank_basis.value == "iwb_weight_proxy"
    assert manifest.source_used == ["IWB"]
    assert manifest.fallback_used is False
    assert manifest.manual_approval_required is True
    assert manifest.generated_checksum.startswith("sha256:")
    assert any(
        "one-cycle safe-promotion boundary" in note.lower() for note in manifest.operator_review_note_block
    )
    assert len(manifest.entries) == 10
    assert [entry.rank for entry in manifest.entries] == list(range(1, 11))
    assert {entry.ticker for entry in manifest.entries} == {
        "AAPL",
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
    assert "SPY" not in {entry.ticker for entry in manifest.entries}
    assert "CASH_USD" not in {entry.ticker for entry in manifest.entries}
    assert "PFFD" not in {entry.ticker for entry in manifest.entries}
    assert next(entry for entry in manifest.entries if entry.ticker == "BRK.B").warnings == [
        "normalized_ticker_from_BRK-B"
    ]
    assert all(entry.validation_status.value == "validated" for entry in manifest.entries)
    assert all(entry.cik and entry.exchange for entry in manifest.entries)
    assert all(entry.source_checksum == manifest.source_checksums["IWB"] for entry in manifest.entries)

    assert diff.candidate_manifest_path == manifest.local_path
    assert diff.approved_current_manifest_path == TOP500_APPROVED_CURRENT_MANIFEST_PATH
    assert diff.added_tickers == []
    assert diff.removed_tickers == []
    assert diff.rank_changes == []
    assert diff.missing_ciks == []
    assert diff.nasdaq_validation_failures == []
    assert diff.manual_approval_required is True
    assert any("one-cycle safe-promotion boundary" in note.lower() for note in diff.operator_review_note_block)


def test_top500_operator_review_summary_is_review_only_and_not_launch_approval():
    result = _primary_result()
    summary = build_top500_operator_review_summary(result)

    assert summary["schema_version"] == "top500-launch-review-summary-v1"
    assert summary["boundary"] == "top500-launch-manifest-review-only-v1"
    assert summary["review_only"] is True
    assert summary["no_live_external_calls"] is True
    assert summary["approved_current_manifest_path"] == TOP500_APPROVED_CURRENT_MANIFEST_PATH
    assert summary["candidate_manifest_path"].endswith(".candidate.2026-04.json")
    assert summary["diff_report_path"].endswith(".diff.2026-04.json")
    assert summary["review_summary_path"].endswith(".review.2026-04.json")
    assert summary["manual_promotion_required"] is True
    assert summary["launch_approved"] is False
    assert summary["review_status"] == "review_needed"
    assert summary["candidate_checksum_matches"] is True
    assert summary["diff_checksum_matches"] is True
    assert summary["source_used"] == ["IWB"]
    assert summary["rank_basis"] == "iwb_weight_proxy"
    assert summary["entry_count"] == 10
    assert "fixture_sized_candidate_not_launch_approved" in summary["stop_conditions"]
    assert "fixture_or_local_only_provenance_not_launch_approved" in summary["stop_conditions"]
    assert "missing_manual_review_or_approval" in summary["stop_conditions"]
    assert "recommendation" in summary["non_advice_framing"]


def test_stock_sec_source_pack_readiness_packet_covers_current_and_candidate_manifests_without_unlocks():
    packet = build_stock_sec_source_pack_readiness_packet()

    assert packet["schema_version"] == "stock-sec-source-pack-readiness-v1"
    assert packet["boundary"] == "stock-sec-source-pack-readiness-review-only-v1"
    assert packet["review_only"] is True
    assert packet["no_live_external_calls"] is True
    assert packet["runtime_manifest_authority"] == TOP500_APPROVED_CURRENT_MANIFEST_PATH
    assert packet["candidate_manifest_paths"] == ["data/universes/us_common_stocks_top500.candidate.2026-04.json"]
    assert packet["manifests_promoted"] is False
    assert packet["sources_approved_by_packet"] is False
    assert packet["retrieval_alone_approves_evidence"] is False
    assert packet["launch_approved"] is False
    assert packet["required_sec_components"] == [
        "sec_submissions",
        "latest_annual_filing",
        "latest_quarterly_filing_when_available",
        "xbrl_company_facts",
    ]
    assert packet["review_status"] == "review_needed"
    assert "stock_sec_source_pack_review_not_complete" in packet["stop_conditions"]
    assert "insufficient_sec_evidence" in packet["stop_conditions"]
    assert "partial_sec_source_pack" in packet["stop_conditions"]

    counts = packet["readiness_counts"]
    assert counts["current_manifest_rows"] == 10
    assert counts["candidate_manifest_rows"] == 10
    assert counts["unique_tickers"] == 10
    assert counts["partial"] == 2
    assert counts["insufficient_evidence"] == 18
    assert counts["source_backed_partial_rendering_ready"] == 2
    assert counts["review_packet_unlocks_generated_output"] == 0

    current_aapl = next(row for row in packet["rows"] if row["manifest_kind"] == "current" and row["ticker"] == "AAPL")
    assert current_aapl["source_pack_status"] == "partial"
    assert current_aapl["source_backed_partial_rendering_ready"] is True
    assert current_aapl["review_packet_unlocks_generated_output"] is False
    components = {component["component_id"]: component for component in current_aapl["components"]}
    assert components["sec_submissions"]["status"] == "pass"
    assert components["latest_annual_filing"]["status"] == "pass"
    assert components["latest_annual_filing"]["citation_ready"] is True
    assert components["latest_annual_filing"]["same_asset_validation"] is True
    assert components["latest_annual_filing"]["official_source_status"] is True
    assert components["latest_annual_filing"]["source_use_policy"] == "full_text_allowed"
    assert components["latest_annual_filing"]["parser_status"] == "parsed"
    assert components["latest_annual_filing"]["freshness_state"] == "fresh"
    assert components["latest_annual_filing"]["golden_asset_source_handoff_status"] == "approved"
    assert components["xbrl_company_facts"]["status"] == "pass"
    assert components["xbrl_company_facts"]["citation_ready"] is True
    assert components["latest_quarterly_filing_when_available"]["status"] == "partial"
    assert components["latest_quarterly_filing_when_available"]["required"] is False
    assert "latest_10q_not_available_in_fixture" in components["latest_quarterly_filing_when_available"]["reason_codes"]

    current_msft = next(row for row in packet["rows"] if row["manifest_kind"] == "current" and row["ticker"] == "MSFT")
    assert current_msft["source_pack_status"] == "insufficient_evidence"
    assert current_msft["source_backed_partial_rendering_ready"] is False
    assert all(component["citation_ready"] is False for component in current_msft["components"])
    assert all(component["golden_asset_source_handoff_status"] != "approved" for component in current_msft["components"])


def test_stock_sec_source_pack_readiness_reports_stale_parser_failed_and_wrong_asset_states():
    fixture = SEC_STOCK_FIXTURES["AAPL"]
    stale_sources = tuple(
        replace(source, freshness_state=FreshnessState.stale)
        if source.source_document_id == "provider_sec_aapl_10k_2026"
        else source
        for source in fixture.sources
    )
    stale_packet = build_stock_sec_source_pack_readiness_packet(
        candidate_manifests=[],
        sec_fixture_by_ticker={"AAPL": replace(fixture, sources=stale_sources)},
    )
    stale_aapl = next(row for row in stale_packet["rows"] if row["ticker"] == "AAPL")
    stale_components = {component["component_id"]: component for component in stale_aapl["components"]}
    assert stale_aapl["source_pack_status"] == "stale"
    assert stale_components["latest_annual_filing"]["status"] == "stale"
    assert stale_components["latest_annual_filing"]["evidence_state"] == "stale"

    parser_failed_packet = build_stock_sec_source_pack_readiness_packet(
        candidate_manifests=[],
        parser_status_by_source_document_id={"provider_sec_aapl_xbrl_2026": SourceParserStatus.failed},
    )
    parser_failed_aapl = next(row for row in parser_failed_packet["rows"] if row["ticker"] == "AAPL")
    parser_failed_xbrl = next(
        component for component in parser_failed_aapl["components"] if component["component_id"] == "xbrl_company_facts"
    )
    assert parser_failed_aapl["source_pack_status"] == "blocked"
    assert parser_failed_xbrl["status"] == "blocked"
    assert "parser_failed" in parser_failed_xbrl["reason_codes"]
    assert parser_failed_xbrl["golden_asset_source_handoff_status"] == "blocked"

    wrong_identity = replace(fixture.identity, ticker="MSFT", cik="0000789019")
    wrong_asset_packet = build_stock_sec_source_pack_readiness_packet(
        candidate_manifests=[],
        sec_fixture_by_ticker={"AAPL": replace(fixture, identity=wrong_identity)},
    )
    wrong_asset_aapl = next(row for row in wrong_asset_packet["rows"] if row["ticker"] == "AAPL")
    assert wrong_asset_aapl["source_pack_status"] == "blocked"
    assert all(
        component["same_asset_validation"] is False
        for component in wrong_asset_aapl["components"]
        if component["source_document_id"]
    )
    assert all(
        "wrong_asset_sec_source" in component["reason_codes"]
        for component in wrong_asset_aapl["components"]
        if component["source_document_id"]
    )


def test_top500_sec_source_pack_batch_plan_is_review_only_and_current_manifest_authoritative():
    plan = build_top500_sec_source_pack_batch_plan()

    assert plan["schema_version"] == "top500-sec-source-pack-batch-plan-v1"
    assert plan["boundary"] == "top500-sec-source-pack-batch-planning-review-only-v1"
    assert plan["review_only"] is True
    assert plan["deterministic"] is True
    assert plan["no_live_external_calls"] is True
    assert plan["runtime_manifest_authority"] == TOP500_APPROVED_CURRENT_MANIFEST_PATH
    assert plan["current_manifest_path"] == TOP500_APPROVED_CURRENT_MANIFEST_PATH
    assert plan["current_manifest_entry_count"] == 10
    assert plan["current_manifest_rows_planned"] == 10
    assert plan["support_resolved_from_current_manifest_only"] is True
    assert plan["candidate_or_priority_data_resolves_runtime_support"] is False
    assert plan["live_provider_or_exchange_data_resolves_runtime_support"] is False
    assert plan["planner_started_ingestion"] is False
    assert plan["sources_approved_by_plan"] is False
    assert plan["top500_manifest_promoted"] is False
    assert plan["generated_output_cache_entries_written"] is False
    assert plan["generated_output_unlocked_by_plan"] is False
    assert "generated_pages" in plan["blocked_generated_surfaces"]
    assert "generated_risk_summaries" in plan["blocked_generated_surfaces"]

    relationship = plan["candidate_relationship_diagnostics"]
    assert relationship["candidate_artifacts_available"] is True
    assert relationship["candidate_data_used_for_runtime_support"] is False
    assert relationship["candidate_only_rows_unlock_generated_output"] is False
    assert relationship["candidate_manifest_paths"] == ["data/universes/us_common_stocks_top500.candidate.2026-04.json"]
    assert relationship["shared_current_candidate_ticker_count"] == 10

    assert plan["planning_summary"] == {
        "planned_row_count": 10,
        "batch_count": 5,
        "high_demand_pre_cache_count": 1,
        "top500_review_count": 9,
        "source_backed_partial_ready_count": 1,
        "insufficient_evidence_count": 9,
        "blocked_generated_surface_count": 9,
    }
    assert plan["manifest_rank_ordering"] == [
        {"rank": 1, "ticker": "AAPL"},
        {"rank": 2, "ticker": "MSFT"},
        {"rank": 3, "ticker": "NVDA"},
        {"rank": 4, "ticker": "AMZN"},
        {"rank": 5, "ticker": "GOOGL"},
        {"rank": 6, "ticker": "META"},
        {"rank": 7, "ticker": "TSLA"},
        {"rank": 8, "ticker": "BRK.B"},
        {"rank": 9, "ticker": "JPM"},
        {"rank": 10, "ticker": "UNH"},
    ]
    batch_groups = {group["batch_name"]: group for group in plan["batch_groups"]}
    assert batch_groups["high-demand-pre-cache"]["tickers"] == ["AAPL"]
    assert batch_groups["TOP500-50"]["tickers"] == ["MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"]
    assert batch_groups["TOP500-150"]["planned_row_count"] == 0

    status_groups = {group["source_pack_status"]: group for group in plan["source_pack_status_groups"]}
    assert status_groups["partial"]["tickers"] == ["AAPL"]
    assert status_groups["insufficient_evidence"]["planned_row_count"] == 9
    priority_groups = {
        group["readiness_priority"]: group["planned_row_count"]
        for group in plan["readiness_priority_groups"]
    }
    assert priority_groups == {
        "approved_partial_ready_needs_quarterly_or_full_review": 1,
        "missing_required_sec_sources": 9,
    }
    assert plan["source_handoff_readiness"]["approved_component_count"] == 3
    assert plan["source_handoff_readiness"]["pending_review_component_count"] == 37
    assert plan["source_handoff_readiness"]["rejected_or_unclear_rights_component_count"] == 37
    assert plan["parser_readiness"]["parser_status_counts"] == {
        "parsed": 3,
        "partial": 0,
        "pending_review": 37,
        "failed": 0,
    }
    assert plan["freshness_as_of_checksum_placeholder_status"]["freshness_state_counts"] == {
        "fresh": 3,
        "stale": 0,
        "unknown": 0,
        "unavailable": 37,
    }
    assert plan["freshness_as_of_checksum_placeholder_status"]["checksum_required_count"] == 3
    assert plan["freshness_as_of_checksum_placeholder_status"]["checksum_present_count"] == 0
    assert "candidate_artifacts_are_diagnostic_only" in plan["stop_conditions"]

    aapl = next(row for row in plan["planned_rows"] if row["ticker"] == "AAPL")
    assert aapl["manifest_rank"] == 1
    assert aapl["batch_name"] == "high-demand-pre-cache"
    assert aapl["high_demand_pre_cache"] is True
    assert aapl["source_pack_status"] == "partial"
    assert aapl["source_backed_partial_rendering_ready"] is True
    assert aapl["fallback_state"] == "source_backed_partial"
    assert aapl["generated_output_unlocked_by_plan"] is False
    components = {component["component_id"]: component for component in aapl["required_sec_source_components"]}
    assert components["sec_submissions"]["source_snapshot_requirement"] == "required_before_evidence_use"
    assert components["sec_submissions"]["checksum_status"] == "placeholder_required"
    assert components["sec_submissions"]["golden_asset_source_handoff_action"] == "approved"
    assert components["latest_quarterly_filing_when_available"]["status"] == "partial"
    assert components["latest_quarterly_filing_when_available"]["partial_or_unavailable_fallback_state"] == "partial"

    msft = next(row for row in plan["planned_rows"] if row["ticker"] == "MSFT")
    assert msft["batch_name"] == "TOP500-50"
    assert msft["source_pack_status"] == "insufficient_evidence"
    assert msft["fallback_state"] == "insufficient_evidence"
    assert all(
        component["source_snapshot_requirement"] == "blocked_until_source_available"
        for component in msft["required_sec_source_components"]
    )


def test_top500_operator_review_inspection_reports_checksum_stop_condition():
    result = _primary_result()
    payload = result.candidate_manifest.model_dump(mode="json")
    payload["generated_checksum"] = "sha256:bad"
    tampered_manifest = Top500CandidateManifest.model_validate(payload)

    summary = inspect_top500_candidate_review_packet(
        candidate_manifest=tampered_manifest,
        diff_report=result.diff_report,
    )

    assert summary["review_status"] == "blocked"
    assert summary["candidate_checksum_matches"] is False
    assert "candidate_checksum_mismatch" in summary["stop_conditions"]


def test_fixture_candidate_file_matches_generation_contract_and_remains_candidate_only():
    result = _primary_result()
    with Path("data/universes/us_common_stocks_top500.candidate.2026-04.json").open("r", encoding="utf-8") as handle:
        fixture_manifest = Top500CandidateManifest.model_validate(json.load(handle))

    assert fixture_manifest.local_path.endswith(".candidate.2026-04.json")
    assert fixture_manifest.approved_current_manifest_path == "data/universes/us_common_stocks_top500.current.json"
    assert fixture_manifest.generated_checksum == result.candidate_manifest.generated_checksum
    assert fixture_manifest.model_dump(mode="json") == result.candidate_manifest.model_dump(mode="json")


def test_parser_invalid_iwb_uses_sp500_fallback_sources_with_explicit_reason_and_review_triggers():
    primary = _load_fixture("official_iwb_holdings.json")
    primary["source"]["parser_status"] = "failed"
    primary["source"]["parser_failure_diagnostics"] = "Mocked parser failure for fallback contract coverage."
    result = generate_top500_candidate_manifest(
        primary_fixture=primary,
        fallback_fixtures=[
            _load_fixture("official_spy_holdings.json"),
            _load_fixture("official_ivv_holdings.json"),
            _load_fixture("official_voo_holdings.json"),
        ],
        sec_rows={
            row["ticker"]: {key: str(value) for key, value in row.items()}
            for row in _load_fixture("sec_company_tickers_exchange.json")["data"]
        },
        nasdaq_rows={
            row["Symbol"].replace("-", "."): {key: str(value) for key, value in row.items()}
            for row in _load_fixture("nasdaq_symbol_directory.json")["rows"]
        },
        candidate_month="2026-04",
        rank_limit=5,
    )

    manifest = result.candidate_manifest
    assert manifest.fallback_used is True
    assert manifest.fallback_reason == "iwb_parser_failed"
    assert manifest.rank_basis.value == "sp500_etf_weight_proxy_fallback"
    assert manifest.source_used == ["SPY", "IVV", "VOO"]
    assert {entry.rank_basis.value for entry in manifest.entries} == {"sp500_etf_weight_proxy_fallback"}
    assert "fallback_sources_used" in manifest.manual_review_triggers
    assert "iwb_parser_failed" in manifest.manual_review_triggers
    assert "source_snapshot_or_parser_warning" in manifest.manual_review_triggers
    assert result.diff_report.fallback_used is True
    assert result.diff_report.source_checksums == manifest.source_checksums


def test_selected_sources_must_pass_golden_asset_source_handoff_before_ranking():
    primary = _load_fixture("official_iwb_holdings.json")
    primary["source"]["parser_status"] = "failed"
    fallback = _load_fixture("official_spy_holdings.json")
    fallback["source"]["source_identity"] = "private://internal/top500-refresh"

    with pytest.raises(SourceHandoffContractError, match="hidden_or_internal_source"):
        generate_top500_candidate_manifest(
            primary_fixture=primary,
            fallback_fixtures=[
                fallback,
                _load_fixture("official_ivv_holdings.json"),
                _load_fixture("official_voo_holdings.json"),
            ],
            sec_rows={},
            nasdaq_rows={},
            candidate_month="2026-04",
            rank_limit=5,
        )


def test_sec_and_nasdaq_validation_warns_or_rejects_disqualifying_rows_before_diff_report():
    primary = deepcopy(_load_fixture("official_iwb_holdings.json"))
    primary["holdings"].insert(
        0,
        {
            "source_id": primary["source"]["source_id"],
            "ticker": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "weight": 9.0,
            "asset_type": "stock",
            "security_type": "common_stock",
            "exchange": "NYSE ARCA",
        },
    )
    primary["holdings"].append(
        {
            "source_id": primary["source"]["source_id"],
            "ticker": "XYZ",
            "name": "Missing SEC common stock fixture",
            "weight": 2.05,
            "asset_type": "stock",
            "security_type": "common_stock",
            "exchange": "NASDAQ",
        }
    )
    result = generate_top500_candidate_manifest(
        primary_fixture=primary,
        fallback_fixtures=[
            _load_fixture("official_spy_holdings.json"),
            _load_fixture("official_ivv_holdings.json"),
            _load_fixture("official_voo_holdings.json"),
        ],
        sec_rows={
            row["ticker"]: {key: str(value) for key, value in row.items()}
            for row in _load_fixture("sec_company_tickers_exchange.json")["data"]
        },
        nasdaq_rows={
            row["Symbol"].replace("-", "."): {key: str(value) for key, value in row.items()}
            for row in _load_fixture("nasdaq_symbol_directory.json")["rows"]
        },
        candidate_month="2026-04",
        rank_limit=12,
        validation_threshold=0.75,
    )

    assert "SPY" not in {entry.ticker for entry in result.candidate_manifest.entries}
    assert {"ticker": "SPY", "reason": "nasdaq_etf_flag", "field": "ETF"} in result.diff_report.nasdaq_validation_failures
    xyz = next(entry for entry in result.candidate_manifest.entries if entry.ticker == "XYZ")
    assert xyz.validation_status.value == "warning"
    assert xyz.cik is None
    assert "missing_sec_company_tickers_exchange_validation" in xyz.warnings
    assert "missing_cik" in xyz.warnings
    assert "XYZ" in result.diff_report.missing_ciks
    assert "nasdaq_validation_failures" in result.candidate_manifest.manual_review_triggers
    assert "missing_cik_review" in result.candidate_manifest.manual_review_triggers


def test_manual_approval_gate_blocks_promotion_without_replacing_current_manifest():
    manifest = _primary_result().candidate_manifest

    assert promotion_requires_manual_approval(manifest) is True
    with pytest.raises(Top500CandidateManifestContractError, match="Manual approval is required"):
        assert_manual_approval_for_promotion(manifest)

    assert_manual_approval_for_promotion(manifest, approved=True)
