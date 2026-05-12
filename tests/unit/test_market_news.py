from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from backend.market_news import (
    MAX_MARKET_NEWS_ITEMS,
    MARKET_NEWS_RESPONSE_BOUNDARY,
    MARKET_NEWS_SELECTION_BOUNDARY,
    MARKET_NEWS_SOURCE_ADAPTER_BOUNDARY,
    FixtureMarketNewsFetcher,
    MarketNewsArticleCandidate,
    build_market_ai_comprehensive_analysis,
    build_market_news_response,
    collect_market_news_candidates,
    fixture_market_news_candidates,
    market_news_provider_adapters,
    select_market_news_focus,
    serialize_market_news_candidates,
)
from backend.market_news_runtime import MarketNewsResponseMemoryCache, build_runtime_market_news_response
from backend.models import (
    MarketNewsTopicBucket,
    SourceAllowlistStatus,
    SourceUsePolicy,
    WeeklyNewsContractState,
)
from backend.settings import build_market_news_settings
from backend.summary_generation import SummaryGenerationContractError
from scripts.run_market_news_live_source_smoke import (
    SMOKE_OPT_IN_ENV,
    SMOKE_SCHEMA_VERSION,
    run_market_news_live_source_smoke,
)


AS_OF = "2026-04-23"
RETRIEVED_AT = "2026-04-23T12:00:00Z"


def test_market_news_fixture_builds_reusable_no_raw_market_pack():
    response = build_market_news_response(as_of=AS_OF)
    focus = response.market_news_focus
    analysis = response.market_ai_comprehensive_analysis

    assert MARKET_NEWS_SOURCE_ADAPTER_BOUNDARY == "market-news-source-adapter-v1"
    assert MARKET_NEWS_SELECTION_BOUNDARY == "market-news-selection-v1"
    assert MARKET_NEWS_RESPONSE_BOUNDARY == "market-news-response-v1"
    assert focus.schema_version == "market-news-focus-v1"
    assert focus.reusable_across_tickers is True
    assert focus.selected_item_count == len(focus.items)
    assert 0 < focus.selected_item_count <= MAX_MARKET_NEWS_ITEMS
    assert focus.audit.no_raw_article_text is True
    assert focus.audit.no_raw_provider_payload is True
    assert focus.audit.no_unrestricted_media is True
    assert focus.audit.no_generated_output_cache_write is True
    assert focus.no_live_external_calls is True
    assert len({item.topic_bucket for item in focus.items}) >= 3
    assert all(item.source.source_use_policy is SourceUsePolicy.summary_allowed for item in focus.items)
    assert all(source.permitted_operations.can_store_raw_text is False for source in focus.source_documents)
    assert all(source.permitted_operations.can_support_canonical_facts is False for source in focus.source_documents)
    assert all(source.export_rights.value == "metadata_only" for source in focus.source_documents)

    assert analysis.analysis_available is True
    assert analysis.state is WeeklyNewsContractState.available
    assert analysis.no_live_external_calls is True
    assert [section.label for section in analysis.sections] == [
        "What Changed This Week",
        "Macro & Policy",
        "Equity Market Drivers",
        "AI / Technology / Semiconductors",
        "Geopolitical & Energy Risks",
        "Credit / Liquidity / Sentiment",
        "Scenario Lens",
        "Practical Watchpoints",
    ]
    rendered = " ".join(
        [section.analysis for section in analysis.sections]
        + [bullet for section in analysis.sections for bullet in section.bullets]
    ).lower()
    for persona in ["atlas", "sophia", "kenji", "crow", "rain"]:
        assert persona not in rendered
    for advice_phrase in ["you should buy", "you should sell", "price target is"]:
        assert advice_phrase not in rendered


