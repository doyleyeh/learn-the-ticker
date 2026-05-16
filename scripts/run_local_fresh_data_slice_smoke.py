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
    persist_lightweight_evidence_if_configured,
)
from backend.chat import build_lightweight_chat_knowledge_pack, generate_chat_from_pack, validate_chat_response
from backend.models import AssetType, LightweightFetchResponse, LightweightFetchState
from backend.knowledge_pack_repository import InMemoryAssetKnowledgePackRepository
from backend.source_snapshot_repository import InMemorySourceSnapshotArtifactRepository
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
        {"left_ticker": "AAPL", "right_ticker": "MSFT", "comparison_type": "stock_vs_stock"},
    ],
    "unavailable_or_blocked_comparison_cases": [
        {"left_ticker": "VOO", "right_ticker": "SPY", "expected_state": "eligible_not_cached"},
        {"left_ticker": "SPY", "right_ticker": "VTI", "expected_state": "eligible_not_cached"},
        {"left_ticker": "VOO", "right_ticker": "TQQQ", "expected_state": "unsupported"},
        {"left_ticker": "AAPL", "right_ticker": "TQQQ", "expected_state": "unsupported"},
    ],
    "partial_etf_pair_coverage": {
        "partial_etf_tickers": [],
        "reason_code": "no_partial_etf_rows_in_current_slice",
        "representative_non_generated_pair": {
            "left_ticker": "SPY",
            "right_ticker": "VTI",
            "expected_state": "eligible_not_cached",
        },
    },
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
    "SPY": {"asset_type": "etf", "support_state": "issuer_backed_supported", "generated_output_eligible": True},
    "VTI": {"asset_type": "etf", "support_state": "issuer_backed_supported", "generated_output_eligible": True},
    "QQQ": {"asset_type": "etf", "support_state": "issuer_backed_supported", "generated_output_eligible": True},
    "XLK": {"asset_type": "etf", "support_state": "issuer_backed_supported", "generated_output_eligible": True},
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
    "AMZN": StockFixture(1018724, "Amazon.com, Inc.", "Nasdaq", 638_000_000_000, 59_000_000_000, 625_000_000_000, 184.40),
    "GOOGL": StockFixture(1652044, "Alphabet Inc. Class A", "Nasdaq", 350_000_000_000, 101_000_000_000, 450_000_000_000, 174.30),
    "META": StockFixture(1326801, "Meta Platforms, Inc.", "Nasdaq", 165_000_000_000, 62_000_000_000, 276_000_000_000, 612.75),
    "TSLA": StockFixture(1318605, "Tesla, Inc.", "Nasdaq", 97_000_000_000, 15_000_000_000, 122_000_000_000, 251.80),
    "BRK.B": StockFixture(1067983, "Berkshire Hathaway Inc. Class B", "NYSE", 371_000_000_000, 89_000_000_000, 1_100_000_000_000, 502.60),
    "JPM": StockFixture(19617, "JPMorgan Chase & Co.", "NYSE", 169_000_000_000, 49_000_000_000, 4_200_000_000_000, 265.35),
    "UNH": StockFixture(731766, "UnitedHealth Group Incorporated", "NYSE", 400_000_000_000, 22_000_000_000, 300_000_000_000, 526.10),
}

