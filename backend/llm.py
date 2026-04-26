from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Sequence

from backend.citations import CitationEvidence, CitationValidationClaim, CitationValidationContext, validate_claims
from backend.models import (
    LlmAnswerState,
    LlmCacheEligibilityDecision,
    LlmFallbackDecision,
    LlmFallbackTrigger,
    LlmGenerationAttemptMetadata,
    LlmGenerationAttemptStatus,
    LlmGenerationRequestMetadata,
    LlmLiveGateState,
    LlmModelDescriptor,
    LlmModelTier,
    LlmOrchestrationResult,
    LlmProviderKind,
    LlmPublicResponseMetadata,
    LlmReadinessStatus,
    LlmRuntimeConfig,
    LlmRuntimeDiagnosticsResponse,
    LlmRuntimeMode,
    LlmTransportMode,
    LlmTransportResult,
    LlmTransportStatus,
    LlmValidationResult,
    LlmValidationStatus,
)
from backend.safety import find_forbidden_output_phrases
from backend.llm_transport import TransportCallable, call_openrouter_transport


LLM_CONTRACT_SCHEMA_VERSION = "llm-runtime-contract-v1"
DEFAULT_MOCK_MODEL = "deterministic-mock-llm"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_FREE_MODEL_ORDER = (
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b-it:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
)
DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL = "deepseek/deepseek-v3.2"
DEFAULT_VALIDATION_RETRY_COUNT = 1
LLM_VALIDATION_GATE_CODES = (
    "schema_validation_required",
    "citation_validation_required",
    "same_asset_or_comparison_pack_source_binding_required",
    "source_use_policy_required",
    "freshness_uncertainty_labels_required",
    "safety_validation_required",
    "one_repair_retry_metadata_required",
    "reasoning_summary_only_required",
)

HIDDEN_PROMPT_MARKERS = (
    "system prompt",
    "developer message",
    "hidden prompt",
    "prompt_version_secret",
)
RAW_REASONING_MARKERS = (
    "reasoning_details",
    "chain of thought",
    "raw reasoning",
    "scratchpad",
)
UNRESTRICTED_SOURCE_TEXT_MARKERS = (
    "raw source text:",
    "unrestricted source text",
    "full restricted article",
    "verbatim source chunk",
)
PREDICTION_OR_TARGET_MARKERS = (
    "price target",
    "guaranteed" + " return",
    "will definitely",
    "certainty about future returns",
)