def test_market_news_selection_rejects_weak_duplicate_or_policy_blocked_items():
    allowed = fixture_market_news_candidates(as_of=AS_OF, retrieved_at=RETRIEVED_AT)[:2]
    weak_source = _candidate(
        "weak_blog",
        source="Unreviewed Blog",
        domain="example.com",
        title="Fed rate rumor moves market chatter",
        description="A thin market rumor with no allowlisted source support.",
    )
    non_english = replace(
        _candidate(
            "non_english",
            title="Fed market update",
            description="English title but candidate language is blocked.",
        ),
        language="zh",
    )
    metadata_only = replace(
        _candidate(
            "metadata_only",
            title="Fed rate update with metadata-only source",
            description="This source is not allowed to support generated summaries.",
        ),
        source_use_policy=SourceUsePolicy.metadata_only,
    )

    focus = select_market_news_focus(
        [*allowed, weak_source, non_english, metadata_only],
        as_of=AS_OF,
    )

    assert focus.selected_item_count == len(allowed)
    assert focus.suppressed_candidate_count >= 3
    assert {item.title for item in focus.items} == {item.title for item in allowed}


def test_critical_claims_need_priority_source_or_two_tier_one_sources():
    unsupported_single = _candidate(
        "single",
        source="CNBC",
        domain="cnbc.com",
        title="Fed rate stress hits markets",
        description="CNBC reported rate stress as a broad market issue.",
    )
    corroborating_left = _candidate(
        "left",
        source="CNBC",
        domain="cnbc.com",
        title="Oil shipping risk returns to market focus",
        description="CNBC reported oil and shipping risk as a market issue.",
    )
    corroborating_right = _candidate(
        "right",
        source="MarketWatch",
        domain="marketwatch.com",
        title="Oil shipping risk returns to market focus",
        description="MarketWatch reported oil and shipping risk as a market issue.",
    )
    priority_single = _candidate(
        "priority",
        source="Reuters",
        domain="reuters.com",
        title="Fed rate stress remains a market focus",
        description="Reuters reported policy stress as a broad market issue.",
    )

    uncorroborated_focus = select_market_news_focus([unsupported_single], as_of=AS_OF)
    corroborated_focus = select_market_news_focus([corroborating_left, corroborating_right], as_of=AS_OF)
    priority_focus = select_market_news_focus([priority_single], as_of=AS_OF)

    assert uncorroborated_focus.selected_item_count == 0
    assert corroborated_focus.selected_item_count == 1
    assert corroborated_focus.items[0].cluster.corroborated is True
    assert sorted(corroborated_focus.items[0].cluster.supporting_sources) == ["CNBC", "MarketWatch"]
    assert priority_focus.selected_item_count == 1
    assert priority_focus.items[0].cluster.critical_claim is True


def test_market_news_selection_suppresses_pundit_and_low_us_relevance_items():
    strong = _candidate(
        "strong",
        source="Reuters",
        domain="reuters.com",
        title="Federal Reserve inflation update shapes S&P 500 market focus",
        description="Reuters reported U.S. inflation and Treasury yield context for Wall Street.",
    )
    pundit = _candidate(
        "pundit",
        source="CNBC",
        domain="cnbc.com",
        title="Jim Cramer's approach to the latest market rally",
        description="A TV segment discussed stocks to watch.",
    )
    foreign_local = _candidate(
        "foreign_local",
        source="Reuters",
        domain="reuters.com",
        title="Indian rupee and bonds look to inflation prints",
        description="Local currency traders watched domestic data without a U.S. market hook.",
    )

    focus = select_market_news_focus([strong, pundit, foreign_local], as_of=AS_OF)

    assert focus.selected_item_count == 1
    assert focus.items[0].title == strong.title
    assert focus.suppressed_candidate_count >= 2


def test_market_ai_analysis_suppresses_until_enough_approved_market_breadth():
    focus = select_market_news_focus(
        fixture_market_news_candidates(as_of=AS_OF, retrieved_at=RETRIEVED_AT)[:2],
        as_of=AS_OF,
    )
    analysis = build_market_ai_comprehensive_analysis(focus)

    assert analysis.state is WeeklyNewsContractState.suppressed
    assert analysis.analysis_available is False
    assert analysis.sections == []
    assert analysis.suppression_reason


