from __future__ import annotations

from dataclasses import dataclass
from typing import Any


NEWS_PUBLISHER_PRIORITY = {
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
    "etf.com": 19,
    "nasdaq": 20,
    "s&p global": 21,
    "sp global": 21,
    "investing.com": 22,
    "investing": 22,
    "business insider": 23,
    "fortune": 24,
    "axios": 25,
    "pr newswire": 26,
    "globenewswire": 27,
    "benzinga": 28,
}

DEMOTED_WEEKLY_PUBLISHERS = {
    "24/7 wall st.",
    "24/7 wall st",
    "benzinga",
    "crypto prowl",
    "investor's business daily",
    "ibd",
    "marketbeat",
    "motley fool",
    "seeking alpha",
    "simply wall st.",
    "simply wall st",
    "the motley fool",
    "zacks",
    "zacks investment research",
}

_PUBLISHER_REPLACEMENTS = {
    "AP News": "Associated Press",
    "FT.com": "Financial Times",
    "Reuters News": "Reuters",
    "The Associated Press": "Associated Press",
    "WSJ.com": "Wall Street Journal",
}

_DOMAIN_SOURCE_MAP = {
    "apnews.com": "Associated Press",
    "asia.nikkei.com": "Nikkei Asia",
    "axios.com": "Axios",
    "barrons.com": "Barron's",
    "bbc.com": "BBC",
    "benzinga.com": "Benzinga",
    "bloomberg.com": "Bloomberg",
    "businessinsider.com": "Business Insider",
    "cnbc.com": "CNBC",
    "cnn.com": "CNN",
    "economist.com": "The Economist",
    "etf.com": "ETF.com",
    "finance.yahoo.com": "Yahoo Finance",
    "fortune.com": "Fortune",
    "ft.com": "Financial Times",
    "globenewswire.com": "GlobeNewswire",
    "investing.com": "Investing.com",
    "investors.com": "Investor's Business Daily",
    "marketbeat.com": "MarketBeat",
    "marketwatch.com": "MarketWatch",
    "morningstar.com": "Morningstar",
    "nasdaq.com": "Nasdaq",
    "nytimes.com": "The New York Times",
    "prnewswire.com": "PR Newswire",
    "reuters.com": "Reuters",
    "seekingalpha.com": "Seeking Alpha",
    "simplywall.st": "Simply Wall St.",
    "spglobal.com": "S&P Global",
    "theguardian.com": "The Guardian",
    "washingtonpost.com": "The Washington Post",
    "wsj.com": "Wall Street Journal",
    "zacks.com": "Zacks",
}

_ADVICE_MARKERS = (
    " buy ",
    " sell ",
    " to buy ",
    "before it soars",
    "better buy",
    "buy now",
    "buy right now",
    "etfs to buy",
    "invest $",
    "should i buy",
    "should i invest",
    "should you buy",
    "should you invest",
    "stocks to buy",
    "time to buy",
    "worth buying",
)
_OPINION_MARKERS = ("column:", "editorial:", "op-ed", "opinion:")
_GENERIC_MARKET_MARKERS = (
    "bubble",
    "correction",
    "euphoria",
    "inflation",
    "market rally",
    "not different this time",
    "rate cut",
    "rate hike",
    "stock market",
    "this time",
)
_ETF_USEFUL_MARKERS = (
    "asset flow",
    "benchmark",
    "distribution",
    "dividend",
    "etf",
    "expense ratio",
    "fee",
    "flow",
    "fund",
    "holding",
    "index",
    "large-cap",
    "large cap",
    "nav",
    "s&p 500",
    "sp500",
    "total return",
    "vanguard",
)
_STOCK_USEFUL_MARKERS = (
    "blackwell",
    "capex",
    "customer",
    "data center",
    "earnings",
    "filing",
    "forecast",
    "gpu",
    "guidance",
    "infrastructure",
    "launch",
    "margin",
    "product",
    "regulatory",
    "revenue",
    "sec",
    "supply",
)
_TICKER_ALIASES = {
    "AAPL": ("apple",),
    "AMZN": ("amazon",),
    "GOOGL": ("alphabet", "google"),
    "IVV": ("ishares core s&p 500", "s&p 500"),
    "META": ("meta platforms", "meta"),
    "MSFT": ("microsoft",),
    "NVDA": ("nvidia",),
    "QQQ": ("invesco qqq", "nasdaq-100", "nasdaq 100"),
    "SPY": ("spdr s&p 500", "s&p 500"),
    "TSLA": ("tesla",),
    "VOO": ("vanguard s&p 500", "s&p 500"),
}


@dataclass(frozen=True)
class TickerNewsQuality:
    publisher: str
    publisher_priority: int
    publisher_tier: str
    publisher_score: int
    acquisition_score: int
    ticker_relevance_score: int
    beginner_utility_score: int
    total_score: int
    suppression_reasons: tuple[str, ...]