def build_llm_runtime_config(
    settings: dict[str, str | bool | int | None] | None = None,
    *,
    server_side_key_present: bool = False,
) -> LlmRuntimeConfig:
    """Build sanitized LLM runtime metadata from explicit settings only.

    The helper intentionally does not read the process environment. Tests and
    deployment wiring can pass a boolean key-presence flag without exposing a
    secret value to this contract.
    """

    settings = settings or {}
    provider_kind = _provider_kind(_setting(settings, "LLM_PROVIDER", "mock"))
    live_enabled = _bool_setting(settings, "LLM_LIVE_GENERATION_ENABLED", False)
    validation_retry_count = _int_setting(settings, "LLM_VALIDATION_RETRY_COUNT", DEFAULT_VALIDATION_RETRY_COUNT)
    reasoning_summary_only = _bool_setting(settings, "LLM_REASONING_SUMMARY_ONLY", True)
    validation_ready = validation_retry_count >= 1 and reasoning_summary_only

    if provider_kind is LlmProviderKind.mock:
        return LlmRuntimeConfig(
            provider_kind=LlmProviderKind.mock,
            runtime_mode=LlmRuntimeMode.deterministic_mock,
            readiness_status=LlmReadinessStatus.disabled_by_default,
            live_generation_enabled=False,
            live_gate_state=LlmLiveGateState.disabled,
            server_side_key_present=False,
            base_url_configured=False,
            model_chain_configured=True,
            endpoint_configured=False,
            configured_model_chain=[
                LlmModelDescriptor(
                    provider_kind=LlmProviderKind.mock,
                    model_name=DEFAULT_MOCK_MODEL,
                    tier=LlmModelTier.mock,
                    order=1,
                )
            ],
            paid_fallback_model=None,
            paid_fallback_enabled=False,
            validation_retry_count=validation_retry_count,
            reasoning_summary_only=True,
            validation_ready=True,
            validation_gates=list(LLM_VALIDATION_GATE_CODES),
            live_network_calls_allowed=False,
            unavailable_reasons=["mock_provider_is_default", "live_generation_disabled_by_default"],
        )

    base_url = _setting(settings, "OPENROUTER_BASE_URL")
    free_model_order = _model_order(_setting(settings, "OPENROUTER_FREE_MODEL_ORDER"))
    paid_fallback_model_name = _setting(settings, "OPENROUTER_PAID_FALLBACK_MODEL")
    paid_fallback_enabled = _bool_setting(settings, "OPENROUTER_PAID_FALLBACK_ENABLED", True)
    base_url_configured = bool(base_url)
    model_chain_configured = bool(free_model_order)
    paid_fallback_configured = bool(paid_fallback_model_name)
    endpoint_configured = bool(base_url_configured and model_chain_configured and paid_fallback_configured)
    unavailable_reasons: list[str] = []
    if not live_enabled:
        unavailable_reasons.append("live_generation_flag_disabled")
    if not server_side_key_present:
        unavailable_reasons.append("server_side_key_presence_flag_missing")
    if not base_url:
        unavailable_reasons.append("openrouter_base_url_missing")
    if not free_model_order:
        unavailable_reasons.append("openrouter_free_model_order_missing")
    if not paid_fallback_model_name:
        unavailable_reasons.append("openrouter_paid_fallback_model_missing")
    if validation_retry_count < 1:
        unavailable_reasons.append("validation_retry_count_below_minimum")
    if not reasoning_summary_only:
        unavailable_reasons.append("reasoning_summary_only_disabled")

    enabled = live_enabled and server_side_key_present and endpoint_configured and validation_ready
    readiness_status = _readiness_status(
        live_enabled=live_enabled,
        server_side_key_present=server_side_key_present,
        endpoint_configured=endpoint_configured,
        validation_ready=validation_ready,
    )
    return LlmRuntimeConfig(
        provider_kind=LlmProviderKind.openrouter,
        runtime_mode=LlmRuntimeMode.gated_live,
        readiness_status=readiness_status,
        live_generation_enabled=live_enabled,
        live_gate_state=LlmLiveGateState.enabled if enabled else LlmLiveGateState.unavailable,
        server_side_key_present=server_side_key_present,
        base_url_configured=base_url_configured,
        model_chain_configured=model_chain_configured,
        endpoint_configured=endpoint_configured,
        configured_model_chain=[
            LlmModelDescriptor(
                provider_kind=LlmProviderKind.openrouter,
                model_name=model_name,
                tier=LlmModelTier.free,
                order=index + 1,
            )
            for index, model_name in enumerate(free_model_order)
        ],
        paid_fallback_model=LlmModelDescriptor(
            provider_kind=LlmProviderKind.openrouter,
            model_name=paid_fallback_model_name or DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL,
            tier=LlmModelTier.paid,
            order=len(free_model_order) + 1,
        ),
        paid_fallback_enabled=paid_fallback_enabled,
        validation_retry_count=validation_retry_count,
        reasoning_summary_only=reasoning_summary_only,
        validation_ready=validation_ready,
        validation_gates=list(LLM_VALIDATION_GATE_CODES),
        live_network_calls_allowed=False,
        unavailable_reasons=unavailable_reasons,
    )


def default_openrouter_settings() -> dict[str, str]:
    return {
        "LLM_PROVIDER": "openrouter",
        "LLM_LIVE_GENERATION_ENABLED": "true",
        "OPENROUTER_BASE_URL": DEFAULT_OPENROUTER_BASE_URL,
        "OPENROUTER_FREE_MODEL_ORDER": ",".join(DEFAULT_OPENROUTER_FREE_MODEL_ORDER),
        "OPENROUTER_PAID_FALLBACK_MODEL": DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL,
        "OPENROUTER_PAID_FALLBACK_ENABLED": "true",
        "LLM_VALIDATION_RETRY_COUNT": str(DEFAULT_VALIDATION_RETRY_COUNT),
        "LLM_REASONING_SUMMARY_ONLY": "true",
    }


