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
        ("BTC", "Crypto assets"),
        ("TQQQ", "Leveraged ETFs"),
        ("SQQQ", "Inverse ETFs"),
    ]

    for query, expected_reason in cases:
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
