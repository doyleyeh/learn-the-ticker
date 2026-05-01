from pathlib import Path

from backend.models import AssetStatus, FreshnessState
from backend.glossary import build_glossary_response
from backend.retrieval import (
    build_asset_knowledge_pack,
    build_asset_knowledge_pack_result,
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
    richer_fields_by_ticker = {
        "AAPL": {
            "products_services_detail",
            "business_quality_strength",
            "financial_quality_revenue_trend",
            "valuation_data_limitation",
        },
        "VOO": {"holdings_exposure_detail", "construction_methodology", "trading_data_limitation"},
        "QQQ": {"holdings_exposure_detail", "construction_methodology", "trading_data_limitation"},
    }

    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)
        fact_fields = {fact.fact.field_name for fact in pack.normalized_facts}

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
        assert richer_fields_by_ticker[ticker] <= fact_fields
        assert all(source.allowlist_status.value == "allowed" for source in pack.source_documents)
        assert all(source.source_use_policy.value in {"full_text_allowed", "summary_allowed"} for source in pack.source_documents)
        assert all(source.source_quality.value in {"official", "issuer", "fixture"} for source in pack.source_documents)


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
        glossary = build_glossary_response(ticker)
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
            *{binding.asset_ticker for binding in glossary.citation_bindings},
            *{source.asset_ticker for source in glossary.source_references},
            *{reference.asset_ticker for reference in glossary.evidence_references},
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


def test_stock_etf_comparison_pack_is_bounded_to_aapl_and_voo():
    for left, right in [("AAPL", "VOO"), ("VOO", "AAPL")]:
        pack = build_comparison_knowledge_pack(left, right)
        allowed = {"AAPL", "VOO"}

        assert pack.comparison_pack_id == "AAPL_vs_VOO"
        assert pack.left_asset_pack.asset.ticker == left
        assert pack.right_asset_pack.asset.ticker == right
        assert pack.left_asset_pack.asset.asset_type.value != pack.right_asset_pack.asset.asset_type.value
        assert {pack.left_asset_pack.asset.ticker, pack.right_asset_pack.asset.ticker} == allowed
        assert {difference.dimension for difference in pack.computed_differences} == {
            "Structure",
            "Basket membership",
            "Breadth",
            "Cost model",
            "Educational role",
        }
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


