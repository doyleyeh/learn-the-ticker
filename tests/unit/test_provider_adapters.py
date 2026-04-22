from pathlib import Path

from backend.models import (
    FreshnessState,
    ProviderDataCategory,
    ProviderKind,
    ProviderResponse,
    ProviderResponseState,
    ProviderSourceUsage,
)
from backend.providers import (
    fetch_mock_provider_response,
    get_mock_provider_adapters,
    mock_etf_issuer_adapter,
    mock_market_reference_adapter,
    mock_recent_development_adapter,
    mock_sec_stock_adapter,
)


ROOT = Path(__file__).resolve().parents[2]


def _assert_no_generated_outputs(response: ProviderResponse) -> None:
    flags = response.generated_output
    assert flags.creates_generated_asset_page is False
    assert flags.creates_generated_chat_answer is False
    assert flags.creates_generated_comparison is False
    assert flags.creates_overview_sections is False
    assert flags.creates_export_payload is False
    assert flags.creates_frontend_route is False


def _assert_same_asset_binding(response: ProviderResponse, ticker: str) -> None:
    source_ids = {source.source_document_id for source in response.source_attributions}
    assert {source.asset_ticker for source in response.source_attributions} <= {ticker}
    assert {fact.asset_ticker for fact in response.facts} <= {ticker}
    assert {event.asset_ticker for event in response.recent_developments} <= {ticker}
    for fact in response.facts:
        assert set(fact.source_document_ids) <= source_ids
        assert fact.uses_glossary_as_support is False
        assert not any("glossary" in citation_id.lower() for citation_id in fact.citation_ids)
    for event in response.recent_developments:
        assert event.source_document_id in source_ids
        assert not any("glossary" in citation_id.lower() for citation_id in event.citation_ids)


def test_mock_adapter_factory_exposes_explicit_capabilities_without_live_calls():
    adapters = get_mock_provider_adapters()

    assert set(adapters) == {
        ProviderKind.sec,
        ProviderKind.etf_issuer,
        ProviderKind.market_reference,
        ProviderKind.recent_development,
    }
    for adapter in adapters.values():
        assert adapter.capability.provider_kind == adapter.provider_kind
        assert adapter.capability.requires_credentials is False
        assert adapter.capability.live_calls_allowed is False
        request = adapter.request("AAPL") if hasattr(adapter, "request") else None
        assert request is not None
        response = adapter.fetch(request)
        validated = ProviderResponse.model_validate(response.model_dump(mode="json"))
        assert validated.no_live_external_calls is True
        _assert_no_generated_outputs(validated)


def test_sec_stock_adapter_returns_canonical_aapl_facts_with_official_attribution():
    adapter = mock_sec_stock_adapter()
    response = adapter.fetch(adapter.request("AAPL"))

    assert response.provider_kind is ProviderKind.sec
    assert response.data_category is ProviderDataCategory.canonical_stock_facts
    assert response.state is ProviderResponseState.supported
    assert response.asset is not None
    assert response.asset.ticker == "AAPL"
    assert response.freshness.freshness_state is FreshnessState.fresh
    assert response.freshness.as_of_date == "2026-04-01"
    assert response.licensing.export_allowed is True
    assert response.licensing.redistribution_allowed is False
    assert {fact.field_name for fact in response.facts} >= {"primary_business", "net_sales_trend_available"}
    assert all(source.is_official is True for source in response.source_attributions)
    assert all(source.source_rank == 1 for source in response.source_attributions)
    assert all(source.usage is ProviderSourceUsage.canonical for source in response.source_attributions)
    assert all(source.can_support_canonical_facts is True for source in response.source_attributions)
    assert all(fact.fact_layer == "canonical" for fact in response.facts)
    _assert_same_asset_binding(response, "AAPL")
    _assert_no_generated_outputs(response)


def test_etf_issuer_adapter_returns_voo_and_qqq_official_facts_and_holdings_metadata():
    adapter = mock_etf_issuer_adapter()

    for ticker, benchmark in [("VOO", "S&P 500 Index"), ("QQQ", "Nasdaq-100 Index")]:
        response = adapter.fetch(adapter.request(ticker))

        assert response.provider_kind is ProviderKind.etf_issuer
        assert response.state is ProviderResponseState.supported
        assert response.asset is not None
        assert response.asset.ticker == ticker
        assert response.licensing.export_allowed is True
        assert response.source_attributions
        assert all(source.is_official is True for source in response.source_attributions)
        assert all(source.source_rank == 1 for source in response.source_attributions)
        fields = {fact.field_name: fact for fact in response.facts}
        assert fields["benchmark"].value == benchmark
        assert fields["expense_ratio"].unit == "%"
        assert fields["holdings_count"].data_category is ProviderDataCategory.etf_holdings_metadata
        _assert_same_asset_binding(response, ticker)
        _assert_no_generated_outputs(response)


