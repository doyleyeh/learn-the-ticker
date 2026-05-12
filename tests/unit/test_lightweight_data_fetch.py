from __future__ import annotations

import json
from typing import Any

import backend.lightweight_data_fetch as lightweight_data_fetch
from backend.analysis_packs import build_economic_indicators_pack
from backend.generation_evidence import evidence_pack_from_lightweight_response
from backend.lightweight_data_fetch import (
    ETF_QUOTE_STAT_ROW_ORDER,
    STOCK_QUOTE_STAT_ROW_ORDER,
    UrlLibJsonFetcher,
    clear_lightweight_fetch_reuse_cache,
    fetch_lightweight_asset_data,
)
from backend.lightweight_page import (
    build_lightweight_details_response,
    build_lightweight_overview_response,
    build_lightweight_sources_response,
    clear_lightweight_page_build_cache,
    evaluate_lightweight_generated_output_promotion,
)
from backend.market_news import build_market_news_response
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
from scripts.run_lightweight_data_fetch_smoke import (
    run_current_stock_manifest_fetch_smoke,
    run_current_supported_etf_manifest_fetch_smoke,
)
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
                ],
                "news": _weekly_news_payload("AAPL"),
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
                ],
                "news": _weekly_news_payload("VOO"),
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
                ],
                "news": _weekly_news_payload("SPY"),
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


class SecUnavailableFakeJsonFetcher(FakeJsonFetcher):
    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        if "sec.gov" in url:
            self.urls.append(url)
            raise RuntimeError("sec_unavailable")
        return super().fetch_json(url, user_agent=user_agent, timeout_seconds=timeout_seconds)


class RecentSecFilingFakeJsonFetcher(FakeJsonFetcher):
    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        if "submissions/CIK0000320193" in url:
            self.urls.append(url)
            return {
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "filingDate": ["2026-05-01"],
                        "reportDate": ["2026-04-30"],
                        "accessionNumber": ["0000320193-26-000777"],
                    }
                }
            }
        return super().fetch_json(url, user_agent=user_agent, timeout_seconds=timeout_seconds)


class AlphaVantageFakeJsonFetcher(FakeJsonFetcher):
    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        if "alphavantage.co" in url and "function=OVERVIEW" in url:
            self.urls.append(url)
            return {
                "Symbol": "AAPL",
                "Name": "Apple Inc.",
                "Exchange": "NASDAQ",
                "Currency": "USD",
                "Sector": "Technology",
                "Industry": "Consumer Electronics",
                "Description": "Apple designs products and services for consumers and businesses.",
                "MarketCapitalization": "3120000000000",
                "PERatio": "30.5",
                "EPS": "6.4",
                "DividendYield": "0.0045",
                "RevenueTTM": "391000000000",
                "ProfitMargin": "0.24",
            }
        if "alphavantage.co" in url and "function=GLOBAL_QUOTE" in url:
            self.urls.append(url)
            return {
                "Global Quote": {
                    "01. symbol": "AAPL",
                    "05. price": "201.25",
                    "06. volume": "1234567",
                    "07. latest trading day": "2026-05-01",
                    "08. previous close": "199.50",
                }
            }
        return super().fetch_json(url, user_agent=user_agent, timeout_seconds=timeout_seconds)


class ReviewedProviderFakeJsonFetcher(FakeJsonFetcher):
    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        if "financialmodelingprep.com/api/v3/profile/AAPL" in url:
            self.urls.append(url)
            return [
                {
                    "symbol": "AAPL",
                    "companyName": "Apple Inc.",
                    "exchangeShortName": "NASDAQ",
                    "currency": "USD",
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "description": "Apple designs products and services.",
                    "mktCap": 3120000000000,
                }
            ]
        if "financialmodelingprep.com/api/v3/quote/AAPL" in url:
            self.urls.append(url)
            return [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "price": 202.4,
                    "previousClose": 201.2,
                    "volume": 7654321,
                    "pe": 31.2,
                    "eps": 6.49,
                }
            ]
        if "financialmodelingprep.com/api/v3/stock_news" in url:
            self.urls.append(url)
            return [
                {
                    "title": "AAPL supplier update supports weekly context",
                    "url": "https://financialmodelingprep.com/news/aapl-supplier-update",
                    "publishedDate": "2026-05-01 14:00:00",
                    "site": "Financial Modeling Prep",
                    "text": "A source-labeled provider news item connects AAPL to a supplier update in the current weekly window.",
                },
                {
                    "title": "AAPL product update appears in provider metadata",
                    "url": "https://financialmodelingprep.com/news/aapl-product-update",
                    "publishedDate": "2026-04-30 13:00:00",
                    "site": "Financial Modeling Prep",
                    "text": "A source-labeled provider news item connects AAPL to product context in the current weekly window.",
                },
            ]
        if "finnhub.io/api/v1/stock/profile2" in url:
            self.urls.append(url)
            return {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ NMS",
                "currency": "USD",
                "finnhubIndustry": "Technology",
                "marketCapitalization": 3120000,
            }
        if "finnhub.io/api/v1/quote" in url:
            self.urls.append(url)
            return {"c": 203.1, "pc": 202.0, "t": 1777665600}
        if "finnhub.io/api/v1/stock/metric" in url:
            self.urls.append(url)
            return {
                "metric": {
                    "10DayAverageTradingVolume": 159.99,
                    "52WeekLow": 150.2,
                    "52WeekHigh": 215.9,
                    "beta": 1.24,
                    "peNormalizedAnnual": 32.1,
                    "epsExclExtraItemsTTM": 6.52,
                    "currentDividendYieldTTM": 0.44,
                    "targetMean": 269.17,
                }
            }
        if "api.tiingo.com/tiingo/daily/AAPL" in url:
            self.urls.append(url)
            return {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "exchangeCode": "NASDAQ",
                "description": "Apple designs products and services.",
            }
        if "api.tiingo.com/iex/AAPL" in url:
            self.urls.append(url)
            return [{"ticker": "AAPL", "last": 204.2, "prevClose": 203.0, "volume": 8765432, "timestamp": "2026-05-01T20:00:00Z"}]
        if "eodhd.com/api/fundamentals/AAPL.US" in url:
            self.urls.append(url)
            return {
                "General": {
                    "Code": "AAPL",
                    "Name": "Apple Inc.",
                    "Exchange": "US",
                    "CurrencyCode": "USD",
                    "Sector": "Technology",
                    "Industry": "Consumer Electronics",
                    "Description": "Apple designs products and services.",
                    "UpdatedAt": "2026-05-01",
                },
                "Highlights": {"MarketCapitalization": 3120000000000, "PERatio": 33.1, "DilutedEpsTTM": 6.55, "DividendYield": 0.004},
            }
        if "eodhd.com/api/real-time/AAPL.US" in url:
            self.urls.append(url)
            return {"close": 205.3, "previousClose": 204.0, "volume": 6543210, "timestamp": "2026-05-01"}
        return super().fetch_json(url, user_agent=user_agent, timeout_seconds=timeout_seconds)


