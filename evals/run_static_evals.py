from pathlib import Path
import os
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = ROOT / "evals"

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")
sys.path.insert(0, str(ROOT))

import backend.models as models
from backend.cache import (
    build_cache_key,
    build_comparison_pack_freshness_input,
    build_generated_output_freshness_input,
    build_knowledge_pack_freshness_input,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
    compute_source_document_checksum,
    evaluate_cache_revalidation,
)
from backend.chat import generate_asset_chat, validate_chat_response
from backend.chat_sessions import (
    CHAT_SESSION_TTL_DAYS,
    CHAT_SESSION_TTL_SECONDS,
    ChatSessionStore,
    answer_chat_with_session,
    chat_session_export_payload,
    delete_chat_session,
    get_chat_session_status,
)
from backend.citations import validate_claims
from backend.comparison import generate_comparison, validate_comparison_response
from backend.data import (
    ASSETS,
    ELIGIBLE_NOT_CACHED_ASSETS,
    OUT_OF_SCOPE_COMMON_STOCKS,
    TOP500_STOCK_UNIVERSE_MANIFEST_PATH,
    is_top500_manifest_stock,
    load_top500_stock_universe_manifest,
    top500_stock_universe_entry,
)
from backend.export import export_asset_page, export_asset_source_list, export_chat_transcript, export_comparison
from backend.glossary import TERM_CATALOG, build_glossary_response
from backend.ingestion import get_ingestion_job_status, request_ingestion
from backend.ingestion import get_pre_cache_job_status, request_launch_universe_pre_cache, request_pre_cache_for_asset
from backend.llm import (
    DEFAULT_OPENROUTER_FREE_MODEL_ORDER,
    DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL,
    build_llm_runtime_config,
    decide_cache_eligibility,
    decide_paid_fallback,
    default_openrouter_settings,
    run_deterministic_mock_generation,
    runtime_diagnostics,
    validate_llm_generated_output,
)
from backend.main import app
from backend.models import (
    CacheEntryKind,
    CacheEntryMetadata,
    CacheEntryState,
    CacheInvalidationReason,
    CacheKeyMetadata,
    CacheScope,
    ChatResponse,
    ChatRequest,
    ChatSessionLifecycleState,
    ChatTranscriptExportRequest,
    CompareResponse,
    ComparisonExportRequest,
    EDUCATIONAL_DISCLAIMER,
    EvidenceState,
    ExportResponse,
    FreshnessState,
    GlossaryResponse,
    IngestionJobResponse,
    KnowledgePackBuildResponse,
    KnowledgePackFreshnessInput,
    LlmFallbackTrigger,
    LlmGenerationAttemptMetadata,
    LlmGenerationAttemptStatus,
    LlmGenerationRequestMetadata,
    LlmLiveGateState,
    LlmModelTier,
    LlmProviderKind,
    LlmRuntimeDiagnosticsResponse,
    LlmValidationStatus,
    MetricValue,
    OverviewSectionFreshnessValidation,
    OverviewSectionFreshnessValidationOutcome,
    PreCacheBatchResponse,
    PreCacheJobResponse,
    ProviderDataCategory,
    ProviderKind,
    ProviderResponse,
    ProviderResponseState,
    ProviderSourceUsage,
    SearchResponse,
    SourceChecksumInput,
    SourceUsePolicy,
    TrustMetricCatalogResponse,
    TrustMetricEvent,
    TrustMetricSummary,
    WeeklyNewsContractState,
)
from backend.overview import (
    build_overview_section_freshness_validation,
    generate_asset_overview,
    validate_overview_response,
)
from backend.providers import fetch_mock_provider_response, get_mock_provider_adapters
from backend.retrieval import (
    build_asset_knowledge_pack,
    build_asset_knowledge_pack_result,
    build_comparison_knowledge_pack,
    load_retrieval_fixture_dataset,
)
from backend.safety import find_forbidden_output_phrases
from backend.sources import build_asset_source_drawer_response
from backend.testing import TestClient
from backend.trust_metrics import (
    get_trust_metric_event_catalog,
    summarize_trust_metric_events,
    validate_trust_metric_event,
    validate_trust_metric_events,
)
from backend.weekly_news import (
    build_ai_comprehensive_analysis,
    build_weekly_news_focus_from_pack,
    compute_weekly_news_window,
)


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
    assert data.get("schema_version") == "golden-assets-v2"

    required_technical_stocks = {"AAPL", "MSFT", "NVDA", "TSLA"}
    required_technical_etfs = {"VOO", "SPY", "VTI", "QQQ", "VGT", "SOXX"}
    required_launch_tickers = {
        "VOO",
        "SPY",
        "VTI",
        "IVV",
        "QQQ",
        "IWM",
        "DIA",
        "VGT",
        "XLK",
        "SOXX",
        "SMH",
        "XLF",
        "XLV",
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "BRK.B",
        "JPM",
        "UNH",
    }
    required_common_pairs = {
        ("VOO", "SPY"),
        ("VTI", "VOO"),
        ("QQQ", "VOO"),
        ("QQQ", "VGT"),
        ("VGT", "SOXX"),
        ("AAPL", "MSFT"),
        ("NVDA", "SOXX"),
    }
    required_manifest_stocks = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"}

    technical = data.get("technical_design_golden_assets", {})
    assert required_technical_stocks <= set(technical.get("stocks", []))
    assert required_technical_etfs <= set(technical.get("etfs", []))

    cached_cases = data.get("cached_supported_assets", [])
    eligible_cases = data.get("eligible_not_cached_launch_assets", [])
    unsupported_cases = data.get("unsupported_samples", [])
    unknown_cases = data.get("unknown_samples", [])
    comparison_cases = data.get("common_comparison_pairs", [])

    assert {case["ticker"] for case in cached_cases} == {"AAPL", "VOO", "QQQ"}
    assert {case["ticker"] for case in cached_cases + eligible_cases} == required_launch_tickers
    assert required_launch_tickers - set(ASSETS) == set(ELIGIBLE_NOT_CACHED_ASSETS)
    assert {case["ticker"] for case in eligible_cases} == set(ELIGIBLE_NOT_CACHED_ASSETS)
    assert required_manifest_stocks <= {entry.ticker for entry in load_top500_stock_universe_manifest().entries}
    assert {ticker for ticker in set(ELIGIBLE_NOT_CACHED_ASSETS) if is_top500_manifest_stock(ticker)} == (
        required_manifest_stocks - {"AAPL"}
    )
    assert {case["ticker"] for case in unsupported_cases} >= {"BTC", "TQQQ", "SQQQ"}
    assert {case["ticker"] for case in unknown_cases} >= {"ZZZZ"}
    assert required_common_pairs <= {(case["left"], case["right"]) for case in comparison_cases}

    for case in cached_cases:
        response = client.get("/api/search", params={"q": case["ticker"]})
        assert response.status_code == 200, f"{case['ticker']} search failed"
        result = response.json()["results"][0]
        assert result["support_classification"] == "cached_supported"
        assert result["asset_type"] == case["expected_type"]
        assert result["name"] == case["expected_name"]
        assert result["generated_route"] == case["expected_generated_route"]
        assert result["can_open_generated_page"] is case["expected_can_open_generated_page"]
        assert result["can_answer_chat"] is case["expected_can_answer_chat"]
        assert result["can_compare"] is case["expected_can_compare"]
        assert result["can_request_ingestion"] is case["expected_can_request_ingestion"]

        overview = generate_asset_overview(case["ticker"])
        assert overview.asset.supported is True
        assert len(overview.top_risks) == case["expected_top_risk_count"]
        assert bool(overview.citations) is case["expected_citations"]
        assert bool(overview.source_documents) is case["expected_source_documents"]
        assert bool(overview.freshness.page_last_updated_at) is case["expected_freshness"]
        assert bool(overview.recent_developments) is case["expected_recent_developments_separate"]

        chat = generate_asset_chat(case["ticker"], "What is this asset?")
        assert chat.asset.supported is True
        assert chat.safety_classification.value == "educational"
        assert chat.citations
        assert chat.source_documents

        ingestion = request_ingestion(case["ticker"])
        assert ingestion.job_state.value == "no_ingestion_needed"
        assert ingestion.generated_route == case["expected_generated_route"]

    eligible_expectations = data["eligible_not_cached_expected_capabilities"]
    for case in eligible_cases:
        ticker = case["ticker"]
        metadata = ELIGIBLE_NOT_CACHED_ASSETS[ticker]
        assert metadata["name"] == case["expected_name"]
        assert metadata["asset_type"] == case["expected_type"]
        assert metadata["launch_group"] == case["launch_group"]

        response = client.get("/api/search", params={"q": ticker})
        assert response.status_code == 200, f"{ticker} search failed"
        body = response.json()
        result = body["results"][0]
        assert body["state"]["status"] == "ingestion_needed"
        assert body["state"]["support_classification"] == "eligible_not_cached"
        assert body["state"]["can_request_ingestion"] is True
        assert result["support_classification"] == "eligible_not_cached"
        assert result["asset_type"] == case["expected_type"]
        assert result["name"] == case["expected_name"]
        assert result["generated_route"] == eligible_expectations["expected_generated_route"]
        assert result["can_open_generated_page"] is eligible_expectations["expected_can_open_generated_page"]
        assert result["can_answer_chat"] is eligible_expectations["expected_can_answer_chat"]
        assert result["can_compare"] is eligible_expectations["expected_can_compare"]
        assert result["can_request_ingestion"] is eligible_expectations["expected_can_request_ingestion"]
        assert result["ingestion_request_route"] == f"/api/admin/ingest/{ticker}"

        ingestion = request_ingestion(ticker)
        assert ingestion.ticker == ticker
        assert ingestion.asset_type.value == case["expected_type"]
        assert ingestion.job_type.value == "on_demand"
        assert ingestion.job_id == f"ingest-on-demand-{ticker.lower()}"
        assert ingestion.status_url == f"/api/jobs/ingest-on-demand-{ticker.lower()}"
        assert ingestion.generated_route is None
        assert ingestion.capabilities.can_open_generated_page is False
        assert ingestion.capabilities.can_answer_chat is False
        assert ingestion.capabilities.can_compare is False
        assert ingestion.capabilities.can_request_ingestion is True
        assert get_ingestion_job_status(ingestion.job_id).model_dump(mode="json") == ingestion.model_dump(mode="json")

        provider = fetch_mock_provider_response(ProviderKind.market_reference, ticker, ProviderDataCategory.asset_resolution)
        assert provider.state is ProviderResponseState.eligible_not_cached
        assert provider.asset is not None
        assert provider.asset.ticker == ticker
        assert provider.asset.asset_type.value == case["expected_type"]
        assert provider.asset.supported is True
        assert provider.licensing.export_allowed is False
        _assert_provider_generated_flags_off(provider, f"golden_provider_{ticker}")

        overview = generate_asset_overview(ticker)
        assert overview.asset.supported is False
        assert overview.beginner_summary is None
        assert overview.claims == []
        assert overview.citations == []
        assert overview.source_documents == []
        assert overview.sections == []

        chat = generate_asset_chat(ticker, "What is this asset?")
        assert chat.asset.supported is False
        assert chat.citations == []
        assert chat.source_documents == []

        export = export_asset_page(ticker)
        assert export.export_state.value == "unavailable"
        assert export.sections == []
        assert export.citations == []
        assert export.source_documents == []
        assert export.metadata["generated_asset_output"] is False

    for case in unsupported_cases:
        response = client.get("/api/search", params={"q": case["ticker"]})
        result = response.json()["results"][0]
        assert result["support_classification"] == case["expected_support_classification"]
        assert result["asset_type"] == case["expected_type"]
        assert result["can_open_generated_page"] is False
        assert result["can_answer_chat"] is False
        assert result["can_compare"] is False

    for case in unknown_cases:
        response = client.get("/api/search", params={"q": case["ticker"]})
        result = response.json()["results"][0]
        assert result["support_classification"] == case["expected_support_classification"]
        assert result["asset_type"] == case["expected_type"]
        assert result["generated_route"] is None

    for case in [*comparison_cases, *data.get("local_generated_comparison_pairs", [])]:
        comparison = generate_comparison(case["left"], case["right"])
        if case["expected_state"] == "supported":
            assert comparison.state.status.value == "supported"
            assert comparison.comparison_type != "unavailable"
            assert bool(comparison.key_differences) is case["expected_generated_output"]
            assert bool(comparison.citations) is case.get("expected_citations", False)
            assert bool(comparison.source_documents) is case.get("expected_source_documents", False)
        else:
            assert comparison.comparison_type == "unavailable"
            assert comparison.key_differences == []
            assert comparison.bottom_line_for_beginners is None
            assert comparison.citations == []
            assert comparison.source_documents == []

    data_source = (ROOT / "backend" / "data.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib", "socket", "os.environ", "api_key"]:
        assert forbidden not in data_source


