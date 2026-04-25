import importlib.util
from pathlib import Path

import pytest

from backend.models import TrustMetricEventType, TrustMetricWorkflowArea
from backend.trust_metric_repository import (
    TRUST_METRIC_EVENT_REPOSITORY_BOUNDARY,
    TRUST_METRIC_EVENT_REPOSITORY_TABLES,
    TrustMetricDiagnosticCategory,
    TrustMetricDiagnosticRow,
    TrustMetricEventRepositoryContractError,
    TrustMetricRepository,
    build_trust_metric_repository_records,
    build_trust_metric_repository_records_from_payloads,
    trust_metric_repository_metadata,
    validate_trust_metric_repository_records,
)
from backend.trust_metrics import (
    get_trust_metric_event_catalog,
    summarize_trust_metric_events,
    validate_trust_metric_event,
    validate_trust_metric_events,
)


ROOT = Path(__file__).resolve().parents[2]


def test_trust_metric_catalog_covers_product_and_trust_metrics():
    catalog = get_trust_metric_event_catalog()
    product_types = {event.event_type.value for event in catalog.product_events}
    trust_types = {event.event_type.value for event in catalog.trust_events}

    assert catalog.schema_version == "trust-metrics-event-v1"
    assert catalog.validation_only is True
    assert catalog.persistence_enabled is False
    assert catalog.external_analytics_enabled is False
    assert catalog.no_live_external_calls is True
    assert {
        "search_success",
        "unsupported_asset_outcome",
        "asset_page_view",
        "comparison_usage",
        "source_drawer_usage",
        "glossary_usage",
        "export_usage",
        "chat_follow_up",
        "chat_answer_outcome",
        "chat_safety_redirect",
        "latency_to_first_meaningful_result",
    } <= product_types
    assert {
        "citation_coverage",
        "unsupported_claim_drop",
        "weak_citation_count",
        "generated_output_validation_failure",
        "safety_redirect_rate",
        "freshness_accuracy",
        "source_retrieval_failure",
        "hallucination_unsupported_fact_incident",
        "stale_data_incident",
    } <= trust_types
    assert {"raw_query", "question", "answer", "source_passage", "source_url", "email", "ip_address"} <= set(
        catalog.forbidden_field_names
    )


def test_validator_accepts_and_normalizes_anonymous_asset_metadata():
    result = validate_trust_metric_event(
        {
            "event_type": "asset_page_view",
            "workflow_area": "asset_page",
            "client_event_id": "local-event-001",
            "asset_ticker": "voo",
            "generated_output_available": True,
            "metadata": {"freshness_state": "fresh", "asset_support_state": "cached_supported"},
        }
    )

    assert result.validation_status.value == "accepted"
    event = result.normalized_event
    assert event is not None
    assert event.schema_version == "trust-metrics-event-v1"
    assert event.occurred_at == "1970-01-01T00:00:00Z"
    assert event.asset_ticker == "VOO"
    assert event.asset_support_state.value == "cached_supported"
    assert event.generated_output_available is True


def test_validator_distinguishes_eligible_unsupported_and_unknown_assets():
    eligible = validate_trust_metric_event(
        {"event_type": "search_success", "workflow_area": "search", "asset_ticker": "spy"}
    )
    unsupported = validate_trust_metric_event(
        {"event_type": "unsupported_asset_outcome", "workflow_area": "search", "asset_ticker": "tqqq"}
    )
    unknown = validate_trust_metric_event(
        {"event_type": "unsupported_asset_outcome", "workflow_area": "search", "asset_ticker": "zzzz"}
    )

    assert eligible.normalized_event.asset_support_state.value == "eligible_not_cached"
    assert unsupported.normalized_event.asset_support_state.value == "recognized_unsupported"
    assert unknown.normalized_event.asset_support_state.value == "unknown"

    invalid = validate_trust_metric_event(
        {
            "event_type": "asset_page_view",
            "workflow_area": "asset_page",
            "asset_ticker": "SPY",
            "generated_output_available": True,
        }
    )
    assert invalid.validation_status.value == "rejected"
    assert any("generated output cannot be available" in reason for reason in invalid.rejection_reasons)