class _FakeHttpResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self, max_bytes: int) -> bytes:
        del max_bytes
        return self.payload


def _settings():
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_weekly_news():
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "true",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_reuse_ttl(ttl_seconds: int):
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_FETCH_REUSE_TTL_SECONDS": str(ttl_seconds),
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_persistent_cache(cache_dir: str):
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_FETCH_REUSE_TTL_SECONDS": "30",
            "LIGHTWEIGHT_FETCH_CACHE_DIR": cache_dir,
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_alpha_provider():
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_ORDER": "alpha_vantage,yahoo",
            "LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED": "true",
            "ALPHA_VANTAGE_API_KEY": "configured-test-key",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_alpha_provider_unreviewed_for_lightweight():
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_ORDER": "alpha_vantage,yahoo",
            "LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED": "false",
            "ALPHA_VANTAGE_API_KEY": "configured-test-key",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_reviewed_provider(provider: str):
    env_name = {
        "fmp": "FMP_API_KEY",
        "finnhub": "FINNHUB_API_KEY",
        "tiingo": "TIINGO_API_KEY",
        "eodhd": "EODHD_API_KEY",
    }[provider]
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_ORDER": f"{provider},yahoo",
            "LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED": "true",
            env_name: "configured-test-key",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _settings_with_reviewed_provider_weekly(provider: str):
    env_name = {
        "fmp": "FMP_API_KEY",
        "finnhub": "FINNHUB_API_KEY",
        "tiingo": "TIINGO_API_KEY",
        "eodhd": "EODHD_API_KEY",
    }[provider]
    return build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_ORDER": f"{provider},yahoo",
            "LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED": "true",
            env_name: "configured-test-key",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-tests/0.1 test@example.com",
        }
    )


def _weekly_news_payload(ticker: str) -> list[dict[str, Any]]:
    normalized = ticker.upper()
    publisher = "Yahoo Finance"
    if normalized in {"VOO", "SPY"}:
        return [
            {
                "uuid": f"{normalized.lower()}-issuer-context",
                "title": f"{normalized} issuer update highlights benchmark and fund context",
                "publisher": publisher,
                "link": f"https://finance.yahoo.com/news/{normalized.lower()}-issuer-context",
                "published_at": "2026-05-01T14:30:00Z",
                "summary": f"Provider news metadata linked {normalized} to an issuer or fund context update during the weekly window.",
                "relatedTickers": [normalized],
                "thumbnail": {"resolutions": [{"url": "https://example.invalid/thumb.jpg"}]},
            },
            {
                "uuid": f"{normalized.lower()}-flows-context",
                "title": f"{normalized} weekly ETF flows context appears in provider news",
                "publisher": "ETF.com",
                "link": f"https://finance.yahoo.com/news/{normalized.lower()}-weekly-flows-context",
                "published_at": "2026-04-30T13:15:00Z",
                "summary": f"Provider metadata surfaced a weekly ETF flow context item related to {normalized}.",
                "relatedTickers": [normalized],
            },
            {
                "uuid": f"{normalized.lower()}-advice-suppressed",
                "title": f"Is {normalized} still worth buying now?",
                "publisher": publisher,
                "link": f"https://finance.yahoo.com/news/{normalized.lower()}-worth-buying",
                "published_at": "2026-04-29T10:00:00Z",
                "summary": "Advice-like headline fixture should be suppressed by the local adapter.",
                "relatedTickers": [normalized],
            },
        ]
    return [
        {
            "uuid": f"{normalized.lower()}-earnings-context",
            "title": f"{normalized} earnings context appears in provider news metadata",
            "publisher": publisher,
            "link": f"https://finance.yahoo.com/news/{normalized.lower()}-earnings-context",
            "published_at": "2026-05-01T14:30:00Z",
            "summary": f"Provider news metadata linked {normalized} to earnings context during the weekly window.",
            "relatedTickers": [normalized],
        },
        {
            "uuid": f"{normalized.lower()}-business-context",
            "title": f"{normalized} product and business update noted by provider news",
            "publisher": "Reuters",
            "link": f"https://finance.yahoo.com/news/{normalized.lower()}-business-context",
            "published_at": "2026-04-30T13:15:00Z",
            "summary": f"Provider metadata surfaced a product or business context item related to {normalized}.",
            "relatedTickers": [normalized],
        },
    ]


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
                        "previousClose": _yahoo_number(199.5),
                        "open": _yahoo_number(201.1),
                        "bid": _yahoo_number(201.2),
                        "bidSize": _yahoo_number(4000),
                        "ask": _yahoo_number(201.4),
                        "askSize": _yahoo_number(200),
                        "dayLow": _yahoo_number(198.7),
                        "dayHigh": _yahoo_number(202.6),
                        "fiftyTwoWeekLow": _yahoo_number(150.2),
                        "fiftyTwoWeekHigh": _yahoo_number(215.9),
                        "volume": _yahoo_number(1234567),
                        "averageVolume": _yahoo_number(2345678),
                        "trailingPE": _yahoo_number(31.4),
                        "forwardPE": _yahoo_number(27.8),
                        "dividendRate": _yahoo_number(1.04),
                        "dividendYield": _yahoo_percent(0.0045),
                        "exDividendDate": {"raw": 1773187200, "fmt": "Mar 11, 2026"},
                        "52WeekChange": _yahoo_percent(0.112),
                    },
                    "defaultKeyStatistics": {
                        "enterpriseValue": _yahoo_money(3_180_000_000_000),
                        "beta": _yahoo_number(1.24),
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
                        "targetMeanPrice": _yahoo_number(269.17),
                    },
                    "calendarEvents": {
                        "earnings": {
                            "earningsDate": [{"raw": 1779235200, "fmt": "May 20, 2026"}],
                        },
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
                        "previousClose": _yahoo_number(661.4),
                        "open": _yahoo_number(662.0),
                        "bid": _yahoo_number(661.8),
                        "bidSize": _yahoo_number(16000),
                        "ask": _yahoo_number(662.1),
                        "askSize": _yahoo_number(12000),
                        "dayLow": _yahoo_number(660.5),
                        "dayHigh": _yahoo_number(665.8),
                        "fiftyTwoWeekLow": _yahoo_number(510.5),
                        "fiftyTwoWeekHigh": _yahoo_number(676.7),
                        "volume": _yahoo_number(5462989),
                        "averageVolume": _yahoo_number(9831696),
                        "totalAssets": _yahoo_money(1_420_000_000_000),
                        "navPrice": _yahoo_number(662.7),
                        "trailingPE": _yahoo_number(29.04),
                        "yield": _yahoo_percent(0.0119),
                        "ytdReturn": _yahoo_percent(0.0598),
                    },
                    "defaultKeyStatistics": {
                        "beta": _yahoo_number(1.0),
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


def test_lightweight_fetch_reuses_same_ticker_range_and_preserves_source_metadata():
    clear_lightweight_fetch_reuse_cache()
    fetcher = FakeJsonFetcher()
    settings = _settings_with_reuse_ttl(30)

    first = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT)
    first_url_count = len(fetcher.urls)
    second = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at="2026-05-02T12:00:10Z")

    assert first.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "miss"
    assert first.diagnostics["lightweight_fetch_reuse"]["stored"] is True
    assert second.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "hit"
    assert second.diagnostics["lightweight_fetch_reuse"]["key_context"] == first.diagnostics["lightweight_fetch_reuse"]["key_context"]
    assert len(fetcher.urls) == first_url_count
    assert [source.model_dump(mode="json") for source in second.sources] == [
        source.model_dump(mode="json") for source in first.sources
    ]
    assert [citation.model_dump(mode="json") for citation in second.citations] == [
        citation.model_dump(mode="json") for citation in first.citations
    ]
    assert second.fallback_diagnostics == first.fallback_diagnostics
    assert second.raw_payload_exposed is False
    assert second.diagnostics["lightweight_fetch_reuse"]["raw_payload_exposed"] is False
    assert second.diagnostics["lightweight_fetch_reuse"]["secret_values_exposed"] is False


