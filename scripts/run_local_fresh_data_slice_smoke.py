#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.lightweight_data_fetch import fetch_lightweight_asset_data, lightweight_payload_checksum
from backend.lightweight_page import (
    build_lightweight_details_response,
    build_lightweight_overview_response,
    build_lightweight_sources_response,
)
from backend.models import AssetType, LightweightFetchResponse, LightweightFetchState
from backend.settings import build_lightweight_data_settings


SCHEMA_VERSION = "local-fresh-data-mvp-slice-smoke-v1"
RETRIEVED_AT = "2026-05-02T12:00:00Z"
SUPPORTED_SLICE_TICKERS = ("AAPL", "MSFT", "NVDA", "VOO", "SPY", "VTI", "QQQ", "XLK")
BLOCKED_SLICE_TICKERS = ("TQQQ", "ARKK", "BND", "GLD")
SLICE_TICKERS = (*SUPPORTED_SLICE_TICKERS, *BLOCKED_SLICE_TICKERS)
BLOCKED_GENERATED_SURFACES = (
    "generated_pages",
    "generated_chat_answers",
    "generated_comparisons",
    "weekly_news_focus",
    "ai_comprehensive_analysis",
    "exports",
    "generated_risk_summaries",
    "generated_output_cache_entries",
)
COMPARISON_EXPORT_PARITY_SUMMARY = {
    "schema_version": "local-fresh-data-mvp-slice-comparison-export-parity-inputs-v1",
    "check_name": "local_fresh_data_mvp_slice_comparison_export_parity",
    "representative_comparison_pairs": [
        {"left_ticker": "VOO", "right_ticker": "QQQ", "comparison_type": "etf_vs_etf"},
        {"left_ticker": "AAPL", "right_ticker": "VOO", "comparison_type": "stock_vs_etf"},
    ],
    "unavailable_or_blocked_comparison_cases": [
        {"left_ticker": "VOO", "right_ticker": "SPY", "expected_state": "eligible_not_cached"},
        {"left_ticker": "VOO", "right_ticker": "TQQQ", "expected_state": "unsupported"},
        {"left_ticker": "AAPL", "right_ticker": "TQQQ", "expected_state": "unsupported"},
    ],
    "asset_export_case_tickers": ["AAPL", "VOO", "QQQ", "SPY", "TQQQ", "ARKK", "BND", "GLD"],
    "export_surfaces": [
        "comparison_json",
        "comparison_markdown",
        "asset_json",
        "asset_markdown",
        "source_list_json",
        "source_list_markdown",
        "asset_chat_compare_redirect",
    ],
    "operator_only_optional_checks_skipped_by_default": True,
}
STATUS_DEFINITIONS = {
    "pass": "Renderable supported row with official SEC stock evidence or official issuer ETF evidence plus labeled provider fallback.",
    "partial": "Renderable ETF row without a deterministic issuer fixture; manifest/scope evidence, labeled provider fallback, and visible issuer gaps remain.",
    "blocked": "Generated-output-ineligible row with every generated surface disabled.",
    "unavailable": "Non-renderable row when deterministic fake evidence or explicit live prerequisites are absent.",
}

