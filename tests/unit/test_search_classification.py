import json
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
from backend.models import SearchResponse
from backend.models import Top500CandidateManifest
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
    assert packet["golden_precache_tickers"] == ["QQQ", "VOO"]
    assert "XLE" in packet["regression_reference_tickers"]
    assert packet["eligible_universe_policy"]["coverage_limit"] == "manifest_defined_reviewed_eligible_universe"
    assert "factor_style" in packet["eligible_universe_policy"]["included_categories"]
    assert "low_volatility" in packet["eligible_universe_policy"]["included_factor_styles"]
    assert "international_or_global_primary_exposure" in packet["eligible_universe_policy"]["excluded_products"]
    assert "issuer_page" in packet["required_issuer_source_pack"]
    assert packet["eligible_supported_entry_count"] == 13
    assert packet["generated_output_eligible_count"] == 2
    assert packet["pending_ingestion_count"] == 11
    assert packet["excluded_product_count"] >= 1
    assert "fixture_or_local_only_provenance_not_launch_approved" in packet["stop_conditions"]
    assert "fixture_source_quality_not_launch_approved" in packet["stop_conditions"]
    assert "issuer_source_pack_review_not_complete" in packet["stop_conditions"]
    assert "missing_golden_ticker" not in packet["stop_conditions"]
    assert "fixture_sized_supported_manifest_not_launch_approved" not in packet["stop_conditions"]

    supported = packet["supported_manifest"]
    recognition = packet["recognition_manifest"]
    assert supported["local_path"] == "data/universes/us_equity_etfs_supported.current.json"
    assert recognition["local_path"] == "data/universes/us_etp_recognition.current.json"
    assert supported["checksum_matches"] is True
    assert recognition["checksum_matches"] is True
    assert supported["support_state_counts"]["cached_supported"] == 2
    assert supported["support_state_counts"]["eligible_not_cached"] == 11
    assert supported["generated_output_eligible_count"] == 2
    assert supported["pending_ingestion_count"] == 11
    assert supported["pending_review_count"] == 13
    assert recognition["support_state_counts"]["recognized_unsupported"] >= 1

    supported_rows = {entry["ticker"]: entry for entry in packet["supported_entries"]}
    recognition_rows = {entry["ticker"]: entry for entry in packet["recognition_entries"]}
    assert supported_rows["VOO"]["generated_output_eligible"] is True
    assert supported_rows["SPY"]["blocked_state_reason"] == "supported_but_not_cached_pending_ingestion"
    assert recognition_rows["TQQQ"]["generated_output_eligible"] is False
    assert recognition_rows["TQQQ"]["blocked_state_reason"] == "blocked_by_exclusion_flags:leveraged"
    assert recognition_rows["TQQQ"]["handoff_status"] == "fixture_metadata_only_review_needed"


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
