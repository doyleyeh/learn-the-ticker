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
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.search import search_assets
from backend.weekly_news_repository import (
    WeeklyNewsEventCandidateRow,
    WeeklyNewsEventEvidenceRepositoryRecords,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
)
from backend.weekly_news import (
    build_weekly_news_focus_from_pack,
    build_ai_comprehensive_analysis,
    validate_ai_comprehensive_analysis,
)


SCHEMA_VERSION = "local-live-ai-validation-smoke-v1"
CHAT_STOCK_CASE_ID = "grounded_chat_supported_stock_mvp_slice"
CHAT_ETF_CASE_ID = "grounded_chat_supported_etf_mvp_slice"
ANALYSIS_CASE_ID = "ai_comprehensive_analysis_threshold_case"
ANALYSIS_EMPTY_CASE_ID = "ai_comprehensive_analysis_zero_evidence_suppressed"
ANALYSIS_ONE_ITEM_CASE_ID = "ai_comprehensive_analysis_one_item_insufficient_evidence"
BLOCKED_REGRESSION_CASE_ID = "blocked_regression_tickers_generated_output_ineligible"
ANALYSIS_AS_OF = "2026-04-23"
ANALYSIS_CREATED_AT = "2026-04-23T12:00:00Z"
CHAT_CASES = (
    (CHAT_STOCK_CASE_ID, "AAPL", "What does this company do?"),
    (CHAT_ETF_CASE_ID, "VOO", "What does this fund hold?"),
)
ANALYSIS_TICKER = "QQQ"
BLOCKED_REGRESSION_TICKERS = ("TQQQ", "ARKK", "BND", "GLD", "BTC", "ZZZZ")
KNOWN_MVP_SLICE_TICKERS = (
    "AAPL",
    "MSFT",
    "NVDA",
    "VOO",
    "SPY",
    "VTI",
    "QQQ",
    "XLK",
    *BLOCKED_REGRESSION_TICKERS,
)
SMOKE_OPT_IN_ENV = "LTT_LIVE_AI_SMOKE_ENABLED"
LIVE_GENERATION_ENV = "LLM_LIVE_GENERATION_ENABLED"
LLM_PROVIDER_ENV = "LLM_PROVIDER"
PROVIDER_KEY_ENV = "OPENROUTER_API_KEY"
TransportFactory = Callable[[str, Mapping[str, Any]], TransportCallable]


