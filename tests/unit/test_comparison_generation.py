from pathlib import Path
from typing import Any

from backend.citations import CitationEvidence, CitationValidationStatus
from backend.comparison import (
    PlannedComparisonClaim,
    generate_comparison,
    validate_comparison_response,
    validate_generated_comparison_claims,
)
from backend.models import AssetStatus, CompareResponse, FreshnessState, SourceDocument
from backend.retrieval import build_comparison_knowledge_pack
from backend.safety import find_forbidden_output_phrases


ROOT = Path(__file__).resolve().parents[2]


def test_voo_qqq_comparison_is_schema_valid_and_source_backed():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")
    validated = CompareResponse.model_validate(comparison.model_dump(mode="json"))

    assert validated.left_asset.ticker == "VOO"
    assert validated.right_asset.ticker == "QQQ"
    assert validated.state.status is AssetStatus.supported
    assert validated.comparison_type == "etf_vs_etf"
    assert validated.bottom_line_for_beginners is not None
    assert validated.citations

    dimensions = {difference.dimension for difference in validated.key_differences}
    assert {"Benchmark", "Expense ratio", "Holdings count", "Breadth", "Educational role"} <= dimensions

    citation_ids = {citation.citation_id for citation in validated.citations}
    source_ids = {source.source_document_id for source in validated.source_documents}
    used_citation_ids = {
        *{citation_id for item in validated.key_differences for citation_id in item.citation_ids},
        *validated.bottom_line_for_beginners.citation_ids,
    }
    assert used_citation_ids <= citation_ids
    assert {citation.source_document_id for citation in validated.citations} <= {
        source.source_document_id for source in pack.comparison_sources
    }
    assert {citation.source_document_id for citation in validated.citations} <= source_ids
    assert source_ids <= {source.source_document_id for source in pack.comparison_sources}
    assert all(source.title for source in validated.source_documents)
    assert all(source.publisher for source in validated.source_documents)
    assert all(source.source_type for source in validated.source_documents)
    assert all(source.url for source in validated.source_documents)
    assert all(source.published_at or source.as_of_date for source in validated.source_documents)
    assert all(source.retrieved_at for source in validated.source_documents)
    assert all(source.freshness_state is FreshnessState.fresh for source in validated.source_documents)
    assert all(source.is_official is True for source in validated.source_documents)
    assert all(source.supporting_passage for source in validated.source_documents)
    assert validate_comparison_response(validated, pack).valid


def test_voo_qqq_comparison_supports_reverse_ticker_order():
    pack = build_comparison_knowledge_pack("QQQ", "VOO")
    comparison = generate_comparison("QQQ", "VOO")

    assert comparison.left_asset.ticker == "QQQ"
    assert comparison.right_asset.ticker == "VOO"
    assert comparison.comparison_type == "etf_vs_etf"
    assert comparison.key_differences[0].plain_english_summary.startswith("QQQ tracks")
    assert comparison.source_documents
    assert {source.source_document_id for source in comparison.source_documents} <= {
        source.source_document_id for source in pack.comparison_sources
    }
    assert validate_comparison_response(comparison, pack).valid


def test_unavailable_comparisons_do_not_generate_claims_or_citations():
    cases = [
        ("VOO", "BTC", AssetStatus.unsupported),
        ("VOO", "ZZZZ", AssetStatus.unknown),
        ("AAPL", "VOO", AssetStatus.unknown),
    ]

    for left_ticker, right_ticker, expected_status in cases:
        comparison = generate_comparison(left_ticker, right_ticker)

        assert comparison.state.status is expected_status
        assert comparison.comparison_type == "unavailable"
        assert comparison.key_differences == []
        assert comparison.bottom_line_for_beginners is None
        assert comparison.citations == []
        assert comparison.source_documents == []


def test_comparison_validation_surfaces_missing_and_insufficient_evidence():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")

    missing = comparison.model_copy(deep=True)
    missing.key_differences[0].citation_ids = []
    assert validate_comparison_response(missing, pack).status is CitationValidationStatus.missing_citation

    insufficient = comparison.model_copy(deep=True)
    insufficient.key_differences[0].citation_ids = [insufficient.key_differences[0].citation_ids[0]]
    assert validate_comparison_response(insufficient, pack).status is CitationValidationStatus.insufficient_evidence

    outside_pack = comparison.model_copy(deep=True)
    outside_pack.key_differences[0].citation_ids = ["c_fact_aapl_primary_business"]
    assert validate_comparison_response(outside_pack, pack).status is CitationValidationStatus.citation_not_found


