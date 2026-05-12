from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.models import (
    AssetType,
    EvidenceState,
    FreshnessState,
    LightweightFetchFact,
    LightweightFetchResponse,
    LightweightFetchSource,
    LightweightSourceLabel,
    SourceAllowlistStatus,
    SourceExportRights,
    SourceQuality,
    SourceParserStatus,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    WeeklyNewsEventType,
)
from backend.weekly_news import (
    MINIMUM_AI_ANALYSIS_ITEMS,
    build_weekly_news_focus_from_pack,
    read_persisted_weekly_news_focus,
)
from backend.weekly_news_repository import (
    InMemoryWeeklyNewsEventEvidenceRepository,
    WeeklyNewsEventEvidenceContractError,
    WeeklyNewsEventCandidateRow,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
)
from backend.source_policy import SourcePolicyAction, validate_source_handoff


WEEKLY_NEWS_SOURCE_ADAPTER_BOUNDARY = "weekly-news-source-adapter-v1"
YAHOO_FINANCE_WEEKLY_NEWS_PROVIDER_NAME = "Yahoo Finance/yfinance-derived news"
LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD = "provider_weekly_news_event"
YAHOO_WEEKLY_NEWS_RIGHTS_NOTE = (
    "Yahoo Finance/yfinance-derived news metadata is a source-labeled fallback for Weekly News Focus. "
    "Only metadata and bounded summaries are used; raw article text, thumbnails, and provider payloads are not displayed or exported."
)

_ADVICE_LIKE_TITLE_MARKERS = (
    " to buy ",
    "before it soars",
    "better buy",
    "buy right now",
    "invest $",
    "should you buy",
    "should i buy",
    "should you invest",
    "should i invest",
    "worth buying",
    "stocks to buy",
    "etfs to buy",
    "buy now",
    "sell now",
    "sell alert",
    "trade ",
    "trading ",
)


@dataclass(frozen=True)
class WeeklyNewsSourceAdapterResult:
    boundary: str
    ticker: str
    sources: list[LightweightFetchSource]
    facts: list[LightweightFetchFact]
    candidate_count: int
    suppressed_count: int
    no_live_external_calls: bool
    suppression_reason_counts: dict[str, int] = field(default_factory=dict)
    raw_article_text_collected: bool = False
    raw_provider_payload_exposed: bool = False
    thumbnail_or_media_forwarded: bool = False