EXPECTED_SLICE: dict[str, dict[str, Any]] = {
    "AAPL": {"asset_type": "stock", "support_state": "supported_renderable", "generated_output_eligible": True},
    "MSFT": {"asset_type": "stock", "support_state": "supported_renderable", "generated_output_eligible": True},
    "NVDA": {"asset_type": "stock", "support_state": "supported_renderable", "generated_output_eligible": True},
    "VOO": {"asset_type": "etf", "support_state": "issuer_backed_supported", "generated_output_eligible": True},
    "SPY": {"asset_type": "etf", "support_state": "supported_renderable_partial", "generated_output_eligible": True},
    "VTI": {"asset_type": "etf", "support_state": "supported_renderable_partial", "generated_output_eligible": True},
    "QQQ": {"asset_type": "etf", "support_state": "issuer_backed_supported", "generated_output_eligible": True},
    "XLK": {"asset_type": "etf", "support_state": "supported_renderable_partial", "generated_output_eligible": True},
    "TQQQ": {
        "asset_type": "unsupported",
        "recognition_type": "etf_or_etp",
        "support_state": "blocked_unsupported",
        "generated_output_eligible": False,
    },
    "ARKK": {
        "asset_type": "unsupported",
        "recognition_type": "etf_or_etp",
        "support_state": "blocked_unsupported",
        "generated_output_eligible": False,
    },
    "BND": {
        "asset_type": "unsupported",
        "recognition_type": "etf_or_etp",
        "support_state": "blocked_unsupported",
        "generated_output_eligible": False,
    },
    "GLD": {
        "asset_type": "unsupported",
        "recognition_type": "etf_or_etp",
        "support_state": "blocked_unsupported",
        "generated_output_eligible": False,
    },
}


@dataclass(frozen=True)
class StockFixture:
    cik: int
    name: str
    exchange: str
    revenue: int
    net_income: int
    assets: int
    price: float


@dataclass(frozen=True)
class QuoteFixture:
    name: str
    quote_type: str
    exchange: str
    instrument_type: str
    price: float


STOCK_FIXTURES = {
    "AAPL": StockFixture(320193, "Apple Inc.", "Nasdaq", 391_000_000_000, 93_000_000_000, 350_000_000_000, 199.50),
    "MSFT": StockFixture(789019, "Microsoft Corporation", "Nasdaq", 245_000_000_000, 88_000_000_000, 512_000_000_000, 412.25),
    "NVDA": StockFixture(1045810, "NVIDIA Corporation", "Nasdaq", 130_000_000_000, 72_000_000_000, 111_000_000_000, 875.10),
}

QUOTE_FIXTURES = {
    "AAPL": QuoteFixture("Apple Inc.", "EQUITY", "NMS", "EQUITY", 199.50),
    "MSFT": QuoteFixture("Microsoft Corporation", "EQUITY", "NMS", "EQUITY", 412.25),
    "NVDA": QuoteFixture("NVIDIA Corporation", "EQUITY", "NMS", "EQUITY", 875.10),
    "VOO": QuoteFixture("Vanguard S&P 500 ETF", "ETF", "PCX", "ETF", 662.52),
    "SPY": QuoteFixture("SPDR S&P 500 ETF Trust", "ETF", "PCX", "ETF", 670.01),
    "VTI": QuoteFixture("Vanguard Total Stock Market ETF", "ETF", "PCX", "ETF", 331.44),
    "QQQ": QuoteFixture("Invesco QQQ Trust", "ETF", "NMS", "ETF", 548.20),
    "XLK": QuoteFixture("Technology Select Sector SPDR Fund", "ETF", "PCX", "ETF", 231.08),
}


class LocalFreshDataSliceFakeFetcher:
    no_live_external_calls = True

    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch_json(self, url: str, *, user_agent: str, timeout_seconds: int) -> dict[str, Any]:
        del user_agent, timeout_seconds
        self.urls.append(url)
        parsed = urlsplit(url)
        if parsed.netloc == "www.sec.gov" and parsed.path.endswith("/company_tickers_exchange.json"):
            return {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [[fixture.cik, fixture.name, ticker, fixture.exchange] for ticker, fixture in STOCK_FIXTURES.items()],
            }
        if parsed.netloc == "data.sec.gov" and parsed.path.startswith("/submissions/CIK"):
            ticker = _ticker_from_cik_path(parsed.path)
            return _sec_submissions_payload(ticker)
        if parsed.netloc == "data.sec.gov" and parsed.path.startswith("/api/xbrl/companyfacts/CIK"):
            ticker = _ticker_from_cik_path(parsed.path)
            return _companyfacts_payload(ticker)
        if parsed.netloc == "query1.finance.yahoo.com" and parsed.path.endswith("/finance/search"):
            ticker = normalize_query_ticker(parse_qs(parsed.query).get("q", [""])[0])
            return _yahoo_search_payload(ticker)
        if parsed.netloc == "query1.finance.yahoo.com" and "/finance/chart/" in parsed.path:
            ticker = normalize_query_ticker(parsed.path.rsplit("/", 1)[-1])
            return _yahoo_chart_payload(ticker)
        raise AssertionError(f"Unexpected deterministic slice URL: {url}")


