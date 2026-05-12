from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Protocol
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from backend.models import (
    Citation,
    EvidenceState,
    EconomicIndicatorsPackResponse,
    FreshnessState,
    MarketAIAnalysisSection,
    MarketAIComprehensiveAnalysisResponse,
    MarketNewsAuditMetadata,
    MarketNewsClusterMetadata,
    MarketNewsFocusResponse,
    MarketNewsItem,
    MarketNewsResponse,
    MarketNewsSelectionRationale,
    MarketNewsTopicBucket,
    SourceAllowlistStatus,
    SourceDocument,
    SourceExportRights,
    SourceOperationPermissions,
    SourceParserStatus,
    SourceQuality,
    SourceReviewStatus,
    SourceStorageRights,
    SourceUsePolicy,
    StateMessage,
    WeeklyNewsContractState,
    WeeklyNewsEmptyState,
    WeeklyNewsEvidenceLimitedState,
    WeeklyNewsSourceMetadata,
)
from backend.generation_evidence import evidence_pack_from_market_news
from backend.news_quality import clean_news_publisher, news_source_from_domain, publisher_priority
from backend.safety import find_forbidden_output_phrases
from backend.settings import MarketNewsSettings, build_market_news_settings
from backend.summary_generation import (
    HybridSummaryGenerationService,
    SummaryGenerationContractError,
    SummaryGenerationService,
    build_default_summary_generation_service,
)
from backend.weekly_news import DEFAULT_WEEKLY_NEWS_AS_OF, compute_weekly_news_window


MARKET_NEWS_SOURCE_ADAPTER_BOUNDARY = "market-news-source-adapter-v1"
MARKET_NEWS_SELECTION_BOUNDARY = "market-news-selection-v1"
MARKET_NEWS_RESPONSE_BOUNDARY = "market-news-response-v1"
MAX_MARKET_NEWS_ITEMS = 20
MINIMUM_MARKET_AI_ITEMS = 5
MINIMUM_MARKET_AI_BUCKETS = 3
MINIMUM_MARKET_DISPLAY_SCORE = 45

_TIER1_SOURCE_PRIORITY = {
    "reuters": 1,
    "associated press": 2,
    "ap": 2,
    "bloomberg": 3,
    "wall street journal": 4,
    "wsj": 4,
    "financial times": 5,
    "ft": 5,
    "cnbc": 8,
    "barron's": 9,
    "barrons": 9,
    "marketwatch": 10,
    "bbc": 11,
    "cnn": 12,
    "the new york times": 13,
    "new york times": 13,
    "the washington post": 14,
    "washington post": 14,
    "the guardian": 15,
    "guardian": 15,
    "the economist": 16,
    "economist": 16,
    "nikkei asia": 17,
    "nikkei": 17,
    "yahoo finance": 18,
    "morningstar": 19,
    "nasdaq": 20,
    "s&p global": 21,
    "investing.com": 22,
    "investing": 22,
    "business insider": 23,
    "fortune": 24,
    "axios": 25,
    "pr newswire": 26,
    "globenewswire": 27,
    "benzinga": 28,
}
_CRITICAL_SOURCE_PRIORITY_CUTOFF = 5
_TOPIC_QUERIES = {
    MarketNewsTopicBucket.macro_fed: "Federal Reserve inflation labor Treasury yields US macro",
    MarketNewsTopicBucket.markets_earnings: "US equity markets earnings S&P 500 Nasdaq sectors",
    MarketNewsTopicBucket.ai_technology_semiconductors: "AI semiconductors big tech data centers chips",
    MarketNewsTopicBucket.geopolitics_energy_supply_chain: "geopolitics energy oil shipping supply chain",
    MarketNewsTopicBucket.credit_liquidity_sentiment: "credit banks dollar liquidity consumer stress",
}
_BUCKET_TARGETS = {
    MarketNewsTopicBucket.macro_fed: 5,
    MarketNewsTopicBucket.markets_earnings: 4,
    MarketNewsTopicBucket.ai_technology_semiconductors: 4,
    MarketNewsTopicBucket.geopolitics_energy_supply_chain: 4,
    MarketNewsTopicBucket.credit_liquidity_sentiment: 3,
}
_TOPIC_KEYWORDS = {
    MarketNewsTopicBucket.macro_fed: (
        "federal reserve",
        "fed ",
        "rate cut",
        "rate hike",
        "interest rate",
        "inflation",
        "cpi",
        "labor market",
        "jobs report",
        "treasury yield",
        "bond yield",
        "us macro",
    ),
    MarketNewsTopicBucket.markets_earnings: (
        "s&p 500",
        "nasdaq",
        "dow",
        "wall street",
        "stocks",
        "equities",
        "earnings",
        "results",
        "sectors",
        "market rally",
        "market selloff",
        "record high",
    ),
    MarketNewsTopicBucket.ai_technology_semiconductors: (
        " ai ",
        "artificial intelligence",
        "semiconductor",
        "chip",
        "chips",
        "nvidia",
        "amd",
        "broadcom",
        "data center",
        "datacenter",
        "cloud",
    ),
    MarketNewsTopicBucket.geopolitics_energy_supply_chain: (
        "oil",
        "crude",
        "energy",
        "opec",
        "war",
        "iran",
        "gulf",
        "hormuz",
        "port",
        "red sea",
        "shipping",
        "supply chain",
        "trade",
        "tariff",
        "sanction",
        "geopolit",
    ),
    MarketNewsTopicBucket.credit_liquidity_sentiment: (
        "credit",
        "liquidity",
        "bank",
        "banks",
        "dollar",
        "debt",
        "loan",
        "consumer stress",
        "defaults",
        "spread",
        "sentiment",
    ),
}
_CRITICAL_MARKERS = (
    "federal reserve",
    "fed ",
    "rate",
    "war",
    "sanction",
    "tariff",
    "missile",
    "invasion",
    "opec",
    "oil",
    "bank failure",
)
_PROMOTIONAL_MARKERS = (
    "sponsored",
    "press release",
    "advertisement",
    "buy now",
    "sell now",
    "stocks to buy",
    "should you buy",
    "price target",
)
_OPINION_MARKERS = ("opinion:", "column:", "editorial:", "op-ed")