def test_lightweight_fetch_reuse_misses_for_different_range_and_can_bypass():
    clear_lightweight_fetch_reuse_cache()
    fetcher = FakeJsonFetcher()
    settings = _settings_with_reuse_ttl(30)

    fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT, chart_range="6mo")
    six_month_url_count = len(fetcher.urls)
    one_year = fetch_lightweight_asset_data(
        "AAPL",
        settings=settings,
        fetcher=fetcher,
        retrieved_at=RETRIEVED_AT,
        chart_range="1y",
    )
    one_year_url_count = len(fetcher.urls)
    bypassed = fetch_lightweight_asset_data(
        "AAPL",
        settings=settings,
        fetcher=fetcher,
        retrieved_at=RETRIEVED_AT,
        chart_range="1y",
        bypass_reuse=True,
    )

    assert one_year.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "miss"
    assert one_year.diagnostics["lightweight_fetch_reuse"]["key_context"]["chart_range"] == "1y"
    assert one_year_url_count > six_month_url_count
    assert bypassed.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "bypass"
    assert bypassed.diagnostics["lightweight_fetch_reuse"]["stored"] is False
    assert len(fetcher.urls) > one_year_url_count


def test_lightweight_fetch_reuse_respects_ttl_expiry(monkeypatch):
    clear_lightweight_fetch_reuse_cache()
    fetcher = FakeJsonFetcher()
    settings = _settings_with_reuse_ttl(1)
    clock = {"value": 10.0}
    monkeypatch.setattr("backend.lightweight_data_fetch.time.monotonic", lambda: clock["value"])

    fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT)
    first_url_count = len(fetcher.urls)
    clock["value"] = 10.5
    hit = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT)
    hit_url_count = len(fetcher.urls)
    clock["value"] = 12.0
    expired = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert hit.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "hit"
    assert hit_url_count == first_url_count
    assert expired.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "miss"
    assert len(fetcher.urls) > first_url_count


def test_lightweight_persistent_cache_reuses_response_across_fetchers(tmp_path):
    clear_lightweight_fetch_reuse_cache()
    cache_dir = tmp_path / "fetch-cache"
    first_fetcher = FakeJsonFetcher()
    settings = _settings_with_persistent_cache(str(cache_dir))

    first = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=first_fetcher, retrieved_at=RETRIEVED_AT)
    first_url_count = len(first_fetcher.urls)
    clear_lightweight_fetch_reuse_cache()
    second_fetcher = FakeJsonFetcher()
    second = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=second_fetcher, retrieved_at=RETRIEVED_AT)

    assert first.diagnostics["lightweight_fetch_persistent_cache"]["cache_status"] == "stored"
    assert first.diagnostics["cache_status"] == "miss"
    assert first_url_count > 0
    assert second_fetcher.urls == []
    assert second.diagnostics["cache_status"] == "persistent_hit"
    assert second.diagnostics["lightweight_fetch_persistent_cache"]["cache_status"] == "hit"
    assert second.raw_payload_exposed is False
    assert second.diagnostics["lightweight_fetch_persistent_cache"]["raw_payload_exposed"] is False
    assert second.diagnostics["lightweight_fetch_persistent_cache"]["secret_values_exposed"] is False
    cache_files = list((cache_dir / "lightweight_fetch" / "AAPL").glob("*.json"))
    assert cache_files
    envelope = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert envelope["schema_version"] == "lightweight-fetch-persistent-cache-v2"
    assert envelope["source_cache_records"]
    assert envelope["normalized_response_checksum"]
    assert envelope["raw_payload_exposed"] is False
    assert all(record["raw_body_stored"] is False for record in envelope["source_cache_records"])
    assert all(record["secret_values_exposed"] is False for record in envelope["source_cache_records"])


