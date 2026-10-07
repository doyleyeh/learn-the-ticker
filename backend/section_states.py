from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.models import (
    AnalysisPackRuntimeMetadata,
    EvidenceState,
    Freshness,
    FreshnessState,
    LightweightApiFallbackDiagnostics,
    RuntimeSectionState,
    RuntimeDiagnosticValue,
    StateMessage,
)


SECTION_STATE_DURABLE_ORIGIN = "durable_repository"
SECTION_STATE_CACHE_ORIGIN = "generated_output_cache"
SECTION_STATE_BACKEND_GENERATED_ORIGIN = "backend_generated"
SECTION_STATE_LIGHTWEIGHT_ORIGIN = "lightweight_fallback"
SECTION_STATE_FIXTURE_ORIGIN = "deterministic_fixture"
SECTION_STATE_UNAVAILABLE_ORIGIN = "unavailable"


def runtime_section_state(
    section_id: str,
    label: str,
    *,
    data_origin: str,
    section_status: str = "available",
    fallback_reason: str | None = None,
    freshness_state: str | FreshnessState | None = None,
    source_handoff_state: str = "not_applicable",
    cache_state: str | None = None,
    evidence_state: str | EvidenceState | None = None,
    diagnostics: dict[str, RuntimeDiagnosticValue] | None = None,
) -> RuntimeSectionState:
    return RuntimeSectionState(
        section_id=section_id,
        label=label,
        data_origin=data_origin,
        section_status=section_status,
        fallback_reason=fallback_reason,
        freshness_state=_value(freshness_state),
        source_handoff_state=source_handoff_state,
        cache_state=cache_state,
        evidence_state=_value(evidence_state),
        diagnostics=diagnostics or {},
    )


def response_section_state(
    response: Any,
    section_id: str,
    label: str,
    *,
    data_origin: str | None = None,
    section_status: str | None = None,
    fallback_reason: str | None = None,
    freshness_state: str | FreshnessState | None = None,
    evidence_state: str | EvidenceState | None = None,
    cache_state: str | None = None,
    diagnostics: dict[str, RuntimeDiagnosticValue] | None = None,
) -> RuntimeSectionState:
    resolved_origin = data_origin or infer_data_origin(response)
    resolved_status = section_status or infer_section_status(response)
    resolved_freshness = freshness_state or infer_freshness_state(response)
    resolved_evidence = evidence_state or infer_evidence_state(response, resolved_status)
    resolved_fallback = fallback_reason or infer_fallback_reason(response, resolved_origin)
    diagnostic_payload: dict[str, RuntimeDiagnosticValue] = {
        "metadata_inferred": True,
        "section_state_schema": "runtime-section-state-v1",
    }
    if diagnostics:
        diagnostic_payload.update(diagnostics)

    return runtime_section_state(
        section_id,
        label,
        data_origin=resolved_origin,
        section_status=resolved_status,
        fallback_reason=resolved_fallback,
        freshness_state=resolved_freshness,
        source_handoff_state=infer_source_handoff_state(response, resolved_origin),
        cache_state=cache_state or infer_cache_state(response, resolved_origin),
        evidence_state=resolved_evidence,
        diagnostics=diagnostic_payload,
    )


def with_section_states(response: Any, states: list[RuntimeSectionState]) -> Any:
    if not isinstance(response, BaseModel):
        return response
    existing = list(getattr(response, "section_states", []) or [])
    merged = _merge_section_states(existing, states)
    return response.model_copy(update={"section_states": merged})


