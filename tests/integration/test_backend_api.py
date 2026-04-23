import os

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.main import app
from backend.safety import find_forbidden_output_phrases
from backend.testing import TestClient


client = TestClient(app)


def _without_session(payload: dict) -> dict:
    stripped = dict(payload)
    stripped.pop("session", None)
    return stripped


def test_health_endpoint_available():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_supported_asset_schema():
    response = client.get("/api/search?q=VOO")

    assert response.status_code == 200
    body = response.json()
    assert body["state"]["status"] == "supported"
    assert body["state"]["support_classification"] == "cached_supported"
    assert body["state"]["can_open_generated_page"] is True
    assert body["state"]["generated_route"] == "/assets/VOO"
    assert body["state"]["can_request_ingestion"] is False
    assert body["state"]["ingestion_request_route"] is None
    assert body["results"][0]["ticker"] == "VOO"
    assert body["results"][0]["asset_type"] == "etf"
    assert body["results"][0]["supported"] is True
    assert body["results"][0]["support_classification"] == "cached_supported"
    assert body["results"][0]["can_open_generated_page"] is True
    assert body["results"][0]["can_answer_chat"] is True
    assert body["results"][0]["can_compare"] is True
    assert body["results"][0]["generated_route"] == "/assets/VOO"
    assert body["results"][0]["can_request_ingestion"] is False
    assert body["results"][0]["ingestion_request_route"] is None


def test_search_classification_states_cover_ambiguous_unknown_and_ingestion_needed():
    ambiguous = client.get("/api/search", params={"q": "S&P 500 ETF"}).json()
    unknown = client.get("/api/search", params={"q": "ZZZZ"}).json()
    out_of_scope = client.get("/api/search", params={"q": "GME"}).json()
    ingestion_needed = client.get("/api/search", params={"q": "SPY"}).json()
    launch_stock = client.get("/api/search", params={"q": "BRK.B"}).json()
    launch_etf = client.get("/api/search", params={"q": "SOXX"}).json()

    assert ambiguous["state"]["status"] == "ambiguous"
    assert ambiguous["state"]["requires_disambiguation"] is True
    assert ambiguous["state"]["can_open_generated_page"] is False
    assert ambiguous["state"]["can_request_ingestion"] is False
    assert {result["ticker"] for result in ambiguous["results"]} >= {"VOO", "SPY"}
    assert "eligible_not_cached" in {result["support_classification"] for result in ambiguous["results"]}
    spy_result = next(result for result in ambiguous["results"] if result["ticker"] == "SPY")
    assert spy_result["can_request_ingestion"] is True
    assert spy_result["ingestion_request_route"] == "/api/admin/ingest/SPY"

    assert unknown["state"]["status"] == "unknown"
    assert unknown["state"]["support_classification"] == "unknown"
    assert unknown["results"][0]["asset_type"] == "unknown"
    assert unknown["results"][0]["generated_route"] is None
    assert unknown["results"][0]["can_open_generated_page"] is False
    assert unknown["results"][0]["can_request_ingestion"] is False

    assert out_of_scope["state"]["status"] == "out_of_scope"
    assert out_of_scope["state"]["support_classification"] == "out_of_scope"
    assert out_of_scope["results"][0]["ticker"] == "GME"
    assert out_of_scope["results"][0]["asset_type"] == "stock"
    assert out_of_scope["results"][0]["generated_route"] is None
    assert out_of_scope["results"][0]["eligible_for_ingestion"] is False
    assert out_of_scope["results"][0]["can_open_generated_page"] is False
    assert out_of_scope["results"][0]["can_request_ingestion"] is False

    assert ingestion_needed["state"]["status"] == "ingestion_needed"
    assert ingestion_needed["state"]["support_classification"] == "eligible_not_cached"
    assert ingestion_needed["state"]["requires_ingestion"] is True
    assert ingestion_needed["state"]["can_request_ingestion"] is True
    assert ingestion_needed["state"]["ingestion_request_route"] == "/api/admin/ingest/SPY"
    assert ingestion_needed["results"][0]["ticker"] == "SPY"
    assert ingestion_needed["results"][0]["eligible_for_ingestion"] is True
    assert ingestion_needed["results"][0]["requires_ingestion"] is True
    assert ingestion_needed["results"][0]["can_open_generated_page"] is False
    assert ingestion_needed["results"][0]["can_answer_chat"] is False
    assert ingestion_needed["results"][0]["can_compare"] is False
    assert ingestion_needed["results"][0]["can_request_ingestion"] is True
    assert ingestion_needed["results"][0]["ingestion_request_route"] == "/api/admin/ingest/SPY"

    for body, expected_ticker, expected_type in [(launch_stock, "BRK.B", "stock"), (launch_etf, "SOXX", "etf")]:
        assert body["state"]["status"] == "ingestion_needed"
        assert body["state"]["support_classification"] == "eligible_not_cached"
        assert body["results"][0]["ticker"] == expected_ticker
        assert body["results"][0]["asset_type"] == expected_type
        assert body["results"][0]["generated_route"] is None
        assert body["results"][0]["can_answer_chat"] is False
        assert body["results"][0]["can_compare"] is False


