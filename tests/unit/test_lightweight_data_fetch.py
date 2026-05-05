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
                            },
                            "timestamp": [1775073600, 1775682000, 1776286800, 1776891600, 1777496400, 1777665600],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [188.0, 191.5, 195.25, 201.0, 198.75, 199.5],
                                        "volume": [1000000, 1200000, 980000, 1400000, 1100000, 1300000],
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        if "quoteSummary/AAPL" in url:
            return _stock_quote_summary_payload("AAPL")
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
                            },
                            "timestamp": [1775073600, 1775682000, 1776286800, 1776891600, 1777496400, 1777665600],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [621.0, 635.2, 650.4, 668.1, 658.4, 662.52],
                                        "volume": [1000000, 1200000, 980000, 1400000, 1100000, 1300000],
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        if "quoteSummary/VOO" in url:
            return _etf_quote_summary_payload("VOO")
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
                            },
                            "timestamp": [1775073600, 1775682000, 1776286800, 1776891600, 1777496400, 1777665600],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [630.0, 645.5, 660.1, 676.4, 665.7, 670.01],
                                        "volume": [1000000, 1200000, 980000, 1400000, 1100000, 1300000],
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        if "quoteSummary/SPY" in url:
            return _etf_quote_summary_payload("SPY")
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


def _stock_quote_summary_payload(ticker: str) -> dict[str, Any]:
    return {
        "quoteSummary": {
            "result": [
                {
                    "price": {
                        "symbol": ticker,
                        "longName": "Apple Inc.",
                        "currency": "USD",
                        "marketCap": _yahoo_money(3_120_000_000_000),
                    },
                    "summaryProfile": {
                        "sector": "Technology",
                        "industry": "Consumer Electronics",
                        "companyOfficers": [{"name": "Tim Cook", "title": "Chief Executive Officer"}],
                    },
                    "summaryDetail": {
                        "trailingPE": _yahoo_number(31.4),
                        "forwardPE": _yahoo_number(27.8),
                        "dividendYield": _yahoo_percent(0.0045),
                        "52WeekChange": _yahoo_percent(0.112),
                    },
                    "defaultKeyStatistics": {
                        "enterpriseValue": _yahoo_money(3_180_000_000_000),
                        "trailingEps": _yahoo_number(6.43),
                        "forwardEps": _yahoo_number(7.18),
                        "priceToBook": _yahoo_number(43.5),
                        "enterpriseToEbitda": _yahoo_number(24.2),
                        "heldPercentInstitutions": _yahoo_percent(0.62),
                    },
                    "financialData": {
                        "totalRevenue": _yahoo_money(391_000_000_000),
                        "grossProfits": _yahoo_money(181_000_000_000),
                        "revenueGrowth": _yahoo_percent(0.06),
                        "totalCash": _yahoo_money(65_000_000_000),
                        "totalDebt": _yahoo_money(95_000_000_000),
                        "currentRatio": _yahoo_number(0.9),
                        "operatingCashflow": _yahoo_money(118_000_000_000),
                        "freeCashflow": _yahoo_money(105_000_000_000),
                        "grossMargins": _yahoo_percent(0.46),
                        "operatingMargins": _yahoo_percent(0.31),
                        "profitMargins": _yahoo_percent(0.24),
                        "returnOnAssets": _yahoo_percent(0.22),
                        "returnOnEquity": _yahoo_percent(1.36),
                    },
                }
            ]
        }
    }


