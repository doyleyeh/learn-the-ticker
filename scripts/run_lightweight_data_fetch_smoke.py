#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.etf_universe import (
    RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH,
    SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH,
    can_generate_output_for_etf_entry,
    load_recognition_etf_universe_manifest,
    load_supported_etf_universe_manifest,
)
from backend.data import (
    TOP500_STOCK_UNIVERSE_MANIFEST_PATH,
    load_top500_stock_universe_manifest,
)
from backend.lightweight_data_fetch import (
    clear_lightweight_fetch_reuse_cache,
    fetch_lightweight_asset_data,
    lightweight_payload_checksum,
)
from backend.lightweight_page import (
    build_lightweight_details_response,
    build_lightweight_overview_response,
    build_lightweight_sources_response,
)
from backend.models import LightweightFetchState
from backend.settings import build_lightweight_data_settings
from scripts.run_local_fresh_data_slice_smoke import LocalFreshDataSliceFakeFetcher, RETRIEVED_AT


DEFAULT_TICKERS = ("AAPL", "VOO")
STOCK_AUTHORITY = "data/universes/us_common_stocks_top500.current.json"
SUPPORTED_ETF_AUTHORITY = "data/universes/us_equity_etfs_supported.current.json"
RECOGNITION_ETF_AUTHORITY = "data/universes/us_etp_recognition.current.json"
GENERATED_SURFACES = (
    "asset_pages",
    "chat_answers",
    "comparisons",
    "weekly_news_focus",
    "ai_comprehensive_analysis",
    "exports",
    "generated_risk_summaries",
    "generated_output_cache_entries",
)


def run_smoke(tickers: list[str], *, live: bool) -> dict[str, object]:
    env = dict(os.environ)
    if live:
        env["DATA_POLICY_MODE"] = "lightweight"
        env["LIGHTWEIGHT_LIVE_FETCH_ENABLED"] = "true"
        env.setdefault("LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED", "true")
    else:
        env.update(
            {
                "DATA_POLICY_MODE": "lightweight",
                "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
                "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
                "SEC_EDGAR_USER_AGENT": "learn-the-ticker-fetch-smoke/0.1 test@example.com",
            }
        )
    settings = build_lightweight_data_settings(env=env)
    clear_lightweight_fetch_reuse_cache()
    fetcher = None if live else LocalFreshDataSliceFakeFetcher()
    responses = [
        fetch_lightweight_asset_data(
            ticker,
            settings=settings,
            fetcher=fetcher,
            retrieved_at=None if live else RETRIEVED_AT,
        )
        for ticker in tickers
    ]
    repeated_responses = [
        fetch_lightweight_asset_data(
            ticker,
            settings=settings,
            fetcher=fetcher,
            retrieved_at=None if live else RETRIEVED_AT,
        )
        for ticker in tickers
    ]
    surface_contracts = [_surface_contract(response) for response in responses]
    acceptable_states = {LightweightFetchState.supported.value, LightweightFetchState.partial.value}
    blocked = [
        response.ticker
        for response, surface in zip(responses, surface_contracts, strict=True)
        if response.fetch_state.value not in acceptable_states
        or not response.sources
        or not response.facts
        or not surface["renderable"]
    ]
    return {
        "schema_version": "lightweight-data-fetch-smoke-v1",
        "status": "pass" if not blocked else "blocked",
        "deterministic_fixture_backed": not live,
        "normal_ci_requires_live_calls": False,
        "live_fetch_enabled": settings.live_fetch_enabled,
        "settings": settings.safe_diagnostics,
        "blocked_tickers": blocked,
        "reuse_diagnostics": _reuse_diagnostics(responses, repeated_responses),
        "current_stock_manifest_fetch": run_current_stock_manifest_fetch_smoke(),
        "surface_contracts": surface_contracts,
        "current_supported_etf_manifest_fetch": run_current_supported_etf_manifest_fetch_smoke(),
        "responses": [
            {
                "ticker": response.ticker,
                "fetch_state": response.fetch_state.value,
                "asset_type": response.asset.asset_type.value,
                "generated_output_eligible": response.generated_output_eligible,
                "source_labels": sorted({source.source_label.value for source in response.sources}),
                "official_source_count": response.diagnostics.get("official_source_count", 0),
                "provider_fallback_source_count": response.diagnostics.get("provider_fallback_source_count", 0),
                "fact_count": len(response.facts),
                "gap_count": len(response.gaps),
                "facts_as_of": response.freshness.facts_as_of,
                "retrieved_at": response.freshness.page_last_updated_at,
                "raw_payload_exposed": response.raw_payload_exposed,
                "payload_checksum": lightweight_payload_checksum(response),
            }
            for response in responses
        ],
    }