def test_knowledge_pack_build_result_is_deterministic_and_metadata_only_for_cached_assets():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        first = build_asset_knowledge_pack_result(ticker)
        second = build_asset_knowledge_pack_result(ticker.lower())
        pack = build_asset_knowledge_pack(ticker)

        assert first.model_dump(mode="json") == second.model_dump(mode="json")
        assert first.schema_version == "asset-knowledge-pack-build-v1"
        assert first.pack_id == f"asset-knowledge-pack-{ticker.lower()}-local-fixture-v1"
        assert first.build_state.value == "available"
        assert first.generated_output_available is True
        assert first.generated_route == f"/assets/{ticker}"
        assert first.capabilities.can_open_generated_page is True
        assert first.capabilities.can_answer_chat is True
        assert first.capabilities.can_compare is True
        assert first.counts.source_document_count == len(pack.source_documents)
        assert first.counts.normalized_fact_count == len(pack.normalized_facts)
        assert first.counts.source_chunk_count == len(pack.source_chunks)
        assert first.counts.recent_development_count == len(pack.recent_developments)
        assert first.counts.evidence_gap_count == len(pack.evidence_gaps)
        assert first.knowledge_pack_freshness_hash
        assert first.cache_key and "knowledge-pack" in first.cache_key
        assert first.cache_revalidation is not None
        assert first.cache_revalidation.reusable is False
        assert first.cache_revalidation.state.value == "miss"
        assert {"weekly_news_focus", "ai_comprehensive_analysis"} <= {label.section_id for label in first.section_freshness}
        assert first.no_live_external_calls is True
        assert first.exports_full_source_documents is False

        assert set(first.source_document_ids) == {source.source_document_id for source in pack.source_documents}
        assert {source.asset_ticker for source in first.source_documents} == {ticker}
        assert all(source.allowlist_status.value == "allowed" for source in first.source_documents)
        assert all(source.source_use_policy.value in {"full_text_allowed", "summary_allowed"} for source in first.source_documents)
        assert all(source.permitted_operations.can_support_citations for source in first.source_documents)
        assert all(checksum.allowlist_status.value == "allowed" for checksum in first.source_checksums)
        assert all(checksum.source_use_policy.value in {"full_text_allowed", "summary_allowed"} for checksum in first.source_checksums)
        assert {fact.asset_ticker for fact in first.normalized_facts} == {ticker}
        assert {chunk.asset_ticker for chunk in first.source_chunks} == {ticker}
        assert {recent.asset_ticker for recent in first.recent_developments} == {ticker}
        assert all(fact.source_document_id in first.source_document_ids for fact in first.normalized_facts)
        assert all(chunk.source_document_id in first.source_document_ids for chunk in first.source_chunks)
        assert all(recent.source_document_id in first.source_document_ids for recent in first.recent_developments)
        assert any(citation_id.startswith("c_fact_") for citation_id in first.citation_ids)
        assert any(citation_id.startswith("c_chk_") for citation_id in first.citation_ids)
        assert any(citation_id.startswith("c_recent_") for citation_id in first.citation_ids)

        dumped = first.model_dump(mode="json")
        assert "supporting_passage" not in dumped
        assert "Apple designs, manufactures" not in str(dumped)
        assert "VOO seeks to track" not in str(dumped)
        assert "QQQ tracks the Nasdaq-100" not in str(dumped)


def test_knowledge_pack_build_result_non_generated_states_do_not_expose_pack_evidence():
    cases = [
        ("SPY", "eligible_not_cached", "eligible_not_cached"),
        ("TQQQ", "unsupported", "unsupported"),
        ("ZZZZ", "unknown", "unknown"),
    ]

    for ticker, expected_build_state, expected_cache_state in cases:
        result = build_asset_knowledge_pack_result(ticker)

        assert result.ticker == ticker
        assert result.build_state.value == expected_build_state
        assert result.generated_output_available is False
        assert result.reusable_generated_output_cache_hit is False
        assert result.generated_route is None
        assert result.capabilities.can_open_generated_page is False
        assert result.capabilities.can_answer_chat is False
        assert result.capabilities.can_compare is False
        assert result.source_document_ids == []
        assert result.citation_ids == []
        assert result.source_documents == []
        assert result.normalized_facts == []
        assert result.source_chunks == []
        assert result.recent_developments == []
        assert result.source_checksums == []
        assert result.knowledge_pack_freshness_hash is None
        assert result.counts.source_document_count == 0
        assert result.counts.citation_count == 0
        assert result.counts.normalized_fact_count == 0
        assert result.counts.source_chunk_count == 0
        assert result.counts.recent_development_count == 0
        assert result.counts.evidence_gap_count == 1
        assert result.evidence_gaps[0].field_name == "asset_knowledge_pack"
        assert result.cache_revalidation is not None
        assert result.cache_revalidation.state.value == expected_cache_state
        assert result.cache_revalidation.reusable is False

    eligible = build_asset_knowledge_pack_result("SPY")
    assert eligible.asset.asset_type.value == "etf"
    assert eligible.capabilities.can_request_ingestion is True


def test_retrieval_module_does_not_import_network_clients():
    retrieval_source = (ROOT / "backend" / "retrieval.py").read_text(encoding="utf-8")

    forbidden_network_imports = [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "import redis",
        "psycopg",
        "sqlalchemy",
        "boto3",
        "openai",
        "anthropic",
        "os.environ",
        "api_key",
    ]
    for forbidden in forbidden_network_imports:
        assert forbidden not in retrieval_source