def test_ingestion_request_route_returns_deterministic_job_or_non_job_states():
    eligible = client.post("/api/admin/ingest/SPY").json()
    eligible_again = client.post("/api/admin/ingest/spy").json()
    eligible_launch = client.post("/api/admin/ingest/SOXX").json()
    cached = client.post("/api/admin/ingest/VOO").json()
    unsupported = client.post("/api/admin/ingest/TQQQ").json()
    out_of_scope = client.post("/api/admin/ingest/GME").json()
    unknown = client.post("/api/admin/ingest/ZZZZ").json()

    assert eligible == eligible_again
    assert eligible["ticker"] == "SPY"
    assert eligible["asset_type"] == "etf"
    assert eligible["job_type"] == "on_demand"
    assert eligible["job_id"] == "ingest-on-demand-spy"
    assert eligible["job_state"] == "pending"
    assert eligible["worker_status"] == "queued"
    assert eligible["status_url"] == "/api/jobs/ingest-on-demand-spy"
    assert eligible["generated_route"] is None
    assert eligible["capabilities"]["can_open_generated_page"] is False
    assert eligible["capabilities"]["can_answer_chat"] is False
    assert eligible["capabilities"]["can_compare"] is False

    assert eligible_launch["ticker"] == "SOXX"
    assert eligible_launch["asset_type"] == "etf"
    assert eligible_launch["job_id"] == "ingest-on-demand-soxx"
    assert eligible_launch["status_url"] == "/api/jobs/ingest-on-demand-soxx"
    assert eligible_launch["generated_route"] is None
    assert eligible_launch["capabilities"]["can_open_generated_page"] is False

    assert cached["ticker"] == "VOO"
    assert cached["job_id"] is None
    assert cached["job_state"] == "no_ingestion_needed"
    assert cached["generated_route"] == "/assets/VOO"
    assert cached["capabilities"]["can_open_generated_page"] is True
    assert cached["capabilities"]["can_answer_chat"] is True
    assert cached["capabilities"]["can_compare"] is True

    assert unsupported["ticker"] == "TQQQ"
    assert unsupported["job_id"] is None
    assert unsupported["job_state"] == "unsupported"
    assert unsupported["generated_route"] is None
    assert unsupported["capabilities"]["can_open_generated_page"] is False
    assert unsupported["capabilities"]["can_answer_chat"] is False
    assert unsupported["capabilities"]["can_compare"] is False

    assert out_of_scope["ticker"] == "GME"
    assert out_of_scope["asset_type"] == "stock"
    assert out_of_scope["job_id"] is None
    assert out_of_scope["job_state"] == "out_of_scope"
    assert out_of_scope["generated_route"] is None
    assert out_of_scope["capabilities"]["can_open_generated_page"] is False
    assert out_of_scope["capabilities"]["can_answer_chat"] is False
    assert out_of_scope["capabilities"]["can_compare"] is False
    assert out_of_scope["capabilities"]["can_request_ingestion"] is False

    assert unknown["ticker"] == "ZZZZ"
    assert unknown["asset_type"] == "unknown"
    assert unknown["job_id"] is None
    assert unknown["job_state"] == "unknown"
    assert unknown["generated_route"] is None
    assert "no asset facts are invented" in unknown["message"].lower()


def test_ingestion_status_route_returns_fixture_backed_states():
    queued = client.get("/api/jobs/ingest-on-demand-spy").json()
    running = client.get("/api/jobs/ingest-on-demand-msft").json()
    succeeded = client.get("/api/jobs/pre-cache-succeeded-voo").json()
    refresh_needed = client.get("/api/jobs/refresh-needed-aapl").json()
    failed = client.get("/api/jobs/ingest-on-demand-msft-failed").json()
    missing = client.get("/api/jobs/missing-job").json()

    assert queued["job_state"] == "pending"
    assert queued["worker_status"] == "queued"
    assert running["job_state"] == "running"
    assert running["worker_status"] == "running"
    assert succeeded["job_state"] == "succeeded"
    assert succeeded["generated_route"] == "/assets/VOO"
    assert refresh_needed["job_state"] == "refresh_needed"
    assert refresh_needed["retryable"] is True
    assert failed["job_state"] == "failed"
    assert failed["worker_status"] == "failed"
    assert failed["error_metadata"]["code"] == "fixture_ingestion_failed"
    assert failed["error_metadata"]["retryable"] is True
    assert missing["job_state"] == "unavailable"
    assert missing["asset_type"] == "unknown"