QUOTE_FIXTURES = {
    "AAPL": QuoteFixture("Apple Inc.", "EQUITY", "NMS", "EQUITY", 199.50),
    "MSFT": QuoteFixture("Microsoft Corporation", "EQUITY", "NMS", "EQUITY", 412.25),
    "NVDA": QuoteFixture("NVIDIA Corporation", "EQUITY", "NMS", "EQUITY", 875.10),
    "AMZN": QuoteFixture("Amazon.com, Inc.", "EQUITY", "NMS", "EQUITY", 184.40),
    "GOOGL": QuoteFixture("Alphabet Inc. Class A", "EQUITY", "NMS", "EQUITY", 174.30),
    "META": QuoteFixture("Meta Platforms, Inc.", "EQUITY", "NMS", "EQUITY", 612.75),
    "TSLA": QuoteFixture("Tesla, Inc.", "EQUITY", "NMS", "EQUITY", 251.80),
    "BRK.B": QuoteFixture("Berkshire Hathaway Inc. Class B", "EQUITY", "NYQ", "EQUITY", 502.60),
    "JPM": QuoteFixture("JPMorgan Chase & Co.", "EQUITY", "NYQ", "EQUITY", 265.35),
    "UNH": QuoteFixture("UnitedHealth Group Incorporated", "EQUITY", "NYQ", "EQUITY", 526.10),
    "VOO": QuoteFixture("Vanguard S&P 500 ETF", "ETF", "PCX", "ETF", 662.52),
    "SPY": QuoteFixture("SPDR S&P 500 ETF Trust", "ETF", "PCX", "ETF", 670.01),
    "VTI": QuoteFixture("Vanguard Total Stock Market ETF", "ETF", "PCX", "ETF", 331.44),
    "IVV": QuoteFixture("iShares Core S&P 500 ETF", "ETF", "PCX", "ETF", 662.10),
    "IWM": QuoteFixture("iShares Russell 2000 ETF", "ETF", "PCX", "ETF", 226.75),
    "DIA": QuoteFixture("SPDR Dow Jones Industrial Average ETF Trust", "ETF", "PCX", "ETF", 462.30),
    "VGT": QuoteFixture("Vanguard Information Technology ETF", "ETF", "PCX", "ETF", 721.45),
    "QQQ": QuoteFixture("Invesco QQQ Trust", "ETF", "NMS", "ETF", 548.20),
    "XLK": QuoteFixture("Technology Select Sector SPDR Fund", "ETF", "PCX", "ETF", 231.08),
    "SOXX": QuoteFixture("iShares Semiconductor ETF", "ETF", "PCX", "ETF", 248.66),
    "SMH": QuoteFixture("VanEck Semiconductor ETF", "ETF", "PCX", "ETF", 327.80),
    "XLF": QuoteFixture("Financial Select Sector SPDR Fund", "ETF", "PCX", "ETF", 54.35),
    "XLV": QuoteFixture("Health Care Select Sector SPDR Fund", "ETF", "PCX", "ETF", 141.22),
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
        if parsed.netloc == "query1.finance.yahoo.com" and "/finance/quoteSummary/" in parsed.path:
            ticker = normalize_query_ticker(parsed.path.rsplit("/", 1)[-1])
            return _yahoo_quote_summary_payload(ticker)
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
        "issuer_backed_etf_tickers": ["VOO", "QQQ", "SPY", "VTI", "XLK"],
        "partial_etf_tickers": [],
        "partial_etf_coverage_reason": "no_partial_etf_rows_in_current_slice",
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
        "fallback_diagnostics": _serialized_fallback_diagnostics(response),
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
            "durable_persistence_contract": {
                "schema_version": "local-fresh-data-slice-durable-persistence-contract-v1",
                "status": "skipped",
                "source_snapshot_persisted": False,
                "knowledge_pack_persisted": False,
                "knowledge_pack_re_read": False,
                "source_snapshot_re_read": False,
                "normalized_fact_count": 0,
                "source_snapshot_artifact_count": 0,
                "strict_audit_quality_source_approval_granted": False,
                "generated_output_cache_promoted": False,
                "raw_payload_exposed": False,
                "secret_values_exposed": False,
                "reason_codes": ["lightweight_response_not_renderable"],
            },
        }
    overview = build_lightweight_overview_response(response)
    details = build_lightweight_details_response(response)
    sources = build_lightweight_sources_response(response)
    chat = _lightweight_chat_surface(response)
    durable = _lightweight_durable_surface(response)
    section_states = {
        section.section_id: {
            "evidence_state": section.evidence_state.value,
            "freshness_state": section.freshness_state.value,
            "citation_count": len(section.citation_ids),
            "source_document_count": len(section.source_document_ids),
        }
        for section in overview.sections
    }
    section_by_id = {section.section_id: section for section in overview.sections}
    price_chart_section = section_by_id.get("price_chart")
    holdings_section = section_by_id.get("holdings_exposure")
    sector_section = section_by_id.get("sector_weightings")
    performance_section = section_by_id.get("performance")
    stock_table_sections = [
        section
        for section in overview.sections
        if section.table is not None
        and (section.section_id in {"business_overview", "financial_quality", "valuation_context"} or section.section_id.startswith("provider_"))
    ]
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
        "generated_chat_answer": chat["generated_chat_answer"],
        "generated_comparison": False,
        "weekly_news_focus": overview.weekly_news_focus.selected_item_count > 0 if overview.weekly_news_focus else False,
        "ai_comprehensive_analysis": overview.ai_comprehensive_analysis.analysis_available
        if overview.ai_comprehensive_analysis
        else False,
        "export": True,
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
        "chat_contract": chat,
        "durable_persistence_contract": durable,
        "detail_fact_keys": detail_fact_keys,
        "partial_section_ids": sorted(
            section_id for section_id, state in section_states.items() if state["evidence_state"] == "partial"
        ),
        "unavailable_detail_fact_keys": sorted(
            key for key, value in details.facts.items() if _is_unavailable_detail_value(value)
        ),
        "section_states": section_states,
        "dashboard_contract": {
            "default_chart_range": "6mo",
            "chart_range": price_chart_section.chart.range if price_chart_section and price_chart_section.chart else None,
            "chart_interval": price_chart_section.chart.interval if price_chart_section and price_chart_section.chart else None,
            "chart_point_count": len(price_chart_section.chart.points) if price_chart_section and price_chart_section.chart else 0,
            "quote_stat_row_count": len(price_chart_section.table.rows) if price_chart_section and price_chart_section.table else 0,
            "top_holdings_row_count": len(holdings_section.table.rows) if holdings_section and holdings_section.table else 0,
            "sector_weighting_row_count": len(sector_section.table.rows) if sector_section and sector_section.table else 0,
            "performance_row_count": len(performance_section.table.rows) if performance_section and performance_section.table else 0,
            "stock_metric_table_count": len(stock_table_sections),
            "stock_metric_table_ids": [section.table.table_id for section in stock_table_sections if section.table is not None],
        },
    }


