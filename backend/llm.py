from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

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
    LlmRuntimeConfig,
    LlmRuntimeDiagnosticsResponse,
    LlmRuntimeMode,
    LlmValidationResult,
    LlmValidationStatus,
)
from backend.safety import find_forbidden_output_phrases


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

    if provider_kind is LlmProviderKind.mock:
        return LlmRuntimeConfig(
            provider_kind=LlmProviderKind.mock,
            runtime_mode=LlmRuntimeMode.deterministic_mock,
            live_generation_enabled=False,
            live_gate_state=LlmLiveGateState.disabled,
            server_side_key_present=False,
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
            live_network_calls_allowed=False,
            unavailable_reasons=["mock_provider_is_default"],
        )

    base_url = _setting(settings, "OPENROUTER_BASE_URL")
    free_model_order = _model_order(_setting(settings, "OPENROUTER_FREE_MODEL_ORDER"))
    paid_fallback_model_name = _setting(settings, "OPENROUTER_PAID_FALLBACK_MODEL")
    paid_fallback_enabled = _bool_setting(settings, "OPENROUTER_PAID_FALLBACK_ENABLED", True)
    endpoint_configured = bool(base_url and free_model_order and paid_fallback_model_name)
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

    enabled = live_enabled and server_side_key_present and endpoint_configured
    return LlmRuntimeConfig(
        provider_kind=LlmProviderKind.openrouter,
        runtime_mode=LlmRuntimeMode.gated_live,
        live_generation_enabled=live_enabled,
        live_gate_state=LlmLiveGateState.enabled if enabled else LlmLiveGateState.unavailable,
        server_side_key_present=server_side_key_present,
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

    status = _validation_status(
        schema_valid=schema_valid,
        citations_valid=citations_valid,
        source_policy_valid=source_policy_valid,
        safety_valid=safety_valid,
        hidden_prompt_absent=hidden_prompt_absent,
        raw_reasoning_absent=raw_reasoning_absent,
        unrestricted_source_text_absent=unrestricted_source_text_absent,
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


def _validation_status(
    *,
    schema_valid: bool,
    citations_valid: bool,
    source_policy_valid: bool,
    safety_valid: bool,
    hidden_prompt_absent: bool,
    raw_reasoning_absent: bool,
    unrestricted_source_text_absent: bool,
) -> LlmValidationStatus:
    if not schema_valid:
        return LlmValidationStatus.invalid_schema
    if not citations_valid:
        return LlmValidationStatus.invalid_citation
    if not source_policy_valid:
        return LlmValidationStatus.invalid_source_policy
    if not safety_valid:
        return LlmValidationStatus.invalid_safety
    if not hidden_prompt_absent:
        return LlmValidationStatus.invalid_hidden_prompt
    if not raw_reasoning_absent:
        return LlmValidationStatus.invalid_raw_reasoning
    if not unrestricted_source_text_absent:
        return LlmValidationStatus.invalid_unrestricted_source_text
    return LlmValidationStatus.valid


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _enum_value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)