def test_comparison_source_metadata_validation_rejects_missing_wrong_stale_unsupported_and_empty_metadata():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")

    missing = comparison.model_copy(deep=True)
    missing.source_documents = []
    assert validate_comparison_response(missing, pack).status is CitationValidationStatus.citation_not_found

    wrong_asset = comparison.model_copy(deep=True)
    for citation in wrong_asset.citations:
        citation.source_document_id = "src_aapl_10k_fixture"
    wrong_asset.source_documents = [_aapl_source_document()]
    assert validate_comparison_response(wrong_asset, pack).status is CitationValidationStatus.wrong_asset

    stale = comparison.model_copy(deep=True)
    stale.source_documents[0].freshness_state = FreshnessState.stale
    assert validate_comparison_response(stale, pack).status is CitationValidationStatus.stale_source

    unsupported = comparison.model_copy(deep=True)
    unsupported.source_documents[0].source_type = "news_article"
    assert validate_comparison_response(unsupported, pack).status is CitationValidationStatus.unsupported_source

    insufficient = comparison.model_copy(deep=True)
    insufficient.source_documents[0].supporting_passage = ""
    assert validate_comparison_response(insufficient, pack).status is CitationValidationStatus.insufficient_evidence


def test_comparison_claim_validation_rejects_wrong_stale_unsupported_and_empty_evidence():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    claim = PlannedComparisonClaim(
        claim_id="claim_bad_comparison",
        claim_text="A comparison claim must stay inside the VOO and QQQ comparison pack.",
        citation_ids=["c_voo_bad", "c_qqq_ok"],
        required_asset_tickers=["VOO", "QQQ"],
    )
    qqq_ok = CitationEvidence(
        citation_id="c_qqq_ok",
        asset_ticker="QQQ",
        source_document_id="src_qqq_fact_sheet_fixture",
        source_type="issuer_fact_sheet",
        supporting_text="QQQ fixture describes Nasdaq-100 exposure.",
    )

    wrong_asset = validate_generated_comparison_claims(
        pack,
        [PlannedComparisonClaim(**{**claim.__dict__, "citation_ids": ["c_aapl_bad", "c_qqq_ok"]})],
        [
            CitationEvidence(
                citation_id="c_aapl_bad",
                asset_ticker="AAPL",
                source_document_id="src_aapl_10k_fixture",
                source_type="sec_filing",
                supporting_text="Apple 10-K fixture.",
            ),
            qqq_ok,
        ],
    )
    stale = validate_generated_comparison_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="c_voo_bad",
                asset_ticker="VOO",
                source_document_id="src_voo_stale",
                source_type="issuer_fact_sheet",
                freshness_state=FreshnessState.stale,
                supporting_text="Old VOO fact sheet fixture.",
            ),
            qqq_ok,
        ],
    )
    unsupported = validate_generated_comparison_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="c_voo_bad",
                asset_ticker="VOO",
                source_document_id="src_voo_news",
                source_type="news_article",
                supporting_text="Generic news fixture.",
            ),
            qqq_ok,
        ],
    )
    insufficient = validate_generated_comparison_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="c_voo_bad",
                asset_ticker="VOO",
                source_document_id="src_voo_empty",
                source_type="issuer_fact_sheet",
                supporting_text="",
            ),
            qqq_ok,
        ],
    )

    assert wrong_asset.status is CitationValidationStatus.wrong_asset
    assert stale.status is CitationValidationStatus.stale_source
    assert unsupported.status is CitationValidationStatus.unsupported_source
    assert insufficient.status is CitationValidationStatus.insufficient_evidence


def test_generated_comparison_copy_avoids_forbidden_advice_phrases():
    for pair in [("VOO", "QQQ"), ("QQQ", "VOO"), ("VOO", "BTC"), ("AAPL", "VOO")]:
        comparison = generate_comparison(*pair)
        assert find_forbidden_output_phrases(_flatten_text(comparison.model_dump(mode="json"))) == []


def test_comparison_generation_module_does_not_import_network_clients():
    comparison_source = (ROOT / "backend" / "comparison.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in comparison_source


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""


def _aapl_source_document() -> SourceDocument:
    return SourceDocument(
        source_document_id="src_aapl_10k_fixture",
        source_type="sec_filing",
        title="Apple Form 10-K fixture excerpt",
        publisher="U.S. SEC",
        url="https://www.sec.gov/",
        published_at="2025-11-01",
        as_of_date="2025-09-27",
        retrieved_at="2026-04-20T00:00:00Z",
        freshness_state=FreshnessState.fresh,
        is_official=True,
        supporting_passage="Apple 10-K fixture evidence.",
    )