def run_current_stock_manifest_fetch_smoke() -> dict[str, Any]:
    """Exercise every current stock manifest row through deterministic lightweight fetch diagnostics."""

    settings = build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-current-stock-smoke/0.1 test@example.com",
        }
    )
    manifest = load_top500_stock_universe_manifest()
    fetcher = LocalFreshDataSliceFakeFetcher()
    clear_lightweight_fetch_reuse_cache()

    rows = [
        _current_stock_row(
            entry,
            fetch_lightweight_asset_data(
                entry.ticker,
                settings=settings,
                fetcher=fetcher,
                retrieved_at=RETRIEVED_AT,
                bypass_reuse=True,
            ),
        )
        for entry in manifest.entries
    ]
    failure_rows = _current_stock_failure_rows(rows)
    counts = {
        "current_stock_manifest_rows": len(rows),
        "sec_backed_supported_count": sum(
            1 for row in rows if row["fetch_state"] == LightweightFetchState.supported.value and row["sec_attempt_state"]["state"] == "supported"
        ),
        "provider_fallback_partial_count": sum(
            1
            for row in rows
            if row["fetch_state"] == LightweightFetchState.partial.value
            and row["provider_fallback_state"]["state"] == "used"
        ),
        "unavailable_count": sum(1 for row in rows if row["fetch_state"] == LightweightFetchState.unavailable.value),
        "blocked_unsupported_or_out_of_scope_count": sum(
            1 for row in rows if row["fetch_state"] in {LightweightFetchState.unsupported.value, LightweightFetchState.out_of_scope.value}
        ),
        "generated_output_eligible_count": sum(1 for row in rows if row["generated_output_eligible"] is True),
        "failure_count": len(failure_rows),
    }
    return {
        "schema_version": "current-stock-manifest-lightweight-fetch-smoke-v1",
        "status": "pass" if not failure_rows else "blocked",
        "deterministic": True,
        "normal_ci_requires_live_calls": False,
        "live_provider_calls_attempted": False,
        "sec_calls_attempted": False,
        "exchange_calls_attempted": False,
        "market_data_calls_attempted": False,
        "news_calls_attempted": False,
        "llm_calls_attempted": False,
        "secret_values_reported": False,
        "raw_payload_values_reported": False,
        "stock_runtime_authority": STOCK_AUTHORITY,
        "stock_manifest_file_path": str(TOP500_STOCK_UNIVERSE_MANIFEST_PATH.relative_to(ROOT)),
        "stock_manifest_checksum": manifest.generated_checksum,
        "counts": counts,
        "generated_output_cache_promotion_prerequisites": {
            "strict_audit_quality_source_approval_required": True,
            "source_handoff_required_for_promotion": True,
            "generated_output_cache_promoted": False,
        },
        "failure_rows": failure_rows,
        "rows": rows,
    }