def yahoo_search_payload_to_weekly_news_facts(
    *,
    ticker: str,
    asset_type: AssetType,
    payload: dict[str, Any],
    retrieved_at: str,
    no_live_external_calls: bool,
    max_items: int = 24,
    provider_name: str = YAHOO_FINANCE_WEEKLY_NEWS_PROVIDER_NAME,
    source_type: str = "yahoo_finance_weekly_news_metadata",
    source_id_prefix: str = "lw_yahoo",
    rights_note: str = YAHOO_WEEKLY_NEWS_RIGHTS_NOTE,
    source_rank_tier: WeeklyNewsSourceRankTier = WeeklyNewsSourceRankTier.provider_context,
    source_quality: SourceQuality = SourceQuality.provider,
    source_label: LightweightSourceLabel = LightweightSourceLabel.provider_derived,
) -> WeeklyNewsSourceAdapterResult:
    """Convert rights-safe provider news metadata into lightweight Weekly News facts."""

    normalized = _normalize_ticker(ticker)
    sources: list[LightweightFetchSource] = []
    facts: list[LightweightFetchFact] = []
    suppressed = 0
    raw_items = payload.get("news")
    if not isinstance(raw_items, list):
        raw_items = []
    suppression_reason_counts: dict[str, int] = {}

    for index, item in enumerate(raw_items):
        if len(facts) >= max_items:
            break
        if not isinstance(item, dict):
            suppressed += 1
            _increment_reason(suppression_reason_counts, "invalid_provider_item")
            continue
        title = _clean_text(item.get("title"))
        publisher = _clean_text(item.get("publisher")) or provider_name
        url = _clean_text(item.get("link"))
        if not title or not url:
            suppressed += 1
            _increment_reason(suppression_reason_counts, "missing_required_metadata")
            continue
        if _is_advice_like_title(title):
            suppressed += 1
            _increment_reason(suppression_reason_counts, "advice_like")
            continue
        if not _item_matches_ticker(item, normalized, title):
            suppressed += 1
            _increment_reason(suppression_reason_counts, "weak_ticker_match")
            continue

        published_at = _published_at(item)
        event_date = published_at[:10] if published_at else retrieved_at[:10]
        event_type = _classify_event_type(title, asset_type)
        summary = _summary_for_item(
            item,
            ticker=normalized,
            event_type=event_type,
            provider_name=provider_name,
        )
        if summary is None:
            suppressed += 1
            _increment_reason(suppression_reason_counts, "metadata_only_without_useful_summary")
            continue
        safe_id = _safe_id(str(item.get("uuid") or f"{normalized}-{index}-{title}"))
        source_document_id = f"{source_id_prefix}_{normalized.lower()}_weekly_news_{safe_id}"
        source = LightweightFetchSource(
            source_document_id=source_document_id,
            source_label=source_label,
            source_type=source_type,
            title=title,
            publisher=publisher,
            url=url,
            is_official=False,
            source_quality=source_quality,
            source_use_policy=SourceUsePolicy.summary_allowed,
            allowlist_status=SourceAllowlistStatus.allowed,
            published_at=published_at,
            as_of_date=event_date,
            retrieved_at=retrieved_at,
            date_precision="day",
            freshness_state=FreshnessState.fresh,
            fallback_reason="Official Weekly News Focus sources were sparse or incomplete for this local MVP request.",
            rights_note=rights_note,
            export_allowed=False,
        )
        sources.append(source)
        facts.append(
            LightweightFetchFact(
                fact_id=f"lw_weekly_news_{normalized.lower()}_{safe_id}",
                field_name=LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD,
                value={
                    "adapter_boundary": WEEKLY_NEWS_SOURCE_ADAPTER_BOUNDARY,
                    "event_id": f"provider_weekly_news_{normalized.lower()}_{safe_id}",
                    "title": title,
                    "summary": summary,
                    "summary_is_metadata_only": _summary_is_metadata_only(item),
                    "publisher": publisher,
                    "url": url,
                    "published_at": published_at,
                    "event_date": event_date,
                    "event_type": event_type.value,
                    "source_rank_tier": source_rank_tier.value,
                    "source_label": source_label.value,
                    "source_quality": source_quality.value,
                    "source_use_policy": SourceUsePolicy.summary_allowed.value,
                    "official_source": False,
                    "ticker_match": "exact_or_related_ticker",
                    "raw_article_text_collected": False,
                    "thumbnail_or_media_forwarded": False,
                    "provider_name": provider_name,
                },
                evidence_state=EvidenceState.supported,
                freshness_state=FreshnessState.fresh,
                as_of_date=event_date,
                retrieved_at=retrieved_at,
                source_document_ids=[source_document_id],
                source_labels=[LightweightSourceLabel.provider_derived],
                fallback_used=True,
                limitations=(
                    "Provider-derived Weekly News metadata is context only; it is not official evidence and "
                    "does not redefine stable asset facts."
                ),
            )
        )

    return WeeklyNewsSourceAdapterResult(
        boundary=WEEKLY_NEWS_SOURCE_ADAPTER_BOUNDARY,
        ticker=normalized,
        sources=sources,
        facts=facts,
        candidate_count=len(facts),
        suppressed_count=suppressed,
        no_live_external_calls=no_live_external_calls,
        suppression_reason_counts=suppression_reason_counts,
    )


def build_lightweight_weekly_news_focus(response: LightweightFetchResponse):
    """Build a Weekly News Focus response from selected lightweight Weekly News facts."""

    candidates = weekly_news_candidate_rows_from_lightweight_response(response)
    candidates = [
        candidate
        for candidate in candidates
        if validate_source_handoff(candidate, action=SourcePolicyAction.generated_claim_support).allowed
    ]
    if not candidates:
        return None

    as_of = response.freshness.page_last_updated_at
    include_current_day = not response.no_live_external_calls
    try:
        records = acquire_weekly_news_event_evidence_from_fixtures(
            asset_ticker=response.asset.ticker,
            as_of=as_of,
            created_at=response.freshness.page_last_updated_at,
            candidates=candidates,
            minimum_ai_analysis_item_count=MINIMUM_AI_ANALYSIS_ITEMS,
            include_current_day=include_current_day,
        )
    except WeeklyNewsEventEvidenceContractError:
        return None
    repo = InMemoryWeeklyNewsEventEvidenceRepository()
    repo.persist(records)
    read = read_persisted_weekly_news_focus(
        response.asset,
        as_of=as_of,
        persisted_event_reader=repo,
    )
    if not read.found or read.weekly_news_focus is None:
        return None
    return read.weekly_news_focus.model_copy(
        update={
            "no_live_external_calls": response.no_live_external_calls,
            "selection_diagnostics": {
                **read.weekly_news_focus.selection_diagnostics,
                "window_policy": "local_live_current_day" if include_current_day else "strict_completed_day",
                "includes_current_day": include_current_day,
            },
        }
    )


