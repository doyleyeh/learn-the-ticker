from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import ValidationError

from backend.data import ASSETS, ELIGIBLE_NOT_CACHED_ASSETS, UNSUPPORTED_ASSETS, normalize_ticker
from backend.models import (
    FreshnessState,
    TrustMetricAssetSupportState,
    TrustMetricCatalogEvent,
    TrustMetricCatalogResponse,
    TrustMetricEvent,
    TrustMetricEventType,
    TrustMetricKind,
    TrustMetricSummary,
    TrustMetricValidatedEvent,
    TrustMetricValidationResponse,
    TrustMetricValidationStatus,
    TrustMetricWorkflowArea,
)


TRUST_METRICS_SCHEMA_VERSION = "trust-metrics-event-v1"
TRUST_METRICS_DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"

FORBIDDEN_EVENT_FIELD_NAMES = {
    "raw_query",
    "query",
    "query_text",
    "search_query",
    "question",
    "prompt",
    "user_prompt",
    "answer",
    "generated_answer",
    "generated_text",
    "raw_generated_text",
    "raw_retrieved_text",
    "source_passage",
    "supporting_passage",
    "source_url",
    "source_urls",
    "url",
    "email",
    "ip_address",
    "user_agent",
    "account_id",
    "user_id",
    "portfolio",
    "allocation",
    "cookies",
    "cookie",
    "external_analytics_id",
    "ga_client_id",
    "amplitude_id",
    "segment_anonymous_id",
}

COMPACT_METADATA_FIELDS = [
    "asset_support_state",
    "can_open_generated_page",
    "can_request_ingestion",
    "chat_outcome",
    "citation_count",
    "citation_coverage_rate",
    "comparison_state",
    "evidence_state",
    "export_content_type",
    "export_format",
    "freshness_state",
    "latency_ms",
    "no_high_signal_state",
    "output_kind",
    "result_count",
    "safety_classification",
    "schema_valid",
    "selected_section",
    "source_document_count",
    "stale_source_count",
    "support_classification",
    "unsupported_claim_count",
    "validation_failure_count",
    "weak_citation_count",
]