def _etf_quote_summary_payload(ticker: str) -> dict[str, Any]:
    return {
        "quoteSummary": {
            "result": [
                {
                    "price": {"symbol": ticker, "longName": "Vanguard S&P 500 ETF", "currency": "USD"},
                    "fundProfile": {
                        "categoryName": "Large Blend",
                        "family": "Vanguard",
                        "legalType": "Exchange Traded Fund",
                    },
                    "summaryDetail": {
                        "totalAssets": _yahoo_money(1_420_000_000_000),
                        "yield": _yahoo_percent(0.0119),
                        "ytdReturn": _yahoo_percent(0.0598),
                    },
                    "topHoldings": {
                        "holdings": [
                            {"symbol": symbol, "holdingName": name, "holdingPercent": _yahoo_percent(weight / 100)}
                            for symbol, name, weight in [
                                ("NVDA", "NVIDIA Corporation", 7.58),
                                ("AAPL", "Apple Inc.", 6.67),
                                ("MSFT", "Microsoft Corporation", 4.92),
                                ("AMZN", "Amazon.com, Inc.", 3.64),
                                ("GOOGL", "Alphabet Inc.", 3.00),
                                ("AVGO", "Broadcom Inc.", 2.63),
                                ("GOOG", "Alphabet Inc.", 2.40),
                                ("META", "Meta Platforms, Inc.", 2.24),
                                ("TSLA", "Tesla, Inc.", 1.87),
                                ("BRK-B", "Berkshire Hathaway Inc.", 1.57),
                            ]
                        ],
                        "sectorWeightings": [
                            {"technology": _yahoo_percent(0.3362)},
                            {"financial_services": _yahoo_percent(0.1221)},
                            {"communication_services": _yahoo_percent(0.1050)},
                            {"consumer_cyclical": _yahoo_percent(0.1002)},
                            {"healthcare": _yahoo_percent(0.0948)},
                            {"industrials": _yahoo_percent(0.0848)},
                        ],
                    },
                    "fundPerformance": {
                        "trailingReturns": {
                            "asOfDate": {"raw": 1777584000, "fmt": "2026-05-01"},
                            "ytd": _yahoo_percent(0.0598),
                            "oneYear": _yahoo_percent(0.1777),
                            "threeYear": _yahoo_percent(0.1828),
                            "fiveYear": _yahoo_percent(0.1202),
                        },
                        "annualTotalReturns": {
                            "returns": [
                                {"year": "2025", "annualValue": _yahoo_percent(0.1782)},
                                {"year": "2024", "annualValue": _yahoo_percent(0.2498)},
                                {"year": "2023", "annualValue": _yahoo_percent(0.2632)},
                            ]
                        },
                    },
                }
            ]
        }
    }


def _yahoo_number(value: float | int) -> dict[str, Any]:
    return {"raw": value, "fmt": f"{value:,.2f}".rstrip("0").rstrip(".")}


def _yahoo_money(value: int) -> dict[str, Any]:
    return {"raw": value, "fmt": f"{value:,}"}


def _yahoo_percent(value: float) -> dict[str, Any]:
    return {"raw": value, "fmt": f"{value * 100:.2f}%"}


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
    assert fields["provider_profile_overview"].value["sector"] == "Technology"
    assert fields["provider_stock_metric_groups"].value["groups"]
    assert len(fields["provider_price_chart"].value["points"]) >= 6
    assert response.diagnostics["official_source_count"] == 3
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.schema_version == "lightweight-api-fallback-diagnostics-v1"
    assert response.fallback_diagnostics.source_path == "sec_official_provider_fallback"
    assert response.fallback_diagnostics.generated_output_eligible is True
    assert response.fallback_diagnostics.official_source_count == 3
    assert response.fallback_diagnostics.provider_fallback_source_count == 1
    assert response.fallback_diagnostics.raw_payload_exposed is False
    assert response.fallback_diagnostics.secret_values_exposed is False
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
    assert len(fields["provider_top_holdings"].value) == 10
    assert fields["provider_top_holdings"].value[0]["symbol"] == "NVDA"
    assert fields["provider_sector_weightings"].value[0]["sector"] == "Technology"
    assert fields["provider_fund_performance"].value["trailing_returns"]
    assert len(fields["provider_price_chart"].value["points"]) >= 6
    assert response.freshness.holdings_as_of == "2026-04-01"
    assert response.diagnostics["issuer_enrichment_state"] == "supported"
    assert response.diagnostics["official_source_count"] == 4
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.source_path == "issuer_backed_etf_provider_fallback"
    assert response.fallback_diagnostics.issuer_evidence_state == "supported"
    assert response.fallback_diagnostics.official_source_count == 4
    assert response.fallback_diagnostics.provider_fallback_source_count == 1
    assert response.fallback_diagnostics.gap_count == 1
    assert {gap.field_name for gap in response.gaps} == {"premium_discount_or_spread"}


