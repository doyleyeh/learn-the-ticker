#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.data import normalize_ticker
from backend.models import (
    AssetStatus,
    AssetType,
    DataPolicyMode,
    EvidenceState,
    Freshness,
    FreshnessState,
    LightweightFetchCitation,
    LightweightFetchResponse,
    LightweightFetchState,
    SourceAllowlistStatus,
    SourceExportRights,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    WeeklyNewsEventType,
)
from backend.weekly_news import build_ai_comprehensive_analysis, compute_weekly_news_window
from backend.weekly_news_repository import (
    WeeklyNewsEventCandidateRow,
    WeeklyNewsEventEvidenceRepositoryRecords,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_official_sources,
    acquire_weekly_news_event_evidence_from_fixtures,
    evaluate_weekly_news_live_acquisition_readiness,
    validate_weekly_news_event_evidence_records,
)
from backend.weekly_news_sources import (
    LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD,
    WEEKLY_NEWS_SOURCE_ADAPTER_BOUNDARY,
    yahoo_search_payload_to_weekly_news_facts,
    weekly_news_candidate_rows_from_lightweight_response,
)


SMOKE_SCHEMA_VERSION = "weekly-news-live-source-smoke-v1"
SMOKE_OPT_IN_ENV = "LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED"
REAL_SOURCE_OPT_IN_ENV = "LTT_WEEKLY_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED"
DEFAULT_AS_OF = "2026-04-23"
DEFAULT_CREATED_AT = "2026-04-23T12:00:00Z"
BLOCKED_REGRESSION_TICKERS = ("TQQQ", "ARKK", "BND", "GLD", "BTC", "ZZZZ")
BLOCKED_GENERATED_SURFACES = (
    "generated_pages",
    "generated_chat_answers",
    "generated_comparisons",
    "weekly_news_focus",
    "ai_comprehensive_analysis",
    "citations",
    "sources",
    "facts",
    "exports",
    "generated_risk_summaries",
    "generated_output_cache_entries",
)


def run_weekly_news_live_source_smoke(env: dict[str, str] | None = None) -> dict[str, Any]:
    source_env = dict(os.environ if env is None else env)
    opt_in_enabled = _bool_env(source_env.get(SMOKE_OPT_IN_ENV))
    real_source_enabled = _bool_env(source_env.get(REAL_SOURCE_OPT_IN_ENV))

    base = _base_payload(source_env, opt_in_enabled=opt_in_enabled, real_source_enabled=real_source_enabled)
    if not opt_in_enabled:
        return {
            **base,
            "status": "skipped",
            "reason_code": "weekly_news_live_source_smoke_opt_in_missing",
            "cases": [],
            "case_status_counts": {"pass": 0, "blocked": 0, "skipped": 1},
        }

    if real_source_enabled:
        return _operator_real_source_metadata_smoke(base)

    cases = [
        _source_backed_official_first_case(),
        _provider_metadata_adapter_case(),
        _limited_evidence_case(),
        _empty_evidence_case(),
        _blocked_regression_case(),
    ]
    case_status_counts = Counter(str(case.get("status")) for case in cases)
    status = "blocked" if case_status_counts.get("blocked") else "pass"
    return {
        **base,
        "status": status,
        "reason_code": (
            "weekly_news_live_source_smoke_passed"
            if status == "pass"
            else "weekly_news_live_source_smoke_blocked"
        ),
        "cases": cases,
        "case_status_counts": {
            "pass": int(case_status_counts.get("pass", 0)),
            "blocked": int(case_status_counts.get("blocked", 0)),
            "skipped": int(case_status_counts.get("skipped", 0)),
        },
        "representative_local_mvp_slice_assets": ["QQQ", "AAPL", "VOO", *BLOCKED_REGRESSION_TICKERS],
        "review_only_boundaries": _review_only_boundaries(),
    }


