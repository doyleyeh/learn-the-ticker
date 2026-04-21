from pathlib import Path
from typing import Any

from backend.chat import (
    PlannedChatClaim,
    generate_asset_chat,
    validate_chat_response,
    validate_generated_chat_claims,
)
from backend.citations import CitationEvidence, CitationValidationStatus
from backend.models import AssetStatus, ChatResponse, FreshnessState, SafetyClassification
from backend.retrieval import build_asset_knowledge_pack
from backend.safety import find_forbidden_output_phrases


ROOT = Path(__file__).resolve().parents[2]


def test_supported_chat_intents_are_schema_valid_and_source_backed():
    cases = [
        ("QQQ", "What is this fund?", "Nasdaq-100 Index", "src_qqq_fact_sheet_fixture"),
        ("AAPL", "What does this company do?", "primary business", "src_aapl_10k_fixture"),
        ("VOO", "What does it hold?", "about 500", "src_voo_fact_sheet_fixture"),
        ("QQQ", "What is the biggest risk?", "concentration", "src_qqq_prospectus_fixture"),
        ("VOO", "What changed recently?", "No high-signal recent development", "src_voo_recent_review"),
        ("VOO", "Why do beginners consider it?", "Beginners may study VOO", "src_voo_fact_sheet_fixture"),
    ]

    for ticker, question, expected_text, expected_source in cases:
        pack = build_asset_knowledge_pack(ticker)
        response = generate_asset_chat(ticker, question)
        validated = ChatResponse.model_validate(response.model_dump(mode="json"))

        assert validated.asset.ticker == ticker
        assert validated.asset.status is AssetStatus.supported
        assert validated.safety_classification is SafetyClassification.educational
        assert expected_text in validated.direct_answer
        assert validated.why_it_matters
        assert validated.citations
        assert any(citation.source_document_id == expected_source for citation in validated.citations)
        assert validated.uncertainty
        assert validate_chat_response(validated, pack).valid


def test_supported_chat_unknown_evidence_does_not_invent_or_cite():
    pack = build_asset_knowledge_pack("AAPL")
    response = generate_asset_chat("AAPL", "Is Apple expensive based on valuation?")

    assert response.safety_classification is SafetyClassification.educational
    assert "Insufficient evidence" in response.direct_answer
    assert "valuation" in " ".join(response.uncertainty).lower()
    assert response.citations == []
    assert validate_chat_response(response, pack).valid


def test_chat_advice_and_unsupported_redirects_have_no_citations():
    advice = generate_asset_chat("VOO", "Should I buy VOO today?")
    unsupported = generate_asset_chat("BTC", "Should I buy BTC?")

    assert advice.safety_classification is SafetyClassification.personalized_advice_redirect
    assert unsupported.safety_classification is SafetyClassification.unsupported_asset_redirect
    assert advice.citations == []
    assert unsupported.citations == []
    assert "educational" in f"{advice.direct_answer} {advice.why_it_matters}".lower()
    assert "outside" in unsupported.direct_answer


def test_chat_response_validation_surfaces_missing_and_unknown_citations():
    pack = build_asset_knowledge_pack("QQQ")
    response = generate_asset_chat("QQQ", "What is this fund?")

    missing = response.model_copy(deep=True)
    missing.citations = []
    assert validate_chat_response(missing, pack).status is CitationValidationStatus.missing_citation

    nonexistent = response.model_copy(deep=True)
    nonexistent.citations[0].chunk_id = "chk_voo_profile_001"
    assert validate_chat_response(nonexistent, pack).status is CitationValidationStatus.citation_not_found


def test_generated_chat_claim_validation_rejects_wrong_stale_unsupported_and_empty_evidence():
    pack = build_asset_knowledge_pack("VOO")
    claim = PlannedChatClaim(
        claim_id="chat_bad_claim",
        claim_text="Chat citations must stay inside the selected asset knowledge pack.",
        citation_ids=["bad"],
        claim_type="factual",
    )

    wrong_asset = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="QQQ",
                source_document_id="src_qqq_fact_sheet_fixture",
                source_type="issuer_fact_sheet",
                supporting_text="QQQ fixture evidence.",
            )
        ],
    )
    stale = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="VOO",
                source_document_id="src_voo_old_fact_sheet",
                source_type="issuer_fact_sheet",
                freshness_state=FreshnessState.stale,
                supporting_text="Old VOO fixture evidence.",
            )
        ],
    )
    unsupported = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="VOO",
                source_document_id="src_voo_news",
                source_type="news_article",
                supporting_text="Generic news fixture evidence.",
            )
        ],
    )
    insufficient = validate_generated_chat_claims(
        pack,
        [claim],
        [
            CitationEvidence(
                citation_id="bad",
                asset_ticker="VOO",
                source_document_id="src_voo_fact_sheet_fixture",
                source_type="issuer_fact_sheet",
                supporting_text="",
            )
        ],
    )

    assert wrong_asset.status is CitationValidationStatus.wrong_asset
    assert stale.status is CitationValidationStatus.stale_source
    assert unsupported.status is CitationValidationStatus.unsupported_source
    assert insufficient.status is CitationValidationStatus.insufficient_evidence


def test_generated_chat_copy_avoids_forbidden_advice_phrases():
    cases = [
        ("VOO", "What is VOO?"),
        ("QQQ", "What risks should a beginner understand?"),
        ("AAPL", "What does Apple do?"),
        ("AAPL", "Is Apple expensive?"),
        ("VOO", "Should I buy VOO?"),
        ("BTC", "Should I buy BTC?"),
    ]

    for ticker, question in cases:
        response = generate_asset_chat(ticker, question)
        assert find_forbidden_output_phrases(_flatten_text(response.model_dump(mode="json"))) == []


def test_chat_generation_module_does_not_import_network_clients():
    chat_source = (ROOT / "backend" / "chat.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in chat_source


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""