def weekly_news_candidate_rows_from_lightweight_response(
    response: LightweightFetchResponse,
) -> list[WeeklyNewsEventCandidateRow]:
    sources_by_id = {source.source_document_id: source for source in response.sources}
    candidates: list[WeeklyNewsEventCandidateRow] = _official_weekly_news_candidate_rows(response, sources_by_id)
    for index, fact in enumerate(response.facts):
        if fact.field_name != LIGHTWEIGHT_WEEKLY_NEWS_FACT_FIELD or not isinstance(fact.value, dict):
            continue
        source = _first_source_for_fact(fact, sources_by_id)
        if source is None:
            continue
        value = fact.value
        event_id = _clean_text(value.get("event_id")) or fact.fact_id
        title = _clean_text(value.get("title")) or source.title
        summary = _clean_text(value.get("summary")) or f"Source-labeled Weekly News metadata for {response.asset.ticker}."
        published_at = _clean_text(value.get("published_at")) or source.published_at
        event_date = _clean_text(value.get("event_date")) or source.as_of_date or (published_at[:10] if published_at else response.freshness.page_last_updated_at[:10])
        citation_ids = list(fact.citation_ids) or [f"lw_cite_{source.source_document_id.removeprefix('lw_')}"]
        checksum_payload = {
            "event_id": event_id,
            "title": title,
            "summary": summary,
            "publisher": source.publisher,
            "url": source.url,
            "published_at": published_at,
            "event_date": event_date,
        }
        source_rank_tier = _source_rank_tier_for_source(source, value)
        candidates.append(
            WeeklyNewsEventCandidateRow(
                candidate_event_id=event_id,
                window_id="pending",
                asset_ticker=response.asset.ticker,
                source_asset_ticker=response.asset.ticker,
                event_type=_coerce_event_type(value.get("event_type"), response.asset.asset_type).value,
                event_title=title,
                event_summary=summary,
                event_date=event_date,
                published_at=published_at,
                retrieved_at=source.retrieved_at or response.freshness.page_last_updated_at,
                period_bucket="previous_market_week",
                source_document_id=source.source_document_id,
                source_chunk_id=f"chk_{fact.fact_id}",
                citation_ids=citation_ids,
                citation_asset_tickers={citation_id: response.asset.ticker for citation_id in citation_ids},
                source_type=source.source_type,
                source_title=source.title,
                source_publisher=source.publisher,
                source_url=source.url,
                source_rank=source_rank_tier_priority_for_adapter(source_rank_tier, index),
                source_rank_tier=source_rank_tier.value,
                source_quality=source.source_quality.value,
                allowlist_status=source.allowlist_status.value,
                source_use_policy=source.source_use_policy.value,
                source_identity=source.url or source.source_document_id,
                is_official=source.is_official,
                storage_rights=SourceStorageRights.summary_allowed.value,
                export_rights=SourceExportRights.excerpts_allowed.value,
                review_status=SourceReviewStatus.approved.value,
                approval_rationale=(
                    "Local MVP Weekly News fallback uses source-labeled metadata and bounded summaries only; "
                    "it cannot support canonical facts."
                ),
                parser_status=SourceParserStatus.parsed.value,
                freshness_state=source.freshness_state.value,
                evidence_state=fact.evidence_state.value,
                importance_score=0,
                high_signal=True,
                important_event_claim=True,
                license_allowed=True,
                recognized_source=True,
                promotional=False,
                irrelevant=False,
                duplicate_group_id=_duplicate_group_id(response.asset.ticker, title, event_date),
                title_checksum=_checksum({"title": title}),
                evidence_checksum=_checksum(checksum_payload),
                stores_raw_article_text=False,
                stores_raw_provider_payload=False,
                stores_unrestricted_source_text=False,
                stores_secret=False,
            )
        )
    return candidates