def _lightweight_chat_surface(response: LightweightFetchResponse) -> dict[str, Any]:
    try:
        pack = build_lightweight_chat_knowledge_pack(response)
        question = "What does it hold?" if response.asset.asset_type is AssetType.etf else "What is this asset?"
        chat = generate_chat_from_pack(pack, question)
        validation = validate_chat_response(chat, pack)
        citation_source_ids = {citation.source_document_id for citation in chat.citations}
        source_document_ids = {source.source_document_id for source in chat.source_documents}
        return {
            "generated_chat_answer": (
                chat.safety_classification.value == "educational"
                and bool(chat.citations)
                and bool(chat.source_documents)
                and validation.valid
                and citation_source_ids <= source_document_ids
            ),
            "safety_classification": chat.safety_classification.value,
            "citation_count": len(chat.citations),
            "source_document_count": len(chat.source_documents),
            "same_asset_citations_only": all(
                source.source_document_id in {pack_source.source_document_id for pack_source in pack.source_documents}
                for source in chat.source_documents
            ),
            "source_use_policies": sorted({source.source_use_policy.value for source in chat.source_documents}),
            "freshness_states": sorted({source.freshness_state.value for source in chat.source_documents}),
            "fallback_diagnostics_in_uncertainty": any(
                "Lightweight fallback diagnostics:" in item for item in chat.uncertainty
            ),
            "validation_status": validation.status.value,
            "generated_output_cache_promoted": False,
            "durable_knowledge_pack_persisted": False,
        }
    except Exception as exc:
        return {
            "generated_chat_answer": False,
            "safety_classification": None,
            "citation_count": 0,
            "source_document_count": 0,
            "same_asset_citations_only": False,
            "source_use_policies": [],
            "freshness_states": [],
            "fallback_diagnostics_in_uncertainty": False,
            "validation_status": f"error:{type(exc).__name__}",
            "generated_output_cache_promoted": False,
            "durable_knowledge_pack_persisted": False,
        }


