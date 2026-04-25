from dataclasses import replace
from pathlib import Path

import pytest

from backend.data import ELIGIBLE_NOT_CACHED_ASSETS
from backend.models import (
    DEFAULT_BLOCKED_EXCERPT_BEHAVIOR,
    DEFAULT_BLOCKED_SOURCE_OPERATIONS,
    EvidenceState,
    FreshnessState,
    ProviderDataCategory,
    ProviderKind,
    ProviderResponse,
    ProviderResponseState,
    ProviderSourceUsage,
    SourceAllowlistStatus,
    SourcePolicyDecision,
    SourcePolicyDecisionState,
    SourceQuality,
    SourceUsePolicy,
)
from backend.provider_adapters import sec_stock as sec_stock_module
from backend.provider_adapters.sec_stock import (
    SEC_STOCK_FIXTURE_CONTRACT_VERSION,
    SEC_STOCK_FIXTURES,
    SecStockFixtureContractError,
    build_sec_stock_provider_response,
    sec_stock_fixture_for_ticker,
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
    fields = {fact.field_name: fact for fact in response.facts}
    assert set(fields) >= {
        "sec_stock_identity",
        "selected_sec_filing_metadata",
        "primary_business",
        "net_sales_trend_available",
        "xbrl_company_fact_net_sales_2024",
        "xbrl_company_fact_net_sales_2023",
        "current_valuation_metrics",
    }
    assert fields["sec_stock_identity"].value == {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
        "exchange": "NASDAQ",
        "asset_type": "stock",
        "support_state": "supported",
        "top500_manifest_member": True,
        "eligible_not_cached": False,
    }
    assert fields["selected_sec_filing_metadata"].value["form_type"] == "10-K"
    assert fields["selected_sec_filing_metadata"].value["source_document_id"] == "provider_sec_aapl_10k_2026"
    assert fields["selected_sec_filing_metadata"].value["official_publisher"] == "U.S. SEC"
    assert fields["xbrl_company_fact_net_sales_2024"].value["period"] == "FY2024"
    assert fields["xbrl_company_fact_net_sales_2024"].unit == "USD"
    assert fields["current_valuation_metrics"].evidence_state is EvidenceState.unavailable
    assert fields["current_valuation_metrics"].freshness_state is FreshnessState.unavailable
    assert fields["current_valuation_metrics"].source_document_ids == []
    assert all(source.is_official is True for source in response.source_attributions)
    assert all(source.allowlist_status.value == "allowed" for source in response.source_attributions)
    assert all(source.source_use_policy.value == "full_text_allowed" for source in response.source_attributions)
    assert all(source.permitted_operations.can_store_raw_text is True for source in response.source_attributions)
    assert all(source.source_rank == 1 for source in response.source_attributions)
    assert all(source.usage is ProviderSourceUsage.canonical for source in response.source_attributions)
    assert all(source.can_support_canonical_facts is True for source in response.source_attributions)
    assert all(fact.fact_layer == "canonical" for fact in response.facts)
    _assert_same_asset_binding(response, "AAPL")
    _assert_no_generated_outputs(response)


def test_sec_stock_fixture_contract_normalizes_submissions_filings_xbrl_and_gaps():
    fixture = sec_stock_fixture_for_ticker("aapl")

    assert SEC_STOCK_FIXTURE_CONTRACT_VERSION == "sec-stock-fixture-adapter-v1"
    assert fixture is SEC_STOCK_FIXTURES["AAPL"]
    assert fixture.identity.ticker == "AAPL"
    assert fixture.identity.cik == "0000320193"
    assert fixture.identity.top500_manifest_member is True
    assert fixture.identity.eligible_not_cached is False
    assert {source.source_type for source in fixture.sources} == {
        "sec_submissions",
        "sec_filing",
        "sec_xbrl_company_facts",
    }
    assert fixture.selected_filings[0].form_type == "10-K"
    assert fixture.selected_filings[0].accession_or_fixture_id
    assert fixture.xbrl_company_facts[0].field_name == "net_sales_2024"
    assert fixture.xbrl_company_facts[0].unit == "USD"
    assert fixture.evidence_gaps[0].evidence_state is EvidenceState.unavailable


def test_sec_stock_fixture_contract_rejects_wrong_ticker_and_policy_blocked_sources(monkeypatch):
    adapter = mock_sec_stock_adapter()
    request = adapter.request("MSFT")
    licensing = fetch_mock_provider_response(ProviderKind.sec, "AAPL").licensing

    monkeypatch.setitem(SEC_STOCK_FIXTURES, "MSFT", SEC_STOCK_FIXTURES["AAPL"])
    with pytest.raises(SecStockFixtureContractError, match="requested ticker"):
        build_sec_stock_provider_response(adapter, request, licensing)

    rejected_decision = SourcePolicyDecision(
        decision=SourcePolicyDecisionState.rejected,
        source_id="rejected_sec_fixture",
        matched_by="domain",
        source_quality=SourceQuality.rejected,
        allowlist_status=SourceAllowlistStatus.rejected,
        source_use_policy=SourceUsePolicy.rejected,
        permitted_operations=DEFAULT_BLOCKED_SOURCE_OPERATIONS.model_copy(),
        allowed_excerpt=DEFAULT_BLOCKED_EXCERPT_BEHAVIOR.model_copy(),
        canonical_facts_allowed=False,
        reason="Test rejected source policy.",
    )
    monkeypatch.setattr(sec_stock_module, "resolve_source_policy", lambda url: rejected_decision)
    with pytest.raises(SecStockFixtureContractError, match="cannot support generated claims"):
        build_sec_stock_provider_response(adapter, adapter.request("AAPL"), licensing)


def test_sec_stock_fixture_contract_rejects_wrong_cik_and_wrong_source_binding(monkeypatch):
    adapter = mock_sec_stock_adapter()
    licensing = fetch_mock_provider_response(ProviderKind.sec, "AAPL").licensing
    fixture = SEC_STOCK_FIXTURES["AAPL"]

    wrong_cik = replace(fixture, identity=replace(fixture.identity, cik="0000000000"))
    monkeypatch.setitem(SEC_STOCK_FIXTURES, "AAPL", wrong_cik)
    with pytest.raises(SecStockFixtureContractError, match="CIK"):
        build_sec_stock_provider_response(adapter, adapter.request("AAPL"), licensing)

    wrong_source_fact = replace(fixture.xbrl_company_facts[0], source_document_id="provider_sec_msft_xbrl_2026")
    wrong_source = replace(fixture, xbrl_company_facts=(wrong_source_fact, *fixture.xbrl_company_facts[1:]))
    monkeypatch.setitem(SEC_STOCK_FIXTURES, "AAPL", wrong_source)
    with pytest.raises(SecStockFixtureContractError, match="invalid source evidence"):
        build_sec_stock_provider_response(adapter, adapter.request("AAPL"), licensing)


def test_etf_issuer_adapter_returns_voo_and_qqq_official_facts_and_holdings_metadata():
    adapter = mock_etf_issuer_adapter()

    for ticker, benchmark in [("VOO", "S&P 500 Index"), ("QQQ", "Nasdaq-100 Index")]:
        response = adapter.fetch(adapter.request(ticker))

        assert response.provider_kind is ProviderKind.etf_issuer
        assert response.state is ProviderResponseState.supported
        assert response.asset is not None
        assert response.asset.ticker == ticker
        assert response.licensing.export_allowed is True
        assert response.licensing.source_use_policy.value == "full_text_allowed"
        assert response.source_attributions
        assert all(source.is_official is True for source in response.source_attributions)
        assert all(source.source_quality.value == "issuer" for source in response.source_attributions)
        assert all(source.source_use_policy.value == "full_text_allowed" for source in response.source_attributions)
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
        assert response.licensing.source_use_policy.value == "metadata_only"
        assert response.source_attributions[0].source_use_policy.value == "metadata_only"
        assert response.source_attributions[0].permitted_operations.can_export_excerpt is False
        assert response.source_attributions[0].permitted_operations.can_support_citations is False
        assert "restricted provider data" in response.licensing.permission_note
        assert response.facts[0].fact_layer == "structured_reference"
        _assert_same_asset_binding(response, ticker)
        _assert_no_generated_outputs(response)

    for ticker in sorted(ELIGIBLE_NOT_CACHED_ASSETS):
        response = adapter.fetch(adapter.request(ticker, ProviderDataCategory.asset_resolution))
        assert response.state is ProviderResponseState.eligible_not_cached
        assert response.asset is not None
        assert response.asset.ticker == ticker
        assert response.asset.asset_type.value == ELIGIBLE_NOT_CACHED_ASSETS[ticker]["asset_type"]
        assert response.asset.name == ELIGIBLE_NOT_CACHED_ASSETS[ticker]["name"]
        assert response.asset.supported is True
        assert response.facts[0].value["eligible_not_cached"] is True
        assert response.facts[0].field_name == "asset_resolution"
        assert response.source_attributions[0].asset_ticker == ticker
        assert response.source_attributions[0].usage is ProviderSourceUsage.structured_reference
        assert response.source_attributions[0].is_official is False
        assert response.licensing.export_allowed is False
        assert response.licensing.redistribution_allowed is False
        assert response.generated_output.creates_generated_asset_page is False
        assert response.generated_output.creates_generated_chat_answer is False
        assert response.generated_output.creates_generated_comparison is False


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

    out_of_scope = market.fetch(market.request("GME"))
    assert out_of_scope.state is ProviderResponseState.out_of_scope
    assert out_of_scope.asset is not None
    assert out_of_scope.asset.ticker == "GME"
    assert out_of_scope.asset.supported is False
    assert out_of_scope.facts == []
    assert out_of_scope.source_attributions == []
    assert out_of_scope.errors[0].code == "recognized_common_stock_outside_top500_manifest"
    _assert_no_generated_outputs(out_of_scope)

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
    assert aapl.licensing.source_use_policy.value == "summary_allowed"
    assert aapl.source_attributions[0].source_use_policy.value == "summary_allowed"
    assert aapl.source_attributions[0].permitted_operations.can_support_canonical_facts is False
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
    sources = [
        (ROOT / "backend" / "providers.py").read_text(encoding="utf-8"),
        (ROOT / "backend" / "provider_adapters" / "sec_stock.py").read_text(encoding="utf-8"),
    ]
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
    for source in sources:
        for needle in forbidden:
            assert needle not in source