def test_launch_universe_pre_cache_routes_return_same_deterministic_contract():
    requested = client.post("/api/admin/pre-cache/launch-universe")
    inspected = client.get("/api/admin/pre-cache/launch-universe")

    assert requested.status_code == 200
    assert inspected.status_code == 200
    assert requested.json() == inspected.json()

    body = requested.json()
    jobs_by_ticker = {job["ticker"]: job for job in body["jobs"]}
    assert body["batch_id"] == "pre-cache-launch-universe-v1"
    assert body["summary"]["total_launch_assets"] == len(body["jobs"])
    assert body["summary"]["cached_or_already_available_assets"] == 3
    assert body["summary"]["generated_output_available_assets"] == 3
    assert {"AAPL", "VOO", "QQQ", "SPY", "MSFT", "AMZN", "NVDA"} <= set(jobs_by_ticker)
    assert jobs_by_ticker["VOO"]["job_state"] == "succeeded"
    assert jobs_by_ticker["VOO"]["generated_route"] == "/assets/VOO"
    assert jobs_by_ticker["SPY"]["job_state"] == "pending"
    assert jobs_by_ticker["SPY"]["generated_route"] is None
    assert jobs_by_ticker["MSFT"]["job_state"] == "running"
    assert jobs_by_ticker["AMZN"]["job_state"] == "failed"

    for ticker, job in jobs_by_ticker.items():
        if ticker not in {"AAPL", "VOO", "QQQ"}:
            assert job["generated_route"] is None
            assert job["generated_output_available"] is False
            assert job["citation_ids"] == []
            assert job["source_document_ids"] == []
            assert job["capabilities"]["can_open_generated_page"] is False
            assert job["capabilities"]["can_answer_chat"] is False
            assert job["capabilities"]["can_compare"] is False


def test_pre_cache_asset_and_status_routes_cover_non_generated_states():
    cached = client.post("/api/admin/pre-cache/AAPL").json()
    queued_etf = client.get("/api/admin/pre-cache/jobs/pre-cache-launch-spy").json()
    queued_stock = client.get("/api/admin/pre-cache/jobs/pre-cache-launch-nvda").json()
    running = client.get("/api/admin/pre-cache/jobs/pre-cache-launch-msft").json()
    failed = client.get("/api/admin/pre-cache/jobs/pre-cache-launch-amzn").json()
    unsupported = client.post("/api/admin/pre-cache/TQQQ").json()
    unsupported_status = client.get("/api/admin/pre-cache/jobs/pre-cache-unsupported-tqqq").json()
    out_of_scope = client.post("/api/admin/pre-cache/GME").json()
    out_of_scope_status = client.get("/api/admin/pre-cache/jobs/pre-cache-out-of-scope-gme").json()
    unknown = client.post("/api/admin/pre-cache/ZZZZ").json()
    unknown_status = client.get("/api/admin/pre-cache/jobs/pre-cache-unknown-zzzz").json()
    missing = client.get("/api/admin/pre-cache/jobs/missing-pre-cache-job").json()

    assert cached["job_state"] == "succeeded"
    assert cached["generated_route"] == "/assets/AAPL"
    assert cached["generated_output_available"] is True
    assert queued_etf["ticker"] == "SPY"
    assert queued_etf["job_state"] == "pending"
    assert queued_stock["ticker"] == "NVDA"
    assert queued_stock["job_state"] == "pending"
    assert running["job_state"] == "running"
    assert failed["job_state"] == "failed"
    assert failed["error_metadata"]["code"] == "fixture_pre_cache_failed"
    assert unsupported == unsupported_status
    assert unsupported["asset_type"] == "unsupported"
    assert unsupported["job_state"] == "unsupported"
    assert out_of_scope == out_of_scope_status
    assert out_of_scope["asset_type"] == "stock"
    assert out_of_scope["job_state"] == "out_of_scope"
    assert unknown == unknown_status
    assert unknown["asset_type"] == "unknown"
    assert unknown["job_state"] == "unknown"
    assert missing["job_state"] == "unavailable"
    assert missing["generated_route"] is None

    for body in [queued_etf, queued_stock, running, failed, unsupported, out_of_scope, unknown, missing]:
        assert body["generated_route"] is None
        assert body["generated_output_available"] is False
        assert body["citation_ids"] == []
        assert body["source_document_ids"] == []
        assert body["capabilities"]["can_open_generated_page"] is False
        assert body["capabilities"]["can_answer_chat"] is False
        assert body["capabilities"]["can_compare"] is False


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
    assert body["weekly_news_focus"]["schema_version"] == "weekly-news-focus-v1"
    assert body["weekly_news_focus"]["window"]["news_window_start"] == "2026-04-13"
    assert body["weekly_news_focus"]["window"]["news_window_end"] == "2026-04-22"
    assert body["weekly_news_focus"]["items"] == []
    assert body["weekly_news_focus"]["empty_state"]["evidence_state"] == "no_high_signal"
    assert body["ai_comprehensive_analysis"]["schema_version"] == "ai-comprehensive-analysis-v1"
    assert body["ai_comprehensive_analysis"]["analysis_available"] is False
    assert body["ai_comprehensive_analysis"]["sections"] == []
    assert "src_voo_fact_sheet_fixture" in source_ids
    assert "src_voo_recent_review" in source_ids
    sections = {section["section_id"]: section for section in body["sections"]}
    assert {
        "fund_objective_role",
        "holdings_exposure",
        "construction_methodology",
        "cost_trading_context",
        "etf_specific_risks",
        "similar_assets_alternatives",
        "recent_developments",
        "educational_suitability",
    } <= set(sections)
    assert sections["fund_objective_role"]["metrics"][0]["citation_ids"][0] in citation_ids
    assert sections["cost_trading_context"]["evidence_state"] == "mixed"
    assert "holdings_exposure_detail" in {item["item_id"] for item in sections["holdings_exposure"]["items"]}
    assert "construction_methodology" in {item["item_id"] for item in sections["construction_methodology"]["items"]}
    assert "trading_data_limitation" in {item["item_id"] for item in sections["cost_trading_context"]["items"]}
    assert sections["recent_developments"]["items"][0]["retrieved_at"]
    assert sections["similar_assets_alternatives"]["citation_ids"] == []