def _official_weekly_news_candidate_rows(
    response: LightweightFetchResponse,
    sources_by_id: dict[str, LightweightFetchSource],
) -> list[WeeklyNewsEventCandidateRow]:
    candidates: list[WeeklyNewsEventCandidateRow] = []
    for index, fact in enumerate(response.facts):
        if fact.field_name not in {
            "latest_sec_filing",
            "stock_official_ir_release",
            "investor_presentation_reference",
            "etf_fact_sheet_metadata",
            "prospectus_reference",
            "issuer_announcement",
            "issuer_holdings_update",
            "issuer_shareholder_report",
        }:
            continue
        if LightweightSourceLabel.official not in fact.source_labels:
            continue
        source = _first_source_for_fact(fact, sources_by_id)
        if source is None:
            continue
        value = fact.value if isinstance(fact.value, dict) else {}
        if fact.field_name == "latest_sec_filing":
            form_type = _clean_text(value.get("form_type")) or "filing"
            event_date = _clean_text(value.get("filing_date")) or fact.as_of_date or source.as_of_date
            title = f"{response.asset.ticker} filed latest {form_type} with the SEC"
            summary = (
                f"Official SEC metadata shows a latest {form_type} filing for {response.asset.ticker}; "
                "use it as recent context separate from stable company facts."
            )
            event_type = WeeklyNewsEventType.regulatory_event
            rank_tier = WeeklyNewsSourceRankTier.official_filing
        elif fact.field_name in {"stock_official_ir_release", "investor_presentation_reference"}:
            event_date = _clean_text(value.get("published_at")) or _clean_text(value.get("event_date")) or fact.as_of_date or source.as_of_date
            title = _clean_text(value.get("title")) or f"{response.asset.ticker} official investor-relations update is available"
            summary = (
                _clean_text(value.get("summary"))
                or f"Official investor-relations metadata is available for {response.asset.ticker}; read it as recent context separate from stable facts."
            )
            event_type = _coerce_event_type(value.get("event_type"), response.asset.asset_type)
            rank_tier = WeeklyNewsSourceRankTier.investor_relations_release
        elif fact.field_name == "prospectus_reference":
            event_date = _clean_text(value.get("publication_date")) or fact.as_of_date or source.as_of_date
            title = f"{response.asset.ticker} official prospectus reference is available"
            summary = (
                f"Official issuer metadata includes a prospectus reference for {response.asset.ticker}; "
                "this is issuer context, not a recommendation."
            )
            event_type = WeeklyNewsEventType.sponsor_update
            rank_tier = WeeklyNewsSourceRankTier.prospectus_update
        elif fact.field_name in {"issuer_announcement", "issuer_shareholder_report"}:
            event_date = _clean_text(value.get("published_at")) or _clean_text(value.get("event_date")) or fact.as_of_date or source.as_of_date
            title = _clean_text(value.get("title")) or f"{response.asset.ticker} official issuer announcement is available"
            summary = (
                _clean_text(value.get("summary"))
                or f"Official issuer metadata is available for {response.asset.ticker}; this is fund context separate from stable facts."
            )
            event_type = WeeklyNewsEventType.sponsor_update
            rank_tier = WeeklyNewsSourceRankTier.etf_issuer_announcement
        elif fact.field_name == "issuer_holdings_update":
            event_date = _clean_text(value.get("as_of_date")) or fact.as_of_date or source.as_of_date
            title = f"{response.asset.ticker} official holdings or exposure metadata changed"
            summary = (
                f"Official issuer metadata includes holdings or exposure evidence for {response.asset.ticker}; "
                "use it as fund context, not a recommendation."
            )
            event_type = WeeklyNewsEventType.sponsor_update
            rank_tier = WeeklyNewsSourceRankTier.fact_sheet_change
        else:
            event_date = _clean_text(value.get("as_of_date")) or fact.as_of_date or source.as_of_date
            title = f"{response.asset.ticker} official issuer fact sheet metadata is available"
            summary = (
                f"Official issuer metadata includes fact-sheet fields for {response.asset.ticker}; "
                "provider news remains fallback context when official weekly items are sparse."
            )
            event_type = WeeklyNewsEventType.sponsor_update
            rank_tier = WeeklyNewsSourceRankTier.fact_sheet_change
        if not event_date:
            continue
        published_at = source.published_at or f"{event_date}T00:00:00Z"
        citation_ids = list(fact.citation_ids) or [f"lw_cite_{source.source_document_id.removeprefix('lw_')}"]
        event_id = f"official_weekly_news_{response.asset.ticker.lower()}_{fact.field_name}_{index}"
        checksum_payload = {
            "event_id": event_id,
            "title": title,
            "summary": summary,
            "publisher": source.publisher,
            "url": source.url,
            "published_at": published_at,
            "event_date": event_date,
        }
        candidates.append(
            WeeklyNewsEventCandidateRow(
                candidate_event_id=event_id,
                window_id="pending",
                asset_ticker=response.asset.ticker,
                source_asset_ticker=response.asset.ticker,
                event_type=event_type.value,
                event_title=title,
                event_summary=summary,
                event_date=event_date,
                published_at=published_at,
                retrieved_at=source.retrieved_at or response.freshness.page_last_updated_at,
                period_bucket="previous_market_week",
                source_document_id=source.source_document_id,
                source_chunk_id=f"chk_{fact.fact_id}",
                citation_ids=citation_ids,
                citation_asset_tickers={citation_id: response.asset.ticker for citation_id in citation_ids},
                source_type=source.source_type,
                source_title=source.title,
                source_publisher=source.publisher,
                source_url=source.url,
                source_rank=source_rank_tier_priority_for_adapter(rank_tier, index),
                source_rank_tier=rank_tier.value,
                source_quality=source.source_quality.value,
                allowlist_status=source.allowlist_status.value,
                source_use_policy=source.source_use_policy.value,
                source_identity=source.url or source.source_document_id,
                is_official=True,
                storage_rights=SourceStorageRights.summary_allowed.value,
                export_rights=SourceExportRights.excerpts_allowed.value,
                review_status=SourceReviewStatus.approved.value,
                approval_rationale="Official lightweight source metadata is used as Weekly News context without exposing raw source text.",
                parser_status=SourceParserStatus.parsed.value,
                freshness_state=source.freshness_state.value,
                evidence_state=fact.evidence_state.value,
                importance_score=0,
                high_signal=True,
                important_event_claim=True,
                license_allowed=True,
                recognized_source=True,
                promotional=False,
                irrelevant=False,
                duplicate_group_id=_duplicate_group_id(response.asset.ticker, title, event_date),
                title_checksum=_checksum({"title": title}),
                evidence_checksum=_checksum(checksum_payload),
                stores_raw_article_text=False,
                stores_raw_provider_payload=False,
                stores_unrestricted_source_text=False,
                stores_secret=False,
            )
        )
    return candidates