def get_trust_metric_event_catalog() -> TrustMetricCatalogResponse:
    product_events = [
        _catalog(
            TrustMetricEventType.search_success,
            TrustMetricWorkflowArea.search,
            TrustMetricKind.product,
            "Search resolved to a compact support outcome.",
            ["result_count", "support_classification", "can_open_generated_page", "can_request_ingestion"],
        ),
        _catalog(
            TrustMetricEventType.unsupported_asset_outcome,
            TrustMetricWorkflowArea.search,
            TrustMetricKind.product,
            "Search or routing identified a recognized unsupported or unknown asset state.",
            ["asset_support_state", "support_classification"],
        ),
        _catalog(
            TrustMetricEventType.asset_page_view,
            TrustMetricWorkflowArea.asset_page,
            TrustMetricKind.product,
            "A cached local asset page contract was viewed.",
            ["asset_support_state", "freshness_state"],
        ),
        _catalog(
            TrustMetricEventType.comparison_usage,
            TrustMetricWorkflowArea.comparison,
            TrustMetricKind.product,
            "A comparison workflow was requested or returned an explicit availability state.",
            ["comparison_state", "asset_support_state", "latency_ms"],
        ),
        _catalog(
            TrustMetricEventType.source_drawer_usage,
            TrustMetricWorkflowArea.source_drawer,
            TrustMetricKind.product,
            "A source drawer or citation detail surface was inspected.",
            ["selected_section", "citation_count", "source_document_count"],
        ),
        _catalog(
            TrustMetricEventType.glossary_usage,
            TrustMetricWorkflowArea.glossary,
            TrustMetricKind.product,
            "A glossary term surface was inspected using compact term metadata.",
            ["selected_section", "asset_support_state"],
        ),
        _catalog(
            TrustMetricEventType.export_usage,
            TrustMetricWorkflowArea.export,
            TrustMetricKind.product,
            "An export workflow returned an availability state.",
            ["export_content_type", "export_format", "asset_support_state"],
        ),
        _catalog(
            TrustMetricEventType.chat_follow_up,
            TrustMetricWorkflowArea.chat,
            TrustMetricKind.product,
            "A chat follow-up interaction was counted without raw question text.",
            ["chat_outcome", "asset_support_state"],
        ),
        _catalog(
            TrustMetricEventType.chat_answer_outcome,
            TrustMetricWorkflowArea.chat,
            TrustMetricKind.product,
            "A chat answer availability or evidence state was counted.",
            ["chat_outcome", "safety_classification", "evidence_state"],
            allows_output_metadata=True,
        ),
        _catalog(
            TrustMetricEventType.chat_safety_redirect,
            TrustMetricWorkflowArea.chat,
            TrustMetricKind.product,
            "A chat safety redirect outcome was counted without raw question text.",
            ["chat_outcome", "safety_classification"],
        ),
        _catalog(
            TrustMetricEventType.latency_to_first_meaningful_result,
            TrustMetricWorkflowArea.search,
            TrustMetricKind.product,
            "Compact latency metadata for the first meaningful local result.",
            ["latency_ms", "support_classification"],
        ),
    ]
    trust_events = [
        _catalog(
            TrustMetricEventType.citation_coverage,
            TrustMetricWorkflowArea.citation,
            TrustMetricKind.trust,
            "Citation coverage metadata for generated output validation.",
            ["citation_coverage_rate", "citation_count", "source_document_count"],
            allows_output_metadata=True,
        ),
        _catalog(
            TrustMetricEventType.unsupported_claim_drop,
            TrustMetricWorkflowArea.generated_output,
            TrustMetricKind.trust,
            "Unsupported factual claims removed during validation.",
            ["unsupported_claim_count", "output_kind"],
            allows_output_metadata=True,
        ),
        _catalog(
            TrustMetricEventType.weak_citation_count,
            TrustMetricWorkflowArea.citation,
            TrustMetricKind.trust,
            "Weak citation findings counted during validation.",
            ["weak_citation_count", "output_kind"],
            allows_output_metadata=True,
        ),
        _catalog(
            TrustMetricEventType.generated_output_validation_failure,
            TrustMetricWorkflowArea.generated_output,
            TrustMetricKind.trust,
            "Generated output failed schema, citation, freshness, or safety validation.",
            ["validation_failure_count", "schema_valid", "output_kind"],
            allows_output_metadata=True,
        ),
        _catalog(
            TrustMetricEventType.safety_redirect_rate,
            TrustMetricWorkflowArea.safety,
            TrustMetricKind.trust,
            "Safety redirects counted as product trust metadata.",
            ["safety_classification", "chat_outcome"],
        ),
        _catalog(
            TrustMetricEventType.freshness_accuracy,
            TrustMetricWorkflowArea.freshness,
            TrustMetricKind.trust,
            "Freshness labels matched validation state.",
            ["freshness_state", "evidence_state"],
            allows_output_metadata=True,
            requires_freshness_state=True,
        ),
        _catalog(
            TrustMetricEventType.source_retrieval_failure,
            TrustMetricWorkflowArea.retrieval,
            TrustMetricKind.trust,
            "Source retrieval failed or returned unavailable evidence metadata.",
            ["evidence_state", "freshness_state"],
            requires_freshness_state=True,
        ),
        _catalog(
            TrustMetricEventType.hallucination_unsupported_fact_incident,
            TrustMetricWorkflowArea.generated_output,
            TrustMetricKind.trust,
            "Unsupported factual output was caught by validation.",
            ["unsupported_claim_count", "output_kind"],
            allows_output_metadata=True,
        ),
        _catalog(
            TrustMetricEventType.stale_data_incident,
            TrustMetricWorkflowArea.freshness,
            TrustMetricKind.trust,
            "Stale source or section state was detected.",
            ["freshness_state", "stale_source_count"],
            allows_output_metadata=True,
            requires_freshness_state=True,
        ),
    ]
    return TrustMetricCatalogResponse(
        product_events=product_events,
        trust_events=trust_events,
        forbidden_field_names=sorted(FORBIDDEN_EVENT_FIELD_NAMES),
    )


def validate_trust_metric_event(payload: dict[str, Any]) -> TrustMetricValidatedEvent:
    reasons: list[str] = []
    field_paths: list[str] = []

    forbidden_paths = _find_forbidden_field_paths(payload)
    if forbidden_paths:
        reasons.append("payload contains privacy-sensitive or licensing-sensitive field names")
        field_paths.extend(forbidden_paths)

    normalized_payload = _normalize_payload(payload)
    try:
        event = TrustMetricEvent.model_validate(normalized_payload)
    except ValidationError as exc:
        return TrustMetricValidatedEvent(
            validation_status=TrustMetricValidationStatus.rejected,
            rejection_reasons=[*reasons, "payload does not match the trust metrics schema"],
            rejected_field_paths=[*field_paths, *[".".join(str(part) for part in error["loc"]) for error in exc.errors()]],
        )

    catalog_by_type = _catalog_by_event_type()
    catalog_event = catalog_by_type.get(event.event_type)
    if catalog_event is None:
        reasons.append("event type is not in the trust metrics catalog")
    else:
        if event.workflow_area is not catalog_event.workflow_area:
            reasons.append("workflow_area does not match the catalog event type")
            field_paths.append("workflow_area")
        if event.output_metadata and not catalog_event.allows_generated_output_metadata:
            reasons.append("event type does not allow generated output metadata")
            field_paths.append("output_metadata")

    reasons.extend(_state_consistency_rejections(event, field_paths))

    if reasons:
        return TrustMetricValidatedEvent(
            validation_status=TrustMetricValidationStatus.rejected,
            rejection_reasons=sorted(set(reasons)),
            rejected_field_paths=sorted(set(field_paths)),
        )

    return TrustMetricValidatedEvent(
        validation_status=TrustMetricValidationStatus.accepted,
        normalized_event=event,
    )