@dataclass(frozen=True)
class SmokeCaseResult:
    case_id: str
    status: str
    reason_code: str
    case_kind: str = "validation"
    asset_ticker: str | None = None
    asset_type: str | None = None
    diagnostic_state: str | None = None
    validation_status: str = "not_validated"
    cacheable: bool = False
    selected_item_count: int | None = None
    expected_minimum_item_count: int | None = None
    threshold_status: str | None = None
    model_tier: str | None = None
    attempt_status: str | None = None
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    live_call_attempted: bool = False
    validation_contract: dict[str, bool] | None = None
    blocked_regression_tickers: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "case_id": self.case_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "case_kind": self.case_kind,
            "validation_status": self.validation_status,
            "cacheable": self.cacheable,
            "live_call_attempted": self.live_call_attempted,
        }
        if self.asset_ticker is not None:
            payload["asset_ticker"] = self.asset_ticker
        if self.asset_type is not None:
            payload["asset_type"] = self.asset_type
        if self.diagnostic_state is not None:
            payload["diagnostic_state"] = self.diagnostic_state
        if self.selected_item_count is not None:
            payload["selected_item_count"] = self.selected_item_count
        if self.expected_minimum_item_count is not None:
            payload["expected_minimum_item_count"] = self.expected_minimum_item_count
        if self.threshold_status is not None:
            payload["threshold_status"] = self.threshold_status
        if self.model_tier is not None:
            payload["model_tier"] = self.model_tier
        if self.attempt_status is not None:
            payload["attempt_status"] = self.attempt_status
        if self.latency_ms is not None:
            payload["latency_ms"] = self.latency_ms
        if self.prompt_tokens is not None:
            payload["prompt_tokens"] = self.prompt_tokens
        if self.completion_tokens is not None:
            payload["completion_tokens"] = self.completion_tokens
        if self.total_tokens is not None:
            payload["total_tokens"] = self.total_tokens
        if self.cost_usd is not None:
            payload["cost_usd"] = self.cost_usd
        if self.validation_contract is not None:
            payload["validation_contract"] = self.validation_contract
        if self.blocked_regression_tickers is not None:
            payload["blocked_regression_tickers"] = self.blocked_regression_tickers
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
    readiness_prerequisites = _readiness_prerequisites(source, runtime, smoke_enabled=smoke_enabled)

    if not smoke_enabled:
        cases = [_skipped(case_id, "explicit_live_ai_smoke_opt_in_missing") for case_id in _all_case_ids()]
    elif runtime.readiness_status is not LlmReadinessStatus.ready_for_explicit_live_call:
        reason = _runtime_block_reason(runtime)
        cases = [
            *[
                _blocked(case_id, reason, asset_ticker=ticker, case_kind="grounded_chat")
                for case_id, ticker, _question in CHAT_CASES
            ],
            _blocked(ANALYSIS_CASE_ID, reason, asset_ticker=ANALYSIS_TICKER, case_kind="ai_comprehensive_analysis"),
            _run_analysis_suppression_case(ANALYSIS_EMPTY_CASE_ID, candidate_count=0),
            _run_analysis_suppression_case(ANALYSIS_ONE_ITEM_CASE_ID, candidate_count=1),
            _run_blocked_regression_case(),
        ]
    else:
        factory = transport_factory or _openrouter_transport_factory(source)
        cases = [
            *[
                _run_grounded_chat_case(
                    case_id=case_id,
                    ticker=ticker,
                    question=question,
                    runtime=runtime,
                    transport_factory=factory,
                )
                for case_id, ticker, question in CHAT_CASES
            ],
            _run_analysis_case(runtime=runtime, transport_factory=factory),
            _run_analysis_suppression_case(ANALYSIS_EMPTY_CASE_ID, candidate_count=0),
            _run_analysis_suppression_case(ANALYSIS_ONE_ITEM_CASE_ID, candidate_count=1),
            _run_blocked_regression_case(),
        ]

    status = _rollup_status(cases)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "normal_ci_requires_live_calls": False,
        "provider_kind": runtime.provider_kind.value,
        "readiness_status": runtime.readiness_status.value,
        "live_generation_enabled": runtime.live_generation_enabled,
        "server_side_key_present": runtime.server_side_key_present,
        "readiness_prerequisites": readiness_prerequisites,
        "live_llm_calls_attempted": any(case.live_call_attempted for case in cases),
        "live_network_calls_attempted": bool(
            transport_factory is None
            and smoke_enabled
            and runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call
            and any(case.live_call_attempted for case in cases)
        ),
        "generated_output_cache_entries_written": False,
        "sources_approved_by_smoke": False,
        "manifests_promoted": False,
        "validation_contract": {
            "grounded_chat_stock_case": CHAT_STOCK_CASE_ID,
            "grounded_chat_etf_case": CHAT_ETF_CASE_ID,
            "analysis_threshold_case": ANALYSIS_CASE_ID,
            "analysis_zero_evidence_case": ANALYSIS_EMPTY_CASE_ID,
            "analysis_one_item_case": ANALYSIS_ONE_ITEM_CASE_ID,
            "blocked_regression_tickers_case": BLOCKED_REGRESSION_CASE_ID,
            "blocked_regression_tickers": list(BLOCKED_REGRESSION_TICKERS),
        },
        "cases": [case.to_dict() for case in cases],
        "sanitized_diagnostics": {
            "normal_ci_requires_live_calls": False,
            "safe_reason_codes_only": True,
            "env_var_names_reported_without_values": True,
            "local_mvp_slice_chat_tickers": [ticker for _case_id, ticker, _question in CHAT_CASES],
            "ai_comprehensive_analysis_minimum_selected_items": 2,
            "blocked_regression_tickers": list(BLOCKED_REGRESSION_TICKERS),
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
    case_id: str,
    ticker: str,
    question: str,
    runtime,
    transport_factory: TransportFactory,
) -> SmokeCaseResult:
    pack = build_asset_knowledge_pack(ticker)
    response = generate_asset_chat(ticker, question)
    if response.safety_classification is not SafetyClassification.educational:
        return _blocked(case_id, "safety_redirect_precedes_live_call", asset_ticker=ticker, case_kind="grounded_chat")
    if not response.citations or not response.source_documents:
        return _blocked(case_id, "grounded_chat_evidence_unavailable", asset_ticker=ticker, case_kind="grounded_chat")
    if not validate_chat_response(response, pack).valid:
        return _blocked(case_id, "grounded_chat_fixture_validation_failed", asset_ticker=ticker, case_kind="grounded_chat")

    evidence = evidence_from_sources(ticker, response.citations, response.source_documents)
    citation_ids = sorted({citation.citation_id for citation in response.citations})
    request = _request(
        task_name="local_live_ai_grounded_chat_smoke",
        output_kind="chat_answer",
        schema_version="local-live-ai-chat-smoke-v1",
        prompt_version="local-live-ai-chat-smoke-v1",
        asset_ticker=ticker,
        knowledge_hash=compute_knowledge_pack_freshness_hash(build_knowledge_pack_freshness_input(pack)),
    )
    prompt_payload = {
        "case": case_id,
        "asset_ticker": ticker,
        "asset_type": pack.asset.asset_type.value,
        "required_json_keys": ["asset_ticker", "direct_answer", "why_it_matters", "citation_ids", "freshness_state"],
        "allowed_citation_ids": citation_ids,
        "source_policy": (
            "Use only same-asset, approved citation IDs. Keep the answer educational. "
            "Do not answer as a comparison or include a second ticker."
        ),
    }
    transport_result = call_openrouter_transport(
        runtime=runtime,
        request_mode=LlmTransportMode.json_mode,
        caller_opted_in=True,
        transport=transport_factory(case_id, prompt_payload),
        sanitized_diagnostics={"case_id": case_id, "asset_ticker": ticker, "case_kind": "grounded_chat"},
    )
    if transport_result.response.status is not LlmTransportStatus.succeeded or not transport_result.content:
        return _blocked(
            case_id,
            transport_result.response.diagnostic_code,
            asset_ticker=ticker,
            asset_type=pack.asset.asset_type.value,
            case_kind="grounded_chat",
            model_tier=_tier(transport_result.response.model_tier),
            live_call_attempted=True,
        )

    parsed = _parse_json_object(transport_result.content)
    output_text = _joined_text(parsed, ["direct_answer", "why_it_matters"])
    emitted_citations = _string_list(parsed.get("citation_ids"))
    same_asset_scope_valid = _single_asset_scope_valid(output_text, ticker)
    schema_valid = bool(
        parsed
        and parsed.get("asset_ticker") == ticker
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
        citation_context=CitationValidationContext(allowed_asset_tickers=[ticker]),
        unsupported_claim_codes=[] if same_asset_scope_valid else ["multi_asset_single_chat_answer"],
    )
    attempt = _attempt(transport_result, validation.status)
    cache = decide_cache_eligibility(request=request, validation=validation, attempt=attempt)
    return _validated_case_result(
        case_id,
        case_kind="grounded_chat",
        asset_ticker=ticker,
        asset_type=pack.asset.asset_type.value,
        validation_status=validation.status,
        cacheable=cache.cacheable,
        attempt=attempt,
        model_tier=_tier(attempt.model_tier),
        live_call_attempted=True,
        validation_contract={
            "selected_asset_grounding": response.asset.ticker == ticker and parsed.get("asset_ticker") == ticker,
            "same_asset_citation_ids": set(emitted_citations) <= set(citation_ids),
            "source_documents_present": bool(response.source_documents),
            "freshness_label_present": parsed.get("freshness_state") in {state.value for state in FreshnessState},
            "educational_framing": validation.safety_valid,
            "single_asset_chat_scope": same_asset_scope_valid,
            "generated_output_cache_write": False,
        },
    )


