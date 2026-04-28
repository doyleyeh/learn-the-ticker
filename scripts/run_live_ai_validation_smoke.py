#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.cache import build_knowledge_pack_freshness_input, compute_knowledge_pack_freshness_hash
from backend.chat import generate_asset_chat, validate_chat_response
from backend.citations import CitationEvidence, CitationValidationClaim, CitationValidationContext, evidence_from_sources
from backend.llm import build_llm_runtime_config, decide_cache_eligibility, validate_llm_generated_output
from backend.llm_transport import TransportCallable, call_openrouter_transport
from backend.models import (
    CacheEntryKind,
    CacheScope,
    FreshnessState,
    LlmGenerationAttemptMetadata,
    LlmGenerationAttemptStatus,
    LlmGenerationRequestMetadata,
    LlmModelTier,
    LlmProviderKind,
    LlmReadinessStatus,
    LlmTransportMode,
    LlmTransportRequestMetadata,
    LlmTransportStatus,
    LlmValidationStatus,
    SafetyClassification,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsEventType,
)
from backend.retrieval import build_asset_knowledge_pack
from backend.weekly_news import (
    WeeklyNewsCandidate,
    build_ai_comprehensive_analysis,
    select_weekly_news_focus,
    validate_ai_comprehensive_analysis,
)


SCHEMA_VERSION = "local-live-ai-validation-smoke-v1"
CHAT_CASE_ID = "grounded_chat_supported_golden_asset"
ANALYSIS_CASE_ID = "ai_comprehensive_analysis_threshold_case"
CHAT_TICKER = "VOO"
ANALYSIS_TICKER = "QQQ"
SMOKE_OPT_IN_ENV = "LTT_LIVE_AI_SMOKE_ENABLED"
LIVE_GENERATION_ENV = "LLM_LIVE_GENERATION_ENABLED"
PROVIDER_KEY_ENV = "OPENROUTER_API_KEY"
TransportFactory = Callable[[str, Mapping[str, Any]], TransportCallable]


@dataclass(frozen=True)
class SmokeCaseResult:
    case_id: str
    status: str
    reason_code: str
    validation_status: str = "not_validated"
    cacheable: bool = False
    selected_item_count: int | None = None
    model_tier: str | None = None
    live_call_attempted: bool = False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "case_id": self.case_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "validation_status": self.validation_status,
            "cacheable": self.cacheable,
            "live_call_attempted": self.live_call_attempted,
        }
        if self.selected_item_count is not None:
            payload["selected_item_count"] = self.selected_item_count
        if self.model_tier is not None:
            payload["model_tier"] = self.model_tier
        return payload


def run_live_ai_validation_smoke(
    env: Mapping[str, str] | None = None,
    *,
    transport_factory: TransportFactory | None = None,
) -> dict[str, object]:
    source = dict(os.environ if env is None else env)
    smoke_enabled = _bool_env(source.get(SMOKE_OPT_IN_ENV))
    settings = _runtime_settings_from_env(source)
    runtime = build_llm_runtime_config(settings, server_side_key_present=bool(_clean(source.get(PROVIDER_KEY_ENV))))

    if not smoke_enabled:
        cases = [
            _skipped(CHAT_CASE_ID, "explicit_live_ai_smoke_opt_in_missing"),
            _skipped(ANALYSIS_CASE_ID, "explicit_live_ai_smoke_opt_in_missing"),
        ]
    elif runtime.readiness_status is not LlmReadinessStatus.ready_for_explicit_live_call:
        reason = _runtime_block_reason(runtime)
        cases = [_blocked(CHAT_CASE_ID, reason), _blocked(ANALYSIS_CASE_ID, reason)]
    else:
        factory = transport_factory or _openrouter_transport_factory(source)
        cases = [
            _run_grounded_chat_case(runtime=runtime, transport_factory=factory),
            _run_analysis_case(runtime=runtime, transport_factory=factory),
        ]

    status = _rollup_status(cases)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "provider_kind": runtime.provider_kind.value,
        "readiness_status": runtime.readiness_status.value,
        "live_generation_enabled": runtime.live_generation_enabled,
        "server_side_key_present": runtime.server_side_key_present,
        "cases": [case.to_dict() for case in cases],
        "sanitized_diagnostics": {
            "normal_ci_requires_live_calls": False,
            "stores_raw_user_text": False,
            "stores_prompt_text": False,
            "stores_source_text": False,
            "stores_model_reasoning": False,
            "stores_raw_transcript": False,
            "stores_generated_live_response": False,
            "writes_generated_output_cache": False,
        },
    }


