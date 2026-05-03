#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.lightweight_data_fetch import fetch_lightweight_asset_data, lightweight_payload_checksum
from backend.lightweight_page import (
    build_lightweight_details_response,
    build_lightweight_overview_response,
    build_lightweight_sources_response,
)
from backend.models import LightweightFetchState
from backend.settings import build_lightweight_data_settings


DEFAULT_TICKERS = ("AAPL", "VOO")


def run_smoke(tickers: list[str], *, live: bool) -> dict[str, object]:
    env = dict(os.environ)
    if live:
        env["DATA_POLICY_MODE"] = "lightweight"
        env["LIGHTWEIGHT_LIVE_FETCH_ENABLED"] = "true"
        env.setdefault("LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED", "true")
    settings = build_lightweight_data_settings(env=env)
    responses = [fetch_lightweight_asset_data(ticker, settings=settings) for ticker in tickers]
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
        "live_fetch_enabled": settings.live_fetch_enabled,
        "settings": settings.safe_diagnostics,
        "blocked_tickers": blocked,
        "surface_contracts": surface_contracts,
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