def _run_analysis_case(
    *,
    runtime,
    transport_factory: TransportFactory,
) -> SmokeCaseResult:
    pack = build_asset_knowledge_pack(ANALYSIS_TICKER)
    records = _analysis_weekly_news_records(candidate_count=2)
    threshold = records.ai_thresholds[0]
    focus = build_weekly_news_focus_from_pack(
        pack,
        as_of=ANALYSIS_AS_OF,
        persisted_event_reader=_WeeklyNewsSmokeReader(records),
    )
    if focus.selected_item_count < threshold.minimum_weekly_news_item_count:
        return _skipped(
            ANALYSIS_CASE_ID,
            "insufficient_approved_weekly_news_evidence",
            selected_item_count=focus.selected_item_count,
        )

    canonical_fact_citation_ids = ["c_fact_qqq_asset_identity"]
    analysis = build_ai_comprehensive_analysis(
        pack.asset,
        focus,
        canonical_fact_citation_ids=canonical_fact_citation_ids,
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
        approved_weekly_news_item_count=threshold.high_signal_selected_item_count,
        high_signal_weekly_news_item_count=threshold.high_signal_selected_item_count,
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
        "required_flags": {"stable_facts_separate": True},
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
        and parsed.get("stable_facts_separate") is True
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
        case_kind="ai_comprehensive_analysis",
        asset_ticker=ANALYSIS_TICKER,
        asset_type=pack.asset.asset_type.value,
        validation_status=validation.status,
        cacheable=cache.cacheable,
        selected_item_count=focus.selected_item_count,
        expected_minimum_item_count=analysis.minimum_weekly_news_item_count,
        threshold_status=threshold.analysis_state,
        attempt=attempt,
        model_tier=_tier(attempt.model_tier),
        live_call_attempted=True,
        validation_contract={
            "weekly_news_threshold_met": focus.selected_item_count >= analysis.minimum_weekly_news_item_count,
            "weekly_news_repository_records_validated": True,
            "required_section_order": section_ids
            == ["what_changed_this_week", "market_context", "business_or_fund_context", "risk_context"],
            "weekly_news_citations_present": bool(set(section_citations) & set(allowed_weekly_citations)),
            "canonical_fact_citations_present": bool(set(emitted_canonical) & set(canonical_fact_citation_ids)),
            "stable_facts_separate": parsed.get("stable_facts_separate") is True,
            "generated_output_cache_write": False,
        },
    )


