from __future__ import annotations

from typing import Any, Iterable

from backend.analysis_pack_context import build_allowed_numeric_facts
from backend.citations import CitationEvidence, EvidenceKind
from backend.models import (
    AssetIdentity,
    EconomicIndicatorsPackResponse,
    LightweightFetchResponse,
    MarketNewsFocusResponse,
    SourceExportRights,
    SourceParserStatus,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    WeeklyNewsFocusResponse,
)
from backend.retrieval import AssetKnowledgePack


GENERATION_EVIDENCE_PACK_SCHEMA_VERSION = "generation-evidence-pack-v1"
MAX_PROMPT_TEXT_CHARS = 420


def empty_generation_evidence_pack(*, asset_ticker: str, scope: str = "asset") -> dict[str, Any]:
    normalized = asset_ticker.strip().upper() or "MARKET"
    return {
        "schema_version": GENERATION_EVIDENCE_PACK_SCHEMA_VERSION,
        "scope": scope,
        "asset_ticker": normalized,
        "allowed_asset_tickers": [normalized],
        "source_documents": [],
        "canonical_facts": [],
        "source_passages": [],
        "market_news": [],
        "weekly_news": [],
        "economic_indicators": [],
        "technical_indicators": {},
        "allowed_numeric_facts": [],
        "citation_evidence": [],
        "evidence_notes": [],
        "rules": _rules(),
    }


