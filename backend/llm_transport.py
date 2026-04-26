from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from backend.models import (
    LlmModelDescriptor,
    LlmModelTier,
    LlmProviderKind,
    LlmReadinessStatus,
    LlmRuntimeConfig,
    LlmTransportMode,
    LlmTransportRequestMetadata,
    LlmTransportResponseMetadata,
    LlmTransportResult,
    LlmTransportRetryability,
    LlmTransportStatus,
)


OPENROUTER_TRANSPORT_CONTRACT_VERSION = "llm-transport-contract-v1"
DEFAULT_TRANSPORT_TIMEOUT_SECONDS = 30
OPENROUTER_CHAT_COMPLETIONS_PATH = "/chat/completions"
TransportCallable = Callable[[LlmTransportRequestMetadata], Mapping[str, Any]]

_BLOCKED_BY_READINESS = "blocked_by_readiness"
_FORBIDDEN_DIAGNOSTIC_KEY_MARKERS = (
    "prompt",
    "message",
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
)
_FORBIDDEN_DIAGNOSTIC_VALUE_MARKERS = (
    "bearer ",
    "reasoning_details",
    "raw_source_text",
    "raw prompt",
    "raw user",
    "raw generated",
    "BEGIN PRIVATE KEY",
)


def call_openrouter_transport(
    *,
    runtime: LlmRuntimeConfig,
    request_mode: LlmTransportMode | str,
    caller_opted_in: bool = False,
    transport: TransportCallable | None = None,
    sanitized_diagnostics: Mapping[str, Any] | None = None,
    timeout_seconds: int = DEFAULT_TRANSPORT_TIMEOUT_SECONDS,
) -> LlmTransportResult:
    """Run the dormant OpenRouter transport boundary with an injected callable.

    This contract never imports a network client and never reads process
    configuration. The only executable path is an explicitly injected callable,
    which keeps normal tests and local runs deterministic.
    """

    mode = _transport_mode(request_mode)
    diagnostics = _sanitize_diagnostics(sanitized_diagnostics)
    block_code = _blocked_code(runtime, caller_opted_in=caller_opted_in, transport=transport)
    if block_code is not None:
        return _blocked_result(
            runtime=runtime,
            mode=mode,
            diagnostic_code=block_code,
            diagnostics=diagnostics,
            timeout_seconds=timeout_seconds,
        )

    request = build_openrouter_transport_request(
        runtime=runtime,
        request_mode=mode,
        sanitized_diagnostics=diagnostics,
        timeout_seconds=timeout_seconds,
    )
    try:
        provider_response = transport(request)
    except TimeoutError:
        return _result_from_status(
            request=request,
            status=LlmTransportStatus.timeout,
            retryability=LlmTransportRetryability.retryable,
            diagnostic_code="timeout",
            provider_status="timeout",
        )
    except Exception:
        return _result_from_status(
            request=request,
            status=LlmTransportStatus.retryable_provider_error,
            retryability=LlmTransportRetryability.retryable,
            diagnostic_code="retryable_provider_error",
            provider_status="exception",
        )

    return _parse_provider_response(request, provider_response)


def build_openrouter_transport_request(
    *,
    runtime: LlmRuntimeConfig,
    request_mode: LlmTransportMode | str,
    sanitized_diagnostics: Mapping[str, Any] | None = None,
    timeout_seconds: int = DEFAULT_TRANSPORT_TIMEOUT_SECONDS,
) -> LlmTransportRequestMetadata:
    mode = _transport_mode(request_mode)
    diagnostics = _sanitize_diagnostics(sanitized_diagnostics)
    timeout = max(1, int(timeout_seconds))
    active_model = runtime.configured_model_chain[0] if runtime.configured_model_chain else None
    return LlmTransportRequestMetadata(
        provider_kind=LlmProviderKind.openrouter,
        request_mode=mode,
        active_model=active_model,
        configured_model_chain=list(runtime.configured_model_chain),
        paid_fallback_model=runtime.paid_fallback_model,
        base_url_configured=runtime.base_url_configured,
        model_chain_configured=runtime.model_chain_configured,
        endpoint_configured=runtime.endpoint_configured,
        validation_retry_count=runtime.validation_retry_count,
        reasoning_summary_only=runtime.reasoning_summary_only,
        timeout_seconds=timeout,
        retryable=True,
        sanitized_diagnostics={
            **diagnostics,
            "endpoint_path": OPENROUTER_CHAT_COMPLETIONS_PATH,
            "schema_mode": mode is LlmTransportMode.schema_mode,
            "json_mode": mode is LlmTransportMode.json_mode,
        },
    )