def test_generated_output_metadata_accepts_ids_without_raw_text_or_urls():
    result = validate_trust_metric_event(
        {
            "event_type": "citation_coverage",
            "workflow_area": "citation",
            "asset_ticker": "QQQ",
            "generated_output_available": True,
            "output_metadata": {
                "output_kind": "chat_answer",
                "prompt_version": "chat-v1",
                "model_name": "deterministic-fixture-model",
                "schema_valid": True,
                "citation_coverage_rate": 0.75,
                "citation_ids": ["c_qqq_profile"],
                "source_document_ids": ["src_qqq_fact_sheet_fixture"],
                "freshness_hash": "freshness-abc",
                "freshness_state": "fresh",
                "safety_status": "educational",
                "unsupported_claim_count": 0,
                "weak_citation_count": 1,
                "stale_source_count": 0,
                "latency_ms": 25,
            },
        }
    )

    assert result.validation_status.value == "accepted"
    event = result.normalized_event
    assert event.output_metadata.citation_coverage_rate == 0.75
    assert event.output_metadata.citation_ids == ["c_qqq_profile"]
    assert event.output_metadata.source_document_ids == ["src_qqq_fact_sheet_fixture"]


def test_validator_rejects_privacy_fields_bad_counts_and_freshness_gaps():
    cases = [
        {
            "event_type": "chat_answer_outcome",
            "workflow_area": "chat",
            "asset_ticker": "VOO",
            "question": "What is this fund?",
        },
        {
            "event_type": "citation_coverage",
            "workflow_area": "citation",
            "asset_ticker": "VOO",
            "generated_output_available": True,
            "output_metadata": {"output_kind": "asset_page", "citation_coverage_rate": 1.25},
        },
        {
            "event_type": "weak_citation_count",
            "workflow_area": "citation",
            "asset_ticker": "VOO",
            "generated_output_available": True,
            "output_metadata": {"output_kind": "asset_page", "weak_citation_count": -1},
        },
        {
            "event_type": "latency_to_first_meaningful_result",
            "workflow_area": "search",
            "metadata": {"latency_ms": -5},
        },
        {
            "event_type": "freshness_accuracy",
            "workflow_area": "freshness",
            "asset_ticker": "VOO",
        },
    ]

    for case in cases:
        result = validate_trust_metric_event(case)
        assert result.validation_status.value == "rejected"
        assert result.rejection_reasons


def test_validator_rejects_source_ids_when_non_generated_output_is_unavailable():
    result = validate_trust_metric_event(
        {
            "event_type": "generated_output_validation_failure",
            "workflow_area": "generated_output",
            "asset_ticker": "BTC",
            "generated_output_available": False,
            "output_metadata": {
                "output_kind": "asset_page",
                "schema_valid": False,
                "citation_ids": ["c_fake"],
                "source_document_ids": ["src_fake"],
            },
        }
    )

    assert result.validation_status.value == "rejected"
    assert any("citation and source document IDs" in reason for reason in result.rejection_reasons)


def test_summarization_is_deterministic_for_accepted_events_only():
    response = validate_trust_metric_events(
        [
            {"event_type": "search_success", "workflow_area": "search", "asset_ticker": "VOO", "metadata": {"latency_ms": 20}},
            {"event_type": "chat_safety_redirect", "workflow_area": "chat", "asset_ticker": "VOO"},
            {
                "event_type": "generated_output_validation_failure",
                "workflow_area": "generated_output",
                "asset_ticker": "VOO",
                "generated_output_available": True,
                "output_metadata": {"output_kind": "asset_page", "schema_valid": False, "latency_ms": 40},
            },
            {"event_type": "source_retrieval_failure", "workflow_area": "retrieval", "metadata": {"freshness_state": "unavailable"}},
            {"event_type": "chat_answer_outcome", "workflow_area": "chat", "answer": "raw text is rejected"},
        ]
    )
    accepted = [item.normalized_event for item in response.events if item.normalized_event is not None]
    repeated_summary = summarize_trust_metric_events(accepted)

    assert response.accepted_count == 4
    assert response.rejected_count == 1
    assert response.summary == repeated_summary
    assert response.summary.product_metric_counts["search_success"] == 1
    assert response.summary.product_metric_counts["chat_safety_redirect"] == 1
    assert response.summary.trust_metric_counts["generated_output_validation_failure"] == 1
    assert response.summary.trust_metric_counts["source_retrieval_failure"] == 1
    assert response.summary.rates["generated_output_validation_failure_rate"] == 0.25
    assert response.summary.rates["safety_redirect_rate"] == 0.25
    assert response.summary.latency_ms == {"count": 2, "min": 20, "max": 40, "average": 30.0}


def test_event_enums_keep_catalog_workflow_shape_stable():
    assert TrustMetricEventType.search_success.value == "search_success"
    assert TrustMetricWorkflowArea.generated_output.value == "generated_output"