def validate_trust_metric_events(payloads: list[dict[str, Any]]) -> TrustMetricValidationResponse:
    validated_events = [validate_trust_metric_event(payload) for payload in payloads]
    accepted = [item.normalized_event for item in validated_events if item.normalized_event is not None]
    return TrustMetricValidationResponse(
        accepted_count=len(accepted),
        rejected_count=len(validated_events) - len(accepted),
        events=validated_events,
        summary=summarize_trust_metric_events(accepted),
    )


def summarize_trust_metric_events(events: list[TrustMetricEvent]) -> TrustMetricSummary:
    catalog_by_type = _catalog_by_event_type()
    event_type_counts = Counter(event.event_type.value for event in events)
    workflow_counts = Counter(event.workflow_area.value for event in events)
    product_counts: Counter[str] = Counter()
    trust_counts: Counter[str] = Counter()
    latencies = [
        int(value)
        for event in events
        for value in [_event_latency_ms(event)]
        if isinstance(value, int)
    ]

    for event in events:
        catalog_event = catalog_by_type[event.event_type]
        if catalog_event.metric_kind is TrustMetricKind.product:
            product_counts[event.event_type.value] += 1
        else:
            trust_counts[event.event_type.value] += 1

    accepted_count = len(events)
    rates = {
        "citation_coverage_event_rate": _rate(event_type_counts[TrustMetricEventType.citation_coverage.value], accepted_count),
        "unsupported_claim_event_rate": _rate(
            event_type_counts[TrustMetricEventType.unsupported_claim_drop.value]
            + event_type_counts[TrustMetricEventType.hallucination_unsupported_fact_incident.value],
            accepted_count,
        ),
        "weak_citation_event_rate": _rate(event_type_counts[TrustMetricEventType.weak_citation_count.value], accepted_count),
        "generated_output_validation_failure_rate": _rate(
            event_type_counts[TrustMetricEventType.generated_output_validation_failure.value], accepted_count
        ),
        "safety_redirect_rate": _rate(
            event_type_counts[TrustMetricEventType.chat_safety_redirect.value]
            + event_type_counts[TrustMetricEventType.safety_redirect_rate.value],
            accepted_count,
        ),
        "stale_data_incident_rate": _rate(event_type_counts[TrustMetricEventType.stale_data_incident.value], accepted_count),
        "source_retrieval_failure_rate": _rate(
            event_type_counts[TrustMetricEventType.source_retrieval_failure.value], accepted_count
        ),
    }
    latency_summary: dict[str, int | float | None] = {
        "count": len(latencies),
        "min": min(latencies) if latencies else None,
        "max": max(latencies) if latencies else None,
        "average": round(sum(latencies) / len(latencies), 2) if latencies else None,
    }
    return TrustMetricSummary(
        accepted_event_count=accepted_count,
        event_type_counts=dict(sorted(event_type_counts.items())),
        workflow_area_counts=dict(sorted(workflow_counts.items())),
        product_metric_counts=dict(sorted(product_counts.items())),
        trust_metric_counts=dict(sorted(trust_counts.items())),
        rates=rates,
        latency_ms=latency_summary,
    )


def _catalog(
    event_type: TrustMetricEventType,
    workflow_area: TrustMetricWorkflowArea,
    metric_kind: TrustMetricKind,
    description: str,
    allowed_metadata_fields: list[str],
    *,
    allows_output_metadata: bool = False,
    requires_freshness_state: bool = False,
) -> TrustMetricCatalogEvent:
    return TrustMetricCatalogEvent(
        event_type=event_type,
        workflow_area=workflow_area,
        metric_kind=metric_kind,
        description=description,
        allowed_metadata_fields=allowed_metadata_fields,
        allows_generated_output_metadata=allows_output_metadata,
        requires_freshness_state=requires_freshness_state,
    )


def _catalog_by_event_type() -> dict[TrustMetricEventType, TrustMetricCatalogEvent]:
    catalog = get_trust_metric_event_catalog()
    return {event.event_type: event for event in [*catalog.product_events, *catalog.trust_events]}


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("schema_version", TRUST_METRICS_SCHEMA_VERSION)
    normalized.setdefault("occurred_at", TRUST_METRICS_DEFAULT_TIMESTAMP)

    for key in ["asset_ticker", "comparison_left_ticker", "comparison_right_ticker"]:
        if normalized.get(key):
            normalized[key] = normalize_ticker(str(normalized[key]))

    asset_ticker = normalized.get("asset_ticker")
    if asset_ticker:
        normalized["asset_support_state"] = _asset_support_state(str(asset_ticker)).value

    return normalized