def test_stock_overview_serializes_structured_prd_sections():
    response = client.get("/api/assets/AAPL/overview")

    assert response.status_code == 200
    body = response.json()
    sections = {section["section_id"]: section for section in body["sections"]}
    assert {
        "business_overview",
        "products_services",
        "strengths",
        "financial_quality",
        "valuation_context",
        "top_risks",
        "recent_developments",
        "educational_suitability",
    } <= set(sections)
    assert sections["business_overview"]["items"][0]["citation_ids"]
    assert sections["strengths"]["evidence_state"] == "supported"
    assert sections["financial_quality"]["evidence_state"] == "mixed"
    assert sections["valuation_context"]["evidence_state"] == "mixed"
    assert sections["valuation_context"]["citation_ids"]
    assert "valuation_data_limitation" in {item["item_id"] for item in sections["valuation_context"]["items"]}
    assert sections["top_risks"]["items"][0]["source_document_ids"]


def test_details_sources_and_recent_routes_exist():
    details = client.get("/api/assets/AAPL/details")
    sources = client.get("/api/assets/AAPL/sources")
    recent = client.get("/api/assets/AAPL/recent")
    weekly = client.get("/api/assets/AAPL/weekly-news")

    assert details.status_code == 200
    assert sources.status_code == 200
    assert recent.status_code == 200
    assert weekly.status_code == 200
    assert details.json()["facts"]["business_model"]
    assert sources.json()["sources"][0]["source_document_id"] == "src_aapl_10k_fixture"
    assert sources.json()["sources"][0]["publisher"] == "U.S. SEC"
    assert sources.json()["sources"][0]["allowlist_status"] == "allowed"
    assert sources.json()["sources"][0]["source_use_policy"] == "full_text_allowed"
    assert sources.json()["schema_version"] == "asset-source-drawer-v1"
    assert sources.json()["drawer_state"] == "available"
    assert sources.json()["source_groups"][0]["source_document_id"] == "src_aapl_10k_fixture"
    assert sources.json()["source_groups"][0]["allowed_excerpts"][0]["text"]
    assert sources.json()["citation_bindings"][0]["citation_id"]
    assert sources.json()["related_claims"][0]["citation_ids"]
    assert sources.json()["section_references"][0]["freshness_state"]
    assert recent.json()["recent_developments"][0]["freshness_state"] == "fresh"
    assert weekly.json()["weekly_news_focus"]["state"] == "no_high_signal"
    assert weekly.json()["ai_comprehensive_analysis"]["state"] == "suppressed"