def test_dormant_trust_metric_repository_metadata_and_revision_are_importable():
    metadata = trust_metric_repository_metadata()

    assert metadata.boundary == TRUST_METRIC_EVENT_REPOSITORY_BOUNDARY
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == TRUST_METRIC_EVENT_REPOSITORY_TABLES
    assert set(TRUST_METRIC_EVENT_REPOSITORY_TABLES) == {
        "trust_metric_event_envelopes",
        "trust_metric_validation_statuses",
        "trust_metric_aggregate_counters",
        "trust_metric_latency_summaries",
        "trust_metric_state_snapshots",
        "trust_metric_diagnostics",
    }
    assert "event_type" in metadata.tables["trust_metric_event_envelopes"].columns
    assert "sanitized_metadata" in metadata.tables["trust_metric_event_envelopes"].columns
    assert "generated_output_state" in metadata.tables["trust_metric_validation_statuses"].columns
    assert "rate" in metadata.tables["trust_metric_aggregate_counters"].columns
    assert "average_ms" in metadata.tables["trust_metric_latency_summaries"].columns
    assert "state_consistency_status" in metadata.tables["trust_metric_state_snapshots"].columns

    revision_path = ROOT / "alembic" / "versions" / "20260425_0007_trust_metric_event_contracts.py"
    source = revision_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("trust_metric_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0007"
    assert module.down_revision == "20260425_0006"
    assert module.TRUST_METRIC_EVENT_TABLE_NAMES == TRUST_METRIC_EVENT_REPOSITORY_TABLES
    for table_name in TRUST_METRIC_EVENT_REPOSITORY_TABLES:
        assert f'"{table_name}"' in source

    for marker in ["user_accounts", "cookies", "external_analytics_events", "provider_secrets", "raw_chat_transcripts"]:
        assert marker not in module.TRUST_METRIC_EVENT_TABLE_NAMES
        assert f'op.create_table("{marker}"' not in source


def test_dormant_trust_metric_repository_builds_rows_from_validated_compact_events():
    records = build_trust_metric_repository_records_from_payloads(
        [
            {
                "event_type": "citation_coverage",
                "workflow_area": "citation",
                "client_event_id": "event-citation-coverage",
                "asset_ticker": "VOO",
                "generated_output_available": True,
                "output_metadata": {
                    "output_kind": "asset_page",
                    "schema_valid": True,
                    "citation_coverage_rate": 1.0,
                    "citation_ids": ["c_voo_overview"],
                    "source_document_ids": ["src_voo_fact_sheet_fixture"],
                    "freshness_hash": "hash-voo",
                    "freshness_state": "fresh",
                    "safety_status": "educational",
                    "unsupported_claim_count": 0,
                    "weak_citation_count": 0,
                    "stale_source_count": 0,
                    "latency_ms": 30,
                },
                "metadata": {"evidence_state": "supported", "freshness_labeled": True},
            },
            {
                "event_type": "chat_safety_redirect",
                "workflow_area": "chat",
                "client_event_id": "event-safety-redirect",
                "asset_ticker": "VOO",
                "metadata": {"chat_outcome": "safety_redirect", "safety_classification": "safety_redirect"},
            },
            {
                "event_type": "latency_to_first_meaningful_result",
                "workflow_area": "search",
                "client_event_id": "event-latency",
                "metadata": {"latency_ms": 20, "support_classification": "cached_supported"},
            },
        ],
        batch_id="trust-batch-001",
        created_at="2026-04-25T20:01:27Z",
    )

    persisted = TrustMetricRepository().persist(records)
    event = persisted.events[0]

    assert persisted.table_names == TRUST_METRIC_EVENT_REPOSITORY_TABLES
    assert event.event_id == "event-citation-coverage"
    assert event.asset_ticker == "VOO"
    assert event.citation_ids == ["c_voo_overview"]
    assert event.source_document_ids == ["src_voo_fact_sheet_fixture"]
    assert event.citation_coverage_rate == 1.0
    assert event.freshness_state == "fresh"
    assert event.evidence_state == "supported"
    assert event.safety_status == "educational"
    assert event.validation_only is True
    assert event.persistence_enabled is False
    assert event.external_analytics_enabled is False
    assert event.analytics_emitted is False
    assert event.stores_raw_user_text is False
    assert persisted.validation_statuses[0].generated_output_state == "available_metadata"
    assert persisted.state_snapshots[0].state_consistency_status == "passed"
    assert persisted.latency_summaries[0].count == 2
    assert persisted.latency_summaries[0].average_ms == 25.0
    assert any(row.event_type == "citation_coverage" and row.count == 1 for row in persisted.aggregate_counters)
    assert any(row.rate is not None for row in persisted.aggregate_counters)


def test_dormant_trust_metric_repository_rejects_unvalidated_raw_or_sensitive_payloads():
    with pytest.raises(TrustMetricEventRepositoryContractError, match="pre-validated"):
        build_trust_metric_repository_records_from_payloads(
            [
                {
                    "event_type": "chat_answer_outcome",
                    "workflow_area": "chat",
                    "asset_ticker": "VOO",
                    "question": "raw question text",
                }
            ],
            batch_id="trust-batch-rejected",
            created_at="2026-04-25T20:01:27Z",
        )

    accepted = validate_trust_metric_event(
        {
            "event_type": "search_success",
            "workflow_area": "search",
            "client_event_id": "event-search",
            "asset_ticker": "VOO",
            "metadata": {"result_count": 1, "support_classification": "cached_supported"},
        }
    ).normalized_event
    assert accepted is not None
    records = build_trust_metric_repository_records(
        [accepted],
        batch_id="trust-batch-search",
        created_at="2026-04-25T20:01:27Z",
    )

    leaking = records.events[0].model_copy(update={"sanitized_metadata": {"raw_prompt": "hidden"}})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="sanitized"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [leaking]}))

    source_url = records.events[0].model_copy(update={"sanitized_metadata": {"source_url": "https://example.test/source"}})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="source URLs|sanitized"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [source_url]}))

    raw_flag = records.events[0].model_copy(update={"stores_raw_query_text": True})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="compact metadata"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [raw_flag]}))


