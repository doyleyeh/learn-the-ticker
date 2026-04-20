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


if __name__ == "__main__":
    test_golden_assets()
    test_safety_cases()
    test_citation_cases()
    print("Static evals passed.")