def test_knowledge_pack_route_serializes_cached_and_non_generated_states():
    cached = client.get("/api/assets/VOO/knowledge-pack")
    cached_again = client.get("/api/assets/voo/knowledge-pack")
    eligible = client.get("/api/assets/SPY/knowledge-pack")
    unsupported = client.get("/api/assets/TQQQ/knowledge-pack")
    unknown = client.get("/api/assets/ZZZZ/knowledge-pack")

    assert cached.status_code == 200
    assert cached_again.status_code == 200
    assert cached.json() == cached_again.json()

    body = cached.json()
    assert body["schema_version"] == "asset-knowledge-pack-build-v1"
    assert body["ticker"] == "VOO"
    assert body["asset"]["ticker"] == "VOO"
    assert body["asset_type"] == "etf"
    assert body["pack_id"] == "asset-knowledge-pack-voo-local-fixture-v1"
    assert body["build_state"] == "available"
    assert body["generated_output_available"] is True
    assert body["reusable_generated_output_cache_hit"] is False
    assert body["generated_route"] == "/assets/VOO"
    assert body["capabilities"]["can_open_generated_page"] is True
    assert body["capabilities"]["can_answer_chat"] is True
    assert body["capabilities"]["can_compare"] is True
    assert body["freshness"]["freshness_state"] == "fresh"
    assert body["knowledge_pack_freshness_hash"]
    assert body["cache_revalidation"]["state"] == "miss"
    assert body["source_document_ids"]
    assert body["citation_ids"]
    assert body["counts"]["source_document_count"] == len(body["source_documents"])
    assert body["counts"]["normalized_fact_count"] == len(body["normalized_facts"])
    assert body["counts"]["source_chunk_count"] == len(body["source_chunks"])
    assert body["counts"]["recent_development_count"] == len(body["recent_developments"])
    assert "canonical_facts" in {label["section_id"] for label in body["section_freshness"]}
    assert {source["asset_ticker"] for source in body["source_documents"]} == {"VOO"}
    assert {source["allowlist_status"] for source in body["source_documents"]} == {"allowed"}
    assert {source["source_use_policy"] for source in body["source_documents"]} <= {"full_text_allowed", "summary_allowed"}
    assert {fact["asset_ticker"] for fact in body["normalized_facts"]} == {"VOO"}
    assert {chunk["asset_ticker"] for chunk in body["source_chunks"]} == {"VOO"}
    assert {recent["asset_ticker"] for recent in body["recent_developments"]} == {"VOO"}
    assert "supporting_passage" not in str(body)

    for response, expected_state, expected_cache_state in [
        (eligible, "eligible_not_cached", "eligible_not_cached"),
        (unsupported, "unsupported", "unsupported"),
        (unknown, "unknown", "unknown"),
    ]:
        assert response.status_code == 200
        non_generated = response.json()
        assert non_generated["build_state"] == expected_state
        assert non_generated["generated_output_available"] is False
        assert non_generated["generated_route"] is None
        assert non_generated["capabilities"]["can_open_generated_page"] is False
        assert non_generated["capabilities"]["can_answer_chat"] is False
        assert non_generated["capabilities"]["can_compare"] is False
        assert non_generated["source_document_ids"] == []
        assert non_generated["citation_ids"] == []
        assert non_generated["source_documents"] == []
        assert non_generated["normalized_facts"] == []
        assert non_generated["source_chunks"] == []
        assert non_generated["recent_developments"] == []
        assert non_generated["source_checksums"] == []
        assert non_generated["knowledge_pack_freshness_hash"] is None
        assert non_generated["cache_revalidation"]["state"] == expected_cache_state
        assert non_generated["cache_revalidation"]["reusable"] is False


def test_asset_page_and_source_list_export_routes_return_contract_payloads():
    asset_export = client.get("/api/assets/VOO/export")
    source_export = client.get("/api/assets/VOO/sources/export")

    assert asset_export.status_code == 200
    assert source_export.status_code == 200

    asset_body = asset_export.json()
    source_body = source_export.json()
    assert asset_body["content_type"] == "asset_page"
    assert asset_body["export_format"] == "markdown"
    assert asset_body["export_state"] == "available"
    assert asset_body["asset"]["ticker"] == "VOO"
    assert asset_body["disclaimer"]
    assert asset_body["licensing_note"]["note_id"] == "export_licensing_scope"
    assert "Educational Disclaimer" in asset_body["rendered_markdown"]
    assert "top_risks" in {section["section_id"] for section in asset_body["sections"]}
    assert "weekly_news_focus" in {section["section_id"] for section in asset_body["sections"]}
    assert "ai_comprehensive_analysis" in {section["section_id"] for section in asset_body["sections"]}
    assert len(next(section for section in asset_body["sections"] if section["section_id"] == "top_risks")["items"]) == 3
    assert asset_body["citations"]
    assert asset_body["source_documents"]

    assert source_body["content_type"] == "asset_source_list"
    assert source_body["export_state"] == "available"
    assert source_body["sections"][0]["section_id"] == "asset_source_list"
    assert source_body["source_documents"][0]["source_document_id"]
    assert source_body["source_documents"][0]["allowed_excerpt"]["note"]
    assert source_body["source_documents"][0]["allowlist_status"] == "allowed"
    assert source_body["source_documents"][0]["source_use_policy"] in {"full_text_allowed", "summary_allowed"}
    assert source_body["source_documents"][0]["permitted_operations"]["can_export_full_text"] is False