def validate_llm_generated_output(
    *,
    output_text: str,
    schema_valid: bool,
    claims: Sequence[CitationValidationClaim | dict[str, Any]] | None = None,
    evidence: Sequence[CitationEvidence | dict[str, Any]] | None = None,
    citation_context: CitationValidationContext | dict[str, Any] | None = None,
    freshness_labels_valid: bool = True,
    unsupported_claim_codes: Sequence[str] | None = None,
    weekly_news_rules_valid: bool = True,
) -> LlmValidationResult:
    validation_errors: list[str] = []
    if not schema_valid:
        validation_errors.append("schema_invalid")

    citation_report = None
    if claims is not None:
        citation_report = validate_claims(claims, evidence or [], citation_context or {"allowed_asset_tickers": []})
        if not citation_report.valid:
            validation_errors.append(f"citation_{citation_report.status.value}")

    safety_hits = find_forbidden_output_phrases(output_text)
    normalized_output = _normalize_text(output_text)
    prediction_hits = [marker for marker in PREDICTION_OR_TARGET_MARKERS if marker in normalized_output]
    if safety_hits or prediction_hits:
        validation_errors.extend([f"safety_{hit}" for hit in [*safety_hits, *prediction_hits]])
    if not freshness_labels_valid:
        validation_errors.append("freshness_label_missing")

    unsupported_claim_codes = unsupported_claim_codes or []
    validation_errors.extend(
        f"unsupported_claim_{_compact_code(code)}" for code in unsupported_claim_codes if str(code).strip()
    )
    if not weekly_news_rules_valid:
        validation_errors.append("weekly_news_evidence_threshold_not_met")

    hidden_prompt_absent = not _contains_any(normalized_output, HIDDEN_PROMPT_MARKERS)
    raw_reasoning_absent = not _contains_any(normalized_output, RAW_REASONING_MARKERS)
    unrestricted_source_text_absent = not _contains_any(normalized_output, UNRESTRICTED_SOURCE_TEXT_MARKERS)

    if not hidden_prompt_absent:
        validation_errors.append("hidden_prompt_leakage")
    if not raw_reasoning_absent:
        validation_errors.append("raw_reasoning_leakage")
    if not unrestricted_source_text_absent:
        validation_errors.append("unrestricted_source_text_leakage")

    citations_valid = citation_report.valid if citation_report is not None else True
    source_policy_valid = not any("disallowed_source_policy" in error for error in validation_errors)
    safety_valid = not safety_hits and not prediction_hits
    unsupported_claims_absent = not unsupported_claim_codes

    status = _validation_status(
        schema_valid=schema_valid,
        citations_valid=citations_valid,
        source_policy_valid=source_policy_valid,
        freshness_labels_valid=freshness_labels_valid,
        safety_valid=safety_valid,
        hidden_prompt_absent=hidden_prompt_absent,
        raw_reasoning_absent=raw_reasoning_absent,
        unrestricted_source_text_absent=unrestricted_source_text_absent,
        unsupported_claims_absent=unsupported_claims_absent,
        weekly_news_rules_valid=weekly_news_rules_valid,
    )
    return LlmValidationResult(
        status=status,
        schema_valid=schema_valid,
        citations_valid=citations_valid,
        source_policy_valid=source_policy_valid,
        safety_valid=safety_valid,
        hidden_prompt_absent=hidden_prompt_absent,
        raw_reasoning_absent=raw_reasoning_absent,
        unrestricted_source_text_absent=unrestricted_source_text_absent,
        validation_errors=validation_errors,
    )


def decide_paid_fallback(
    *,
    runtime: LlmRuntimeConfig,
    trigger: LlmFallbackTrigger,
    current_tier: LlmModelTier = LlmModelTier.free,
    repair_attempt_count: int = DEFAULT_VALIDATION_RETRY_COUNT,
) -> LlmFallbackDecision:
    should_fallback = (
        runtime.provider_kind is LlmProviderKind.openrouter
        and runtime.paid_fallback_enabled
        and runtime.paid_fallback_model is not None
        and trigger
        in {
            LlmFallbackTrigger.free_chain_error,
            LlmFallbackTrigger.rate_limit,
            LlmFallbackTrigger.structured_output_failure,
            LlmFallbackTrigger.validation_failed_after_repair,
        }
        and (
            trigger is not LlmFallbackTrigger.validation_failed_after_repair
            or repair_attempt_count >= runtime.validation_retry_count
        )
    )
    return LlmFallbackDecision(
        should_fallback=should_fallback,
        trigger=trigger,
        from_model_tier=current_tier,
        to_model=runtime.paid_fallback_model if should_fallback else None,
        after_repair_retry=trigger is LlmFallbackTrigger.validation_failed_after_repair,
        reason=(
            "Paid fallback is considered only after the free chain errors, rate limits, structured-output "
            "failure, or validation failure after one repair retry."
            if should_fallback
            else "Paid fallback is not applicable for this deterministic contract state."
        ),
    )