def _current_stock_row(entry: Any, response: Any) -> dict[str, Any]:
    provider_count = int(response.diagnostics.get("provider_fallback_source_count", 0) or 0)
    return {
        "ticker": entry.ticker,
        "company_name": entry.name,
        "exchange": entry.exchange,
        "cik": entry.cik,
        "rank": entry.rank,
        "rank_basis": entry.rank_basis,
        "asset_type": "stock",
        "support_authority": STOCK_AUTHORITY,
        "support_state": "top500_manifest_supported",
        "fetch_state": response.fetch_state.value,
        "page_render_state": response.page_render_state.value,
        "generated_output_eligible": response.generated_output_eligible,
        "source_labels": sorted({source.source_label.value for source in response.sources}),
        "source_count": len(response.sources),
        "citation_count": len(response.citations),
        "fact_count": len(response.facts),
        "gap_count": len(response.gaps),
        "official_source_count": int(response.diagnostics.get("official_source_count", 0) or 0),
        "provider_fallback_source_count": provider_count,
        "sec_attempt_state": _sec_attempt_state(response),
        "provider_fallback_state": {
            "attempted": bool(response.diagnostics.get("provider_fallback_attempted")),
            "state": "used" if provider_count else "unavailable",
            "source_count": provider_count,
            "labels": [
                source.source_label.value
                for source in response.sources
                if source.source_label.value == "provider_derived"
            ],
            "source_use_note": "provider_derived display fallback only; not official SEC evidence or source-pack approval",
        },
        "missing_evidence_gaps": [
            {
                "field_name": gap.field_name,
                "evidence_state": gap.evidence_state.value,
                "freshness_state": gap.freshness_state.value,
                "message": str(gap.limitations or gap.value),
            }
            for gap in response.gaps
        ],
        "freshness": {
            "page_last_updated_at": response.freshness.page_last_updated_at,
            "facts_as_of": response.freshness.facts_as_of,
            "holdings_as_of": response.freshness.holdings_as_of,
            "freshness_state": response.freshness.freshness_state.value,
        },
        "payload_checksum": lightweight_payload_checksum(response),
        "source_checksums": _source_checksums(response),
        "raw_payload_exposed": response.raw_payload_exposed,
        "no_live_external_calls": response.no_live_external_calls,
        "fallback_diagnostics": response.fallback_diagnostics.model_dump(mode="json")
        if response.fallback_diagnostics
        else None,
    }


def _sec_attempt_state(response: Any) -> dict[str, Any]:
    facts = {fact.field_name for fact in response.facts}
    attempted = set(response.diagnostics.get("official_sources_attempted") or [])
    errors = response.diagnostics.get("official_source_errors") or []
    components = [
        {
            "component_id": "sec_company_identity",
            "source": "sec_company_tickers_exchange",
            "attempted": "sec_company_tickers_exchange" in attempted,
            "state": "supported" if "sec_identity" in facts else "missing",
        },
        {
            "component_id": "sec_submissions",
            "source": "sec_submissions",
            "attempted": "sec_submissions" in attempted,
            "state": "supported" if "latest_sec_filing" in facts else "missing",
        },
        {
            "component_id": "sec_xbrl_companyfacts",
            "source": "sec_companyfacts",
            "attempted": "sec_companyfacts" in attempted,
            "state": "supported"
            if {"latest_revenue_fact", "latest_net_income_fact", "latest_assets_fact"} & facts
            else "missing",
        },
        {
            "component_id": "sec_filing_evidence",
            "source": "sec_submissions_or_filing_fixture",
            "attempted": "sec_submissions" in attempted,
            "state": "supported" if "latest_sec_filing" in facts else "missing",
        },
    ]
    return {
        "attempted": bool(attempted),
        "state": "supported" if all(component["state"] == "supported" for component in components[:3]) else "partial",
        "components": components,
        "missing_components": [
            component["component_id"] for component in components if component["state"] != "supported"
        ],
        "errors": errors,
        "raw_payload_exposed": False,
        "source_pack_status": "not_approved_by_smoke",
    }