def _lightweight_durable_surface(response: LightweightFetchResponse) -> dict[str, Any]:
    source_repo = InMemorySourceSnapshotArtifactRepository()
    knowledge_repo = InMemoryAssetKnowledgePackRepository()
    diagnostics = persist_lightweight_evidence_if_configured(
        response,
        source_snapshot_repository=source_repo,
        knowledge_pack_repository=knowledge_repo,
    )
    read_back = knowledge_repo.read_knowledge_pack_records(response.asset.ticker)
    snapshot_back = source_repo.read_source_snapshot_records(response.asset.ticker)
    return {
        "schema_version": "local-fresh-data-slice-durable-persistence-contract-v1",
        "status": diagnostics["status"],
        "source_snapshot_persisted": diagnostics["source_snapshot_persisted"],
        "knowledge_pack_persisted": diagnostics["knowledge_pack_persisted"],
        "knowledge_pack_re_read": read_back is not None,
        "source_snapshot_re_read": snapshot_back is not None,
        "normalized_fact_count": len(read_back.normalized_facts) if read_back else 0,
        "source_snapshot_artifact_count": len(snapshot_back.artifacts) if snapshot_back else 0,
        "strict_audit_quality_source_approval_granted": False,
        "generated_output_cache_promoted": False,
        "raw_payload_exposed": False,
        "secret_values_exposed": False,
        "reason_codes": diagnostics["reason_codes"],
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
    fallback_diagnostics = _serialized_fallback_diagnostics(response)
    blockers.extend(_fallback_diagnostic_blockers(response, expected, fallback_diagnostics))
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
        chat_contract = surface.get("chat_contract", {})
        if not surface.get("generated_chat_answer") or chat_contract.get("generated_output_cache_promoted") is not False:
            blockers.append({"reason_code": "lightweight_grounded_chat_contract_failed", "chat_contract": chat_contract})
        durable_contract = surface.get("durable_persistence_contract", {})
        if (
            durable_contract.get("status") != "persisted"
            or durable_contract.get("source_snapshot_persisted") is not True
            or durable_contract.get("knowledge_pack_persisted") is not True
            or durable_contract.get("knowledge_pack_re_read") is not True
            or durable_contract.get("source_snapshot_re_read") is not True
            or durable_contract.get("generated_output_cache_promoted") is not False
            or durable_contract.get("strict_audit_quality_source_approval_granted") is not False
        ):
            blockers.append({"reason_code": "lightweight_durable_persistence_contract_failed", "durable_contract": durable_contract})
        dashboard = surface.get("dashboard_contract", {})
        if dashboard.get("chart_range") != "6mo" or dashboard.get("chart_point_count", 0) < 6:
            blockers.append({"reason_code": "dashboard_chart_range_or_points_missing", "dashboard_contract": dashboard})
        if dashboard.get("quote_stat_row_count", 0) < 1:
            blockers.append({"reason_code": "dashboard_quote_stats_missing", "dashboard_contract": dashboard})
        if response.asset.asset_type is AssetType.stock and "official" not in {source.source_label.value for source in response.sources}:
            blockers.append({"reason_code": "stock_official_source_missing"})
        if response.asset.asset_type is AssetType.stock and surface.get("dashboard_contract", {}).get("stock_metric_table_count", 0) < 3:
            blockers.append({"reason_code": "stock_dashboard_metric_groups_missing", "dashboard_contract": dashboard})
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
                for metric_name, minimum in (
                    ("top_holdings_row_count", 10),
                    ("sector_weighting_row_count", 1),
                    ("performance_row_count", 1),
                ):
                    if dashboard.get(metric_name, 0) < minimum:
                        blockers.append(
                            {
                                "reason_code": "issuer_backed_etf_dashboard_section_missing",
                                "metric_name": metric_name,
                                "minimum": minimum,
                                "dashboard_contract": dashboard,
                            }
                        )
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


def _serialized_fallback_diagnostics(response: LightweightFetchResponse) -> dict[str, Any]:
    if response.fallback_diagnostics is None:
        return {}
    return response.fallback_diagnostics.model_dump(mode="json")


def _fallback_diagnostic_blockers(
    response: LightweightFetchResponse,
    expected: dict[str, Any],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    if not diagnostics:
        return [{"reason_code": "fallback_diagnostics_missing"}]

    blockers: list[dict[str, Any]] = []
    if diagnostics.get("schema_version") != "lightweight-api-fallback-diagnostics-v1":
        blockers.append({"reason_code": "fallback_diagnostics_schema_mismatch"})
    if diagnostics.get("fetch_state") != response.fetch_state.value:
        blockers.append({"reason_code": "fallback_diagnostics_fetch_state_mismatch"})
    if diagnostics.get("page_render_state") != response.page_render_state.value:
        blockers.append({"reason_code": "fallback_diagnostics_page_render_state_mismatch"})
    if diagnostics.get("generated_output_eligible") != response.generated_output_eligible:
        blockers.append({"reason_code": "fallback_diagnostics_generated_output_eligibility_mismatch"})
    if diagnostics.get("source_count") != len(response.sources):
        blockers.append({"reason_code": "fallback_diagnostics_source_count_mismatch"})
    if diagnostics.get("citation_count") != len(response.citations):
        blockers.append({"reason_code": "fallback_diagnostics_citation_count_mismatch"})
    if diagnostics.get("fact_count") != len(response.facts):
        blockers.append({"reason_code": "fallback_diagnostics_fact_count_mismatch"})
    if diagnostics.get("gap_count") != len(response.gaps):
        blockers.append({"reason_code": "fallback_diagnostics_gap_count_mismatch"})
    if diagnostics.get("raw_payload_exposed") is not False:
        blockers.append({"reason_code": "fallback_diagnostics_raw_payload_exposed"})
    if diagnostics.get("secret_values_exposed") is not False:
        blockers.append({"reason_code": "fallback_diagnostics_secret_values_exposed"})
    if diagnostics.get("raw_payload_fields_exposed") is not False:
        blockers.append({"reason_code": "fallback_diagnostics_raw_payload_fields_exposed"})
    if diagnostics.get("hidden_prompt_or_reasoning_exposed") is not False:
        blockers.append({"reason_code": "fallback_diagnostics_hidden_prompt_or_reasoning_exposed"})
    if diagnostics.get("diagnostics_are_sanitized") is not True:
        blockers.append({"reason_code": "fallback_diagnostics_not_sanitized"})

    expected_source_path = _expected_fallback_source_path(response, expected)
    if diagnostics.get("source_path") != expected_source_path:
        blockers.append(
            {
                "reason_code": "fallback_diagnostics_source_path_mismatch",
                "expected": expected_source_path,
                "actual": diagnostics.get("source_path"),
            }
        )
    if "raw_payload_hidden" not in set(diagnostics.get("reason_codes") or []):
        blockers.append({"reason_code": "fallback_diagnostics_raw_payload_hidden_reason_missing"})
    return blockers


def _expected_fallback_source_path(response: LightweightFetchResponse, expected: dict[str, Any]) -> str:
    if not expected["generated_output_eligible"]:
        return "blocked_scope_screen"
    if response.asset.asset_type is AssetType.stock:
        return "sec_official_provider_fallback"
    if expected.get("support_state") == "issuer_backed_supported":
        return "issuer_backed_etf_provider_fallback"
    return "etf_manifest_scope_provider_fallback"


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
        ],
        "news": _yahoo_weekly_news_payload(ticker),
    }


