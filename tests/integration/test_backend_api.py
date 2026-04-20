import os

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.main import app
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
    assert body["claims"][0]["citation_ids"] == ["c_voo_profile"]
    assert body["citations"][0]["citation_id"] == "c_voo_profile"
    assert body["source_documents"][0]["source_document_id"] == "src_voo_fact_sheet"


def test_details_sources_and_recent_routes_exist():
    details = client.get("/api/assets/AAPL/details")
    sources = client.get("/api/assets/AAPL/sources")
    recent = client.get("/api/assets/AAPL/recent")

    assert details.status_code == 200
    assert sources.status_code == 200
    assert recent.status_code == 200
    assert details.json()["facts"]["business_model"]
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


def test_chat_supported_question_is_grounded_with_citation():
    response = client.post("/api/assets/QQQ/chat", json={"question": "What is this fund?"})

    assert response.status_code == 200
    body = response.json()
    assert body["safety_classification"] == "educational"
    assert body["citations"][0]["source_document_id"] == "src_qqq_fact_sheet"
    assert body["uncertainty"]


def test_chat_unknown_asset_redirects():
    response = client.post("/api/assets/DOGE/chat", json={"question": "What is this?"})

    assert response.status_code == 200
    body = response.json()
    assert body["safety_classification"] == "unsupported_asset_redirect"
    assert body["citations"] == []
    assert body["uncertainty"]