def decide_cache_eligibility(
    *,
    request: LlmGenerationRequestMetadata,
    validation: LlmValidationResult,
    attempt: LlmGenerationAttemptMetadata,
    freshness_hash: str | None = None,
    input_hash: str | None = None,
    suppressed: bool = False,
    repair_attempt_output: bool = False,
) -> LlmCacheEligibilityDecision:
    rejection_reasons: list[str] = []
    if not validation.valid:
        rejection_reasons.append(f"validation_{validation.status.value}")
    if suppressed:
        rejection_reasons.append("suppressed_output")
    if repair_attempt_output or attempt.repair_attempt:
        rejection_reasons.append("repair_attempt_output")
    if attempt.status not in {
        LlmGenerationAttemptStatus.mock_succeeded,
        LlmGenerationAttemptStatus.validation_succeeded,
    }:
        rejection_reasons.append(f"attempt_{attempt.status.value}")
    if not (freshness_hash or input_hash or request.source_freshness_hash or request.knowledge_pack_hash):
        rejection_reasons.append("missing_freshness_or_input_hash")

    return LlmCacheEligibilityDecision(
        cacheable=not rejection_reasons,
        validation_status=validation.status,
        model_name=attempt.model_name,
        model_tier=attempt.model_tier,
        prompt_version=request.prompt_version,
        schema_version=request.schema_version,
        freshness_hash=freshness_hash or request.source_freshness_hash,
        input_hash=input_hash or request.knowledge_pack_hash,
        attempt_count=attempt.attempt_index,
        rejection_reasons=rejection_reasons,
    )


def run_deterministic_mock_generation(
    request: LlmGenerationRequestMetadata,
    *,
    output_text: str = "Deterministic mock generated output with cited educational context.",
    claims: Sequence[CitationValidationClaim | dict[str, Any]] | None = None,
    evidence: Sequence[CitationEvidence | dict[str, Any]] | None = None,
    citation_context: CitationValidationContext | dict[str, Any] | None = None,
) -> LlmOrchestrationResult:
    runtime = build_llm_runtime_config()
    validation = validate_llm_generated_output(
        output_text=output_text,
        schema_valid=True,
        claims=claims,
        evidence=evidence,
        citation_context=citation_context,
    )
    attempt = LlmGenerationAttemptMetadata(
        attempt_index=1,
        provider_kind=LlmProviderKind.mock,
        model_name=DEFAULT_MOCK_MODEL,
        model_tier=LlmModelTier.mock,
        status=(
            LlmGenerationAttemptStatus.mock_succeeded
            if validation.valid
            else LlmGenerationAttemptStatus.validation_failed
        ),
        validation_status=validation.status,
        latency_ms=0,
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=0.0,
    )
    fallback = decide_paid_fallback(runtime=runtime, trigger=LlmFallbackTrigger.none, current_tier=LlmModelTier.mock)
    cache_decision = decide_cache_eligibility(request=request, validation=validation, attempt=attempt)
    public_metadata = LlmPublicResponseMetadata(
        provider_kind=LlmProviderKind.mock,
        live_enabled=False,
        model_name=DEFAULT_MOCK_MODEL,
        model_tier=LlmModelTier.mock,
        validation_status=validation.status,
        attempt_count=1,
        answer_state=LlmAnswerState.complete if validation.valid else LlmAnswerState.unavailable,
        cached=False,
        latency_ms=0,
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=0.0,
        reasoning_summary="Deterministic mock response validated against schema, citations, source policy, and safety.",
    )
    return LlmOrchestrationResult(
        request=request,
        runtime=runtime,
        attempts=[attempt],
        validation=validation,
        fallback_decision=fallback,
        public_metadata=public_metadata,
        cache_decision=cache_decision,
        no_live_external_calls=True,
    )