def source_rank_tier_priority_for_adapter(tier: WeeklyNewsSourceRankTier, index: int) -> int:
    base = {
        WeeklyNewsSourceRankTier.official_filing: 1,
        WeeklyNewsSourceRankTier.investor_relations_release: 2,
        WeeklyNewsSourceRankTier.etf_issuer_announcement: 3,
        WeeklyNewsSourceRankTier.prospectus_update: 4,
        WeeklyNewsSourceRankTier.fact_sheet_change: 5,
        WeeklyNewsSourceRankTier.allowlisted_news: 20,
        WeeklyNewsSourceRankTier.provider_context: 30,
        WeeklyNewsSourceRankTier.unknown: 99,
    }[tier]
    return base + index


def _first_source_for_fact(
    fact: LightweightFetchFact,
    sources_by_id: dict[str, LightweightFetchSource],
) -> LightweightFetchSource | None:
    for source_id in fact.source_document_ids:
        source = sources_by_id.get(source_id)
        if source is not None:
            return source
    return None


def _source_rank_tier_for_source(source: LightweightFetchSource, value: dict[str, Any]) -> WeeklyNewsSourceRankTier:
    explicit = value.get("source_rank_tier")
    if explicit:
        try:
            return WeeklyNewsSourceRankTier(str(explicit))
        except ValueError:
            pass
    if source.is_official and source.source_type.startswith("sec"):
        return WeeklyNewsSourceRankTier.official_filing
    if source.is_official and "issuer" in source.source_type:
        return WeeklyNewsSourceRankTier.etf_issuer_announcement
    if source.source_quality is SourceQuality.allowlisted:
        return WeeklyNewsSourceRankTier.allowlisted_news
    return WeeklyNewsSourceRankTier.provider_context


