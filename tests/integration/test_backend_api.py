import os

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.main import app
from backend.safety import find_forbidden_output_phrases
from backend.testing import TestClient


client = TestClient(app)


def test_health_endpoint_available():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_supported_asset_schema():
    response = client.get("/api/search?q=VOO")

    assert response.status_code == 200
    body = response.json()
    assert body["state"]["status"] == "supported"
    assert body["results"][0]["ticker"] == "VOO"
    assert body["results"][0]["asset_type"] == "etf"
    assert body["results"][0]["supported"] is True


def test_overview_has_beginner_sections_and_citations():
    response = client.get("/api/assets/VOO/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["asset"]["ticker"] == "VOO"
    assert body["freshness"]["freshness_state"] == "fresh"
    assert body["beginner_summary"]["what_it_is"]
    assert len(body["top_risks"]) == 3
    citation_ids = {citation["citation_id"] for citation in body["citations"]}
    source_ids = {source["source_document_id"] for source in body["source_documents"]}
    assert body["claims"][0]["citation_ids"][0] in citation_ids
    assert body["top_risks"][0]["citation_ids"][0] in citation_ids
    assert body["recent_developments"][0]["citation_ids"][0] in citation_ids
    assert "src_voo_fact_sheet_fixture" in source_ids
    assert "src_voo_recent_review" in source_ids


def test_details_sources_and_recent_routes_exist():
    details = client.get("/api/assets/AAPL/details")
    sources = client.get("/api/assets/AAPL/sources")
    recent = client.get("/api/assets/AAPL/recent")

    assert details.status_code == 200
    assert sources.status_code == 200
    assert recent.status_code == 200
    assert details.json()["facts"]["business_model"]
    assert sources.json()["sources"][0]["source_document_id"] == "src_aapl_10k_fixture"
    assert sources.json()["sources"][0]["publisher"] == "U.S. SEC"
    assert recent.json()["recent_developments"][0]["freshness_state"] == "fresh"


def test_unknown_and_unsupported_assets_return_clear_states():
    unknown = client.get("/api/assets/ZZZZ/overview").json()
    unsupported = client.get("/api/search", params={"q": "BTC"}).json()

    assert unknown["state"]["status"] == "unknown"
    assert unknown["asset"]["supported"] is False
    assert unknown["beginner_summary"] is None
    assert unsupported["state"]["status"] == "unsupported"
    assert unsupported["results"][0]["supported"] is False
    assert "outside" in unsupported["state"]["message"]


def test_compare_route_returns_educational_shape():
    response = client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"})

    assert response.status_code == 200
    body = response.json()
    assert body["comparison_type"] == "etf_vs_etf"
    assert body["bottom_line_for_beginners"]["summary"]
    assert body["key_differences"][0]["citation_ids"]
    assert body["state"]["status"] == "supported"
    assert {item["dimension"] for item in body["key_differences"]} >= {
        "Benchmark",
        "Expense ratio",
        "Holdings count",
        "Breadth",
        "Educational role",
    }


def test_compare_route_uses_fixture_pipeline_in_reverse_order_and_unavailable_states():
    reverse = client.post("/api/compare", json={"left_ticker": "QQQ", "right_ticker": "VOO"}).json()
    unsupported = client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "BTC"}).json()

    assert reverse["left_asset"]["ticker"] == "QQQ"
    assert reverse["right_asset"]["ticker"] == "VOO"
    assert reverse["comparison_type"] == "etf_vs_etf"
    assert reverse["key_differences"][0]["plain_english_summary"].startswith("QQQ tracks")
    assert unsupported["state"]["status"] == "unsupported"
    assert unsupported["comparison_type"] == "unavailable"
    assert unsupported["key_differences"] == []
    assert unsupported["bottom_line_for_beginners"] is None
    assert unsupported["citations"] == []


def test_chat_advice_like_question_redirects_to_education():
    response = client.post("/api/assets/VOO/chat", json={"question": "Should I buy VOO today?"})

    assert response.status_code == 200
    body = response.json()
    combined = f"{body['direct_answer']} {body['why_it_matters']}".lower()
    assert body["safety_classification"] == "personalized_advice_redirect"
    assert "educational" in combined
    assert "you should buy" not in combined
    assert "price target" not in combined
    assert body["citations"] == []
    assert body["source_documents"] == []