def test_lightweight_spy_issuer_fixture_returns_supported_with_explicit_remaining_gap():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("SPY", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

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
    assert fields["etf_identity"].value["issuer"] == "State Street Global Advisors"
    assert fields["etf_identity"].value["eligible_not_cached"] is True
    assert fields["etf_fact_sheet_metadata"].value["benchmark"] == "S&P 500 Index"
    assert fields["benchmark"].value == "S&P 500 Index"
    assert fields["expense_ratio"].value == 0.0945
    assert fields["holdings_count"].value == 503
    assert fields["top_holding_nvidia"].value["holding_ticker"] == "NVDA"
    assert fields["information_technology_exposure"].value["exposure_category"] == "sector"
    assert fields["etf_manifest_scope_signal"].value["support_state"] == "eligible_not_cached"
    assert fields["provider_identity_or_market_reference"].value["instrumentType"] == "ETF"
    assert fields["provider_market_price"].value["regularMarketPrice"] == 670.01
    assert response.freshness.holdings_as_of == "2026-04-01"
    assert response.diagnostics["issuer_enrichment_state"] == "supported"
    assert response.diagnostics["official_source_count"] == 4
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.source_path == "issuer_backed_etf_provider_fallback"
    assert response.fallback_diagnostics.fetch_state is LightweightFetchState.supported
    assert response.fallback_diagnostics.issuer_evidence_state == "supported"
    assert response.fallback_diagnostics.official_source_count == 4
    assert response.fallback_diagnostics.partial_source_count == 1
    assert response.fallback_diagnostics.provider_fallback_source_count == 1
    assert response.fallback_diagnostics.gap_count == 1
    assert "partial_or_unavailable_evidence_gaps" in response.fallback_diagnostics.reason_codes
    assert {gap.field_name for gap in response.gaps} == {"premium_discount_or_spread"}


def test_lightweight_fetch_blocks_manifest_unsupported_etf_without_provider_calls():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("ARKK", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert response.fetch_state is LightweightFetchState.unsupported
    assert response.generated_output_eligible is False
    assert response.page_render_state is EvidenceState.unsupported
    assert response.sources == []
    assert fetcher.urls == []
    assert response.diagnostics["blocked_generated_output"] is True
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.source_path == "blocked_scope_screen"
    assert response.fallback_diagnostics.generated_output_eligible is False
    assert response.fallback_diagnostics.source_count == 0
    assert response.fallback_diagnostics.raw_payload_exposed is False


def test_lightweight_fetch_disabled_returns_unavailable_without_live_calls():
    settings = build_lightweight_data_settings({"DATA_POLICY_MODE": "lightweight"})

    response = fetch_lightweight_asset_data("AAPL", settings=settings, retrieved_at=RETRIEVED_AT)

    assert response.fetch_state is LightweightFetchState.unavailable
    assert response.generated_output_eligible is False
    assert response.no_live_external_calls is True
    assert response.diagnostics["reason_code"] == "lightweight_live_fetch_disabled"
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.source_path == "lightweight_fetch_unavailable"
    assert response.fallback_diagnostics.reason_codes == [
        "fetch_state_unavailable",
        "generated_output_blocked",
        "lightweight_live_fetch_disabled",
        "page_render_state_unavailable",
        "partial_or_unavailable_evidence_gaps",
        "raw_payload_hidden",
    ]


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
    sections = {section.section_id: section for section in overview.sections}
    assert {
        "business_overview",
        "products_services",
        "strengths",
        "financial_quality",
        "valuation_context",
        "provider_price_performance",
        "provider_income_statement",
        "provider_balance_sheet",
        "provider_cash_flow",
        "provider_margins_returns_ownership",
        "price_chart",
        "top_risks",
        "market_reference",
        "educational_suitability",
    } <= set(sections)
    assert sections["products_services"].evidence_state is EvidenceState.mixed
    assert sections["financial_quality"].evidence_state is EvidenceState.mixed
    assert sections["valuation_context"].evidence_state is EvidenceState.mixed
    assert sections["business_overview"].table is not None
    assert sections["business_overview"].table.table_id == "stock_profile_snapshot"
    assert sections["financial_quality"].table is not None
    assert sections["valuation_context"].table is not None
    assert sections["price_chart"].chart is not None
    assert len(sections["price_chart"].chart.points) >= 6
    assert sections["top_risks"].items[0].citation_ids
    assert {metric.metric_id for metric in sections["financial_quality"].metrics} == {
        "latest_revenue_fact",
        "latest_net_income_fact",
        "latest_assets_fact",
    }
    assert overview.weekly_news_focus is not None
    assert overview.weekly_news_focus.selected_item_count == 0
    assert overview.ai_comprehensive_analysis is not None
    assert overview.ai_comprehensive_analysis.analysis_available is False
    assert details.facts["business_model"]
    assert details.facts["products_services_context"]
    assert details.facts["financial_quality_context"]
    assert details.facts["valuation_context"]
    assert details.facts["risk_context"]
    assert details.facts["provider_market_price"].value == 199.5
    assert sources.drawer_state is SourceDrawerState.available
    assert sources.source_groups
    assert sources.citation_bindings
    assert sources.related_claims
    assert sources.diagnostics.generated_output_created is True
    assert overview.fallback_diagnostics is not None
    assert overview.fallback_diagnostics.source_path == "sec_official_provider_fallback"
    assert details.fallback_diagnostics == overview.fallback_diagnostics
    assert sources.fallback_diagnostics == overview.fallback_diagnostics


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
    assert {
        "fund_objective_role",
        "holdings_exposure",
        "sector_weightings",
        "performance",
        "price_chart",
        "construction_methodology",
        "cost_trading_context",
        "etf_specific_risks",
        "similar_assets_alternatives",
        "educational_suitability",
        "lightweight_evidence_gaps",
    } <= set(sections)
    assert sections["fund_objective_role"].evidence_state is EvidenceState.supported
    assert sections["holdings_exposure"].evidence_state is EvidenceState.supported
    assert sections["fund_objective_role"].table is not None
    assert sections["fund_objective_role"].table.table_id == "etf_overview"
    assert sections["holdings_exposure"].table is not None
    assert sections["holdings_exposure"].table.table_id == "top_holdings"
    assert len(sections["holdings_exposure"].table.rows) == 10
    assert sections["holdings_exposure"].table.rows[0].values["symbol"] == "NVDA"
    aapl_holding = next(row for row in sections["holdings_exposure"].table.rows if row.values["symbol"] == "AAPL")
    assert aapl_holding.values["weight"] == 7.0
    assert aapl_holding.evidence_state is EvidenceState.supported
    assert sections["sector_weightings"].table is not None
    assert sections["sector_weightings"].table.rows[0].values["sector"] == "Technology"
    assert sections["performance"].table is not None
    assert sections["price_chart"].chart is not None
    assert len(sections["price_chart"].chart.points) >= 6
    assert sections["construction_methodology"].evidence_state is EvidenceState.mixed
    assert sections["cost_trading_context"].evidence_state is EvidenceState.mixed
    assert sections["etf_specific_risks"].items[0].citation_ids
    assert {metric.metric_id for metric in sections["cost_trading_context"].metrics} == {
        "expense_ratio",
        "provider_market_price",
    }
    assert details.facts["role"]
    assert details.facts["holdings"]
    assert details.facts["construction_methodology"]
    assert details.facts["benchmark"].value == "S&P 500 Index"
    assert details.facts["cost_context"].value == 0.03
    assert details.facts["prospectus_reference"].value == "summary_prospectus published 2026-04-01"
    assert details.facts["risk_context"]
    assert details.facts["comparison_overlap_context"]


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
    assert result["status_counts"] == {"pass": 8, "partial": 0, "blocked": 4, "unavailable": 0}
    assert result["issuer_backed_etf_tickers"] == ["VOO", "QQQ", "SPY", "VTI", "XLK"]
    assert result["partial_etf_tickers"] == []
    assert result["partial_etf_coverage_reason"] == "no_partial_etf_rows_in_current_slice"
    comparison_summary = result["comparison_export_parity_summary"]
    assert {
        (pair["left_ticker"], pair["right_ticker"], pair["comparison_type"])
        for pair in comparison_summary["representative_comparison_pairs"]
    } == {
        ("VOO", "QQQ", "etf_vs_etf"),
        ("AAPL", "VOO", "stock_vs_etf"),
        ("AAPL", "MSFT", "stock_vs_stock"),
    }
    assert {
        (case["left_ticker"], case["right_ticker"], case["expected_state"])
        for case in comparison_summary["unavailable_or_blocked_comparison_cases"]
    } == {
        ("VOO", "SPY", "eligible_not_cached"),
        ("SPY", "VTI", "eligible_not_cached"),
        ("VOO", "TQQQ", "unsupported"),
        ("AAPL", "TQQQ", "unsupported"),
    }
    assert comparison_summary["partial_etf_pair_coverage"]["reason_code"] == "no_partial_etf_rows_in_current_slice"

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
        fallback_diagnostics = row["fallback_diagnostics"]
        assert fallback_diagnostics["schema_version"] == "lightweight-api-fallback-diagnostics-v1"
        assert fallback_diagnostics["source_path"] == "sec_official_provider_fallback"
        assert fallback_diagnostics["source_count"] == row["source_count"]
        assert fallback_diagnostics["raw_payload_exposed"] is False
        assert fallback_diagnostics["secret_values_exposed"] is False
        surface = row["surface_contract"]
        assert surface["renderable"] is True
        assert surface["generated_page"] is True
        assert surface["source_drawer_state"] == "available"
        assert {"business_model", "provider_market_price"} <= set(surface["detail_fact_keys"])
        assert surface["unavailable_detail_fact_keys"] == []
        assert surface["section_states"]["business_overview"]["evidence_state"] == "supported"
        assert surface["section_states"]["products_services"]["evidence_state"] == "mixed"
        assert surface["section_states"]["financial_quality"]["evidence_state"] == "mixed"
        assert surface["section_states"]["valuation_context"]["evidence_state"] == "mixed"
        assert surface["section_states"]["top_risks"]["evidence_state"] == "supported"

    for ticker in ("VOO", "QQQ", "SPY", "VTI", "XLK"):
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
        fallback_diagnostics = row["fallback_diagnostics"]
        assert fallback_diagnostics["source_path"] == "issuer_backed_etf_provider_fallback"
        assert fallback_diagnostics["issuer_evidence_state"] == "supported"
        assert fallback_diagnostics["official_source_count"] == row["official_source_count"]
        surface = row["surface_contract"]
        assert surface["renderable"] is True
        assert surface["source_drawer_state"] == "available"
        assert {"role", "holdings", "cost_context", "manifest_scope_signal", "provider_market_price"} <= set(
            surface["detail_fact_keys"]
        )
        assert surface["unavailable_detail_fact_keys"] == []
        assert surface["section_states"]["fund_objective_role"]["evidence_state"] == "supported"
        assert surface["section_states"]["holdings_exposure"]["evidence_state"] == "supported"
        assert surface["section_states"]["construction_methodology"]["evidence_state"] == "mixed"
        assert surface["section_states"]["cost_trading_context"]["evidence_state"] == "mixed"
        assert surface["section_states"]["etf_specific_risks"]["evidence_state"] == "supported"
        assert surface["section_states"]["similar_assets_alternatives"]["evidence_state"] == "insufficient_evidence"

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
        fallback_diagnostics = row["fallback_diagnostics"]
        assert fallback_diagnostics["source_path"] == "blocked_scope_screen"
        assert fallback_diagnostics["generated_output_eligible"] is False
        assert fallback_diagnostics["source_count"] == 0
        assert fallback_diagnostics["raw_payload_exposed"] is False
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
    assert result.results[0].fallback_diagnostics is not None
    assert result.results[0].fallback_diagnostics.schema_version == "lightweight-api-fallback-diagnostics-v1"
    assert result.results[0].fallback_diagnostics.source_path == "sec_official_provider_fallback"
    assert result.results[0].fallback_diagnostics.raw_payload_exposed is False
