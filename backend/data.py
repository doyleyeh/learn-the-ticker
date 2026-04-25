from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.etf_universe import blocked_etf_entries, legacy_eligible_not_cached_etf_metadata
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
    Top500StockUniverseEntry,
    Top500StockUniverseManifest,
)


STUB_TIMESTAMP = "2026-04-20T00:00:00Z"
TOP500_STOCK_UNIVERSE_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "universes" / "us_common_stocks_top500.current.json"
)
TOP500_STOCK_UNIVERSE_SCHEMA_VERSION = "top500-us-common-stock-universe-v1"


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _assert_no_manifest_advice_language(manifest: Top500StockUniverseManifest) -> None:
    text = " ".join(
        [
            manifest.coverage_purpose,
            manifest.policy_note,
            manifest.rank_basis,
            manifest.source_provenance,
            *(entry.rank_basis for entry in manifest.entries),
            *(entry.source_provenance for entry in manifest.entries),
        ]
    ).lower()
    forbidden_phrases = [
        "should buy",
        "should sell",
        "should hold",
        "price target",
        "target price",
        "model portfolio inclusion",
        "personalized allocation",
    ]
    hits = [phrase for phrase in forbidden_phrases if phrase in text]
    if hits:
        raise ValueError(f"Top-500 manifest contains advice-like language: {hits}")


def validate_top500_stock_universe_manifest(manifest: Top500StockUniverseManifest) -> Top500StockUniverseManifest:
    if manifest.schema_version != TOP500_STOCK_UNIVERSE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported Top-500 manifest schema version: {manifest.schema_version}")
    if manifest.local_path != "data/universes/us_common_stocks_top500.current.json":
        raise ValueError("Top-500 manifest local_path must point to the runtime local manifest path.")
    if manifest.production_mirror_env_var != "TOP500_UNIVERSE_MANIFEST_URI":
        raise ValueError("Top-500 manifest must declare the private production mirror env var.")
    if manifest.rank_limit != 500:
        raise ValueError("Top-500 manifest rank_limit must remain 500.")
    if not manifest.entries:
        raise ValueError("Top-500 manifest must contain at least one stock entry.")

    tickers = [entry.ticker for entry in manifest.entries]
    ranks = [entry.rank for entry in manifest.entries]
    if len(tickers) != len(set(tickers)):
        raise ValueError("Top-500 manifest entries must have unique tickers.")
    if len(ranks) != len(set(ranks)):
        raise ValueError("Top-500 manifest entries must have unique ranks.")
    if any(entry.ticker != normalize_ticker(entry.ticker) for entry in manifest.entries):
        raise ValueError("Top-500 manifest tickers must be normalized uppercase symbols.")
    if any(entry.asset_type != "stock" for entry in manifest.entries):
        raise ValueError("Top-500 manifest must contain stock entries only.")
    if any(entry.security_type != "us_listed_common_stock" for entry in manifest.entries):
        raise ValueError("Top-500 manifest entries must be U.S.-listed common stocks only.")
    if any(entry.rank < 1 or entry.rank > manifest.rank_limit for entry in manifest.entries):
        raise ValueError("Top-500 manifest ranks must be within the declared rank_limit.")
    if any(not entry.checksum_input or not entry.generated_checksum for entry in manifest.entries):
        raise ValueError("Top-500 manifest entries must include checksum inputs and generated checksums.")
    if any(entry.snapshot_date != manifest.snapshot_date for entry in manifest.entries):
        raise ValueError("Top-500 manifest entry snapshot dates must match the manifest snapshot date.")
    _assert_no_manifest_advice_language(manifest)
    return manifest


@lru_cache(maxsize=1)
def load_top500_stock_universe_manifest() -> Top500StockUniverseManifest:
    with TOP500_STOCK_UNIVERSE_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_top500_stock_universe_manifest(Top500StockUniverseManifest.model_validate(payload))


def top500_stock_universe_entries_by_ticker() -> dict[str, Top500StockUniverseEntry]:
    return {entry.ticker: entry for entry in load_top500_stock_universe_manifest().entries}


def top500_stock_universe_entry(ticker: str) -> Top500StockUniverseEntry | None:
    return top500_stock_universe_entries_by_ticker().get(normalize_ticker(ticker))


def is_top500_manifest_stock(ticker: str) -> bool:
    return top500_stock_universe_entry(ticker) is not None


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


_STATIC_UNSUPPORTED_ASSETS: dict[str, str] = {
    "BTC": "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
    "ETH": "Crypto assets are outside the current U.S. stock and plain-vanilla ETF scope.",
}


_STATIC_UNSUPPORTED_ASSET_SEARCH_METADATA: dict[str, dict[str, str | list[str] | None]] = {
    "BTC": {
        "name": "Bitcoin",
        "category": "crypto",
        "aliases": ["bitcoin", "crypto"],
    },
    "ETH": {
        "name": "Ethereum",
        "category": "crypto",
        "aliases": ["ethereum", "ether", "crypto"],
    },
}