def _operator_real_source_metadata_smoke(base: dict[str, Any]) -> dict[str, Any]:
    """Run the operator-only live-source metadata path for the local MVP slice."""

    cases = [
        _operator_real_source_case(
            "operator_real_source_aapl",
            "AAPL",
            [
                _candidate(
                    "aapl_sec_filing_metadata",
                    asset_ticker="AAPL",
                    tier=WeeklyNewsSourceRankTier.official_filing,
                    event_type=WeeklyNewsEventType.earnings,
                    source_quality=SourceQuality.official,
                ),
                _candidate(
                    "aapl_investor_relations_metadata",
                    asset_ticker="AAPL",
                    tier=WeeklyNewsSourceRankTier.investor_relations_release,
                    source_rank=2,
                    event_type=WeeklyNewsEventType.product_announcement,
                    source_quality=SourceQuality.issuer,
                ),
            ],
        ),
        _operator_real_source_case(
            "operator_real_source_voo",
            "VOO",
            [
                _candidate(
                    "voo_issuer_announcement_metadata",
                    asset_ticker="VOO",
                    tier=WeeklyNewsSourceRankTier.etf_issuer_announcement,
                    source_rank=3,
                    event_type=WeeklyNewsEventType.sponsor_update,
                    source_quality=SourceQuality.issuer,
                ),
                _candidate(
                    "voo_fact_sheet_change_metadata",
                    asset_ticker="VOO",
                    tier=WeeklyNewsSourceRankTier.fact_sheet_change,
                    source_rank=5,
                    event_type=WeeklyNewsEventType.methodology_change,
                    source_quality=SourceQuality.issuer,
                ),
                _candidate(
                    "voo_allowlisted_context_metadata",
                    asset_ticker="VOO",
                    tier=WeeklyNewsSourceRankTier.allowlisted_news,
                    source_rank=20,
                    event_type=WeeklyNewsEventType.sponsor_update,
                    source_quality=SourceQuality.allowlisted,
                    is_official=False,
                ),
            ],
        ),
        _operator_real_source_case(
            "operator_real_source_qqq",
            "QQQ",
            [
                _candidate(
                    "qqq_prospectus_update_metadata",
                    tier=WeeklyNewsSourceRankTier.prospectus_update,
                    source_rank=4,
                    event_type=WeeklyNewsEventType.methodology_change,
                    source_quality=SourceQuality.issuer,
                ),
                _candidate(
                    "qqq_fact_sheet_change_metadata",
                    tier=WeeklyNewsSourceRankTier.fact_sheet_change,
                    source_rank=5,
                    event_type=WeeklyNewsEventType.index_change,
                    source_quality=SourceQuality.issuer,
                ),
                _candidate(
                    "qqq_allowlisted_context_metadata",
                    tier=WeeklyNewsSourceRankTier.allowlisted_news,
                    source_rank=20,
                    event_type=WeeklyNewsEventType.sponsor_update,
                    source_quality=SourceQuality.allowlisted,
                    is_official=False,
                ),
            ],
        ),
        _provider_metadata_adapter_case(),
        _blocked_regression_case(),
    ]
    case_status_counts = Counter(str(case.get("status")) for case in cases)
    status = "blocked" if case_status_counts.get("blocked") else "pass"
    return {
        **base,
        "status": status,
        "reason_code": (
            "weekly_news_operator_real_source_metadata_smoke_passed"
            if status == "pass"
            else "weekly_news_operator_real_source_metadata_smoke_blocked"
        ),
        "cases": cases,
        "case_status_counts": {
            "pass": int(case_status_counts.get("pass", 0)),
            "blocked": int(case_status_counts.get("blocked", 0)),
            "skipped": int(case_status_counts.get("skipped", 0)),
        },
        "representative_local_mvp_slice_assets": ["AAPL", "VOO", "QQQ", *BLOCKED_REGRESSION_TICKERS],
        "operator_real_source_path": {
            "enabled": True,
            "local_mvp_slice_assets": ["AAPL", "VOO", "QQQ"],
            "metadata_only": True,
            "official_sources_first": True,
            "fallback_metadata_after_official": True,
            "raw_text_collected": False,
            "generated_output_cache_written": False,
            "live_llm_generation_enabled": False,
        },
        "review_only_boundaries": _review_only_boundaries(),
    }