def _run_analysis_suppression_case(case_id: str, *, candidate_count: int) -> SmokeCaseResult:
    pack = build_asset_knowledge_pack(ANALYSIS_TICKER)
    records = _analysis_weekly_news_records(candidate_count=candidate_count)
    threshold = records.ai_thresholds[0]
    focus = build_weekly_news_focus_from_pack(
        pack,
        as_of=ANALYSIS_AS_OF,
        persisted_event_reader=_WeeklyNewsSmokeReader(records),
    )
    analysis = build_ai_comprehensive_analysis(
        pack.asset,
        focus,
        canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
        approved_weekly_news_item_count=threshold.high_signal_selected_item_count,
        high_signal_weekly_news_item_count=threshold.high_signal_selected_item_count,
    )
    validate_ai_comprehensive_analysis(analysis, focus)
    expected_state = "empty" if candidate_count == 0 else "insufficient_evidence"
    valid_suppression = (
        focus.selected_item_count == candidate_count
        and analysis.analysis_available is False
        and analysis.sections == []
        and analysis.weekly_news_selected_item_count == candidate_count
        and analysis.minimum_weekly_news_item_count == 2
    )
    if not valid_suppression:
        return _blocked(
            case_id,
            "analysis_threshold_suppression_contract_failed",
            asset_ticker=ANALYSIS_TICKER,
            asset_type=pack.asset.asset_type.value,
            case_kind="ai_comprehensive_analysis_threshold_suppression",
            selected_item_count=focus.selected_item_count,
        )
    return SmokeCaseResult(
        case_id=case_id,
        status="pass",
        reason_code=f"{expected_state}_suppressed_without_ai_output",
        case_kind="ai_comprehensive_analysis_threshold_suppression",
        asset_ticker=ANALYSIS_TICKER,
        asset_type=pack.asset.asset_type.value,
        diagnostic_state=expected_state,
        validation_status="not_validated",
        cacheable=False,
        selected_item_count=focus.selected_item_count,
        expected_minimum_item_count=analysis.minimum_weekly_news_item_count,
        threshold_status=threshold.analysis_state,
        live_call_attempted=False,
        validation_contract={
            "analysis_available": False,
            "sections_absent": True,
            "weekly_news_threshold_met": False,
            "weekly_news_repository_records_validated": True,
            "generated_output_usable": False,
            "generated_output_cache_write": False,
            "stable_facts_separate": analysis.stable_facts_are_separate,
        },
    )


