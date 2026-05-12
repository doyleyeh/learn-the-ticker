from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.models import AnalysisPackImportBundle, EconomicIndicatorItem


AI_CONTEXT_SCHEMA_VERSION = "analysis-pack-ai-context-v1"
YIELD_CURVE_FLAT_OR_INVERTED_THRESHOLD_BPS = 25.0
GEOPOLITICAL_SUPPLY_CHAIN_RISK_KEYWORDS = (
    "middle east",
    "red sea",
    "hormuz",
    "suez",
    "iran",
    "sanctions",
    "sanction",
    "blockade",
    "conflict",
    "disruption",
    "shipping",
    "supply chain",
)


def build_ai_context_artifact(bundle: AnalysisPackImportBundle) -> dict[str, Any]:
    technical = bundle.validation_metadata.get("technical_data_artifact")
    technical_rows = technical.get("tickers", {}) if isinstance(technical, dict) else {}
    context = {
        "schema_version": AI_CONTEXT_SCHEMA_VERSION,
        "bundle_id": bundle.bundle_id,
        "generated_at": bundle.generated_at,
        "freshness_expires_at": bundle.freshness_expires_at,
        "prompt_version": bundle.prompt_version,
        "scope": {
            "region": "US",
            "language": "en",
            "stable_facts_separate_from_timely_context": True,
            "visible_persona_labels_allowed": False,
            "raw_article_text_allowed": False,
            "raw_provider_payload_allowed": False,
        },
        "market_news": _market_context(bundle),
        "tickers": _ticker_context(bundle),
        "economic_indicators": _economic_context(bundle),
        "technical_indicators": {
            ticker: row
            for ticker, row in sorted(technical_rows.items())
            if isinstance(row, dict)
        },
        "canonical_fact_citation_ids": _canonical_fact_citation_ids(bundle),
        "source_document_ids": _all_source_document_ids(bundle),
        "citation_ids": _all_citation_ids(bundle),
        "allowed_numeric_facts": _allowed_numeric_facts(bundle, technical_rows),
        "rules": {
            "numeric_integrity_required": True,
            "yield_curve_flat_or_inverted_threshold_bps": YIELD_CURVE_FLAT_OR_INVERTED_THRESHOLD_BPS,
            "yield_curve_silence_rule": (
                "Mention yield-curve flattening or inversion only when a validated spread is under 25 bps or inverted."
            ),
            "geopolitical_supply_chain_warning_keywords": list(GEOPOLITICAL_SUPPLY_CHAIN_RISK_KEYWORDS),
            "persona_labels_visible": False,
        },
    }
    context["context_checksum"] = compute_ai_context_checksum(context)
    return context


def compute_ai_context_checksum(context: dict[str, Any]) -> str:
    payload = dict(context)
    payload.pop("context_checksum", None)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_ai_context_artifact(bundle: AnalysisPackImportBundle) -> list[str]:
    context = bundle.validation_metadata.get("ai_context_artifact")
    checksum = bundle.validation_metadata.get("ai_context_checksum")
    if not isinstance(context, dict):
        return ["ai_context_missing"]
    reason_codes: list[str] = []
    if context.get("schema_version") != AI_CONTEXT_SCHEMA_VERSION:
        reason_codes.append("unsupported_ai_context_schema")
    if context.get("bundle_id") != bundle.bundle_id:
        reason_codes.append("ai_context_bundle_mismatch")
    if checksum != compute_ai_context_checksum(context):
        reason_codes.append("ai_context_checksum_mismatch")
    if context.get("context_checksum") != checksum:
        reason_codes.append("ai_context_checksum_mismatch")
    bundle_source_ids = set(_all_source_document_ids(bundle))
    bundle_citation_ids = set(_all_citation_ids(bundle))
    context_source_ids = set(_string_list(context.get("source_document_ids")))
    context_citation_ids = set(_string_list(context.get("citation_ids")))
    if not context_source_ids <= bundle_source_ids:
        reason_codes.append("ai_context_unknown_source_id")
    if not context_citation_ids <= bundle_citation_ids:
        reason_codes.append("ai_context_unknown_citation_id")
    if not isinstance(context.get("allowed_numeric_facts"), list):
        reason_codes.append("ai_context_numeric_facts_missing")
    return list(dict.fromkeys(reason_codes))


def _market_context(bundle: AnalysisPackImportBundle) -> dict[str, Any]:
    if bundle.market_context_pack is None:
        return {"selected_items": [], "ai_analysis_section_ids": []}
    focus = bundle.market_context_pack.market_news_focus
    analysis = bundle.market_context_pack.market_ai_comprehensive_analysis
    return {
        "selected_items": [
            {
                "story_id": item.story_id,
                "title": item.title,
                "summary": item.summary,
                "published_at": item.published_at,
                "topic_bucket": item.topic_bucket.value,
                "citation_ids": list(item.citation_ids),
                "source_document_ids": [item.source.source_document_id],
                "source_use_policy": item.source.source_use_policy.value,
            }
            for item in focus.items
        ],
        "ai_analysis_section_ids": [section.section_id for section in analysis.sections],
        "market_news_story_ids": list(analysis.market_news_story_ids),
    }


