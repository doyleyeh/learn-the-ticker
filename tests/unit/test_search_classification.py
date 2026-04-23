from backend.data import (
    ELIGIBLE_NOT_CACHED_ASSETS,
    load_top500_stock_universe_manifest,
    top500_stock_universe_entry,
)
from backend.models import SearchResponse
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
    assert "non-leveraged U.S.-listed equity ETFs" in result.blocked_explanation.supported_v1_scope
    assert result.blocked_explanation.blocked_capabilities.can_open_generated_page is False
    assert result.blocked_explanation.blocked_capabilities.can_answer_chat is False
    assert result.blocked_explanation.blocked_capabilities.can_compare is False
    assert result.blocked_explanation.blocked_capabilities.can_request_ingestion is False
    assert result.blocked_explanation.ingestion_eligible is False
    assert result.blocked_explanation.ingestion_request_route is None