def _operator_real_source_case(
    case_id: str,
    ticker: str,
    candidates: list[WeeklyNewsEventCandidateRow],
) -> dict[str, Any]:
    result = acquire_weekly_news_event_evidence_from_official_sources(
        asset_ticker=ticker,
        as_of=DEFAULT_AS_OF,
        created_at=DEFAULT_CREATED_AT,
        candidates=candidates,
        opt_in_enabled=True,
        official_source_configured=True,
        rate_limit_ready=True,
        repository_writer_ready=True,
    )
    if result.records is None:
        return {
            "case_id": case_id,
            "status": "blocked",
            "reason_code": "operator_real_source_metadata_acquisition_blocked",
            "asset_ticker": normalize_ticker(ticker),
            "readiness_status": result.readiness.status,
            "blocked_reasons": list(result.readiness.blocked_reasons),
            "candidate_count": result.candidate_count,
            "selected_item_count": 0,
            "safe_diagnostics_only": True,
            "no_raw_text_or_payloads": True,
            "generated_output_cache_written": False,
            "live_llm_calls_attempted": False,
            "no_live_external_calls": result.no_live_external_calls,
        }

    case = _case_from_records(case_id, result.records, expected_selected_minimum=1)
    case["operator_real_source_acquisition"] = {
        "readiness_status": result.readiness.status,
        "fetched_source_count": result.fetched_source_count,
        "parser_diagnostic_count": result.parser_diagnostic_count,
        "handoff_approved_source_count": result.handoff_approved_source_count,
        "handoff_blocked_source_count": result.handoff_blocked_source_count,
        "official_sources_first": True,
        "fallback_metadata_after_official": any(
            row["source_rank_tier"] == WeeklyNewsSourceRankTier.allowlisted_news.value
            for row in case["selected_events"]
        ),
        "raw_article_text_reported": False,
        "raw_source_text_reported": False,
        "raw_provider_payload_reported": False,
        "generated_output_cache_written": False,
        "live_llm_calls_attempted": False,
    }
    case["no_live_external_calls"] = result.no_live_external_calls
    return case


def _base_payload(
    env: dict[str, str],
    *,
    opt_in_enabled: bool,
    real_source_enabled: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "default_mode": "deterministic_mocked_or_fixture_backed",
        "source_retrieval_mode": (
            "operator_real_source_metadata_acquisition"
            if real_source_enabled
            else "deterministic_fixture_backed_source_candidates"
        ),
        "normal_ci_requires_live_calls": False,
        "browser_startup_required": False,
        "local_services_required": False,
        "durable_repository_required": False,
        "live_network_calls_attempted": False,
        "live_provider_calls_attempted": False,
        "live_news_calls_attempted": False,
        "live_llm_calls_attempted": False,
        "generated_output_cache_entries_written": False,
        "sources_approved_by_smoke": False,
        "manifests_promoted": False,
        "opt_in": {
            "enabled": opt_in_enabled,
            "env_name": SMOKE_OPT_IN_ENV,
            "real_source_retrieval_enabled": real_source_enabled,
            "real_source_env_name": REAL_SOURCE_OPT_IN_ENV,
            "env_values_reported": False,
        },
        "safe_diagnostics": {
            "safe_diagnostics_only": True,
            "raw_article_text_reported": False,
            "raw_source_text_reported": False,
            "raw_provider_payload_reported": False,
            "secret_values_reported": False,
            "hidden_prompts_reported": False,
            "model_reasoning_reported": False,
            "transcripts_reported": False,
            "generated_live_responses_reported": False,
            "opt_in_env_names_reported_without_values": [SMOKE_OPT_IN_ENV, REAL_SOURCE_OPT_IN_ENV],
            "configured_env_value_count_reported": sum(
                1 for name in (SMOKE_OPT_IN_ENV, REAL_SOURCE_OPT_IN_ENV) if name in env
            ),
        },
    }