def _yahoo_weekly_news_payload(ticker: str) -> list[dict[str, Any]]:
    if ticker not in QUOTE_FIXTURES:
        return []
    return [
        {
            "uuid": f"{ticker.lower()}-weekly-context",
            "title": f"{ticker} weekly context appears in provider news metadata",
            "publisher": "Yahoo Finance",
            "link": f"https://finance.yahoo.com/news/{ticker.lower()}-weekly-context",
            "published_at": "2026-05-01T14:30:00Z",
            "summary": f"Provider metadata surfaced a Weekly News context item related to {ticker}.",
            "relatedTickers": [ticker],
        },
        {
            "uuid": f"{ticker.lower()}-source-context",
            "title": f"{ticker} source-labeled update appears in provider news",
            "publisher": "ETF.com" if QUOTE_FIXTURES[ticker].quote_type == "ETF" else "Reuters",
            "link": f"https://finance.yahoo.com/news/{ticker.lower()}-source-context",
            "published_at": "2026-04-30T13:15:00Z",
            "summary": f"Provider metadata surfaced a source-labeled recent context item for {ticker}.",
            "relatedTickers": [ticker],
        },
    ]


def _yahoo_chart_payload(ticker: str) -> dict[str, Any]:
    fixture = QUOTE_FIXTURES.get(ticker)
    if fixture is None:
        return {"chart": {"result": []}}
    timestamps = [1775073600, 1775682000, 1776286800, 1776891600, 1777496400, 1777665600]
    closes = [round(fixture.price * multiplier, 2) for multiplier in (0.94, 0.97, 0.99, 1.01, 0.995, 1.0)]
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
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "close": closes,
                                "volume": [1000000, 1200000, 980000, 1400000, 1100000, 1300000],
                            }
                        ]
                    },
                }
            ]
        }
    }


