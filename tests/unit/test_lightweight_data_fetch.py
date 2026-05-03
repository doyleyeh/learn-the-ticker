from __future__ import annotations

from typing import Any

from backend.lightweight_data_fetch import fetch_lightweight_asset_data
from backend.lightweight_page import (
    build_lightweight_details_response,
    build_lightweight_overview_response,
    build_lightweight_sources_response,
)
from backend.models import (
    AssetStatus,
    AssetType,
    EvidenceState,
    LightweightFetchState,
    LightweightSourceLabel,
    SearchResponseStatus,
    SourceDrawerState,
)
from backend.search import search_assets
from backend.settings import build_lightweight_data_settings
from scripts.run_local_fresh_data_slice_smoke import run_slice_smoke


RETRIEVED_AT = "2026-05-02T12:00:00Z"


class FakeJsonFetcher:
    no_live_external_calls = True

    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        self.urls.append(url)
        if "company_tickers_exchange" in url:
            return {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [[320193, "Apple Inc.", "AAPL", "Nasdaq"]],
            }
        if "submissions/CIK0000320193" in url:
            return {
                "filings": {
                    "recent": {
                        "form": ["10-Q", "10-K"],
                        "filingDate": ["2026-04-30", "2025-10-31"],
                        "reportDate": ["2026-03-28", "2025-09-27"],
                        "accessionNumber": ["0000320193-26-000001", "0000320193-25-000111"],
                    }
                }
            }
        if "companyfacts/CIK0000320193" in url:
            return {
                "facts": {
                    "us-gaap": {
                        "RevenueFromContractWithCustomerExcludingAssessedTax": {
                            "label": "Revenue",
                            "units": {
                                "USD": [
                                    {
                                        "val": 391000000000,
                                        "fy": 2025,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2025-10-31",
                                        "end": "2025-09-27",
                                    }
                                ]
                            },
                        },
                        "NetIncomeLoss": {
                            "label": "Net income",
                            "units": {
                                "USD": [
                                    {
                                        "val": 93000000000,
                                        "fy": 2025,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2025-10-31",
                                        "end": "2025-09-27",
                                    }
                                ]
                            },
                        },
                        "Assets": {
                            "label": "Assets",
                            "units": {
                                "USD": [
                                    {
                                        "val": 350000000000,
                                        "fy": 2025,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2025-10-31",
                                        "end": "2025-09-27",
                                    }
                                ]
                            },
                        },
                    }
                }
            }
        if "finance/search?q=AAPL" in url:
            return {
                "quotes": [
                    {
                        "symbol": "AAPL",
                        "quoteType": "EQUITY",
                        "shortname": "Apple Inc.",
                        "longname": "Apple Inc.",
                        "exchange": "NMS",
                    }
                ]
            }
        if "finance/chart/AAPL" in url:
            return {
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "symbol": "AAPL",
                                "instrumentType": "EQUITY",
                                "regularMarketPrice": 199.5,
                                "regularMarketTime": 1777665600,
                                "currency": "USD",
                                "fullExchangeName": "NasdaqGS",
                            }
                        }
                    ]
                }
            }
        if "finance/search?q=VOO" in url:
            return {
                "quotes": [
                    {
                        "symbol": "VOO",
                        "quoteType": "ETF",
                        "shortname": "Vanguard S&P 500 ETF",
                        "longname": "Vanguard S&P 500 ETF",
                        "exchange": "PCX",
                    }
                ]
            }
        if "finance/chart/VOO" in url:
            return {
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "symbol": "VOO",
                                "instrumentType": "ETF",
                                "regularMarketPrice": 662.52,
                                "regularMarketTime": 1777665600,
                                "currency": "USD",
                                "fullExchangeName": "NYSEArca",
                            }
                        }
                    ]
                }
            }
        if "finance/search?q=SPY" in url:
            return {
                "quotes": [
                    {
                        "symbol": "SPY",
                        "quoteType": "ETF",
                        "shortname": "SPDR S&P 500 ETF Trust",
                        "longname": "SPDR S&P 500 ETF Trust",
                        "exchange": "PCX",
                    }
                ]
            }
        if "finance/chart/SPY" in url:
            return {
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "symbol": "SPY",
                                "instrumentType": "ETF",
                                "regularMarketPrice": 670.01,
                                "regularMarketTime": 1777665600,
                                "currency": "USD",
                                "fullExchangeName": "NYSEArca",
                            }
                        }
                    ]
                }
            }
        raise AssertionError(f"Unexpected URL: {url}")


