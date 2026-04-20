from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = ROOT / "evals"


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
    }

    found = {case.get("expected_behavior") for case in cases}
    missing = required_behaviors - found
    assert not missing, f"Missing safety behaviors: {missing}"


def test_citation_cases():
    data = load_yaml("citation_eval_cases.yaml")
    cases = data.get("cases", [])
    assert cases, "citation_eval_cases.yaml must define cases"

    assert any(case.get("citation_required") for case in cases)
    assert any(case.get("expected_behavior") == "reject_wrong_asset_citation" for case in cases)


if __name__ == "__main__":
    test_golden_assets()
    test_safety_cases()
    test_citation_cases()
    print("Static evals passed.")