def test_top500_stock_universe_manifest_contract():
    manifest_path = ROOT / "data" / "universes" / "us_common_stocks_top500.current.json"
    assert TOP500_STOCK_UNIVERSE_MANIFEST_PATH == manifest_path
    assert manifest_path.exists(), "Top-500 stock universe manifest must exist at the runtime path"

    manifest = load_top500_stock_universe_manifest()
    assert manifest.schema_version == "top500-us-common-stock-universe-v1"
    assert manifest.local_path == "data/universes/us_common_stocks_top500.current.json"
    assert manifest.production_mirror_env_var == "TOP500_UNIVERSE_MANIFEST_URI"
    assert manifest.rank_limit == 500
    assert manifest.entries
    assert "Operational coverage metadata" in manifest.coverage_purpose
    assert "not an endorsement" in manifest.policy_note
    assert "not a recommendation" in manifest.policy_note
    assert "not a model portfolio" in manifest.policy_note
    assert "runtime source of truth" in manifest.rank_basis
    assert "no live provider query" in manifest.source_provenance

    required_entry_fields = {
        "ticker",
        "name",
        "asset_type",
        "security_type",
        "cik",
        "exchange",
        "rank",
        "rank_basis",
        "source_provenance",
        "snapshot_date",
        "checksum_input",
        "generated_checksum",
        "approval_timestamp",
    }
    required_manifest_backed = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"}
    entries = {entry.ticker: entry for entry in manifest.entries}
    assert required_manifest_backed <= set(entries)
    assert set(OUT_OF_SCOPE_COMMON_STOCKS).isdisjoint(entries)

    for ticker, entry in entries.items():
        payload = entry.model_dump(mode="json")
        assert required_entry_fields <= set(payload), f"{ticker} missing manifest fields"
        assert entry.asset_type == "stock"
        assert entry.security_type == "us_listed_common_stock"
        assert entry.exchange
        assert entry.rank_basis
        assert entry.source_provenance
        assert entry.snapshot_date == manifest.snapshot_date
        assert entry.checksum_input
        assert entry.generated_checksum.startswith("sha256:")
        assert entry.approval_timestamp
        assert top500_stock_universe_entry(ticker) == entry
        assert is_top500_manifest_stock(ticker) is True

    for ticker in ["MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"]:
        metadata = ELIGIBLE_NOT_CACHED_ASSETS[ticker]
        entry = entries[ticker]
        assert metadata["name"] == entry.name
        assert metadata["asset_type"] == "stock"
        assert metadata["exchange"] == entry.exchange
        assert metadata["manifest_id"] == manifest.manifest_id
        assert metadata["manifest_rank"] == str(entry.rank)
        assert metadata["rank_basis"] == entry.rank_basis
        assert metadata["source_provenance"] == entry.source_provenance
        assert metadata["snapshot_date"] == entry.snapshot_date

    out_of_scope = client.get("/api/search", params={"q": "GME"}).json()
    assert out_of_scope["state"]["status"] == "out_of_scope"
    assert out_of_scope["results"][0]["support_classification"] == "out_of_scope"
    assert out_of_scope["results"][0]["eligible_for_ingestion"] is False
    assert out_of_scope["results"][0]["generated_route"] is None

    data_source = (ROOT / "backend" / "data.py").read_text(encoding="utf-8")
    search_source = (ROOT / "backend" / "search.py").read_text(encoding="utf-8")
    provider_source = (ROOT / "backend" / "providers.py").read_text(encoding="utf-8")
    for source in [data_source, search_source, provider_source]:
        for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
            assert forbidden not in source

    manifest_text = manifest_path.read_text(encoding="utf-8").lower()
    for forbidden in ["should buy", "should sell", "should hold", "price target", "personalized allocation"]:
        assert forbidden not in manifest_text


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

    required_states = {"supported", "ambiguous", "unsupported", "out_of_scope", "unknown", "ingestion_needed"}
    found_states = {case.get("expected_state") for case in cases}
    missing_states = required_states - found_states
    assert not missing_states, f"Missing search states: {missing_states}"

    required_classifications = {
        "cached_supported",
        "recognized_unsupported",
        "out_of_scope",
        "unknown",
        "eligible_not_cached",
    }
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
        validated = SearchResponse.model_validate(body)
        state = body["state"]
        results = body["results"]

        assert validated.query == case["query"]
        assert len(validated.results) == len(results)

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

        expected_blocked_explanation = case.get("expected_blocked_explanation")
        if expected_blocked_explanation:
            explanation = state["blocked_explanation"]
            assert explanation is not None, f"{case['id']} should expose blocked explanation metadata"
            assert explanation["schema_version"] == "search-blocked-explanation-v1"
            assert explanation["status"] == expected_blocked_explanation["status"]
            assert explanation["support_classification"] == expected_blocked_explanation["support_classification"]
            assert explanation["explanation_kind"] == "scope_blocked_search_result"
            assert explanation["explanation_category"] == expected_blocked_explanation["explanation_category"]
            assert "Supported MVP coverage" in explanation["supported_v1_scope"]
            assert explanation["blocked_capabilities"]["can_open_generated_page"] is False
            assert explanation["blocked_capabilities"]["can_answer_chat"] is False
            assert explanation["blocked_capabilities"]["can_compare"] is False
            assert explanation["blocked_capabilities"]["can_request_ingestion"] is False
            assert explanation["ingestion_eligible"] is False
            assert explanation["ingestion_request_route"] is None
            assert explanation["diagnostics"]["deterministic_contract"] is True
            assert explanation["diagnostics"]["generated_asset_analysis"] is False
            assert explanation["diagnostics"]["includes_citations"] is False
            assert explanation["diagnostics"]["includes_source_documents"] is False
            assert explanation["diagnostics"]["includes_freshness"] is False
            assert explanation["diagnostics"]["uses_live_calls"] is False
        else:
            assert state["blocked_explanation"] is None

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
                assert result["blocked_explanation"] is None
            elif result["support_classification"] == "eligible_not_cached":
                assert result["generated_route"] is None
                assert result["can_open_generated_page"] is False
                assert result["can_answer_chat"] is False
                assert result["can_compare"] is False
                assert result["can_request_ingestion"] is True
                assert result["ingestion_request_route"] == f"/api/admin/ingest/{result['ticker']}"
                assert result["blocked_explanation"] is None
            else:
                assert result["generated_route"] is None
                assert result["can_open_generated_page"] is False
                assert result["can_answer_chat"] is False
                assert result["can_compare"] is False
                assert result["can_request_ingestion"] is False
                assert result["ingestion_request_route"] is None
                if expected_blocked_explanation and len(results) == 1:
                    assert result["blocked_explanation"] == state["blocked_explanation"]
                else:
                    assert result["blocked_explanation"] is None

    search_source = (ROOT / "backend" / "search.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    models_source = (ROOT / "backend" / "models.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in search_source
        assert forbidden not in main_source
    for marker in [
        "search-blocked-explanation-v1",
        "scope_blocked_search_result",
        "top500_manifest_scope",
        "Supported MVP coverage is limited to U.S.-listed common stocks",
    ]:
        assert marker in search_source or marker in models_source
        assert not find_forbidden_output_phrases(marker)


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


def test_pre_cache_cases():
    data = load_yaml("pre_cache_eval_cases.yaml")
    required_models = set(data.get("required_models", []))
    missing_models = {name for name in required_models if not hasattr(models, name)}
    assert not missing_models, f"Missing pre-cache contract models: {missing_models}"

    required_helpers = {
        "request_launch_universe_pre_cache",
        "request_pre_cache_for_asset",
        "get_pre_cache_job_status",
    }
    missing_helpers = {name for name in required_helpers if name not in globals()}
    assert not missing_helpers, f"Missing pre-cache helper functions: {missing_helpers}"

    batch = request_launch_universe_pre_cache()
    endpoint_response = client.post("/api/admin/pre-cache/launch-universe")
    status_response = client.get("/api/admin/pre-cache/launch-universe")
    assert endpoint_response.status_code == 200
    assert status_response.status_code == 200
    validated = PreCacheBatchResponse.model_validate(batch.model_dump(mode="json"))
    assert endpoint_response.json() == validated.model_dump(mode="json")
    assert status_response.json() == validated.model_dump(mode="json")

    expected_batch_id = data["expected_batch_id"]
    assert validated.batch_id == expected_batch_id
    assert validated.status_url == data["expected_status_url"]
    assert validated.deterministic is True
    assert validated.no_live_external_calls is True
    assert validated.summary.total_launch_assets == len(validated.jobs)
    assert validated.summary.total_launch_assets == len({*ASSETS, *ELIGIBLE_NOT_CACHED_ASSETS})
    assert validated.summary.cached_or_already_available_assets == len(ASSETS)
    assert validated.summary.generated_output_available_assets == len(ASSETS)

    jobs_by_ticker = {job.ticker: job for job in validated.jobs}
    assert set(jobs_by_ticker) == {*ASSETS, *ELIGIBLE_NOT_CACHED_ASSETS}
    for ticker, expected_route in data["cached_generated_routes"].items():
        job = jobs_by_ticker[ticker]
        assert job.job_id == f"pre-cache-launch-{ticker.lower()}"
        assert job.job_state.value == "succeeded"
        assert job.worker_status.value == "succeeded"
        assert job.generated_route == expected_route
        assert job.generated_output_available is True
        assert job.capabilities.can_open_generated_page is True
        assert job.capabilities.can_answer_chat is True
        assert job.capabilities.can_compare is True
        assert get_pre_cache_job_status(job.job_id).model_dump(mode="json") == job.model_dump(mode="json")

    for ticker in ELIGIBLE_NOT_CACHED_ASSETS:
        job = jobs_by_ticker[ticker]
        assert job.job_type.value == "pre_cache"
        assert job.launch_group == ELIGIBLE_NOT_CACHED_ASSETS[ticker]["launch_group"]
        assert job.generated_route is None
        assert job.generated_output_available is False
        assert job.citation_ids == []
        assert job.source_document_ids == []
        assert job.capabilities.can_open_generated_page is False
        assert job.capabilities.can_answer_chat is False
        assert job.capabilities.can_compare is False

        overview = generate_asset_overview(ticker)
        chat = generate_asset_chat(ticker, "What is this asset?")
        export = export_asset_page(ticker)
        assert overview.beginner_summary is None
        assert overview.citations == []
        assert overview.source_documents == []
        assert chat.citations == []
        assert chat.source_documents == []
        assert export.citations == []
        assert export.source_documents == []

    required_status_states = set(data.get("required_status_states", []))
    found_status_states = set()
    for case in data.get("status_cases", []):
        if case["lookup"] == "status":
            response = client.get(f"/api/admin/pre-cache/jobs/{case['job_id']}")
            direct = get_pre_cache_job_status(case["job_id"])
        elif case["lookup"] == "asset":
            response = client.post(f"/api/admin/pre-cache/{case['ticker']}")
            direct = request_pre_cache_for_asset(case["ticker"])
        else:
            raise AssertionError(f"Unknown pre-cache lookup: {case['lookup']}")

        assert response.status_code == 200, f"{case['id']} pre-cache endpoint failed"
        validated_job = PreCacheJobResponse.model_validate(response.json())
        assert validated_job.model_dump(mode="json") == direct.model_dump(mode="json")
        assert validated_job.ticker == case["expected_ticker"]
        assert validated_job.asset_type.value == case["expected_asset_type"]
        assert validated_job.job_state.value == case["expected_job_state"]
        assert (validated_job.worker_status.value if validated_job.worker_status else None) == case["expected_worker_status"]
        assert validated_job.generated_route == case["expected_generated_route"]
        assert validated_job.generated_output_available is case["expected_generated_output_available"]
        found_status_states.add(validated_job.job_state.value)

        if not validated_job.generated_output_available:
            assert validated_job.generated_route is None
            assert validated_job.citation_ids == []
            assert validated_job.source_document_ids == []
            assert validated_job.capabilities.can_open_generated_page is False
            assert validated_job.capabilities.can_answer_chat is False
            assert validated_job.capabilities.can_compare is False

    missing_states = required_status_states - found_status_states
    assert not missing_states, f"Missing pre-cache status states: {missing_states}"

    cache_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.pre_cache_job,
            scope=CacheScope.job,
            asset_ticker="SPY",
            mode_or_output_type="launch-universe",
            schema_version="pre-cache-job-v1",
            source_freshness_state=FreshnessState.unavailable,
            input_freshness_hash=expected_batch_id,
        )
    )
    blocked = evaluate_cache_revalidation(None, cache_key, input_state=CacheEntryState.unavailable)
    assert "pre-cache-job" in cache_key
    assert blocked.reusable is False

    ingestion_source = (ROOT / "backend" / "ingestion.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in data.get("forbidden_live_call_imports", []):
        assert forbidden not in ingestion_source
        assert forbidden not in main_source


def test_trust_metrics_cases():
    data = load_yaml("trust_metrics_eval_cases.yaml")
    required_models = set(data.get("required_models", []))
    missing_models = {name for name in required_models if not hasattr(models, name)}
    assert not missing_models, f"Missing trust metrics contract models: {missing_models}"

    required_helpers = set(data.get("required_helpers", []))
    missing_helpers = {name for name in required_helpers if name not in globals()}
    assert not missing_helpers, f"Missing trust metrics helper functions: {missing_helpers}"

    catalog = get_trust_metric_event_catalog()
    validated_catalog = TrustMetricCatalogResponse.model_validate(catalog.model_dump(mode="json"))
    assert validated_catalog.schema_version == data["schema_version"].replace("evals", "event").replace("-v1", "-v1")
    assert validated_catalog.validation_only is True
    assert validated_catalog.persistence_enabled is False
    assert validated_catalog.external_analytics_enabled is False
    assert validated_catalog.no_live_external_calls is True

    product_events = {event.event_type.value for event in validated_catalog.product_events}
    trust_events = {event.event_type.value for event in validated_catalog.trust_events}
    assert set(data.get("required_product_events", [])) <= product_events
    assert set(data.get("required_trust_events", [])) <= trust_events
    assert set(data.get("required_forbidden_fields", [])) <= set(validated_catalog.forbidden_field_names)

    accepted = validate_trust_metric_event(
        {
            "event_type": "citation_coverage",
            "workflow_area": "citation",
            "asset_ticker": "voo",
            "generated_output_available": True,
            "output_metadata": {
                "output_kind": "asset_page",
                "schema_valid": True,
                "citation_coverage_rate": 1,
                "citation_ids": ["c_voo_profile"],
                "source_document_ids": ["src_voo_fact_sheet_fixture"],
                "freshness_state": "fresh",
                "latency_ms": 10,
            },
        }
    )
    assert accepted.validation_status.value == "accepted"
    assert accepted.normalized_event is not None
    assert accepted.normalized_event.asset_ticker == "VOO"
    assert accepted.normalized_event.asset_support_state.value == "cached_supported"
    assert TrustMetricEvent.model_validate(accepted.normalized_event.model_dump(mode="json"))

    rejected_privacy = validate_trust_metric_event(
        {"event_type": "chat_answer_outcome", "workflow_area": "chat", "asset_ticker": "VOO", "question": "raw text"}
    )
    rejected_state = validate_trust_metric_event(
        {
            "event_type": "asset_page_view",
            "workflow_area": "asset_page",
            "asset_ticker": "SPY",
            "generated_output_available": True,
        }
    )
    rejected_freshness = validate_trust_metric_event(
        {"event_type": "freshness_accuracy", "workflow_area": "freshness", "asset_ticker": "VOO"}
    )
    for rejected in [rejected_privacy, rejected_state, rejected_freshness]:
        assert rejected.validation_status.value == "rejected"
        assert rejected.rejection_reasons
        assert rejected.normalized_event is None

    batch = validate_trust_metric_events(
        [
            {"event_type": "search_success", "workflow_area": "search", "asset_ticker": "VOO", "metadata": {"latency_ms": 20}},
            {"event_type": "chat_safety_redirect", "workflow_area": "chat", "asset_ticker": "VOO"},
            {"event_type": "source_retrieval_failure", "workflow_area": "retrieval", "metadata": {"freshness_state": "unavailable"}},
            {"event_type": "chat_answer_outcome", "workflow_area": "chat", "answer": "raw text"},
        ]
    )
    accepted_events = [event.normalized_event for event in batch.events if event.normalized_event is not None]
    summary = summarize_trust_metric_events(accepted_events)
    validated_summary = TrustMetricSummary.model_validate(summary.model_dump(mode="json"))
    assert batch.accepted_count == 3
    assert batch.rejected_count == 1
    assert batch.summary == validated_summary
    assert summary.product_metric_counts["search_success"] == 1
    assert summary.product_metric_counts["chat_safety_redirect"] == 1
    assert summary.trust_metric_counts["source_retrieval_failure"] == 1
    assert summary.rates["safety_redirect_rate"] == 0.3333
    assert summary.latency_ms["average"] == 20

    for route in data.get("required_api_routes", []):
        assert route in (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    trust_metrics_source = (ROOT / "backend" / "trust_metrics.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in data.get("forbidden_imports", []):
        assert forbidden not in trust_metrics_source
        if forbidden != "os.environ":
            assert forbidden not in main_source


def test_knowledge_pack_cases():
    data = load_yaml("knowledge_pack_eval_cases.yaml")
    required_models = set(data.get("required_models", []))
    missing_models = {name for name in required_models if not hasattr(models, name)}
    assert not missing_models, f"Missing knowledge-pack contract models: {missing_models}"

    required_helpers = set(data.get("required_helpers", []))
    missing_helpers = {name for name in required_helpers if name not in globals()}
    assert not missing_helpers, f"Missing knowledge-pack helper functions: {missing_helpers}"

    required_sections = set(data.get("required_section_freshness_ids", []))
    required_cached_metadata = set(data.get("required_cached_metadata", []))

    for case in data.get("supported_cached_cases", []):
        result = build_asset_knowledge_pack_result(case["ticker"])
        endpoint_response = client.get(f"/api/assets/{case['ticker']}/knowledge-pack")
        repeated = build_asset_knowledge_pack_result(case["ticker"].lower())
        pack = build_asset_knowledge_pack(case["ticker"])
        expected_input = build_knowledge_pack_freshness_input(pack, section_freshness_labels=result.section_freshness)
        expected_hash = compute_knowledge_pack_freshness_hash(expected_input)

        assert endpoint_response.status_code == 200, f"{case['id']} endpoint failed"
        validated = KnowledgePackBuildResponse.model_validate(endpoint_response.json())
        assert validated.model_dump(mode="json") == result.model_dump(mode="json")
        assert repeated.model_dump(mode="json") == result.model_dump(mode="json")

        assert result.schema_version == "asset-knowledge-pack-build-v1"
        assert result.ticker == case["ticker"]
        assert result.asset.ticker == case["ticker"]
        assert result.asset.asset_type.value == case["expected_asset_type"]
        assert result.pack_id == case["expected_pack_id"]
        assert result.build_state.value == "available"
        assert result.generated_output_available is True
        assert result.generated_route == case["expected_generated_route"]
        assert result.capabilities.can_open_generated_page is True
        assert result.capabilities.can_answer_chat is True
        assert result.capabilities.can_compare is True
        assert result.capabilities.can_request_ingestion is False
        assert result.reusable_generated_output_cache_hit is False
        assert result.no_live_external_calls is True
        assert result.exports_full_source_documents is False

        assert result.knowledge_pack_freshness_hash == expected_hash
        assert result.cache_key is not None and "knowledge-pack" in result.cache_key
        assert result.cache_revalidation is not None
        assert result.cache_revalidation.state is CacheEntryState.miss
        assert result.cache_revalidation.expected_freshness_hash == expected_hash
        assert result.source_checksums == expected_input.source_checksums

        section_ids = {label.section_id for label in result.section_freshness}
        assert required_sections <= section_ids
        assert required_cached_metadata <= set(KnowledgePackBuildResponse.model_fields)
        assert set(result.source_document_ids) == {source.source_document_id for source in pack.source_documents}
        assert result.counts.source_document_count == len(result.source_documents)
        assert result.counts.citation_count == len(result.citation_ids)
        assert result.counts.normalized_fact_count == len(result.normalized_facts)
        assert result.counts.source_chunk_count == len(result.source_chunks)
        assert result.counts.recent_development_count == len(result.recent_developments)
        assert result.counts.evidence_gap_count == len(result.evidence_gaps)
        assert {source.asset_ticker for source in result.source_documents} == {case["ticker"]}
        assert {fact.asset_ticker for fact in result.normalized_facts} == {case["ticker"]}
        assert {chunk.asset_ticker for chunk in result.source_chunks} == {case["ticker"]}
        assert {recent.asset_ticker for recent in result.recent_developments} == {case["ticker"]}
        assert all(fact.source_document_id in result.source_document_ids for fact in result.normalized_facts)
        assert all(chunk.source_document_id in result.source_document_ids for chunk in result.source_chunks)
        assert all(recent.source_document_id in result.source_document_ids for recent in result.recent_developments)
        assert any(citation_id.startswith("c_fact_") for citation_id in result.citation_ids)
        assert any(citation_id.startswith("c_recent_") for citation_id in result.citation_ids)

        dumped = result.model_dump(mode="json")
        for forbidden in data.get("forbidden_raw_export_fields", []):
            assert forbidden not in dumped, f"{case['id']} exported raw field {forbidden}"
        assert "Apple designs, manufactures" not in str(dumped)
        assert "VOO seeks to track" not in str(dumped)
        assert "QQQ tracks the Nasdaq-100" not in str(dumped)

    for case in data.get("non_generated_cases", []):
        result = build_asset_knowledge_pack_result(case["ticker"])
        endpoint_response = client.get(f"/api/assets/{case['ticker']}/knowledge-pack")
        assert endpoint_response.status_code == 200, f"{case['id']} endpoint failed"
        validated = KnowledgePackBuildResponse.model_validate(endpoint_response.json())
        assert validated.model_dump(mode="json") == result.model_dump(mode="json")

        assert result.asset.asset_type.value == case["expected_asset_type"]
        assert result.build_state.value == case["expected_build_state"]
        assert result.generated_output_available is False
        assert result.reusable_generated_output_cache_hit is False
        assert result.generated_route is None
        assert result.capabilities.can_open_generated_page is False
        assert result.capabilities.can_answer_chat is False
        assert result.capabilities.can_compare is False
        assert result.capabilities.can_request_ingestion is case["expected_can_request_ingestion"]
        assert result.source_document_ids == []
        assert result.citation_ids == []
        assert result.source_documents == []
        assert result.normalized_facts == []
        assert result.source_chunks == []
        assert result.recent_developments == []
        assert result.source_checksums == []
        assert result.knowledge_pack_freshness_hash is None
        assert result.counts.source_document_count == 0
        assert result.counts.citation_count == 0
        assert result.counts.normalized_fact_count == 0
        assert result.counts.source_chunk_count == 0
        assert result.counts.recent_development_count == 0
        assert result.counts.evidence_gap_count == 1
        assert result.cache_revalidation is not None
        assert result.cache_revalidation.state.value == case["expected_cache_state"]
        assert result.cache_revalidation.reusable is False

        overview = generate_asset_overview(case["ticker"])
        chat = generate_asset_chat(case["ticker"], "What is this asset?")
        comparison = generate_comparison("VOO", case["ticker"])
        assert overview.citations == []
        assert overview.source_documents == []
        assert chat.citations == []
        assert chat.source_documents == []
        assert comparison.citations == []
        assert comparison.source_documents == []

    retrieval_source = (ROOT / "backend" / "retrieval.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in data.get("forbidden_live_call_imports", []):
        assert forbidden not in retrieval_source
        if forbidden != "os.environ":
            assert forbidden not in main_source


def test_provider_cases():
    data = load_yaml("provider_eval_cases.yaml")
    adapters = get_mock_provider_adapters()
    required_provider_kinds = {ProviderKind(kind) for kind in data.get("required_provider_kinds", [])}
    assert required_provider_kinds <= set(adapters), f"Missing provider adapters: {required_provider_kinds - set(adapters)}"
    llm_contract = data.get("llm_runtime_provider_contract", {})
    assert llm_contract["default_provider_kind"] == "mock"
    assert llm_contract["live_provider_kind"] == "openrouter"
    assert llm_contract["requires_sanitized_key_presence_flag"] is True
    assert llm_contract["no_secret_values_allowed"] is True
    assert llm_contract["default_live_network_calls_allowed"] is False
    assert llm_contract["free_model_order"] == list(DEFAULT_OPENROUTER_FREE_MODEL_ORDER)
    assert llm_contract["paid_fallback_model"] == DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL

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


def test_cache_cases():
    data = load_yaml("cache_eval_cases.yaml")
    required_models = set(data.get("required_models", []))
    missing_models = {name for name in required_models if not hasattr(models, name)}
    assert not missing_models, f"Missing cache contract models: {missing_models}"

    required_helpers = set(data.get("required_helpers", []))
    missing_helpers = {name for name in required_helpers if name not in globals()}
    assert not missing_helpers, f"Missing cache helper functions: {missing_helpers}"

    required_states = set(data.get("required_revalidation_states", []))
    actual_states = {state.value for state in CacheEntryState}
    missing_states = required_states - actual_states
    assert not missing_states, f"Missing cache revalidation states: {missing_states}"

    required_reasons = set(data.get("required_invalidation_reasons", []))
    actual_reasons = {reason.value for reason in CacheInvalidationReason}
    missing_reasons = required_reasons - actual_reasons
    assert not missing_reasons, f"Missing cache invalidation reasons: {missing_reasons}"

    source_fields = set(SourceChecksumInput.model_fields)
    missing_source_fields = set(data.get("source_checksum_required_inputs", [])) - source_fields
    assert not missing_source_fields, f"Missing source checksum inputs: {missing_source_fields}"

    knowledge_fields = set(KnowledgePackFreshnessInput.model_fields)
    missing_knowledge_fields = set(data.get("knowledge_pack_required_inputs", [])) - knowledge_fields
    assert not missing_knowledge_fields, f"Missing knowledge-pack freshness inputs: {missing_knowledge_fields}"

    generated_fields = set(models.GeneratedOutputFreshnessInput.model_fields)
    missing_generated_fields = set(data.get("generated_output_required_inputs", [])) - generated_fields
    assert not missing_generated_fields, f"Missing generated-output freshness inputs: {missing_generated_fields}"

    voo_pack = build_asset_knowledge_pack("VOO")
    knowledge_input = build_knowledge_pack_freshness_input(voo_pack)
    knowledge_hash = compute_knowledge_pack_freshness_hash(knowledge_input)
    generated_input = build_generated_output_freshness_input(
        output_identity="asset:VOO",
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        prompt_version="asset-page-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=knowledge_input,
    )
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    changed_prompt_hash = compute_generated_output_freshness_hash(
        generated_input.model_copy(update={"prompt_version": "asset-page-prompt-v2"})
    )
    assert generated_hash != changed_prompt_hash

    reordered_knowledge = KnowledgePackFreshnessInput(
        **{
            **knowledge_input.model_dump(mode="json"),
            "source_checksums": list(reversed(knowledge_input.source_checksums)),
            "canonical_facts": list(reversed(knowledge_input.canonical_facts)),
            "recent_events": list(reversed(knowledge_input.recent_events)),
            "evidence_gaps": list(reversed(knowledge_input.evidence_gaps)),
            "section_freshness_labels": list(reversed(knowledge_input.section_freshness_labels)),
        }
    )
    assert knowledge_hash == compute_knowledge_pack_freshness_hash(reordered_knowledge)

    key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.asset_page,
            scope=CacheScope.asset,
            asset_ticker="VOO",
            mode_or_output_type="beginner",
            schema_version="asset-page-v1",
            source_freshness_state=FreshnessState.fresh,
            prompt_version="asset-page-prompt-v1",
            model_name="deterministic-fixture-model",
            input_freshness_hash=generated_hash,
        )
    )
    assert "asset-voo" in key
    assert "prompt-asset-page-prompt-v1" in key
    assert "model-deterministic-fixture-model" in key

    comparison_pack = build_comparison_knowledge_pack("VOO", "QQQ")
    comparison_input = build_comparison_pack_freshness_input(comparison_pack)
    assert comparison_input.comparison_left_ticker == "VOO"
    assert comparison_input.comparison_right_ticker == "QQQ"
    forward_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            comparison_left_ticker="VOO",
            comparison_right_ticker="QQQ",
            pack_identity=comparison_input.pack_identity,
            mode_or_output_type="beginner",
            schema_version="comparison-v1",
            source_freshness_state=FreshnessState.fresh,
        )
    )
    reverse_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.comparison,
            scope=CacheScope.comparison,
            comparison_left_ticker="QQQ",
            comparison_right_ticker="VOO",
            pack_identity=comparison_input.pack_identity,
            mode_or_output_type="beginner",
            schema_version="comparison-v1",
            source_freshness_state=FreshnessState.fresh,
        )
    )
    assert forward_key != reverse_key
    assert "comparison-voo-to-qqq" in forward_key
    assert "comparison-qqq-to-voo" in reverse_key

    reusable_entry = CacheEntryMetadata(
        cache_key=key,
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        generated_output_freshness_hash=generated_hash,
        source_document_ids=["src_voo_fact_sheet_fixture"],
        citation_ids=["c_voo_profile"],
        source_freshness_states={"src_voo_fact_sheet_fixture": FreshnessState.fresh},
        section_freshness_labels={"top_risks": FreshnessState.fresh},
        cache_allowed=True,
    )
    assert evaluate_cache_revalidation(reusable_entry, key, generated_hash).state is CacheEntryState.hit
    assert evaluate_cache_revalidation(reusable_entry, key, changed_prompt_hash).state is CacheEntryState.hash_mismatch
    assert evaluate_cache_revalidation(None, key).state is CacheEntryState.miss
    assert evaluate_cache_revalidation(None, key, input_state=ProviderResponseState.unsupported).state is CacheEntryState.unsupported
    assert evaluate_cache_revalidation(None, key, cache_allowed=False).state is CacheEntryState.permission_limited

    case_states = {case["expected_state"] for case in data.get("cases", []) if "expected_state" in case}
    assert {"permission_limited", "unsupported", "hash_mismatch"} <= case_states

    cache_source = (ROOT / "backend" / "cache.py").read_text(encoding="utf-8")
    for forbidden in data.get("forbidden_cache_imports", []):
        assert forbidden not in cache_source


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
    required_validation_fields = {
        "section_id",
        "section_type",
        "displayed_freshness_state",
        "displayed_evidence_state",
        "validated_freshness_state",
        "validation_outcome",
        "citation_bindings",
        "source_bindings",
        "knowledge_pack_freshness_inputs",
        "diagnostics",
    }
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
        freshness_validation = {item.section_id: item for item in overview.section_freshness_validation}
        assert OverviewSectionFreshnessValidationOutcome.validated in set(OverviewSectionFreshnessValidationOutcome)
        assert required_validation_fields <= set(OverviewSectionFreshnessValidation.model_fields)
        assert build_overview_section_freshness_validation(overview=overview, pack=pack) == overview.section_freshness_validation
        assert {section.section_id for section in overview.sections} <= set(freshness_validation)
        assert {"weekly_news_focus", "ai_comprehensive_analysis"} <= set(freshness_validation)
        assert all(item.diagnostics.derived_from_existing_local_evidence_only for item in freshness_validation.values())
        assert all(item.diagnostics.used_knowledge_pack_freshness_inputs for item in freshness_validation.values())
        assert all(item.diagnostics.no_live_external_calls for item in freshness_validation.values())
        assert all(item.diagnostics.same_asset_citation_bindings_only for item in freshness_validation.values())
        assert all(item.diagnostics.same_asset_source_bindings_only for item in freshness_validation.values())
        assert all(
            binding.asset_ticker == ticker
            for item in freshness_validation.values()
            for binding in [*item.citation_bindings, *item.source_bindings]
        )
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
            expected_cost_freshness = FreshnessState.stale if ticker == "VOO" else FreshnessState.unavailable
            assert freshness_validation["cost_trading_context"].displayed_freshness_state is expected_cost_freshness
            assert "holdings_exposure_detail" in {item.item_id for item in sections["holdings_exposure"].items}
            assert "construction_methodology" in {item.item_id for item in sections["construction_methodology"].items}
            assert "trading_data_limitation" in {item.item_id for item in sections["cost_trading_context"].items}
            assert sections["recent_developments"].evidence_state is EvidenceState.no_major_recent_development
            assert sections["recent_developments"].items[0].retrieved_at
            assert len(sections["etf_specific_risks"].items) == 3
            assert freshness_validation["weekly_news_focus"].displayed_evidence_state is EvidenceState.no_high_signal
            assert freshness_validation["ai_comprehensive_analysis"].displayed_evidence_state is EvidenceState.insufficient_evidence
            if ticker == "VOO":
                mutated = overview.model_copy(
                    update={
                        "sections": [
                            section.model_copy(update={"freshness_state": FreshnessState.fresh})
                            if section.section_id == "cost_trading_context"
                            else section
                            for section in overview.sections
                        ]
                    }
                )
                mismatched = {
                    item.section_id: item
                    for item in build_overview_section_freshness_validation(overview=mutated, pack=pack)
                }
                assert mismatched["cost_trading_context"].validation_outcome is OverviewSectionFreshnessValidationOutcome.mismatch
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
        assert overview.section_freshness_validation == []
        assert overview.citations == []
        assert overview.source_documents == []
        assert overview.sections == []

    overview_source = (ROOT / "backend" / "overview.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in overview_source


def test_source_drawer_cases():
    data = load_yaml("source_drawer_eval_cases.yaml")
    assert data.get("schema_version") == "source-drawer-evals-v1"

    missing_models = {name for name in data["required_models"] if not hasattr(models, name)}
    assert not missing_models, f"Missing source drawer contract models: {missing_models}"
    assert "build_asset_source_drawer_response" in data["required_helpers"]
    assert callable(build_asset_source_drawer_response)

    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    sources_source = (ROOT / "backend" / "sources.py").read_text(encoding="utf-8")
    assert "build_asset_source_drawer_response" in main_source
    assert "@app.get(\"/api/assets/{ticker}/sources\"" in main_source
    for forbidden in data["forbidden_static_markers"]:
        assert forbidden not in sources_source
        if forbidden not in {"OPENROUTER_API_KEY"}:
            assert forbidden not in main_source

    for ticker in data["supported_cached_assets"]:
        overview = generate_asset_overview(ticker)
        pack = build_asset_knowledge_pack(ticker)
        response = build_asset_source_drawer_response(ticker)
        validated = models.SourcesResponse.model_validate(response.model_dump(mode="json"))
        citation_ids = {citation.citation_id for citation in overview.citations}
        source_ids = {source.source_document_id for source in overview.source_documents}
        pack_source_ids = {source.source_document_id for source in pack.source_documents}
        binding_citation_ids = {binding.citation_id for binding in validated.citation_bindings}
        binding_source_ids = {binding.source_document_id for binding in validated.citation_bindings}

        assert validated.schema_version == "asset-source-drawer-v1"
        assert validated.asset.ticker == ticker
        assert validated.selected_asset and validated.selected_asset.ticker == ticker
        assert validated.drawer_state.value == "available"
        assert validated.sources
        assert validated.source_groups
        assert validated.citation_bindings
        assert validated.related_claims
        assert validated.section_references
        assert binding_citation_ids <= citation_ids
        assert binding_source_ids <= source_ids
        assert binding_source_ids <= pack_source_ids
        assert all(binding.asset_ticker == ticker for binding in validated.citation_bindings)
        assert all(group.title and group.publisher and group.source_type and group.url for group in validated.source_groups)
        assert all(group.published_at or group.as_of_date for group in validated.source_groups)
        assert all(group.retrieved_at for group in validated.source_groups)
        assert all(group.allowlist_status.value == "allowed" for group in validated.source_groups)
        assert all(
            group.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
            for group in validated.source_groups
        )
        assert all(group.permitted_operations.can_export_full_text is False for group in validated.source_groups)
        assert all(group.allowed_excerpts for group in validated.source_groups if group.citation_ids)
        assert any(reference.evidence_state in {EvidenceState.mixed, EvidenceState.unavailable, EvidenceState.no_major_recent_development, EvidenceState.insufficient_evidence} for reference in validated.section_references)
        assert any(reference.timely_context for reference in validated.section_references)
        assert validated.diagnostics.no_live_external_calls is True
        assert validated.diagnostics.generated_output_created is False
        serialized = str(validated.model_dump(mode="json")).lower()
        for phrase in data["forbidden_advice_phrases"]:
            assert phrase not in serialized

        filtered = build_asset_source_drawer_response(ticker, citation_id=validated.citation_bindings[0].citation_id)
        assert {binding.citation_id for binding in filtered.citation_bindings} == {validated.citation_bindings[0].citation_id}
        assert filtered.source_groups

    for case in data["non_generated_cases"]:
        response = build_asset_source_drawer_response(case["ticker"])
        assert response.drawer_state.value == case["expected_drawer_state"]
        assert response.sources == []
        assert response.source_groups == []
        assert response.citation_bindings == []
        assert response.related_claims == []
        assert response.section_references == []
        assert response.diagnostics.unavailable_reasons
        assert response.diagnostics.unsupported_generated_output_suppressed is True


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


def test_comparison_evidence_availability_contract():
    data = load_yaml("comparison_evidence_eval_cases.yaml")
    assert data.get("schema_version") == "comparison-evidence-evals-v1"

    for model_name in data["required_models"]:
        assert hasattr(models, model_name), f"Missing comparison evidence model: {model_name}"

    comparison_source = (ROOT / "backend" / "comparison.py").read_text(encoding="utf-8")
    models_source = (ROOT / "backend" / "models.py").read_text(encoding="utf-8")
    for helper_name in data["required_helpers"]:
        assert helper_name in comparison_source, f"Missing comparison evidence helper: {helper_name}"

    for state in data["required_non_generated_states"]:
        assert f'{state} = "{state}"' in models_source

    required_dimensions = set(data["required_dimensions"])
    for case in data["supported_pairs"]:
        comparison = generate_comparison(case["left"], case["right"])
        validated = CompareResponse.model_validate(comparison.model_dump(mode="json"))
        availability = validated.evidence_availability
        assert availability is not None
        assert availability.schema_version == "comparison-evidence-availability-v1"
        assert availability.availability_state.value == case["expected_state"]
        assert availability.left_asset.ticker == case["left"]
        assert availability.right_asset.ticker == case["right"]
        assert set(availability.required_dimensions) == required_dimensions
        assert {dimension.dimension for dimension in availability.required_evidence_dimensions} == required_dimensions
        assert all(dimension.availability_state.value == "available" for dimension in availability.required_evidence_dimensions)
        assert availability.evidence_items
        assert availability.claim_bindings
        assert availability.citation_bindings
        assert availability.source_references
        assert {binding.side_role.value for binding in availability.citation_bindings} >= {
            "left_side_support",
            "right_side_support",
        }
        assert {binding.side_role.value for binding in availability.claim_bindings} == {"shared_comparison_support"}
        citation_ids = {citation.citation_id for citation in validated.citations}
        source_ids = {source.source_document_id for source in validated.source_documents}
        assert {binding.citation_id for binding in availability.citation_bindings} <= citation_ids
        assert {binding.source_document_id for binding in availability.citation_bindings} <= source_ids
        assert {reference.source_document_id for reference in availability.source_references} <= source_ids
        assert {reference.asset_ticker for reference in availability.source_references} <= {case["left"], case["right"]}
        assert all(reference.allowlist_status.value == "allowed" for reference in availability.source_references)
        assert all(
            reference.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
            for reference in availability.source_references
        )
        assert all(
            reference.permitted_operations.can_support_generated_output
            and reference.permitted_operations.can_support_citations
            for reference in availability.source_references
        )
        assert all(binding.supports_generated_claim is True for binding in availability.citation_bindings)
        assert all(item.freshness_state.value == "fresh" for item in availability.evidence_items)
        assert availability.diagnostics.no_live_external_calls is True
        assert availability.diagnostics.live_provider_calls_attempted is False
        assert availability.diagnostics.live_llm_calls_attempted is False
        assert availability.diagnostics.availability_contract_created_generated_output is False
        assert availability.diagnostics.no_new_generated_output is True
        serialized = str(availability.model_dump(mode="json")).lower()
        for forbidden in ["supporting_passage", "supporting_text", "raw_source_text", "reasoning_details"]:
            assert forbidden not in serialized
        for phrase in data["forbidden_advice_phrases"]:
            assert phrase not in serialized

    for case in data["non_generated_cases"]:
        comparison = generate_comparison(case["left"], case["right"])
        availability = comparison.evidence_availability
        assert comparison.comparison_type == "unavailable"
        assert comparison.key_differences == []
        assert comparison.bottom_line_for_beginners is None
        assert comparison.citations == []
        assert comparison.source_documents == []
        assert availability is not None
        assert availability.availability_state.value == case["expected_state"]
        assert availability.evidence_items == []
        assert availability.claim_bindings == []
        assert availability.citation_bindings == []
        assert availability.source_references == []
        assert availability.diagnostics.generated_comparison_available is False
        assert availability.diagnostics.no_live_external_calls is True
        assert availability.diagnostics.no_new_generated_output is True
        assert availability.diagnostics.unavailable_reasons

    for marker in data["forbidden_static_markers"]:
        assert marker not in comparison_source


def test_glossary_context_contract():
    data = load_yaml("glossary_context_eval_cases.yaml")
    assert data.get("schema_version") == "glossary-context-evals-v1"

    missing_models = {name for name in data["required_models"] if not hasattr(models, name)}
    assert not missing_models, f"Missing glossary context models: {missing_models}"

    helper_globals = {"build_glossary_response": build_glossary_response, "TERM_CATALOG": TERM_CATALOG}
    assert set(data["required_helpers"]) <= set(helper_globals)
    assert TERM_CATALOG

    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    glossary_source = (ROOT / "backend" / "glossary.py").read_text(encoding="utf-8")
    models_source = (ROOT / "backend" / "models.py").read_text(encoding="utf-8")
    frontend_glossary_source = (ROOT / "apps" / "web" / "lib" / "glossary.ts").read_text(encoding="utf-8")
    for route in data["required_routes"]:
        assert route in main_source
    assert "build_glossary_response" in main_source

    for marker in data["forbidden_static_markers"]:
        if marker == "apps/web/lib/glossary.ts":
            assert "glossary-asset-context-v1" not in frontend_glossary_source
            continue
        assert marker not in glossary_source
        if marker not in {"OPENROUTER_API_KEY"}:
            assert marker not in main_source

    for state in data["required_context_states"]:
        assert f'{state} = "{state}"' in models_source

    catalog_terms = {entry.term for entry in TERM_CATALOG}
    assert set(data["required_stock_terms"]) <= catalog_terms
    assert set(data["required_etf_terms"]) <= catalog_terms

    for ticker in data["supported_cached_assets"]:
        pack = build_asset_knowledge_pack(ticker)
        response = build_glossary_response(ticker)
        validated = GlossaryResponse.model_validate(response.model_dump(mode="json"))
        source_ids = {source.source_document_id for source in pack.source_documents}
        citation_ids = {binding.citation_id for binding in validated.citation_bindings}
        expected_terms = set(data["required_stock_terms"] if ticker == "AAPL" else data["required_etf_terms"])

        assert validated.schema_version == "glossary-asset-context-v1"
        assert validated.selected_asset.ticker == ticker
        assert validated.glossary_state.value == "available"
        assert expected_terms <= {term.term_identity.term for term in validated.terms}
        assert all(term.generic_definition.simple_definition for term in validated.terms)
        assert all(term.generic_definition.why_it_matters for term in validated.terms)
        assert all(term.generic_definition.common_beginner_mistake for term in validated.terms)
        assert all(term.generic_definition.generic_definition_requires_citation is False for term in validated.terms)
        assert {reference.asset_ticker for reference in validated.evidence_references} <= {ticker}
        assert {binding.asset_ticker for binding in validated.citation_bindings} <= {ticker}
        assert {binding.source_document_id for binding in validated.citation_bindings} <= source_ids
        assert {reference.source_document_id for reference in validated.source_references} <= source_ids
        assert all(reference.allowlist_status.value == "allowed" for reference in validated.source_references)
        assert all(
            reference.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
            for reference in validated.source_references
        )
        assert all(
            binding.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed}
            for binding in validated.citation_bindings
        )
        assert all(binding.permitted_operations.can_support_citations for binding in validated.citation_bindings)
        used_citations = {
            citation_id
            for term in validated.terms
            for citation_id in term.asset_context.citation_ids
        }
        assert used_citations <= citation_ids
        assert validated.diagnostics.no_live_external_calls is True
        assert validated.diagnostics.live_provider_calls_attempted is False
        assert validated.diagnostics.live_llm_calls_attempted is False
        assert validated.diagnostics.no_new_generated_output is True
        assert validated.diagnostics.no_frontend_change_required is True
        assert validated.diagnostics.generic_definitions_are_not_evidence is True
        serialized = str(validated.model_dump(mode="json")).lower()
        for marker in data["forbidden_serialized_markers"]:
            assert marker not in serialized
        for phrase in data["forbidden_advice_phrases"]:
            assert phrase not in serialized

    for case in data["supported_term_cases"]:
        response = build_glossary_response(case["ticker"], term=case["term"])
        assert len(response.terms) == 1
        assert response.terms[0].asset_context.availability_state.value == case["expected_state"]
        assert response.terms[0].asset_context.citation_ids
        assert response.citation_bindings
        assert response.source_references

    for case in data["generic_only_cases"]:
        response = build_glossary_response(case["ticker"], term=case["term"])
        assert len(response.terms) == 1
        assert response.terms[0].asset_context.availability_state.value == case["expected_state"]
        assert response.terms[0].asset_context.citation_ids == []
        assert response.citation_bindings == []
        assert response.source_references == []

    for case in data["non_generated_cases"]:
        response = build_glossary_response(case["ticker"], term="expense ratio")
        assert response.glossary_state.value == case["expected_response_state"]
        assert response.evidence_references == []
        assert response.citation_bindings == []
        assert response.source_references == []
        assert response.diagnostics.unavailable_reasons
        assert response.diagnostics.no_live_external_calls is True
        assert response.diagnostics.no_new_generated_output is True
        assert all(term.asset_context.citation_ids == [] for term in response.terms)


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