def _settings():
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def test_lightweight_stock_fetch_prefers_sec_and_labels_provider_fallback():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("AAPL", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert response.schema_version == "lightweight-asset-fetch-v1"
    assert response.fetch_state is LightweightFetchState.supported
    assert response.page_render_state is EvidenceState.supported
    assert response.asset.asset_type is AssetType.stock
    assert response.asset.name == "Apple Inc."
    assert response.generated_output_eligible is True
    assert response.no_live_external_calls is True
    assert response.raw_payload_exposed is False
    assert {source.source_label for source in response.sources} >= {
        LightweightSourceLabel.official,
        LightweightSourceLabel.provider_derived,
    }
    fields = {fact.field_name: fact for fact in response.facts}
    assert fields["sec_identity"].value["cik"] == "0000320193"
    assert fields["latest_sec_filing"].value["form_type"] == "10-K"
    assert fields["latest_revenue_fact"].source_labels == [LightweightSourceLabel.official]
    assert fields["latest_net_income_fact"].value["value"] == 93000000000
    assert fields["latest_assets_fact"].value["value"] == 350000000000
    assert fields["provider_identity_or_market_reference"].fallback_used is True
    assert fields["provider_market_price"].value["regularMarketPrice"] == 199.5
    assert response.diagnostics["official_source_count"] == 3
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert all("raw" not in fact.field_name for fact in response.facts)


def test_lightweight_etf_fetch_uses_issuer_fixtures_before_manifest_and_provider_fallback():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("VOO", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert response.fetch_state is LightweightFetchState.supported
    assert response.page_render_state is EvidenceState.supported
    assert response.asset.asset_type is AssetType.etf
    assert response.generated_output_eligible is True
    assert response.no_live_external_calls is True
    assert {source.source_label for source in response.sources} == {
        LightweightSourceLabel.official,
        LightweightSourceLabel.partial,
        LightweightSourceLabel.provider_derived,
    }
    fields = {fact.field_name: fact for fact in response.facts}
    assert fields["etf_identity"].value["issuer"] == "Vanguard"
    assert fields["etf_fact_sheet_metadata"].value["benchmark"] == "S&P 500 Index"
    assert fields["benchmark"].value == "S&P 500 Index"
    assert fields["expense_ratio"].value == 0.03
    assert fields["holdings_count"].value == 500
    assert fields["top_holding_apple"].value["name"] == "Apple Inc."
    assert fields["equity_exposure"].value["exposure_category"] == "asset_class"
    assert fields["etf_manifest_scope_signal"].value["support_state"] == "cached_supported"
    assert fields["provider_identity_or_market_reference"].value["instrumentType"] == "ETF"
    assert fields["provider_market_price"].value["regularMarketPrice"] == 662.52
    assert response.freshness.holdings_as_of == "2026-04-01"
    assert response.diagnostics["issuer_enrichment_state"] == "supported"
    assert response.diagnostics["official_source_count"] == 4
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert {gap.field_name for gap in response.gaps} == {"premium_discount_or_spread"}


def test_lightweight_etf_without_issuer_fixture_stays_partial_with_explicit_gap():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("SPY", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert response.fetch_state is LightweightFetchState.partial
    assert response.page_render_state is EvidenceState.partial
    assert response.asset.asset_type is AssetType.etf
    assert response.generated_output_eligible is True
    assert response.no_live_external_calls is True
    assert {source.source_label for source in response.sources} == {
        LightweightSourceLabel.partial,
        LightweightSourceLabel.provider_derived,
    }
    fields = {fact.field_name: fact for fact in response.facts}
    assert fields["etf_manifest_scope_signal"].value["support_state"] == "eligible_not_cached"
    assert fields["provider_identity_or_market_reference"].value["instrumentType"] == "ETF"
    assert fields["provider_market_price"].value["regularMarketPrice"] == 670.01
    assert response.diagnostics["issuer_enrichment_state"] == "eligible_not_cached"
    assert response.diagnostics["official_source_count"] == 0
    assert {gap.field_name for gap in response.gaps} == {"etf_issuer_evidence"}


def test_lightweight_fetch_blocks_manifest_unsupported_etf_without_provider_calls():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("ARKK", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert response.fetch_state is LightweightFetchState.unsupported
    assert response.generated_output_eligible is False
    assert response.page_render_state is EvidenceState.unsupported
    assert response.sources == []
    assert fetcher.urls == []
    assert response.diagnostics["blocked_generated_output"] is True


def test_lightweight_fetch_disabled_returns_unavailable_without_live_calls():
    settings = build_lightweight_data_settings({"DATA_POLICY_MODE": "lightweight"})

    response = fetch_lightweight_asset_data("AAPL", settings=settings, retrieved_at=RETRIEVED_AT)

    assert response.fetch_state is LightweightFetchState.unavailable
    assert response.generated_output_eligible is False
    assert response.no_live_external_calls is True
    assert response.diagnostics["reason_code"] == "lightweight_live_fetch_disabled"


def test_lightweight_stock_fetch_builds_overview_details_and_source_drawer_contracts():
    response = fetch_lightweight_asset_data(
        "AAPL",
        settings=_settings(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )

    overview = build_lightweight_overview_response(response)
    details = build_lightweight_details_response(response)
    sources = build_lightweight_sources_response(response)

    assert overview.asset.ticker == "AAPL"
    assert overview.state.status is AssetStatus.supported
    assert overview.beginner_summary is not None
    assert "SEC" in overview.beginner_summary.what_it_is
    assert len(overview.top_risks) == 3
    assert overview.source_documents
    assert overview.citations
    assert {section.section_id for section in overview.sections} >= {"business_overview", "market_reference"}
    assert overview.weekly_news_focus is not None
    assert overview.weekly_news_focus.selected_item_count == 0
    assert overview.ai_comprehensive_analysis is not None
    assert overview.ai_comprehensive_analysis.analysis_available is False
    assert details.facts["business_model"]
    assert details.facts["provider_market_price"].value == 199.5
    assert sources.drawer_state is SourceDrawerState.available
    assert sources.source_groups
    assert sources.citation_bindings
    assert sources.related_claims
    assert sources.diagnostics.generated_output_created is True


def test_lightweight_issuer_backed_etf_fetch_builds_supported_page_contracts():
    response = fetch_lightweight_asset_data(
        "VOO",
        settings=_settings(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )

    overview = build_lightweight_overview_response(response)
    details = build_lightweight_details_response(response)

    assert overview.asset.asset_type is AssetType.etf
    assert overview.state.status is AssetStatus.supported
    assert overview.beginner_summary is not None
    assert "ETF" in overview.beginner_summary.what_it_is
    sections = {section.section_id: section for section in overview.sections}
    assert sections["fund_objective_role"].evidence_state is EvidenceState.supported
    assert sections["holdings_exposure"].evidence_state is EvidenceState.supported
    assert sections["cost_trading_context"].evidence_state is EvidenceState.partial
    assert details.facts["role"]
    assert details.facts["holdings"]
    assert details.facts["benchmark"].value == "S&P 500 Index"
    assert details.facts["cost_context"].value == 0.03
    assert details.facts["prospectus_reference"].value == "summary_prospectus published 2026-04-01"


def test_local_fresh_data_mvp_slice_smoke_contract_is_deterministic():
    result = run_slice_smoke()

    assert result["schema_version"] == "local-fresh-data-mvp-slice-smoke-v1"
    assert result["status"] == "pass"
    assert result["normal_ci_requires_live_calls"] is False
    assert result["browser_startup_required"] is False
    assert result["local_services_required"] is False
    assert result["secret_values_reported"] is False
    assert result["raw_payload_values_reported"] is False
    assert result["raw_payload_exposed_count"] == 0
    assert result["supported_renderable_tickers"] == ["AAPL", "MSFT", "NVDA", "VOO", "SPY", "VTI", "QQQ", "XLK"]
    assert result["blocked_regression_tickers"] == ["TQQQ", "ARKK", "BND", "GLD"]
    assert set(result["status_definitions"]) == {"pass", "partial", "blocked", "unavailable"}
    assert result["status_counts"] == {"pass": 5, "partial": 3, "blocked": 4, "unavailable": 0}
    assert result["issuer_backed_etf_tickers"] == ["VOO", "QQQ"]
    assert result["partial_etf_tickers"] == ["SPY", "VTI", "XLK"]

    rows = {row["ticker"]: row for row in result["rows"]}
    for ticker in ("AAPL", "MSFT", "NVDA"):
        row = rows[ticker]
        assert row["status"] == "pass"
        assert row["asset_type"] == "stock"
        assert row["fetch_state"] == "supported"
        assert row["page_render_state"] == "supported"
        assert row["generated_output_eligible"] is True
        assert row["source_count"] >= 4
        assert row["citation_count"] > 0
        assert row["fact_count"] > 0
        assert row["freshness"]["facts_as_of"] == "2025-10-31"
        assert row["raw_payload_exposed"] is False
        assert row["no_live_external_calls"] is True
        assert set(row["source_labels"]) == {"official", "provider_derived"}
        surface = row["surface_contract"]
        assert surface["renderable"] is True
        assert surface["generated_page"] is True
        assert surface["source_drawer_state"] == "available"
        assert {"business_model", "provider_market_price"} <= set(surface["detail_fact_keys"])
        assert surface["unavailable_detail_fact_keys"] == []
        assert surface["section_states"]["business_overview"]["evidence_state"] == "supported"

    for ticker in ("VOO", "QQQ"):
        row = rows[ticker]
        assert row["status"] == "pass"
        assert row["asset_type"] == "etf"
        assert row["fetch_state"] == "supported"
        assert row["page_render_state"] == "supported"
        assert row["generated_output_eligible"] is True
        assert row["issuer_backed"] is True
        assert row["issuer_evidence_state"] == "supported"
        assert row["official_source_count"] == 4
        assert row["provider_fallback_source_count"] == 1
        assert row["freshness"]["holdings_as_of"] == "2026-04-01"
        assert row["raw_payload_exposed"] is False
        assert row["no_live_external_calls"] is True
        assert set(row["source_labels"]) == {"official", "partial", "provider_derived"}
        surface = row["surface_contract"]
        assert surface["renderable"] is True
        assert surface["source_drawer_state"] == "available"
        assert {"role", "holdings", "cost_context", "manifest_scope_signal", "provider_market_price"} <= set(
            surface["detail_fact_keys"]
        )
        assert surface["unavailable_detail_fact_keys"] == []
        assert surface["section_states"]["fund_objective_role"]["evidence_state"] == "supported"
        assert surface["section_states"]["holdings_exposure"]["evidence_state"] == "supported"
        assert surface["section_states"]["cost_trading_context"]["evidence_state"] == "partial"

    for ticker in ("SPY", "VTI", "XLK"):
        row = rows[ticker]
        assert row["status"] == "partial"
        assert row["asset_type"] == "etf"
        assert row["fetch_state"] == "partial"
        assert row["page_render_state"] == "partial"
        assert row["generated_output_eligible"] is True
        assert row["issuer_backed"] is False
        assert row["issuer_evidence_state"] == "partial"
        assert row["freshness"]["holdings_as_of"] == "2026-05-01"
        assert row["raw_payload_exposed"] is False
        assert row["no_live_external_calls"] is True
        assert row["source_labels"] == ["partial", "provider_derived"]
        surface = row["surface_contract"]
        assert surface["renderable"] is True
        assert surface["source_drawer_state"] == "available"
        assert {"role", "holdings", "cost_context", "manifest_scope_signal", "provider_market_price"} <= set(
            surface["detail_fact_keys"]
        )
        assert surface["unavailable_detail_fact_keys"] == ["benchmark", "cost_context", "prospectus_reference"]
        assert {"cost_trading_context", "fund_objective_role", "holdings_exposure"} <= set(
            surface["partial_section_ids"]
        )
        assert surface["section_states"]["holdings_exposure"]["evidence_state"] == "partial"
        assert surface["section_states"]["cost_trading_context"]["evidence_state"] == "partial"

    for ticker in ("TQQQ", "ARKK", "BND", "GLD"):
        row = rows[ticker]
        assert row["status"] == "blocked"
        assert row["asset_type"] == "unsupported"
        assert row["expected_recognition_type"] == "etf_or_etp"
        assert row["fetch_state"] == "unsupported"
        assert row["generated_output_eligible"] is False
        assert row["source_count"] == 0
        assert row["citation_count"] == 0
        assert row["fact_count"] == 0
        assert row["fetch_call_count"] == 0
        assert row["raw_payload_exposed"] is False
        assert row["no_live_external_calls"] is True
        assert row["blocked_generated_surfaces"] == result["blocked_generated_surfaces"]
        assert row["surface_contract"] == {
            "renderable": False,
            "generated_page": False,
            "generated_chat_answer": False,
            "generated_comparison": False,
            "weekly_news_focus": False,
            "ai_comprehensive_analysis": False,
            "export": False,
            "generated_risk_summary": False,
            "source_drawer_state": "unavailable",
            "overview_state": "unsupported",
        }


def test_live_lightweight_search_can_open_exact_eligible_not_cached_asset(monkeypatch):
    response = fetch_lightweight_asset_data(
        "AAPL",
        settings=_settings(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )
    msft_response = response.model_copy(
        update={
            "ticker": "MSFT",
            "asset": response.asset.model_copy(update={"ticker": "MSFT", "name": "Microsoft Corporation"}),
        }
    )

    monkeypatch.setenv("DATA_POLICY_MODE", "lightweight")
    monkeypatch.setenv("LIGHTWEIGHT_LIVE_FETCH_ENABLED", "true")
    monkeypatch.setenv("LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED", "true")
    monkeypatch.setattr("backend.search.fetch_lightweight_asset_data", lambda ticker, settings: msft_response)

    result = search_assets("MSFT")

    assert result.state.status is SearchResponseStatus.supported
    assert result.results[0].ticker == "MSFT"
    assert result.results[0].can_open_generated_page is True
    assert result.results[0].generated_route == "/assets/MSFT"