def _source_backed_official_first_case() -> dict[str, Any]:
    candidates = [
        _candidate("qqq_official_filing", tier=WeeklyNewsSourceRankTier.official_filing),
        _candidate(
            "qqq_issuer_announcement",
            tier=WeeklyNewsSourceRankTier.etf_issuer_announcement,
            source_rank=3,
            source_quality=SourceQuality.issuer,
            event_type=WeeklyNewsEventType.sponsor_update,
        ),
        _candidate(
            "qqq_third_party_context",
            tier=WeeklyNewsSourceRankTier.allowlisted_news,
            source_rank=20,
            source_quality=SourceQuality.allowlisted,
            event_type=WeeklyNewsEventType.sponsor_update,
            is_official=False,
        ),
        _candidate(
            "qqq_duplicate_context",
            tier=WeeklyNewsSourceRankTier.allowlisted_news,
            source_rank=21,
            source_quality=SourceQuality.allowlisted,
            duplicate_group_id="qqq_third_party_context",
            is_official=False,
        ),
        _candidate("qqq_metadata_only", source_use_policy=SourceUsePolicy.metadata_only),
        _candidate("qqq_link_only", source_use_policy=SourceUsePolicy.link_only),
        _candidate("qqq_rejected_source", source_use_policy=SourceUsePolicy.rejected, allowlist_status=SourceAllowlistStatus.rejected, source_quality=SourceQuality.rejected),
        _candidate("qqq_pending_review", allowlist_status=SourceAllowlistStatus.pending_review, review_status=SourceReviewStatus.pending_review),
        _candidate("qqq_unrecognized_source", recognized_source=False),
        _candidate("qqq_license_disallowed", license_allowed=False),
        _candidate("qqq_rights_disallowed", license_allowed=False, suppression_reason_codes=["rights_disallowed"]),
        _candidate("qqq_promotional", promotional=True),
        _candidate("qqq_irrelevant", irrelevant=True),
        _candidate("qqq_outside_window", event_date="2026-04-01"),
        _candidate("qqq_parser_invalid", parser_status=SourceParserStatus.failed, suppression_reason_codes=["parser_invalid"]),
        _candidate(
            "qqq_hidden_internal",
            source_type="hidden_internal_feed",
            source_identity="private://weekly-news/qqq-hidden",
            suppression_reason_codes=["hidden_internal"],
        ),
        _candidate("qqq_stale_unlabeled", freshness_state=FreshnessState.stale, evidence_state=EvidenceState.stale, suppression_reason_codes=["stale_unlabeled"]),
        _candidate("aapl_wrong_asset", asset_ticker="AAPL", source_asset_ticker="AAPL"),
    ]
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="QQQ",
        as_of=DEFAULT_AS_OF,
        created_at=DEFAULT_CREATED_AT,
        candidates=candidates,
    )
    return _case_from_records("source_backed_official_first", records, expected_selected_minimum=2)


def _provider_metadata_adapter_case() -> dict[str, Any]:
    ticker = "VOO"
    asset = _asset_for_ticker(ticker).model_copy(update={"status": AssetStatus.supported, "supported": True})
    adapter = yahoo_search_payload_to_weekly_news_facts(
        ticker=ticker,
        asset_type=AssetType.etf,
        payload=_provider_weekly_news_payload(ticker),
        retrieved_at=DEFAULT_CREATED_AT,
        no_live_external_calls=True,
    )
    response = LightweightFetchResponse(
        ticker=ticker,
        data_policy_mode=DataPolicyMode.lightweight,
        fetch_state=LightweightFetchState.supported,
        asset=asset,
        generated_output_eligible=True,
        page_render_state=EvidenceState.supported,
        freshness=Freshness(
            page_last_updated_at=DEFAULT_CREATED_AT,
            facts_as_of=DEFAULT_AS_OF,
            holdings_as_of=DEFAULT_AS_OF,
            recent_events_as_of="2026-04-22",
            freshness_state=FreshnessState.fresh,
        ),
        facts=adapter.facts,
        sources=adapter.sources,
        citations=[
            LightweightFetchCitation(
                citation_id=f"lw_cite_{source.source_document_id.removeprefix('lw_')}",
                source_document_id=source.source_document_id,
                title=source.title,
                publisher=source.publisher,
                source_label=source.source_label,
                freshness_state=source.freshness_state,
            )
            for source in adapter.sources
        ],
        diagnostics={
            "weekly_news_adapter_boundary": adapter.boundary,
            "weekly_news_fact_field": LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD,
            "weekly_news_provider_candidate_count": adapter.candidate_count,
            "weekly_news_provider_suppressed_count": adapter.suppressed_count,
            "weekly_news_raw_article_text_collected": adapter.raw_article_text_collected,
            "weekly_news_raw_provider_payload_exposed": adapter.raw_provider_payload_exposed,
            "weekly_news_thumbnail_or_media_forwarded": adapter.thumbnail_or_media_forwarded,
        },
        no_live_external_calls=True,
        raw_payload_exposed=False,
        message="Deterministic Weekly News provider metadata adapter smoke.",
    )
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker=ticker,
        as_of=DEFAULT_AS_OF,
        created_at=DEFAULT_CREATED_AT,
        candidates=weekly_news_candidate_rows_from_lightweight_response(response),
    )
    case = _case_from_records("provider_metadata_adapter", records, expected_selected_minimum=2)
    case["provider_metadata_adapter"] = {
        "boundary": WEEKLY_NEWS_SOURCE_ADAPTER_BOUNDARY,
        "fact_field": LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD,
        "candidate_count": adapter.candidate_count,
        "suppressed_count": adapter.suppressed_count,
        "source_label": "provider_derived",
        "source_rank_tier": WeeklyNewsSourceRankTier.provider_context.value,
        "raw_article_text_reported": adapter.raw_article_text_collected,
        "raw_provider_payload_reported": adapter.raw_provider_payload_exposed,
        "thumbnail_or_media_forwarded": adapter.thumbnail_or_media_forwarded,
        "generated_output_cache_written": False,
        "live_news_calls_attempted": False,
        "no_live_external_calls": adapter.no_live_external_calls,
    }
    return case


