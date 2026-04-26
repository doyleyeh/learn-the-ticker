import os
from pathlib import Path
from typing import Any

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.main import app
from backend.safety import find_forbidden_output_phrases
from backend.testing import TestClient


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "apps" / "web"
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

    for query in ["VOO", "BTC", "GME", "SPY", "ZZZZ"]:
        response_payloads.append(client.get("/api/search", params={"q": query}).json())

    for ticker in ["VOO", "QQQ", "AAPL"]:
        response_payloads.append(client.get(f"/api/assets/{ticker}/overview").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/details").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/recent").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/export").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/sources/export").json())
        response_payloads.append(client.get(f"/api/assets/{ticker}/glossary").json())

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
    response_payloads.append(client.get("/api/llm/runtime").json())

    chat_cases = [
        ("VOO", "What is VOO?"),
        ("VOO", "Should I buy VOO?"),
        ("VOO", "Should I buy VOO or QQQ?"),
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
        text = (WEB_ROOT / path).read_text(encoding="utf-8")
        assert_no_forbidden_phrases(path, text)


def test_chat_starter_prompt_copy_is_advice_safe():
    text = (WEB_ROOT / "components/AssetChatPanel.tsx").read_text(encoding="utf-8")
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
            (WEB_ROOT / "components/ExportControls.tsx").read_text(encoding="utf-8"),
            (WEB_ROOT / "lib/exportControls.ts").read_text(encoding="utf-8"),
            (WEB_ROOT / "app/assets/[ticker]/page.tsx").read_text(encoding="utf-8"),
            (WEB_ROOT / "app/compare/page.tsx").read_text(encoding="utf-8"),
            (WEB_ROOT / "components/AssetChatPanel.tsx").read_text(encoding="utf-8"),
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
            (WEB_ROOT / "components/ComparisonSuggestions.tsx").read_text(encoding="utf-8"),
            (WEB_ROOT / "lib/compareSuggestions.ts").read_text(encoding="utf-8"),
            (WEB_ROOT / "app/assets/[ticker]/page.tsx").read_text(encoding="utf-8"),
            (WEB_ROOT / "app/compare/page.tsx").read_text(encoding="utf-8"),
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


def test_llm_contract_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "llm.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "models.py").read_text(encoding="utf-8"),
        ]
    )
    markers = [
        "llm-runtime-contract-v1",
        "deterministic_mock",
        "gated_live",
        "reasoning_summary",
        "validation_failed_after_repair",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("llm contract", combined)


def test_chat_session_contract_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "chat_sessions.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "models.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "export.py").read_text(encoding="utf-8"),
        ]
    )
    markers = [
        "chat-session-contract-v1",
        "CHAT_SESSION_TTL_SECONDS",
        "ticker_mismatch",
        "deleted",
        "local_accountless_chat_session",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("chat session contract", combined)


def test_glossary_asset_context_contract_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "glossary.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "models.py").read_text(encoding="utf-8"),
        ]
    )
    markers = [
        "glossary-asset-context-v1",
        "generic_definitions_are_not_evidence",
        "no_new_generated_output",
        "same_asset_evidence_only",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("glossary asset context contract", combined)


def test_etf_universe_manifest_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "etf_universe.py").read_text(encoding="utf-8"),
            (ROOT / "data" / "universes" / "us_equity_etfs.current.json").read_text(encoding="utf-8"),
        ]
    )
    markers = [
        "us-equity-etf-universe-v1",
        "eligible_not_cached",
        "recognized_unsupported",
        "out_of_scope",
        "unavailable",
        "generated outputs remain blocked",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("ETF universe manifest contract", combined)


def test_search_blocked_explanation_contract_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "search.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "models.py").read_text(encoding="utf-8"),
        ]
    )
    markers = [
        "search-blocked-explanation-v1",
        "scope_blocked_search_result",
        "top500_manifest_scope",
        "Supported MVP coverage is limited to U.S.-listed common stocks",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("search blocked explanation contract", combined)


def test_weekly_news_event_evidence_contract_copy_is_advice_safe():
    combined = "\n".join(
        [
            (ROOT / "backend" / "repositories" / "weekly_news.py").read_text(encoding="utf-8"),
            (ROOT / "backend" / "weekly_news_repository.py").read_text(encoding="utf-8"),
            (ROOT / "alembic" / "versions" / "20260425_0008_weekly_news_event_evidence_contracts.py").read_text(
                encoding="utf-8"
            ),
        ]
    )
    markers = [
        "weekly-news-event-evidence-repository-contract-v1",
        "persisted_evidence_only",
        "threshold_metadata_only",
        "source_policy_blocked",
        "stable_facts_are_separate",
    ]

    for marker in markers:
        assert marker in combined
        assert_no_forbidden_phrases(marker, marker)

    assert_no_forbidden_phrases("weekly news event evidence contract", combined)


def test_backend_runtime_gap_audit_copy_is_advice_safe_and_sanitized():
    text = (ROOT / "docs" / "backend_mvp_runtime_gap_audit.md").read_text(encoding="utf-8")

    markers = [
        "Backend MVP Runtime Gap Audit",
        "runtime_gap",
        "T-101 route read-path wiring",
        "T-102 executable ingestion jobs",
        "T-103 SEC golden-path acquisition",
        "T-104 ETF issuer golden-path acquisition",
        "Weekly News Focus showing only the evidence-backed set",
        "Normal CI remains deterministic",
    ]

    for marker in markers:
        assert marker in text
        assert_no_forbidden_phrases(marker, marker)

    for forbidden in [
        "OPENROUTER_API_KEY",
        "FMP_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "FINNHUB_API_KEY",
        "TIINGO_API_KEY",
        "EODHD_API_KEY",
        "BEGIN PRIVATE KEY",
        "Authorization",
        "Bearer ",
        "signed URL",
        "public storage URL",
        "raw transcript",
    ]:
        assert forbidden not in text

    assert_no_forbidden_phrases("backend runtime gap audit", text)