def _ticker_context(bundle: AnalysisPackImportBundle) -> dict[str, Any]:
    tickers: dict[str, Any] = {}
    for ticker, pack in sorted(bundle.ticker_packs.items()):
        tickers[ticker] = {
            "asset": pack.asset.model_dump(mode="json"),
            "weekly_news_items": [
                {
                    "event_id": item.event_id,
                    "title": item.title,
                    "summary": item.summary,
                    "event_type": item.event_type.value,
                    "published_at": item.published_at,
                    "citation_ids": list(item.citation_ids),
                    "source_document_ids": [item.source.source_document_id],
                    "source_use_policy": item.source.source_use_policy.value,
                }
                for item in pack.weekly_news_focus.items
            ],
            "ai_analysis_section_ids": [section.section_id for section in pack.ai_comprehensive_analysis.sections],
            "weekly_news_event_ids": list(pack.ai_comprehensive_analysis.weekly_news_event_ids),
            "canonical_fact_citation_ids": list(pack.ai_comprehensive_analysis.canonical_fact_citation_ids),
            "source_document_ids": list(pack.ai_comprehensive_analysis.source_document_ids),
        }
    return tickers


def _economic_context(bundle: AnalysisPackImportBundle) -> list[dict[str, Any]]:
    if bundle.economic_indicators is None:
        return []
    return [
        {
            "indicator_id": item.indicator_id,
            "name": item.name,
            "category": item.category.value,
            "value": item.value,
            "numeric_value": item.numeric_value,
            "unit": item.unit,
            "period": item.period,
            "as_of_date": item.as_of_date,
            "published_at": item.published_at,
            "retrieved_at": item.retrieved_at,
            "citation_ids": list(item.citation_ids),
            "source_document_ids": list(item.source_document_ids),
            "source_use_policy": item.source.source_use_policy.value,
        }
        for item in bundle.economic_indicators.items
    ]


def _canonical_fact_citation_ids(bundle: AnalysisPackImportBundle) -> dict[str, list[str]]:
    return {
        ticker: list(pack.ai_comprehensive_analysis.canonical_fact_citation_ids)
        for ticker, pack in sorted(bundle.ticker_packs.items())
    }


def _all_source_document_ids(bundle: AnalysisPackImportBundle) -> list[str]:
    source_ids = {source.source_document_id for source in bundle.source_documents}
    if bundle.market_context_pack is not None:
        source_ids.update(source.source_document_id for source in bundle.market_context_pack.market_news_focus.source_documents)
    if bundle.economic_indicators is not None:
        source_ids.update(source.source_document_id for source in bundle.economic_indicators.source_documents)
    for pack in bundle.ticker_packs.values():
        source_ids.update(source.source_document_id for source in pack.weekly_news_focus.source_documents)
        source_ids.update(pack.ai_comprehensive_analysis.source_document_ids)
    technical = bundle.validation_metadata.get("technical_data_artifact")
    rows = technical.get("tickers", {}) if isinstance(technical, dict) else {}
    for row in rows.values() if isinstance(rows, dict) else ():
        if isinstance(row, dict) and isinstance(row.get("source"), dict) and row["source"].get("source_document_id"):
            source_ids.add(str(row["source"]["source_document_id"]))
    return sorted(source_ids)


def _all_citation_ids(bundle: AnalysisPackImportBundle) -> list[str]:
    citation_ids = {citation.citation_id for citation in bundle.citations}
    if bundle.market_context_pack is not None:
        citation_ids.update(citation.citation_id for citation in bundle.market_context_pack.market_news_focus.citations)
    if bundle.economic_indicators is not None:
        citation_ids.update(citation.citation_id for citation in bundle.economic_indicators.citations)
    for pack in bundle.ticker_packs.values():
        citation_ids.update(citation.citation_id for citation in pack.weekly_news_focus.citations)
        citation_ids.update(pack.ai_comprehensive_analysis.canonical_fact_citation_ids)
    technical = bundle.validation_metadata.get("technical_data_artifact")
    rows = technical.get("tickers", {}) if isinstance(technical, dict) else {}
    for row in rows.values() if isinstance(rows, dict) else ():
        if isinstance(row, dict) and isinstance(row.get("source"), dict) and row["source"].get("citation_id"):
            citation_ids.add(str(row["source"]["citation_id"]))
    return sorted(citation_ids)


def _allowed_numeric_facts(
    bundle: AnalysisPackImportBundle,
    technical_rows: Any,
) -> list[dict[str, Any]]:
    return build_allowed_numeric_facts(bundle.economic_indicators, technical_rows)