def run_mocked_live_generation_orchestration(
    request: LlmGenerationRequestMetadata,
    *,
    runtime: LlmRuntimeConfig,
    caller_opted_in: bool = False,
    transport: TransportCallable | None = None,
    repair_transport: TransportCallable | None = None,
    schema_valid: bool = True,
    repair_schema_valid: bool | None = None,
    claims: Sequence[CitationValidationClaim | dict[str, Any]] | None = None,
    repair_claims: Sequence[CitationValidationClaim | dict[str, Any]] | None = None,
    evidence: Sequence[CitationEvidence | dict[str, Any]] | None = None,
    repair_evidence: Sequence[CitationEvidence | dict[str, Any]] | None = None,
    citation_context: CitationValidationContext | dict[str, Any] | None = None,
    repair_citation_context: CitationValidationContext | dict[str, Any] | None = None,
    freshness_labels_valid: bool = True,
    repair_freshness_labels_valid: bool | None = None,
    unsupported_claim_codes: Sequence[str] | None = None,
    repair_unsupported_claim_codes: Sequence[str] | None = None,
    weekly_news_selected_item_count: int | None = None,
    canonical_fact_citation_ids: Sequence[str] | None = None,
    request_mode: LlmTransportMode | str = LlmTransportMode.schema_mode,
) -> LlmOrchestrationResult:
    """Validate mocked live-provider output behind explicit opt-in gates.

    This is a dormant backend contract. It uses the T-097 injected transport
    boundary, models one repair retry for validation failures, and returns only
    sanitized metadata. It is not called by public routes.
    """

    diagnostics: dict[str, str | int | bool | float | None] = {
        "orchestration_contract": "llm-live-orchestration-contract-v1",
        "request_mode": _enum_value(request_mode),
        "caller_opted_in": caller_opted_in,
        "readiness_status": runtime.readiness_status.value,
        "provider_kind": runtime.provider_kind.value,
        "fallback_configured": runtime.paid_fallback_model is not None,
        "max_repair_retry_count": min(runtime.validation_retry_count, 1),
    }
    first_transport = call_openrouter_transport(
        runtime=runtime,
        request_mode=request_mode,
        caller_opted_in=caller_opted_in,
        transport=transport,
        sanitized_diagnostics={"orchestration_attempt": "initial"},
    )
    if first_transport.response.status is not LlmTransportStatus.succeeded or not first_transport.content:
        attempt = _attempt_from_transport(first_transport, attempt_index=1, validation_status=LlmValidationStatus.not_validated)
        fallback = decide_paid_fallback(
            runtime=runtime,
            trigger=_fallback_trigger_for_transport(first_transport),
            current_tier=attempt.model_tier,
        )
        validation = _not_validated_result(first_transport.response.diagnostic_code)
        cache_decision = decide_cache_eligibility(request=request, validation=validation, attempt=attempt, suppressed=True)
        return _orchestration_result(
            request=request,
            runtime=runtime,
            attempts=[attempt],
            validation=validation,
            fallback=fallback,
            cache_decision=cache_decision,
            diagnostics={
                **diagnostics,
                "validation_status": validation.status.value,
                "transport_status": first_transport.response.status.value,
                "primary_rejection_code": first_transport.response.diagnostic_code,
                "generated_content_usable": False,
            },
        )

    weekly_rules_valid = _weekly_news_analysis_rules_valid(
        request=request,
        weekly_news_selected_item_count=weekly_news_selected_item_count,
        canonical_fact_citation_ids=canonical_fact_citation_ids,
    )
    validation = validate_llm_generated_output(
        output_text=first_transport.content,
        schema_valid=schema_valid,
        claims=claims,
        evidence=evidence,
        citation_context=citation_context,
        freshness_labels_valid=freshness_labels_valid,
        unsupported_claim_codes=unsupported_claim_codes,
        weekly_news_rules_valid=weekly_rules_valid,
    )
    first_attempt = _attempt_from_transport(
        first_transport,
        attempt_index=1,
        validation_status=validation.status,
        status=(
            LlmGenerationAttemptStatus.validation_succeeded
            if validation.valid
            else LlmGenerationAttemptStatus.validation_failed
        ),
    )
    attempts = [first_attempt]
    final_validation = validation
    final_attempt = first_attempt

    if not validation.valid and runtime.validation_retry_count >= 1:
        retry_transport = repair_transport or transport
        repair_result = call_openrouter_transport(
            runtime=runtime,
            request_mode=request_mode,
            caller_opted_in=caller_opted_in,
            transport=retry_transport,
            sanitized_diagnostics={"orchestration_attempt": "repair_retry"},
        )
        if repair_result.response.status is LlmTransportStatus.succeeded and repair_result.content:
            repair_validation = validate_llm_generated_output(
                output_text=repair_result.content,
                schema_valid=schema_valid if repair_schema_valid is None else repair_schema_valid,
                claims=repair_claims if repair_claims is not None else claims,
                evidence=repair_evidence if repair_evidence is not None else evidence,
                citation_context=(
                    repair_citation_context if repair_citation_context is not None else citation_context
                ),
                freshness_labels_valid=(
                    freshness_labels_valid
                    if repair_freshness_labels_valid is None
                    else repair_freshness_labels_valid
                ),
                unsupported_claim_codes=(
                    repair_unsupported_claim_codes
                    if repair_unsupported_claim_codes is not None
                    else unsupported_claim_codes
                ),
                weekly_news_rules_valid=weekly_rules_valid,
            )
            repair_attempt = _attempt_from_transport(
                repair_result,
                attempt_index=2,
                validation_status=repair_validation.status,
                status=(
                    LlmGenerationAttemptStatus.validation_succeeded
                    if repair_validation.valid
                    else LlmGenerationAttemptStatus.validation_failed
                ),
                repair_attempt=True,
            )
            final_validation = repair_validation
            final_attempt = repair_attempt
            attempts.append(repair_attempt)
        else:
            repair_attempt = _attempt_from_transport(
                repair_result,
                attempt_index=2,
                validation_status=LlmValidationStatus.not_validated,
                repair_attempt=True,
            )
            attempts.append(repair_attempt)
            final_attempt = repair_attempt

    fallback_trigger = (
        LlmFallbackTrigger.validation_failed_after_repair
        if not final_validation.valid and len(attempts) > 1
        else LlmFallbackTrigger.none
    )
    fallback = decide_paid_fallback(
        runtime=runtime,
        trigger=fallback_trigger,
        current_tier=final_attempt.model_tier,
        repair_attempt_count=max(0, len(attempts) - 1),
    )
    generated_content_usable = final_validation.valid and final_attempt.status is LlmGenerationAttemptStatus.validation_succeeded
    cache_decision = decide_cache_eligibility(
        request=request,
        validation=final_validation,
        attempt=final_attempt,
        suppressed=not generated_content_usable,
    )
    rejection_codes = _validation_rejection_codes(final_validation)
    return _orchestration_result(
        request=request,
        runtime=runtime,
        attempts=attempts,
        validation=final_validation,
        fallback=fallback,
        cache_decision=cache_decision,
        generated_content_usable=generated_content_usable,
        diagnostics={
            **diagnostics,
            "validation_status": final_validation.status.value,
            "attempt_count": len(attempts),
            "repair_retry_attempted": len(attempts) > 1,
            "fallback_trigger": fallback.trigger.value,
            "fallback_would_execute": fallback.should_fallback,
            "cacheable": cache_decision.cacheable,
            "generated_content_usable": generated_content_usable,
            "primary_rejection_code": rejection_codes[0] if rejection_codes else None,
            "rejection_code_count": len(rejection_codes),
        },
    )