def _run_grounded_chat_case(
    *,
    runtime,
    transport_factory: TransportFactory,
) -> SmokeCaseResult:
    pack = build_asset_knowledge_pack(CHAT_TICKER)
    response = generate_asset_chat(CHAT_TICKER, "What does this fund hold?")
    if response.safety_classification is not SafetyClassification.educational:
        return _blocked(CHAT_CASE_ID, "safety_redirect_precedes_live_call")
    if not response.citations or not response.source_documents:
        return _blocked(CHAT_CASE_ID, "grounded_chat_evidence_unavailable")
    if not validate_chat_response(response, pack).valid:
        return _blocked(CHAT_CASE_ID, "grounded_chat_fixture_validation_failed")

    evidence = evidence_from_sources(CHAT_TICKER, response.citations, response.source_documents)
    citation_ids = sorted({citation.citation_id for citation in response.citations})
    request = _request(
        task_name="local_live_ai_grounded_chat_smoke",
        output_kind="chat_answer",
        schema_version="local-live-ai-chat-smoke-v1",
        prompt_version="local-live-ai-chat-smoke-v1",
        asset_ticker=CHAT_TICKER,
        knowledge_hash=compute_knowledge_pack_freshness_hash(build_knowledge_pack_freshness_input(pack)),
    )
    prompt_payload = {
        "case": CHAT_CASE_ID,
        "asset_ticker": CHAT_TICKER,
        "required_json_keys": ["direct_answer", "why_it_matters", "citation_ids", "freshness_state"],
        "allowed_citation_ids": citation_ids,
        "source_policy": "Use only same-asset, approved citation IDs. Keep the answer educational.",
    }
    transport_result = call_openrouter_transport(
        runtime=runtime,
        request_mode=LlmTransportMode.json_mode,
        caller_opted_in=True,
        transport=transport_factory(CHAT_CASE_ID, prompt_payload),
        sanitized_diagnostics={"case_id": CHAT_CASE_ID},
    )
    if transport_result.response.status is not LlmTransportStatus.succeeded or not transport_result.content:
        return _blocked(
            CHAT_CASE_ID,
            transport_result.response.diagnostic_code,
            model_tier=_tier(transport_result.response.model_tier),
            live_call_attempted=True,
        )

    parsed = _parse_json_object(transport_result.content)
    output_text = _joined_text(parsed, ["direct_answer", "why_it_matters"])
    emitted_citations = _string_list(parsed.get("citation_ids"))
    schema_valid = bool(
        parsed
        and output_text
        and emitted_citations
        and set(emitted_citations) <= set(citation_ids)
        and parsed.get("freshness_state") in {state.value for state in FreshnessState}
    )
    validation = validate_llm_generated_output(
        output_text=output_text,
        schema_valid=schema_valid,
        claims=[
            CitationValidationClaim(
                claim_id="live_smoke_grounded_chat_claim",
                claim_text="Live grounded-chat smoke answer is bound to the selected asset knowledge pack.",
                citation_ids=emitted_citations,
                claim_type="factual",
                freshness_label=FreshnessState(str(parsed.get("freshness_state", FreshnessState.fresh.value)))
                if parsed.get("freshness_state") in {state.value for state in FreshnessState}
                else None,
            )
        ],
        evidence=evidence,
        citation_context=CitationValidationContext(allowed_asset_tickers=[CHAT_TICKER]),
    )
    attempt = _attempt(transport_result, validation.status)
    cache = decide_cache_eligibility(request=request, validation=validation, attempt=attempt)
    return _validated_case_result(
        CHAT_CASE_ID,
        validation_status=validation.status,
        cacheable=cache.cacheable,
        model_tier=_tier(attempt.model_tier),
        live_call_attempted=True,
    )