def clean_news_publisher(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return _PUBLISHER_REPLACEMENTS.get(text, text)


def news_source_from_domain(domain: str | None) -> str | None:
    normalized = (domain or "").lower().removeprefix("www.")
    return _DOMAIN_SOURCE_MAP.get(normalized)


def publisher_priority(source: str | None) -> int:
    normalized = _normalized_publisher(source)
    return NEWS_PUBLISHER_PRIORITY.get(normalized, 99)


def publisher_tier(source: str | None) -> str:
    normalized = _normalized_publisher(source)
    priority = NEWS_PUBLISHER_PRIORITY.get(normalized)
    if normalized in DEMOTED_WEEKLY_PUBLISHERS:
        return "demoted"
    if priority is None:
        return "unknown"
    if priority <= 10:
        return "top_tier"
    if priority <= 21:
        return "reputable_finance"
    return "standard"


def score_ticker_weekly_news(
    *,
    ticker: str,
    asset_type: str,
    asset_name: str | None,
    title: str | None,
    summary: str | None,
    publisher: str | None,
    source_rank_tier: str,
    source_type: str,
    event_type: str | None,
    is_official: bool = False,
) -> TickerNewsQuality:
    normalized_ticker = ticker.strip().upper()
    clean_publisher = clean_news_publisher(publisher) or "Unknown publisher"
    tier = publisher_tier(clean_publisher)
    priority = publisher_priority(clean_publisher)
    text = f" {title or ''} {summary or ''} ".lower()
    official = is_official or source_rank_tier in {
        "official_filing",
        "investor_relations_release",
        "etf_issuer_announcement",
        "prospectus_update",
        "fact_sheet_change",
    }
    acquisition_score = _acquisition_score(source_rank_tier, source_type)
    publisher_score = _publisher_score(tier, official)
    relevance_score, relevance_reasons = _ticker_relevance_score(
        normalized_ticker,
        asset_type=asset_type,
        asset_name=asset_name,
        text=text,
        official=official,
    )
    utility_score = _beginner_utility_score(asset_type=asset_type, text=text, event_type=event_type)
    reasons = set(relevance_reasons)

    if _is_advice_like(text):
        reasons.add("advice_like")
    if _is_opinion_like(text):
        reasons.add("opinion_or_column")
    if (
        asset_type == "etf"
        and _has_generic_market_context(text)
        and relevance_score < 35
        and not official
    ):
        reasons.add("generic_market_context_for_ticker")
    if tier == "demoted" and (relevance_score < 35 or utility_score < 12) and not official:
        reasons.add("demoted_publisher_backfill_only")
    if priority >= 99 and tier != "demoted" and relevance_score < 35 and not official:
        reasons.add("low_source_quality")

    total_score = publisher_score + acquisition_score + relevance_score + utility_score
    return TickerNewsQuality(
        publisher=clean_publisher,
        publisher_priority=priority,
        publisher_tier=tier,
        publisher_score=publisher_score,
        acquisition_score=acquisition_score,
        ticker_relevance_score=relevance_score,
        beginner_utility_score=utility_score,
        total_score=total_score,
        suppression_reasons=tuple(sorted(reasons)),
    )


def _ticker_relevance_score(
    ticker: str,
    *,
    asset_type: str,
    asset_name: str | None,
    text: str,
    official: bool,
) -> tuple[int, set[str]]:
    if official:
        return 45, set()
    aliases = {ticker.lower(), *_TICKER_ALIASES.get(ticker, ())}
    aliases.update(_name_aliases(asset_name))
    alias_hit = any(alias and alias in text for alias in aliases)
    if asset_type == "etf":
        useful_hook = any(marker in text for marker in _ETF_USEFUL_MARKERS)
        if alias_hit and useful_hook:
            return 45, set()
        if alias_hit:
            return 38, set()
        if useful_hook:
            return 28, set()
        return 0, {"weak_ticker_relevance"}
    useful_hook = any(marker in text for marker in _STOCK_USEFUL_MARKERS)
    if alias_hit and useful_hook:
        return 45, set()
    if alias_hit:
        return 38, set()
    if useful_hook:
        return 18, {"weak_ticker_relevance"}
    return 0, {"weak_ticker_relevance"}


def _beginner_utility_score(*, asset_type: str, text: str, event_type: str | None) -> int:
    score = 0
    if event_type in {
        "earnings",
        "fee_change",
        "guidance",
        "index_change",
        "methodology_change",
        "product_announcement",
        "regulatory_event",
        "sponsor_update",
    }:
        score += 12
    markers = _ETF_USEFUL_MARKERS if asset_type == "etf" else _STOCK_USEFUL_MARKERS
    if any(marker in text for marker in markers):
        score += 12
    if _has_generic_market_context(text):
        score -= 6
    return max(0, score)


def _publisher_score(tier: str, official: bool) -> int:
    if official:
        return 30
    return {
        "top_tier": 28,
        "reputable_finance": 24,
        "standard": 15,
        "demoted": 5,
        "unknown": 4,
    }.get(tier, 4)


def _acquisition_score(source_rank_tier: str, source_type: str) -> int:
    if source_rank_tier in {
        "official_filing",
        "investor_relations_release",
        "etf_issuer_announcement",
        "prospectus_update",
        "fact_sheet_change",
    }:
        return 30
    if source_rank_tier == "allowlisted_news":
        return 16
    if "yahoo" in source_type:
        return 10
    return 12


def _name_aliases(asset_name: str | None) -> set[str]:
    cleaned = (asset_name or "").lower()
    aliases: set[str] = set()
    for suffix in (" inc.", " corporation", " corp.", " company", " class a"):
        cleaned = cleaned.replace(suffix, "")
    if cleaned:
        aliases.add(cleaned.strip())
        first_word = cleaned.split()[0]
        if len(first_word) > 3:
            aliases.add(first_word)
    return aliases


def _is_advice_like(text: str) -> bool:
    padded = f" {text.lower()} "
    return any(marker in padded for marker in _ADVICE_MARKERS)


def _is_opinion_like(text: str) -> bool:
    stripped = text.strip().lower()
    return any(stripped.startswith(marker) for marker in _OPINION_MARKERS)


def _has_generic_market_context(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _GENERIC_MARKET_MARKERS)


def _normalized_publisher(source: str | None) -> str:
    clean = clean_news_publisher(source) or ""
    return clean.lower().strip()


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None
