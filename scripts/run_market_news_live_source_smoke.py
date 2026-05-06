#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.market_news import (
    FixtureMarketNewsFetcher,
    build_market_ai_comprehensive_analysis,
    collect_market_news_candidates,
    fixture_market_news_candidates,
    market_news_provider_adapters,
    select_market_news_focus,
    serialize_market_news_candidates,
)
from backend.models import MarketNewsTopicBucket, SourceAllowlistStatus
from backend.settings import build_market_news_settings


SMOKE_SCHEMA_VERSION = "market-news-live-source-smoke-v1"
SMOKE_OPT_IN_ENV = "MARKET_NEWS_LIVE_SOURCE_SMOKE_ENABLED"
SMOKE_OPT_IN_ENV_ALT = "LTT_MARKET_NEWS_LIVE_SOURCE_SMOKE_ENABLED"
REAL_SOURCE_OPT_IN_ENV = "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED"
REAL_SOURCE_OPT_IN_ENV_ALT = "LTT_MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED"
DEFAULT_AS_OF = "2026-04-23"
DEFAULT_RETRIEVED_AT = "2026-04-23T12:00:00Z"


def run_market_news_live_source_smoke(env: dict[str, str] | None = None) -> dict[str, Any]:
    source_env = dict(os.environ if env is None else env)
    opt_in_enabled = _bool_env(source_env.get(SMOKE_OPT_IN_ENV) or source_env.get(SMOKE_OPT_IN_ENV_ALT))
    real_source_enabled = _bool_env(
        source_env.get(REAL_SOURCE_OPT_IN_ENV) or source_env.get(REAL_SOURCE_OPT_IN_ENV_ALT)
    )
    base = _base_payload(source_env, opt_in_enabled=opt_in_enabled, real_source_enabled=real_source_enabled)

    if not opt_in_enabled:
        return {
            **base,
            "status": "skipped",
            "reason_code": "market_news_live_source_smoke_opt_in_missing",
            "cases": [],
            "case_status_counts": {"pass": 0, "blocked": 0, "skipped": 1},
        }

    cases = [
        _provider_adapter_matrix_case(),
        _selection_safety_gate_case(),
        _critical_claim_gate_case(),
        _ai_threshold_case(),
    ]
    case_status_counts = Counter(str(case.get("status")) for case in cases)
    status = "blocked" if case_status_counts.get("blocked") else "pass"
    return {
        **base,
        "status": status,
        "reason_code": (
            "market_news_operator_real_source_metadata_smoke_passed"
            if real_source_enabled and status == "pass"
            else "market_news_live_source_smoke_passed"
            if status == "pass"
            else "market_news_live_source_smoke_blocked"
        ),
        "cases": cases,
        "case_status_counts": {
            "pass": int(case_status_counts.get("pass", 0)),
            "blocked": int(case_status_counts.get("blocked", 0)),
            "skipped": int(case_status_counts.get("skipped", 0)),
        },
        "operator_real_source_path": {
            "enabled": real_source_enabled,
            "metadata_only": True,
            "real_network_fetch_performed": False,
            "raw_article_text_collected": False,
            "raw_provider_payload_logged": False,
            "generated_output_cache_written": False,
        },
    }


def _base_payload(source_env: dict[str, str], *, opt_in_enabled: bool, real_source_enabled: bool) -> dict[str, Any]:
    settings = build_market_news_settings(source_env)
    return {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "status": "skipped",
        "normal_ci_requires_live_calls": False,
        "live_sources_fetched": False,
        "opt_in_env": SMOKE_OPT_IN_ENV,
        "opt_in_enabled": opt_in_enabled,
        "real_source_opt_in_env": REAL_SOURCE_OPT_IN_ENV,
        "real_source_enabled": real_source_enabled,
        "settings": settings.safe_diagnostics,
        "provider_adapter_boundary": "market-news-source-adapter-v1",
        "selection_boundary": "market-news-selection-v1",
        "response_boundary": "market-news-response-v1",
    }