def runtime_diagnostics(
    settings: dict[str, str | bool | int | None] | None = None,
    *,
    server_side_key_present: bool = False,
) -> LlmRuntimeDiagnosticsResponse:
    runtime = build_llm_runtime_config(settings, server_side_key_present=server_side_key_present)
    return LlmRuntimeDiagnosticsResponse(
        runtime=runtime,
        public_metadata_fields=sorted(LlmPublicResponseMetadata.model_fields),
        credential_values_exposed=False,
        private_prompt_fields_exposed=False,
        model_reasoning_payload_exposed=False,
        restricted_source_payload_exposed=False,
        no_live_external_calls=True,
    )


def _orchestration_result(
    *,
    request: LlmGenerationRequestMetadata,
    runtime: LlmRuntimeConfig,
    attempts: list[LlmGenerationAttemptMetadata],
    validation: LlmValidationResult,
    fallback: LlmFallbackDecision,
    cache_decision: LlmCacheEligibilityDecision,
    diagnostics: dict[str, str | int | bool | float | None],
    generated_content_usable: bool = False,
) -> LlmOrchestrationResult:
    final_attempt = attempts[-1]
    public_metadata = LlmPublicResponseMetadata(
        provider_kind=runtime.provider_kind,
        live_enabled=runtime.live_generation_enabled,
        model_name=final_attempt.model_name,
        model_tier=final_attempt.model_tier,
        validation_status=validation.status,
        attempt_count=len([attempt for attempt in attempts if attempt.attempt_index > 0]),
        answer_state=(
            LlmAnswerState.complete
            if generated_content_usable
            else (LlmAnswerState.partial if fallback.should_fallback else LlmAnswerState.unavailable)
        ),
        cached=False,
        latency_ms=_sum_ints(attempt.latency_ms for attempt in attempts),
        prompt_tokens=_sum_ints(attempt.prompt_tokens for attempt in attempts),
        completion_tokens=_sum_ints(attempt.completion_tokens for attempt in attempts),
        cost_usd=_sum_floats(attempt.cost_usd for attempt in attempts),
        reasoning_summary=(
            "Mocked live-generation artifact passed validation gates."
            if generated_content_usable
            else "Mocked live-generation artifact is unavailable or validation-limited."
        ),
    )
    return LlmOrchestrationResult(
        request=request,
        runtime=runtime,
        attempts=attempts,
        validation=validation,
        fallback_decision=fallback,
        public_metadata=public_metadata,
        cache_decision=cache_decision,
        generated_content_usable=generated_content_usable,
        sanitized_diagnostics=_sanitize_orchestration_diagnostics(diagnostics),
        no_live_external_calls=True,
    )