def _run_analysis_case(
    *,
    runtime,
    transport_factory: TransportFactory,
) -> SmokeCaseResult:
    pack = build_asset_knowledge_pack(ANALYSIS_TICKER)
    focus = select_weekly_news_focus(
        pack.asset,
        [
            _analysis_candidate("official_filing", WeeklyNewsEventType.regulatory_event, "sec_8k", SourceQuality.official),
            _analysis_candidate("issuer_update", WeeklyNewsEventType.sponsor_update, "issuer_press_release", SourceQuality.issuer),
        ],
        as_of="2026-04-23",
    )
    if focus.selected_item_count < 2:
        return _skipped(ANALYSIS_CASE_ID, "insufficient_approved_weekly_news_evidence", selected_item_count=focus.selected_item_count)

    canonical_fact_citation_ids = ["c_fact_qqq_asset_identity"]
    analysis = build_ai_comprehensive_analysis(
        pack.asset,
        focus,
        canonical_fact_citation_ids=canonical_fact_citation_ids,
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
    )
    validate_ai_comprehensive_analysis(analysis, focus)
    allowed_weekly_citations = sorted({citation_id for item in focus.items for citation_id in item.citation_ids})
    allowed_citations = sorted({*allowed_weekly_citations, *canonical_fact_citation_ids})
    evidence = [
        CitationEvidence(
            citation_id=citation_id,
            asset_ticker=ANALYSIS_TICKER,
            source_document_id=item.source.source_document_id,
            source_type=item.source.source_type,
            freshness_state=item.freshness_state,
            supporting_text=item.summary,
            is_recent=True,
            allowlist_status=item.source.allowlist_status,
            source_use_policy=item.source.source_use_policy,
            is_official=item.source.is_official,
            source_quality=item.source.source_quality,
        )
        for item in focus.items
        for citation_id in item.citation_ids
    ]
    evidence.append(
        CitationEvidence(
            citation_id=canonical_fact_citation_ids[0],
            asset_ticker=ANALYSIS_TICKER,
            source_document_id="src_qqq_fact_sheet_fixture",
            source_type="issuer_fact_sheet",
            freshness_state=FreshnessState.fresh,
            supporting_text="Approved canonical fact fixture for QQQ identity.",
            is_official=True,
            source_quality=SourceQuality.issuer,
            source_use_policy=SourceUsePolicy.full_text_allowed,
        )
    )

    request = _request(
        task_name="local_live_ai_comprehensive_analysis_smoke",
        output_kind="weekly_news_analysis",
        schema_version="local-live-ai-analysis-smoke-v1",
        prompt_version="local-live-ai-analysis-smoke-v1",
        asset_ticker=ANALYSIS_TICKER,
        knowledge_hash=compute_knowledge_pack_freshness_hash(build_knowledge_pack_freshness_input(pack)),
    )
    prompt_payload = {
        "case": ANALYSIS_CASE_ID,
        "asset_ticker": ANALYSIS_TICKER,
        "required_section_order": [
            "what_changed_this_week",
            "market_context",
            "business_or_fund_context",
            "risk_context",
        ],
        "weekly_news_selected_item_count": focus.selected_item_count,
        "allowed_weekly_citation_ids": allowed_weekly_citations,
        "canonical_fact_citation_ids": canonical_fact_citation_ids,
        "source_policy": "Return compact JSON only. Keep stable facts separate from Weekly News Focus.",
    }
    transport_result = call_openrouter_transport(
        runtime=runtime,
        request_mode=LlmTransportMode.json_mode,
        caller_opted_in=True,
        transport=transport_factory(ANALYSIS_CASE_ID, prompt_payload),
        sanitized_diagnostics={"case_id": ANALYSIS_CASE_ID},
    )
    if transport_result.response.status is not LlmTransportStatus.succeeded or not transport_result.content:
        return _blocked(
            ANALYSIS_CASE_ID,
            transport_result.response.diagnostic_code,
            selected_item_count=focus.selected_item_count,
            model_tier=_tier(transport_result.response.model_tier),
            live_call_attempted=True,
        )

    parsed = _parse_json_object(transport_result.content)
    sections = parsed.get("sections") if isinstance(parsed.get("sections"), list) else []
    section_ids = [str(section.get("section_id")) for section in sections if isinstance(section, Mapping)]
    section_citations = sorted(
        {
            citation_id
            for section in sections
            if isinstance(section, Mapping)
            for citation_id in _string_list(section.get("citation_ids"))
        }
    )
    emitted_canonical = _string_list(parsed.get("canonical_fact_citation_ids"))
    schema_valid = (
        section_ids
        == ["what_changed_this_week", "market_context", "business_or_fund_context", "risk_context"]
        and bool(section_citations)
        and set(section_citations) <= set(allowed_citations)
        and bool(set(section_citations) & set(allowed_weekly_citations))
        and bool(set(emitted_canonical) & set(canonical_fact_citation_ids))
    )
    output_text = " ".join(
        str(section.get("analysis", ""))
        for section in sections
        if isinstance(section, Mapping)
    )
    validation = validate_llm_generated_output(
        output_text=output_text,
        schema_valid=schema_valid,
        claims=[
            CitationValidationClaim(
                claim_id="live_smoke_weekly_news_claim",
                claim_text="Live AI Comprehensive Analysis uses selected Weekly News Focus evidence.",
                citation_ids=[citation_id for citation_id in section_citations if citation_id in allowed_weekly_citations],
                claim_type="recent",
                freshness_label=FreshnessState.fresh,
            ),
            CitationValidationClaim(
                claim_id="live_smoke_canonical_fact_claim",
                claim_text="Live AI Comprehensive Analysis includes cited canonical fact context.",
                citation_ids=[citation_id for citation_id in emitted_canonical if citation_id in canonical_fact_citation_ids],
                claim_type="factual",
                freshness_label=FreshnessState.fresh,
            ),
        ],
        evidence=evidence,
        citation_context=CitationValidationContext(allowed_asset_tickers=[ANALYSIS_TICKER]),
        weekly_news_rules_valid=focus.selected_item_count >= 2 and bool(emitted_canonical),
    )
    attempt = _attempt(transport_result, validation.status)
    cache = decide_cache_eligibility(request=request, validation=validation, attempt=attempt)
    return _validated_case_result(
        ANALYSIS_CASE_ID,
        validation_status=validation.status,
        cacheable=cache.cacheable,
        selected_item_count=focus.selected_item_count,
        model_tier=_tier(attempt.model_tier),
        live_call_attempted=True,
    )