def _provider_adapter_matrix_case() -> dict[str, Any]:
    settings = build_market_news_settings(
        {
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKETAUX_API_KEY": "configured",
            "ALPHA_VANTAGE_API_KEY": "configured",
            "FINNHUB_API_KEY": "configured",
            "GUARDIAN_API_KEY": "configured",
            "GNEWS_API_KEY": "configured",
            "MEDIASTACK_API_KEY": "configured",
            "NEWSAPI_API_KEY": "configured",
        }
    )
    candidates = collect_market_news_candidates(
        fetcher=FixtureMarketNewsFetcher(payloads_by_provider=_provider_payloads()),
        settings=settings,
        as_of=DEFAULT_AS_OF,
        retrieved_at=DEFAULT_RETRIEVED_AT,
    )
    focus = select_market_news_focus(candidates, as_of=DEFAULT_AS_OF)
    providers = sorted({candidate.provider for candidate in candidates})
    required_providers = sorted(adapter.provider for adapter in market_news_provider_adapters())
    serialized = serialize_market_news_candidates(candidates)
    blocked_tokens = ["configured", "Authorization", "Bearer ", "raw article body", "provider payload value"]
    return {
        "case_id": "provider_adapter_matrix",
        "status": "pass" if set(required_providers) <= set(providers) and not any(token in serialized for token in blocked_tokens) else "blocked",
        "provider_count": len(providers),
        "providers": providers,
        "required_providers": required_providers,
        "candidate_count": len(candidates),
        "selected_item_count": focus.selected_item_count,
        "raw_article_text_reported": False,
        "raw_provider_payload_logged": False,
        "sanitized_serialization": True,
    }


def _selection_safety_gate_case() -> dict[str, Any]:
    candidates = fixture_market_news_candidates(as_of=DEFAULT_AS_OF, retrieved_at=DEFAULT_RETRIEVED_AT)
    blocked = candidates[0].__class__(
        **{
            **candidates[0].__dict__,
            "article_id": "blocked_non_allowlisted",
            "source": "Unreviewed Blog",
            "source_domain": "example.com",
            "allowlist_status": SourceAllowlistStatus.not_allowlisted,
            "source_priority": 99,
        }
    )
    focus = select_market_news_focus([*candidates, blocked], as_of=DEFAULT_AS_OF)
    return {
        "case_id": "selection_safety_gates",
        "status": "pass" if focus.selected_item_count <= 20 and focus.suppressed_candidate_count >= 1 else "blocked",
        "selected_item_count": focus.selected_item_count,
        "suppressed_candidate_count": focus.suppressed_candidate_count,
        "no_raw_article_text": focus.audit.no_raw_article_text,
        "no_generated_output_cache_write": focus.audit.no_generated_output_cache_write,
    }


def _critical_claim_gate_case() -> dict[str, Any]:
    weak = fixture_market_news_candidates(as_of=DEFAULT_AS_OF, retrieved_at=DEFAULT_RETRIEVED_AT)[0].__class__(
        **{
            **fixture_market_news_candidates(as_of=DEFAULT_AS_OF, retrieved_at=DEFAULT_RETRIEVED_AT)[0].__dict__,
            "article_id": "weak_critical_claim",
            "source": "CNBC",
            "source_domain": "cnbc.com",
            "source_priority": 8,
            "title": "Fed rate stress hits markets",
            "description": "A critical policy claim without priority-source corroboration.",
        }
    )
    focus = select_market_news_focus([weak], as_of=DEFAULT_AS_OF)
    return {
        "case_id": "critical_claim_gate",
        "status": "pass" if focus.selected_item_count == 0 else "blocked",
        "selected_item_count": focus.selected_item_count,
        "critical_claim_requires_priority_or_corroboration": True,
    }


def _ai_threshold_case() -> dict[str, Any]:
    focus = select_market_news_focus(
        fixture_market_news_candidates(as_of=DEFAULT_AS_OF, retrieved_at=DEFAULT_RETRIEVED_AT)[:2],
        as_of=DEFAULT_AS_OF,
    )
    analysis = build_market_ai_comprehensive_analysis(focus)
    return {
        "case_id": "ai_threshold",
        "status": "pass" if not analysis.analysis_available and analysis.state.value == "suppressed" else "blocked",
        "analysis_available": analysis.analysis_available,
        "minimum_market_news_item_count": analysis.minimum_market_news_item_count,
        "selected_topic_bucket_count": analysis.selected_topic_bucket_count,
    }