def test_market_reference_adapter_covers_supported_and_eligible_not_cached_with_restricted_licensing():
    adapter = mock_market_reference_adapter()

    for ticker in ["AAPL", "VOO", "QQQ"]:
        response = adapter.fetch(adapter.request(ticker, ProviderDataCategory.asset_resolution))
        assert response.state is ProviderResponseState.supported
        assert response.asset is not None
        assert response.asset.ticker == ticker
        assert response.source_attributions[0].source_rank == 4
        assert response.source_attributions[0].usage is ProviderSourceUsage.structured_reference
        assert response.source_attributions[0].is_official is False
        assert response.licensing.export_allowed is False
        assert response.licensing.redistribution_allowed is False
        assert "restricted provider data" in response.licensing.permission_note
        assert response.facts[0].fact_layer == "structured_reference"
        _assert_same_asset_binding(response, ticker)
        _assert_no_generated_outputs(response)

    for ticker in ["SPY", "MSFT"]:
        response = adapter.fetch(adapter.request(ticker, ProviderDataCategory.asset_resolution))
        assert response.state is ProviderResponseState.eligible_not_cached
        assert response.asset is not None
        assert response.asset.ticker == ticker
        assert response.asset.supported is True
        assert response.facts[0].value["eligible_not_cached"] is True
        assert response.generated_output.creates_generated_asset_page is False


def test_provider_failure_states_are_explicit_without_invented_facts():
    market = mock_market_reference_adapter()
    recent = mock_recent_development_adapter()

    for ticker in ["BTC", "TQQQ", "SQQQ"]:
        response = market.fetch(market.request(ticker))
        assert response.state is ProviderResponseState.unsupported
        assert response.asset is not None
        assert response.asset.supported is False
        assert response.facts == []
        assert response.source_attributions == []
        assert response.errors[0].code == "recognized_unsupported_asset"
        _assert_no_generated_outputs(response)

    unknown = market.fetch(market.request("ZZZZ"))
    assert unknown.state is ProviderResponseState.unknown
    assert unknown.asset is None
    assert unknown.facts == []
    assert unknown.errors[0].code == "unknown_asset"
    _assert_no_generated_outputs(unknown)

    unavailable = recent.fetch(recent.request("ZZZZ"))
    assert unavailable.state is ProviderResponseState.unavailable
    assert unavailable.asset is None
    assert unavailable.recent_developments == []
    assert unavailable.errors[0].code == "provider_fixture_unavailable"
    assert unavailable.errors[0].retryable is True
    _assert_no_generated_outputs(unavailable)


def test_recent_development_adapter_separates_recent_context_from_canonical_facts():
    adapter = mock_recent_development_adapter()
    aapl = adapter.fetch(adapter.request("AAPL"))

    assert aapl.state is ProviderResponseState.supported
    assert aapl.facts == []
    assert len(aapl.recent_developments) == 1
    event = aapl.recent_developments[0]
    assert event.asset_ticker == "AAPL"
    assert event.event_date == "2026-04-01"
    assert event.source_date == "2026-04-01"
    assert event.retrieved_at
    assert event.source_document_id == aapl.source_attributions[0].source_document_id
    assert event.freshness_state is FreshnessState.fresh
    assert event.is_high_signal is True
    assert event.can_overwrite_canonical_facts is False
    assert aapl.source_attributions[0].usage is ProviderSourceUsage.recent_context
    assert aapl.source_attributions[0].can_support_canonical_facts is False
    assert aapl.source_attributions[0].can_support_recent_developments is True
    _assert_same_asset_binding(aapl, "AAPL")

    for ticker in ["VOO", "QQQ"]:
        no_signal = adapter.fetch(adapter.request(ticker))
        assert no_signal.state is ProviderResponseState.no_high_signal
        assert no_signal.recent_developments == []
        assert no_signal.source_attributions[0].asset_ticker == ticker
        assert no_signal.source_attributions[0].usage is ProviderSourceUsage.recent_context
        assert no_signal.source_attributions[0].can_support_canonical_facts is False
        assert no_signal.freshness.as_of_date == "2026-04-20"
        _assert_no_generated_outputs(no_signal)


def test_source_hierarchy_keeps_official_sources_ahead_of_structured_and_recent_context():
    sec_aapl = fetch_mock_provider_response(ProviderKind.sec, "AAPL")
    market_aapl = fetch_mock_provider_response(ProviderKind.market_reference, "AAPL")
    issuer_voo = fetch_mock_provider_response(ProviderKind.etf_issuer, "VOO")
    market_voo = fetch_mock_provider_response(ProviderKind.market_reference, "VOO")
    recent_aapl = fetch_mock_provider_response(ProviderKind.recent_development, "AAPL")

    assert min(source.source_rank for source in sec_aapl.source_attributions) < min(
        source.source_rank for source in market_aapl.source_attributions
    )
    assert min(source.source_rank for source in issuer_voo.source_attributions) < min(
        source.source_rank for source in market_voo.source_attributions
    )
    assert all(source.usage is ProviderSourceUsage.recent_context for source in recent_aapl.source_attributions)
    assert all(source.can_support_canonical_facts is False for source in recent_aapl.source_attributions)
    assert all(event.can_overwrite_canonical_facts is False for event in recent_aapl.recent_developments)


def test_provider_module_has_no_live_call_or_credential_imports():
    source = (ROOT / "backend" / "providers.py").read_text(encoding="utf-8")
    forbidden = [
        "import requests",
        "import httpx",
        "urllib",
        "socket",
        "boto3",
        "polygon",
        "massive",
        "finnhub",
        "benzinga",
        "os.environ",
        "api_key",
    ]
    for needle in forbidden:
        assert needle not in source