def _published_at(item: dict[str, Any]) -> str | None:
    raw_time = item.get("providerPublishTime") or item.get("published_at") or item.get("publishedAt")
    if raw_time is None:
        return None
    if isinstance(raw_time, (int, float)):
        return datetime.fromtimestamp(float(raw_time), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    text = _clean_text(raw_time)
    return text


def _summary_for_item(
    item: dict[str, Any],
    *,
    ticker: str,
    event_type: WeeklyNewsEventType,
    provider_name: str,
) -> str | None:
    snippet = _clean_text(item.get("summary") or item.get("snippet"))
    if snippet:
        return _bounded_words(snippet, 36)
    title = _clean_text(item.get("title"))
    if not title or not _title_has_useful_news_hook(title, event_type):
        return None
    event_label = event_type.value.replace("_", " ")
    return (
        f"{provider_name} supplied headline-only {event_label} metadata for {ticker}: "
        f"{_bounded_words(title, 18)}. Treat it as source-labeled context, not an article summary."
    )


def _item_matches_ticker(item: dict[str, Any], ticker: str, title: str) -> bool:
    related = item.get("relatedTickers") or item.get("related_tickers")
    if isinstance(related, list) and related:
        return ticker in {_normalize_ticker(str(value)) for value in related}
    return ticker in title.upper()


def _summary_is_metadata_only(item: dict[str, Any]) -> bool:
    return _clean_text(item.get("summary") or item.get("snippet")) is None


def _title_has_useful_news_hook(title: str, event_type: WeeklyNewsEventType) -> bool:
    text = f" {title.lower()} "
    if event_type is not WeeklyNewsEventType.other:
        return True
    markers = (
        "earnings",
        "revenue",
        "guidance",
        "product",
        "launch",
        "data center",
        "customer",
        "regulatory",
        "filing",
        "expense ratio",
        "fee",
        "flow",
        "holding",
        "holdings",
        "index",
        "rebalance",
        "distribution",
        "dividend",
        "benchmark",
        "prospectus",
    )
    return any(marker in text for marker in markers)


def _classify_event_type(title: str, asset_type: AssetType) -> WeeklyNewsEventType:
    text = title.lower()
    if "earnings" in text or "revenue" in text:
        return WeeklyNewsEventType.earnings
    if "guidance" in text or "outlook" in text:
        return WeeklyNewsEventType.guidance
    if "fee" in text or "expense ratio" in text:
        return WeeklyNewsEventType.fee_change
    if "methodology" in text:
        return WeeklyNewsEventType.methodology_change
    if "index" in text or "rebalance" in text:
        return WeeklyNewsEventType.index_change
    if "merger" in text or "acquisition" in text:
        return WeeklyNewsEventType.fund_merger if asset_type is AssetType.etf else WeeklyNewsEventType.merger_acquisition
    if "liquidat" in text or "shutdown" in text or "closure" in text:
        return WeeklyNewsEventType.fund_liquidation if asset_type is AssetType.etf else WeeklyNewsEventType.other
    if "flow" in text or "liquidity" in text:
        return WeeklyNewsEventType.large_flow_event
    if asset_type is AssetType.etf:
        return WeeklyNewsEventType.sponsor_update
    if "product" in text or "launch" in text:
        return WeeklyNewsEventType.product_announcement
    return WeeklyNewsEventType.other


def _coerce_event_type(value: Any, asset_type: AssetType) -> WeeklyNewsEventType:
    try:
        return WeeklyNewsEventType(str(value))
    except (TypeError, ValueError):
        return _classify_event_type("", asset_type)


def _is_advice_like_title(title: str) -> bool:
    text = f" {title.lower()} "
    return any(marker in text for marker in _ADVICE_LIKE_TITLE_MARKERS)


def _increment_reason(counts: dict[str, int], reason: str) -> None:
    counts[reason] = counts.get(reason, 0) + 1


def _duplicate_group_id(ticker: str, title: str, event_date: str) -> str:
    normalized_title = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    return f"weekly-news:{_normalize_ticker(ticker)}:{event_date}:{normalized_title}"


def _checksum(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if not cleaned:
        cleaned = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return cleaned[:48]


def _bounded_words(text: str, max_words: int) -> str:
    words = text.split()
    return " ".join(words[:max_words])


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()