def _provider_payloads() -> dict[str, Any]:
    epoch = int(datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc).timestamp())
    rss = """
    <rss><channel><item>
      <title>Reuters market update from RSS</title>
      <link>https://www.reuters.com/markets/rss-market-update</link>
      <description>Reuters reported a market update from RSS metadata.</description>
      <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
      <source>Reuters</source>
    </item></channel></rss>
    """
    return {
        "rss": rss,
        "google_news_rss": rss,
        "gdelt": {
            "articles": [
                {
                    "title": "Reuters GDELT market update",
                    "url": "https://www.reuters.com/markets/gdelt-market-update",
                    "seendate": "20260422T120000Z",
                    "sourceCommonName": "Reuters",
                }
            ]
        },
        "marketaux": {
            "data": [
                {
                    "title": "Reuters Marketaux market update",
                    "description": "Reuters reported market context through Marketaux metadata.",
                    "url": "https://www.reuters.com/markets/marketaux-market-update",
                    "published_at": "2026-04-22T12:00:00Z",
                    "source": "Reuters",
                    "entities": [{"name": "Federal Reserve"}],
                }
            ]
        },
        "alpha_vantage": {
            "feed": [
                {
                    "title": "Reuters Alpha Vantage market update",
                    "summary": "Reuters reported market context through Alpha Vantage metadata.",
                    "url": "https://www.reuters.com/markets/alpha-market-update",
                    "time_published": "20260422T120000",
                    "source": "Reuters",
                    "ticker_sentiment": [{"ticker": "SPY"}],
                }
            ]
        },
        "finnhub": [
            {
                "headline": "Reuters Finnhub market update",
                "summary": "Reuters reported market context through Finnhub metadata.",
                "url": "https://www.reuters.com/markets/finnhub-market-update",
                "datetime": epoch,
                "source": "Reuters",
            }
        ],
        "guardian": {
            "response": {
                "results": [
                    {
                        "webTitle": "Guardian market update",
                        "webUrl": "https://www.theguardian.com/business/2026/apr/22/market-update",
                        "webPublicationDate": "2026-04-22T12:00:00Z",
                        "fields": {"trailText": "The Guardian reported global market context."},
                    }
                ]
            }
        },
        "gnews": {
            "articles": [
                {
                    "title": "Reuters GNews market update",
                    "description": "Reuters reported market context through GNews metadata.",
                    "url": "https://www.reuters.com/markets/gnews-market-update",
                    "publishedAt": "2026-04-22T12:00:00Z",
                    "source": {"name": "Reuters"},
                }
            ]
        },
        "mediastack": {
            "data": [
                {
                    "title": "Reuters Mediastack market update",
                    "description": "Reuters reported market context through Mediastack metadata.",
                    "url": "https://www.reuters.com/markets/mediastack-market-update",
                    "published_at": "2026-04-22T12:00:00Z",
                    "source": "Reuters",
                }
            ]
        },
        "newsapi": {
            "articles": [
                {
                    "title": "Reuters NewsAPI market update",
                    "description": "Reuters reported market context through NewsAPI metadata.",
                    "url": "https://www.reuters.com/markets/newsapi-market-update",
                    "publishedAt": "2026-04-22T12:00:00Z",
                    "source": {"name": "Reuters"},
                }
            ]
        },
        "yahoo_finance_search": {
            "news": [
                {
                    "title": "Reuters Yahoo Finance market update",
                    "summary": "Reuters reported market context through Yahoo metadata.",
                    "link": "https://www.reuters.com/markets/yahoo-market-update",
                    "providerPublishTime": epoch,
                    "publisher": "Reuters",
                    "relatedTickers": ["SPY"],
                }
            ]
        },
    }


def _bool_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the optional Market News Focus live-source smoke.")
    parser.add_argument("--json", action="store_true", help="Print the smoke payload as JSON.")
    args = parser.parse_args()
    result = run_market_news_live_source_smoke()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['reason_code']}")


if __name__ == "__main__":
    main()