def test_chat_session_cases():
    from datetime import datetime, timedelta, timezone

    data = load_yaml("chat_session_eval_cases.yaml")
    assert data.get("schema_version") == "chat-session-evals-v1"

    missing_models = {name for name in data["required_models"] if not hasattr(models, name)}
    assert not missing_models, f"Missing chat session contract models: {missing_models}"

    helper_globals = {
        "ChatSessionStore",
        "answer_chat_with_session",
        "get_chat_session_status",
        "delete_chat_session",
        "chat_session_export_payload",
    }
    assert set(data["required_helpers"]) <= helper_globals
    assert CHAT_SESSION_TTL_DAYS == data["ttl"]["days"]
    assert CHAT_SESSION_TTL_SECONDS == data["ttl"]["seconds"]
    assert {state.value for state in ChatSessionLifecycleState} == set(data["required_lifecycle_states"])

    chat_session_source = (ROOT / "backend" / "chat_sessions.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    export_source = (ROOT / "backend" / "export.py").read_text(encoding="utf-8")
    for route in data["required_routes"]:
        assert route in main_source
    for forbidden in data["forbidden_imports"]:
        assert forbidden not in chat_session_source
    for forbidden in data["forbidden_storage_markers"]:
        assert forbidden not in chat_session_source

    class Clock:
        def __init__(self) -> None:
            self.now = datetime(2026, 4, 23, 13, 1, 25, tzinfo=timezone.utc)

        def __call__(self) -> datetime:
            return self.now

        def advance(self, **kwargs):
            self.now += timedelta(**kwargs)

    for index, case in enumerate(data["cases"]):
        clock = Clock()
        store = ChatSessionStore(id_generator=lambda i=index: f"abcdeffedcba4{i:03d}8abcdeffedcba{i:03d}", clock=clock)
        response = answer_chat_with_session(case["ticker"], ChatRequest(question=case["question"]), store=store)
        validated = ChatResponse.model_validate(response.model_dump(mode="json"))
        assert validated.session.lifecycle_state.value == case["expected_state"]
        assert validated.session.turn_count == case["expected_turn_count"]
        assert validated.session.export_available is case["expected_export_available"]
        assert validated.safety_classification.value == case["expected_safety_classification"]
        assert not find_forbidden_output_phrases(_flatten_static_text(validated.model_dump(mode="json")))
        if validated.session.conversation_id:
            assert case["ticker"] not in validated.session.conversation_id
            status = get_chat_session_status(validated.session.conversation_id, store=store)
            assert status.session.conversation_id == validated.session.conversation_id
            assert case["question"] not in str(status.model_dump(mode="json"))

    clock = Clock()
    store = ChatSessionStore(id_generator=lambda: "fedcbaabcdef44448fedcbaabcdef444", clock=clock)
    created = answer_chat_with_session("VOO", ChatRequest(question="What is VOO?"), store=store)
    conversation_id = created.session.conversation_id
    continued = answer_chat_with_session(
        "VOO",
        ChatRequest(question="What top risk should a beginner understand?", conversation_id=conversation_id),
        store=store,
    )
    mismatch = answer_chat_with_session("QQQ", ChatRequest(question="What is QQQ?", conversation_id=conversation_id), store=store)
    metadata, turns = chat_session_export_payload(conversation_id, store=store)
    deleted = delete_chat_session(conversation_id, store=store)
    deleted_status = get_chat_session_status(conversation_id, store=store)

    assert continued.session.turn_count == 2
    assert mismatch.session.lifecycle_state is ChatSessionLifecycleState.ticker_mismatch
    assert mismatch.citations == []
    assert metadata.export_available is True
    assert len(turns) == 2
    assert "What top risk should a beginner understand?" not in str([turn.model_dump(mode="json") for turn in turns])
    assert deleted.deleted is True
    assert deleted_status.session.lifecycle_state is ChatSessionLifecycleState.deleted
    assert deleted_status.turn_summaries == []
    assert "chat_session_export_payload" in export_source


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
            assert any(section.section_id == "weekly_news_focus" for section in validated.sections)
            assert any(section.section_id == "ai_comprehensive_analysis" for section in validated.sections)
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


def test_weekly_news_cases():
    data = load_yaml("weekly_news_eval_cases.yaml")
    assert data.get("schema_version") == "weekly-news-evals-v1"

    for case in data["window_cases"]:
        window = compute_weekly_news_window(case["as_of"])
        assert window.previous_market_week.model_dump(mode="json") == case["expected_previous_market_week"]
        assert window.current_week_to_date.model_dump(mode="json") == case["expected_current_week_to_date"]
        assert window.news_window_start == case["expected_news_window_start"]
        assert window.news_window_end == case["expected_news_window_end"]

    for case in data["fixture_cases"]:
        pack = build_asset_knowledge_pack(case["ticker"])
        focus = build_weekly_news_focus_from_pack(pack, as_of="2026-04-23")
        analysis = build_ai_comprehensive_analysis(pack.asset, focus)

        assert focus.state.value == case["expected_state"]
        assert len(focus.items) == case["expected_item_count"]
        assert focus.stable_facts_are_separate is True
        assert analysis.state.value == case["expected_ai_state"]
        assert analysis.analysis_available is case["expected_ai_available"]
        assert analysis.stable_facts_are_separate is True
        if focus.items == []:
            assert focus.empty_state is not None
            assert focus.empty_state.message

    required_models = {
        "WeeklyNewsWindow",
        "WeeklyNewsItem",
        "WeeklyNewsSelectionRationale",
        "WeeklyNewsDeduplicationMetadata",
        "WeeklyNewsSourceMetadata",
        "WeeklyNewsFocusResponse",
        "AIComprehensiveAnalysisSection",
        "AIComprehensiveAnalysisResponse",
    }
    assert required_models <= set(dir(models))

    overview = generate_asset_overview("VOO")
    assert overview.weekly_news_focus is not None
    assert overview.ai_comprehensive_analysis is not None
    assert overview.weekly_news_focus.state is WeeklyNewsContractState.no_high_signal
    assert overview.ai_comprehensive_analysis.state is WeeklyNewsContractState.suppressed
    assert not overview.ai_comprehensive_analysis.analysis_available
    assert "weekly_news_focus" not in {section.section_id for section in overview.sections if section.section_type.value == "stable_facts"}

    weekly_source = (ROOT / "backend" / "weekly_news.py").read_text(encoding="utf-8")
    for required in data["source_policy_required_exclusions"]:
        assert required in weekly_source
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in weekly_source
    analysis_text = _flatten_static_text(overview.ai_comprehensive_analysis.model_dump(mode="json"))
    for phrase in data["forbidden_analysis_language"]:
        assert phrase not in analysis_text.lower()


def test_llm_provider_cases():
    data = load_yaml("llm_provider_eval_cases.yaml")
    assert data.get("schema_version") == "llm-provider-evals-v1"

    missing_models = {name for name in data.get("required_models", []) if not hasattr(models, name)}
    assert not missing_models, f"Missing LLM provider contract models: {missing_models}"

    required_helpers = set(data.get("required_helpers", []))
    helper_globals = {
        "build_llm_runtime_config",
        "default_openrouter_settings",
        "validate_llm_generated_output",
        "decide_paid_fallback",
        "decide_cache_eligibility",
        "run_deterministic_mock_generation",
        "runtime_diagnostics",
    }
    assert required_helpers <= helper_globals, f"Missing LLM provider helpers: {required_helpers - helper_globals}"

    default_config = build_llm_runtime_config()
    assert default_config.provider_kind.value == data["default_runtime"]["provider_kind"]
    assert default_config.live_generation_enabled is data["default_runtime"]["live_generation_enabled"]
    assert default_config.live_gate_state.value == data["default_runtime"]["live_gate_state"]
    assert default_config.live_network_calls_allowed is data["default_runtime"]["live_network_calls_allowed"]

    disabled_openrouter = build_llm_runtime_config({"LLM_PROVIDER": "openrouter"})
    enabled_openrouter = build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True)
    assert disabled_openrouter.live_gate_state is LlmLiveGateState.unavailable
    assert enabled_openrouter.live_gate_state is LlmLiveGateState.enabled
    assert [model.model_name for model in enabled_openrouter.configured_model_chain] == data["openrouter_free_model_order"]
    assert tuple(data["openrouter_free_model_order"]) == DEFAULT_OPENROUTER_FREE_MODEL_ORDER
    assert enabled_openrouter.paid_fallback_model is not None
    assert enabled_openrouter.paid_fallback_model.model_name == data["paid_fallback_model"]
    assert DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL == data["paid_fallback_model"]
    assert enabled_openrouter.live_network_calls_allowed is False

    fallback = decide_paid_fallback(
        runtime=enabled_openrouter,
        trigger=LlmFallbackTrigger.validation_failed_after_repair,
        current_tier=LlmModelTier.free,
        repair_attempt_count=1,
    )
    assert fallback.should_fallback is True
    assert fallback.to_model is not None
    assert fallback.to_model.model_name == data["paid_fallback_model"]
    assert set(data["fallback_triggers"]) <= {trigger.value for trigger in LlmFallbackTrigger}

    request = LlmGenerationRequestMetadata(
        task_name="asset_summary",
        output_kind="asset_page",
        prompt_version="asset-page-prompt-v1",
        schema_version="asset-page-v1",
        safety_policy_version="safety-v1",
        asset_ticker="VOO",
        knowledge_pack_hash="knowledge-hash",
        source_freshness_hash="freshness-hash",
    )
    valid_evidence = [
        {
            "citation_id": "c_voo_profile",
            "asset_ticker": "VOO",
            "source_document_id": "src_voo_fact_sheet",
            "source_type": "issuer_fact_sheet",
            "supporting_text": "VOO issuer fact sheet fixture.",
        }
    ]
    valid_claim = {
        "claim_id": "claim_voo",
        "claim_text": "VOO has a local cited issuer fact sheet fixture.",
        "claim_type": "factual",
        "citation_ids": ["c_voo_profile"],
    }
    result = run_deterministic_mock_generation(
        request,
        claims=[valid_claim],
        evidence=valid_evidence,
        citation_context={"allowed_asset_tickers": ["VOO"]},
    )
    assert result.no_live_external_calls is True
    assert result.runtime.provider_kind is LlmProviderKind.mock
    assert result.validation.status is LlmValidationStatus.valid
    assert result.public_metadata.model_tier.value == "mock"
    assert result.cache_decision.cacheable is True

    invalid_schema = validate_llm_generated_output(output_text="Educational output.", schema_valid=False)
    missing_citation = validate_llm_generated_output(
        output_text="Educational output.",
        schema_valid=True,
        claims=[{**valid_claim, "citation_ids": ["c_missing"]}],
        evidence=valid_evidence,
        citation_context={"allowed_asset_tickers": ["VOO"]},
    )
    disallowed_source = validate_llm_generated_output(
        output_text="Educational output.",
        schema_valid=True,
        claims=[valid_claim],
        evidence=[
            {
                **valid_evidence[0],
                "allowlist_status": "rejected",
                "source_use_policy": "rejected",
            }
        ],
        citation_context={"allowed_asset_tickers": ["VOO"]},
    )
    rejection_statuses = {
        "schema_invalid": invalid_schema.status.value,
        "missing_citation": missing_citation.status.value,
        "disallowed_source_policy": disallowed_source.status.value,
        "advice_like_language": validate_llm_generated_output(
            output_text="This text includes a price target.",
            schema_valid=True,
        ).status.value,
        "hidden_prompt_leakage": validate_llm_generated_output(
            output_text="hidden prompt should not appear",
            schema_valid=True,
        ).status.value,
        "raw_reasoning_leakage": validate_llm_generated_output(
            output_text="reasoning_details should not appear",
            schema_valid=True,
        ).status.value,
        "unrestricted_source_text_leakage": validate_llm_generated_output(
            output_text="raw source text: full article",
            schema_valid=True,
        ).status.value,
    }
    for case in data["validation_rejection_cases"]:
        assert rejection_statuses[case["id"]] == case["expected_status"], case["id"]

    attempt = LlmGenerationAttemptMetadata(
        attempt_index=1,
        provider_kind=LlmProviderKind.mock,
        model_name="deterministic-mock-llm",
        model_tier=LlmModelTier.mock,
        status=LlmGenerationAttemptStatus.mock_succeeded,
        validation_status=LlmValidationStatus.valid,
    )
    cache_decision = decide_cache_eligibility(
        request=request,
        validation=result.validation,
        attempt=attempt,
        freshness_hash="freshness-hash",
    )
    assert cache_decision.cacheable is True
    repair_decision = decide_cache_eligibility(
        request=request,
        validation=result.validation,
        attempt=attempt.model_copy(update={"repair_attempt": True}),
        freshness_hash="freshness-hash",
    )
    assert repair_decision.cacheable is False

    diagnostics = runtime_diagnostics(default_openrouter_settings(), server_side_key_present=True)
    validated_diagnostics = LlmRuntimeDiagnosticsResponse.model_validate(diagnostics.model_dump(mode="json"))
    assert set(data["public_metadata_allowed_fields"]) == set(validated_diagnostics.public_metadata_fields)
    serialized = str(validated_diagnostics.model_dump(mode="json")).lower()
    for marker in data["forbidden_public_markers"]:
        assert marker not in serialized

    llm_source = (ROOT / "backend" / "llm.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    for forbidden in data["forbidden_imports"]:
        assert forbidden not in llm_source
        if forbidden != "os.environ":
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
    test_top500_stock_universe_manifest_contract()
    test_safety_cases()
    test_citation_cases()
    test_search_cases()
    test_ingestion_cases()
    test_pre_cache_cases()
    test_knowledge_pack_cases()
    test_provider_cases()
    test_cache_cases()
    test_retrieval_fixture_contract()
    test_generated_overview_contract()
    test_source_drawer_cases()
    test_generated_comparison_contract()
    test_comparison_evidence_availability_contract()
    test_glossary_context_contract()
    test_generated_chat_contract()
    test_export_cases()
    test_weekly_news_cases()
    test_llm_provider_cases()
    print("Static evals passed.")