def _blocked_code(
    runtime: LlmRuntimeConfig,
    *,
    caller_opted_in: bool,
    transport: TransportCallable | None,
) -> str | None:
    if runtime.provider_kind is not LlmProviderKind.openrouter:
        return "provider_not_openrouter"
    if not runtime.live_generation_enabled:
        return "live_generation_disabled"
    if not runtime.server_side_key_present:
        return "server_side_key_missing"
    if not runtime.base_url_configured:
        return "openrouter_base_url_missing"
    if not runtime.model_chain_configured or not runtime.configured_model_chain:
        return "openrouter_model_chain_missing"
    if not runtime.endpoint_configured:
        return "openrouter_endpoint_incomplete"
    if not runtime.validation_ready or runtime.readiness_status is LlmReadinessStatus.validation_not_ready:
        return "validation_not_ready"
    if runtime.readiness_status is not LlmReadinessStatus.ready_for_explicit_live_call:
        return _BLOCKED_BY_READINESS
    if not caller_opted_in:
        return "explicit_live_transport_opt_in_missing"
    if transport is None:
        return "injected_transport_missing"
    return None


def _blocked_result(
    *,
    runtime: LlmRuntimeConfig,
    mode: LlmTransportMode,
    diagnostic_code: str,
    diagnostics: dict[str, str | int | bool | float | None],
    timeout_seconds: int,
) -> LlmTransportResult:
    request = build_openrouter_transport_request(
        runtime=runtime,
        request_mode=mode,
        sanitized_diagnostics=diagnostics,
        timeout_seconds=timeout_seconds,
    )
    return _result_from_status(
        request=request,
        status=LlmTransportStatus.blocked,
        retryability=LlmTransportRetryability.not_applicable,
        diagnostic_code=diagnostic_code,
        provider_status="blocked",
    )


def _parse_provider_response(
    request: LlmTransportRequestMetadata,
    provider_response: Mapping[str, Any],
) -> LlmTransportResult:
    status_code = _int_or_none(provider_response.get("status_code"))
    provider_status = _provider_status(status_code)
    if status_code is not None and status_code >= 400:
        retryable = status_code == 429 or status_code >= 500
        return _result_from_status(
            request=request,
            status=(
                LlmTransportStatus.retryable_provider_error
                if retryable
                else LlmTransportStatus.nonretryable_provider_error
            ),
            retryability=(
                LlmTransportRetryability.retryable
                if retryable
                else LlmTransportRetryability.nonretryable
            ),
            diagnostic_code=(
                "retryable_provider_error"
                if retryable
                else "nonretryable_provider_error"
            ),
            provider_status=provider_status,
            latency_ms=_int_or_none(provider_response.get("latency_ms")),
        )

    body = provider_response.get("json")
    if not isinstance(body, Mapping):
        return _result_from_status(
            request=request,
            status=LlmTransportStatus.invalid_response_shape,
            retryability=LlmTransportRetryability.nonretryable,
            diagnostic_code="invalid_response_shape",
            provider_status=provider_status,
            latency_ms=_int_or_none(provider_response.get("latency_ms")),
        )

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
        return _result_from_status(
            request=request,
            status=LlmTransportStatus.invalid_response_shape,
            retryability=LlmTransportRetryability.nonretryable,
            diagnostic_code="invalid_response_shape",
            provider_status=provider_status,
            latency_ms=_int_or_none(provider_response.get("latency_ms")),
        )

    first_choice = choices[0]
    message = first_choice.get("message")
    content = _message_content(message)
    if content is None:
        return _result_from_status(
            request=request,
            status=LlmTransportStatus.missing_content,
            retryability=LlmTransportRetryability.retryable,
            diagnostic_code="missing_content",
            provider_status=provider_status,
            finish_reason=_string_or_none(first_choice.get("finish_reason")),
            latency_ms=_int_or_none(provider_response.get("latency_ms")),
        )

    model_name = _string_or_none(body.get("model")) or _active_model_name(request)
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    model_tier = _model_tier(model_name, request)
    return LlmTransportResult(
        request=request,
        response=LlmTransportResponseMetadata(
            provider_kind=LlmProviderKind.openrouter,
            status=LlmTransportStatus.succeeded,
            retryability=LlmTransportRetryability.not_applicable,
            diagnostic_code="ok",
            request_mode=request.request_mode,
            model_name=model_name,
            model_tier=model_tier,
            provider_status=provider_status,
            finish_reason=_string_or_none(first_choice.get("finish_reason")),
            prompt_tokens=_int_or_none(usage.get("prompt_tokens")),
            completion_tokens=_int_or_none(usage.get("completion_tokens")),
            total_tokens=_int_or_none(usage.get("total_tokens")),
            cost_usd=_float_or_none(
                body["cost_usd"] if "cost_usd" in body else provider_response.get("cost_usd")
            ),
            latency_ms=_int_or_none(provider_response.get("latency_ms")),
            sanitized_diagnostics={
                "response_shape": "chat_completion",
                "content_present": True,
            },
        ),
        content=content,
        no_live_external_calls=True,
    )