def run_slice_smoke(tickers: list[str] | None = None) -> dict[str, Any]:
    active_tickers = [normalize_query_ticker(ticker) for ticker in (tickers or list(SLICE_TICKERS))]
    settings = build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-slice-smoke/0.1 test@example.com",
        }
    )
    fetcher = LocalFreshDataSliceFakeFetcher()
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    for ticker in active_tickers:
        before_count = len(fetcher.urls)
        response = fetch_lightweight_asset_data(
            ticker,
            settings=settings,
            fetcher=fetcher,
            retrieved_at=RETRIEVED_AT,
        )
        row = _row_contract(response, EXPECTED_SLICE.get(ticker, _unknown_expected(ticker)), len(fetcher.urls) - before_count)
        rows.append(row)
        blockers.extend(row["blockers"])

    status_counts = _status_counts(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if not blockers else "blocked",
        "slice_name": "local_fresh_data_mvp_slice",
        "policy": "lightweight_personal_mvp_only",
        "normal_ci_requires_live_calls": False,
        "browser_startup_required": False,
        "local_services_required": False,
        "secret_values_reported": False,
        "raw_payload_values_reported": False,
        "raw_payload_exposed_count": sum(1 for row in rows if row["raw_payload_exposed"]),
        "status_definitions": STATUS_DEFINITIONS,
        "supported_renderable_tickers": list(SUPPORTED_SLICE_TICKERS),
        "issuer_backed_etf_tickers": ["VOO", "QQQ"],
        "partial_etf_tickers": ["SPY", "VTI", "XLK"],
        "blocked_regression_tickers": list(BLOCKED_SLICE_TICKERS),
        "blocked_generated_surfaces": list(BLOCKED_GENERATED_SURFACES),
        "comparison_export_parity_summary": COMPARISON_EXPORT_PARITY_SUMMARY,
        "status_counts": status_counts,
        "blockers": blockers,
        "rows": rows,
    }


def _row_contract(response: LightweightFetchResponse, expected: dict[str, Any], fetch_call_count: int) -> dict[str, Any]:
    row_status = _row_status(response)
    surface = _surface_contract(response)
    blockers = _row_blockers(response, expected, row_status, surface, fetch_call_count)
    source_labels = sorted({source.source_label.value for source in response.sources})
    issuer_backed = (
        response.asset.asset_type is AssetType.etf
        and response.fetch_state is LightweightFetchState.supported
        and "official" in source_labels
        and response.diagnostics.get("issuer_enrichment_state") == "supported"
    )
    return {
        "ticker": response.ticker,
        "status": row_status,
        "expected_asset_type": expected["asset_type"],
        "expected_recognition_type": expected.get("recognition_type", expected["asset_type"]),
        "expected_support_state": expected["support_state"],
        "expected_generated_output_eligible": expected["generated_output_eligible"],
        "asset_type": response.asset.asset_type.value,
        "fetch_state": response.fetch_state.value,
        "page_render_state": response.page_render_state.value,
        "generated_output_eligible": response.generated_output_eligible,
        "source_labels": source_labels,
        "official_source_count": response.diagnostics.get("official_source_count", 0),
        "provider_fallback_source_count": response.diagnostics.get("provider_fallback_source_count", 0),
        "issuer_backed": issuer_backed,
        "issuer_evidence_state": "supported" if issuer_backed else "partial" if response.asset.asset_type is AssetType.etf else "not_applicable",
        "source_count": len(response.sources),
        "citation_count": len(response.citations),
        "fact_count": len(response.facts),
        "gap_count": len(response.gaps),
        "freshness": {
            "page_last_updated_at": response.freshness.page_last_updated_at,
            "facts_as_of": response.freshness.facts_as_of,
            "holdings_as_of": response.freshness.holdings_as_of,
            "freshness_state": response.freshness.freshness_state.value,
        },
        "raw_payload_exposed": response.raw_payload_exposed,
        "no_live_external_calls": response.no_live_external_calls,
        "fetch_call_count": fetch_call_count,
        "payload_checksum": lightweight_payload_checksum(response),
        "surface_contract": surface,
        "blocked_generated_surfaces": list(BLOCKED_GENERATED_SURFACES) if not response.generated_output_eligible else [],
        "blockers": blockers,
    }