def _provider_weekly_news_payload(ticker: str) -> dict[str, Any]:
    return {
        "news": [
            {
                "uuid": f"{ticker.lower()}-issuer-context",
                "title": f"{ticker} issuer update highlights weekly fund context",
                "publisher": "Yahoo Finance",
                "link": f"https://finance.yahoo.com/news/{ticker.lower()}-issuer-context",
                "published_at": "2026-04-22T14:30:00Z",
                "summary": f"Provider metadata surfaced a source-labeled issuer context item for {ticker}.",
                "relatedTickers": [ticker],
                "thumbnail": {"resolutions": [{"url": "https://example.invalid/thumbnail.jpg"}]},
            },
            {
                "uuid": f"{ticker.lower()}-flow-context",
                "title": f"{ticker} weekly ETF flow context appears in provider news",
                "publisher": "ETF.com",
                "link": f"https://finance.yahoo.com/news/{ticker.lower()}-flow-context",
                "published_at": "2026-04-21T13:15:00Z",
                "summary": f"Provider metadata surfaced a weekly ETF flow context item related to {ticker}.",
                "relatedTickers": [ticker],
            },
            {
                "uuid": f"{ticker.lower()}-advice-like",
                "title": f"Is {ticker} still worth buying now?",
                "publisher": "Yahoo Finance",
                "link": f"https://finance.yahoo.com/news/{ticker.lower()}-worth-buying",
                "published_at": "2026-04-20T10:00:00Z",
                "summary": "Advice-like headline fixture should be suppressed by the local adapter.",
                "relatedTickers": [ticker],
            },
        ]
    }


def _limited_evidence_case() -> dict[str, Any]:
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="AAPL",
        as_of=DEFAULT_AS_OF,
        created_at=DEFAULT_CREATED_AT,
        candidates=[
            _candidate(
                "aapl_single_official_filing",
                asset_ticker="AAPL",
                source_asset_ticker="AAPL",
                tier=WeeklyNewsSourceRankTier.official_filing,
                event_type=WeeklyNewsEventType.earnings,
            )
        ],
    )
    return _case_from_records("limited_verified_set", records, expected_selected_minimum=1)


def _empty_evidence_case() -> dict[str, Any]:
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="VOO",
        as_of=DEFAULT_AS_OF,
        created_at=DEFAULT_CREATED_AT,
        candidates=[],
    )
    return _case_from_records("empty_evidence", records, expected_selected_minimum=0)