def test_market_ai_analysis_falls_back_when_live_generation_repeats_headlines():
    class RepeatingHeadlineService:
        def generate_market_ai_comprehensive_analysis(self, **kwargs):
            raise SummaryGenerationContractError("Generated analysis only repeats selected headlines.")

    focus = select_market_news_focus(fixture_market_news_candidates(as_of=AS_OF), as_of=AS_OF)

    analysis = build_market_ai_comprehensive_analysis(
        focus,
        summary_generation_service=RepeatingHeadlineService(),
    )

    assert analysis.state is WeeklyNewsContractState.available
    assert analysis.analysis_available is True
    assert analysis.sections
    rendered = " ".join(section.analysis for section in analysis.sections).lower()
    assert "selected market news focus items are" not in rendered
    assert "bucket has" not in rendered
    assert "set spans" not in rendered


def test_market_news_adapters_normalize_all_provider_payload_shapes_without_live_calls():
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKETAUX_API_KEY": "marketaux-secret-value",
            "ALPHA_VANTAGE_API_KEY": "alpha-secret-value",
            "FINNHUB_API_KEY": "finnhub-secret-value",
            "GUARDIAN_API_KEY": "guardian-secret-value",
            "GNEWS_API_KEY": "gnews-secret-value",
            "MEDIASTACK_API_KEY": "mediastack-secret-value",
            "NEWSAPI_API_KEY": "newsapi-secret-value",
        }
    )
    fetcher = FixtureMarketNewsFetcher(payloads_by_provider=_provider_payloads())

    candidates = collect_market_news_candidates(
        fetcher=fetcher,
        settings=settings,
        as_of=AS_OF,
        retrieved_at=RETRIEVED_AT,
    )
    providers = {candidate.provider for candidate in candidates}

    assert {adapter.provider for adapter in market_news_provider_adapters()} <= providers
    assert all(candidate.language == "en" for candidate in candidates)
    assert all(not hasattr(candidate, "raw") for candidate in candidates)
    focus = select_market_news_focus(candidates, as_of=AS_OF)
    assert focus.selected_item_count <= MAX_MARKET_NEWS_ITEMS
    assert focus.audit.provider_counts["gdelt"] >= 1
    serialized = serialize_market_news_candidates(candidates)
    for forbidden in ["configured", "Authorization", "Bearer ", "raw article body", "provider payload value"]:
        assert forbidden not in serialized