def _yahoo_quote_summary_payload(ticker: str) -> dict[str, Any]:
    quote = QUOTE_FIXTURES.get(ticker)
    if quote is None:
        return {"quoteSummary": {"result": []}}
    if quote.quote_type == "ETF":
        result = _etf_quote_summary(ticker, quote)
    else:
        result = _stock_quote_summary(ticker, quote)
    return {"quoteSummary": {"result": [result]}}


def _stock_quote_summary(ticker: str, quote: QuoteFixture) -> dict[str, Any]:
    stock = STOCK_FIXTURES.get(ticker)
    revenue = stock.revenue if stock else 100_000_000_000
    market_cap = int(quote.price * 15_700_000_000) if ticker == "AAPL" else int(quote.price * 7_500_000_000)
    return {
        "price": {
            "symbol": ticker,
            "longName": quote.name,
            "currency": "USD",
            "marketCap": _yahoo_money(market_cap),
        },
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Consumer Electronics" if ticker == "AAPL" else "Software - Infrastructure",
            "fullTimeEmployees": 164000 if ticker == "AAPL" else 228000,
            "companyOfficers": [
                {"name": "Tim Cook" if ticker == "AAPL" else "Satya Nadella", "title": "Chief Executive Officer"}
            ],
            "longBusinessSummary": f"{quote.name} provider profile summary fixture.",
        },
        "summaryDetail": {
            "trailingPE": _yahoo_number(31.4 if ticker == "AAPL" else 35.2),
            "forwardPE": _yahoo_number(27.8 if ticker == "AAPL" else 29.6),
            "dividendYield": _yahoo_percent(0.0045 if ticker == "AAPL" else 0.0072),
            "52WeekChange": _yahoo_percent(0.112 if ticker == "AAPL" else 0.184),
            "SandP52WeekChange": _yahoo_percent(0.157),
        },
        "defaultKeyStatistics": {
            "enterpriseValue": _yahoo_money(int(market_cap * 1.02)),
            "trailingEps": _yahoo_number(6.43 if ticker == "AAPL" else 12.11),
            "forwardEps": _yahoo_number(7.18 if ticker == "AAPL" else 13.92),
            "priceToBook": _yahoo_number(43.5 if ticker == "AAPL" else 10.8),
            "enterpriseToEbitda": _yahoo_number(24.2 if ticker == "AAPL" else 23.1),
            "heldPercentInstitutions": _yahoo_percent(0.62 if ticker == "AAPL" else 0.74),
        },
        "financialData": {
            "totalRevenue": _yahoo_money(revenue),
            "grossProfits": _yahoo_money(int(revenue * 0.45)),
            "revenueGrowth": _yahoo_percent(0.06 if ticker == "AAPL" else 0.15),
            "ebitda": _yahoo_money(int(revenue * 0.34)),
            "totalCash": _yahoo_money(65_000_000_000 if ticker == "AAPL" else 80_000_000_000),
            "totalDebt": _yahoo_money(95_000_000_000 if ticker == "AAPL" else 58_000_000_000),
            "currentRatio": _yahoo_number(0.92 if ticker == "AAPL" else 1.25),
            "operatingCashflow": _yahoo_money(118_000_000_000 if ticker == "AAPL" else 110_000_000_000),
            "freeCashflow": _yahoo_money(105_000_000_000 if ticker == "AAPL" else 78_000_000_000),
            "grossMargins": _yahoo_percent(0.46 if ticker == "AAPL" else 0.69),
            "operatingMargins": _yahoo_percent(0.31 if ticker == "AAPL" else 0.45),
            "profitMargins": _yahoo_percent(0.24 if ticker == "AAPL" else 0.36),
            "returnOnAssets": _yahoo_percent(0.22 if ticker == "AAPL" else 0.18),
            "returnOnEquity": _yahoo_percent(1.36 if ticker == "AAPL" else 0.34),
        },
    }