def _surface_contract(response: LightweightFetchResponse) -> dict[str, Any]:
    if response.fetch_state not in {LightweightFetchState.supported, LightweightFetchState.partial}:
        return {
            "renderable": False,
            "generated_page": False,
            "generated_chat_answer": False,
            "generated_comparison": False,
            "weekly_news_focus": False,
            "ai_comprehensive_analysis": False,
            "export": False,
            "generated_risk_summary": False,
            "source_drawer_state": "unavailable",
            "overview_state": response.page_render_state.value,
        }
    overview = build_lightweight_overview_response(response)
    details = build_lightweight_details_response(response)
    sources = build_lightweight_sources_response(response)
    section_states = {
        section.section_id: {
            "evidence_state": section.evidence_state.value,
            "freshness_state": section.freshness_state.value,
            "citation_count": len(section.citation_ids),
            "source_document_count": len(section.source_document_ids),
        }
        for section in overview.sections
    }
    detail_fact_keys = sorted(details.facts.keys())
    return {
        "renderable": (
            overview.state.status.value == "supported"
            and len(overview.top_risks) == 3
            and bool(overview.sections)
            and bool(overview.citations)
            and bool(sources.source_groups)
            and not response.raw_payload_exposed
        ),
        "generated_page": True,
        "generated_chat_answer": False,
        "generated_comparison": False,
        "weekly_news_focus": overview.weekly_news_focus.selected_item_count > 0 if overview.weekly_news_focus else False,
        "ai_comprehensive_analysis": overview.ai_comprehensive_analysis.analysis_available
        if overview.ai_comprehensive_analysis
        else False,
        "export": False,
        "generated_risk_summary": bool(overview.top_risks),
        "overview_state": overview.state.status.value,
        "asset_type": overview.asset.asset_type.value,
        "beginner_summary_present": overview.beginner_summary is not None,
        "top_risk_count": len(overview.top_risks),
        "section_count": len(overview.sections),
        "citation_count": len(overview.citations),
        "source_document_count": len(overview.source_documents),
        "source_drawer_state": sources.drawer_state.value,
        "source_group_count": len(sources.source_groups),
        "source_drawer_citation_binding_count": len(sources.citation_bindings),
        "source_drawer_related_claim_count": len(sources.related_claims),
        "detail_fact_keys": detail_fact_keys,
        "partial_section_ids": sorted(
            section_id for section_id, state in section_states.items() if state["evidence_state"] == "partial"
        ),
        "unavailable_detail_fact_keys": sorted(
            key for key, value in details.facts.items() if _is_unavailable_detail_value(value)
        ),
        "section_states": section_states,
    }


def _row_status(response: LightweightFetchResponse) -> str:
    if response.fetch_state is LightweightFetchState.supported:
        return "pass"
    if response.fetch_state is LightweightFetchState.partial:
        return "partial"
    if response.fetch_state in {LightweightFetchState.unsupported, LightweightFetchState.out_of_scope, LightweightFetchState.unknown}:
        return "blocked"
    return "unavailable"


def _is_unavailable_detail_value(value: Any) -> bool:
    unwrapped = getattr(value, "value", value)
    return isinstance(unwrapped, str) and unwrapped.lower().startswith("unavailable")