def _run_blocked_regression_case() -> SmokeCaseResult:
    invalid: list[str] = []
    for ticker in BLOCKED_REGRESSION_TICKERS:
        search = search_assets(ticker)
        result = search.results[0] if search.results else None
        pack_result = build_asset_knowledge_pack_result(ticker)
        chat = generate_asset_chat(ticker, "What is this asset?")
        blocked = bool(
            result
            and result.supported is False
            and result.generated_route is None
            and result.can_open_generated_page is False
            and result.can_answer_chat is False
            and result.can_compare is False
            and pack_result.generated_output_available is False
            and chat.safety_classification is SafetyClassification.unsupported_asset_redirect
            and chat.citations == []
            and chat.source_documents == []
        )
        if not blocked:
            invalid.append(ticker)

    if invalid:
        return _blocked(
            BLOCKED_REGRESSION_CASE_ID,
            "blocked_regression_ticker_generated_output_boundary_failed",
            case_kind="blocked_regression_tickers",
            blocked_regression_tickers=invalid,
        )

    return SmokeCaseResult(
        case_id=BLOCKED_REGRESSION_CASE_ID,
        status="pass",
        reason_code="generated_output_ineligible_without_live_ai_call",
        case_kind="blocked_regression_tickers",
        diagnostic_state="blocked",
        validation_status="not_validated",
        cacheable=False,
        live_call_attempted=False,
        blocked_regression_tickers=list(BLOCKED_REGRESSION_TICKERS),
        validation_contract={
            "generated_pages": False,
            "generated_chat_answers": False,
            "generated_comparisons": False,
            "weekly_news_focus": False,
            "ai_comprehensive_analysis": False,
            "citations": False,
            "sources": False,
            "exports": False,
            "generated_risk_summaries": False,
            "generated_output_cache_write": False,
        },
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


@dataclass(frozen=True)
class _WeeklyNewsSmokeReader:
    records: WeeklyNewsEventEvidenceRepositoryRecords

    def read_weekly_news_event_evidence_records(self, ticker: str) -> WeeklyNewsEventEvidenceRepositoryRecords | None:
        return self.records if ticker.upper() == ANALYSIS_TICKER else None


def _analysis_weekly_news_records(*, candidate_count: int) -> WeeklyNewsEventEvidenceRepositoryRecords:
    candidates = [
        _analysis_evidence_row(
            "official_filing",
            WeeklyNewsEventType.regulatory_event,
            WeeklyNewsSourceRankTier.official_filing,
            SourceQuality.official,
        ),
        _analysis_evidence_row(
            "issuer_update",
            WeeklyNewsEventType.sponsor_update,
            WeeklyNewsSourceRankTier.etf_issuer_announcement,
            SourceQuality.issuer,
        ),
    ][:candidate_count]
    return acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker=ANALYSIS_TICKER,
        as_of=ANALYSIS_AS_OF,
        created_at=ANALYSIS_CREATED_AT,
        candidates=candidates,
    )