def test_dormant_trust_metric_repository_enforces_state_freshness_and_source_policy_boundaries():
    records = build_trust_metric_repository_records_from_payloads(
        [
            {
                "event_type": "freshness_accuracy",
                "workflow_area": "freshness",
                "client_event_id": "event-freshness",
                "asset_ticker": "VOO",
                "generated_output_available": True,
                "output_metadata": {
                    "output_kind": "asset_page",
                    "citation_ids": ["c_voo_overview"],
                    "source_document_ids": ["src_voo_fact_sheet_fixture"],
                    "freshness_state": "fresh",
                    "safety_status": "educational",
                },
                "metadata": {"evidence_state": "supported", "freshness_labeled": True},
            }
        ],
        batch_id="trust-batch-freshness",
        created_at="2026-04-25T20:01:27Z",
    )

    blocked_support = records.events[0].model_copy(update={"asset_support_state": "recognized_unsupported"})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="blocked support"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [blocked_support]}))

    stale_unlabeled = records.events[0].model_copy(update={"freshness_state": "stale", "sanitized_metadata": {"freshness_labeled": False}})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="unsupported, stale, partial"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [stale_unlabeled]}))

    partial_unlabeled = records.events[0].model_copy(update={"evidence_state": "partial", "sanitized_metadata": {"uncertainty_labeled": False}})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="unsupported, stale, partial"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [partial_unlabeled]}))

    source_policy_block = records.events[0].model_copy(update={"sanitized_metadata": {"source_use_status": "source_policy_blocked"}})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="Source-policy-blocked"):
        validate_trust_metric_repository_records(records.model_copy(update={"events": [source_policy_block]}))

    diagnostic = TrustMetricDiagnosticRow(
        diagnostic_id="diag-freshness-state",
        batch_id="trust-batch-freshness",
        event_id=records.events[0].event_id,
        category=TrustMetricDiagnosticCategory.freshness.value,
        code="freshness_label_checked",
        event_type="freshness_accuracy",
        workflow_area="freshness",
        freshness_states={"page": "fresh"},
        compact_metadata={"validation_code": "freshness_label_checked", "counter": 1},
        created_at="2026-04-25T20:01:27Z",
    )
    validate_trust_metric_repository_records(records.model_copy(update={"diagnostics": [diagnostic]}))

    leaking_diagnostic = diagnostic.model_copy(update={"compact_metadata": {"answer_text": "raw answer"}})
    with pytest.raises(TrustMetricEventRepositoryContractError, match="sanitized"):
        validate_trust_metric_repository_records(records.model_copy(update={"diagnostics": [leaking_diagnostic]}))


def test_dormant_trust_metric_repository_imports_do_not_open_live_paths():
    repository_source = (ROOT / "backend" / "repositories" / "trust_metrics.py").read_text(encoding="utf-8")

    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "redis",
        "boto3",
        "OPENROUTER",
        "openai",
        "os.environ",
        "api_key",
        "document.cookie",
        "localStorage",
    ]
    for marker in forbidden:
        assert marker not in repository_source

    records = build_trust_metric_repository_records_from_payloads(
        [{"event_type": "search_success", "workflow_area": "search", "client_event_id": "event-search"}],
        batch_id="trust-batch-session",
        created_at="2026-04-25T20:01:27Z",
    )

    class BadSession:
        pass

    with pytest.raises(TrustMetricEventRepositoryContractError, match="add_all"):
        TrustMetricRepository(session=BadSession()).persist(records)