def _row_blockers(
    response: LightweightFetchResponse,
    expected: dict[str, Any],
    row_status: str,
    surface: dict[str, Any],
    fetch_call_count: int,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    expected_asset_type = expected["asset_type"]
    expected_generated = expected["generated_output_eligible"]
    if expected_asset_type != response.asset.asset_type.value:
        blockers.append({"reason_code": "asset_type_mismatch", "expected": expected_asset_type, "actual": response.asset.asset_type.value})
    if expected_generated != response.generated_output_eligible:
        blockers.append(
            {
                "reason_code": "generated_output_eligibility_mismatch",
                "expected": expected_generated,
                "actual": response.generated_output_eligible,
            }
        )
    if response.raw_payload_exposed:
        blockers.append({"reason_code": "raw_payload_exposed"})
    if not response.no_live_external_calls:
        blockers.append({"reason_code": "live_external_call_required"})
    if expected_generated:
        if row_status not in {"pass", "partial"}:
            blockers.append({"reason_code": "renderable_row_not_pass_or_partial", "status": row_status})
        if not surface.get("renderable"):
            blockers.append({"reason_code": "renderable_surface_contract_failed", "surface": surface})
        if response.asset.asset_type is AssetType.stock and "official" not in {source.source_label.value for source in response.sources}:
            blockers.append({"reason_code": "stock_official_source_missing"})
        if response.asset.asset_type is AssetType.etf:
            expected_support_state = expected.get("support_state")
            labels = {source.source_label.value for source in response.sources}
            section_states = surface.get("section_states", {})
            if expected_support_state == "issuer_backed_supported":
                if response.fetch_state is not LightweightFetchState.supported or response.page_render_state.value != "supported":
                    blockers.append(
                        {
                            "reason_code": "issuer_backed_etf_not_supported",
                            "fetch_state": response.fetch_state.value,
                            "page_render_state": response.page_render_state.value,
                        }
                    )
                if "official" not in labels:
                    blockers.append({"reason_code": "issuer_backed_etf_official_source_missing", "source_labels": sorted(labels)})
                if response.diagnostics.get("issuer_enrichment_state") != "supported":
                    blockers.append(
                        {
                            "reason_code": "issuer_backed_etf_enrichment_not_supported",
                            "issuer_enrichment_state": response.diagnostics.get("issuer_enrichment_state"),
                        }
                    )
                for section_id in ("fund_objective_role", "holdings_exposure"):
                    if (section_states.get(section_id) or {}).get("evidence_state") != "supported":
                        blockers.append({"reason_code": "issuer_backed_etf_supported_section_missing", "section_id": section_id})
                if surface.get("unavailable_detail_fact_keys"):
                    blockers.append(
                        {
                            "reason_code": "issuer_backed_etf_detail_fact_unavailable",
                            "unavailable_detail_fact_keys": surface.get("unavailable_detail_fact_keys"),
                        }
                    )
            else:
                if response.fetch_state is not LightweightFetchState.partial or response.page_render_state.value != "partial":
                    blockers.append(
                        {
                            "reason_code": "partial_etf_state_mismatch",
                            "fetch_state": response.fetch_state.value,
                            "page_render_state": response.page_render_state.value,
                        }
                    )
                if "partial" not in labels or "provider_derived" not in labels:
                    blockers.append({"reason_code": "etf_partial_or_provider_source_label_missing", "source_labels": sorted(labels)})
                if response.diagnostics.get("issuer_enrichment_state") == "supported":
                    blockers.append({"reason_code": "partial_etf_unexpected_issuer_enrichment"})
                for section_id in ("holdings_exposure", "cost_trading_context"):
                    if (section_states.get(section_id) or {}).get("evidence_state") != "partial":
                        blockers.append({"reason_code": "etf_partial_section_label_missing", "section_id": section_id})
                if "etf_issuer_evidence" not in {gap.field_name for gap in response.gaps}:
                    blockers.append({"reason_code": "partial_etf_issuer_gap_missing"})
    else:
        exposed_surface = any(bool(surface.get(key)) for key in ("generated_page", "generated_chat_answer", "generated_comparison", "weekly_news_focus", "ai_comprehensive_analysis", "export", "generated_risk_summary"))
        if row_status != "blocked":
            blockers.append({"reason_code": "blocked_row_status_mismatch", "status": row_status})
        if exposed_surface or response.sources or response.citations or response.facts:
            blockers.append(
                {
                    "reason_code": "blocked_row_exposed_generated_surface_or_evidence",
                    "source_count": len(response.sources),
                    "citation_count": len(response.citations),
                    "fact_count": len(response.facts),
                    "surface": surface,
                }
            )
        if fetch_call_count != 0:
            blockers.append({"reason_code": "blocked_row_used_provider_fetch", "fetch_call_count": fetch_call_count})
    return blockers


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in STATUS_DEFINITIONS}
    for row in rows:
        counts[row["status"]] += 1
    return counts