def build_allowed_numeric_facts(
    economic_indicators: Any | None,
    technical_rows: Any,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    if economic_indicators is not None:
        for item in economic_indicators.items:
            facts.extend(_economic_numeric_fact(item))
    if isinstance(technical_rows, dict):
        for ticker, row in sorted(technical_rows.items()):
            if isinstance(row, dict) and row.get("state") == "computed":
                facts.extend(_technical_numeric_facts(str(ticker).upper(), row))
    return facts


def _economic_numeric_fact(item: EconomicIndicatorItem) -> list[dict[str, Any]]:
    if item.numeric_value is None:
        return []
    aliases = {
        "dxy": ["dxy", "u.s. dollar index", "us dollar index"],
        "vix": ["vix", "cboe volatility index", "volatility index"],
        "treasury_10y": ["us10y", "10-year treasury", "10 year treasury", "10y treasury"],
        "treasury_3m": ["3-month treasury", "3 month treasury", "3m treasury"],
        "treasury_30y": ["30-year treasury", "30 year treasury", "30y treasury"],
        "wti_oil": ["wti", "wti oil", "crude oil"],
    }.get(item.indicator_id, [item.name.lower(), item.indicator_id.replace("_", " ")])
    return [
        {
            "fact_id": f"economic:{item.indicator_id}",
            "scope": "market",
            "label": item.name,
            "value": item.numeric_value,
            "unit": item.unit,
            "as_of_date": item.as_of_date,
            "aliases": aliases,
            "tolerance_abs": _numeric_tolerance(item.numeric_value),
            "citation_ids": list(item.citation_ids),
            "source_document_ids": list(item.source_document_ids),
        }
    ]


def _technical_numeric_facts(ticker: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    citation_ids = [str(source.get("citation_id"))] if source.get("citation_id") else []
    source_document_ids = [str(source.get("source_document_id"))] if source.get("source_document_id") else []
    facts: list[dict[str, Any]] = []

    def add(path: str, value: Any, label: str, aliases: list[str], unit: str | None = None) -> None:
        if not isinstance(value, (int, float)):
            return
        facts.append(
            {
                "fact_id": f"technical:{ticker}:{path}",
                "scope": "ticker",
                "ticker": ticker,
                "label": label,
                "value": float(value),
                "unit": unit,
                "as_of_date": row.get("as_of_date"),
                "aliases": aliases,
                "tolerance_abs": _numeric_tolerance(float(value)),
                "citation_ids": citation_ids,
                "source_document_ids": source_document_ids,
            }
        )

    add("close", row.get("close"), f"{ticker} close price", [f"{ticker.lower()} close", "close price", "closing price"], "USD")
    kd = row.get("KD") if isinstance(row.get("KD"), dict) else {}
    add("KD_K", kd.get("K"), f"{ticker} KD K", [f"{ticker.lower()} kd k", "kd k", "k value"])
    add("KD_D", kd.get("D"), f"{ticker} KD D", [f"{ticker.lower()} kd d", "kd d", "d value"])
    rsi = row.get("RSI") if isinstance(row.get("RSI"), dict) else {}
    add("RSI", rsi.get("value"), f"{ticker} RSI", [f"{ticker.lower()} rsi", "rsi"])
    macd = row.get("MACD") if isinstance(row.get("MACD"), dict) else {}
    add("MACD", macd.get("macd"), f"{ticker} MACD", [f"{ticker.lower()} macd", "macd"])
    add("MACD_signal", macd.get("signal"), f"{ticker} MACD signal", [f"{ticker.lower()} macd signal", "macd signal"])
    add("MACD_histogram", macd.get("histogram"), f"{ticker} MACD histogram", [f"{ticker.lower()} macd histogram", "macd histogram"])
    dmi = row.get("DMI_ADX") if isinstance(row.get("DMI_ADX"), dict) else {}
    add("ADX", dmi.get("ADX"), f"{ticker} ADX", [f"{ticker.lower()} adx", "adx"])
    for period, value in (row.get("BIAS") if isinstance(row.get("BIAS"), dict) else {}).items():
        add(f"BIAS_{period}", value, f"{ticker} BIAS {period}", [f"{ticker.lower()} bias {period}", f"bias {period}", "bias"], "percent")
    for period, value in (row.get("moving_averages") if isinstance(row.get("moving_averages"), dict) else {}).items():
        add(
            f"MA_{period}",
            value,
            f"{ticker} {period}-day moving average",
            [f"{ticker.lower()} {period}-day moving average", f"{period}-day moving average", f"ma{period}"],
            "USD",
        )
    volume = row.get("volume_change") if isinstance(row.get("volume_change"), dict) else {}
    add("volume_change_percent", volume.get("percent_change"), f"{ticker} volume change", [f"{ticker.lower()} volume change", "volume change"], "percent")
    return facts


def _numeric_tolerance(value: float) -> float:
    return max(0.02, abs(float(value)) * 0.02)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
