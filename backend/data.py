from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.models import (
    AssetIdentity,
    AssetStatus,
    AssetType,
    BeginnerSummary,
    Claim,
    Citation,
    Freshness,
    FreshnessState,
    MetricValue,
    RecentDevelopment,
    RiskItem,
    SourceDocument,
    StateMessage,
    SuitabilitySummary,
)


STUB_TIMESTAMP = "2026-04-20T00:00:00Z"


def _source(
    source_document_id: str,
    title: str,
    publisher: str,
    source_type: str,
    url: str,
    passage: str,
) -> SourceDocument:
    return SourceDocument(
        source_document_id=source_document_id,
        source_type=source_type,
        title=title,
        publisher=publisher,
        url=url,
        published_at="2026-04-01",
        retrieved_at=STUB_TIMESTAMP,
        freshness_state=FreshnessState.fresh,
        is_official=True,
        supporting_passage=passage,
    )


def _citation(citation_id: str, source: SourceDocument) -> Citation:
    return Citation(
        citation_id=citation_id,
        source_document_id=source.source_document_id,
        title=source.title,
        publisher=source.publisher,
        freshness_state=source.freshness_state,
    )


VOO_SOURCE = _source(
    "src_voo_fact_sheet",
    "Vanguard S&P 500 ETF fact sheet",
    "Vanguard",
    "issuer_fact_sheet",
    "https://investor.vanguard.com/",
    "Stub passage: VOO seeks to track the S&P 500 Index and publishes fund costs, holdings, and risk information.",
)
QQQ_SOURCE = _source(
    "src_qqq_fact_sheet",
    "Invesco QQQ Trust fact sheet",
    "Invesco",
    "issuer_fact_sheet",
    "https://www.invesco.com/",
    "Stub passage: QQQ tracks the Nasdaq-100 Index and is more concentrated in large growth-oriented companies.",
)
AAPL_SOURCE = _source(
    "src_aapl_10k",
    "Apple Inc. Form 10-K",
    "U.S. SEC",
    "sec_filing",
    "https://www.sec.gov/",
    "Stub passage: Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and services.",
)