def infer_data_origin(response: Any) -> str:
    fallback_diagnostics = getattr(response, "fallback_diagnostics", None)
    if isinstance(fallback_diagnostics, LightweightApiFallbackDiagnostics):
        return SECTION_STATE_LIGHTWEIGHT_ORIGIN

    metadata = getattr(response, "analysis_pack_metadata", None)
    if isinstance(metadata, AnalysisPackRuntimeMetadata):
        if metadata.analysis_source == "imported_local_pack":
            return SECTION_STATE_DURABLE_ORIGIN
        if metadata.analysis_source == "backend_generated":
            return SECTION_STATE_BACKEND_GENERATED_ORIGIN
        if metadata.analysis_source == "deterministic_fixture":
            return SECTION_STATE_FIXTURE_ORIGIN

    if getattr(response, "cache_revalidation", None) is not None:
        cache_revalidation = getattr(response, "cache_revalidation")
        if getattr(cache_revalidation, "reusable", False):
            return SECTION_STATE_CACHE_ORIGIN

    return SECTION_STATE_FIXTURE_ORIGIN


def infer_section_status(response: Any) -> str:
    state = getattr(response, "state", None)
    state_value = _value(state)
    if isinstance(state, StateMessage):
        state_value = _value(state.status)
    if state_value == "supported":
        return "available"
    if state_value in {"available", "succeeded"}:
        return "available"
    if state_value in {"no_high_signal"}:
        return "empty"
    if state_value in {"partial", "stale", "unknown", "unavailable", "insufficient_evidence", "suppressed"}:
        return state_value
    if state_value in {"unsupported", "out_of_scope", "eligible_not_cached"}:
        return state_value
    return "available"


def infer_freshness_state(response: Any) -> str | None:
    explicit = getattr(response, "freshness_state", None)
    if explicit is not None:
        return _value(explicit)
    freshness = getattr(response, "freshness", None)
    if isinstance(freshness, Freshness):
        return _value(freshness.freshness_state)
    evidence_state = _value(getattr(response, "evidence_state", None))
    if evidence_state in {"partial", "stale", "unknown", "unavailable", "insufficient_evidence"}:
        return evidence_state
    if getattr(response, "window", None) is not None:
        return "fresh"
    return None


def infer_evidence_state(response: Any, section_status: str) -> str | None:
    explicit = getattr(response, "evidence_state", None)
    if explicit is not None:
        return _value(explicit)
    if section_status == "available":
        return "supported"
    if section_status == "empty":
        return "no_high_signal"
    if section_status in {"partial", "stale", "unknown", "unavailable", "insufficient_evidence", "unsupported"}:
        return section_status
    return None


def infer_fallback_reason(response: Any, data_origin: str) -> str | None:
    fallback_diagnostics = getattr(response, "fallback_diagnostics", None)
    if isinstance(fallback_diagnostics, LightweightApiFallbackDiagnostics):
        if fallback_diagnostics.reason_codes:
            return ",".join(fallback_diagnostics.reason_codes)
        return fallback_diagnostics.source_path
    if data_origin == SECTION_STATE_FIXTURE_ORIGIN:
        return "deterministic_fixture_fallback"
    return None


def infer_source_handoff_state(response: Any, data_origin: str) -> str:
    if data_origin in {SECTION_STATE_DURABLE_ORIGIN, SECTION_STATE_CACHE_ORIGIN, SECTION_STATE_BACKEND_GENERATED_ORIGIN}:
        return "approved"
    if data_origin == SECTION_STATE_LIGHTWEIGHT_ORIGIN:
        return "lightweight_labeled"
    return "not_applicable"


def infer_cache_state(response: Any, data_origin: str) -> str:
    cache_revalidation = getattr(response, "cache_revalidation", None)
    if cache_revalidation is not None:
        return _value(getattr(cache_revalidation, "state", None)) or "unknown"
    if data_origin == SECTION_STATE_CACHE_ORIGIN:
        return "hit"
    return "not_applicable"


def _merge_section_states(
    existing: list[RuntimeSectionState],
    additions: list[RuntimeSectionState],
) -> list[RuntimeSectionState]:
    by_id = {state.section_id: state for state in existing}
    for state in additions:
        by_id[state.section_id] = state
    return list(by_id.values())


def _value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