class MarketNewsContractError(ValueError):
    """Raised when Market News Focus contracts are violated."""


class MarketNewsFetchError(RuntimeError):
    """Raised when an opt-in Market News source request fails."""


class MarketNewsFetcher(Protocol):
    no_live_external_calls: bool

    def fetch_json(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> Any:
        ...

    def fetch_text(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> str:
        ...


@dataclass(frozen=True)
class MarketNewsArticleCandidate:
    article_id: str
    provider: str
    source: str
    source_domain: str
    title: str
    description: str
    url: str
    canonical_url: str
    published_at: str
    retrieved_at: str
    language: str
    topic_bucket: MarketNewsTopicBucket
    entities: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    source_quality: SourceQuality = SourceQuality.allowlisted
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed
    source_use_policy: SourceUsePolicy = SourceUsePolicy.summary_allowed
    license_allowed: bool = True
    source_priority: int = 99


@dataclass(frozen=True)
class MarketNewsStoryCluster:
    cluster_id: str
    representative: MarketNewsArticleCandidate
    articles: tuple[MarketNewsArticleCandidate, ...]
    suppressed_duplicate_count: int
    critical_claim: bool
    corroborated: bool
    rationale: MarketNewsSelectionRationale


@dataclass(frozen=True)
class MarketNewsAdapterResult:
    provider: str
    candidates: tuple[MarketNewsArticleCandidate, ...]
    skipped_reason: str | None = None
    no_live_external_calls: bool = True


@dataclass(frozen=True)
class MarketNewsProviderAdapter:
    provider: str
    credential_name: str | None
    parser: str

    def collect(
        self,
        *,
        fetcher: MarketNewsFetcher,
        settings: MarketNewsSettings,
        topic_bucket: MarketNewsTopicBucket,
        as_of: str | date | datetime,
        retrieved_at: str,
    ) -> MarketNewsAdapterResult:
        credential = settings.credential_for(self.credential_name) if self.credential_name else None
        if self.credential_name and not credential:
            return MarketNewsAdapterResult(
                provider=self.provider,
                candidates=(),
                skipped_reason="provider_credential_not_configured",
                no_live_external_calls=True,
            )
        url = _provider_url(self.provider, topic_bucket, credential)
        if self.parser == "rss":
            text = fetcher.fetch_text(url, timeout_seconds=settings.fetch_timeout_seconds)
            candidates = _parse_rss_candidates(
                text,
                provider=self.provider,
                topic_bucket=topic_bucket,
                retrieved_at=retrieved_at,
            )
        else:
            payload = fetcher.fetch_json(url, timeout_seconds=settings.fetch_timeout_seconds)
            candidates = _parse_json_candidates(
                payload,
                provider=self.provider,
                topic_bucket=topic_bucket,
                retrieved_at=retrieved_at,
            )
        return MarketNewsAdapterResult(
            provider=self.provider,
            candidates=tuple(candidates),
            no_live_external_calls=fetcher.no_live_external_calls,
        )


@dataclass
class FixtureMarketNewsFetcher:
    payloads_by_provider: dict[str, Any] = field(default_factory=dict)
    no_live_external_calls: bool = True

    def fetch_json(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> Any:
        del headers, timeout_seconds
        provider = _provider_from_url(url)
        payload = self.payloads_by_provider.get(provider)
        if payload is None:
            return {}
        if isinstance(payload, (dict, list)):
            return payload
        raise MarketNewsFetchError(f"Fixture JSON payload for {provider} is not JSON-compatible metadata.")

    def fetch_text(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> str:
        del headers, timeout_seconds
        provider = _provider_from_url(url)
        payload = self.payloads_by_provider.get(provider)
        return payload if isinstance(payload, str) else ""


def market_news_provider_adapters() -> tuple[MarketNewsProviderAdapter, ...]:
    return (
        MarketNewsProviderAdapter("rss", None, "rss"),
        MarketNewsProviderAdapter("google_news_rss", None, "rss"),
        MarketNewsProviderAdapter("gdelt", None, "json"),
        MarketNewsProviderAdapter("marketaux", "marketaux", "json"),
        MarketNewsProviderAdapter("alpha_vantage", "alpha_vantage", "json"),
        MarketNewsProviderAdapter("finnhub", "finnhub", "json"),
        MarketNewsProviderAdapter("guardian", "guardian", "json"),
        MarketNewsProviderAdapter("gnews", "gnews", "json"),
        MarketNewsProviderAdapter("mediastack", "mediastack", "json"),
        MarketNewsProviderAdapter("newsapi", "newsapi", "json"),
        MarketNewsProviderAdapter("yahoo_finance_search", None, "json"),
    )


def build_market_news_response(
    *,
    as_of: str | date | datetime = DEFAULT_WEEKLY_NEWS_AS_OF,
    candidates: list[MarketNewsArticleCandidate] | None = None,
    settings: MarketNewsSettings | None = None,
    fetcher: MarketNewsFetcher | None = None,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
) -> MarketNewsResponse:
    settings = settings or build_market_news_settings()
    retrieved_at = _retrieved_at_for_as_of(as_of)
    if candidates is None:
        if settings.can_attempt_live_fetch and fetcher is not None:
            candidates = collect_market_news_candidates(
                fetcher=fetcher,
                settings=settings,
                as_of=as_of,
                retrieved_at=retrieved_at,
            )
        else:
            candidates = fixture_market_news_candidates(as_of=as_of, retrieved_at=retrieved_at)

    focus = select_market_news_focus(
        candidates,
        as_of=as_of,
        no_live_external_calls=(fetcher.no_live_external_calls if fetcher is not None else True),
    )
    analysis = build_market_ai_comprehensive_analysis(focus, economic_indicators=economic_indicators)
    return MarketNewsResponse(
        state=StateMessage(
            status="supported",
            message="Market News Focus is available as reusable timely context separate from ticker-specific facts.",
        ),
        market_news_focus=focus,
        market_ai_comprehensive_analysis=analysis,
    )


def collect_market_news_candidates(
    *,
    fetcher: MarketNewsFetcher,
    settings: MarketNewsSettings,
    as_of: str | date | datetime,
    retrieved_at: str,
) -> list[MarketNewsArticleCandidate]:
    candidates: list[MarketNewsArticleCandidate] = []
    for topic_bucket in MarketNewsTopicBucket:
        for adapter in market_news_provider_adapters():
            try:
                result = adapter.collect(
                    fetcher=fetcher,
                    settings=settings,
                    topic_bucket=topic_bucket,
                    as_of=as_of,
                    retrieved_at=retrieved_at,
                )
            except (MarketNewsFetchError, OSError, TimeoutError, ValueError):
                continue
            candidates.extend(result.candidates)
    return candidates


def select_market_news_focus(
    candidates: list[MarketNewsArticleCandidate],
    *,
    as_of: str | date | datetime,
    no_live_external_calls: bool = True,
    configured_max_item_count: int = MAX_MARKET_NEWS_ITEMS,
    minimum_display_score: int = MINIMUM_MARKET_DISPLAY_SCORE,
) -> MarketNewsFocusResponse:
    window = compute_weekly_news_window(as_of)
    eligible: list[MarketNewsArticleCandidate] = []
    suppressed = 0
    for candidate in candidates:
        reasons = _candidate_exclusion_reasons(candidate, window)
        if reasons:
            suppressed += 1
            continue
        eligible.append(candidate)

    clusters = _cluster_market_news_candidates(eligible, minimum_display_score=minimum_display_score)
    selected_clusters = _select_market_news_clusters(clusters, configured_max_item_count)
    selected_ids = {cluster.cluster_id for cluster in selected_clusters}
    suppressed += sum(1 for cluster in clusters if cluster.cluster_id not in selected_ids)
    items = [_item_from_cluster(cluster, index) for index, cluster in enumerate(selected_clusters, start=1)]
    citations = [
        Citation(
            citation_id=citation_id,
            source_document_id=item.source.source_document_id,
            title=item.source.title,
            publisher=item.source.publisher,
            freshness_state=item.freshness_state,
        )
        for item in items
        for citation_id in item.citation_ids
    ]
    source_documents = [_source_document_from_item(item) for item in items]

    if not items:
        state = WeeklyNewsContractState.no_high_signal
        evidence_state = EvidenceState.no_high_signal
        limited_state = WeeklyNewsEvidenceLimitedState.empty
        empty_state = WeeklyNewsEmptyState(
            state=state,
            message="No major Market News Focus items passed the source-use and evidence rules for this window.",
            evidence_state=evidence_state,
            selected_item_count=0,
            suppressed_candidate_count=suppressed,
        )
    elif len(items) < configured_max_item_count:
        state = WeeklyNewsContractState.available
        evidence_state = EvidenceState.partial
        limited_state = WeeklyNewsEvidenceLimitedState.limited_verified_set
        empty_state = None
    else:
        state = WeeklyNewsContractState.available
        evidence_state = EvidenceState.supported
        limited_state = WeeklyNewsEvidenceLimitedState.full
        empty_state = None

    audit = MarketNewsAuditMetadata(
        candidate_count=len(candidates),
        cluster_count=len(clusters),
        selected_cluster_count=len(items),
        suppressed_candidate_count=suppressed,
        topic_bucket_counts=_topic_counts(items),
        provider_counts=_provider_counts(candidates),
    )
    return MarketNewsFocusResponse(
        state=state,
        window=window,
        configured_max_item_count=configured_max_item_count,
        selected_item_count=len(items),
        suppressed_candidate_count=suppressed,
        evidence_state=evidence_state,
        evidence_limited_state=limited_state,
        items=items,
        empty_state=empty_state,
        citations=citations,
        source_documents=source_documents,
        audit=audit,
        no_live_external_calls=no_live_external_calls,
    )


def build_market_ai_comprehensive_analysis(
    focus: MarketNewsFocusResponse,
    *,
    minimum_market_news_item_count: int = MINIMUM_MARKET_AI_ITEMS,
    minimum_topic_bucket_count: int = MINIMUM_MARKET_AI_BUCKETS,
    summary_generation_service: SummaryGenerationService | None = None,
    economic_indicators: EconomicIndicatorsPackResponse | None = None,
) -> MarketAIComprehensiveAnalysisResponse:
    selected_bucket_count = len({item.topic_bucket for item in focus.items})
    if focus.selected_item_count < minimum_market_news_item_count or selected_bucket_count < minimum_topic_bucket_count:
        return MarketAIComprehensiveAnalysisResponse(
            state=WeeklyNewsContractState.suppressed,
            analysis_available=False,
            minimum_market_news_item_count=minimum_market_news_item_count,
            minimum_topic_bucket_count=minimum_topic_bucket_count,
            market_news_selected_item_count=focus.selected_item_count,
            selected_topic_bucket_count=selected_bucket_count,
            suppression_reason=(
                "AI Comprehensive Analysis: Market News Focus is suppressed until enough approved market items "
                "span multiple topic buckets."
            ),
        )

    service = summary_generation_service or build_default_summary_generation_service()
    generation_evidence_pack = evidence_pack_from_market_news(focus, economic_indicators=economic_indicators)
    try:
        response = service.generate_market_ai_comprehensive_analysis(
            focus=focus,
            minimum_market_news_item_count=minimum_market_news_item_count,
            minimum_topic_bucket_count=minimum_topic_bucket_count,
            generation_evidence_pack=generation_evidence_pack,
        )
    except SummaryGenerationContractError:
        try:
            response = HybridSummaryGenerationService().generate_market_ai_comprehensive_analysis(
                focus=focus,
                minimum_market_news_item_count=minimum_market_news_item_count,
                minimum_topic_bucket_count=minimum_topic_bucket_count,
                generation_evidence_pack=generation_evidence_pack,
            )
        except SummaryGenerationContractError:
            return MarketAIComprehensiveAnalysisResponse(
                state=WeeklyNewsContractState.suppressed,
                analysis_available=False,
                minimum_market_news_item_count=minimum_market_news_item_count,
                minimum_topic_bucket_count=minimum_topic_bucket_count,
                market_news_selected_item_count=focus.selected_item_count,
                selected_topic_bucket_count=selected_bucket_count,
                suppression_reason=(
                    "AI Comprehensive Analysis: Market News Focus is suppressed because generated analysis failed "
                    "schema, citation, freshness, headline-repetition, or safety validation."
                ),
            )
    validate_market_ai_comprehensive_analysis(response, focus)
    return response


def validate_market_ai_comprehensive_analysis(
    analysis: MarketAIComprehensiveAnalysisResponse,
    focus: MarketNewsFocusResponse,
) -> MarketAIComprehensiveAnalysisResponse:
    if not analysis.analysis_available:
        if analysis.sections:
            raise MarketNewsContractError("Suppressed Market AI analysis must not include sections.")
        return analysis
    expected_order = [
        "what_changed_this_week",
        "macro_policy",
        "equity_market_drivers",
        "ai_technology_semiconductors",
        "geopolitical_energy_risks",
        "credit_liquidity_sentiment",
        "scenario_lens",
        "practical_watchpoints",
    ]
    if [section.section_id for section in analysis.sections] != expected_order:
        raise MarketNewsContractError("Market AI analysis sections are not in the required order.")
    allowed_citations = {citation_id for item in focus.items for citation_id in item.citation_ids}
    if not allowed_citations:
        raise MarketNewsContractError("Market AI analysis requires Market News Focus citations.")
    for section in analysis.sections:
        if not section.citation_ids:
            raise MarketNewsContractError(f"Market AI section {section.section_id} is missing citations.")
        if not set(section.citation_ids) <= allowed_citations:
            raise MarketNewsContractError(f"Market AI section {section.section_id} cites evidence outside selected market clusters.")
    combined_text = " ".join(
        [section.analysis for section in analysis.sections]
        + [bullet for section in analysis.sections for bullet in section.bullets]
    )
    forbidden = find_forbidden_output_phrases(combined_text)
    if forbidden:
        raise MarketNewsContractError(f"Market AI analysis includes forbidden advice language: {', '.join(forbidden)}")
    return analysis


def fixture_market_news_candidates(
    *,
    as_of: str | date | datetime = DEFAULT_WEEKLY_NEWS_AS_OF,
    retrieved_at: str | None = None,
) -> list[MarketNewsArticleCandidate]:
    retrieved = retrieved_at or _retrieved_at_for_as_of(as_of)
    rows = [
        ("reuters", "Reuters", "reuters.com", "Fed officials describe inflation risks as policy debate continues", "Federal Reserve officials discussed inflation and labor-market data in the current policy window.", MarketNewsTopicBucket.macro_fed, "2026-04-22T13:00:00Z", ("Federal Reserve", "inflation")),
        ("bloomberg", "Bloomberg", "bloomberg.com", "Treasury yields move as investors parse rate outlook", "Treasury-market reporting focused on how rate expectations shaped yields.", MarketNewsTopicBucket.macro_fed, "2026-04-21T16:00:00Z", ("Treasury yields",)),
        ("cnbc", "CNBC", "cnbc.com", "US stocks end mixed as earnings season drives sector moves", "Market reporting connected index moves with earnings and sector leadership.", MarketNewsTopicBucket.markets_earnings, "2026-04-22T20:30:00Z", ("S&P 500", "Nasdaq")),
        ("marketwatch", "MarketWatch", "marketwatch.com", "Earnings reports highlight consumer and margin pressure", "Company earnings coverage described mixed consumer demand and margin commentary.", MarketNewsTopicBucket.markets_earnings, "2026-04-20T18:00:00Z", ("earnings", "consumer")),
        ("financial_times", "Financial Times", "ft.com", "Chip demand remains central to AI infrastructure spending", "Technology reporting focused on chip demand, AI infrastructure, and data-center spending.", MarketNewsTopicBucket.ai_technology_semiconductors, "2026-04-22T10:00:00Z", ("AI", "semiconductors")),
        ("nikkei", "Nikkei Asia", "asia.nikkei.com", "Asian chip suppliers track data-center investment signals", "Regional technology coverage connected supplier activity with AI infrastructure demand.", MarketNewsTopicBucket.ai_technology_semiconductors, "2026-04-19T09:00:00Z", ("data centers",)),
        ("ap", "Associated Press", "apnews.com", "Oil markets watch shipping risk after latest geopolitical flare-up", "Energy reporting connected shipping risk with oil-market uncertainty.", MarketNewsTopicBucket.geopolitics_energy_supply_chain, "2026-04-18T12:00:00Z", ("oil", "shipping")),
        ("guardian", "The Guardian", "theguardian.com", "Supply-chain concerns return as trade tensions stay in focus", "Global reporting described trade and supply-chain risk as a market watchpoint.", MarketNewsTopicBucket.geopolitics_energy_supply_chain, "2026-04-17T12:00:00Z", ("trade", "supply chain")),
        ("wsj", "Wall Street Journal", "wsj.com", "Banks report cautious credit commentary as consumers slow", "Bank coverage highlighted credit quality and consumer stress commentary.", MarketNewsTopicBucket.credit_liquidity_sentiment, "2026-04-22T14:00:00Z", ("banks", "credit")),
        ("bbc", "BBC", "bbc.com", "Dollar and liquidity conditions stay in market focus", "Market coverage connected dollar moves and liquidity conditions with broader sentiment.", MarketNewsTopicBucket.credit_liquidity_sentiment, "2026-04-16T14:00:00Z", ("dollar", "liquidity")),
    ]
    candidates: list[MarketNewsArticleCandidate] = []
    for index, (provider, source, domain, title, description, bucket, published_at, entities) in enumerate(rows, start=1):
        url = f"https://{domain}/markets/{_slug(title)}"
        candidates.append(
            _candidate(
                provider=provider,
                source=source,
                source_domain=domain,
                title=title,
                description=description,
                url=url,
                published_at=published_at,
                retrieved_at=retrieved,
                topic_bucket=bucket,
                entities=entities,
                article_id=f"fixture_market_news_{index}",
            )
        )
    return candidates


def _cluster_market_news_candidates(
    candidates: list[MarketNewsArticleCandidate],
    *,
    minimum_display_score: int,
) -> list[MarketNewsStoryCluster]:
    clusters: list[list[MarketNewsArticleCandidate]] = []
    for candidate in sorted(
        candidates,
        key=lambda row: (row.topic_bucket.value, row.source_priority, _published_desc_sort_key(row), row.article_id),
    ):
        matched = False
        for cluster in clusters:
            if _same_story(candidate, cluster[0]):
                cluster.append(candidate)
                matched = True
                break
        if not matched:
            clusters.append([candidate])

    story_clusters: list[MarketNewsStoryCluster] = []
    for rows in clusters:
        ranked_rows = sorted(rows, key=lambda row: (row.source_priority, _published_desc_sort_key(row), row.article_id))
        representative = ranked_rows[0]
        critical = _is_critical_claim(representative)
        corroborated = _cluster_corrobated(ranked_rows, critical)
        rationale = _selection_rationale(representative, ranked_rows, critical, corroborated, minimum_display_score)
        story_clusters.append(
            MarketNewsStoryCluster(
                cluster_id=f"market_cluster:{_hash_text(representative.canonical_url or representative.title)[:16]}",
                representative=representative,
                articles=tuple(ranked_rows),
                suppressed_duplicate_count=max(0, len(ranked_rows) - 1),
                critical_claim=critical,
                corroborated=corroborated,
                rationale=rationale,
            )
        )
    return [cluster for cluster in story_clusters if cluster.rationale.selected]


def _select_market_news_clusters(
    clusters: list[MarketNewsStoryCluster],
    configured_max_item_count: int,
) -> list[MarketNewsStoryCluster]:
    ranked = sorted(
        clusters,
        key=lambda cluster: (
            -cluster.rationale.total_score,
            cluster.representative.source_priority,
            _published_desc_sort_key(cluster.representative),
            cluster.cluster_id,
        ),
    )
    selected: list[MarketNewsStoryCluster] = []
    selected_ids: set[str] = set()
    for bucket, target in _BUCKET_TARGETS.items():
        bucket_rows = [cluster for cluster in ranked if cluster.representative.topic_bucket is bucket]
        for cluster in bucket_rows[:target]:
            if len(selected) >= configured_max_item_count:
                break
            selected.append(cluster)
            selected_ids.add(cluster.cluster_id)
    for cluster in ranked:
        if len(selected) >= configured_max_item_count:
            break
        if cluster.cluster_id not in selected_ids:
            selected.append(cluster)
            selected_ids.add(cluster.cluster_id)
    return selected


def _item_from_cluster(cluster: MarketNewsStoryCluster, index: int) -> MarketNewsItem:
    candidate = cluster.representative
    citation_id = f"c_market_news_{index}"
    source_document_id = f"src_market_news_{_hash_text(candidate.canonical_url or candidate.title)[:16]}"
    return MarketNewsItem(
        story_id=f"market_story_{index}",
        title=candidate.title,
        summary=_market_summary(candidate),
        published_at=candidate.published_at,
        topic_bucket=candidate.topic_bucket,
        entities=list(candidate.entities),
        citation_ids=[citation_id],
        source=WeeklyNewsSourceMetadata(
            source_document_id=source_document_id,
            source_type="market_news_story_cluster",
            title=candidate.title,
            publisher=candidate.source,
            url=candidate.canonical_url or candidate.url,
            published_at=candidate.published_at,
            as_of_date=candidate.published_at[:10],
            retrieved_at=candidate.retrieved_at,
            freshness_state=FreshnessState.fresh,
            is_official=False,
            source_quality=candidate.source_quality,
            allowlist_status=candidate.allowlist_status,
            source_use_policy=candidate.source_use_policy,
        ),
        freshness_state=FreshnessState.fresh,
        importance_score=cluster.rationale.total_score,
        cluster=MarketNewsClusterMetadata(
            cluster_id=cluster.cluster_id,
            representative_article_id=candidate.article_id,
            supporting_sources=sorted({row.source for row in cluster.articles}),
            article_count=len(cluster.articles),
            suppressed_duplicate_count=cluster.suppressed_duplicate_count,
            topic_bucket=candidate.topic_bucket,
            critical_claim=cluster.critical_claim,
            corroborated=cluster.corroborated,
        ),
        selection_rationale=cluster.rationale,
    )


def _source_document_from_item(item: MarketNewsItem) -> SourceDocument:
    return SourceDocument(
        source_document_id=item.source.source_document_id,
        source_type=item.source.source_type,
        title=item.source.title,
        publisher=item.source.publisher,
        url=item.source.url,
        published_at=item.source.published_at,
        as_of_date=item.source.as_of_date,
        retrieved_at=item.source.retrieved_at,
        freshness_state=item.source.freshness_state,
        is_official=False,
        supporting_passage=_bounded_words(item.summary, 45),
        source_quality=item.source.source_quality,
        allowlist_status=item.source.allowlist_status,
        source_use_policy=item.source.source_use_policy,
        permitted_operations=SourceOperationPermissions(
            can_store_metadata=True,
            can_store_raw_text=False,
            can_display_metadata=True,
            can_display_excerpt=True,
            can_summarize=True,
            can_cache=True,
            can_export_metadata=True,
            can_export_excerpt=False,
            can_export_full_text=False,
            can_support_generated_output=True,
            can_support_citations=True,
            can_support_canonical_facts=False,
            can_support_recent_developments=True,
        ),
        source_identity=item.source.url,
        storage_rights=SourceStorageRights.summary_allowed,
        export_rights=SourceExportRights.metadata_only,
        review_status=SourceReviewStatus.approved,
        approval_rationale="Market News Focus uses source-labeled metadata and bounded summaries only.",
        parser_status=SourceParserStatus.parsed,
    )


def _selection_rationale(
    representative: MarketNewsArticleCandidate,
    rows: list[MarketNewsArticleCandidate],
    critical: bool,
    corroborated: bool,
    minimum_display_score: int,
) -> MarketNewsSelectionRationale:
    source_quality_score = max(0, 25 - min(representative.source_priority, 20))
    freshness_score = _freshness_score(representative)
    topic_relevance_score = 20 if representative.topic_bucket in MarketNewsTopicBucket else 0
    market_impact_score = _market_impact_score(representative)
    corroboration_score = 10 if len({row.source for row in rows}) >= 2 or representative.source_priority <= 5 else 5
    novelty_score = 10
    penalty_score = 0
    reasons: list[str] = []
    if critical and not corroborated:
        penalty_score += 30
        reasons.append("critical_claim_not_corrobated")
    total_score = source_quality_score + freshness_score + topic_relevance_score + market_impact_score + corroboration_score + novelty_score - penalty_score
    selected = total_score >= minimum_display_score and not reasons
    if total_score < minimum_display_score:
        reasons.append("below_minimum_display_score")
    return MarketNewsSelectionRationale(
        source_quality_score=source_quality_score,
        freshness_score=freshness_score,
        topic_relevance_score=topic_relevance_score,
        market_impact_score=market_impact_score,
        corroboration_score=corroboration_score,
        novelty_score=novelty_score,
        penalty_score=penalty_score,
        total_score=total_score,
        selected=selected,
        exclusion_reasons=sorted(set(reasons)),
    )


def _candidate_exclusion_reasons(candidate: MarketNewsArticleCandidate, window: Any) -> list[str]:
    reasons: list[str] = []
    if not candidate.title or not candidate.url:
        reasons.append("missing_title_or_url")
    if candidate.language.lower() != "en":
        reasons.append("non_english")
    if candidate.allowlist_status is not SourceAllowlistStatus.allowed:
        reasons.append("non_allowlisted_source")
    if candidate.source_use_policy not in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed}:
        reasons.append("source_policy_blocked")
    if candidate.source_priority >= 99:
        reasons.append("unrecognized_source")
    if not candidate.license_allowed:
        reasons.append("license_disallowed")
    if _date_part(candidate.published_at) < window.news_window_start or _date_part(candidate.published_at) > window.news_window_end:
        reasons.append("outside_market_week_window")
    lowered = f"{candidate.title} {candidate.description}".lower()
    if any(marker in lowered for marker in _PROMOTIONAL_MARKERS):
        reasons.append("promotional")
    if any(lowered.startswith(marker) for marker in _OPINION_MARKERS):
        reasons.append("opinion")
    if (
        candidate.provider in {adapter.provider for adapter in market_news_provider_adapters()}
        and _topic_keyword_score(candidate.topic_bucket, candidate.title, candidate.description) == 0
    ):
        reasons.append("topic_relevance_low")
    return sorted(set(reasons))


def _candidate(
    *,
    provider: str,
    source: str,
    source_domain: str,
    title: str,
    description: str,
    url: str,
    published_at: str,
    retrieved_at: str,
    topic_bucket: MarketNewsTopicBucket,
    entities: tuple[str, ...] = (),
    symbols: tuple[str, ...] = (),
    article_id: str | None = None,
    language: str = "en",
) -> MarketNewsArticleCandidate:
    clean_source = _clean_source_name(source) or _source_from_domain(source_domain) or provider
    source_priority = _source_priority(clean_source)
    canonical_url = _canonical_url(url)
    clean_title = _clean_text(title) or "Untitled market news item"
    clean_description = _bounded_words(_clean_text(description) or "", 50)
    inferred_topic_bucket = _infer_topic_bucket(clean_title, clean_description, fallback=topic_bucket)
    return MarketNewsArticleCandidate(
        article_id=article_id or f"market_article:{_hash_text(provider + canonical_url + title)[:16]}",
        provider=provider,
        source=clean_source,
        source_domain=(source_domain or _domain(canonical_url)).lower(),
        title=clean_title,
        description=clean_description,
        url=url,
        canonical_url=canonical_url,
        published_at=_normalize_timestamp(published_at),
        retrieved_at=retrieved_at,
        language=_normalize_language(language),
        topic_bucket=inferred_topic_bucket,
        entities=tuple(entities),
        symbols=tuple(symbols),
        source_priority=source_priority,
    )


def _infer_topic_bucket(title: str, description: str, *, fallback: MarketNewsTopicBucket) -> MarketNewsTopicBucket:
    scores = {
        bucket: _topic_keyword_score(bucket, title, description) for bucket in _TOPIC_KEYWORDS
    }
    best_bucket, best_score = max(
        scores.items(),
        key=lambda item: (item[1], _BUCKET_TARGETS.get(item[0], 0)),
    )
    return best_bucket if best_score > 0 else fallback


def _topic_keyword_score(bucket: MarketNewsTopicBucket, title: str, description: str) -> int:
    text = f" {title} {description} ".lower()
    return sum(1 for marker in _TOPIC_KEYWORDS.get(bucket, ()) if marker in text)


def _provider_url(provider: str, topic_bucket: MarketNewsTopicBucket, credential: str | None) -> str:
    query = _TOPIC_QUERIES[topic_bucket]
    if provider == "rss":
        return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY,QQQ&region=US&lang=en-US&l=50"
    if provider == "google_news_rss":
        return f"https://news.google.com/rss/search?{urlencode({'q': query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})}"
    if provider == "gdelt":
        return "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode(
            {"query": query, "mode": "artlist", "format": "json", "maxrecords": "50", "sort": "hybridrel"}
        )
    if provider == "marketaux":
        return "https://api.marketaux.com/v1/news/all?" + urlencode(
            {"api_token": credential or "", "language": "en", "search": query, "filter_entities": "true"}
        )
    if provider == "alpha_vantage":
        return "https://www.alphavantage.co/query?" + urlencode(
            {"function": "NEWS_SENTIMENT", "apikey": credential or "", "topics": "financial_markets,economy_macro"}
        )
    if provider == "finnhub":
        return "https://finnhub.io/api/v1/news?" + urlencode({"category": "general", "token": credential or ""})
    if provider == "guardian":
        return "https://content.guardianapis.com/search?" + urlencode(
            {"q": query, "api-key": credential or "", "show-fields": "trailText", "lang": "en"}
        )
    if provider == "gnews":
        return "https://gnews.io/api/v4/search?" + urlencode({"q": query, "lang": "en", "token": credential or ""})
    if provider == "mediastack":
        return "https://api.mediastack.com/v1/news?" + urlencode(
            {"access_key": credential or "", "languages": "en", "keywords": query}
        )
    if provider == "newsapi":
        return "https://newsapi.org/v2/everything?" + urlencode({"q": query, "language": "en", "apiKey": credential or ""})
    if provider == "yahoo_finance_search":
        return f"https://query1.finance.yahoo.com/v1/finance/search?q={quote(query)}&quotesCount=0&newsCount=20"
    raise MarketNewsFetchError(f"Unknown Market News provider: {provider}")


def _parse_rss_candidates(
    text: str,
    *,
    provider: str,
    topic_bucket: MarketNewsTopicBucket,
    retrieved_at: str,
) -> list[MarketNewsArticleCandidate]:
    if not text.strip():
        return []
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return []
    candidates: list[MarketNewsArticleCandidate] = []
    channel_language = _normalize_language(root.findtext(".//channel/language") or "en")
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        url = item.findtext("link") or ""
        description = item.findtext("description") or ""
        published_at = item.findtext("pubDate") or retrieved_at
        source = item.findtext("source") or _source_from_domain(_domain(url)) or provider
        candidates.append(
            _candidate(
                provider=provider,
                source=source,
                source_domain=_domain(url),
                title=title,
                description=description,
                url=url,
                published_at=published_at,
                retrieved_at=retrieved_at,
                topic_bucket=topic_bucket,
                language=channel_language,
            )
        )
    return candidates


def _parse_json_candidates(
    payload: Any,
    *,
    provider: str,
    topic_bucket: MarketNewsTopicBucket,
    retrieved_at: str,
) -> list[MarketNewsArticleCandidate]:
    rows = _json_rows(payload, provider)
    candidates: list[MarketNewsArticleCandidate] = []
    for row in rows:
        title, description, url, published_at, source, symbols, entities, language = _json_fields(row, provider, retrieved_at)
        if not title or not url:
            continue
        candidates.append(
            _candidate(
                provider=provider,
                source=source or _source_from_domain(_domain(url)) or provider,
                source_domain=_domain(url),
                title=title,
                description=description,
                url=url,
                published_at=published_at,
                retrieved_at=retrieved_at,
                topic_bucket=topic_bucket,
                symbols=tuple(symbols),
                entities=tuple(entities),
                language=language,
            )
        )
    return candidates


def _json_rows(payload: Any, provider: str) -> list[dict[str, Any]]:
    if provider != "finnhub" and not isinstance(payload, dict):
        return []
    if provider == "gdelt":
        rows = payload.get("articles")
    elif provider == "alpha_vantage":
        rows = payload.get("feed")
    elif provider == "guardian":
        rows = (payload.get("response") or {}).get("results")
    elif provider in {"marketaux", "mediastack"}:
        rows = payload.get("data")
    elif provider == "gnews":
        rows = payload.get("articles")
    elif provider == "newsapi":
        rows = payload.get("articles")
    elif provider == "finnhub":
        rows = payload
    elif provider == "yahoo_finance_search":
        rows = payload.get("news")
    else:
        rows = []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _json_fields(
    row: dict[str, Any],
    provider: str,
    retrieved_at: str,
) -> tuple[str, str, str, str, str, list[str], list[str], str]:
    symbols: list[str] = []
    entities: list[str] = []
    if provider == "gdelt":
        return (
            str(row.get("title") or ""),
            str(row.get("seendate") or ""),
            str(row.get("url") or ""),
            str(row.get("seendate") or retrieved_at),
            str(row.get("sourceCommonName") or row.get("domain") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "alpha_vantage":
        symbols = [str(item.get("ticker")) for item in row.get("ticker_sentiment", []) if isinstance(item, dict) and item.get("ticker")]
        return (
            str(row.get("title") or ""),
            str(row.get("summary") or ""),
            str(row.get("url") or ""),
            str(row.get("time_published") or retrieved_at),
            str(row.get("source") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "guardian":
        fields = row.get("fields") if isinstance(row.get("fields"), dict) else {}
        return (
            str(row.get("webTitle") or ""),
            str(fields.get("trailText") or ""),
            str(row.get("webUrl") or ""),
            str(row.get("webPublicationDate") or retrieved_at),
            "The Guardian",
            symbols,
            entities,
            str(row.get("lang") or "en"),
        )
    if provider == "marketaux":
        entities = [str(item.get("name") or item.get("symbol")) for item in row.get("entities", []) if isinstance(item, dict)]
        return (
            str(row.get("title") or ""),
            str(row.get("description") or row.get("snippet") or ""),
            str(row.get("url") or ""),
            str(row.get("published_at") or retrieved_at),
            str((row.get("source") or "") if isinstance(row.get("source"), str) else (row.get("source") or {}).get("name") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "finnhub":
        timestamp = row.get("datetime")
        published = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat().replace("+00:00", "Z") if timestamp else retrieved_at
        return (
            str(row.get("headline") or ""),
            str(row.get("summary") or ""),
            str(row.get("url") or ""),
            published,
            str(row.get("source") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "gnews":
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        return (
            str(row.get("title") or ""),
            str(row.get("description") or ""),
            str(row.get("url") or ""),
            str(row.get("publishedAt") or retrieved_at),
            str(source.get("name") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "mediastack":
        return (
            str(row.get("title") or ""),
            str(row.get("description") or ""),
            str(row.get("url") or ""),
            str(row.get("published_at") or retrieved_at),
            str(row.get("source") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "newsapi":
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        return (
            str(row.get("title") or ""),
            str(row.get("description") or ""),
            str(row.get("url") or ""),
            str(row.get("publishedAt") or retrieved_at),
            str(source.get("name") or ""),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    if provider == "yahoo_finance_search":
        published = row.get("providerPublishTime")
        published_at = datetime.fromtimestamp(float(published), tz=timezone.utc).isoformat().replace("+00:00", "Z") if published else retrieved_at
        symbols = [str(value) for value in row.get("relatedTickers", []) if value]
        return (
            str(row.get("title") or ""),
            str(row.get("summary") or ""),
            str(row.get("link") or ""),
            published_at,
            str(row.get("publisher") or "Yahoo Finance/yfinance-derived news"),
            symbols,
            entities,
            str(row.get("language") or "en"),
        )
    return "", "", "", retrieved_at, "", symbols, entities, "en"


def _analysis_section(
    section_id: Any,
    label: Any,
    analysis: str,
    bullets: list[str],
    citation_ids: list[str],
) -> MarketAIAnalysisSection:
    return MarketAIAnalysisSection(
        section_id=section_id,
        label=label,
        analysis=analysis,
        bullets=bullets,
        citation_ids=sorted(set(citation_ids)),
        uncertainty=[],
    )


def _bucket_sentence(
    titles_by_bucket: dict[MarketNewsTopicBucket, list[str]],
    bucket: MarketNewsTopicBucket,
    label: str,
) -> str:
    titles = titles_by_bucket.get(bucket) or []
    if not titles:
        return f"The selected Market News Focus pack has limited {label} evidence in this window."
    return f"The selected {label} items include: {'; '.join(titles[:2])}."


def _citations_for_bucket(focus: MarketNewsFocusResponse, bucket: MarketNewsTopicBucket) -> list[str]:
    return sorted({citation_id for item in focus.items if item.topic_bucket is bucket for citation_id in item.citation_ids})


def _market_summary(candidate: MarketNewsArticleCandidate) -> str:
    text = candidate.description or candidate.title
    if text:
        return _bounded_words(text, 32)
    return f"{candidate.source} reported this market-wide item for the {candidate.topic_bucket.value.replace('_', ' ')} bucket."


def _same_story(left: MarketNewsArticleCandidate, right: MarketNewsArticleCandidate) -> bool:
    if left.canonical_url and left.canonical_url == right.canonical_url:
        return True
    left_tokens = set(_normalized_title(left.title).split())
    right_tokens = set(_normalized_title(right.title).split())
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    return overlap >= 0.72


def _cluster_corrobated(rows: list[MarketNewsArticleCandidate], critical: bool) -> bool:
    if not critical:
        return True
    if rows[0].source_priority <= _CRITICAL_SOURCE_PRIORITY_CUTOFF:
        return True
    return len({row.source for row in rows if row.source_priority < 99}) >= 2


def _is_critical_claim(candidate: MarketNewsArticleCandidate) -> bool:
    text = f" {candidate.title} {candidate.description} ".lower()
    return any(marker in text for marker in _CRITICAL_MARKERS)


def _market_impact_score(candidate: MarketNewsArticleCandidate) -> int:
    text = f" {candidate.title} {candidate.description} ".lower()
    impact_markers = ("market", "fed", "inflation", "rate", "yield", "oil", "earnings", "credit", "liquidity", "ai", "chip")
    return 15 if any(marker in text for marker in impact_markers) else 5


def _freshness_score(candidate: MarketNewsArticleCandidate) -> int:
    published = _parse_datetime(candidate.published_at)
    retrieved = _parse_datetime(candidate.retrieved_at)
    if published is None or retrieved is None:
        return 8
    age_days = max(0, (retrieved.date() - published.date()).days)
    if age_days <= 1:
        return 20
    if age_days <= 3:
        return 16
    if age_days <= 5:
        return 12
    if age_days <= 7:
        return 8
    return 4


def _topic_counts(items: list[MarketNewsItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.topic_bucket.value] = counts.get(item.topic_bucket.value, 0) + 1
    return counts


def _provider_counts(candidates: list[MarketNewsArticleCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.provider] = counts.get(candidate.provider, 0) + 1
    return counts


def _provider_from_url(url: str) -> str:
    host = urlsplit(url).hostname or ""
    if "news.google.com" in host:
        return "google_news_rss"
    if "gdeltproject.org" in host:
        return "gdelt"
    if "marketaux.com" in host:
        return "marketaux"
    if "alphavantage.co" in host:
        return "alpha_vantage"
    if "finnhub.io" in host:
        return "finnhub"
    if "guardianapis.com" in host:
        return "guardian"
    if "gnews.io" in host:
        return "gnews"
    if "mediastack.com" in host:
        return "mediastack"
    if "newsapi.org" in host:
        return "newsapi"
    if "query1.finance.yahoo.com" in host:
        return "yahoo_finance_search"
    return "rss"


def _clean_source_name(value: str | None) -> str | None:
    return clean_news_publisher(value)


def _source_from_domain(domain: str) -> str | None:
    return news_source_from_domain(domain)


def _source_priority(source: str) -> int:
    return publisher_priority(source)


def _canonical_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return url
    filtered = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"ref", "ref_src", "cmpid", "ocid"}
    ]
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            urlencode(filtered),
            "",
        )
    )


def _domain(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _normalize_timestamp(value: str) -> str:
    text = _clean_text(value) or DEFAULT_WEEKLY_NEWS_AS_OF
    if re.fullmatch(r"\d{8}T\d{6}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}T{text[9:11]}:{text[11:13]}:{text[13:15]}Z"
    parsed = _parse_datetime(text)
    if parsed:
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{text}T00:00:00Z"
    return text


def _parse_datetime(value: str) -> datetime | None:
    text = value.strip()
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def _date_part(value: str) -> str:
    normalized = _normalize_timestamp(value)
    return normalized[:10]


def _published_desc_sort_key(candidate: MarketNewsArticleCandidate) -> float:
    parsed = _parse_datetime(candidate.published_at)
    if parsed is None:
        return 0
    return -parsed.timestamp()


def _retrieved_at_for_as_of(as_of: str | date | datetime) -> str:
    as_of_date = compute_weekly_news_window(as_of).as_of_date
    return f"{as_of_date}T12:00:00Z"


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80]


def _normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _normalize_language(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return "unknown"
    normalized = text.lower().replace("_", "-")
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("zh"):
        return "zh"
    return normalized.split("-", 1)[0]


def _bounded_words(text: str, max_words: int) -> str:
    words = text.split()
    return " ".join(words[:max_words])


def serialize_market_news_candidates(candidates: list[MarketNewsArticleCandidate]) -> str:
    safe_rows = [
        {
            "article_id": candidate.article_id,
            "provider": candidate.provider,
            "source": candidate.source,
            "source_domain": candidate.source_domain,
            "title": candidate.title,
            "canonical_url": candidate.canonical_url,
            "published_at": candidate.published_at,
            "topic_bucket": candidate.topic_bucket.value,
            "source_use_policy": candidate.source_use_policy.value,
        }
        for candidate in candidates
    ]
    return json.dumps(safe_rows, sort_keys=True)
