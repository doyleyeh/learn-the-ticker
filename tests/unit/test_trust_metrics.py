from backend.models import TrustMetricEventType, TrustMetricWorkflowArea
from backend.trust_metrics import (
    get_trust_metric_event_catalog,
    summarize_trust_metric_events,
    validate_trust_metric_event,
    validate_trust_metric_events,
)


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