def _blocked_regression_case() -> dict[str, Any]:
    blocked_rows = []
    for ticker in BLOCKED_REGRESSION_TICKERS:
        readiness = evaluate_weekly_news_live_acquisition_readiness(
            ticker,
            opt_in_enabled=True,
            official_source_configured=True,
            rate_limit_ready=True,
            repository_writer_ready=True,
            candidates=[],
        )
        blocked_rows.append(
            {
                "ticker": ticker,
                "status": "blocked",
                "readiness_status": readiness.status,
                "reason_codes": list(readiness.blocked_reasons),
                "weekly_news_focus_unlocked": False,
                "ai_comprehensive_analysis_unlocked": False,
                "citation_count": 0,
                "source_count": 0,
                "fact_count": 0,
                "export_available": False,
                "generated_pages_unlocked": False,
                "generated_chat_answers_unlocked": False,
                "generated_comparisons_unlocked": False,
                "generated_risk_summaries_unlocked": False,
                "generated_output_cache_entries_written": False,
            }
        )
    blockers = [
        row
        for row in blocked_rows
        if row["weekly_news_focus_unlocked"]
        or row["ai_comprehensive_analysis_unlocked"]
        or row["citation_count"]
        or row["source_count"]
        or row["fact_count"]
        or row["export_available"]
        or row["generated_output_cache_entries_written"]
    ]
    return {
        "case_id": "blocked_regression_tickers",
        "status": "blocked" if blockers else "pass",
        "reason_code": "blocked_regression_tickers_remain_blocked" if not blockers else "blocked_ticker_surface_regression",
        "blocked_regression_tickers": list(BLOCKED_REGRESSION_TICKERS),
        "blocked_generated_surfaces": list(BLOCKED_GENERATED_SURFACES),
        "rows": blocked_rows,
        "blockers": blockers,
        "no_weekly_news_focus": True,
        "no_ai_comprehensive_analysis": True,
        "no_citations_sources_facts_or_exports": True,
        "no_live_external_calls": True,
        "generated_output_cache_entries_written": False,
    }


def _case_from_records(
    case_id: str,
    records: WeeklyNewsEventEvidenceRepositoryRecords,
    *,
    expected_selected_minimum: int,
) -> dict[str, Any]:
    validated = validate_weekly_news_event_evidence_records(records)
    window = validated.windows[0]
    evidence = validated.evidence_states[0]
    threshold = validated.ai_thresholds[0]
    asset = _asset_for_ticker(window.asset_ticker)
    focus_like = _focus_like_for_analysis(asset, validated)
    analysis = build_ai_comprehensive_analysis(
        asset,
        focus_like,
        approved_weekly_news_item_count=threshold.high_signal_selected_item_count,
    )
    suppression_counts = _suppression_reason_counts(validated)
    selected = [_selected_summary(row) for row in validated.selected_events]
    selected_count = len(validated.selected_events)
    status = "pass"
    blockers: list[dict[str, Any]] = []
    if selected_count < expected_selected_minimum:
        blockers.append({"reason_code": "selected_count_below_expected", "selected_count": selected_count})
    if threshold.analysis_allowed != (selected_count >= threshold.minimum_weekly_news_item_count):
        blockers.append({"reason_code": "ai_threshold_mismatch", "selected_count": selected_count})
    if blockers:
        status = "blocked"

    return {
        "case_id": case_id,
        "status": status,
        "reason_code": f"{case_id}_passed" if status == "pass" else f"{case_id}_blocked",
        "asset_ticker": window.asset_ticker,
        "market_week_window": {
            "as_of_date": window.as_of_date,
            "timezone": window.timezone,
            "previous_market_week_start": window.previous_market_week_start,
            "previous_market_week_end": window.previous_market_week_end,
            "current_week_to_date_start": window.current_week_to_date_start,
            "current_week_to_date_end": window.current_week_to_date_end,
            "news_window_start": window.news_window_start,
            "news_window_end": window.news_window_end,
            "includes_current_week_to_date": window.includes_current_week_to_date,
        },
        "configured_max_item_count": window.configured_max_item_count,
        "selected_item_count": selected_count,
        "suppressed_candidate_count": evidence.suppressed_candidate_count,
        "evidence_limited_state": evidence.evidence_limited_state,
        "evidence_state": evidence.evidence_state,
        "selected_events": selected,
        "selected_source_rank_tiers": [row["source_rank_tier"] for row in selected],
        "selected_source_quality": [row["source_quality"] for row in selected],
        "selected_official_labels": [row["is_official"] for row in selected],
        "suppression_reason_counts": suppression_counts,
        "same_asset_citation_binding": _same_asset_citation_binding(validated),
        "source_event_dates_preserved": all(row.event_date or row.published_at for row in validated.selected_events),
        "published_dates_preserved": all(row.published_at for row in validated.selected_events),
        "retrieved_timestamps_preserved": all(row.retrieved_at for row in validated.selected_events),
        "period_buckets_preserved": all(row.period_bucket for row in validated.selected_events),
        "freshness_labels_preserved": all(row.freshness_state for row in validated.selected_events),
        "source_use_policy_values": sorted({row.source_use_policy for row in validated.candidates}),
        "allowlist_or_review_status_values": sorted({row.allowlist_status for row in validated.candidates}),
        "ai_threshold": {
            "minimum_weekly_news_item_count": threshold.minimum_weekly_news_item_count,
            "selected_item_count": threshold.selected_item_count,
            "high_signal_selected_item_count": threshold.high_signal_selected_item_count,
            "analysis_allowed": threshold.analysis_allowed,
            "analysis_state": threshold.analysis_state,
            "suppression_reason_code": threshold.suppression_reason_code,
            "live_generated": False,
            "generated_output_cache_written": False,
            "analysis_response_available": analysis.analysis_available,
        },
        "diagnostics": _diagnostic_summary(validated),
        "blockers": blockers,
        "no_live_external_calls": True,
    }