def _unknown_expected(ticker: str) -> dict[str, Any]:
    return {"asset_type": "unknown", "support_state": f"unexpected_{ticker.lower()}", "generated_output_eligible": False}


def _ticker_from_cik_path(path: str) -> str:
    cik = path.rsplit("CIK", 1)[-1].split(".", 1)[0]
    for ticker, fixture in STOCK_FIXTURES.items():
        if str(fixture.cik).zfill(10) == cik:
            return ticker
    raise AssertionError(f"Unexpected CIK path: {path}")


def _sec_submissions_payload(ticker: str) -> dict[str, Any]:
    del ticker
    return {
        "filings": {
            "recent": {
                "form": ["10-Q", "10-K"],
                "filingDate": ["2026-04-30", "2025-10-31"],
                "reportDate": ["2026-03-28", "2025-09-27"],
                "accessionNumber": ["0000000000-26-000001", "0000000000-25-000111"],
            }
        }
    }


def _companyfacts_payload(ticker: str) -> dict[str, Any]:
    fixture = STOCK_FIXTURES[ticker]
    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "label": "Revenue",
                    "units": {"USD": [_gaap_fact(fixture.revenue, "Revenue")]},
                },
                "NetIncomeLoss": {
                    "label": "Net income",
                    "units": {"USD": [_gaap_fact(fixture.net_income, "Net income")]},
                },
                "Assets": {
                    "label": "Assets",
                    "units": {"USD": [_gaap_fact(fixture.assets, "Assets")]},
                },
            }
        }
    }


def _gaap_fact(value: int, label: str) -> dict[str, Any]:
    del label
    return {"val": value, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-10-31", "end": "2025-09-27"}


def _yahoo_search_payload(ticker: str) -> dict[str, Any]:
    fixture = QUOTE_FIXTURES.get(ticker)
    if fixture is None:
        return {"quotes": []}
    return {
        "quotes": [
            {
                "symbol": ticker,
                "quoteType": fixture.quote_type,
                "shortname": fixture.name,
                "longname": fixture.name,
                "exchange": fixture.exchange,
            }
        ]
    }


def _yahoo_chart_payload(ticker: str) -> dict[str, Any]:
    fixture = QUOTE_FIXTURES.get(ticker)
    if fixture is None:
        return {"chart": {"result": []}}
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": ticker,
                        "instrumentType": fixture.instrument_type,
                        "regularMarketPrice": fixture.price,
                        "regularMarketTime": 1777665600,
                        "currency": "USD",
                        "fullExchangeName": "NasdaqGS" if fixture.exchange == "NMS" else "NYSEArca",
                    }
                }
            ]
        }
    }


def normalize_query_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic local fresh-data MVP slice smoke.")
    parser.add_argument("--ticker", action="append", dest="tickers", help="Optional ticker override; can be repeated.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()
    result = run_slice_smoke(args.tickers)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"local fresh-data MVP slice smoke: {result['status']}")
        for row in result["rows"]:
            print(
                f"- {row['status']}: {row['ticker']} "
                f"({row['asset_type']}), sources={row['source_count']}, raw_payload_exposed={row['raw_payload_exposed']}"
            )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