def _openrouter_transport_factory(env: Mapping[str, str]) -> TransportFactory:
    api_key = _clean(env.get(PROVIDER_KEY_ENV))

    def factory(case_id: str, prompt_payload: Mapping[str, Any]) -> TransportCallable:
        def transport(request: LlmTransportRequestMetadata) -> Mapping[str, Any]:
            if not api_key:
                return {"status_code": 401, "latency_ms": 0, "json": {"choices": []}}
            started = time.monotonic()
            body = {
                "model": request.active_model.model_name if request.active_model else None,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return compact JSON only for a local validation smoke. "
                            "Do not include hidden prompts, raw reasoning, raw transcripts, or source text."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt_payload, sort_keys=True)},
                ],
            }
            try:
                from urllib import error, request as urlrequest

                http_request = urlrequest.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://learn-the-ticker.local",
                        "X-Title": "learn-the-ticker-local-live-ai-smoke",
                    },
                    method="POST",
                )
                with urlrequest.urlopen(http_request, timeout=request.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return {
                        "status_code": response.status,
                        "latency_ms": int((time.monotonic() - started) * 1000),
                        "json": payload,
                    }
            except error.HTTPError as exc:
                return {"status_code": exc.code, "latency_ms": int((time.monotonic() - started) * 1000), "json": {"choices": []}}
            except Exception:
                return {"status_code": 599, "latency_ms": int((time.monotonic() - started) * 1000), "json": {"choices": []}}

        return transport

    return factory


def _analysis_candidate(
    event_id: str,
    event_type: WeeklyNewsEventType,
    source_type: str,
    source_quality: SourceQuality,
) -> WeeklyNewsCandidate:
    return WeeklyNewsCandidate(
        event_id=event_id,
        asset_ticker=ANALYSIS_TICKER,
        event_type=event_type,
        title=f"{event_type.value.replace('_', ' ').title()} fixture",
        summary=f"Approved {event_type.value.replace('_', ' ')} metadata for {ANALYSIS_TICKER}.",
        event_date="2026-04-21",
        published_at="2026-04-21T12:00:00Z",
        retrieved_at="2026-04-21T13:00:00Z",
        source_document_id=f"src_{ANALYSIS_TICKER.lower()}_{event_id}",
        source_chunk_id=f"chk_{ANALYSIS_TICKER.lower()}_{event_id}",
        source_type=source_type,
        source_rank=1 if source_quality is SourceQuality.official else 2,
        source_title=f"{ANALYSIS_TICKER} {event_type.value.replace('_', ' ').title()}",
        publisher="Approved official-source fixture",
        url=f"local://weekly-news-smoke/{ANALYSIS_TICKER}/{event_id}",
        source_quality=source_quality,
        allowlist_status=SourceAllowlistStatus.allowed,
        source_use_policy=SourceUsePolicy.summary_allowed,
        freshness_state=FreshnessState.fresh,
        is_official=True,
        supporting_text="Approved local smoke evidence metadata.",
    )


def _request(
    *,
    task_name: str,
    output_kind: str,
    schema_version: str,
    prompt_version: str,
    asset_ticker: str,
    knowledge_hash: str,
) -> LlmGenerationRequestMetadata:
    return LlmGenerationRequestMetadata(
        task_name=task_name,
        output_kind=output_kind,
        prompt_version=prompt_version,
        schema_version=schema_version,
        safety_policy_version="safety-v1",
        asset_ticker=asset_ticker,
        knowledge_pack_hash=knowledge_hash,
        source_freshness_hash=knowledge_hash,
    )


def _attempt(transport_result, validation_status: LlmValidationStatus) -> LlmGenerationAttemptMetadata:
    response = transport_result.response
    model_name = response.model_name or "unavailable"
    model_tier = response.model_tier or LlmModelTier.unavailable
    return LlmGenerationAttemptMetadata(
        attempt_index=1,
        provider_kind=response.provider_kind,
        model_name=model_name,
        model_tier=model_tier,
        status=(
            LlmGenerationAttemptStatus.validation_succeeded
            if validation_status is LlmValidationStatus.valid
            else LlmGenerationAttemptStatus.validation_failed
        ),
        validation_status=validation_status,
        latency_ms=response.latency_ms,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        cost_usd=response.cost_usd,
    )


def _validated_case_result(
    case_id: str,
    *,
    validation_status: LlmValidationStatus,
    cacheable: bool,
    selected_item_count: int | None = None,
    model_tier: str | None,
    live_call_attempted: bool,
) -> SmokeCaseResult:
    if validation_status is LlmValidationStatus.valid and cacheable:
        return SmokeCaseResult(
            case_id=case_id,
            status="pass",
            reason_code="validated_and_cache_eligible",
            validation_status=validation_status.value,
            cacheable=True,
            selected_item_count=selected_item_count,
            model_tier=model_tier,
            live_call_attempted=live_call_attempted,
        )
    reason = (
        "cache_ineligible_output"
        if validation_status is LlmValidationStatus.valid and not cacheable
        else f"validation_{validation_status.value}"
    )
    return SmokeCaseResult(
        case_id=case_id,
        status="blocked",
        reason_code=reason,
        validation_status=validation_status.value,
        cacheable=cacheable,
        selected_item_count=selected_item_count,
        model_tier=model_tier,
        live_call_attempted=live_call_attempted,
    )


def _runtime_settings_from_env(env: Mapping[str, str]) -> dict[str, str]:
    settings = {
        "LLM_PROVIDER": env.get("LLM_PROVIDER", "mock"),
        "LLM_LIVE_GENERATION_ENABLED": env.get("LLM_LIVE_GENERATION_ENABLED", "false"),
        "OPENROUTER_BASE_URL": env.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "OPENROUTER_FREE_MODEL_ORDER": env.get(
            "OPENROUTER_FREE_MODEL_ORDER",
            "openai/gpt-oss-120b:free,google/gemma-4-31b-it:free,qwen/qwen3-next-80b-a3b-instruct:free,meta-llama/llama-3.3-70b-instruct:free",
        ),
        "OPENROUTER_PAID_FALLBACK_MODEL": env.get("OPENROUTER_PAID_FALLBACK_MODEL", "deepseek/deepseek-v3.2"),
        "OPENROUTER_PAID_FALLBACK_ENABLED": env.get("OPENROUTER_PAID_FALLBACK_ENABLED", "true"),
        "LLM_VALIDATION_RETRY_COUNT": env.get("LLM_VALIDATION_RETRY_COUNT", "1"),
        "LLM_REASONING_SUMMARY_ONLY": env.get("LLM_REASONING_SUMMARY_ONLY", "true"),
    }
    return {key: value for key, value in settings.items() if value is not None}


def _runtime_block_reason(runtime) -> str:
    if runtime.provider_kind is not LlmProviderKind.openrouter:
        return "provider_not_openrouter"
    if not runtime.live_generation_enabled:
        return "live_generation_flag_disabled"
    if not runtime.server_side_key_present:
        return "server_side_key_missing"
    if not runtime.validation_ready:
        return "validation_not_ready"
    return (runtime.unavailable_reasons or ["llm_runtime_not_ready"])[0]


def _parse_json_object(content: str | None) -> dict[str, Any]:
    if not content:
        return {}
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _joined_text(payload: Mapping[str, Any], keys: list[str]) -> str:
    return " ".join(str(payload.get(key, "")).strip() for key in keys if str(payload.get(key, "")).strip())


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _skipped(case_id: str, reason_code: str, *, selected_item_count: int | None = None) -> SmokeCaseResult:
    return SmokeCaseResult(case_id=case_id, status="skipped", reason_code=reason_code, selected_item_count=selected_item_count)


def _blocked(
    case_id: str,
    reason_code: str,
    *,
    selected_item_count: int | None = None,
    model_tier: str | None = None,
    live_call_attempted: bool = False,
) -> SmokeCaseResult:
    return SmokeCaseResult(
        case_id=case_id,
        status="blocked",
        reason_code=reason_code,
        selected_item_count=selected_item_count,
        model_tier=model_tier,
        live_call_attempted=live_call_attempted,
    )


def _rollup_status(cases: list[SmokeCaseResult]) -> str:
    statuses = {case.status for case in cases}
    if "blocked" in statuses:
        return "blocked"
    if statuses == {"pass"}:
        return "pass"
    return "skipped"


def _tier(value: Any) -> str | None:
    return value.value if isinstance(value, LlmModelTier) else None


def _bool_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _clean(value: str | None) -> str | None:
    stripped = str(value or "").strip()
    return stripped or None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an operator-only local live-AI validation smoke for grounded chat and AI Comprehensive Analysis."
    )
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON diagnostics.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    parser.parse_args(argv)
    result = run_live_ai_validation_smoke()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
