from pathlib import Path
import os
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = ROOT / "evals"

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")
sys.path.insert(0, str(ROOT))

from backend.chat import generate_asset_chat, validate_chat_response
from backend.citations import validate_claims
from backend.comparison import generate_comparison, validate_comparison_response
from backend.export import export_asset_page, export_asset_source_list, export_chat_transcript, export_comparison
from backend.ingestion import get_ingestion_job_status, request_ingestion
from backend.main import app
from backend.models import (
    ChatResponse,
    ChatTranscriptExportRequest,
    CompareResponse,
    ComparisonExportRequest,
    EDUCATIONAL_DISCLAIMER,
    EvidenceState,
    ExportResponse,
    IngestionJobResponse,
    MetricValue,
    ProviderDataCategory,
    ProviderKind,
    ProviderResponse,
    ProviderResponseState,
    ProviderSourceUsage,
)
from backend.overview import generate_asset_overview, validate_overview_response
from backend.providers import fetch_mock_provider_response, get_mock_provider_adapters
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


def test_search_cases():
    data = load_yaml("search_eval_cases.yaml")
    cases = data.get("cases", [])
    assert cases, "search_eval_cases.yaml must define cases"

    required_states = {"supported", "ambiguous", "unsupported", "unknown", "ingestion_needed"}
    found_states = {case.get("expected_state") for case in cases}
    missing_states = required_states - found_states
    assert not missing_states, f"Missing search states: {missing_states}"

    required_classifications = {"cached_supported", "recognized_unsupported", "unknown", "eligible_not_cached"}
    found_classifications = {
        classification
        for case in cases
        for classification in case.get("expected_support_classifications", [])
    }
    missing_classifications = required_classifications - found_classifications
    assert not missing_classifications, f"Missing search support classifications: {missing_classifications}"

    for case in cases:
        response = client.get("/api/search", params={"q": case["query"]})
        assert response.status_code == 200, f"{case['id']} search request failed"
        body = response.json()
        state = body["state"]
        results = body["results"]

        assert state["status"] == case["expected_state"], (
            f"{case['id']} expected {case['expected_state']}, got {state['status']}"
        )
        assert state["can_open_generated_page"] is case["expected_can_open_generated_page"]
        assert state["can_request_ingestion"] is case.get("expected_can_request_ingestion", False)
        assert state["requires_disambiguation"] is case.get("expected_requires_disambiguation", False)
        assert state["requires_ingestion"] is case.get("expected_requires_ingestion", False)
        expected_ingestion_route = case.get("expected_ingestion_request_route")
        if expected_ingestion_route:
            assert state["ingestion_request_route"] == expected_ingestion_route
        else:
            assert state["ingestion_request_route"] is None

        result_tickers = {result["ticker"] for result in results}
        expected_tickers = set(case["expected_result_tickers"])
        assert expected_tickers <= result_tickers, f"{case['id']} missing expected tickers: {expected_tickers - result_tickers}"

        result_classifications = {result["support_classification"] for result in results}
        expected_classifications = set(case["expected_support_classifications"])
        assert expected_classifications <= result_classifications, (
            f"{case['id']} missing classifications: {expected_classifications - result_classifications}"
        )

        for result in results:
            if result["support_classification"] == "cached_supported":
                assert result["generated_route"] == f"/assets/{result['ticker']}"
                assert result["can_open_generated_page"] is True
                assert result["can_answer_chat"] is True
                assert result["can_compare"] is True
                assert result["can_request_ingestion"] is False
                assert result["ingestion_request_route"] is None
            elif result["support_classification"] == "eligible_not_cached":
                assert result["generated_route"] is None
                assert result["can_open_generated_page"] is False
                assert result["can_answer_chat"] is False
                assert result["can_compare"] is False
                assert result["can_request_ingestion"] is True
                assert result["ingestion_request_route"] == f"/api/admin/ingest/{result['ticker']}"
            else:
                assert result["generated_route"] is None
                assert result["can_open_generated_page"] is False
                assert result["can_answer_chat"] is False
                assert result["can_compare"] is False
                assert result["can_request_ingestion"] is False
                assert result["ingestion_request_route"] is None

    search_source = (ROOT / "backend" / "search.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in search_source
        assert forbidden not in main_source


def test_ingestion_cases():
    data = load_yaml("ingestion_eval_cases.yaml")
    request_cases = data.get("request_cases", [])
    status_cases = data.get("status_cases", [])
    assert request_cases, "ingestion_eval_cases.yaml must define request cases"
    assert status_cases, "ingestion_eval_cases.yaml must define status cases"

    required_request_states = {"pending", "running", "no_ingestion_needed", "unsupported", "unknown"}
    found_request_states = {case.get("expected_job_state") for case in request_cases}
    missing_request_states = required_request_states - found_request_states
    assert not missing_request_states, f"Missing ingestion request states: {missing_request_states}"

    required_status_states = {"pending", "running", "succeeded", "refresh_needed", "failed", "unavailable"}
    found_status_states = {case.get("expected_job_state") for case in status_cases}
    missing_status_states = required_status_states - found_status_states
    assert not missing_status_states, f"Missing ingestion status states: {missing_status_states}"

    for case in request_cases:
        response = client.post(f"/api/admin/ingest/{case['ticker']}")
        assert response.status_code == 200, f"{case['id']} ingestion request failed"
        body = response.json()
        validated = IngestionJobResponse.model_validate(body)

        assert validated.ticker == case["ticker"]
        assert validated.asset_type.value == case["expected_asset_type"]
        assert (validated.job_type.value if validated.job_type else None) == case["expected_job_type"]
        assert validated.job_id == case["expected_job_id"]
        assert validated.job_state.value == case["expected_job_state"]
        assert (validated.worker_status.value if validated.worker_status else None) == case["expected_worker_status"]
        assert validated.status_url == case["expected_status_url"]
        assert validated.generated_route == case["expected_generated_route"]
        assert validated.retryable is case["expected_retryable"]
        expected_capabilities = case["expected_capabilities"]
        assert validated.capabilities.can_open_generated_page is expected_capabilities["can_open_generated_page"]
        assert validated.capabilities.can_answer_chat is expected_capabilities["can_answer_chat"]
        assert validated.capabilities.can_compare is expected_capabilities["can_compare"]
        assert validated.capabilities.can_request_ingestion is expected_capabilities["can_request_ingestion"]
        assert "buy" not in validated.message.lower()
        assert "sell" not in validated.message.lower()
        assert "hold" not in validated.message.lower()

        rerun = request_ingestion(case["ticker"])
        assert rerun.model_dump(mode="json") == body

    for case in status_cases:
        response = client.get(f"/api/jobs/{case['job_id']}")
        assert response.status_code == 200, f"{case['id']} status lookup failed"
        validated = IngestionJobResponse.model_validate(response.json())

        assert validated.job_id == case["job_id"]
        assert validated.ticker == case["expected_ticker"]
        assert validated.asset_type.value == case["expected_asset_type"]
        assert validated.job_state.value == case["expected_job_state"]
        assert (validated.worker_status.value if validated.worker_status else None) == case["expected_worker_status"]
        assert validated.status_url == f"/api/jobs/{case['job_id']}"
        assert validated.generated_route == case["expected_generated_route"]
        expected_error_code = case.get("expected_error_code")
        if expected_error_code:
            assert validated.error_metadata is not None
            assert validated.error_metadata.code == expected_error_code
        else:
            assert validated.error_metadata is None

        direct = get_ingestion_job_status(case["job_id"])
        assert direct.model_dump(mode="json") == validated.model_dump(mode="json")

    ingestion_source = (ROOT / "backend" / "ingestion.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in ingestion_source
        assert forbidden not in main_source


def test_provider_cases():
    data = load_yaml("provider_eval_cases.yaml")
    adapters = get_mock_provider_adapters()
    required_provider_kinds = {ProviderKind(kind) for kind in data.get("required_provider_kinds", [])}
    assert required_provider_kinds <= set(adapters), f"Missing provider adapters: {required_provider_kinds - set(adapters)}"

    for adapter in adapters.values():
        assert adapter.capability.requires_credentials is False
        assert adapter.capability.live_calls_allowed is False
        assert adapter.capability.data_categories

    for case in data.get("supported_cases", []):
        response = fetch_mock_provider_response(
            ProviderKind(case["provider_kind"]),
            case["ticker"],
            ProviderDataCategory(case["data_category"]),
        )
        validated = ProviderResponse.model_validate(response.model_dump(mode="json"))
        assert validated.state.value == case["expected_state"], f"{case['id']} returned {validated.state.value}"
        assert validated.asset is not None, f"{case['id']} should include asset identity"
        assert validated.asset.ticker == case["ticker"]
        assert validated.asset.asset_type.value == case["expected_asset_type"]
        assert validated.no_live_external_calls is True
        _assert_provider_generated_flags_off(validated, case["id"])
        assert bool(validated.licensing.export_allowed) is case["expected_export_allowed"]

        source_ids = {source.source_document_id for source in validated.source_attributions}
        assert source_ids, f"{case['id']} should include source attribution"
        assert {source.asset_ticker for source in validated.source_attributions} == {case["ticker"]}
        assert all(source.usage is ProviderSourceUsage(case["expected_source_usage"]) for source in validated.source_attributions)
        assert all(source.is_official is case["expected_official_source"] for source in validated.source_attributions)
        assert all(source.retrieved_at for source in validated.source_attributions)
        assert all(source.freshness_state.value in {"fresh", "stale", "unknown", "unavailable"} for source in validated.source_attributions)
        assert all(source.licensing.provider_name == validated.licensing.provider_name for source in validated.source_attributions)

        expected_fact_fields = set(case.get("expected_fact_fields", []))
        fact_fields = {fact.field_name for fact in validated.facts}
        assert expected_fact_fields <= fact_fields, f"{case['id']} missing facts: {expected_fact_fields - fact_fields}"
        assert {fact.asset_ticker for fact in validated.facts} <= {case["ticker"]}
        assert all(set(fact.source_document_ids) <= source_ids for fact in validated.facts)
        assert all(fact.uses_glossary_as_support is False for fact in validated.facts)
        assert not any("glossary" in citation_id.lower() for fact in validated.facts for citation_id in fact.citation_ids)

        if case.get("expected_recent_events"):
            assert validated.recent_developments, f"{case['id']} expected recent-development candidates"
            assert all(event.asset_ticker == case["ticker"] for event in validated.recent_developments)
            assert all(event.event_date for event in validated.recent_developments)
            assert all(event.source_date or event.as_of_date for event in validated.recent_developments)
            assert all(event.retrieved_at for event in validated.recent_developments)
            assert all(event.source_document_id in source_ids for event in validated.recent_developments)
            assert all(event.can_overwrite_canonical_facts is False for event in validated.recent_developments)

    for case in data.get("eligible_not_cached_cases", []):
        response = fetch_mock_provider_response(ProviderKind(case["provider_kind"]), case["ticker"])
        validated = ProviderResponse.model_validate(response.model_dump(mode="json"))
        assert validated.state is ProviderResponseState.eligible_not_cached
        assert validated.asset is not None
        assert validated.asset.asset_type.value == case["expected_asset_type"]
        _assert_provider_generated_flags_off(validated, case["id"])

    for case in data.get("failure_cases", []):
        response = fetch_mock_provider_response(ProviderKind(case["provider_kind"]), case["ticker"])
        validated = ProviderResponse.model_validate(response.model_dump(mode="json"))
        assert validated.state.value == case["expected_state"]
        assert validated.facts == []
        assert validated.recent_developments == []
        assert validated.errors
        assert validated.errors[0].code == case["expected_error_code"]
        _assert_provider_generated_flags_off(validated, case["id"])

    for case in data.get("recent_no_high_signal_cases", []):
        response = fetch_mock_provider_response(ProviderKind(case["provider_kind"]), case["ticker"])
        validated = ProviderResponse.model_validate(response.model_dump(mode="json"))
        assert validated.state is ProviderResponseState.no_high_signal
        assert validated.recent_developments == []
        assert validated.source_attributions
        assert all(source.usage is ProviderSourceUsage.recent_context for source in validated.source_attributions)
        assert all(source.can_support_canonical_facts is False for source in validated.source_attributions)
        _assert_provider_generated_flags_off(validated, case["id"])

    sec_aapl = fetch_mock_provider_response(ProviderKind.sec, "AAPL")
    market_aapl = fetch_mock_provider_response(ProviderKind.market_reference, "AAPL")
    issuer_voo = fetch_mock_provider_response(ProviderKind.etf_issuer, "VOO")
    market_voo = fetch_mock_provider_response(ProviderKind.market_reference, "VOO")
    assert min(source.source_rank for source in sec_aapl.source_attributions) < min(
        source.source_rank for source in market_aapl.source_attributions
    )
    assert min(source.source_rank for source in issuer_voo.source_attributions) < min(
        source.source_rank for source in market_voo.source_attributions
    )
    assert market_aapl.licensing.export_allowed is False
    assert market_aapl.licensing.redistribution_allowed is False

    providers_source = (ROOT / "backend" / "providers.py").read_text(encoding="utf-8")
    for forbidden in [
        "import requests",
        "import httpx",
        "urllib",
        "socket",
        "boto3",
        "polygon",
        "massive",
        "finnhub",
        "benzinga",
        "os.environ",
        "api_key",
    ]:
        assert forbidden not in providers_source


def test_retrieval_fixture_contract():
    dataset = load_retrieval_fixture_dataset()
    assert dataset.no_live_external_calls is True

    required_tickers = {"AAPL", "VOO", "QQQ"}
    fixture_tickers = {fixture.asset.ticker for fixture in dataset.assets}
    assert required_tickers <= fixture_tickers

    all_gap_states = set()
    for ticker in required_tickers:
        pack = build_asset_knowledge_pack(ticker)
        fact_fields = {fact.fact.field_name for fact in pack.normalized_facts}
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

        if ticker == "AAPL":
            assert {
                "products_services_detail",
                "business_quality_strength",
                "financial_quality_revenue_trend",
                "valuation_data_limitation",
            } <= fact_fields
        else:
            assert {
                "holdings_exposure_detail",
                "construction_methodology",
                "trading_data_limitation",
            } <= fact_fields

    comparison_pack = build_comparison_knowledge_pack("VOO", "QQQ")
    assert comparison_pack.computed_differences
    assert {source.asset_ticker for source in comparison_pack.comparison_sources} <= {"VOO", "QQQ"}

    all_gap_states.update(gap.evidence_state for gap in build_asset_knowledge_pack("BTC").evidence_gaps)
    assert {"missing", "stale", "unsupported", "insufficient"} <= all_gap_states

    retrieval_source = (ROOT / "backend" / "retrieval.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in retrieval_source


def test_generated_overview_contract():
    stock_sections = {
        "business_overview",
        "products_services",
        "strengths",
        "financial_quality",
        "valuation_context",
        "top_risks",
        "recent_developments",
        "educational_suitability",
    }
    etf_sections = {
        "fund_objective_role",
        "holdings_exposure",
        "construction_methodology",
        "cost_trading_context",
        "etf_specific_risks",
        "similar_assets_alternatives",
        "recent_developments",
        "educational_suitability",
    }

    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)
        overview = generate_asset_overview(ticker)
        citation_ids = {citation.citation_id for citation in overview.citations}
        source_ids = {source.source_document_id for source in overview.source_documents}
        pack_source_ids = {source.source_document_id for source in pack.source_documents}
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
            *{citation_id for section in overview.sections for citation_id in section.citation_ids},
            *{citation_id for section in overview.sections for item in section.items for citation_id in item.citation_ids},
            *{citation_id for section in overview.sections for metric in section.metrics for citation_id in metric.citation_ids},
        }
        used_source_ids = {
            *{source_id for section in overview.sections for source_id in section.source_document_ids},
            *{source_id for section in overview.sections for item in section.items for source_id in item.source_document_ids},
            *{source_id for section in overview.sections for metric in section.metrics for source_id in metric.source_document_ids},
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
        assert used_source_ids <= source_ids
        assert used_source_ids <= pack_source_ids
        assert validate_overview_response(overview, pack).valid
        section_ids = {section.section_id for section in overview.sections}
        if ticker == "AAPL":
            assert stock_sections <= section_ids
            sections = {section.section_id: section for section in overview.sections}
            assert sections["strengths"].evidence_state is EvidenceState.supported
            assert sections["financial_quality"].evidence_state is EvidenceState.mixed
            assert sections["valuation_context"].evidence_state is EvidenceState.mixed
            assert "net_sales_trend" in {item.item_id for item in sections["financial_quality"].items}
            assert "valuation_data_limitation" in {item.item_id for item in sections["valuation_context"].items}
        else:
            assert etf_sections <= section_ids
            sections = {section.section_id: section for section in overview.sections}
            assert sections["holdings_exposure"].evidence_state is EvidenceState.mixed
            assert sections["construction_methodology"].evidence_state is EvidenceState.mixed
            assert sections["cost_trading_context"].evidence_state is EvidenceState.mixed
            assert "holdings_exposure_detail" in {item.item_id for item in sections["holdings_exposure"].items}
            assert "construction_methodology" in {item.item_id for item in sections["construction_methodology"].items}
            assert "trading_data_limitation" in {item.item_id for item in sections["cost_trading_context"].items}
            assert sections["recent_developments"].evidence_state is EvidenceState.no_major_recent_development
            assert sections["recent_developments"].items[0].retrieved_at
            assert len(sections["etf_specific_risks"].items) == 3
        assert any(
            item.evidence_state
            in {EvidenceState.unavailable, EvidenceState.unknown, EvidenceState.stale, EvidenceState.insufficient_evidence}
            for section in overview.sections
            for item in section.items
        )

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
        assert overview.sections == []

    overview_source = (ROOT / "backend" / "overview.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in overview_source


def test_generated_comparison_contract():
    pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison = generate_comparison("VOO", "QQQ")
    reverse = generate_comparison("QQQ", "VOO")
    validated = CompareResponse.model_validate(comparison.model_dump(mode="json"))
    citation_ids = {citation.citation_id for citation in validated.citations}
    source_ids = {source.source_document_id for source in validated.source_documents}
    pack_source_ids = {source.source_document_id for source in pack.comparison_sources}
    used_citation_ids = {
        *{citation_id for item in validated.key_differences for citation_id in item.citation_ids},
        *validated.bottom_line_for_beginners.citation_ids,
    }

    assert validated.left_asset.ticker == "VOO"
    assert validated.right_asset.ticker == "QQQ"
    assert validated.state.status.value == "supported"
    assert validated.comparison_type == "etf_vs_etf"
    assert validated.bottom_line_for_beginners is not None
    assert {"Benchmark", "Expense ratio", "Holdings count", "Breadth", "Educational role"} <= {
        item.dimension for item in validated.key_differences
    }
    assert used_citation_ids <= citation_ids
    assert {citation.source_document_id for citation in validated.citations} <= {
        source.source_document_id for source in pack.comparison_sources
    }
    assert validated.source_documents
    assert {citation.source_document_id for citation in validated.citations} <= source_ids
    assert source_ids <= pack_source_ids
    assert all(source.title for source in validated.source_documents)
    assert all(source.publisher for source in validated.source_documents)
    assert all(source.source_type for source in validated.source_documents)
    assert all(source.url for source in validated.source_documents)
    assert all(source.published_at or source.as_of_date for source in validated.source_documents)
    assert all(source.retrieved_at for source in validated.source_documents)
    assert all(source.freshness_state.value == "fresh" for source in validated.source_documents)
    assert all(source.is_official is True for source in validated.source_documents)
    assert all(source.supporting_passage for source in validated.source_documents)
    assert validate_comparison_response(validated, pack).valid
    assert reverse.left_asset.ticker == "QQQ"
    assert reverse.right_asset.ticker == "VOO"
    reverse_pack = build_comparison_knowledge_pack("QQQ", "VOO")
    reverse_source_ids = {source.source_document_id for source in reverse.source_documents}
    assert reverse.source_documents
    assert reverse_source_ids <= {source.source_document_id for source in reverse_pack.comparison_sources}
    assert {citation.source_document_id for citation in reverse.citations} <= reverse_source_ids
    assert validate_comparison_response(reverse, reverse_pack).valid

    for pair in [("VOO", "BTC"), ("VOO", "ZZZZ"), ("AAPL", "VOO")]:
        unavailable = generate_comparison(*pair)
        assert unavailable.comparison_type == "unavailable"
        assert unavailable.key_differences == []
        assert unavailable.bottom_line_for_beginners is None
        assert unavailable.citations == []
        assert unavailable.source_documents == []

    comparison_source = (ROOT / "backend" / "comparison.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in comparison_source


def test_generated_chat_contract():
    supported_cases = [
        ("AAPL", "What does Apple do?", "primary business"),
        ("VOO", "What is VOO and what risks should a beginner understand?", "market risk"),
        ("QQQ", "What does QQQ hold?", "about 100"),
        ("VOO", "What changed recently?", "No high-signal recent development"),
        ("QQQ", "Why do beginners consider it?", "Beginners may study QQQ"),
    ]

    for ticker, question, expected_text in supported_cases:
        pack = build_asset_knowledge_pack(ticker)
        response = generate_asset_chat(ticker, question)
        validated = ChatResponse.model_validate(response.model_dump(mode="json"))
        source_ids = {source.source_document_id for source in pack.source_documents}
        citations_by_id = {citation.citation_id: citation for citation in validated.citations}
        source_documents_by_id = {source.citation_id: source for source in validated.source_documents}

        assert validated.asset.ticker == ticker
        assert validated.asset.supported is True
        assert validated.safety_classification.value == "educational"
        assert expected_text in validated.direct_answer
        assert validated.why_it_matters
        assert validated.citations
        assert validated.source_documents
        assert {citation.source_document_id for citation in validated.citations} <= source_ids
        assert set(citations_by_id) == set(source_documents_by_id)
        for citation_id, citation in citations_by_id.items():
            source_document = source_documents_by_id[citation_id]
            assert source_document.source_document_id == citation.source_document_id
            assert source_document.chunk_id == citation.chunk_id
            assert source_document.source_document_id in source_ids
            assert source_document.title
            assert source_document.source_type
            assert source_document.url
            assert source_document.published_at or source_document.as_of_date
            assert source_document.retrieved_at
            assert source_document.supporting_passage
        assert validate_chat_response(validated, pack).valid
        assert not find_forbidden_output_phrases(
            " ".join(
                [
                    validated.direct_answer,
                    validated.why_it_matters,
                    " ".join(validated.uncertainty),
                ]
            )
        )

    insufficient = generate_asset_chat("AAPL", "Is Apple expensive based on valuation?")
    assert insufficient.safety_classification.value == "educational"
    assert "Insufficient evidence" in insufficient.direct_answer
    assert insufficient.citations == []
    assert insufficient.source_documents == []
    assert validate_chat_response(insufficient, build_asset_knowledge_pack("AAPL")).valid

    for ticker in ["BTC", "ZZZZ"]:
        unavailable = generate_asset_chat(ticker, "What is this?")
        assert unavailable.asset.supported is False
        assert unavailable.safety_classification.value == "unsupported_asset_redirect"
        assert unavailable.citations == []
        assert unavailable.source_documents == []

    chat_source = (ROOT / "backend" / "chat.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in chat_source


def test_export_cases():
    data = load_yaml("export_eval_cases.yaml")
    cases = data.get("cases", [])
    assert cases, "export_eval_cases.yaml must define cases"

    required_kinds = {"asset_page", "asset_source_list", "comparison", "chat_transcript"}
    found_kinds = {case.get("export_kind") for case in cases}
    missing_kinds = required_kinds - found_kinds
    assert not missing_kinds, f"Missing export kinds: {missing_kinds}"

    required_states = {"available", "unsupported", "unavailable"}
    found_states = {case.get("expected_state") for case in cases}
    missing_states = required_states - found_states
    assert not missing_states, f"Missing export states: {missing_states}"

    for case in cases:
        export_kind = case["export_kind"]
        if export_kind == "asset_page":
            export = export_asset_page(case["ticker"])
            endpoint_response = client.get(f"/api/assets/{case['ticker']}/export")
        elif export_kind == "asset_source_list":
            export = export_asset_source_list(case["ticker"])
            endpoint_response = client.get(f"/api/assets/{case['ticker']}/sources/export")
        elif export_kind == "comparison":
            request = ComparisonExportRequest(
                left_ticker=case["left_ticker"],
                right_ticker=case["right_ticker"],
            )
            export = export_comparison(request)
            endpoint_response = client.post("/api/compare/export", json=request.model_dump(mode="json"))
        elif export_kind == "chat_transcript":
            request = ChatTranscriptExportRequest(question=case["question"])
            export = export_chat_transcript(case["ticker"], request)
            endpoint_response = client.post(f"/api/assets/{case['ticker']}/chat/export", json=request.model_dump(mode="json"))
        else:
            raise AssertionError(f"Unknown export kind: {export_kind}")

        assert endpoint_response.status_code == 200, f"{case['id']} export endpoint failed"
        endpoint_export = ExportResponse.model_validate(endpoint_response.json())
        validated = ExportResponse.model_validate(export.model_dump(mode="json"))
        assert endpoint_export.model_dump(mode="json") == validated.model_dump(mode="json")

        assert validated.content_type.value == export_kind
        assert validated.export_state.value == case["expected_state"]
        assert validated.disclaimer == EDUCATIONAL_DISCLAIMER
        assert bool(validated.licensing_note.text) is case["expected_licensing_note"]
        assert "full paid-news articles" in validated.licensing_note.text
        assert "Educational Disclaimer" in validated.rendered_markdown

        section_ids = {section.section_id for section in validated.sections}
        expected_sections = set(case["expected_sections"])
        assert expected_sections <= section_ids, f"{case['id']} missing sections: {expected_sections - section_ids}"

        if case["expected_citations"]:
            assert validated.citations, f"{case['id']} expected citations"
            used_citation_ids = {
                *{citation_id for section in validated.sections for citation_id in section.citation_ids},
                *{citation_id for section in validated.sections for item in section.items for citation_id in item.citation_ids},
            }
            assert used_citation_ids <= {citation.citation_id for citation in validated.citations}
            assert not any("glossary" in citation.citation_id.lower() for citation in validated.citations)
        else:
            assert validated.citations == [], f"{case['id']} should not export citations"

        if case["expected_sources"]:
            assert validated.source_documents, f"{case['id']} expected source metadata"
            assert all(source.source_document_id for source in validated.source_documents)
            assert all(source.title for source in validated.source_documents)
            assert all(source.source_type for source in validated.source_documents)
            assert all(source.publisher for source in validated.source_documents)
            assert all(source.url for source in validated.source_documents)
            assert all(source.retrieved_at for source in validated.source_documents)
            assert all(source.allowed_excerpt is not None for source in validated.source_documents)
            assert {citation.source_document_id for citation in validated.citations} <= {
                source.source_document_id for source in validated.source_documents
            }
        else:
            assert validated.source_documents == [], f"{case['id']} should not export source documents"

        expected_classification = case.get("expected_safety_classification")
        if expected_classification:
            assert validated.metadata["safety_classification"] == expected_classification

        if validated.content_type.value == "asset_page" and validated.export_state.value == "available":
            top_risks = next(section for section in validated.sections if section.section_id == "top_risks")
            assert len(top_risks.items) == 3
            assert any(section.section_id == "recent_developments" for section in validated.sections)
            assert validated.metadata["recent_developments_separate"] is True

        if validated.export_state.value in {"unsupported", "unavailable"}:
            assert validated.sections == []
            assert validated.citations == []
            assert validated.source_documents == []

        assert not find_forbidden_output_phrases(_flatten_static_text(validated.model_dump(mode="json")))

    export_source = (ROOT / "backend" / "export.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "reportlab", "weasyprint"]:
        assert forbidden not in export_source
        assert forbidden not in main_source


def _flatten_static_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_static_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_static_text(item) for item in value.values())
    return ""


def _assert_provider_generated_flags_off(response: ProviderResponse, case_id: str) -> None:
    flags = response.generated_output
    assert flags.creates_generated_asset_page is False, f"{case_id} created generated asset page"
    assert flags.creates_generated_chat_answer is False, f"{case_id} created generated chat answer"
    assert flags.creates_generated_comparison is False, f"{case_id} created generated comparison"
    assert flags.creates_overview_sections is False, f"{case_id} created overview sections"
    assert flags.creates_export_payload is False, f"{case_id} created export payload"
    assert flags.creates_frontend_route is False, f"{case_id} created frontend route"


if __name__ == "__main__":
    test_golden_assets()
    test_safety_cases()
    test_citation_cases()
    test_search_cases()
    test_ingestion_cases()
    test_provider_cases()
    test_retrieval_fixture_contract()
    test_generated_overview_contract()
    test_generated_comparison_contract()
    test_generated_chat_contract()
    test_export_cases()
    print("Static evals passed.")