def test_market_news_live_metadata_rebuckets_query_results_by_article_content():
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
        }
    )
    rss_text = """
    <rss><channel>
      <item>
        <title>Oil prices rise as Strait of Hormuz shipping risk returns</title>
        <link>https://www.reuters.com/markets/oil-hormuz-risk</link>
        <description>Reuters reported oil and shipping risk as an energy-market issue.</description>
        <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
        <source>Reuters</source>
      </item>
      <item>
        <title>Federal Reserve officials discuss inflation and Treasury yields</title>
        <link>https://www.reuters.com/markets/fed-inflation-yields</link>
        <description>Reuters reported macro policy context.</description>
        <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
        <source>Reuters</source>
      </item>
      <item>
        <title>Nvidia and AMD shares rise as AI chip demand improves</title>
        <link>https://www.reuters.com/markets/ai-chip-demand</link>
        <description>Reuters reported semiconductor demand for AI data centers.</description>
        <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
        <source>Reuters</source>
      </item>
      <item>
        <title>Bank credit spreads widen as liquidity worries return</title>
        <link>https://www.reuters.com/markets/bank-credit-liquidity</link>
        <description>Reuters reported credit and liquidity sentiment.</description>
        <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
        <source>Reuters</source>
      </item>
      <item>
        <title>S&amp;P 500 earnings results lift Wall Street stocks</title>
        <link>https://www.reuters.com/markets/sp500-earnings-results</link>
        <description>Reuters reported equity-market earnings context.</description>
        <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
        <source>Reuters</source>
      </item>
    </channel></rss>
    """
    fetcher = FixtureMarketNewsFetcher(payloads_by_provider={"rss": rss_text, "google_news_rss": rss_text})

    candidates = collect_market_news_candidates(
        fetcher=fetcher,
        settings=settings,
        as_of=AS_OF,
        retrieved_at=RETRIEVED_AT,
    )
    topics_by_title = {candidate.title: candidate.topic_bucket for candidate in candidates}

    assert topics_by_title["Oil prices rise as Strait of Hormuz shipping risk returns"] is MarketNewsTopicBucket.geopolitics_energy_supply_chain
    assert topics_by_title["Federal Reserve officials discuss inflation and Treasury yields"] is MarketNewsTopicBucket.macro_fed
    assert topics_by_title["Nvidia and AMD shares rise as AI chip demand improves"] is MarketNewsTopicBucket.ai_technology_semiconductors
    assert topics_by_title["Bank credit spreads widen as liquidity worries return"] is MarketNewsTopicBucket.credit_liquidity_sentiment
    assert topics_by_title["S&P 500 earnings results lift Wall Street stocks"] is MarketNewsTopicBucket.markets_earnings


def test_runtime_market_news_fetch_uses_ttl_cache_for_opt_in_live_path():
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKET_NEWS_CACHE_TTL_HOURS": "1",
            "MARKETAUX_API_KEY": "configured",
            "ALPHA_VANTAGE_API_KEY": "configured",
            "FINNHUB_API_KEY": "configured",
            "GUARDIAN_API_KEY": "configured",
            "GNEWS_API_KEY": "configured",
            "MEDIASTACK_API_KEY": "configured",
            "NEWSAPI_API_KEY": "configured",
        }
    )
    fetcher = CountingMarketNewsFetcher(_provider_payloads())
    cache = MarketNewsResponseMemoryCache()

    first = build_runtime_market_news_response(as_of=AS_OF, settings=settings, fetcher=fetcher, cache=cache)
    first_call_count = len(fetcher.urls)
    second = build_runtime_market_news_response(as_of=AS_OF, settings=settings, fetcher=fetcher, cache=cache)

    assert first.market_news_focus.selected_item_count > 0
    assert first.market_news_focus.no_live_external_calls is False
    assert second.market_news_focus.no_live_external_calls is False
    assert len(fetcher.urls) == first_call_count
    assert second.model_dump(mode="json") == first.model_dump(mode="json")


def test_runtime_market_news_cache_only_returns_fixture_without_cold_live_fetch():
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKET_NEWS_CACHE_TTL_HOURS": "1",
            "MARKETAUX_API_KEY": "configured",
        }
    )
    fetcher = CountingMarketNewsFetcher(_provider_payloads())

    response = build_runtime_market_news_response(
        as_of=AS_OF,
        settings=settings,
        fetcher=fetcher,
        cache=MarketNewsResponseMemoryCache(),
        cache_only=True,
    )

    assert fetcher.urls == []
    assert response.market_news_focus.selected_item_count > 0
    assert response.market_news_focus.no_live_external_calls is True


