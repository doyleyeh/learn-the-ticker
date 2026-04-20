from pathlib import Path
import os
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = ROOT / "evals"

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")
sys.path.insert(0, str(ROOT))

from backend.citations import validate_claims
from backend.main import app
from backend.models import MetricValue
from backend.overview import generate_asset_overview, validate_overview_response
from backend.retrieval import build_asset_knowledge_pack, build_comparison_knowledge_pack, load_retrieval_fixture_dataset
from backend.safety import find_forbidden_output_phrases
from backend.testing import TestClient


client = TestClient(app)


def load_yaml(filename: str) -> dict:
    path = EVALS_DIR / filename
    assert path.exists(), f"Missing eval file: {filename}"
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{filename} must parse to a YAML object"
    return data


def test_golden_assets():
    data = load_yaml("golden_assets.yaml")
    assert "stocks" in data
    assert "etfs" in data
    assert len(data["stocks"]) >= 4
    assert len(data["etfs"]) >= 6


def test_safety_cases():
    data = load_yaml("safety_eval_cases.yaml")
    cases = data.get("cases", [])
    assert cases, "safety_eval_cases.yaml must define cases"

    required_behaviors = {
        "redirect_to_education",
        "no_personalized_allocation",
        "no_unsupported_price_target",
        "no_tax_advice",
        "no_brokerage_or_trading_execution",
        "no_future_return_certainty",
        "unsupported_asset_redirect",
        "educational_answer",
    }

    found = {case.get("expected_behavior") for case in cases}
    missing = required_behaviors - found
    assert not missing, f"Missing safety behaviors: {missing}"

    for case in cases:
        ticker = case.get("ticker", "VOO")
        response = client.post(f"/api/assets/{ticker}/chat", json={"question": case["user_input"]})
        assert response.status_code == 200, f"{case['id']} chat request failed"
        body = response.json()
        combined_output = " ".join(
            [
                body.get("direct_answer", ""),
                body.get("why_it_matters", ""),
                " ".join(body.get("uncertainty", [])),
            ]
        )
        normalized_output = " ".join(combined_output.lower().split())

        expected_classification = case.get("expected_safety_classification")
        assert body["safety_classification"] == expected_classification, (
            f"{case['id']} expected {expected_classification}, got {body['safety_classification']}"
        )

        if case.get("expected_citations") is True:
            assert body["citations"], f"{case['id']} should return grounded citations"
        elif case.get("expected_citations") is False:
            assert body["citations"] == [], f"{case['id']} should not return citations"

        for phrase in case.get("must_include", []):
            assert phrase.lower() in normalized_output, f"{case['id']} missing required output phrase: {phrase}"

        forbidden_hits = find_forbidden_output_phrases(combined_output)
        assert not forbidden_hits, f"{case['id']} leaked forbidden output phrases: {forbidden_hits}"

        for phrase in case.get("must_not_include", []):
            assert phrase.lower() not in normalized_output, f"{case['id']} leaked forbidden phrase: {phrase}"


def test_citation_cases():
    data = load_yaml("citation_eval_cases.yaml")
    cases = data.get("cases", [])
    assert cases, "citation_eval_cases.yaml must define cases"

    assert any(case.get("citation_required") for case in cases)
    assert any(case.get("expected_behavior") == "reject_wrong_asset_citation" for case in cases)

    validation_cases = [case for case in cases if "validation_claim" in case]
    assert validation_cases, "citation_eval_cases.yaml must include deterministic validation inputs"

    for case in validation_cases:
        expected_status = case.get("expected_status")
        assert expected_status, f"{case['id']} must define expected_status"
        report = validate_claims(
            claims=[case["validation_claim"]],
            evidence=case.get("evidence", []),
            context=case["context"],
        )
        assert report.status.value == expected_status, (
            f"{case['id']} expected {expected_status}, got {report.status.value}: "
            f"{[issue.message for issue in report.issues]}"
        )


