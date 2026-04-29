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