ASSETS: dict[str, dict[str, Any]] = {
    "VOO": {
        "identity": AssetIdentity(
            ticker="VOO",
            name="Vanguard S&P 500 ETF",
            asset_type=AssetType.etf,
            exchange="NYSE Arca",
            issuer="Vanguard",
            status=AssetStatus.supported,
            supported=True,
        ),
        "freshness": Freshness(
            page_last_updated_at=STUB_TIMESTAMP,
            facts_as_of="2026-04-01",
            holdings_as_of="2026-04-01",
            recent_events_as_of="2026-04-20",
            freshness_state=FreshnessState.fresh,
        ),
        "sources": [VOO_SOURCE],
        "citations": [_citation("c_voo_profile", VOO_SOURCE)],
        "snapshot": {
            "issuer": "Vanguard",
            "benchmark": "S&P 500 Index",
            "expense_ratio": MetricValue(value=0.03, unit="%", citation_ids=["c_voo_profile"]),
            "holdings_count": MetricValue(value=500, unit="approximate companies", citation_ids=["c_voo_profile"]),
        },
        "summary": BeginnerSummary(
            what_it_is="VOO is a plain-vanilla ETF designed to follow the S&P 500 Index, a basket of large U.S. companies.",
            why_people_consider_it="Beginners often study it because it offers broad large-company exposure in one fund with a simple index-tracking approach.",
            main_catch="It is still stock-market exposure, so it can fall with the market and is not a complete plan by itself.",
        ),
        "claims": [
            Claim(
                claim_id="claim_voo_tracks_index",
                claim_text="VOO is designed to follow the S&P 500 Index.",
                citation_ids=["c_voo_profile"],
            )
        ],
        "risks": [
            RiskItem(
                title="Market risk",
                plain_english_explanation="The fund can lose value when large U.S. stocks fall.",
                citation_ids=["c_voo_profile"],
            ),
            RiskItem(
                title="Large-company focus",
                plain_english_explanation="The fund does not cover every public company or every asset class.",
                citation_ids=["c_voo_profile"],
            ),
            RiskItem(
                title="Index tracking limits",
                plain_english_explanation="The fund aims to follow an index rather than avoid weaker areas of the market.",
                citation_ids=["c_voo_profile"],
            ),
        ],
        "recent": [
            RecentDevelopment(
                title="No high-signal recent development in stub data",
                summary="This skeleton keeps recent context separate and reports that no major recent item is available in the local fixture.",
                event_date=None,
                citation_ids=["c_voo_profile"],
                freshness_state=FreshnessState.fresh,
            )
        ],
        "suitability": SuitabilitySummary(
            may_fit="Educationally, it is useful for learning how broad U.S. large-company index ETFs work.",
            may_not_fit="It may be less useful for learning about bonds, international stocks, or narrow sector exposure.",
            learn_next="Compare it with a total-market ETF and a more concentrated growth ETF to understand diversification.",
        ),
        "facts": {
            "role": "Broad U.S. large-company ETF",
            "holdings": ["Large U.S. companies represented in the S&P 500 Index"],
            "cost_context": MetricValue(value=0.03, unit="%", citation_ids=["c_voo_profile"]),
        },
    },
    "QQQ": {
        "identity": AssetIdentity(
            ticker="QQQ",
            name="Invesco QQQ Trust",
            asset_type=AssetType.etf,
            exchange="NASDAQ",
            issuer="Invesco",
            status=AssetStatus.supported,
            supported=True,
        ),
        "freshness": Freshness(
            page_last_updated_at=STUB_TIMESTAMP,
            facts_as_of="2026-04-01",
            holdings_as_of="2026-04-01",
            recent_events_as_of="2026-04-20",
            freshness_state=FreshnessState.fresh,
        ),
        "sources": [QQQ_SOURCE],
        "citations": [_citation("c_qqq_profile", QQQ_SOURCE)],
        "snapshot": {
            "issuer": "Invesco",
            "benchmark": "Nasdaq-100 Index",
            "expense_ratio": MetricValue(value=0.20, unit="%", citation_ids=["c_qqq_profile"]),
            "holdings_count": MetricValue(value=100, unit="approximate companies", citation_ids=["c_qqq_profile"]),
        },
        "summary": BeginnerSummary(
            what_it_is="QQQ is an ETF designed to follow the Nasdaq-100 Index.",
            why_people_consider_it="Beginners often study it to understand concentrated exposure to large non-financial Nasdaq-listed companies.",
            main_catch="It is narrower than a broad-market fund, so a few large companies and sectors can drive more of the result.",
        ),
        "claims": [
            Claim(
                claim_id="claim_qqq_tracks_index",
                claim_text="QQQ is designed to follow the Nasdaq-100 Index.",
                citation_ids=["c_qqq_profile"],
            )
        ],
        "risks": [
            RiskItem(
                title="Concentration risk",
                plain_english_explanation="A smaller group of large holdings can have an outsized impact on results.",
                citation_ids=["c_qqq_profile"],
            ),
            RiskItem(
                title="Sector tilt",
                plain_english_explanation="The fund can lean heavily toward growth-oriented technology and communication companies.",
                citation_ids=["c_qqq_profile"],
            ),
            RiskItem(
                title="Market risk",
                plain_english_explanation="The fund can fall when the stocks in its index decline.",
                citation_ids=["c_qqq_profile"],
            ),
        ],
        "recent": [
            RecentDevelopment(
                title="No high-signal recent development in stub data",
                summary="This skeleton keeps recent context separate and reports that no major recent item is available in the local fixture.",
                event_date=None,
                citation_ids=["c_qqq_profile"],
                freshness_state=FreshnessState.fresh,
            )
        ],
        "suitability": SuitabilitySummary(
            may_fit="Educationally, it is useful for learning how narrower growth-oriented ETF exposure differs from broad-market exposure.",
            may_not_fit="It may be less useful as an example of a diversified total-market fund.",
            learn_next="Compare its index, holdings count, and top-holding concentration with VOO.",
        ),
        "facts": {
            "role": "Narrower growth-oriented ETF",
            "holdings": ["Large Nasdaq-listed non-financial companies"],
            "cost_context": MetricValue(value=0.20, unit="%", citation_ids=["c_qqq_profile"]),
        },
    },
    "AAPL": {
        "identity": AssetIdentity(
            ticker="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.stock,
            exchange="NASDAQ",
            issuer=None,
            status=AssetStatus.supported,
            supported=True,
        ),
        "freshness": Freshness(
            page_last_updated_at=STUB_TIMESTAMP,
            facts_as_of="2026-04-01",
            holdings_as_of=None,
            recent_events_as_of="2026-04-20",
            freshness_state=FreshnessState.fresh,
        ),
        "sources": [AAPL_SOURCE],
        "citations": [_citation("c_aapl_profile", AAPL_SOURCE)],
        "snapshot": {
            "sector": "Technology",
            "industry": "Consumer electronics",
            "primary_business": "Products and services",
        },
        "summary": BeginnerSummary(
            what_it_is="Apple is a U.S.-listed company that sells devices, software, and services.",
            why_people_consider_it="Beginners often study it because its products are familiar and its filings explain a large global consumer technology business.",
            main_catch="A single company is less diversified than an ETF, so company-specific problems matter more.",
        ),
        "claims": [
            Claim(
                claim_id="claim_aapl_business",
                claim_text="Apple sells devices, software, and services.",
                citation_ids=["c_aapl_profile"],
            )
        ],
        "risks": [
            RiskItem(
                title="Product concentration",
                plain_english_explanation="A large business line can matter a lot to overall results.",
                citation_ids=["c_aapl_profile"],
            ),
            RiskItem(
                title="Competition",
                plain_english_explanation="Consumer technology markets can change quickly as competitors release new products.",
                citation_ids=["c_aapl_profile"],
            ),
            RiskItem(
                title="Supply chain and regulation",
                plain_english_explanation="Global operations can be affected by manufacturing, legal, or regulatory issues.",
                citation_ids=["c_aapl_profile"],
            ),
        ],
        "recent": [
            RecentDevelopment(
                title="No high-signal recent development in stub data",
                summary="This skeleton keeps recent context separate and reports that no major recent item is available in the local fixture.",
                event_date=None,
                citation_ids=["c_aapl_profile"],
                freshness_state=FreshnessState.fresh,
            )
        ],
        "suitability": SuitabilitySummary(
            may_fit="Educationally, it is useful for learning how a large single-company business model works.",
            may_not_fit="It should not be confused with diversified fund exposure.",
            learn_next="Compare company-specific risk with ETF diversification.",
        ),
        "facts": {
            "business_model": "Sells devices, software, and services",
            "diversification_context": "Single-company stock, not a fund",
        },
    },
}