def test_runtime_market_news_persistent_cache_reuses_pack_across_memory_caches(tmp_path):
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKET_NEWS_CACHE_TTL_HOURS": "1",
            "MARKET_NEWS_CACHE_DIR": str(tmp_path),
            "MARKETAUX_API_KEY": "configured",
            "ALPHA_VANTAGE_API_KEY": "configured",
            "FINNHUB_API_KEY": "configured",
            "GUARDIAN_API_KEY": "configured",
            "GNEWS_API_KEY": "configured",
            "MEDIASTACK_API_KEY": "configured",
            "NEWSAPI_API_KEY": "configured",
        }
    )
    first_fetcher = CountingMarketNewsFetcher(_provider_payloads())

    first = build_runtime_market_news_response(
        as_of=AS_OF,
        settings=settings,
        fetcher=first_fetcher,
        cache=MarketNewsResponseMemoryCache(),
    )
    second_fetcher = CountingMarketNewsFetcher(_provider_payloads())
    second = build_runtime_market_news_response(
        as_of=AS_OF,
        settings=settings,
        fetcher=second_fetcher,
        cache=MarketNewsResponseMemoryCache(),
    )

    assert first.market_news_focus.selected_item_count > 0
    assert second.model_dump(mode="json") == first.model_dump(mode="json")
    assert second_fetcher.urls == []
    cache_files = list((tmp_path / "market_news").glob("*.json"))
    assert cache_files
    serialized = cache_files[0].read_text(encoding="utf-8")
    for secret in [
        "marketaux-secret-value",
        "alpha-secret-value",
        "finnhub-secret-value",
        "guardian-secret-value",
        "gnews-secret-value",
        "mediastack-secret-value",
        "newsapi-secret-value",
    ]:
        assert secret not in serialized
    assert "raw article body" not in serialized
    assert "provider payload value" not in serialized


def test_market_news_selection_prefers_fresher_representative_and_score_on_ties():
    old = replace(
        _candidate(
            "old",
            source="Reuters",
            domain="reuters.com",
            title="Fed policy update shapes market focus",
            description="Reuters reported policy and market context for the current evidence window.",
        ),
        published_at="2026-04-20T12:00:00Z",
        canonical_url="https://reuters.com/markets/fed-policy-old",
        url="https://reuters.com/markets/fed-policy-old",
    )
    new = replace(
        old,
        article_id="test_new",
        published_at="2026-04-22T12:00:00Z",
        canonical_url="https://reuters.com/markets/fed-policy-new",
        url="https://reuters.com/markets/fed-policy-new",
    )

    focus = select_market_news_focus([old, new], as_of=AS_OF)

    assert focus.selected_item_count == 1
    assert focus.items[0].published_at == "2026-04-22T12:00:00Z"
    assert focus.items[0].selection_rationale.freshness_score > 16
    assert focus.items[0].cluster.representative_article_id == "test_new"


def test_market_news_live_provider_language_metadata_is_enforced():
    settings = build_market_news_settings(
        env={
            "MARKET_NEWS_FETCH_ENABLED": "true",
            "MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED": "true",
            "MARKETAUX_API_KEY": "configured",
        }
    )
    fetcher = FixtureMarketNewsFetcher(
        payloads_by_provider={
            "marketaux": {
                "data": [
                    {
                        "title": "Reuters German-language market update",
                        "description": "Reuters reported market context through Marketaux metadata.",
                        "url": "https://www.reuters.com/markets/non-english-market-update",
                        "published_at": "2026-04-22T12:00:00Z",
                        "source": "Reuters",
                        "language": "de",
                    }
                ]
            }
        }
    )

    candidates = collect_market_news_candidates(
        fetcher=fetcher,
        settings=settings,
        as_of=AS_OF,
        retrieved_at=RETRIEVED_AT,
    )
    focus = select_market_news_focus(candidates, as_of=AS_OF)

    assert {candidate.language for candidate in candidates} == {"de"}
    assert focus.selected_item_count == 0
    assert focus.suppressed_candidate_count >= 1