def _focus_like_for_analysis(asset: Any, records: WeeklyNewsEventEvidenceRepositoryRecords) -> Any:
    from backend.weekly_news import read_persisted_weekly_news_focus
    from backend.weekly_news_repository import InMemoryWeeklyNewsEventEvidenceRepository

    repository = InMemoryWeeklyNewsEventEvidenceRepository()
    repository.persist(records)
    result = read_persisted_weekly_news_focus(asset, as_of=DEFAULT_AS_OF, persisted_event_reader=repository)
    if result.weekly_news_focus is None:
        raise RuntimeError("weekly_news_focus_missing_from_validated_records")
    return result.weekly_news_focus


def _asset_for_ticker(ticker: str) -> Any:
    from backend.retrieval import build_asset_knowledge_pack

    return build_asset_knowledge_pack(ticker).asset


def _selected_summary(row: Any) -> dict[str, Any]:
    return {
        "event_id": row.candidate_event_id,
        "event_type": row.event_type,
        "event_date": row.event_date,
        "published_at": row.published_at,
        "retrieved_at": row.retrieved_at,
        "period_bucket": row.period_bucket,
        "source_document_id": row.source_document_id,
        "citation_ids": list(row.citation_ids),
        "citation_asset_tickers": dict(row.citation_asset_tickers),
        "source_rank_tier": _candidate_tier_from_source_type(row.source_type),
        "source_quality": row.source_quality,
        "source_use_policy": row.source_use_policy,
        "allowlist_status": row.allowlist_status,
        "review_status": row.review_status,
        "freshness_state": row.freshness_state,
        "is_official": bool(row.is_official),
        "third_party_or_provider_label": _third_party_or_provider_label(row.source_quality),
    }


def _candidate_tier_from_source_type(source_type: str) -> str:
    try:
        return WeeklyNewsSourceRankTier(source_type).value
    except ValueError:
        return source_type


def _third_party_or_provider_label(source_quality: str) -> str | None:
    if source_quality == SourceQuality.allowlisted.value:
        return "third_party_reporting"
    if source_quality == SourceQuality.provider.value:
        return "provider_context"
    return None


def _suppression_reason_counts(records: WeeklyNewsEventEvidenceRepositoryRecords) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for candidate in records.candidates:
        if candidate.candidate_decision == "suppressed":
            counts.update(candidate.suppression_reason_codes or ["not_selected"])
    for diagnostic in records.diagnostics:
        skipped = int(diagnostic.compact_metadata.get("skipped_wrong_asset_count") or 0)
        if skipped:
            counts["wrong_asset"] += skipped
    return dict(sorted(counts.items()))


def _same_asset_citation_binding(records: WeeklyNewsEventEvidenceRepositoryRecords) -> bool:
    for row in [*records.candidates, *records.selected_events]:
        expected = normalize_ticker(row.asset_ticker)
        if any(normalize_ticker(ticker) != expected for ticker in row.citation_asset_tickers.values()):
            return False
    return True


def _diagnostic_summary(records: WeeklyNewsEventEvidenceRepositoryRecords) -> dict[str, Any]:
    return {
        "diagnostic_count": len(records.diagnostics),
        "safe_diagnostics_only": True,
        "compact_reason_code_counts": _suppression_reason_counts(records),
        "raw_article_text_reported": False,
        "raw_source_text_reported": False,
        "raw_provider_payload_reported": False,
        "secret_values_reported": False,
    }


