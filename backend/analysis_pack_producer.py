from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.analysis_packs import (
    ANALYSIS_PACK_VALIDATOR_VERSION,
    HIGH_DEMAND_ANALYSIS_PACK_TICKERS,
    build_economic_indicators_pack,
    compute_analysis_pack_bundle_checksum,
    validate_analysis_pack_import_bundle,
)
from backend.data import ASSETS
from backend.economic_indicators_live import build_live_economic_indicators_pack
from backend.lightweight_data_fetch import fetch_lightweight_asset_data
from backend.market_news_runtime import build_runtime_market_news_response
from backend.market_news import build_market_news_response
from backend.models import (
    AnalysisPackImportBundle,
    AnalysisPackValidationMetadata,
    Citation,
    AssetStatus,
    StateMessage,
    SourceDocument,
    WeeklyNewsResponse,
)
from backend.overview import generate_asset_overview
from backend.settings import build_lightweight_data_settings, build_market_news_settings
from backend.technical_indicators import build_live_technical_data_artifact
from backend.weekly_news import build_ai_comprehensive_analysis
from backend.weekly_news_sources import build_lightweight_weekly_news_focus


ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION = "analysis-pack-producer-report-v1"
ANALYSIS_PACK_PRODUCER_PROMPT_VERSION = "codex-assisted-analysis-pack-prompt-v1"
CODEX_INSTRUCTIONS_PATH = "docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md"


def default_analysis_pack_tickers() -> tuple[str, ...]:
    return tuple(ticker for ticker in HIGH_DEMAND_ANALYSIS_PACK_TICKERS if ticker in ASSETS)


def default_live_analysis_pack_tickers() -> tuple[str, ...]:
    return HIGH_DEMAND_ANALYSIS_PACK_TICKERS