def run_current_supported_etf_manifest_fetch_smoke() -> dict[str, Any]:
    """Exercise every current supported ETF row through deterministic lightweight fetch diagnostics."""

    settings = build_lightweight_data_settings(
        {
            "DATA_POLICY_MODE": "lightweight",
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
            "SEC_EDGAR_USER_AGENT": "learn-the-ticker-current-etf-smoke/0.1 test@example.com",
        }
    )
    supported_manifest = load_supported_etf_universe_manifest()
    recognition_manifest = load_recognition_etf_universe_manifest()
    fetcher = LocalFreshDataSliceFakeFetcher()
    clear_lightweight_fetch_reuse_cache()

    rows = [
        _current_supported_etf_row(
            entry,
            fetch_lightweight_asset_data(
                entry.ticker,
                settings=settings,
                fetcher=fetcher,
                retrieved_at=RETRIEVED_AT,
                bypass_reuse=True,
            ),
        )
        for entry in supported_manifest.entries
    ]
    recognition_rows = [_recognition_row(entry) for entry in recognition_manifest.entries]
    failure_rows = _current_supported_etf_failure_rows(rows, recognition_rows)
    counts = {
        "current_supported_etf_manifest_rows": len(rows),
        "issuer_backed_supported_count": sum(1 for row in rows if row["official_issuer_attempt_state"]["state"] == "supported"),
        "provider_fallback_partial_count": sum(
            1
            for row in rows
            if row["fetch_state"] == LightweightFetchState.partial.value
            and row["provider_fallback_state"]["state"] == "used"
        ),
        "unavailable_count": sum(1 for row in rows if row["fetch_state"] == LightweightFetchState.unavailable.value),
        "blocked_recognition_count": sum(1 for row in recognition_rows if row["generated_output_eligible"] is False),
        "generated_output_eligible_count": sum(1 for row in rows if row["generated_output_eligible"] is True),
        "strict_manifest_generated_output_eligible_count": sum(
            1 for row in rows if row["strict_manifest_generated_output_eligible"] is True
        ),
        "failure_count": len(failure_rows),
    }
    return {
        "schema_version": "current-supported-etf-lightweight-fetch-smoke-v1",
        "status": "pass" if not failure_rows else "blocked",
        "deterministic": True,
        "normal_ci_requires_live_calls": False,
        "live_provider_calls_attempted": False,
        "issuer_calls_attempted": False,
        "market_data_calls_attempted": False,
        "news_calls_attempted": False,
        "llm_calls_attempted": False,
        "secret_values_reported": False,
        "raw_payload_values_reported": False,
        "supported_runtime_authority": SUPPORTED_ETF_AUTHORITY,
        "recognition_runtime_authority": RECOGNITION_ETF_AUTHORITY,
        "supported_manifest_file_path": str(SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH.relative_to(ROOT)),
        "recognition_manifest_file_path": str(RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH.relative_to(ROOT)),
        "supported_manifest_checksum": supported_manifest.generated_checksum,
        "recognition_manifest_checksum": recognition_manifest.generated_checksum,
        "recognition_rows_unlock_generated_output": any(row["generated_output_eligible"] for row in recognition_rows),
        "counts": counts,
        "failure_rows": failure_rows,
        "rows": rows,
        "recognition_rows": recognition_rows,
    }


def _current_supported_etf_row(entry: Any, response: Any) -> dict[str, Any]:
    provider_count = int(response.diagnostics.get("provider_fallback_source_count", 0) or 0)
    official_state = _official_issuer_attempt_state(response)
    return {
        "ticker": entry.ticker,
        "issuer": entry.issuer,
        "name": entry.fund_name,
        "asset_type": "etf",
        "support_authority": SUPPORTED_ETF_AUTHORITY,
        "recognition_authority_used_for_generated_output": False,
        "support_state": entry.support_state.value,
        "launch_cache_state": entry.launch_cache_state.value,
        "fetch_state": response.fetch_state.value,
        "page_render_state": response.page_render_state.value,
        "generated_output_eligible": response.generated_output_eligible,
        "strict_manifest_generated_output_eligible": can_generate_output_for_etf_entry(entry),
        "source_labels": sorted({source.source_label.value for source in response.sources}),
        "source_count": len(response.sources),
        "citation_count": len(response.citations),
        "fact_count": len(response.facts),
        "gap_count": len(response.gaps),
        "official_source_count": int(response.diagnostics.get("official_source_count", 0) or 0),
        "provider_fallback_source_count": provider_count,
        "official_issuer_attempt_state": official_state,
        "provider_fallback_state": {
            "attempted": bool(response.diagnostics.get("provider_fallback_attempted")),
            "state": "used" if provider_count else "unavailable",
            "source_count": provider_count,
            "labels": [
                source.source_label.value
                for source in response.sources
                if source.source_label.value == "provider_derived"
            ],
            "source_use_note": "provider_derived display fallback only; not official issuer evidence",
        },
        "missing_evidence_gaps": [
            {
                "field_name": gap.field_name,
                "evidence_state": gap.evidence_state.value,
                "freshness_state": gap.freshness_state.value,
                "message": str(gap.limitations or gap.value),
            }
            for gap in response.gaps
        ],
        "freshness": {
            "page_last_updated_at": response.freshness.page_last_updated_at,
            "facts_as_of": response.freshness.facts_as_of,
            "holdings_as_of": response.freshness.holdings_as_of,
            "freshness_state": response.freshness.freshness_state.value,
        },
        "payload_checksum": lightweight_payload_checksum(response),
        "source_checksums": _source_checksums(response),
        "raw_payload_exposed": response.raw_payload_exposed,
        "no_live_external_calls": response.no_live_external_calls,
        "fallback_diagnostics": response.fallback_diagnostics.model_dump(mode="json")
        if response.fallback_diagnostics
        else None,
    }