def evidence_pack_from_knowledge_pack(
    pack: AssetKnowledgePack,
    *,
    citation_ids: Iterable[str] | None = None,
    evidence_notes: Iterable[str] | None = None,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    market_news_focus: MarketNewsFocusResponse | None = None,
    weekly_news_focus: WeeklyNewsFocusResponse | None = None,
    technical_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    allowed = set(_string_list(citation_ids))
    result = empty_generation_evidence_pack(asset_ticker=pack.asset.ticker, scope="asset")
    result["source_documents"] = [_source_document(source) for source in pack.source_documents][:16]
    result["canonical_facts"] = [
        _fact_entry(item)
        for item in pack.normalized_facts
        if item.fact.evidence_state in {"supported", "partial"} and (not allowed or f"c_{item.fact.fact_id}" in allowed)
    ][:18]
    result["source_passages"] = [_chunk_entry(item) for item in pack.source_chunks if not allowed or f"c_{item.chunk.chunk_id}" in allowed][:12]
    result["citation_evidence"] = [
        _citation_evidence_from_fact(item, pack.asset.ticker)
        for item in pack.normalized_facts
        if item.fact.evidence_state in {"supported", "partial"} and (not allowed or f"c_{item.fact.fact_id}" in allowed)
    ]
    result["citation_evidence"].extend(
        _citation_evidence_from_chunk(item, pack.asset.ticker)
        for item in pack.source_chunks
        if not allowed or f"c_{item.chunk.chunk_id}" in allowed
    )
    _add_common_context(
        result,
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        weekly_news_focus=weekly_news_focus,
        technical_context=technical_context,
        evidence_notes=evidence_notes,
    )
    return _dedupe_pack(result)


def evidence_pack_from_lightweight_response(
    response: LightweightFetchResponse,
    *,
    citation_ids: Iterable[str] | None = None,
    evidence_notes: Iterable[str] | None = None,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    market_news_focus: MarketNewsFocusResponse | None = None,
    weekly_news_focus: WeeklyNewsFocusResponse | None = None,
    technical_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    allowed = set(_string_list(citation_ids))
    result = empty_generation_evidence_pack(asset_ticker=response.asset.ticker, scope="asset")
    source_by_id = {source.source_document_id: source for source in response.sources}
    result["source_documents"] = [_lightweight_source(source) for source in response.sources][:16]
    result["canonical_facts"] = [_lightweight_fact_entry(fact) for fact in response.facts]
    result["canonical_facts"] = [
        fact
        for fact in result["canonical_facts"]
        if fact["evidence_state"] in {"supported", "partial"} and (not allowed or set(fact["citation_ids"]) & allowed)
    ][:22]
    result["citation_evidence"] = []
    for fact in response.facts:
        for source_id in fact.source_document_ids:
            source = source_by_id.get(source_id)
            if source is None:
                continue
            citation_id = _lightweight_fact_citation_id(fact, source_id)
            if allowed and citation_id not in allowed:
                continue
            result["citation_evidence"].append(_citation_evidence_from_lightweight_fact(response, fact, source, citation_id))
    _add_common_context(
        result,
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        weekly_news_focus=weekly_news_focus,
        technical_context=technical_context or _technical_context_from_lightweight(response),
        evidence_notes=evidence_notes,
    )
    return _dedupe_pack(result)


def evidence_pack_from_market_news(
    focus: MarketNewsFocusResponse,
    *,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
) -> dict[str, Any]:
    result = empty_generation_evidence_pack(asset_ticker="MARKET", scope="market")
    result["market_news"] = [_market_item(item) for item in focus.items]
    result["source_documents"] = [_source_document(source) for source in focus.source_documents]
    result["citation_evidence"] = [
        _citation_evidence_from_market_item(item)
        for item in focus.items
    ]
    _add_common_context(result, economic_indicators=economic_indicators)
    return _dedupe_pack(result)


def evidence_pack_from_weekly_news(
    asset: AssetIdentity,
    weekly_news_focus: WeeklyNewsFocusResponse,
    *,
    canonical_fact_citation_ids: Iterable[str] | None = None,
    canonical_source_document_ids: Iterable[str] | None = None,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    market_news_focus: MarketNewsFocusResponse | None = None,
    technical_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del canonical_source_document_ids
    result = empty_generation_evidence_pack(asset_ticker=asset.ticker, scope="ticker")
    result["asset"] = asset.model_dump(mode="json")
    result["weekly_news"] = [_weekly_item(item) for item in weekly_news_focus.items]
    result["source_documents"] = [_source_document(source) for source in weekly_news_focus.source_documents]
    result["citation_evidence"] = [_citation_evidence_from_weekly_item(item, asset.ticker) for item in weekly_news_focus.items]
    result["canonical_fact_citation_ids"] = _string_list(canonical_fact_citation_ids)
    _add_common_context(
        result,
        economic_indicators=economic_indicators,
        market_news_focus=market_news_focus,
        technical_context=technical_context,
    )
    return _dedupe_pack(result)


def evidence_pack_from_citation_evidence(
    *,
    asset: AssetIdentity,
    evidence: Iterable[CitationEvidence],
    evidence_summaries: Iterable[str] | None = None,
    evidence_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    result = empty_generation_evidence_pack(asset_ticker=asset.ticker, scope="chat")
    rows = [item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item) for item in evidence]
    result["citation_evidence"] = rows
    result["source_passages"] = [
        {
            "citation_id": row.get("citation_id"),
            "source_document_id": row.get("source_document_id"),
            "source_type": row.get("source_type"),
            "freshness_state": row.get("freshness_state"),
            "text": _truncate(row.get("supporting_text")),
        }
        for row in rows
    ][:12]
    result["evidence_notes"] = list(evidence_notes or evidence_summaries or [])[:16]
    return _dedupe_pack(result)


def generation_pack_allowed_numeric_facts(pack: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(pack, dict):
        return []
    return [item for item in pack.get("allowed_numeric_facts", []) if isinstance(item, dict)]


def generation_pack_citation_evidence(pack: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(pack, dict):
        return []
    return [item for item in pack.get("citation_evidence", []) if isinstance(item, dict)]


def generation_pack_allowed_asset_tickers(pack: dict[str, Any] | None, fallback: str) -> list[str]:
    if not isinstance(pack, dict):
        return [fallback.strip().upper()]
    values = _string_list(pack.get("allowed_asset_tickers"))
    return values or [fallback.strip().upper()]


def _add_common_context(
    result: dict[str, Any],
    *,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
    market_news_focus: MarketNewsFocusResponse | None = None,
    weekly_news_focus: WeeklyNewsFocusResponse | None = None,
    technical_context: dict[str, Any] | None = None,
    evidence_notes: Iterable[str] | None = None,
) -> None:
    if economic_indicators is not None:
        if "MARKET" not in result["allowed_asset_tickers"]:
            result["allowed_asset_tickers"].append("MARKET")
        result["economic_indicators"] = [_economic_item(item) for item in economic_indicators.items][:20]
        result["source_documents"].extend(_source_document(source) for source in economic_indicators.source_documents)
        result["citation_evidence"].extend(_citation_evidence_from_economic_item(item) for item in economic_indicators.items)
    if market_news_focus is not None:
        if "MARKET" not in result["allowed_asset_tickers"]:
            result["allowed_asset_tickers"].append("MARKET")
        result["market_news"] = [_market_item(item) for item in market_news_focus.items]
        result["source_documents"].extend(_source_document(source) for source in market_news_focus.source_documents)
        result["citation_evidence"].extend(_citation_evidence_from_market_item(item) for item in market_news_focus.items)
    if weekly_news_focus is not None:
        result["weekly_news"] = [_weekly_item(item) for item in weekly_news_focus.items]
        result["source_documents"].extend(_source_document(source) for source in weekly_news_focus.source_documents)
    if technical_context:
        result["technical_indicators"] = _technical_context(technical_context)
    result["allowed_numeric_facts"] = build_allowed_numeric_facts(economic_indicators, _technical_rows(result["technical_indicators"]))
    if evidence_notes:
        result["evidence_notes"] = list(dict.fromkeys(str(note) for note in evidence_notes if str(note).strip()))[:24]


def _dedupe_pack(pack: dict[str, Any]) -> dict[str, Any]:
    pack["source_documents"] = _dedupe_dicts(pack.get("source_documents", []), "source_document_id")
    pack["citation_evidence"] = _dedupe_dicts(pack.get("citation_evidence", []), "citation_id")
    pack["canonical_facts"] = _dedupe_dicts(pack.get("canonical_facts", []), "fact_id")
    pack["source_passages"] = _dedupe_dicts(pack.get("source_passages", []), "citation_id")
    pack["allowed_numeric_facts"] = _dedupe_dicts(pack.get("allowed_numeric_facts", []), "fact_id")
    return pack


def _dedupe_dicts(items: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        value = str(item.get(key) or "")
        if value and value not in result:
            result[value] = item
    return list(result.values())


def _source_document(source: Any) -> dict[str, Any]:
    return {
        "source_document_id": getattr(source, "source_document_id", None),
        "source_type": getattr(source, "source_type", None),
        "title": getattr(source, "title", None),
        "publisher": getattr(source, "publisher", None),
        "published_at": getattr(source, "published_at", None),
        "as_of_date": getattr(source, "as_of_date", None),
        "retrieved_at": getattr(source, "retrieved_at", None),
        "freshness_state": _value(getattr(source, "freshness_state", None)),
        "is_official": bool(getattr(source, "is_official", False)),
        "source_quality": _value(getattr(source, "source_quality", None)),
        "allowlist_status": _value(getattr(source, "allowlist_status", None)),
        "source_use_policy": _value(getattr(source, "source_use_policy", None)),
    }


def _lightweight_source(source: Any) -> dict[str, Any]:
    row = _source_document(source)
    row["source_label"] = _value(getattr(source, "source_label", None))
    row["raw_payload_exposed"] = bool(getattr(source, "raw_payload_exposed", False))
    return row


def _fact_entry(item: Any) -> dict[str, Any]:
    fact = item.fact
    return {
        "fact_id": fact.fact_id,
        "field_name": fact.field_name,
        "value": _compact_value(fact.value),
        "unit": fact.unit,
        "period": fact.period,
        "as_of_date": fact.as_of_date,
        "freshness_state": _value(fact.freshness_state),
        "evidence_state": fact.evidence_state,
        "citation_ids": [f"c_{fact.fact_id}"],
        "source_document_ids": [fact.source_document_id],
    }


def _lightweight_fact_entry(fact: Any) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "field_name": fact.field_name,
        "value": _compact_value(fact.value),
        "as_of_date": fact.as_of_date,
        "retrieved_at": fact.retrieved_at,
        "freshness_state": _value(fact.freshness_state),
        "evidence_state": _value(fact.evidence_state),
        "citation_ids": [_lightweight_fact_citation_id(fact, source_id) for source_id in fact.source_document_ids],
        "source_document_ids": list(fact.source_document_ids),
        "source_labels": [_value(label) for label in fact.source_labels],
        "fallback_used": bool(fact.fallback_used),
        "limitations": fact.limitations,
    }


def _chunk_entry(item: Any) -> dict[str, Any]:
    return {
        "citation_id": f"c_{item.chunk.chunk_id}",
        "source_document_id": item.source_document.source_document_id,
        "section_name": item.chunk.section_name,
        "freshness_state": _value(item.source_document.freshness_state),
        "supported_claim_types": list(item.chunk.supported_claim_types),
        "text": _truncate(item.chunk.text),
    }


def _market_item(item: Any) -> dict[str, Any]:
    return {
        "story_id": item.story_id,
        "title": item.title,
        "summary": _truncate(item.summary),
        "published_at": item.published_at,
        "topic_bucket": _value(item.topic_bucket),
        "entities": list(item.entities),
        "citation_ids": list(item.citation_ids),
        "source_document_ids": [item.source.source_document_id],
        "source_use_policy": _value(item.source.source_use_policy),
    }


def _weekly_item(item: Any) -> dict[str, Any]:
    return {
        "event_id": item.event_id,
        "title": item.title,
        "summary": _truncate(item.summary),
        "event_type": _value(item.event_type),
        "event_date": item.event_date,
        "published_at": item.published_at,
        "citation_ids": list(item.citation_ids),
        "source_document_ids": [item.source.source_document_id],
        "source_quality": _value(item.source.source_quality),
        "source_use_policy": _value(item.source.source_use_policy),
        "is_official": bool(item.source.is_official),
    }


def _economic_item(item: Any) -> dict[str, Any]:
    return {
        "indicator_id": item.indicator_id,
        "name": item.name,
        "category": _value(item.category),
        "value": item.value,
        "numeric_value": item.numeric_value,
        "unit": item.unit,
        "period": item.period,
        "as_of_date": item.as_of_date,
        "published_at": item.published_at,
        "citation_ids": list(item.citation_ids),
        "source_document_ids": list(item.source_document_ids),
        "source_use_policy": _value(item.source.source_use_policy),
    }


def _technical_context(context: dict[str, Any]) -> dict[str, Any]:
    if context.get("state") == "computed":
        return {
            "state": "computed",
            "ticker": context.get("ticker"),
            "as_of_date": context.get("as_of_date"),
            "point_count": context.get("point_count"),
            "close": context.get("close"),
            "KD": context.get("KD"),
            "RSI": context.get("RSI"),
            "MACD": context.get("MACD"),
            "BIAS": context.get("BIAS"),
            "DMI_ADX": context.get("DMI_ADX"),
            "moving_averages": context.get("moving_averages"),
            "volume_change": context.get("volume_change"),
            "source": context.get("source"),
        }
    return {"state": context.get("state", "unavailable"), "reason": context.get("reason")}


def _technical_rows(context: Any) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    ticker = str(context.get("ticker") or "").strip().upper()
    if ticker:
        return {ticker: context}
    return {}


def _technical_context_from_lightweight(response: LightweightFetchResponse) -> dict[str, Any] | None:
    fact = next((item for item in response.facts if item.field_name == "provider_price_chart"), None)
    if fact is None or not isinstance(fact.value, dict):
        return None
    return {
        "state": "summary_only",
        "ticker": response.asset.ticker,
        "as_of_date": fact.as_of_date,
        "chart_range": fact.value.get("range"),
        "point_count": fact.value.get("point_count"),
        "latest_close": fact.value.get("latest_close"),
        "latest_date": fact.value.get("latest_date"),
        "delayed_or_best_effort_label": fact.value.get("delayed_or_best_effort_label"),
    }


def _citation_evidence_from_fact(item: Any, asset_ticker: str) -> dict[str, Any]:
    return CitationEvidence(
        citation_id=f"c_{item.fact.fact_id}",
        asset_ticker=asset_ticker,
        source_document_id=item.source_document.source_document_id,
        source_type=item.source_document.source_type,
        evidence_kind=EvidenceKind.normalized_fact,
        freshness_state=item.fact.freshness_state,
        as_of_date=item.fact.as_of_date,
        supported_claim_types=item.source_chunk.supported_claim_types,
        supporting_text=item.source_chunk.text,
        supports_claim=item.fact.evidence_state in {"supported", "partial"},
        is_recent=False,
        allowlist_status=item.source_document.allowlist_status,
        source_use_policy=item.source_document.source_use_policy,
        source_identity=item.source_document.url or item.source_document.source_document_id,
        is_official=item.source_document.is_official,
        source_quality=item.source_document.source_quality,
    ).model_dump(mode="json")


def _citation_evidence_from_chunk(item: Any, asset_ticker: str) -> dict[str, Any]:
    return CitationEvidence(
        citation_id=f"c_{item.chunk.chunk_id}",
        asset_ticker=asset_ticker,
        source_document_id=item.source_document.source_document_id,
        source_type=item.source_document.source_type,
        evidence_kind=EvidenceKind.document_chunk,
        freshness_state=item.source_document.freshness_state,
        as_of_date=item.source_document.as_of_date,
        published_at=item.source_document.published_at,
        supported_claim_types=item.chunk.supported_claim_types,
        supporting_text=item.chunk.text,
        supports_claim=True,
        is_recent=item.source_document.source_type == "recent_development",
        allowlist_status=item.source_document.allowlist_status,
        source_use_policy=item.source_document.source_use_policy,
        source_identity=item.source_document.url or item.source_document.source_document_id,
        is_official=item.source_document.is_official,
        source_quality=item.source_document.source_quality,
    ).model_dump(mode="json")


def _citation_evidence_from_lightweight_fact(response: LightweightFetchResponse, fact: Any, source: Any, citation_id: str) -> dict[str, Any]:
    supporting_text = (
        f"{response.asset.ticker} normalized fact {fact.field_name}: {_compact_value(fact.value)}. "
        f"as_of={fact.as_of_date or source.as_of_date or 'unknown'}; source_use={_value(source.source_use_policy)}."
    )
    return CitationEvidence(
        citation_id=citation_id,
        asset_ticker=response.asset.ticker,
        source_document_id=source.source_document_id,
        source_type=_lightweight_source_type(source),
        evidence_kind=EvidenceKind.normalized_fact,
        freshness_state=fact.freshness_state,
        as_of_date=fact.as_of_date or source.as_of_date,
        retrieved_at=fact.retrieved_at or source.retrieved_at,
        supported_claim_types=_supported_claim_types_for_fact(fact.field_name),
        supporting_text=supporting_text,
        supports_claim=_value(fact.evidence_state) in {"supported", "partial"},
        is_recent=source.source_type == "yahoo_finance_weekly_news_metadata",
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        source_identity=source.url or source.source_document_id,
        is_official=source.is_official,
        source_quality=source.source_quality,
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.excerpts_allowed,
        review_status=SourceReviewStatus.approved,
        approval_rationale="Lightweight source-labeled evidence approved for local generated educational output.",
        parser_status=SourceParserStatus.partial,
    ).model_dump(mode="json")


def _citation_evidence_from_market_item(item: Any) -> dict[str, Any]:
    return CitationEvidence(
        citation_id=item.citation_ids[0] if item.citation_ids else f"c_market_{item.story_id}",
        asset_ticker="MARKET",
        source_document_id=item.source.source_document_id,
        source_type="market_news_story_cluster",
        evidence_kind=EvidenceKind.source_document,
        freshness_state=item.freshness_state,
        published_at=item.published_at,
        supported_claim_types=["recent", "interpretation", "factual"],
        supporting_text=item.summary,
        supports_claim=True,
        is_recent=True,
        allowlist_status=item.source.allowlist_status,
        source_use_policy=item.source.source_use_policy,
        source_identity=item.source.url,
        is_official=item.source.is_official,
        source_quality=item.source.source_quality,
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.excerpts_allowed,
        review_status=SourceReviewStatus.approved,
        approval_rationale="Selected Market News Focus metadata passed source-use and selection rules.",
        parser_status=SourceParserStatus.partial,
    ).model_dump(mode="json")


def _citation_evidence_from_weekly_item(item: Any, asset_ticker: str) -> dict[str, Any]:
    return CitationEvidence(
        citation_id=item.citation_ids[0] if item.citation_ids else f"c_weekly_{item.event_id}",
        asset_ticker=asset_ticker,
        source_document_id=item.source.source_document_id,
        source_type=item.source.source_type,
        evidence_kind=EvidenceKind.source_document,
        freshness_state=item.freshness_state,
        published_at=item.published_at,
        as_of_date=item.event_date,
        supported_claim_types=["recent", "interpretation", "risk", "factual"],
        supporting_text=item.summary,
        supports_claim=True,
        is_recent=True,
        allowlist_status=item.source.allowlist_status,
        source_use_policy=item.source.source_use_policy,
        source_identity=item.source.url,
        is_official=item.source.is_official,
        source_quality=item.source.source_quality,
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.excerpts_allowed,
        review_status=SourceReviewStatus.approved,
        approval_rationale="Selected Weekly News Focus metadata passed source-use and selection rules.",
        parser_status=SourceParserStatus.partial,
    ).model_dump(mode="json")


def _citation_evidence_from_economic_item(item: Any) -> dict[str, Any]:
    source = item.source
    return CitationEvidence(
        citation_id=item.citation_ids[0] if item.citation_ids else f"c_economic_{item.indicator_id}",
        asset_ticker="MARKET",
        source_document_id=item.source_document_ids[0] if item.source_document_ids else source.source_document_id,
        source_type=source.source_type,
        evidence_kind=EvidenceKind.normalized_fact,
        freshness_state=item.freshness_state,
        as_of_date=item.as_of_date,
        published_at=item.published_at,
        retrieved_at=item.retrieved_at,
        supported_claim_types=["factual", "interpretation"],
        supporting_text=f"{item.name}: {item.value}; period={item.period}; source={source.publisher}.",
        supports_claim=item.evidence_state.value in {"supported", "partial"},
        is_recent=False,
        allowlist_status=source.allowlist_status,
        source_use_policy=source.source_use_policy,
        source_identity=source.url,
        is_official=source.is_official,
        source_quality=source.source_quality,
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.excerpts_allowed,
        review_status=SourceReviewStatus.approved,
        approval_rationale="Economic indicator source is source-labeled and citation-bound.",
        parser_status=SourceParserStatus.parsed,
    ).model_dump(mode="json")


def _lightweight_fact_citation_id(fact: Any, source_id: str) -> str:
    source_ids = list(getattr(fact, "source_document_ids", []) or [])
    citation_ids = list(getattr(fact, "citation_ids", []) or [])
    if source_id in source_ids and len(citation_ids) == len(source_ids):
        return str(citation_ids[source_ids.index(source_id)])
    if citation_ids:
        return str(citation_ids[0])
    suffix = source_id.replace("src_", "").replace("lw_", "").replace("/", "_")
    return f"c_{fact.fact_id}_{suffix}"


def _lightweight_source_type(source: Any) -> str:
    if source.source_type in {"sec_company_tickers_exchange", "sec_submissions", "sec_companyfacts"}:
        return "sec_filing"
    if source.source_type == "provider_market_reference":
        return "structured_market_data"
    if source.source_type == "yahoo_finance_weekly_news_metadata":
        return "recent_development"
    return source.source_type


def _supported_claim_types_for_fact(field_name: str) -> list[str]:
    if field_name in {"canonical_asset_identity", "sec_identity", "etf_identity", "benchmark", "expense_ratio", "holdings_count"}:
        return ["factual", "interpretation"]
    if field_name in {"provider_price_chart", "provider_market_price", "provider_quote_stats"}:
        return ["factual", "interpretation"]
    if field_name == "lightweight_weekly_news_context":
        return ["recent", "interpretation", "risk", "factual"]
    return ["factual", "interpretation", "risk"]


def _compact_value(value: Any) -> str:
    if isinstance(value, dict):
        text = ", ".join(f"{key}: {_compact_value(item)}" for key, item in sorted(value.items())[:10])
    elif isinstance(value, list):
        text = "; ".join(_compact_value(item) for item in value[:8])
    else:
        text = str(value)
    return _truncate(text)


def _truncate(value: Any, limit: int = MAX_PROMPT_TEXT_CHARS) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(item) for item in value if str(item).strip()]


def _rules() -> dict[str, Any]:
    return {
        "use_supplied_evidence_only": True,
        "raw_article_text_allowed": False,
        "raw_provider_payload_allowed": False,
        "raw_ohlcv_series_allowed": False,
        "numeric_claims_must_match_allowed_numeric_facts": True,
        "stable_facts_separate_from_market_and_weekly_news": True,
        "no_buy_sell_hold_allocation_tax_brokerage_or_price_target": True,
        "style": "analytical_plain_english",
    }