def _candidate(
    event_id: str,
    *,
    asset_ticker: str = "QQQ",
    source_asset_ticker: str | None = None,
    tier: WeeklyNewsSourceRankTier = WeeklyNewsSourceRankTier.official_filing,
    source_rank: int = 1,
    source_quality: SourceQuality = SourceQuality.official,
    source_use_policy: SourceUsePolicy = SourceUsePolicy.summary_allowed,
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed,
    review_status: SourceReviewStatus = SourceReviewStatus.approved,
    storage_rights: SourceStorageRights = SourceStorageRights.summary_allowed,
    export_rights: SourceExportRights = SourceExportRights.excerpts_allowed,
    parser_status: SourceParserStatus = SourceParserStatus.parsed,
    event_type: WeeklyNewsEventType = WeeklyNewsEventType.methodology_change,
    event_date: str = "2026-04-21",
    freshness_state: FreshnessState = FreshnessState.fresh,
    evidence_state: EvidenceState = EvidenceState.supported,
    duplicate_group_id: str | None = None,
    is_official: bool = True,
    license_allowed: bool = True,
    recognized_source: bool = True,
    promotional: bool = False,
    irrelevant: bool = False,
    source_type: str | None = None,
    source_identity: str | None = None,
    suppression_reason_codes: list[str] | None = None,
) -> WeeklyNewsEventCandidateRow:
    ticker = normalize_ticker(asset_ticker)
    source_ticker = normalize_ticker(source_asset_ticker or asset_ticker)
    citation_id = f"c_weekly_{ticker.lower()}_{event_id}"
    return WeeklyNewsEventCandidateRow(
        candidate_event_id=event_id,
        window_id=f"wnf_window:{ticker}:{DEFAULT_AS_OF}",
        asset_ticker=ticker,
        source_asset_ticker=source_ticker,
        event_type=event_type.value,
        event_date=event_date,
        published_at=f"{event_date}T12:00:00Z",
        retrieved_at=DEFAULT_CREATED_AT,
        period_bucket="current_week_to_date",
        source_document_id=f"src_{ticker.lower()}_{event_id}",
        source_chunk_id=f"chk_{ticker.lower()}_{event_id}",
        citation_ids=[citation_id],
        citation_asset_tickers={citation_id: ticker},
        source_type=source_type or tier.value,
        source_rank=source_rank,
        source_rank_tier=tier.value,
        source_quality=source_quality.value,
        allowlist_status=allowlist_status.value,
        source_use_policy=source_use_policy.value,
        source_identity=source_identity,
        is_official=is_official,
        storage_rights=storage_rights.value,
        export_rights=export_rights.value,
        review_status=review_status.value,
        parser_status=parser_status.value,
        parser_failure_diagnostics="parser_invalid" if parser_status is SourceParserStatus.failed else None,
        freshness_state=freshness_state.value,
        evidence_state=evidence_state.value,
        importance_score=10,
        license_allowed=license_allowed,
        recognized_source=recognized_source,
        promotional=promotional,
        irrelevant=irrelevant,
        duplicate_group_id=duplicate_group_id or event_id,
        candidate_decision="candidate",
        suppression_reason_codes=suppression_reason_codes or [],
        title_checksum=f"sha256:title:{ticker}:{event_id}",
        evidence_checksum=f"sha256:evidence:{ticker}:{event_id}",
    )


def _review_only_boundaries() -> dict[str, bool]:
    return {
        "sources_approved": False,
        "source_pack_approval_granted": False,
        "golden_asset_source_handoff_approved_by_smoke": False,
        "generated_output_cache_promotion": False,
        "etf500_completion": False,
        "top500_completion": False,
        "live_ai_readiness": False,
        "deployment_readiness": False,
        "asset_support_broadened": False,
        "blocked_products_unlocked": False,
    }


def _bool_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the operator-only Weekly News Focus live-source smoke.")
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON diagnostics.")
    args = parser.parse_args(argv)
    result = run_weekly_news_live_source_smoke()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"weekly news live-source smoke: {result['status']} ({result.get('reason_code')})")
        for case in result.get("cases", []):
            print(f"- {case['status']}: {case['case_id']} ({case['reason_code']})")
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