def _result_from_status(
    *,
    request: LlmTransportRequestMetadata,
    status: LlmTransportStatus,
    retryability: LlmTransportRetryability,
    diagnostic_code: str,
    provider_status: str | None,
    finish_reason: str | None = None,
    latency_ms: int | None = None,
) -> LlmTransportResult:
    active_model = request.active_model
    return LlmTransportResult(
        request=request,
        response=LlmTransportResponseMetadata(
            provider_kind=LlmProviderKind.openrouter,
            status=status,
            retryability=retryability,
            diagnostic_code=diagnostic_code,
            request_mode=request.request_mode,
            model_name=active_model.model_name if active_model else None,
            model_tier=active_model.tier if active_model else LlmModelTier.unavailable,
            provider_status=provider_status,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            sanitized_diagnostics={
                "diagnostic_code": diagnostic_code,
                "content_present": False,
            },
        ),
        content=None,
        no_live_external_calls=True,
    )


def _transport_mode(value: LlmTransportMode | str) -> LlmTransportMode:
    if isinstance(value, LlmTransportMode):
        return value
    if str(value).strip().lower() == LlmTransportMode.json_mode.value:
        return LlmTransportMode.json_mode
    return LlmTransportMode.schema_mode


def _sanitize_diagnostics(values: Mapping[str, Any] | None) -> dict[str, str | int | bool | float | None]:
    sanitized: dict[str, str | int | bool | float | None] = {}
    for key, value in (values or {}).items():
        normalized_key = str(key).strip().lower()
        if not normalized_key or any(marker in normalized_key for marker in _FORBIDDEN_DIAGNOSTIC_KEY_MARKERS):
            continue
        if isinstance(value, bool) or value is None:
            sanitized[normalized_key] = value
        elif isinstance(value, int | float):
            sanitized[normalized_key] = value
        else:
            string_value = " ".join(str(value).split())
            lowered = string_value.lower()
            if "http://" in lowered or "https://" in lowered:
                continue
            if any(marker.lower() in lowered for marker in _FORBIDDEN_DIAGNOSTIC_VALUE_MARKERS):
                continue
            sanitized[normalized_key] = string_value[:120]
    return sanitized


def _provider_status(status_code: int | None) -> str:
    if status_code is None:
        return "unknown"
    if 200 <= status_code < 300:
        return "ok"
    return f"http_{status_code}"


def _message_content(message: Any) -> str | None:
    if not isinstance(message, Mapping):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    return stripped or None


def _active_model_name(request: LlmTransportRequestMetadata) -> str | None:
    return request.active_model.model_name if request.active_model else None


def _model_tier(model_name: str | None, request: LlmTransportRequestMetadata) -> LlmModelTier:
    if model_name is None:
        return LlmModelTier.unavailable
    for model in [*request.configured_model_chain, request.paid_fallback_model]:
        if isinstance(model, LlmModelDescriptor) and model.model_name == model_name:
            return model.tier
    return request.active_model.tier if request.active_model else LlmModelTier.unavailable


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