def _attempt_from_transport(
    transport_result: LlmTransportResult,
    *,
    attempt_index: int,
    validation_status: LlmValidationStatus,
    status: LlmGenerationAttemptStatus | None = None,
    repair_attempt: bool = False,
) -> LlmGenerationAttemptMetadata:
    response = transport_result.response
    active_model = transport_result.request.active_model if transport_result.request else None
    model_name = response.model_name or (active_model.model_name if active_model else "unavailable")
    model_tier = response.model_tier or (active_model.tier if active_model else LlmModelTier.unavailable)
    return LlmGenerationAttemptMetadata(
        attempt_index=attempt_index,
        provider_kind=response.provider_kind,
        model_name=model_name,
        model_tier=model_tier,
        status=status or _attempt_status_for_transport(response.status),
        validation_status=validation_status,
        repair_attempt=repair_attempt,
        latency_ms=response.latency_ms,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        cost_usd=response.cost_usd,
    )


def _attempt_status_for_transport(status: LlmTransportStatus) -> LlmGenerationAttemptStatus:
    if status is LlmTransportStatus.blocked:
        return LlmGenerationAttemptStatus.blocked
    if status is LlmTransportStatus.nonretryable_provider_error:
        return LlmGenerationAttemptStatus.structured_output_failed
    if status in {LlmTransportStatus.invalid_response_shape, LlmTransportStatus.missing_content}:
        return LlmGenerationAttemptStatus.structured_output_failed
    if status is LlmTransportStatus.retryable_provider_error:
        return LlmGenerationAttemptStatus.provider_error
    if status is LlmTransportStatus.timeout:
        return LlmGenerationAttemptStatus.provider_error
    return LlmGenerationAttemptStatus.validation_failed


def _fallback_trigger_for_transport(transport_result: LlmTransportResult) -> LlmFallbackTrigger:
    response = transport_result.response
    if response.provider_status == "http_429":
        return LlmFallbackTrigger.rate_limit
    if response.status in {LlmTransportStatus.invalid_response_shape, LlmTransportStatus.missing_content}:
        return LlmFallbackTrigger.structured_output_failure
    if response.status in {LlmTransportStatus.retryable_provider_error, LlmTransportStatus.timeout}:
        return LlmFallbackTrigger.free_chain_error
    return LlmFallbackTrigger.none


def _not_validated_result(reason_code: str) -> LlmValidationResult:
    return LlmValidationResult(
        status=LlmValidationStatus.not_validated,
        schema_valid=False,
        citations_valid=False,
        source_policy_valid=False,
        safety_valid=False,
        hidden_prompt_absent=True,
        raw_reasoning_absent=True,
        unrestricted_source_text_absent=True,
        validation_errors=[_compact_code(reason_code)],
    )


