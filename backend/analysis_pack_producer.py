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
from backend.market_news import build_market_news_response
from backend.models import (
    AnalysisPackImportBundle,
    AnalysisPackValidationMetadata,
    Citation,
    SourceDocument,
    WeeklyNewsResponse,
)
from backend.overview import generate_asset_overview


ANALYSIS_PACK_PRODUCER_SCHEMA_VERSION = "analysis-pack-producer-report-v1"
ANALYSIS_PACK_PRODUCER_PROMPT_VERSION = "codex-assisted-analysis-pack-prompt-v1"
CODEX_INSTRUCTIONS_PATH = "docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md"


def default_analysis_pack_tickers() -> tuple[str, ...]:
    return tuple(ticker for ticker in HIGH_DEMAND_ANALYSIS_PACK_TICKERS if ticker in ASSETS)


def build_analysis_pack_bundle(
    *,
    tickers: list[str] | tuple[str, ...] | None = None,
    bundle_id: str | None = None,
    generated_at: str | None = None,
    freshness_expires_at: str | None = None,
    expires_days: int = 7,
    fail_on_skipped: bool = False,
) -> tuple[AnalysisPackImportBundle, dict[str, Any]]:
    requested_tickers = _normalize_tickers(tickers or default_analysis_pack_tickers())
    generated_at_value = generated_at or _utc_now_iso()
    expires_at_value = freshness_expires_at or _expires_at(generated_at_value, days=expires_days)
    bundle_id_value = bundle_id or f"analysis-pack-{generated_at_value.replace(':', '').replace('-', '').replace('+0000', 'Z')}"

    market_context_pack = build_market_news_response()
    market_context_pack = market_context_pack.model_copy(update={"analysis_pack_metadata": None})
    economic_indicators = build_economic_indicators_pack(metadata=None)

    ticker_packs: dict[str, WeeklyNewsResponse] = {}
    skipped_tickers: list[dict[str, str]] = []
    for ticker in requested_tickers:
        if ticker not in HIGH_DEMAND_ANALYSIS_PACK_TICKERS:
            skipped_tickers.append({"ticker": ticker, "reason": "not_high_demand_allowlisted"})
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
            "source_mode": "deterministic_fixture",
            "no_html_injection": True,
            "no_raw_article_or_provider_payload_storage": True,
            "visible_persona_labels_allowed": False,
            "skipped_tickers": skipped_tickers,
        },
        checksums={},
        longer_ticker_candidate_history=_build_candidate_history_summary(ticker_packs),
    )
    checksums = {
        "market_context_pack": _stable_digest(market_context_pack.model_dump(mode="json")),
        "economic_indicators": _stable_digest(economic_indicators.model_dump(mode="json")),
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
        "no_live_external_calls": True,
        "raw_article_text_collected": bundle.raw_article_text_collected,
        "raw_provider_payload_exposed": bundle.raw_provider_payload_exposed,
        "current_limitations": [
            "deterministic_fixture_source_mode",
            "no_live_technical_indicator_fetch",
            "no_live_official_macro_fetch",
            "no_tier1_news_search_in_ci",
        ],
    }


def build_technical_data_artifact(bundle: AnalysisPackImportBundle) -> dict[str, Any]:
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