def test_trust_metrics_catalog_route_is_validation_only_contract():
    response = client.get("/api/trust-metrics/catalog")

    assert response.status_code == 200
    body = response.json()
    product_types = {event["event_type"] for event in body["product_events"]}
    trust_types = {event["event_type"] for event in body["trust_events"]}
    assert body["schema_version"] == "trust-metrics-event-v1"
    assert body["validation_only"] is True
    assert body["persistence_enabled"] is False
    assert body["external_analytics_enabled"] is False
    assert body["no_live_external_calls"] is True
    assert "search_success" in product_types
    assert "asset_page_view" in product_types
    assert "chat_answer_outcome" in product_types
    assert "citation_coverage" in trust_types
    assert "generated_output_validation_failure" in trust_types
    assert "freshness_accuracy" in trust_types
    assert "source_url" in body["forbidden_field_names"]


def test_trust_metrics_validate_route_accepts_rejects_and_summarizes_without_storage():
    response = client.post(
        "/api/trust-metrics/validate",
        json={
            "events": [
                {
                    "event_type": "search_success",
                    "workflow_area": "search",
                    "asset_ticker": "voo",
                    "metadata": {"result_count": 1, "latency_ms": 15},
                },
                {
                    "event_type": "citation_coverage",
                    "workflow_area": "citation",
                    "asset_ticker": "VOO",
                    "generated_output_available": True,
                    "output_metadata": {
                        "output_kind": "asset_page",
                        "schema_valid": True,
                        "citation_coverage_rate": 1,
                        "citation_ids": ["c_voo_profile"],
                        "source_document_ids": ["src_voo_fact_sheet_fixture"],
                        "freshness_state": "fresh",
                    },
                },
                {
                    "event_type": "chat_answer_outcome",
                    "workflow_area": "chat",
                    "asset_ticker": "VOO",
                    "question": "raw question text is not allowed",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_count"] == 2
    assert body["rejected_count"] == 1
    assert body["stored"] is False
    assert body["forwarded"] is False
    assert body["enriched_from_live_services"] is False
    accepted_event = body["events"][0]["normalized_event"]
    assert accepted_event["asset_ticker"] == "VOO"
    assert accepted_event["asset_support_state"] == "cached_supported"
    assert accepted_event["occurred_at"] == "1970-01-01T00:00:00Z"
    assert body["events"][2]["validation_status"] == "rejected"
    assert "question" in body["events"][2]["rejected_field_paths"]
    assert body["summary"]["event_type_counts"] == {"citation_coverage": 1, "search_success": 1}
    assert body["summary"]["rates"]["citation_coverage_event_rate"] == 0.5


def test_trust_metrics_validate_route_blocks_non_generated_asset_inconsistency():
    response = client.post(
        "/api/trust-metrics/validate",
        json={
            "events": [
                {
                    "event_type": "asset_page_view",
                    "workflow_area": "asset_page",
                    "asset_ticker": "SPY",
                    "generated_output_available": True,
                },
                {
                    "event_type": "generated_output_validation_failure",
                    "workflow_area": "generated_output",
                    "asset_ticker": "TQQQ",
                    "output_metadata": {
                        "output_kind": "asset_page",
                        "schema_valid": False,
                        "citation_ids": ["c_bad"],
                        "source_document_ids": ["src_bad"],
                    },
                },
                {
                    "event_type": "stale_data_incident",
                    "workflow_area": "freshness",
                    "asset_ticker": "VOO",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_count"] == 0
    assert body["rejected_count"] == 3
    joined_reasons = " ".join(reason for event in body["events"] for reason in event["rejection_reasons"])
    assert "generated output cannot be available" in joined_reasons
    assert "citation and source document IDs" in joined_reasons
    assert "freshness_state" in joined_reasons


def test_trust_metrics_validation_does_not_mutate_existing_generated_payloads():
    overview_before = client.get("/api/assets/VOO/overview").json()
    chat_before = client.post("/api/assets/VOO/chat", json={"question": "What is VOO?"}).json()
    comparison_before = client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json()
    export_before = client.get("/api/assets/VOO/export").json()

    validation = client.post(
        "/api/trust-metrics/validate",
        json={
            "events": [
                {"event_type": "export_usage", "workflow_area": "export", "asset_ticker": "VOO"},
                {"event_type": "chat_safety_redirect", "workflow_area": "chat", "asset_ticker": "VOO"},
            ]
        },
    )

    assert validation.status_code == 200
    assert client.get("/api/assets/VOO/overview").json() == overview_before
    assert _without_session(client.post("/api/assets/VOO/chat", json={"question": "What is VOO?"}).json()) == _without_session(
        chat_before
    )
    assert client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"}).json() == comparison_before
    assert client.get("/api/assets/VOO/export").json() == export_before


def test_llm_runtime_route_is_sanitized_diagnostics_only_contract():
    response = client.get("/api/llm/runtime")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "llm-runtime-contract-v1"
    assert body["runtime"]["provider_kind"] == "mock"
    assert body["runtime"]["runtime_mode"] == "deterministic_mock"
    assert body["runtime"]["live_generation_enabled"] is False
    assert body["runtime"]["live_gate_state"] == "disabled"
    assert body["runtime"]["server_side_key_present"] is False
    assert body["runtime"]["live_network_calls_allowed"] is False
    assert body["credential_values_exposed"] is False
    assert body["private_prompt_fields_exposed"] is False
    assert body["model_reasoning_payload_exposed"] is False
    assert body["restricted_source_payload_exposed"] is False
    assert "reasoning_summary" in body["public_metadata_fields"]
    serialized = str(body).lower()
    assert "api_key" not in serialized
    assert "reasoning_details" not in serialized
    assert "raw_source_text" not in serialized


def test_comparison_and_chat_export_routes_return_explicit_shapes():
    comparison = client.post(
        "/api/compare/export",
        json={"left_ticker": "VOO", "right_ticker": "QQQ", "export_format": "markdown"},
    )
    comparison_query = client.get("/api/compare/export", params={"left_ticker": "VOO", "right_ticker": "QQQ"})
    chat = client.post(
        "/api/assets/QQQ/chat/export",
        json={"question": "What is this fund?", "conversation_id": "local-test"},
    )

    assert comparison.status_code == 200
    assert comparison_query.status_code == 200
    assert chat.status_code == 200

    comparison_body = comparison.json()
    assert comparison_query.json() == comparison_body
    assert comparison_body["content_type"] == "comparison"
    assert comparison_body["export_state"] == "available"
    assert comparison_body["left_asset"]["ticker"] == "VOO"
    assert comparison_body["right_asset"]["ticker"] == "QQQ"
    assert comparison_body["metadata"]["comparison_type"] == "etf_vs_etf"
    assert "key_differences" in {section["section_id"] for section in comparison_body["sections"]}
    assert comparison_body["citations"]
    assert comparison_body["source_documents"]

    chat_body = chat.json()
    assert chat_body["content_type"] == "chat_transcript"
    assert chat_body["export_state"] == "available"
    assert chat_body["asset"]["ticker"] == "QQQ"
    assert chat_body["metadata"]["submitted_question"] == "What is this fund?"
    assert chat_body["metadata"]["safety_classification"] == "educational"
    assert "chat_answer" in {section["section_id"] for section in chat_body["sections"]}
    assert chat_body["citations"]
    assert chat_body["source_documents"]


def test_advice_chat_export_redirects_without_factual_sources():
    response = client.post("/api/assets/VOO/chat/export", json={"question": "Should I buy VOO today?"})

    assert response.status_code == 200
    body = response.json()
    assert body["content_type"] == "chat_transcript"
    assert body["export_state"] == "available"
    assert body["metadata"]["safety_classification"] == "personalized_advice_redirect"
    assert "educational" in body["rendered_markdown"].lower()
    assert body["citations"] == []
    assert body["source_documents"] == []


def test_export_routes_block_unsupported_unknown_and_eligible_not_cached_outputs():
    unsupported = client.get("/api/assets/BTC/export").json()
    unknown = client.get("/api/assets/ZZZZ/export").json()
    eligible_not_cached = client.get("/api/assets/SPY/export").json()
    unavailable_comparison = client.post(
        "/api/compare/export",
        json={"left_ticker": "VOO", "right_ticker": "BTC"},
    ).json()
    unsupported_chat = client.post("/api/assets/BTC/chat/export", json={"question": "What is this?"}).json()

    for body in [unsupported, unknown, eligible_not_cached, unavailable_comparison, unsupported_chat]:
        assert body["export_state"] in {"unsupported", "unavailable"}
        assert body["sections"] == []
        assert body["citations"] == []
        assert body["source_documents"] == []
        assert "Export unavailable" in body["rendered_markdown"]

    assert unsupported["export_state"] == "unsupported"
    assert unknown["export_state"] == "unavailable"
    assert eligible_not_cached["export_state"] == "unavailable"
    assert unsupported_chat["metadata"]["generated_chat_answer"] is False


def test_unknown_and_unsupported_assets_return_clear_states():
    unknown = client.get("/api/assets/ZZZZ/overview").json()
    unsupported_overview = client.get("/api/assets/BTC/overview").json()
    unsupported = client.get("/api/search", params={"q": "BTC"}).json()

    assert unknown["state"]["status"] == "unknown"
    assert unknown["asset"]["supported"] is False
    assert unknown["beginner_summary"] is None
    assert unknown["sections"] == []
    assert unsupported_overview["state"]["status"] == "unsupported"
    assert unsupported_overview["asset"]["supported"] is False
    assert unsupported_overview["sections"] == []
    assert unsupported["state"]["status"] == "unsupported"
    assert unsupported["state"]["support_classification"] == "recognized_unsupported"
    assert unsupported["results"][0]["supported"] is False
    assert unsupported["results"][0]["support_classification"] == "recognized_unsupported"
    assert unsupported["results"][0]["can_open_generated_page"] is False
    assert unsupported["results"][0]["can_answer_chat"] is False
    assert unsupported["results"][0]["can_compare"] is False
    assert unsupported["results"][0]["generated_route"] is None
    assert "outside" in unsupported["state"]["message"]


def test_compare_route_returns_educational_shape():
    response = client.post("/api/compare", json={"left_ticker": "VOO", "right_ticker": "QQQ"})

    assert response.status_code == 200
    body = response.json()
    assert body["comparison_type"] == "etf_vs_etf"
    assert body["bottom_line_for_beginners"]["summary"]
    assert body["key_differences"][0]["citation_ids"]
    assert body["state"]["status"] == "supported"
    assert body["source_documents"]
    source_ids = {source["source_document_id"] for source in body["source_documents"]}
    assert {citation["source_document_id"] for citation in body["citations"]} <= source_ids
    source = body["source_documents"][0]
    assert source["source_document_id"]
    assert source["title"]
    assert source["publisher"]
    assert source["source_type"]
    assert source["url"]
    assert source["published_at"] or source["as_of_date"]
    assert source["retrieved_at"]
    assert source["freshness_state"] == "fresh"
    assert source["is_official"] is True
    assert source["supporting_passage"]
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
    assert unsupported["source_documents"] == []


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
    assert body["session"]["lifecycle_state"] == "active"
    assert body["session"]["selected_asset"]["ticker"] == "QQQ"
    assert body["session"]["turn_count"] == 1
    assert body["session"]["export_available"] is True


def test_chat_session_status_continue_mismatch_delete_and_export_routes():
    first = client.post("/api/assets/VOO/chat", json={"question": "What is VOO?"})
    assert first.status_code == 200
    first_body = first.json()
    conversation_id = first_body["session"]["conversation_id"]

    continued = client.post(
        "/api/assets/VOO/chat",
        json={"question": "What top risk should a beginner understand?", "conversation_id": conversation_id},
    )
    status = client.get(f"/api/chat-sessions/{conversation_id}")
    mismatch = client.post(
        "/api/assets/QQQ/chat",
        json={"question": "What is this fund?", "conversation_id": conversation_id},
    )
    export = client.get(f"/api/chat-sessions/{conversation_id}/export")
    deleted = client.post(f"/api/chat-sessions/{conversation_id}/delete")
    deleted_again = client.post(f"/api/chat-sessions/{conversation_id}/delete")
    deleted_export = client.get(f"/api/chat-sessions/{conversation_id}/export")

    assert continued.status_code == 200
    assert status.status_code == 200
    assert mismatch.status_code == 200
    assert export.status_code == 200
    assert deleted.status_code == 200
    assert deleted_again.status_code == 200
    assert deleted_export.status_code == 200

    continued_body = continued.json()
    status_body = status.json()
    mismatch_body = mismatch.json()
    export_body = export.json()
    deleted_body = deleted.json()
    deleted_again_body = deleted_again.json()
    deleted_export_body = deleted_export.json()

    assert continued_body["session"]["conversation_id"] == conversation_id
    assert continued_body["session"]["turn_count"] == 2
    assert status_body["session"]["lifecycle_state"] == "active"
    assert status_body["session"]["selected_asset"]["ticker"] == "VOO"
    assert len(status_body["turn_summaries"]) == 2
    assert "What is VOO?" not in str(status_body)
    assert mismatch_body["session"]["lifecycle_state"] == "ticker_mismatch"
    assert mismatch_body["citations"] == []
    assert mismatch_body["source_documents"] == []
    assert export_body["content_type"] == "chat_transcript"
    assert export_body["export_state"] == "available"
    assert export_body["metadata"]["conversation_id"] == conversation_id
    assert export_body["citations"]
    assert export_body["source_documents"]
    assert "What top risk should a beginner understand?" not in export_body["rendered_markdown"]
    assert deleted_body["deleted"] is True
    assert deleted_again_body["deleted"] is True
    assert deleted_body["session"]["lifecycle_state"] == "deleted"
    assert deleted_export_body["export_state"] == "unavailable"
    assert deleted_export_body["sections"] == []


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
