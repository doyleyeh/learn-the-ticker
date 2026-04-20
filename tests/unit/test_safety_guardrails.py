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


def test_backend_responses_do_not_leak_advice_phrases():
    response_payloads = []

    for ticker in ["VOO", "QQQ", "AAPL"]:
        response_payloads.append(client.get(f"/api/assets/{ticker}/overview").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/details").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/recent").json())

    response_payloads.append(client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json())

    chat_cases = [
        ("VOO", "What is VOO?"),
        ("VOO", "Should I buy VOO?"),
        ("AAPL", "Give me a price target for AAPL."),
        ("BTC", "Should I buy BTC?"),
    ]
    for ticker, question in chat_cases:
        response_payloads.append(client.post(f"/api/assets/{ticker}/chat", json={"question": question}).json())

    for index, payload in enumerate(response_payloads):
        assert_no_forbidden_phrases(f"backend response {index}", flatten_text(payload))


def test_frontend_copy_fixtures_and_comparison_do_not_leak_advice_phrases():
    paths = [
        "app/page.tsx",
        "app/assets/[ticker]/page.tsx",
        "app/compare/page.tsx",
        "components/AssetHeader.tsx",
        "components/CitationChip.tsx",
        "components/FreshnessLabel.tsx",
        "components/GlossaryPopover.tsx",
        "components/SearchBox.tsx",
        "components/SourceDrawer.tsx",
        "lib/fixtures.ts",
        "lib/glossary.ts",
    ]

    for path in paths:
        text = (ROOT / path).read_text(encoding="utf-8")
        assert_no_forbidden_phrases(path, text)
