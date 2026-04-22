import os
from pathlib import Path
from typing import Any

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.main import app
from backend.safety import find_forbidden_output_phrases
from backend.testing import TestClient


ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(flatten_text(item) for item in value.values())
    return ""


def assert_no_forbidden_phrases(label: str, text: str) -> None:
    hits = find_forbidden_output_phrases(text)
    assert hits == [], f"{label} leaked forbidden phrases: {hits}"


def test_forbidden_output_phrase_detector_rejects_advice_like_copy():
    forbidden_examples = [
        "You should buy VOO.",
        "Allocate 20% to QQQ.",
        "The price target is $100.",
        "Open a brokerage account.",
    ]

    for example in forbidden_examples:
        assert find_forbidden_output_phrases(example), f"Expected forbidden phrase hit for: {example}"


def test_backend_responses_do_not_leak_advice_phrases():
    response_payloads = []

    for ticker in ["VOO", "QQQ", "AAPL"]:
        response_payloads.append(client.get(f"/api/assets/{ticker}/overview").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/details").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/recent").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/export").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/sources/export").json())

    response_payloads.append(client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json())
    response_payloads.append(
        client.post("/api/compare/export", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json()
    )
    response_payloads.append(client.get("/api/trust-metrics/catalog").json())
    response_payloads.append(
        client.post(
            "/api/trust-metrics/validate",
            json={
                "events": [
                    {
                        "event_type": "chat_safety_redirect",
                        "workflow_area": "chat",
                        "asset_ticker": "VOO",
                        "metadata": {"safety_classification": "personalized_advice_redirect"},
                    }
                ]
            },
        ).json()
    )

    chat_cases = [
        ("VOO", "What is VOO?"),
        ("VOO", "Should I buy VOO?"),
        ("AAPL", "Give me a price target for AAPL."),
        ("BTC", "Should I buy BTC?"),
    ]
    for ticker, question in chat_cases:
        response_payloads.append(client.post(f"/api/assets/{ticker}/chat", json={"question": question}).json())
        response_payloads.append(client.post(f"/api/assets/{ticker}/chat/export", json={"question": question}).json())

    for index, payload in enumerate(response_payloads):
        assert_no_forbidden_phrases(f"backend response {index}", flatten_text(payload))


def test_frontend_copy_fixtures_and_comparison_do_not_leak_advice_phrases():
    paths = [
        "app/page.tsx",
        "app/assets/[ticker]/page.tsx",
        "app/compare/page.tsx",
        "components/AssetHeader.tsx",
        "components/AssetChatPanel.tsx",
        "components/AssetEtfSections.tsx",
        "components/AssetStockSections.tsx",
        "components/AssetModeLayout.tsx",
        "components/CitationChip.tsx",
        "components/ComparisonSuggestions.tsx",
        "components/ComparisonSourceDetails.tsx",
        "components/ExportControls.tsx",
        "components/FreshnessLabel.tsx",
        "components/GlossaryPopover.tsx",
        "components/SearchBox.tsx",
        "components/SourceDrawer.tsx",
        "lib/assetChat.ts",
        "lib/compare.ts",
        "lib/compareSuggestions.ts",
        "lib/exportControls.ts",
        "lib/fixtures.ts",
        "lib/glossary.ts",
    ]

    for path in paths:
        text = (ROOT / path).read_text(encoding="utf-8")
        assert_no_forbidden_phrases(path, text)


def test_chat_starter_prompt_copy_is_advice_safe():
    text = (ROOT / "components/AssetChatPanel.tsx").read_text(encoding="utf-8")
    prompt_copy_markers = [
        "What is ${normalizedTicker} in plain English?",
        "business model work?",
        "fund exposure",
        "What top risk should a beginner understand",
        "What changed recently",
        "without a personal recommendation",
    ]

    for marker in prompt_copy_markers:
        assert marker in text
        assert_no_forbidden_phrases(marker, marker)


def test_frontend_export_control_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "components/ExportControls.tsx").read_text(encoding="utf-8"),
            (ROOT / "lib/exportControls.ts").read_text(encoding="utf-8"),
            (ROOT / "app/assets/[ticker]/page.tsx").read_text(encoding="utf-8"),
            (ROOT / "app/compare/page.tsx").read_text(encoding="utf-8"),
            (ROOT / "components/AssetChatPanel.tsx").read_text(encoding="utf-8"),
        ]
    )
    export_copy_markers = [
        "citation IDs",
        "source metadata",
        "freshness/as-of dates",
        "educational disclaimer",
        "licensing scope",
        "full source documents",
        "restricted provider payloads",
        "live external download URLs",
        "Export controls stay unavailable",
        "Save chat transcript",
    ]

    for marker in export_copy_markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("frontend export controls", combined)


def test_frontend_comparison_suggestion_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "components/ComparisonSuggestions.tsx").read_text(encoding="utf-8"),
            (ROOT / "lib/compareSuggestions.ts").read_text(encoding="utf-8"),
            (ROOT / "app/assets/[ticker]/page.tsx").read_text(encoding="utf-8"),
            (ROOT / "app/compare/page.tsx").read_text(encoding="utf-8"),
        ]
    )
    suggestion_copy_markers = [
        "local source-backed comparison",
        "benchmark, cost, holdings breadth, and beginner role",
        "No local source-backed comparison pack",
        "peer list, citation chips, source documents",
        "not facts about the requested pair",
        "this is not personal advice",
    ]

    for marker in suggestion_copy_markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("frontend comparison suggestions", combined)


def test_trust_metrics_contract_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "trust_metrics.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "models.py").read_text(encoding="utf-8"),
        ]
    )
    markers = [
        "trust-metrics-event-v1",
        "validation_only",
        "external_analytics_enabled",
        "chat_safety_redirect",
        "generated_output_validation_failure",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("trust metrics contract", combined)