def _analysis_evidence_row(
    event_id: str,
    event_type: WeeklyNewsEventType,
    source_rank_tier: WeeklyNewsSourceRankTier,
    source_quality: SourceQuality,
) -> WeeklyNewsEventCandidateRow:
    citation_id = f"c_weekly_{ANALYSIS_TICKER.lower()}_{event_id}"
    source_type = (
        "sec_8k"
        if source_rank_tier is WeeklyNewsSourceRankTier.official_filing
        else "issuer_press_release"
    )
    return WeeklyNewsEventCandidateRow(
        candidate_event_id=event_id,
        window_id=f"wnf_window:{ANALYSIS_TICKER}:{ANALYSIS_AS_OF}",
        asset_ticker=ANALYSIS_TICKER,
        source_asset_ticker=ANALYSIS_TICKER,
        event_type=event_type.value,
        event_date="2026-04-21",
        published_at="2026-04-21T12:00:00Z",
        retrieved_at=ANALYSIS_CREATED_AT,
        period_bucket="current_week_to_date",
        source_document_id=f"src_{ANALYSIS_TICKER.lower()}_{event_id}",
        source_chunk_id=f"chk_{ANALYSIS_TICKER.lower()}_{event_id}",
        citation_ids=[citation_id],
        citation_asset_tickers={citation_id: ANALYSIS_TICKER},
        source_type=source_type,
        source_rank=1,
        source_rank_tier=source_rank_tier.value,
        source_quality=source_quality.value,
        allowlist_status=SourceAllowlistStatus.allowed.value,
        source_use_policy=SourceUsePolicy.summary_allowed.value,
        source_identity=f"local-weekly-news-smoke:{ANALYSIS_TICKER}:{event_id}",
        is_official=True,
        freshness_state=FreshnessState.fresh.value,
        evidence_state="supported",
        importance_score=10,
        duplicate_group_id=event_id,
        title_checksum=f"sha256:title:{ANALYSIS_TICKER}:{event_id}",
        evidence_checksum=f"sha256:evidence:{ANALYSIS_TICKER}:{event_id}",
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
    case_kind: str,
    asset_ticker: str,
    asset_type: str,
    validation_status: LlmValidationStatus,
    cacheable: bool,
    selected_item_count: int | None = None,
    expected_minimum_item_count: int | None = None,
    threshold_status: str | None = None,
    attempt: LlmGenerationAttemptMetadata,
    model_tier: str | None,
    live_call_attempted: bool,
    validation_contract: dict[str, bool],
) -> SmokeCaseResult:
    total_tokens = (
        attempt.prompt_tokens + attempt.completion_tokens
        if attempt.prompt_tokens is not None and attempt.completion_tokens is not None
        else None
    )
    if validation_status is LlmValidationStatus.valid and cacheable:
        return SmokeCaseResult(
            case_id=case_id,
            status="pass",
            reason_code="validated_and_cache_eligible",
            case_kind=case_kind,
            asset_ticker=asset_ticker,
            asset_type=asset_type,
            validation_status=validation_status.value,
            cacheable=True,
            selected_item_count=selected_item_count,
            expected_minimum_item_count=expected_minimum_item_count,
            threshold_status=threshold_status,
            model_tier=model_tier,
            attempt_status=attempt.status.value,
            latency_ms=attempt.latency_ms,
            prompt_tokens=attempt.prompt_tokens,
            completion_tokens=attempt.completion_tokens,
            total_tokens=total_tokens,
            cost_usd=attempt.cost_usd,
            live_call_attempted=live_call_attempted,
            validation_contract=validation_contract,
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
        case_kind=case_kind,
        asset_ticker=asset_ticker,
        asset_type=asset_type,
        validation_status=validation_status.value,
        cacheable=cacheable,
        selected_item_count=selected_item_count,
        expected_minimum_item_count=expected_minimum_item_count,
        threshold_status=threshold_status,
        model_tier=model_tier,
        attempt_status=attempt.status.value,
        latency_ms=attempt.latency_ms,
        prompt_tokens=attempt.prompt_tokens,
        completion_tokens=attempt.completion_tokens,
        total_tokens=total_tokens,
        cost_usd=attempt.cost_usd,
        live_call_attempted=live_call_attempted,
        validation_contract=validation_contract,
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


def _skipped(
    case_id: str,
    reason_code: str,
    *,
    selected_item_count: int | None = None,
    case_kind: str = "validation",
) -> SmokeCaseResult:
    return SmokeCaseResult(
        case_id=case_id,
        status="skipped",
        reason_code=reason_code,
        case_kind=case_kind,
        selected_item_count=selected_item_count,
    )


def _blocked(
    case_id: str,
    reason_code: str,
    *,
    case_kind: str = "validation",
    asset_ticker: str | None = None,
    asset_type: str | None = None,
    diagnostic_state: str | None = None,
    selected_item_count: int | None = None,
    expected_minimum_item_count: int | None = None,
    model_tier: str | None = None,
    live_call_attempted: bool = False,
    validation_contract: dict[str, bool] | None = None,
    blocked_regression_tickers: list[str] | None = None,
) -> SmokeCaseResult:
    return SmokeCaseResult(
        case_id=case_id,
        status="blocked",
        reason_code=reason_code,
        case_kind=case_kind,
        asset_ticker=asset_ticker,
        asset_type=asset_type,
        diagnostic_state=diagnostic_state,
        selected_item_count=selected_item_count,
        expected_minimum_item_count=expected_minimum_item_count,
        model_tier=model_tier,
        live_call_attempted=live_call_attempted,
        validation_contract=validation_contract,
        blocked_regression_tickers=blocked_regression_tickers,
    )


def _rollup_status(cases: list[SmokeCaseResult]) -> str:
    statuses = {case.status for case in cases}
    if "blocked" in statuses:
        return "blocked"
    if statuses == {"pass"}:
        return "pass"
    return "skipped"


def _all_case_ids() -> tuple[str, ...]:
    return (
        CHAT_STOCK_CASE_ID,
        CHAT_ETF_CASE_ID,
        ANALYSIS_CASE_ID,
        ANALYSIS_EMPTY_CASE_ID,
        ANALYSIS_ONE_ITEM_CASE_ID,
        BLOCKED_REGRESSION_CASE_ID,
    )


def _readiness_prerequisites(
    env: Mapping[str, str],
    runtime,
    *,
    smoke_enabled: bool,
) -> list[dict[str, object]]:
    return [
        _readiness_row(SMOKE_OPT_IN_ENV, smoke_enabled, "explicit_live_ai_smoke_opt_in_required"),
        _readiness_row(LLM_PROVIDER_ENV, runtime.provider_kind is LlmProviderKind.openrouter, "provider_must_be_openrouter"),
        _readiness_row(LIVE_GENERATION_ENV, runtime.live_generation_enabled, "live_generation_flag_required"),
        _readiness_row(PROVIDER_KEY_ENV, runtime.server_side_key_present, "server_side_key_presence_required"),
        _readiness_row("OPENROUTER_BASE_URL", runtime.base_url_configured, "openrouter_base_url_required"),
        _readiness_row("OPENROUTER_FREE_MODEL_ORDER", runtime.model_chain_configured, "openrouter_model_chain_required"),
        _readiness_row(
            "OPENROUTER_PAID_FALLBACK_MODEL",
            runtime.paid_fallback_model is not None,
            "openrouter_paid_fallback_model_required",
        ),
        _readiness_row(
            "LLM_VALIDATION_RETRY_COUNT",
            runtime.validation_retry_count >= 1,
            "validation_retry_count_minimum_required",
        ),
        _readiness_row(
            "LLM_REASONING_SUMMARY_ONLY",
            runtime.reasoning_summary_only is True,
            "reasoning_summary_only_required",
        ),
    ]


def _readiness_row(env_var: str, satisfied: bool, missing_reason_code: str) -> dict[str, object]:
    return {
        "env_var": env_var,
        "satisfied": bool(satisfied),
        "reason_code": "satisfied" if satisfied else missing_reason_code,
    }


def _single_asset_scope_valid(output_text: str, selected_ticker: str) -> bool:
    selected = selected_ticker.upper()
    normalized = (
        output_text.upper()
        .replace("'S", " ")
        .replace("/", " ")
        .replace("-", " ")
    )
    tokens = {
        token.strip(".,;:!?()[]{}\"'")
        for token in normalized.split()
    }
    mentioned_other_tickers = (tokens & set(KNOWN_MVP_SLICE_TICKERS)) - {selected}
    return not mentioned_other_tickers


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
