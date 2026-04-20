from pathlib import Path

from backend.models import AssetStatus, FreshnessState
from backend.retrieval import (
    build_asset_knowledge_pack,
    build_comparison_knowledge_pack,
    load_retrieval_fixture_dataset,
    supported_fixture_tickers,
)


ROOT = Path(__file__).resolve().parents[2]


def test_required_stock_and_etf_retrieval_fixtures_exist():
    dataset = load_retrieval_fixture_dataset()
    tickers = set(supported_fixture_tickers())

    assert {"AAPL", "VOO", "QQQ"} <= tickers
    assert dataset.no_live_external_calls is True
    assert sum(1 for fixture in dataset.assets if fixture.asset.asset_type.value == "stock") >= 1
    assert sum(1 for fixture in dataset.assets if fixture.asset.asset_type.value == "etf") >= 2


def test_each_supported_fixture_has_source_chunks_facts_freshness_and_recent_layer():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)

        assert pack.asset.status is AssetStatus.supported
        assert pack.freshness.facts_as_of
        assert pack.freshness.recent_events_as_of
        assert pack.source_documents
        assert pack.source_chunks
        assert pack.normalized_facts
        assert pack.recent_developments
        assert any(fact.fact.field_name == "canonical_asset_identity" for fact in pack.normalized_facts)
        assert all(source.asset_ticker == ticker for source in pack.source_documents)
        assert all(chunk.chunk.asset_ticker == ticker for chunk in pack.source_chunks)
        assert all(fact.fact.asset_ticker == ticker for fact in pack.normalized_facts)
        assert all(recent.recent_development.asset_ticker == ticker for recent in pack.recent_developments)


def test_retrieval_items_attach_source_metadata_to_facts_chunks_and_recent_developments():
    pack = build_asset_knowledge_pack("VOO")

    fact = next(item for item in pack.normalized_facts if item.fact.field_name == "expense_ratio")
    assert fact.source_document.source_document_id == fact.fact.source_document_id
    assert fact.source_chunk.chunk_id == fact.fact.source_chunk_id
    assert fact.source_document.publisher == "Vanguard"
    assert fact.source_chunk.text

    chunk = pack.source_chunks[0]
    assert chunk.source_document.source_document_id == chunk.chunk.source_document_id
    assert chunk.source_document.freshness_state is FreshnessState.fresh

    recent = pack.recent_developments[0]
    assert recent.source_document.source_type == "recent_development"
    assert recent.source_chunk.supported_claim_types == ["recent"]


def test_single_asset_retrieval_never_returns_wrong_asset_evidence():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)
        returned_assets = {
            *{source.asset_ticker for source in pack.source_documents},
            *{chunk.chunk.asset_ticker for chunk in pack.source_chunks},
            *{chunk.source_document.asset_ticker for chunk in pack.source_chunks},
            *{fact.fact.asset_ticker for fact in pack.normalized_facts},
            *{fact.source_document.asset_ticker for fact in pack.normalized_facts},
            *{fact.source_chunk.asset_ticker for fact in pack.normalized_facts},
            *{recent.recent_development.asset_ticker for recent in pack.recent_developments},
            *{recent.source_document.asset_ticker for recent in pack.recent_developments},
            *{recent.source_chunk.asset_ticker for recent in pack.recent_developments},
        }

        assert returned_assets == {ticker}


def test_comparison_pack_is_bounded_to_voo_and_qqq():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    allowed = {"VOO", "QQQ"}

    assert pack.comparison_pack_id == "VOO_vs_QQQ"
    assert {pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker} == allowed
    assert pack.computed_differences
    assert {source.asset_ticker for source in pack.comparison_sources} <= allowed

    fact_assets = {
        fact.fact.asset_ticker
        for asset_pack in [pack.left_asset_pack, pack.right_asset_pack]
        for fact in asset_pack.normalized_facts
    }
    assert fact_assets == allowed


def test_missing_stale_unsupported_and_insufficient_evidence_are_explicit():
    aapl = build_asset_knowledge_pack("AAPL")
    voo = build_asset_knowledge_pack("VOO")
    qqq = build_asset_knowledge_pack("QQQ")
    unsupported = build_asset_knowledge_pack("BTC")
    unknown = build_asset_knowledge_pack("ZZZZ")

    gap_states = {
        gap.evidence_state
        for pack in [aapl, voo, qqq, unsupported, unknown]
        for gap in pack.evidence_gaps
    }
    assert {"missing", "stale", "unsupported", "insufficient"} <= gap_states
    assert unsupported.asset.status is AssetStatus.unsupported
    assert unknown.asset.status is AssetStatus.unknown
    assert unsupported.source_documents == []
    assert unknown.normalized_facts == []


def test_retrieval_module_does_not_import_network_clients():
    retrieval_source = (ROOT / "backend" / "retrieval.py").read_text(encoding="utf-8")

    forbidden_network_imports = [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
    ]
    for forbidden in forbidden_network_imports:
        assert forbidden not in retrieval_source