def _official_issuer_attempt_state(response: Any) -> dict[str, Any]:
    components = response.diagnostics.get("issuer_enrichment_components") or []
    missing = response.diagnostics.get("issuer_enrichment_missing_components") or []
    return {
        "attempted": bool(response.diagnostics.get("issuer_enrichment_attempted")),
        "source": response.diagnostics.get("issuer_enrichment_source"),
        "state": response.diagnostics.get("issuer_enrichment_state"),
        "component_state_counts": response.diagnostics.get("issuer_enrichment_component_state_counts") or {},
        "missing_components": list(missing),
        "components": components,
        "raw_payload_exposed": bool(response.diagnostics.get("issuer_enrichment_raw_payload_exposed", False)),
        "source_pack_status": (response.diagnostics.get("issuer_source_pack_automation") or {}).get("source_pack_status"),
    }


def _source_checksums(response: Any) -> list[dict[str, str]]:
    records = []
    for source in response.sources:
        payload = {
            "source_document_id": source.source_document_id,
            "source_label": source.source_label.value,
            "source_type": source.source_type,
            "publisher": source.publisher,
            "url": source.url,
            "as_of_date": source.as_of_date,
            "retrieved_at": source.retrieved_at,
            "source_use_policy": source.source_use_policy.value,
            "freshness_state": source.freshness_state.value,
        }
        records.append(
            {
                "source_document_id": source.source_document_id,
                "source_label": source.source_label.value,
                "source_checksum": "sha256:"
                + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
            }
        )
    return records


def _recognition_row(entry: Any) -> dict[str, Any]:
    return {
        "ticker": entry.ticker,
        "name": entry.fund_name,
        "issuer": entry.issuer,
        "support_authority": RECOGNITION_ETF_AUTHORITY,
        "authoritative_for_generated_output": False,
        "support_state": entry.support_state.value,
        "launch_cache_state": entry.launch_cache_state.value,
        "generated_output_eligible": False,
        "surface_eligibility": {surface: False for surface in GENERATED_SURFACES},
    }