def test_market_news_settings_keep_credentials_private_and_keyed_adapters_skip_when_missing():
    settings = build_market_news_settings(env={})
    assert settings.fetch_enabled is False
    assert settings.can_attempt_live_fetch is False
    assert settings.safe_diagnostics["provider_credentials_configured"]["marketaux"] is False
    keyed_settings = build_market_news_settings(env={"MARKETAUX_API_KEY": "super-secret-value"})
    assert keyed_settings.safe_diagnostics["provider_credentials_configured"]["marketaux"] is True
    assert "super-secret-value" not in repr(keyed_settings)
    assert "super-secret-value" not in str(keyed_settings.safe_diagnostics)

    fetcher = FixtureMarketNewsFetcher(payloads_by_provider=_provider_payloads())
    marketaux = next(adapter for adapter in market_news_provider_adapters() if adapter.provider == "marketaux")
    result = marketaux.collect(
        fetcher=fetcher,
        settings=settings,
        topic_bucket=MarketNewsTopicBucket.macro_fed,
        as_of=AS_OF,
        retrieved_at=RETRIEVED_AT,
    )
    assert result.candidates == ()
    assert result.skipped_reason == "provider_credential_not_configured"
    assert result.no_live_external_calls is True


def test_market_news_module_avoids_direct_live_network_clients_and_secret_names():
    source = Path("backend/market_news.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in source


def test_market_news_live_source_smoke_is_optional_and_sanitized():
    skipped = run_market_news_live_source_smoke(env={})
    assert skipped["schema_version"] == SMOKE_SCHEMA_VERSION
    assert skipped["status"] == "skipped"
    assert skipped["normal_ci_requires_live_calls"] is False
    assert skipped["live_sources_fetched"] is False

    result = run_market_news_live_source_smoke(env={SMOKE_OPT_IN_ENV: "true"})
    assert result["status"] == "pass"
    assert result["normal_ci_requires_live_calls"] is False
    assert result["live_sources_fetched"] is False
    cases = {case["case_id"]: case for case in result["cases"]}
    assert {"provider_adapter_matrix", "selection_safety_gates", "critical_claim_gate", "ai_threshold"} <= set(cases)
    assert cases["provider_adapter_matrix"]["raw_article_text_reported"] is False
    assert cases["provider_adapter_matrix"]["raw_provider_payload_logged"] is False
    serialized = repr(result)
    for forbidden in ["Bearer ", "Authorization", "BEGIN PRIVATE KEY", "raw article body", "provider payload value", "sk-"]:
        assert forbidden not in serialized


def _candidate(
    article_id: str,
    *,
    source: str = "Reuters",
    domain: str = "reuters.com",
    title: str = "Fed policy update shapes market focus",
    description: str = "Reuters reported policy and market context for the current evidence window.",
    bucket: MarketNewsTopicBucket = MarketNewsTopicBucket.macro_fed,
) -> MarketNewsArticleCandidate:
    return MarketNewsArticleCandidate(
        article_id=f"test_{article_id}",
        provider="test",
        source=source,
        source_domain=domain,
        title=title,
        description=description,
        url=f"https://{domain}/markets/{article_id}",
        canonical_url=f"https://{domain}/markets/{article_id}",
        published_at="2026-04-22T12:00:00Z",
        retrieved_at=RETRIEVED_AT,
        language="en",
        topic_bucket=bucket,
        entities=("Federal Reserve",),
        source_priority=_priority_for_source(source),
        allowlist_status=(
            SourceAllowlistStatus.allowed
            if source in {"Reuters", "CNBC", "MarketWatch"}
            else SourceAllowlistStatus.not_allowlisted
        ),
    )


def _priority_for_source(source: str) -> int:
    return {"Reuters": 1, "CNBC": 8, "MarketWatch": 10}.get(source, 99)


class CountingMarketNewsFetcher:
    no_live_external_calls = False

    def __init__(self, payloads: dict[str, object]) -> None:
        self.fixture = FixtureMarketNewsFetcher(payloads_by_provider=payloads)
        self.urls: list[str] = []

    def fetch_json(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15):
        self.urls.append(url)
        return self.fixture.fetch_json(url, headers=headers, timeout_seconds=timeout_seconds)

    def fetch_text(self, url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 15) -> str:
        self.urls.append(url)
        return self.fixture.fetch_text(url, headers=headers, timeout_seconds=timeout_seconds)


def _provider_payloads():
    finnhub_time = int(datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc).timestamp())
    rss_text = """
    <rss><channel>
      <item>
        <title>Reuters Federal Reserve inflation market update from RSS</title>
        <link>https://www.reuters.com/markets/rss-market-update</link>
        <description>Reuters reported Federal Reserve inflation and Treasury yield context from RSS metadata.</description>
        <pubDate>Wed, 22 Apr 2026 12:00:00 GMT</pubDate>
        <source>Reuters</source>
      </item>
    </channel></rss>
    """
    return {
        "rss": rss_text,
        "google_news_rss": rss_text,
        "gdelt": {
            "articles": [
                {
                    "title": "Reuters GDELT Federal Reserve inflation market update",
                    "url": "https://www.reuters.com/markets/gdelt-market-update",
                    "seendate": "20260422T120000Z",
                    "sourceCommonName": "Reuters",
                }
            ]
        },
        "marketaux": {
            "data": [
                {
                    "title": "Reuters Marketaux Federal Reserve inflation market update",
                    "description": "Reuters reported Federal Reserve inflation and Treasury yield context through Marketaux metadata.",
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
                    "title": "Reuters Alpha Vantage Federal Reserve inflation market update",
                    "summary": "Reuters reported Federal Reserve inflation and Treasury yield context through Alpha Vantage metadata.",
                    "url": "https://www.reuters.com/markets/alpha-market-update",
                    "time_published": "20260422T120000",
                    "source": "Reuters",
                    "ticker_sentiment": [{"ticker": "SPY"}],
                }
            ]
        },
        "finnhub": [
            {
                "headline": "Reuters Finnhub Federal Reserve inflation market update",
                "summary": "Reuters reported Federal Reserve inflation and Treasury yield context through Finnhub metadata.",
                "url": "https://www.reuters.com/markets/finnhub-market-update",
                "datetime": finnhub_time,
                "source": "Reuters",
            }
        ],
        "guardian": {
            "response": {
                "results": [
                    {
                        "webTitle": "Guardian Federal Reserve inflation market update",
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
                    "title": "Reuters GNews Federal Reserve inflation market update",
                    "description": "Reuters reported Federal Reserve inflation and Treasury yield context through GNews metadata.",
                    "url": "https://www.reuters.com/markets/gnews-market-update",
                    "publishedAt": "2026-04-22T12:00:00Z",
                    "source": {"name": "Reuters"},
                }
            ]
        },
        "mediastack": {
            "data": [
                {
                    "title": "Reuters Mediastack Federal Reserve inflation market update",
                    "description": "Reuters reported Federal Reserve inflation and Treasury yield context through Mediastack metadata.",
                    "url": "https://www.reuters.com/markets/mediastack-market-update",
                    "published_at": "2026-04-22T12:00:00Z",
                    "source": "Reuters",
                }
            ]
        },
        "newsapi": {
            "articles": [
                {
                    "title": "Reuters NewsAPI Federal Reserve inflation market update",
                    "description": "Reuters reported Federal Reserve inflation and Treasury yield context through NewsAPI metadata.",
                    "url": "https://www.reuters.com/markets/newsapi-market-update",
                    "publishedAt": "2026-04-22T12:00:00Z",
                    "source": {"name": "Reuters"},
                }
            ]
        },
        "yahoo_finance_search": {
            "news": [
                {
                    "title": "Reuters Yahoo Finance Federal Reserve inflation market update",
                    "summary": "Reuters reported Federal Reserve inflation and Treasury yield context through Yahoo metadata.",
                    "link": "https://www.reuters.com/markets/yahoo-market-update",
                    "providerPublishTime": finnhub_time,
                    "publisher": "Reuters",
                    "relatedTickers": ["SPY"],
                }
            ]
        },
    }