def _blocked_etf_asset_message(category: str) -> str:
    labels = {
        "leveraged_etf": "Leveraged ETFs",
        "inverse_etf": "Inverse ETFs",
        "active_etf": "Active ETFs",
        "fixed_income_etf": "Fixed-income ETFs",
        "commodity_etf": "Commodity ETFs",
        "multi_asset_etf": "Multi-asset ETFs",
        "etn": "ETNs",
        "other_unsupported": "Unsupported ETF-like products",
    }
    label = labels.get(category, "This ETF-like product")
    return f"{label} are outside the current non-leveraged U.S. equity ETF scope."


def _unsupported_etf_assets_from_manifest() -> dict[str, str]:
    return {
        ticker: _blocked_etf_asset_message(entry.etf_category.value)
        for ticker, entry in blocked_etf_entries().items()
        if entry.support_state.value == "recognized_unsupported"
    }


def _unsupported_etf_search_metadata_from_manifest() -> dict[str, dict[str, str | list[str] | None]]:
    return {
        ticker: {
            "name": entry.fund_name,
            "category": entry.etf_category.value,
            "aliases": entry.aliases,
            "issuer": entry.issuer,
            "exchange": entry.exchange,
            "support_state": entry.support_state.value,
            "source_provenance": entry.source_provenance,
            "snapshot_date": entry.snapshot_date,
        }
        for ticker, entry in blocked_etf_entries().items()
        if entry.support_state.value == "recognized_unsupported"
    }


UNSUPPORTED_ASSETS: dict[str, str] = {
    **_STATIC_UNSUPPORTED_ASSETS,
    **_unsupported_etf_assets_from_manifest(),
}


UNSUPPORTED_ASSET_SEARCH_METADATA: dict[str, dict[str, str | list[str] | None]] = {
    **_STATIC_UNSUPPORTED_ASSET_SEARCH_METADATA,
    **_unsupported_etf_search_metadata_from_manifest(),
}


_ELIGIBLE_NOT_CACHED_ETF_ASSETS: dict[str, dict[str, str | list[str] | None]] = (
    legacy_eligible_not_cached_etf_metadata()
)


def _eligible_not_cached_stock_assets_from_manifest() -> dict[str, dict[str, str | list[str] | None]]:
    stocks: dict[str, dict[str, str | list[str] | None]] = {}
    for entry in load_top500_stock_universe_manifest().entries:
        if entry.ticker in ASSETS:
            continue
        stocks[entry.ticker] = {
            "name": entry.name,
            "asset_type": entry.asset_type,
            "exchange": entry.exchange,
            "issuer": None,
            "aliases": entry.aliases,
            "launch_group": entry.launch_group,
            "manifest_id": load_top500_stock_universe_manifest().manifest_id,
            "manifest_rank": str(entry.rank),
            "rank_basis": entry.rank_basis,
            "source_provenance": entry.source_provenance,
            "snapshot_date": entry.snapshot_date,
            "approval_timestamp": entry.approval_timestamp,
        }
    return stocks


ELIGIBLE_NOT_CACHED_ASSETS: dict[str, dict[str, str | list[str] | None]] = {
    **_ELIGIBLE_NOT_CACHED_ETF_ASSETS,
    **_eligible_not_cached_stock_assets_from_manifest(),
}


def _out_of_scope_etf_assets_from_manifest() -> dict[str, dict[str, str | list[str] | None]]:
    out_of_scope: dict[str, dict[str, str | list[str] | None]] = {}
    for ticker, entry in blocked_etf_entries().items():
        if entry.support_state.value != "out_of_scope":
            continue
        out_of_scope[ticker] = {
            "name": entry.fund_name,
            "asset_type": entry.asset_type,
            "exchange": entry.exchange,
            "issuer": entry.issuer,
            "aliases": entry.aliases,
            "reason": _blocked_etf_asset_message(entry.etf_category.value),
            "etf_category": entry.etf_category.value,
            "support_state": entry.support_state.value,
            "source_provenance": entry.source_provenance,
            "snapshot_date": entry.snapshot_date,
        }
    return out_of_scope


OUT_OF_SCOPE_COMMON_STOCKS: dict[str, dict[str, str | list[str] | None]] = {
    "GME": {
        "name": "GameStop Corp.",
        "asset_type": "stock",
        "exchange": "NYSE",
        "issuer": None,
        "aliases": ["gamestop", "gamestop corp", "common stock"],
        "reason": (
            "Recognized U.S.-listed common stock outside the local Top-500 manifest; out of scope for "
            "generated outputs unless explicitly approved for on-demand ingestion later."
        ),
    },
    **_out_of_scope_etf_assets_from_manifest(),
}


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