def _current_supported_etf_failure_rows(rows: list[dict[str, Any]], recognition_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        labels = set(row["source_labels"])
        if row["support_authority"] != SUPPORTED_ETF_AUTHORITY:
            failures.append(_failure_row(row, "supported_etf_wrong_authority"))
        if row["recognition_authority_used_for_generated_output"]:
            failures.append(_failure_row(row, "supported_etf_used_recognition_authority"))
        if row["fetch_state"] not in {LightweightFetchState.supported.value, LightweightFetchState.partial.value}:
            failures.append(_failure_row(row, "supported_etf_fetch_state_not_renderable_or_partial"))
        if row["generated_output_eligible"] and not labels:
            failures.append(_failure_row(row, "generated_output_eligible_without_source_labels"))
        if row["fetch_state"] == LightweightFetchState.partial.value and "provider_derived" not in labels:
            failures.append(_failure_row(row, "partial_etf_missing_provider_derived_label"))
        if row["official_issuer_attempt_state"]["state"] == "supported" and "official" not in labels:
            failures.append(_failure_row(row, "issuer_supported_without_official_label"))
        if row["raw_payload_exposed"] or not row["no_live_external_calls"]:
            failures.append(_failure_row(row, "unsafe_payload_or_live_call_boundary"))
    for row in recognition_rows:
        if row["generated_output_eligible"] or any(row["surface_eligibility"].values()):
            failures.append(_failure_row(row, "recognition_row_unlocked_generated_output"))
    return failures


def _current_stock_failure_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        labels = set(row["source_labels"])
        if row["support_authority"] != STOCK_AUTHORITY:
            failures.append(_failure_row(row, "stock_row_wrong_runtime_authority"))
        if row["fetch_state"] not in {
            LightweightFetchState.supported.value,
            LightweightFetchState.partial.value,
            LightweightFetchState.unavailable.value,
        }:
            failures.append(_failure_row(row, "stock_row_unexpected_fetch_state"))
        if row["fetch_state"] == LightweightFetchState.supported.value and row["sec_attempt_state"]["state"] != "supported":
            failures.append(_failure_row(row, "stock_supported_without_sec_supported_state"))
        if row["fetch_state"] == LightweightFetchState.partial.value and "provider_derived" not in labels:
            failures.append(_failure_row(row, "stock_partial_missing_provider_derived_label"))
        if row["provider_fallback_state"]["state"] == "used" and "provider_derived" not in labels:
            failures.append(_failure_row(row, "stock_provider_fallback_used_without_label"))
        if row["generated_output_eligible"] and not labels:
            failures.append(_failure_row(row, "stock_generated_output_eligible_without_source_labels"))
        if row["raw_payload_exposed"] or not row["no_live_external_calls"]:
            failures.append(_failure_row(row, "stock_unsafe_payload_or_live_call_boundary"))
        if not str(row["payload_checksum"]).startswith("sha256:"):
            failures.append(_failure_row(row, "stock_payload_checksum_missing"))
    return failures


def _failure_row(row: dict[str, Any], reason_code: str) -> dict[str, Any]:
    return {
        "reason_code": reason_code,
        "ticker": row["ticker"],
        "support_authority": row.get("support_authority"),
        "support_state": row.get("support_state"),
        "fetch_state": row.get("fetch_state"),
        "generated_output_eligible": row.get("generated_output_eligible"),
    }


def _reuse_diagnostics(first_responses, repeated_responses) -> dict[str, object]:
    rows = []
    hit_count = 0
    miss_count = 0
    for first, repeated in zip(first_responses, repeated_responses, strict=True):
        first_reuse = first.diagnostics.get("lightweight_fetch_reuse") or {}
        repeated_reuse = repeated.diagnostics.get("lightweight_fetch_reuse") or {}
        if first_reuse.get("cache_status") == "miss":
            miss_count += 1
        if repeated_reuse.get("cache_status") == "hit":
            hit_count += 1
        rows.append(
            {
                "ticker": first.ticker,
                "first_cache_status": first_reuse.get("cache_status"),
                "repeat_cache_status": repeated_reuse.get("cache_status"),
                "repeat_age_seconds": repeated_reuse.get("age_seconds"),
                "payload_checksum_stable": lightweight_payload_checksum(first) == lightweight_payload_checksum(repeated),
                "raw_payload_exposed": bool(first.raw_payload_exposed or repeated.raw_payload_exposed),
            }
        )
    return {
        "schema_version": "lightweight-fetch-reuse-smoke-v1",
        "enabled": bool((first_responses[0].diagnostics.get("lightweight_fetch_reuse") or {}).get("enabled"))
        if first_responses
        else False,
        "first_fetch_miss_count": miss_count,
        "repeat_fetch_hit_count": hit_count,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an opt-in lightweight fresh-data fetch smoke.")
    parser.add_argument("--ticker", action="append", dest="tickers", help="Ticker to fetch; can be repeated.")
    parser.add_argument("--live", action="store_true", help="Enable live lightweight fetching for this smoke run.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    result = run_smoke(args.tickers or list(DEFAULT_TICKERS), live=args.live)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"lightweight data fetch smoke: {result['status']}")
        for response in result["responses"]:  # type: ignore[index]
            print(
                f"- {response['ticker']}: {response['fetch_state']} "
                f"({response['asset_type']}), sources={','.join(response['source_labels'])}"
            )
    return 0 if result["status"] == "pass" else 1


def _surface_contract(response) -> dict[str, object]:
    if response.fetch_state.value not in {LightweightFetchState.supported.value, LightweightFetchState.partial.value}:
        return {
            "ticker": response.ticker,
            "renderable": False,
            "reason": "fetch_state_not_renderable",
        }
    overview = build_lightweight_overview_response(response)
    details = build_lightweight_details_response(response)
    sources = build_lightweight_sources_response(response)
    return {
        "ticker": response.ticker,
        "renderable": (
            overview.state.status.value == "supported"
            and len(overview.top_risks) == 3
            and bool(overview.sections)
            and bool(overview.citations)
            and bool(sources.source_groups)
        ),
        "overview_state": overview.state.status.value,
        "asset_type": overview.asset.asset_type.value,
        "section_count": len(overview.sections),
        "top_risk_count": len(overview.top_risks),
        "citation_count": len(overview.citations),
        "source_group_count": len(sources.source_groups),
        "drawer_state": sources.drawer_state.value,
        "detail_fact_keys": sorted(details.facts.keys()),
        "weekly_news_state": overview.weekly_news_focus.state.value if overview.weekly_news_focus else "unavailable",
        "ai_analysis_available": overview.ai_comprehensive_analysis.analysis_available
        if overview.ai_comprehensive_analysis
        else False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
