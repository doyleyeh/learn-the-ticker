from __future__ import annotations

from typing import Any

from backend.lightweight_data_fetch import fetch_lightweight_asset_data
from backend.models import (
    AssetType,
    EvidenceState,
    LightweightFetchState,
    LightweightSourceLabel,
)
from backend.settings import build_lightweight_data_settings


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
                        }
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
    assert fields["provider_identity_or_market_reference"].fallback_used is True
    assert response.diagnostics["official_source_count"] == 3
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert all("raw" not in fact.field_name for fact in response.facts)


def test_lightweight_etf_fetch_uses_manifest_scope_signal_and_provider_fallback():
    fetcher = FakeJsonFetcher()

    response = fetch_lightweight_asset_data("VOO", settings=_settings(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)

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
    assert fields["etf_manifest_scope_signal"].value["support_state"] == "cached_supported"
    assert fields["provider_identity_or_market_reference"].value["instrumentType"] == "ETF"
    assert response.freshness.holdings_as_of is not None


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