def test_chat_advice_like_questions_redirect_without_citations():
    cases = [
        ("VOO", "How much of my portfolio should I put in VOO?"),
        ("AAPL", "Give me a price target for AAPL."),
        ("VOO", "Is VOO right for my taxes this year?"),
        ("QQQ", "Which brokerage should I use and how do I place a trade for QQQ?"),
        ("QQQ", "Will QQQ definitely outperform next year?"),
        ("AAPL", "Should I sell or hold AAPL this week?"),
    ]

    for ticker, question in cases:
        response = client.post(f"/api/assets/{ticker}/chat", json={"question": question})

        assert response.status_code == 200
        body = response.json()
        combined = f"{body['direct_answer']} {body['why_it_matters']} {' '.join(body['uncertainty'])}"
        assert body["safety_classification"] == "personalized_advice_redirect"
        assert "educational" in combined.lower()
        assert body["citations"] == []
        assert body["source_documents"] == []
        assert find_forbidden_output_phrases(combined) == []


def test_chat_supported_question_is_grounded_with_citation():
    response = client.post("/api/assets/QQQ/chat", json={"question": "What is this fund?"})

    assert response.status_code == 200
    body = response.json()
    assert body["safety_classification"] == "educational"
    assert "Nasdaq-100 Index" in body["direct_answer"]
    assert body["citations"][0]["source_document_id"] == "src_qqq_fact_sheet_fixture"
    assert body["source_documents"]
    source = body["source_documents"][0]
    assert source["citation_id"] == body["citations"][0]["citation_id"]
    assert source["source_document_id"] == body["citations"][0]["source_document_id"]
    assert source["chunk_id"] == body["citations"][0]["chunk_id"]
    assert source["title"]
    assert source["source_type"] == "issuer_fact_sheet"
    assert source["published_at"] or source["as_of_date"]
    assert source["retrieved_at"]
    assert source["url"]
    assert source["freshness_state"] == "fresh"
    assert source["supporting_passage"]
    assert body["uncertainty"]


def test_chat_supported_beginner_intents_use_selected_asset_pack():
    cases = [
        ("AAPL", "What does Apple do?", "primary business", "src_aapl_10k_fixture"),
        ("VOO", "What does VOO hold?", "about 500", "src_voo_fact_sheet_fixture"),
        ("QQQ", "What is the biggest risk?", "concentration", "src_qqq_prospectus_fixture"),
        ("VOO", "What changed recently?", "No high-signal recent development", "src_voo_recent_review"),
        ("AAPL", "Is Apple expensive based on valuation?", "Insufficient evidence", None),
    ]

    for ticker, question, expected_answer, expected_source in cases:
        response = client.post(f"/api/assets/{ticker}/chat", json={"question": question})

        assert response.status_code == 200
        body = response.json()
        assert body["asset"]["ticker"] == ticker
        assert body["safety_classification"] == "educational"
        assert expected_answer in body["direct_answer"]
        if expected_source is None:
            assert body["citations"] == []
            assert body["source_documents"] == []
            assert "valuation" in " ".join(body["uncertainty"]).lower()
        else:
            assert body["citations"]
            assert body["source_documents"]
            assert expected_source in {citation["source_document_id"] for citation in body["citations"]}
            assert expected_source in {source["source_document_id"] for source in body["source_documents"]}


def test_chat_unsupported_assets_redirect_to_scope_language():
    cases = [
        ("DOGE", "What is this?", "local skeleton data"),
        ("BTC", "Should I buy BTC?", "Crypto assets are outside"),
        ("TQQQ", "What should I do with TQQQ?", "Leveraged ETFs are outside"),
        ("SQQQ", "Should I hold SQQQ?", "Inverse ETFs are outside"),
    ]

    for ticker, question, expected_phrase in cases:
        response = client.post(f"/api/assets/{ticker}/chat", json={"question": question})

        assert response.status_code == 200
        body = response.json()
        combined = f"{body['direct_answer']} {body['why_it_matters']} {' '.join(body['uncertainty'])}"
        assert body["safety_classification"] == "unsupported_asset_redirect"
        assert expected_phrase in combined
        assert body["citations"] == []
        assert body["source_documents"] == []
        assert body["uncertainty"]
        assert find_forbidden_output_phrases(combined) == []