def test_lightweight_fetch_reuse_preserves_partial_provider_fallback_result():
    clear_lightweight_fetch_reuse_cache()
    fetcher = SecUnavailableFakeJsonFetcher()
    settings = _settings_with_reuse_ttl(30)

    first = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT)
    first_url_count = len(fetcher.urls)
    second = fetch_lightweight_asset_data("AAPL", settings=settings, fetcher=fetcher, retrieved_at=RETRIEVED_AT)

    assert first.fetch_state is LightweightFetchState.partial
    assert first.page_render_state is EvidenceState.partial
    assert first.diagnostics["official_source_errors"]
    assert first.fallback_diagnostics is not None
    assert first.fallback_diagnostics.source_path == "provider_fallback_only"
    assert second.diagnostics["lightweight_fetch_reuse"]["cache_status"] == "hit"
    assert len(fetcher.urls) == first_url_count
    assert second.fetch_state is first.fetch_state
    assert second.fallback_diagnostics == first.fallback_diagnostics
    assert second.raw_payload_exposed is False


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
    assert fields["provider_quote_stats"].value["rows"]
    assert {row["metric_id"] for row in fields["provider_quote_stats"].value["rows"]} >= set(STOCK_QUOTE_STAT_ROW_ORDER)
    assert fields["provider_stock_metric_groups"].value["groups"]
    assert len(fields["provider_price_chart"].value["points"]) >= 6
    assert fields["provider_price_chart"].value["range"] == "6mo"
    assert fields["provider_price_chart"].value["interval"] == "1d"
    assert response.diagnostics["official_source_count"] == 3
    assert response.diagnostics["stock_official_ir_discovery"]["status"] == "registry_ready"
    assert response.diagnostics["stock_official_ir_discovery"]["human_review_required_per_source"] is False
    assert response.diagnostics["stock_official_ir_discovery"]["fallback_order"] == ["sec", "official_ir", "provider_api", "yahoo"]
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert response.diagnostics["fetch_tier_order"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["fetch_tiers_attempted"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["fetch_tiers_succeeded"] == ["official", "yahoo"]
    assert response.diagnostics["fields_filled_by_tier"]["official"] == [
        "latest_assets_fact",
        "latest_net_income_fact",
        "latest_revenue_fact",
        "latest_sec_filing",
        "sec_identity",
    ]
    assert response.diagnostics["fields_filled_by_tier"]["yahoo"]
    assert response.diagnostics["quote_stat_merge"]["row_contract"] == list(STOCK_QUOTE_STAT_ROW_ORDER)
    assert response.diagnostics["quote_stat_merge"]["unavailable_metric_ids"] == []
    assert response.diagnostics["final_fallback_level"] == "yahoo"
    first_sec_url = next(index for index, url in enumerate(fetcher.urls) if "sec.gov" in url)
    first_yahoo_url = next(index for index, url in enumerate(fetcher.urls) if "finance.yahoo.com" in url)
    assert first_sec_url < first_yahoo_url
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.schema_version == "lightweight-api-fallback-diagnostics-v1"
    assert response.fallback_diagnostics.source_path == "sec_official_provider_fallback"
    assert response.fallback_diagnostics.generated_output_eligible is True
    assert response.fallback_diagnostics.official_source_count == 3
    assert response.fallback_diagnostics.provider_fallback_source_count == 1
    assert response.fallback_diagnostics.raw_payload_exposed is False
    assert response.fallback_diagnostics.secret_values_exposed is False
    assert all("raw" not in fact.field_name for fact in response.facts)

    generation_pack = evidence_pack_from_lightweight_response(response)
    generation_context = generation_pack["generation_context"]
    assert generation_context["schema_version"] == "generation-context-v1"
    assert generation_context["asset_profile"]["sector"] == "Technology"
    assert "regularMarketPrice" not in json.dumps(generation_context)
    assert "provider_market_price" not in generation_context["evidence_limits"].get("notes", [])

    promotion = evaluate_lightweight_generated_output_promotion(response, allow_generated_output_cache_promotion=True)
    assert promotion["promotion_allowed"] is False
    assert "strict_audit_quality_source_approval_not_granted" in promotion["reason_codes"]

    overview = build_lightweight_overview_response(response)
    price_section = next(section for section in overview.sections if section.section_id == "price_chart")
    assert price_section.table is not None
    assert [row.row_id for row in price_section.table.rows] == list(STOCK_QUOTE_STAT_ROW_ORDER)
    assert all(row.evidence_state is not EvidenceState.unavailable for row in price_section.table.rows)
    assert next(row for row in price_section.table.rows if row.row_id == "forward_dividend_yield").values["value"] == "1.04 (0.45%)"


def test_lightweight_provider_api_runs_before_yahoo_and_fills_missing_fields_only():
    fetcher = AlphaVantageFakeJsonFetcher()

    response = fetch_lightweight_asset_data("AAPL", settings=_settings_with_alpha_provider(), fetcher=fetcher, retrieved_at=RETRIEVED_AT)
    fields = {fact.field_name: fact for fact in response.facts}

    alpha_url_indexes = [index for index, url in enumerate(fetcher.urls) if "alphavantage.co" in url]
    first_yahoo_url = next(index for index, url in enumerate(fetcher.urls) if "finance.yahoo.com" in url)
    assert alpha_url_indexes
    assert max(alpha_url_indexes) < first_yahoo_url
    assert response.diagnostics["fetch_tiers_attempted"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["fetch_tiers_succeeded"] == ["official", "provider_api", "yahoo"]
    assert "provider_market_price" in response.diagnostics["fields_filled_by_tier"]["provider_api"]
    assert fields["provider_market_price"].value["regularMarketPrice"] == 201.25
    assert any(source.publisher == "Alpha Vantage" for source in response.sources)
    assert any(source.publisher == "Yahoo Finance" for source in response.sources)
    assert "configured-test-key" not in str(response.model_dump(mode="json"))


def test_unreviewed_provider_api_runs_for_lightweight_display_but_not_strict_audit():
    fetcher = AlphaVantageFakeJsonFetcher()

    response = fetch_lightweight_asset_data(
        "AAPL",
        settings=_settings_with_alpha_provider_unreviewed_for_lightweight(),
        fetcher=fetcher,
        retrieved_at=RETRIEVED_AT,
    )

    alpha_url_indexes = [index for index, url in enumerate(fetcher.urls) if "alphavantage.co" in url]
    first_yahoo_url = next(index for index, url in enumerate(fetcher.urls) if "finance.yahoo.com" in url)
    assert alpha_url_indexes
    assert max(alpha_url_indexes) < first_yahoo_url
    assert response.diagnostics["fetch_tiers_attempted"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["fetch_tiers_succeeded"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["provider_api_source_use_reviewed"] is False
    assert response.diagnostics["provider_api_strict_audit_approved"] is False
    assert response.diagnostics["provider_api_lightweight_display_allowed_without_review"] is True
    assert response.diagnostics["provider_api_skipped"] == []
    assert "provider_market_price" in response.diagnostics["fields_filled_by_tier"]["provider_api"]
    assert any(source.publisher == "Alpha Vantage" for source in response.sources)
    serialized = str(response.model_dump(mode="json"))
    assert "configured-test-key" not in serialized
    assert response.raw_payload_exposed is False


def test_reviewed_provider_api_adapters_run_before_yahoo_without_secret_exposure():
    for provider, expected_publisher in [
        ("fmp", "Financial Modeling Prep"),
        ("finnhub", "Finnhub"),
        ("tiingo", "Tiingo"),
        ("eodhd", "EODHD"),
    ]:
        fetcher = ReviewedProviderFakeJsonFetcher()

        response = fetch_lightweight_asset_data(
            "AAPL",
            settings=_settings_with_reviewed_provider(provider),
            fetcher=fetcher,
            retrieved_at=RETRIEVED_AT,
        )

        provider_host_marker = {
            "fmp": "financialmodelingprep.com",
            "finnhub": "finnhub.io",
            "tiingo": "api.tiingo.com",
            "eodhd": "eodhd.com",
        }[provider]
        provider_url_indexes = [index for index, url in enumerate(fetcher.urls) if provider_host_marker in url]
        first_yahoo_url = next(index for index, url in enumerate(fetcher.urls) if "finance.yahoo.com" in url)
        assert provider_url_indexes
        assert max(provider_url_indexes) < first_yahoo_url
        assert response.diagnostics["fetch_tiers_attempted"] == ["official", "provider_api", "yahoo"]
        assert "provider_market_price" in response.diagnostics["fields_filled_by_tier"]["provider_api"]
        assert any(source.publisher == expected_publisher for source in response.sources)
        serialized = str(response.model_dump(mode="json"))
        assert "configured-test-key" not in serialized
        assert "provider payload value" not in serialized.lower()
        assert response.raw_payload_exposed is False


def test_quote_stats_merge_by_metric_and_do_not_treat_finnhub_average_volume_as_volume():
    fetcher = ReviewedProviderFakeJsonFetcher()

    response = fetch_lightweight_asset_data(
        "AAPL",
        settings=_settings_with_reviewed_provider("finnhub"),
        fetcher=fetcher,
        retrieved_at=RETRIEVED_AT,
    )

    quote_stat_facts = [fact for fact in response.facts if fact.field_name == "provider_quote_stats"]
    assert len(quote_stat_facts) >= 2
    finnhub_fact = next(fact for fact in quote_stat_facts if fact.source_document_ids == ["lw_finnhub_aapl_market_reference"])
    finnhub_rows = {row["metric_id"]: row for row in finnhub_fact.value["rows"]}
    assert "volume" not in finnhub_rows
    assert finnhub_rows["average_volume"]["value"] == "159,990,000"
    assert "forward_dividend_yield" not in finnhub_rows

    overview = build_lightweight_overview_response(response)
    price_section = next(section for section in overview.sections if section.section_id == "price_chart")
    assert price_section.table is not None
    rows = {row.row_id: row for row in price_section.table.rows}
    assert list(rows) == list(STOCK_QUOTE_STAT_ROW_ORDER)
    assert rows["bid"].values["value"] == "201.2 x 4,000"
    assert rows["ask"].values["value"] == "201.4 x 200"
    assert rows["volume"].values["value"] == "1,234,567"
    assert rows["average_volume"].values["value"] == "159,990,000"
    assert rows["forward_dividend_yield"].values["value"] == "1.04 (0.45%)"
    assert response.diagnostics["quote_stat_merge"]["unavailable_metric_ids"] == []


def test_configured_provider_api_weekly_news_runs_before_yahoo_without_raw_payloads():
    fetcher = ReviewedProviderFakeJsonFetcher()

    response = fetch_lightweight_asset_data(
        "AAPL",
        settings=_settings_with_reviewed_provider_weekly("fmp"),
        fetcher=fetcher,
        retrieved_at=RETRIEVED_AT,
    )

    fmp_news_url = next(index for index, url in enumerate(fetcher.urls) if "financialmodelingprep.com/api/v3/stock_news" in url)
    first_yahoo_url = next(index for index, url in enumerate(fetcher.urls) if "finance.yahoo.com" in url)
    assert fmp_news_url < first_yahoo_url
    weekly_facts = [fact for fact in response.facts if fact.field_name == "provider_weekly_news_event"]
    assert len(weekly_facts) >= 4
    assert any(source.source_type == "fmp_weekly_news_metadata" for source in response.sources)
    assert response.diagnostics["weekly_news_source_order"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["weekly_news_provider_api_candidate_count"] == 2
    assert response.diagnostics["weekly_news_yahoo_candidate_count"] == 2
    assert response.diagnostics["fmp_weekly_news_candidate_count"] == 2
    assert response.diagnostics["fmp_weekly_news_raw_payload_exposed"] is False
    assert "configured-test-key" not in str(response.model_dump(mode="json"))
    assert "provider payload value" not in str(response.model_dump(mode="json")).lower()
    overview = build_lightweight_overview_response(response)
    assert overview.weekly_news_focus is not None
    assert overview.weekly_news_focus.selection_diagnostics["selected_counts_by_acquisition_source"] == {
        "provider_api": 2,
        "yahoo": 2,
    }
    assert {item.source.source_type for item in overview.weekly_news_focus.items} >= {
        "fmp_weekly_news_metadata",
        "yahoo_finance_weekly_news_metadata",
    }
    assert overview.weekly_news_focus.items[0].source.publisher in {"Reuters", "Yahoo Finance"}


def test_url_lib_json_fetcher_accepts_provider_news_array_payload(monkeypatch):
    def fake_urlopen(request, timeout):
        del timeout
        assert request.full_url.startswith("https://financialmodelingprep.com/api/v3/stock_news")
        return _FakeHttpResponse(
            json.dumps(
                [
                    {
                        "title": "AAPL provider news row",
                        "url": "https://financialmodelingprep.com/news/aapl-provider-news",
                    }
                ]
            ).encode("utf-8")
        )

    monkeypatch.setattr(lightweight_data_fetch, "urlopen", fake_urlopen)

    payload = UrlLibJsonFetcher().fetch_json(
        "https://financialmodelingprep.com/api/v3/stock_news?tickers=AAPL&limit=8&apikey=test",
        user_agent="learn-the-ticker-tests/0.1",
        timeout_seconds=1,
    )

    assert isinstance(payload, list)
    assert payload[0]["title"] == "AAPL provider news row"


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
    quote_stat_ids = {row["metric_id"] for row in fields["provider_quote_stats"].value["rows"]}
    assert {"net_assets", "yield", "ytd_return"}.issubset(quote_stat_ids)
    assert len(fields["provider_price_chart"].value["points"]) >= 6
    assert fields["provider_price_chart"].value["range"] == "6mo"
    assert response.freshness.holdings_as_of == "2026-04-01"
    assert response.diagnostics["issuer_enrichment_state"] == "supported"
    assert response.diagnostics["issuer_enrichment_source"] == "etf_issuer_official_adapter"
    assert response.diagnostics["issuer_enrichment_live_capable"] is True
    assert response.diagnostics["issuer_source_pack_automation"]["source_pack_status"] == "automated_policy_ready"
    assert response.diagnostics["issuer_source_pack_automation"]["human_review_required_per_source"] is False
    assert response.diagnostics["issuer_source_pack_automation"]["fallback_order"] == ["official_issuer", "provider_api", "yahoo"]
    assert "holdings" in response.diagnostics["issuer_source_pack_automation"]["source_types"]
    component_by_id = {
        component["component_id"]: component
        for component in response.diagnostics["issuer_enrichment_components"]
    }
    assert component_by_id["issuer_page"]["status"] == "supported"
    assert component_by_id["fact_sheet"]["source_type"] == "issuer_fact_sheet"
    assert component_by_id["prospectus_or_summary_prospectus"]["source_type"] == "summary_prospectus"
    assert component_by_id["holdings"]["source_type"] == "issuer_holdings_file"
    assert component_by_id["exposures"]["source_type"] == "issuer_exposure_file"
    assert response.diagnostics["issuer_enrichment_missing_components"] == []
    assert response.diagnostics["fetch_tiers_attempted"] == ["official", "provider_api", "yahoo"]
    assert response.diagnostics["fetch_tiers_succeeded"] == ["official", "yahoo"]
    assert response.diagnostics["fields_filled_by_tier"]["official"]
    assert response.diagnostics["quote_stat_merge"]["row_contract"] == list(ETF_QUOTE_STAT_ROW_ORDER)
    assert response.diagnostics["quote_stat_merge"]["unavailable_metric_ids"] == []
    assert response.diagnostics["final_fallback_level"] == "yahoo"
    assert response.diagnostics["official_source_count"] == 4
    assert response.diagnostics["provider_fallback_source_count"] == 1
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.source_path == "issuer_backed_etf_provider_fallback"
    assert response.fallback_diagnostics.issuer_evidence_state == "supported"
    assert response.fallback_diagnostics.official_source_count == 4
    assert response.fallback_diagnostics.provider_fallback_source_count == 1
    assert response.fallback_diagnostics.gap_count == 1
    assert {gap.field_name for gap in response.gaps} == {"premium_discount_or_spread"}

    overview = build_lightweight_overview_response(response)
    price_section = next(section for section in overview.sections if section.section_id == "price_chart")
    assert price_section.table is not None
    assert price_section.table.table_id == "quote_stats"
    assert [row.row_id for row in price_section.table.rows] == list(ETF_QUOTE_STAT_ROW_ORDER)
    expense_row = next(row for row in price_section.table.rows if row.row_id == "expense_ratio")
    assert expense_row.evidence_state is EvidenceState.supported
    assert expense_row.citation_ids


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
    assert [risk.title for risk in overview.top_risks] == [
        "Single-company risk",
        "Business and competition risk",
        "Financial and valuation risk",
    ]
    assert all("Provider" not in risk.title for risk in overview.top_risks)
    assert all("Reported results can change" != risk.title for risk in overview.top_risks)
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
        "evidence_limits",
        "educational_suitability",
    } <= set(sections)
    assert sections["products_services"].evidence_state is EvidenceState.mixed
    assert "provider_profile_context" in {item.item_id for item in sections["products_services"].items}
    assert "products_services_gap" not in {item.item_id for item in sections["products_services"].items}
    assert "lightweight response" not in sections["products_services"].beginner_summary.lower()
    assert sections["strengths"].evidence_state is EvidenceState.partial
    assert "provider_learning_context" in {item.item_id for item in sections["strengths"].items}
    assert "strengths_gap" not in {item.item_id for item in sections["strengths"].items}
    assert sections["financial_quality"].evidence_state is EvidenceState.mixed
    assert "provider_financial_snapshot" in {item.item_id for item in sections["financial_quality"].items}
    assert "financial_quality_trend_gap" not in {item.item_id for item in sections["financial_quality"].items}
    assert sections["valuation_context"].evidence_state is EvidenceState.mixed
    assert "provider_valuation_ratios" in {item.item_id for item in sections["valuation_context"].items}
    assert "valuation_metrics_gap" not in {item.item_id for item in sections["valuation_context"].items}
    assert sections["business_overview"].table is not None
    assert sections["business_overview"].table.table_id == "stock_profile_snapshot"
    assert sections["financial_quality"].table is not None
    assert sections["valuation_context"].table is not None
    assert sections["price_chart"].chart is not None
    assert len(sections["price_chart"].chart.points) >= 6
    assert sections["top_risks"].items[0].citation_ids
    assert sections["evidence_limits"].section_type.value == "evidence_gap"
    assert "provider_reference_limits" in {item.item_id for item in sections["evidence_limits"].items}
    assert "reported_facts_are_point_in_time" in {item.item_id for item in sections["evidence_limits"].items}
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


def test_lightweight_weekly_news_adapter_selects_provider_metadata_when_enabled():
    response = fetch_lightweight_asset_data(
        "VOO",
        settings=_settings_with_weekly_news(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )
    overview = build_lightweight_overview_response(response)
    weekly_news_facts = [fact for fact in response.facts if fact.field_name == "provider_weekly_news_event"]

    assert response.diagnostics["weekly_news_adapter_boundary"] == "weekly-news-source-adapter-v1"
    assert response.diagnostics["weekly_news_fetch_enabled"] is True
    assert response.diagnostics["weekly_news_provider_candidate_count"] == 2
    assert response.diagnostics["weekly_news_provider_suppressed_count"] == 1
    assert response.diagnostics["weekly_news_raw_article_text_collected"] is False
    assert response.diagnostics["weekly_news_raw_provider_payload_exposed"] is False
    assert response.diagnostics["weekly_news_thumbnail_or_media_forwarded"] is False
    assert response.fallback_diagnostics is not None
    assert response.fallback_diagnostics.provider_fallback_source_count == 3
    assert response.fallback_diagnostics.freshness.recent_events_as_of == "2026-05-01"
    assert len(weekly_news_facts) == 2
    assert all(fact.evidence_state is EvidenceState.supported for fact in weekly_news_facts)
    dumped = str(response.model_dump(mode="json")).lower()
    assert "thumb.jpg" not in dumped
    assert "raw article body" not in dumped

    assert overview.weekly_news_focus is not None
    assert overview.weekly_news_focus.selected_item_count == 2
    assert overview.weekly_news_focus.items[0].source.source_quality.value == "provider"
    assert overview.weekly_news_focus.items[0].source.source_use_policy.value == "summary_allowed"
    assert overview.ai_comprehensive_analysis is not None
    assert overview.ai_comprehensive_analysis.analysis_available is True
    assert overview.ai_comprehensive_analysis.weekly_news_selected_item_count == 2


def test_lightweight_weekly_news_prefers_recent_official_filing_without_provider_news_flag():
    response = fetch_lightweight_asset_data(
        "AAPL",
        settings=_settings(),
        fetcher=RecentSecFilingFakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )
    overview = build_lightweight_overview_response(response)

    assert overview.weekly_news_focus is not None
    assert overview.weekly_news_focus.selected_item_count == 1
    item = overview.weekly_news_focus.items[0]
    assert item.source.is_official is True
    assert item.source.source_quality.value == "official"
    assert item.source.source_use_policy.value == "full_text_allowed"
    assert overview.ai_comprehensive_analysis is not None
    assert overview.ai_comprehensive_analysis.analysis_available is False


def test_lightweight_overview_uses_runtime_market_news_builder(monkeypatch):
    clear_lightweight_page_build_cache()
    calls: list[bool] = []

    def fake_runtime_market_news(*, cache_only: bool = False):
        calls.append(cache_only)
        return build_market_news_response()

    monkeypatch.setattr("backend.lightweight_page.build_runtime_market_news_response", fake_runtime_market_news)
    response = fetch_lightweight_asset_data(
        "VOO",
        settings=_settings(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )

    overview = build_lightweight_overview_response(response)

    assert calls == [True]
    assert overview.market_news_focus is not None


def test_lightweight_page_build_cache_reuses_validated_overview(monkeypatch):
    clear_lightweight_page_build_cache()
    calls: list[bool] = []

    def fake_runtime_market_news(*, cache_only: bool = False):
        calls.append(cache_only)
        return build_market_news_response()

    monkeypatch.setattr("backend.lightweight_page.build_runtime_market_news_response", fake_runtime_market_news)
    response = fetch_lightweight_asset_data(
        "VOO",
        settings=_settings(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )
    refreshed_response = response.model_copy(deep=True)
    refreshed_response.freshness.page_last_updated_at = "2026-05-10T05:00:00Z"
    for source in refreshed_response.sources:
        source.retrieved_at = "2026-05-10T05:00:00Z"
    for fact in refreshed_response.facts:
        if fact.retrieved_at is not None:
            fact.retrieved_at = "2026-05-10T05:00:00Z"

    first = build_lightweight_overview_response(response)
    second = build_lightweight_overview_response(refreshed_response)

    assert calls == [True]
    assert first == second
    assert first is not second


def test_lightweight_page_build_cache_reuses_overview_with_same_economic_context(monkeypatch):
    clear_lightweight_page_build_cache()
    calls: list[bool] = []

    def fake_runtime_market_news(*, cache_only: bool = False, economic_indicators=None):  # noqa: ANN001
        assert economic_indicators is not None
        calls.append(cache_only)
        return build_market_news_response(economic_indicators=economic_indicators)

    monkeypatch.setattr("backend.lightweight_page.build_runtime_market_news_response", fake_runtime_market_news)
    response = fetch_lightweight_asset_data(
        "VOO",
        settings=_settings(),
        fetcher=FakeJsonFetcher(),
        retrieved_at=RETRIEVED_AT,
    )
    economic_indicators = build_economic_indicators_pack()

    first = build_lightweight_overview_response(response, economic_indicators=economic_indicators)
    second = build_lightweight_overview_response(response, economic_indicators=economic_indicators.model_copy(deep=True))

    assert calls == [True]
    assert first == second
    assert first is not second


def test_lightweight_issuer_backed_etf_fetch_builds_supported_page_contracts():
    clear_lightweight_page_build_cache()
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
    assert [risk.title for risk in overview.top_risks] == [
        "Market risk",
        "Concentration risk",
        "Tracking risk",
    ]
    assert "Provider fallback limits" not in {risk.title for risk in overview.top_risks}
    assert "Issuer facts are point-in-time" not in {risk.title for risk in overview.top_risks}
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
        "evidence_limits",
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
    assert "methodology_scope_note" in {item.item_id for item in sections["construction_methodology"].items}
    assert "methodology_detail_gap" not in {item.item_id for item in sections["construction_methodology"].items}
    assert "lightweight mode" not in sections["construction_methodology"].beginner_summary.lower()
    assert sections["cost_trading_context"].evidence_state is EvidenceState.mixed
    assert "quote_stats_context" in {item.item_id for item in sections["cost_trading_context"].items}
    assert "premium_discount_or_spread" not in {item.item_id for item in sections["cost_trading_context"].items}
    assert sections["etf_specific_risks"].items[0].citation_ids
    assert sections["evidence_limits"].section_type.value == "evidence_gap"
    assert "provider_fallback_limits" in {item.item_id for item in sections["evidence_limits"].items}
    assert "issuer_facts_are_point_in_time" in {item.item_id for item in sections["evidence_limits"].items}
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
        assert surface["generated_chat_answer"] is True
        assert surface["source_drawer_state"] == "available"
        assert surface["chat_contract"]["safety_classification"] == "educational"
        assert surface["chat_contract"]["citation_count"] > 0
        assert surface["chat_contract"]["source_document_count"] > 0
        assert surface["chat_contract"]["same_asset_citations_only"] is True
        assert surface["chat_contract"]["fallback_diagnostics_in_uncertainty"] is True
        assert surface["chat_contract"]["generated_output_cache_promoted"] is False
        assert surface["chat_contract"]["durable_knowledge_pack_persisted"] is False
        assert surface["durable_persistence_contract"]["status"] == "persisted"
        assert surface["durable_persistence_contract"]["source_snapshot_persisted"] is True
        assert surface["durable_persistence_contract"]["knowledge_pack_persisted"] is True
        assert surface["durable_persistence_contract"]["knowledge_pack_re_read"] is True
        assert surface["durable_persistence_contract"]["source_snapshot_re_read"] is True
        assert surface["durable_persistence_contract"]["generated_output_cache_promoted"] is False
        assert surface["durable_persistence_contract"]["strict_audit_quality_source_approval_granted"] is False
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
        assert surface["generated_chat_answer"] is True
        assert surface["source_drawer_state"] == "available"
        assert surface["chat_contract"]["safety_classification"] == "educational"
        assert surface["chat_contract"]["citation_count"] > 0
        assert surface["chat_contract"]["source_document_count"] > 0
        assert surface["chat_contract"]["same_asset_citations_only"] is True
        assert surface["chat_contract"]["fallback_diagnostics_in_uncertainty"] is True
        assert surface["chat_contract"]["generated_output_cache_promoted"] is False
        assert surface["chat_contract"]["durable_knowledge_pack_persisted"] is False
        assert surface["durable_persistence_contract"]["status"] == "persisted"
        assert surface["durable_persistence_contract"]["source_snapshot_persisted"] is True
        assert surface["durable_persistence_contract"]["knowledge_pack_persisted"] is True
        assert surface["durable_persistence_contract"]["knowledge_pack_re_read"] is True
        assert surface["durable_persistence_contract"]["source_snapshot_re_read"] is True
        assert surface["durable_persistence_contract"]["generated_output_cache_promoted"] is False
        assert surface["durable_persistence_contract"]["strict_audit_quality_source_approval_granted"] is False
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
        durable_contract = row["surface_contract"].pop("durable_persistence_contract")
        assert durable_contract["status"] == "skipped"
        assert durable_contract["source_snapshot_persisted"] is False
        assert durable_contract["knowledge_pack_persisted"] is False
        assert durable_contract["generated_output_cache_promoted"] is False
        assert durable_contract["strict_audit_quality_source_approval_granted"] is False
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


def test_current_supported_etf_manifest_fetch_smoke_reports_every_row_without_live_calls():
    result = run_current_supported_etf_manifest_fetch_smoke()

    assert result["schema_version"] == "current-supported-etf-lightweight-fetch-smoke-v1"
    assert result["status"] == "pass"
    assert result["normal_ci_requires_live_calls"] is False
    assert result["live_provider_calls_attempted"] is False
    assert result["issuer_calls_attempted"] is False
    assert result["recognition_rows_unlock_generated_output"] is False
    assert result["failure_rows"] == []

    counts = result["counts"]
    assert counts == {
        "current_supported_etf_manifest_rows": 13,
        "issuer_backed_supported_count": 5,
        "provider_fallback_partial_count": 8,
        "unavailable_count": 0,
        "blocked_recognition_count": 9,
        "generated_output_eligible_count": 13,
        "strict_manifest_generated_output_eligible_count": 2,
        "failure_count": 0,
    }

    rows = {row["ticker"]: row for row in result["rows"]}
    assert set(rows) == {"VOO", "QQQ", "SPY", "VTI", "IVV", "IWM", "DIA", "VGT", "XLK", "SOXX", "SMH", "XLF", "XLV"}
    voo = rows["VOO"]
    assert voo["support_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert voo["fetch_state"] == "supported"
    assert voo["official_issuer_attempt_state"]["state"] == "supported"
    assert voo["official_issuer_attempt_state"]["missing_components"] == []
    assert {
        component["component_id"]: component["status"]
        for component in voo["official_issuer_attempt_state"]["components"]
    } == {
        "issuer_page": "supported",
        "fact_sheet": "supported",
        "prospectus_or_summary_prospectus": "supported",
        "holdings": "supported",
        "exposures": "supported",
    }
    assert voo["provider_fallback_state"]["state"] == "used"
    assert all(record["source_checksum"].startswith("sha256:") for record in voo["source_checksums"])
    assert voo["payload_checksum"].startswith("sha256:")
    assert voo["raw_payload_exposed"] is False
    assert voo["no_live_external_calls"] is True

    ivv = rows["IVV"]
    assert ivv["fetch_state"] == "partial"
    assert ivv["page_render_state"] == "partial"
    assert ivv["official_issuer_attempt_state"]["state"] == "eligible_not_cached"
    assert ivv["official_issuer_attempt_state"]["missing_components"] == []
    assert set(ivv["source_labels"]) == {"partial", "provider_derived"}
    assert ivv["provider_fallback_state"]["state"] == "used"
    assert "provider_derived display fallback only" in ivv["provider_fallback_state"]["source_use_note"]
    assert "etf_issuer_evidence" in {gap["field_name"] for gap in ivv["missing_evidence_gaps"]}

    recognition_rows = result["recognition_rows"]
    assert len(recognition_rows) == 9
    assert all(row["support_authority"] == "data/universes/us_etp_recognition.current.json" for row in recognition_rows)
    assert all(row["authoritative_for_generated_output"] is False for row in recognition_rows)
    assert all(row["generated_output_eligible"] is False for row in recognition_rows)
    assert all(all(value is False for value in row["surface_eligibility"].values()) for row in recognition_rows)


def test_current_stock_manifest_fetch_smoke_reports_every_row_without_live_calls():
    result = run_current_stock_manifest_fetch_smoke()

    assert result["schema_version"] == "current-stock-manifest-lightweight-fetch-smoke-v1"
    assert result["status"] == "pass"
    assert result["normal_ci_requires_live_calls"] is False
    assert result["live_provider_calls_attempted"] is False
    assert result["sec_calls_attempted"] is False
    assert result["failure_rows"] == []
    assert result["stock_runtime_authority"] == "data/universes/us_common_stocks_top500.current.json"
    assert result["generated_output_cache_promotion_prerequisites"] == {
        "strict_audit_quality_source_approval_required": True,
        "source_handoff_required_for_promotion": True,
        "generated_output_cache_promoted": False,
    }

    counts = result["counts"]
    assert counts == {
        "current_stock_manifest_rows": 10,
        "sec_backed_supported_count": 10,
        "provider_fallback_partial_count": 0,
        "unavailable_count": 0,
        "blocked_unsupported_or_out_of_scope_count": 0,
        "generated_output_eligible_count": 10,
        "failure_count": 0,
    }

    rows = {row["ticker"]: row for row in result["rows"]}
    assert set(rows) == {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"}
    amzn = rows["AMZN"]
    assert amzn["company_name"] == "Amazon.com, Inc."
    assert amzn["support_authority"] == "data/universes/us_common_stocks_top500.current.json"
    assert amzn["fetch_state"] == "supported"
    assert amzn["sec_attempt_state"]["state"] == "supported"
    assert {
        component["component_id"]: component["state"]
        for component in amzn["sec_attempt_state"]["components"]
    } == {
        "sec_company_identity": "supported",
        "sec_submissions": "supported",
        "sec_xbrl_companyfacts": "supported",
        "sec_filing_evidence": "supported",
    }
    assert amzn["provider_fallback_state"]["state"] == "used"
    assert "provider_derived display fallback only" in amzn["provider_fallback_state"]["source_use_note"]
    assert amzn["freshness"]["facts_as_of"] == "2025-10-31"
    assert amzn["payload_checksum"].startswith("sha256:")
    assert all(record["source_checksum"].startswith("sha256:") for record in amzn["source_checksums"])
    assert amzn["raw_payload_exposed"] is False
    assert amzn["no_live_external_calls"] is True