def _weekly_news_analysis_rules_valid(
    *,
    request: LlmGenerationRequestMetadata,
    weekly_news_selected_item_count: int | None,
    canonical_fact_citation_ids: Sequence[str] | None,
) -> bool:
    if request.output_kind != "weekly_news_analysis":
        return True
    return (weekly_news_selected_item_count or 0) >= 2 and bool(canonical_fact_citation_ids)


def _validation_rejection_codes(validation: LlmValidationResult) -> list[str]:
    if validation.valid:
        return []
    return [_compact_code(error) for error in validation.validation_errors] or [validation.status.value]


def _sanitize_orchestration_diagnostics(
    diagnostics: dict[str, str | int | bool | float | None],
) -> dict[str, str | int | bool | float | None]:
    forbidden = (
        "prompt",
        "question",
        "answer",
        "transcript",
        "source_text",
        "source_url",
        "authorization",
        "credential",
        "password",
        "token",
        "signed_url",
        "public_url",
        "storage_path",
        "reasoning",
        "generated_text",
    )
    sanitized: dict[str, str | int | bool | float | None] = {}
    for key, value in diagnostics.items():
        normalized_key = key.lower()
        if any(marker in normalized_key for marker in forbidden):
            continue
        if isinstance(value, str) and any(marker in value.lower() for marker in forbidden):
            continue
        sanitized[key] = value
    return sanitized


def _sum_ints(values: Iterable[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _sum_floats(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _provider_kind(value: str | None) -> LlmProviderKind:
    if (value or "mock").strip().lower() == "openrouter":
        return LlmProviderKind.openrouter
    return LlmProviderKind.mock


def _model_order(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    models = tuple(model.strip() for model in value.split(",") if model.strip())
    return models


def _setting(settings: dict[str, str | bool | int | None], key: str, default: str | None = None) -> str | None:
    value = settings.get(key, default)
    if value is None:
        return None
    return str(value).strip()


def _bool_setting(settings: dict[str, str | bool | int | None], key: str, default: bool) -> bool:
    value = settings.get(key, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _int_setting(settings: dict[str, str | bool | int | None], key: str, default: int) -> int:
    value = settings.get(key, default)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _readiness_status(
    *,
    live_enabled: bool,
    server_side_key_present: bool,
    endpoint_configured: bool,
    validation_ready: bool,
) -> LlmReadinessStatus:
    if not live_enabled:
        return LlmReadinessStatus.disabled_by_default
    if not server_side_key_present or not endpoint_configured:
        return LlmReadinessStatus.unavailable
    if not validation_ready:
        return LlmReadinessStatus.validation_not_ready
    return LlmReadinessStatus.ready_for_explicit_live_call


def _validation_status(
    *,
    schema_valid: bool,
    citations_valid: bool,
    source_policy_valid: bool,
    freshness_labels_valid: bool,
    safety_valid: bool,
    hidden_prompt_absent: bool,
    raw_reasoning_absent: bool,
    unrestricted_source_text_absent: bool,
    unsupported_claims_absent: bool,
    weekly_news_rules_valid: bool,
) -> LlmValidationStatus:
    if not schema_valid:
        return LlmValidationStatus.invalid_schema
    if not citations_valid:
        return LlmValidationStatus.invalid_citation
    if not source_policy_valid:
        return LlmValidationStatus.invalid_source_policy
    if not freshness_labels_valid:
        return LlmValidationStatus.invalid_freshness
    if not safety_valid:
        return LlmValidationStatus.invalid_safety
    if not hidden_prompt_absent:
        return LlmValidationStatus.invalid_hidden_prompt
    if not raw_reasoning_absent:
        return LlmValidationStatus.invalid_raw_reasoning
    if not unrestricted_source_text_absent:
        return LlmValidationStatus.invalid_unrestricted_source_text
    if not unsupported_claims_absent:
        return LlmValidationStatus.invalid_unsupported_claim
    if not weekly_news_rules_valid:
        return LlmValidationStatus.invalid_weekly_news_evidence
    return LlmValidationStatus.valid


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _enum_value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _compact_code(value: Any) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in str(value).strip().lower())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")[:80] or "unknown"