def _etf_quote_summary(ticker: str, quote: QuoteFixture) -> dict[str, Any]:
    return {
        "price": {"symbol": ticker, "longName": quote.name, "currency": "USD"},
        "summaryProfile": {
            "longBusinessSummary": (
                "The fund manager employs an indexing investment approach designed to track the performance "
                "of the Standard & Poor's 500 Index, a widely recognized benchmark of U.S. stock market "
                "performance that is dominated by the stocks of large U.S. companies. The advisor attempts "
                "to replicate the target index by investing all, or substantially all, of its assets in the "
                "stocks that make up the index, holding each stock in approximately the same proportion as "
                "its weighting in the index."
            )
            if ticker == "VOO"
            else f"{quote.name} provider fund profile summary fixture.",
        },
        "fundProfile": {
            "categoryName": "Large Blend" if ticker in {"VOO", "SPY"} else "Large Growth",
            "family": "Vanguard" if ticker in {"VOO", "VTI"} else "State Street" if ticker == "XLK" else "Invesco",
            "legalType": "Exchange Traded Fund",
        },
        "summaryDetail": {
            "totalAssets": _yahoo_money(1_420_000_000_000 if ticker == "VOO" else 600_000_000_000),
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
                {"consumer_defensive": _yahoo_percent(0.0526)},
                {"energy": _yahoo_percent(0.0402)},
                {"utilities": _yahoo_percent(0.0255)},
                {"real_estate": _yahoo_percent(0.0195)},
                {"basic_materials": _yahoo_percent(0.0191)},
            ],
        },
        "fundPerformance": {
            "trailingReturns": {
                "asOfDate": {"raw": 1777584000, "fmt": "2026-05-01"},
                "ytd": _yahoo_percent(0.0598),
                "oneMonth": _yahoo_percent(-0.0498),
                "threeMonth": _yahoo_percent(-0.0434),
                "oneYear": _yahoo_percent(0.1777),
                "threeYear": _yahoo_percent(0.1828),
                "fiveYear": _yahoo_percent(0.1202),
                "tenYear": _yahoo_percent(0.1412),
            },
            "annualTotalReturns": {
                "returns": [
                    {"year": "2025", "annualValue": _yahoo_percent(0.1782)},
                    {"year": "2024", "annualValue": _yahoo_percent(0.2498)},
                    {"year": "2023", "annualValue": _yahoo_percent(0.2632)},
                    {"year": "2022", "annualValue": _yahoo_percent(-0.1819)},
                    {"year": "2021", "annualValue": _yahoo_percent(0.2878)},
                    {"year": "2020", "annualValue": _yahoo_percent(0.1829)},
                ]
            },
        },
    }


def _yahoo_number(value: float | int) -> dict[str, Any]:
    return {"raw": value, "fmt": f"{value:,.2f}".rstrip("0").rstrip(".")}


def _yahoo_money(value: int) -> dict[str, Any]:
    return {"raw": value, "fmt": f"{value:,}"}


def _yahoo_percent(value: float) -> dict[str, Any]:
    return {"raw": value, "fmt": f"{value * 100:.2f}%"}


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