def _asset_support_state(ticker: str) -> TrustMetricAssetSupportState:
    normalized = normalize_ticker(ticker)
    if normalized in ASSETS:
        return TrustMetricAssetSupportState.cached_supported
    if normalized in ELIGIBLE_NOT_CACHED_ASSETS:
        return TrustMetricAssetSupportState.eligible_not_cached
    if normalized in UNSUPPORTED_ASSETS:
        return TrustMetricAssetSupportState.recognized_unsupported
    return TrustMetricAssetSupportState.unknown


def _find_forbidden_field_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            field_path = f"{prefix}.{key}" if prefix else str(key)
            if normalized_key in FORBIDDEN_EVENT_FIELD_NAMES or "cookie" in normalized_key:
                paths.append(field_path)
            paths.extend(_find_forbidden_field_paths(item, field_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_find_forbidden_field_paths(item, f"{prefix}[{index}]"))
    return paths


def _state_consistency_rejections(event: TrustMetricEvent, field_paths: list[str]) -> list[str]:
    reasons: list[str] = []
    non_generated_states = {
        TrustMetricAssetSupportState.eligible_not_cached,
        TrustMetricAssetSupportState.recognized_unsupported,
        TrustMetricAssetSupportState.unknown,
        TrustMetricAssetSupportState.unavailable,
    }

    if event.asset_support_state in non_generated_states and event.generated_output_available:
        reasons.append("generated output cannot be available for unsupported, unknown, unavailable, or eligible-not-cached assets")
        field_paths.append("generated_output_available")

    if event.output_metadata:
        metadata = event.output_metadata
        if metadata.citation_coverage_rate is not None and not 0 <= metadata.citation_coverage_rate <= 1:
            reasons.append("citation coverage rate must be between 0 and 1")
            field_paths.append("output_metadata.citation_coverage_rate")
        if metadata.unsupported_claim_count < 0:
            reasons.append("unsupported claim count cannot be negative")
            field_paths.append("output_metadata.unsupported_claim_count")
        if metadata.weak_citation_count < 0:
            reasons.append("weak citation count cannot be negative")
            field_paths.append("output_metadata.weak_citation_count")
        if metadata.stale_source_count < 0:
            reasons.append("stale source count cannot be negative")
            field_paths.append("output_metadata.stale_source_count")
        if metadata.latency_ms is not None and metadata.latency_ms < 0:
            reasons.append("latency_ms cannot be negative")
            field_paths.append("output_metadata.latency_ms")
        if (
            event.asset_support_state in non_generated_states
            and not event.generated_output_available
            and (metadata.citation_ids or metadata.source_document_ids)
        ):
            reasons.append("citation and source document IDs are not valid when no generated output exists")
            field_paths.append("output_metadata.citation_ids")
            field_paths.append("output_metadata.source_document_ids")

    latency = event.metadata.get("latency_ms")
    if isinstance(latency, (int, float)) and latency < 0:
        reasons.append("latency_ms cannot be negative")
        field_paths.append("metadata.latency_ms")

    for key in ["unsupported_claim_count", "weak_citation_count", "stale_source_count", "citation_count", "source_document_count"]:
        value = event.metadata.get(key)
        if isinstance(value, (int, float)) and value < 0:
            reasons.append(f"{key} cannot be negative")
            field_paths.append(f"metadata.{key}")

    coverage = event.metadata.get("citation_coverage_rate")
    if isinstance(coverage, (int, float)) and not 0 <= coverage <= 1:
        reasons.append("citation coverage rate must be between 0 and 1")
        field_paths.append("metadata.citation_coverage_rate")

    if _requires_freshness_state(event) and not _has_freshness_state(event):
        reasons.append("freshness or recent-development metric events require an explicit freshness_state")
        field_paths.append("metadata.freshness_state")

    return reasons


def _requires_freshness_state(event: TrustMetricEvent) -> bool:
    catalog_event = _catalog_by_event_type().get(event.event_type)
    return bool(catalog_event and catalog_event.requires_freshness_state)


def _has_freshness_state(event: TrustMetricEvent) -> bool:
    if event.output_metadata and event.output_metadata.freshness_state:
        return True
    value = event.metadata.get("freshness_state")
    return isinstance(value, str) and value in {state.value for state in FreshnessState}


def _event_latency_ms(event: TrustMetricEvent) -> int | None:
    if event.output_metadata and event.output_metadata.latency_ms is not None:
        return event.output_metadata.latency_ms
    value = event.metadata.get("latency_ms")
    if isinstance(value, int):
        return value
    return None


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