def test_retrieval_fixture_contract():
    dataset = load_retrieval_fixture_dataset()
    assert dataset.no_live_external_calls is True

    required_tickers = {"AAPL", "VOO", "QQQ"}
    fixture_tickers = {fixture.asset.ticker for fixture in dataset.assets}
    assert required_tickers <= fixture_tickers

    all_gap_states = set()
    for ticker in required_tickers:
        pack = build_asset_knowledge_pack(ticker)
        assert pack.asset.supported is True
        assert pack.freshness.facts_as_of
        assert pack.freshness.recent_events_as_of
        assert pack.source_documents, f"{ticker} must include source document metadata"
        assert pack.source_chunks, f"{ticker} must include retrievable chunks"
        assert pack.normalized_facts, f"{ticker} must include normalized facts"
        assert pack.recent_developments, f"{ticker} must include a separate recent-development layer"

        returned_assets = {
            *{source.asset_ticker for source in pack.source_documents},
            *{chunk.chunk.asset_ticker for chunk in pack.source_chunks},
            *{fact.fact.asset_ticker for fact in pack.normalized_facts},
            *{fact.source_document.asset_ticker for fact in pack.normalized_facts},
            *{fact.source_chunk.asset_ticker for fact in pack.normalized_facts},
            *{recent.recent_development.asset_ticker for recent in pack.recent_developments},
            *{recent.source_document.asset_ticker for recent in pack.recent_developments},
        }
        assert returned_assets == {ticker}

        for fact in pack.normalized_facts:
            assert fact.source_document.source_document_id == fact.fact.source_document_id
            assert fact.source_chunk.chunk_id == fact.fact.source_chunk_id
            assert fact.source_document.retrieved_at

        all_gap_states.update(gap.evidence_state for gap in pack.evidence_gaps)

    comparison_pack = build_comparison_knowledge_pack("VOO", "QQQ")
    assert comparison_pack.computed_differences
    assert {source.asset_ticker for source in comparison_pack.comparison_sources} <= {"VOO", "QQQ"}

    all_gap_states.update(gap.evidence_state for gap in build_asset_knowledge_pack("BTC").evidence_gaps)
    assert {"missing", "stale", "unsupported", "insufficient"} <= all_gap_states

    retrieval_source = (ROOT / "backend" / "retrieval.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in retrieval_source


def test_generated_overview_contract():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)
        overview = generate_asset_overview(ticker)
        citation_ids = {citation.citation_id for citation in overview.citations}
        source_ids = {source.source_document_id for source in overview.source_documents}
        used_citation_ids = {
            *{citation_id for claim in overview.claims for citation_id in claim.citation_ids},
            *{citation_id for risk in overview.top_risks for citation_id in risk.citation_ids},
            *{citation_id for recent in overview.recent_developments for citation_id in recent.citation_ids},
            *{
                citation_id
                for value in overview.snapshot.values()
                if isinstance(value, MetricValue)
                for citation_id in value.citation_ids
            },
        }

        assert overview.asset.supported is True
        assert overview.beginner_summary is not None
        assert overview.beginner_summary.what_it_is
        assert overview.beginner_summary.why_people_consider_it
        assert overview.beginner_summary.main_catch
        assert len(overview.top_risks) == 3
        assert overview.freshness.facts_as_of
        assert overview.freshness.recent_events_as_of
        assert overview.recent_developments
        assert "No high-signal recent development" in overview.recent_developments[0].title
        assert overview.claims
        assert used_citation_ids <= citation_ids
        assert {citation.source_document_id for citation in overview.citations} <= source_ids
        assert validate_overview_response(overview, pack).valid

        combined_output = " ".join(
            [
                overview.beginner_summary.what_it_is,
                overview.beginner_summary.why_people_consider_it,
                overview.beginner_summary.main_catch,
                " ".join(risk.plain_english_explanation for risk in overview.top_risks),
                " ".join(recent.summary for recent in overview.recent_developments),
                overview.suitability_summary.may_fit if overview.suitability_summary else "",
                overview.suitability_summary.may_not_fit if overview.suitability_summary else "",
                overview.suitability_summary.learn_next if overview.suitability_summary else "",
            ]
        )
        assert not find_forbidden_output_phrases(combined_output)

    for ticker in ["BTC", "ZZZZ"]:
        overview = generate_asset_overview(ticker)
        assert overview.asset.supported is False
        assert overview.beginner_summary is None
        assert overview.claims == []
        assert overview.citations == []
        assert overview.source_documents == []

    overview_source = (ROOT / "backend" / "overview.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in overview_source


if __name__ == "__main__":
    test_golden_assets()
    test_safety_cases()
    test_citation_cases()
    test_retrieval_fixture_contract()
    test_generated_overview_contract()
    print("Static evals passed.")