def build_analysis_pack_bundle(
    *,
    tickers: list[str] | tuple[str, ...] | None = None,
    bundle_id: str | None = None,
    generated_at: str | None = None,
    freshness_expires_at: str | None = None,
    expires_days: int = 7,
    fail_on_skipped: bool = False,
    live: bool = False,
    market_fetcher: Any | None = None,
    lightweight_fetcher: Any | None = None,
    technical_fetcher: Any | None = None,
    economic_fetcher: Any | None = None,
) -> tuple[AnalysisPackImportBundle, dict[str, Any]]:
    requested_tickers = _normalize_tickers(tickers or (default_live_analysis_pack_tickers() if live else default_analysis_pack_tickers()))
    generated_at_value = generated_at or _utc_now_iso()
    expires_at_value = freshness_expires_at or _expires_at(generated_at_value, days=expires_days)
    bundle_id_value = bundle_id or f"analysis-pack-{generated_at_value.replace(':', '').replace('-', '').replace('+0000', 'Z')}"

    live_diagnostics: dict[str, Any] = {}
    if live:
        market_settings = build_market_news_settings(
            env={
                "MARKET_NEWS_FETCH_ENABLED": "true",
                "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            }
        )
        market_context_pack = build_runtime_market_news_response(
            as_of=generated_at_value[:10],
            settings=market_settings,
            fetcher=market_fetcher,
        )
    else:
        market_context_pack = build_market_news_response()
    market_context_pack = market_context_pack.model_copy(update={"analysis_pack_metadata": None})
    if live:
        try:
            economic_indicators = build_live_economic_indicators_pack(
                generated_at=generated_at_value,
                fetcher=economic_fetcher,
            )
            live_diagnostics["economic_indicators_source_mode"] = "live_fred_csv"
        except Exception as exc:
            economic_indicators = build_economic_indicators_pack(metadata=None)
            live_diagnostics["economic_indicators_source_mode"] = "deterministic_fixture_fallback"
            live_diagnostics["economic_indicators_fallback_reason"] = type(exc).__name__
    else:
        economic_indicators = build_economic_indicators_pack(metadata=None)
        live_diagnostics["economic_indicators_source_mode"] = "deterministic_fixture"

    ticker_packs: dict[str, WeeklyNewsResponse] = {}
    skipped_tickers: list[dict[str, str]] = []
    for ticker in requested_tickers:
        if ticker not in HIGH_DEMAND_ANALYSIS_PACK_TICKERS:
            skipped_tickers.append({"ticker": ticker, "reason": "not_high_demand_allowlisted"})
            continue
        if live:
            live_pack = _build_live_ticker_pack(
                ticker,
                generated_at=generated_at_value,
                fetcher=lightweight_fetcher,
            )
            if live_pack is None:
                skipped_tickers.append({"ticker": ticker, "reason": "live_weekly_news_or_ai_analysis_unavailable"})
                continue
            ticker_packs[ticker] = live_pack
            continue
        if ticker not in ASSETS:
            skipped_tickers.append({"ticker": ticker, "reason": "not_available_in_current_fixture_universe"})
            continue
        overview = generate_asset_overview(ticker)
        if overview.weekly_news_focus is None or overview.ai_comprehensive_analysis is None:
            skipped_tickers.append({"ticker": ticker, "reason": "weekly_news_or_ai_analysis_unavailable"})
            continue
        ticker_packs[ticker] = WeeklyNewsResponse(
            asset=overview.asset,
            state=overview.state,
            weekly_news_focus=overview.weekly_news_focus,
            ai_comprehensive_analysis=overview.ai_comprehensive_analysis,
        )

    technical_data_artifact = (
        build_live_technical_data_artifact(
            [ticker for ticker in requested_tickers if ticker in HIGH_DEMAND_ANALYSIS_PACK_TICKERS],
            bundle_id=bundle_id_value,
            generated_at=generated_at_value,
            fetcher=technical_fetcher,
        )
        if live
        else None
    )

    if fail_on_skipped and skipped_tickers:
        skipped = ", ".join(f"{item['ticker']}:{item['reason']}" for item in skipped_tickers)
        raise ValueError(f"Analysis pack producer skipped requested ticker(s): {skipped}")

    source_documents = _dedupe_sources(
        [
            *market_context_pack.market_news_focus.source_documents,
            *economic_indicators.source_documents,
            *[
                source
                for pack in ticker_packs.values()
                for source in pack.weekly_news_focus.source_documents
            ],
        ]
    )
    citations = _dedupe_citations(
        [
            *market_context_pack.market_news_focus.citations,
            *economic_indicators.citations,
            *[citation for pack in ticker_packs.values() for citation in pack.weekly_news_focus.citations],
        ]
    )

    draft = AnalysisPackImportBundle(
        bundle_id=bundle_id_value,
        generated_at=generated_at_value,
        freshness_expires_at=expires_at_value,
        prompt_version=ANALYSIS_PACK_PRODUCER_PROMPT_VERSION,
        validation=AnalysisPackValidationMetadata(
            validation_status="passed",
            validator_version=ANALYSIS_PACK_VALIDATOR_VERSION,
            checked_at=generated_at_value,
        ),
        market_context_pack=market_context_pack,
        ticker_packs=ticker_packs,
        economic_indicators=economic_indicators,
        source_documents=source_documents,
        citations=citations,
        validation_metadata={
            "producer_schema_version": ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION,
            "codex_instruction_path": CODEX_INSTRUCTIONS_PATH,
            "source_mode": "live_operator" if live else "deterministic_fixture",
            "no_live_external_calls": not live,
            "no_html_injection": True,
            "no_raw_article_or_provider_payload_storage": True,
            "visible_persona_labels_allowed": False,
            "skipped_tickers": skipped_tickers,
            "live_diagnostics": live_diagnostics,
            "technical_data_artifact": technical_data_artifact,
        },
        checksums={},
        longer_ticker_candidate_history=_build_candidate_history_summary(ticker_packs),
    )
    checksums = {
        "market_context_pack": _stable_digest(market_context_pack.model_dump(mode="json")),
        "economic_indicators": _stable_digest(economic_indicators.model_dump(mode="json")),
        **({"technical_data_artifact": _stable_digest(technical_data_artifact)} if technical_data_artifact else {}),
        **{
            f"ticker_pack:{ticker}": _stable_digest(pack.model_dump(mode="json"))
            for ticker, pack in ticker_packs.items()
        },
    }
    draft = draft.model_copy(update={"checksums": checksums})
    bundle = draft.model_copy(
        update={
            "validation": draft.validation.model_copy(
                update={"checksum": compute_analysis_pack_bundle_checksum(draft)}
            )
        }
    )
    validation_reason_codes = validate_analysis_pack_import_bundle(bundle, now=generated_at_value)
    summary = build_analysis_pack_producer_summary(
        bundle,
        requested_tickers=requested_tickers,
        skipped_tickers=skipped_tickers,
        validation_reason_codes=validation_reason_codes,
    )
    return bundle, summary


def build_analysis_pack_producer_summary(
    bundle: AnalysisPackImportBundle,
    *,
    requested_tickers: list[str],
    skipped_tickers: list[dict[str, str]],
    validation_reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    reason_codes = validation_reason_codes or validate_analysis_pack_import_bundle(bundle, now=bundle.generated_at)
    return {
        "schema_version": ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION,
        "bundle_id": bundle.bundle_id,
        "generated_at": bundle.generated_at,
        "freshness_expires_at": bundle.freshness_expires_at,
        "prompt_version": bundle.prompt_version,
        "codex_instruction_path": CODEX_INSTRUCTIONS_PATH,
        "requested_tickers": requested_tickers,
        "included_tickers": sorted(bundle.ticker_packs),
        "skipped_tickers": skipped_tickers,
        "market_context_pack_included": bundle.market_context_pack is not None,
        "economic_indicators_included": bundle.economic_indicators is not None,
        "ticker_pack_count": len(bundle.ticker_packs),
        "source_document_count": len(bundle.source_documents),
        "citation_count": len(bundle.citations),
        "validation_status": "passed" if not reason_codes else "failed",
        "validation_reason_codes": reason_codes,
        "no_live_external_calls": bool(bundle.validation_metadata.get("no_live_external_calls", True)),
        "source_mode": bundle.validation_metadata.get("source_mode", "deterministic_fixture"),
        "technical_indicator_status": (
            (bundle.validation_metadata.get("technical_data_artifact") or {}).get("technical_indicator_status")
            if isinstance(bundle.validation_metadata.get("technical_data_artifact"), dict)
            else "not_computed_without_live_market_data_adapter"
        ),
        "raw_article_text_collected": bundle.raw_article_text_collected,
        "raw_provider_payload_exposed": bundle.raw_provider_payload_exposed,
        "current_limitations": _current_limitations(bundle),
    }


def build_technical_data_artifact(bundle: AnalysisPackImportBundle) -> dict[str, Any]:
    technical = bundle.validation_metadata.get("technical_data_artifact")
    if isinstance(technical, dict):
        return technical
    return {
        "schema_version": "analysis-pack-technical-data-artifact-v1",
        "bundle_id": bundle.bundle_id,
        "generated_at": bundle.generated_at,
        "source_mode": "deterministic_fixture",
        "no_live_external_calls": True,
        "technical_indicator_status": "not_computed_without_live_market_data_adapter",
        "indicators_reserved": [
            "KD",
            "RSI",
            "MACD",
            "BIAS",
            "DMI_ADX",
            "moving_averages",
            "volume_change",
        ],
        "tickers": {
            ticker: {
                "state": "reserved_not_computed",
                "reason": "The current producer creates validated analysis-pack JSON from repo evidence; live price-series technical calculation is a future adapter.",
            }
            for ticker in sorted(bundle.ticker_packs)
        },
    }


def _build_live_ticker_pack(
    ticker: str,
    *,
    generated_at: str,
    fetcher: Any | None,
) -> WeeklyNewsResponse | None:
    settings = build_lightweight_data_settings(
        env={
            "LIGHTWEIGHT_LIVE_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED": "true",
            "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED": "true",
        }
    )
    response = fetch_lightweight_asset_data(
        ticker,
        settings=settings,
        fetcher=fetcher,
        chart_range="1y",
        bypass_reuse=True,
        retrieved_at=generated_at,
    )
    if response.asset.status is not AssetStatus.supported:
        return None
    weekly_focus = build_lightweight_weekly_news_focus(response)
    if weekly_focus is None:
        return None
    analysis = build_ai_comprehensive_analysis(
        response.asset,
        weekly_focus,
        canonical_fact_citation_ids=[citation.citation_id for citation in response.citations[:4]],
        canonical_source_document_ids=[source.source_document_id for source in response.sources[:4]],
    )
    return WeeklyNewsResponse(
        asset=response.asset,
        state=StateMessage(
            status=response.asset.status,
            message=f"Live local analysis pack evidence is available for {response.asset.ticker}.",
        ),
        weekly_news_focus=weekly_focus,
        ai_comprehensive_analysis=analysis,
    )


def _current_limitations(bundle: AnalysisPackImportBundle) -> list[str]:
    if bundle.validation_metadata.get("source_mode") == "live_operator":
        limitations = ["normal_ci_still_uses_deterministic_no_live_path"]
        live_diagnostics = bundle.validation_metadata.get("live_diagnostics")
        if isinstance(live_diagnostics, dict) and live_diagnostics.get("economic_indicators_source_mode") == "deterministic_fixture_fallback":
            limitations.append("economic_indicators_used_fixture_fallback")
        technical = bundle.validation_metadata.get("technical_data_artifact")
        if not isinstance(technical, dict) or technical.get("technical_indicator_status") not in {"computed", "partial"}:
            limitations.append("technical_indicator_fetch_unavailable")
        return limitations
    return [
        "deterministic_fixture_source_mode",
        "no_live_technical_indicator_fetch",
        "no_live_official_macro_fetch",
        "no_tier1_news_search_in_ci",
    ]


def build_macro_cache_artifact(bundle: AnalysisPackImportBundle) -> dict[str, Any]:
    indicators = bundle.economic_indicators.items if bundle.economic_indicators is not None else []
    return {
        "schema_version": "analysis-pack-macro-cache-artifact-v1",
        "bundle_id": bundle.bundle_id,
        "generated_at": bundle.generated_at,
        "source_mode": "economic-indicators-pack-v1",
        "region": "US",
        "upsert_only": True,
        "indicators": {
            item.indicator_id: {
                "name": item.name,
                "category": item.category.value,
                "value": item.value,
                "numeric_value": item.numeric_value,
                "unit": item.unit,
                "period": item.period,
                "as_of_date": item.as_of_date,
                "published_at": item.published_at,
                "retrieved_at": item.retrieved_at,
                "source_document_ids": item.source_document_ids,
                "citation_ids": item.citation_ids,
                "freshness_state": item.freshness_state.value,
                "trend_direction": item.trend_direction.value,
            }
            for item in indicators
        },
    }


def load_analysis_pack_bundle(path: str) -> AnalysisPackImportBundle:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return AnalysisPackImportBundle.model_validate(payload)


def _normalize_tickers(tickers: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = ticker.strip().upper()
        if not clean or clean in seen:
            continue
        normalized.append(clean)
        seen.add(clean)
    return normalized


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expires_at(generated_at: str, *, days: int) -> str:
    parsed = _parse_datetime(generated_at)
    return (parsed + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _dedupe_sources(sources: list[SourceDocument]) -> list[SourceDocument]:
    deduped: dict[str, SourceDocument] = {}
    for source in sources:
        deduped.setdefault(source.source_document_id, source)
    return list(deduped.values())


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    deduped: dict[str, Citation] = {}
    for citation in citations:
        deduped.setdefault(citation.citation_id, citation)
    return list(deduped.values())


def _stable_digest(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _build_candidate_history_summary(ticker_packs: dict[str, WeeklyNewsResponse]) -> dict[str, list[dict[str, Any]]]:
    return {
        ticker: [
            {
                "candidate_history_schema_version": "ticker-candidate-history-summary-v1",
                "dedupe_only": True,
                "may_support_current_claims": False,
                "selected_weekly_news_item_count": pack.weekly_news_focus.selected_item_count,
                "ai_analysis_available": pack.ai_comprehensive_analysis.analysis_available,
                "candidate_raw_text_stored": False,
                "raw_provider_payload_stored": False,
            }
        ]
        for ticker, pack in ticker_packs.items()
    }