UNSUPPORTED_ASSETS: dict[str, str] = {
    "BTC": "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
    "ETH": "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
    "TQQQ": "Leveraged ETFs are outside the current plain-vanilla ETF scope.",
    "SQQQ": "Inverse ETFs are outside the current plain-vanilla ETF scope.",
}


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def supported_asset(ticker: str) -> dict[str, Any] | None:
    asset = ASSETS.get(normalize_ticker(ticker))
    return deepcopy(asset) if asset else None


def fallback_asset(ticker: str) -> AssetIdentity:
    normalized = normalize_ticker(ticker)
    if normalized in UNSUPPORTED_ASSETS:
        return AssetIdentity(
            ticker=normalized,
            name=normalized,
            asset_type=AssetType.unsupported,
            status=AssetStatus.unsupported,
            supported=False,
        )
    return AssetIdentity(
        ticker=normalized,
        name=normalized,
        asset_type=AssetType.unknown,
        status=AssetStatus.unknown,
        supported=False,
    )


def state_for_asset(asset: AssetIdentity) -> StateMessage:
    if asset.status is AssetStatus.supported:
        return StateMessage(status=AssetStatus.supported, message="Asset is supported by deterministic stub data.")
    if asset.status is AssetStatus.unsupported:
        reason = UNSUPPORTED_ASSETS.get(asset.ticker, "This asset type is outside the current product scope.")
        return StateMessage(status=AssetStatus.unsupported, message=reason)
    return StateMessage(
        status=AssetStatus.unknown,
        message="This ticker is not available in the local skeleton data yet.",
    )


def empty_freshness() -> Freshness:
    return Freshness(
        page_last_updated_at=STUB_TIMESTAMP,
        facts_as_of=None,
        holdings_as_of=None,
        recent_events_as_of=None,
        freshness_state=FreshnessState.unknown,
    )
