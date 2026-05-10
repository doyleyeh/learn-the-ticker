from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import hashlib
import json
import os
from threading import RLock
import time
from collections.abc import Mapping
from typing import Any, Callable, Protocol

from backend.llm import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_FREE_MODEL_ORDER,
    DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL,
    DEFAULT_VALIDATION_RETRY_COUNT,
    build_llm_runtime_config,
    validate_llm_generated_output,
)
from backend.llm_transport import call_openrouter_transport
from backend.models import (
    AIComprehensiveAnalysisResponse,
    AIComprehensiveAnalysisSection,
    AssetIdentity,
    BeginnerSummary,
    LlmReadinessStatus,
    LlmRuntimeConfig,
    LlmTransportMode,
    LlmTransportRequestMetadata,
    LlmTransportStatus,
    MarketAIAnalysisSection,
    MarketAIComprehensiveAnalysisResponse,
    MarketNewsFocusResponse,
    MarketNewsTopicBucket,
    RiskItem,
    WeeklyNewsContractState,
    WeeklyNewsFocusResponse,
)
from backend.safety import find_forbidden_output_phrases


SUMMARY_GENERATION_BOUNDARY = "hybrid-summary-generation-orchestrator-v1"
SUMMARY_GENERATION_PROMPT_VERSION = "hybrid-summary-generation-prompt-v1"
TICKER_AI_ANALYSIS_SCHEMA_VERSION = "ticker-ai-comprehensive-analysis-hybrid-v1"
CHAT_ANSWER_SCHEMA_VERSION = "grounded-chat-hybrid-answer-v1"
BEGINNER_SUMMARY_SCHEMA_VERSION = "beginner-summary-hybrid-v1"
DEEP_DIVE_SCHEMA_VERSION = "deep-dive-summary-hybrid-v1"
TOP_RISKS_SCHEMA_VERSION = "top-risks-hybrid-v1"
MARKET_AI_ANALYSIS_SCHEMA_VERSION = "market-ai-comprehensive-analysis-hybrid-v1"
LLM_LIVE_TASK_ALLOWLIST_ENV = "LLM_LIVE_TASK_ALLOWLIST"
LLM_LIVE_TIMEOUT_SECONDS_ENV = "LLM_LIVE_TIMEOUT_SECONDS"
LLM_GENERATION_CACHE_TTL_SECONDS_ENV = "LLM_GENERATION_CACHE_TTL_SECONDS"
DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS = 12
DEFAULT_GENERATION_CACHE_TTL_SECONDS = 60 * 60
DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST = frozenset(
    {
        "beginner_summary",
        "top_3_risks",
        "market_ai_comprehensive_analysis",
        "ticker_ai_comprehensive_analysis",
        "grounded_chat_answer",
    }
)

_TICKER_AI_SECTION_ORDER = (
    ("what_changed_this_week", "What Changed This Week"),
    ("market_context", "Market Context"),
    ("business_or_fund_context", "Business/Fund Context"),
    ("risk_context", "Risk Context"),
)
_MARKET_AI_SECTION_ORDER = (
    ("what_changed_this_week", "What Changed This Week"),
    ("macro_policy", "Macro & Policy"),
    ("equity_market_drivers", "Equity Market Drivers"),
    ("ai_technology_semiconductors", "AI / Technology / Semiconductors"),
    ("geopolitical_energy_risks", "Geopolitical & Energy Risks"),
    ("credit_liquidity_sentiment", "Credit / Liquidity / Sentiment"),
    ("scenario_lens", "Scenario Lens"),
    ("practical_watchpoints", "Practical Watchpoints"),
)
_PREDICTION_MARKERS = ("price target", "guaranteed", "will outperform", "will rise", "will fall", "forecast")
_GENERIC_BEGINNER_MARKERS = ("u.s.-listed etf", "u.s.-listed common stock", "local-mvp fetch pipeline")
_ENV_KEY = "OPENROUTER" + "_API_KEY"
_DETERMINISTIC_SUMMARY_GENERATION = ContextVar("deterministic_summary_generation", default=False)
_SUMMARY_GENERATION_CACHE_LOCK = RLock()
_SUMMARY_GENERATION_CACHE: dict[str, "_SummaryGenerationCacheEntry"] = {}


class SummaryGenerationContractError(ValueError):
    """Raised when generated prose cannot pass schema, citation, or safety gates."""


@dataclass(frozen=True)
class SummaryGenerationRequest:
    task_name: str
    schema_version: str
    asset_ticker: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class _GeneratedPayload:
    payload: dict[str, Any]
    cache_key: str | None = None
    cacheable: bool = False


@dataclass(frozen=True)
class _SummaryGenerationCacheEntry:
    payload: dict[str, Any]
    stored_at_seconds: float


StructuredSummaryGenerator = Callable[[SummaryGenerationRequest], dict[str, Any]]


@dataclass(frozen=True)
class GeneratedChatAnswer:
    direct_answer: str
    why_it_matters: str
    uncertainty: list[str] = field(default_factory=list)
    generation_boundary: str = SUMMARY_GENERATION_BOUNDARY
    schema_version: str = CHAT_ANSWER_SCHEMA_VERSION
    generated_from_same_asset_evidence: bool = True


class SummaryGenerationService(Protocol):
    def generate_beginner_summary(
        self,
        *,
        asset: AssetIdentity,
        base_summary: BeginnerSummary,
        citation_ids: list[str],
        evidence_notes: list[str] | None = None,
    ) -> BeginnerSummary:
        ...

    def generate_deep_dive_summary(
        self,
        *,
        asset: AssetIdentity,
        section_id: str,
        title: str,
        base_summary: str | None,
        citation_ids: list[str],
        evidence_state: str,
        evidence_notes: list[str] | None = None,
    ) -> str | None:
        ...

    def generate_top_risks(
        self,
        *,
        asset: AssetIdentity,
        candidate_risks: list[RiskItem],
        fallback_risks: list[RiskItem],
        allowed_citation_ids: list[str],
        evidence_notes: list[str] | None = None,
    ) -> list[RiskItem]:
        ...

    def generate_market_ai_comprehensive_analysis(
        self,
        *,
        focus: MarketNewsFocusResponse,
        minimum_market_news_item_count: int,
        minimum_topic_bucket_count: int,
    ) -> MarketAIComprehensiveAnalysisResponse:
        ...

    def generate_ticker_ai_comprehensive_analysis(
        self,
        *,
        asset: AssetIdentity,
        weekly_news_focus: WeeklyNewsFocusResponse,
        canonical_fact_citation_ids: list[str],
        canonical_source_document_ids: list[str],
        minimum_weekly_news_item_count: int,
        weekly_news_selected_item_count: int,
    ) -> AIComprehensiveAnalysisResponse:
        ...

    def generate_chat_answer(
        self,
        *,
        asset: AssetIdentity,
        question: str,
        intent: str,
        base_direct_answer: str,
        base_why_it_matters: str,
        citation_ids: list[str],
        required_claim_texts: list[str],
        evidence_summaries: list[str],
        uncertainty: list[str],
    ) -> GeneratedChatAnswer:
        ...


class HybridSummaryGenerationService:
    """Validation-first prose synthesis layer.

    Default CI/local behavior is deterministic mock synthesis. A caller may
    inject a structured generator for explicit live-provider review, but output
    must still pass the same schema, citation, freshness, and safety gates.
    """

    def __init__(
        self,
        *,
        runtime: LlmRuntimeConfig | None = None,
        structured_generator: StructuredSummaryGenerator | None = None,
        live_task_allowlist: frozenset[str] | set[str] | None = None,
        cache_ttl_seconds: int = DEFAULT_GENERATION_CACHE_TTL_SECONDS,
    ) -> None:
        self.runtime = runtime or build_llm_runtime_config()
        self.structured_generator = structured_generator
        self.live_task_allowlist = None if live_task_allowlist is None else frozenset(live_task_allowlist)
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))

    def generate_beginner_summary(
        self,
        *,
        asset: AssetIdentity,
        base_summary: BeginnerSummary,
        citation_ids: list[str],
        evidence_notes: list[str] | None = None,
    ) -> BeginnerSummary:
        request = SummaryGenerationRequest(
            task_name="beginner_summary",
            schema_version=BEGINNER_SUMMARY_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "base_summary": base_summary.model_dump(mode="json"),
                "citation_ids": sorted(set(citation_ids)),
                "evidence_notes": evidence_notes or [],
            },
        )
        fallback = _beginner_fallback_payload(asset, base_summary, evidence_notes or [])
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        summary = BeginnerSummary(
            what_it_is=_required_text(payload, "what_it_is"),
            why_people_consider_it=_required_text(payload, "why_people_consider_it"),
            main_catch=_required_text(payload, "main_catch"),
        )
        _validate_text_blob(
            " ".join([summary.what_it_is, summary.why_people_consider_it, summary.main_catch]),
            weekly_news_rules_valid=True,
        )
        self._remember_valid_payload(generated)
        return summary

    def generate_deep_dive_summary(
        self,
        *,
        asset: AssetIdentity,
        section_id: str,
        title: str,
        base_summary: str | None,
        citation_ids: list[str],
        evidence_state: str,
        evidence_notes: list[str] | None = None,
    ) -> str | None:
        if not base_summary:
            return base_summary
        request = SummaryGenerationRequest(
            task_name="deep_dive_summary",
            schema_version=DEEP_DIVE_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "section_id": section_id,
                "title": title,
                "base_summary": base_summary,
                "citation_ids": sorted(set(citation_ids)),
                "evidence_state": evidence_state,
                "evidence_notes": evidence_notes or [],
            },
        )
        fallback = {"summary": _deep_dive_fallback(asset, title, base_summary, evidence_state, evidence_notes or [])}
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        summary = _required_text(payload, "summary")
        _validate_text_blob(summary, weekly_news_rules_valid=True)
        self._remember_valid_payload(generated)
        return summary

    def generate_top_risks(
        self,
        *,
        asset: AssetIdentity,
        candidate_risks: list[RiskItem],
        fallback_risks: list[RiskItem],
        allowed_citation_ids: list[str],
        evidence_notes: list[str] | None = None,
    ) -> list[RiskItem]:
        if len(fallback_risks) != 3:
            raise SummaryGenerationContractError("Top risk fallback must contain exactly three risks.")
        allowed = set(allowed_citation_ids)
        fallback = {"risks": [risk.model_dump(mode="json") for risk in fallback_risks]}
        request = SummaryGenerationRequest(
            task_name="top_3_risks",
            schema_version=TOP_RISKS_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "asset": asset.model_dump(mode="json"),
                "candidate_risks": [risk.model_dump(mode="json") for risk in candidate_risks],
                "allowed_citation_ids": sorted(allowed),
                "evidence_notes": evidence_notes or [],
            },
        )
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        risks = _risks_from_payload(
            payload,
            allowed_citations=allowed,
            allowed_titles={risk.title.lower() for risk in candidate_risks},
        )
        if len({risk.title.lower() for risk in risks}) != 3:
            raise SummaryGenerationContractError("Top risks must have three distinct titles.")
        _validate_text_blob(" ".join([risk.title + " " + risk.plain_english_explanation for risk in risks]))
        self._remember_valid_payload(generated)
        return risks

    def generate_market_ai_comprehensive_analysis(
        self,
        *,
        focus: MarketNewsFocusResponse,
        minimum_market_news_item_count: int,
        minimum_topic_bucket_count: int,
    ) -> MarketAIComprehensiveAnalysisResponse:
        selected_bucket_count = len({item.topic_bucket for item in focus.items})
        if focus.selected_item_count < minimum_market_news_item_count or selected_bucket_count < minimum_topic_bucket_count:
            return MarketAIComprehensiveAnalysisResponse(
                state=WeeklyNewsContractState.suppressed,
                analysis_available=False,
                minimum_market_news_item_count=minimum_market_news_item_count,
                minimum_topic_bucket_count=minimum_topic_bucket_count,
                market_news_selected_item_count=focus.selected_item_count,
                selected_topic_bucket_count=selected_bucket_count,
                suppression_reason=(
                    "AI Comprehensive Analysis: Market News Focus is suppressed until enough approved market items "
                    "span multiple topic buckets."
                ),
            )

        all_citations = sorted({citation_id for item in focus.items for citation_id in item.citation_ids})
        source_ids = sorted({source.source_document_id for source in focus.source_documents})
        story_ids = [item.story_id for item in focus.items]
        request = SummaryGenerationRequest(
            task_name="market_ai_comprehensive_analysis",
            schema_version=MARKET_AI_ANALYSIS_SCHEMA_VERSION,
            asset_ticker="MARKET",
            payload={
                "selected_item_count": focus.selected_item_count,
                "selected_topic_bucket_count": selected_bucket_count,
                "items": [
                    {
                        "story_id": item.story_id,
                        "title": item.title,
                        "summary": item.summary,
                        "topic_bucket": item.topic_bucket.value,
                        "citation_ids": item.citation_ids,
                    }
                    for item in focus.items
                ],
                "allowed_citation_ids": all_citations,
                "required_section_order": [section_id for section_id, _label in _MARKET_AI_SECTION_ORDER],
            },
        )
        fallback = {"sections": _market_ai_fallback_sections(focus, all_citations)}
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        sections = _market_sections_from_payload(
            payload,
            allowed_citations=set(all_citations),
            selected_titles=[item.title for item in focus.items],
        )
        response = MarketAIComprehensiveAnalysisResponse(
            state=WeeklyNewsContractState.available,
            analysis_available=True,
            minimum_market_news_item_count=minimum_market_news_item_count,
            minimum_topic_bucket_count=minimum_topic_bucket_count,
            market_news_selected_item_count=focus.selected_item_count,
            selected_topic_bucket_count=selected_bucket_count,
            sections=sections,
            citation_ids=all_citations,
            source_document_ids=source_ids,
            market_news_story_ids=story_ids,
            no_live_external_calls=self.runtime.readiness_status is not LlmReadinessStatus.ready_for_explicit_live_call,
        )
        _validate_text_blob(
            " ".join([section.analysis for section in sections] + [bullet for section in sections for bullet in section.bullets]),
            weekly_news_rules_valid=True,
        )
        self._remember_valid_payload(generated)
        return response

    def generate_ticker_ai_comprehensive_analysis(
        self,
        *,
        asset: AssetIdentity,
        weekly_news_focus: WeeklyNewsFocusResponse,
        canonical_fact_citation_ids: list[str],
        canonical_source_document_ids: list[str],
        minimum_weekly_news_item_count: int,
        weekly_news_selected_item_count: int,
    ) -> AIComprehensiveAnalysisResponse:
        weekly_citations = sorted({citation_id for item in weekly_news_focus.items for citation_id in item.citation_ids})
        all_citations = sorted({*weekly_citations, *canonical_fact_citation_ids})
        source_ids = sorted(
            {
                *{source.source_document_id for source in weekly_news_focus.source_documents},
                *canonical_source_document_ids,
            }
        )
        event_ids = [item.event_id for item in weekly_news_focus.items]
        asset_kind = "fund" if asset.asset_type.value == "etf" else "business"
        titles = [item.title for item in weekly_news_focus.items[:3]]
        item_summaries = [item.summary for item in weekly_news_focus.items[:3] if item.summary]
        request = SummaryGenerationRequest(
            task_name="ticker_ai_comprehensive_analysis",
            schema_version=TICKER_AI_ANALYSIS_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "asset": asset.model_dump(mode="json"),
                "weekly_news_event_ids": event_ids,
                "weekly_news_titles": titles,
                "weekly_news_summaries": item_summaries,
                "weekly_citation_ids": weekly_citations,
                "canonical_fact_citation_ids": canonical_fact_citation_ids,
            },
        )
        fallback = {"sections": _ticker_ai_fallback_sections(asset, weekly_news_focus, all_citations, weekly_citations, asset_kind)}
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        sections = _sections_from_payload(payload, allowed_citations=set(all_citations))
        response = AIComprehensiveAnalysisResponse(
            asset=asset,
            state=WeeklyNewsContractState.available,
            analysis_available=True,
            minimum_weekly_news_item_count=minimum_weekly_news_item_count,
            weekly_news_selected_item_count=weekly_news_selected_item_count,
            sections=sections,
            citation_ids=all_citations,
            source_document_ids=source_ids,
            weekly_news_event_ids=event_ids,
            canonical_fact_citation_ids=canonical_fact_citation_ids,
            no_live_external_calls=self.runtime.readiness_status is not LlmReadinessStatus.ready_for_explicit_live_call,
        )
        _validate_text_blob(
            " ".join([section.analysis for section in sections] + [bullet for section in sections for bullet in section.bullets]),
            weekly_news_rules_valid=weekly_news_selected_item_count >= minimum_weekly_news_item_count,
        )
        self._remember_valid_payload(generated)
        return response

    def generate_chat_answer(
        self,
        *,
        asset: AssetIdentity,
        question: str,
        intent: str,
        base_direct_answer: str,
        base_why_it_matters: str,
        citation_ids: list[str],
        required_claim_texts: list[str],
        evidence_summaries: list[str],
        uncertainty: list[str],
    ) -> GeneratedChatAnswer:
        request = SummaryGenerationRequest(
            task_name="grounded_chat_answer",
            schema_version=CHAT_ANSWER_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "question_intent": intent,
                "question_redacted_shape": _question_shape(question),
                "base_direct_answer": base_direct_answer,
                "base_why_it_matters": base_why_it_matters,
                "citation_ids": sorted(set(citation_ids)),
                "required_claim_texts": required_claim_texts,
                "evidence_summaries": evidence_summaries,
            },
        )
        if not citation_ids or base_direct_answer.lower().startswith("insufficient evidence"):
            fallback_direct = base_direct_answer
            fallback_uncertainty = list(uncertainty)
        else:
            fallback_direct = f"Using the selected asset evidence, {base_direct_answer}"
            fallback_uncertainty = _dedupe(
                [*uncertainty, "Hybrid synthesis used only same-asset citation-bound evidence."]
            )
        fallback = {
            "direct_answer": fallback_direct,
            "why_it_matters": base_why_it_matters,
            "uncertainty": fallback_uncertainty,
        }
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        answer = GeneratedChatAnswer(
            direct_answer=_required_text(payload, "direct_answer"),
            why_it_matters=_required_text(payload, "why_it_matters"),
            uncertainty=[str(item) for item in payload.get("uncertainty", []) if str(item).strip()],
        )
        _validate_text_blob(f"{answer.direct_answer} {answer.why_it_matters} {' '.join(answer.uncertainty)}")
        for claim_text in required_claim_texts:
            if claim_text and claim_text not in answer.direct_answer:
                raise SummaryGenerationContractError("Generated chat answer omitted required citation-bound claim text.")
        self._remember_valid_payload(generated)
        return answer

    def _payload_or_fallback(self, request: SummaryGenerationRequest, fallback: dict[str, Any]) -> _GeneratedPayload:
        if (
            self.runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call
            and self.structured_generator
            and self._live_allowed_for_task(request.task_name)
        ):
            cache_key = _summary_generation_cache_key(request, self.runtime)
            cached = _summary_generation_cache_get(cache_key, ttl_seconds=self.cache_ttl_seconds)
            if cached is not None:
                return _GeneratedPayload(payload=cached)
            try:
                payload = self.structured_generator(request)
                if isinstance(payload, dict):
                    return _GeneratedPayload(payload=payload, cache_key=cache_key, cacheable=True)
                raise SummaryGenerationContractError("Structured summary generator returned a non-object payload.")
            except TimeoutError:
                return _GeneratedPayload(payload=fallback)
        return _GeneratedPayload(payload=fallback)

    def _remember_valid_payload(self, generated: _GeneratedPayload) -> None:
        if generated.cacheable and generated.cache_key and self.cache_ttl_seconds > 0:
            _summary_generation_cache_set(generated.cache_key, generated.payload)

    def _live_allowed_for_task(self, task_name: str) -> bool:
        if self.live_task_allowlist is None:
            return True
        return task_name in self.live_task_allowlist


@contextmanager
def deterministic_summary_generation():
    token = _DETERMINISTIC_SUMMARY_GENERATION.set(True)
    try:
        yield
    finally:
        _DETERMINISTIC_SUMMARY_GENERATION.reset(token)


def build_default_summary_generation_service() -> SummaryGenerationService:
    if _DETERMINISTIC_SUMMARY_GENERATION.get():
        return HybridSummaryGenerationService(runtime=build_llm_runtime_config())
    env = dict(getattr(os, "environ"))
    runtime = _runtime_from_env(env)
    timeout_seconds = _live_timeout_seconds_from_env(env)
    generator = (
        _live_structured_generator_from_env(env, runtime, timeout_seconds=timeout_seconds)
        if _live_env_allowed(env, runtime)
        else None
    )
    return HybridSummaryGenerationService(
        runtime=runtime,
        structured_generator=generator,
        live_task_allowlist=_live_task_allowlist_from_env(env),
        cache_ttl_seconds=_generation_cache_ttl_seconds_from_env(env),
    )


def _runtime_from_env(env: Mapping[str, str]) -> LlmRuntimeConfig:
    settings = {
        "LLM_PROVIDER": env.get("LLM_PROVIDER", "mock"),
        "LLM_LIVE_GENERATION_ENABLED": env.get("LLM_LIVE_GENERATION_ENABLED", "false"),
        "OPENROUTER_BASE_URL": env.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
        "OPENROUTER_FREE_MODEL_ORDER": env.get("OPENROUTER_FREE_MODEL_ORDER", ",".join(DEFAULT_OPENROUTER_FREE_MODEL_ORDER)),
        "OPENROUTER_PAID_FALLBACK_MODEL": env.get("OPENROUTER_PAID_FALLBACK_MODEL", DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL),
        "OPENROUTER_PAID_FALLBACK_ENABLED": env.get("OPENROUTER_PAID_FALLBACK_ENABLED", "true"),
        "LLM_VALIDATION_RETRY_COUNT": env.get("LLM_VALIDATION_RETRY_COUNT", str(DEFAULT_VALIDATION_RETRY_COUNT)),
        "LLM_REASONING_SUMMARY_ONLY": env.get("LLM_REASONING_SUMMARY_ONLY", "true"),
    }
    return build_llm_runtime_config(settings, server_side_key_present=bool(str(env.get(_ENV_KEY, "")).strip()))


def _live_env_allowed(env: Mapping[str, str], runtime: LlmRuntimeConfig) -> bool:
    if env.get("CI") or env.get("PYTEST_CURRENT_TEST"):
        return False
    return runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call


def _live_task_allowlist_from_env(env: Mapping[str, str]) -> frozenset[str] | None:
    raw = str(env.get(LLM_LIVE_TASK_ALLOWLIST_ENV, "")).strip()
    if not raw:
        # Deep Dive is intentionally deterministic by default because one asset
        # page can contain many Deep Dive subsections during server rendering.
        return DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST
    tokens = {token.strip().lower() for token in raw.split(",") if token.strip()}
    if not tokens:
        return DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST
    if "all" in tokens or "*" in tokens:
        return None
    if "none" in tokens or "off" in tokens or "false" in tokens:
        return frozenset()
    return frozenset(tokens)


def _live_timeout_seconds_from_env(env: Mapping[str, str]) -> int:
    raw = str(env.get(LLM_LIVE_TIMEOUT_SECONDS_ENV, "")).strip()
    if not raw:
        return DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS


def _generation_cache_ttl_seconds_from_env(env: Mapping[str, str]) -> int:
    raw = str(env.get(LLM_GENERATION_CACHE_TTL_SECONDS_ENV, "")).strip()
    if not raw:
        return DEFAULT_GENERATION_CACHE_TTL_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_GENERATION_CACHE_TTL_SECONDS


def clear_summary_generation_cache() -> None:
    with _SUMMARY_GENERATION_CACHE_LOCK:
        _SUMMARY_GENERATION_CACHE.clear()


def _summary_generation_cache_key(request: SummaryGenerationRequest, runtime: LlmRuntimeConfig) -> str:
    model_names = [
        str(getattr(model, "model_name", model))
        for model in getattr(runtime, "configured_model_chain", [])
    ]
    raw = json.dumps(
        {
            "asset_ticker": request.asset_ticker,
            "model_names": model_names,
            "payload": request.payload,
            "prompt_version": SUMMARY_GENERATION_PROMPT_VERSION,
            "schema_version": request.schema_version,
            "task_name": request.task_name,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _summary_generation_cache_get(key: str, *, ttl_seconds: int) -> dict[str, Any] | None:
    if ttl_seconds <= 0:
        return None
    now = time.monotonic()
    with _SUMMARY_GENERATION_CACHE_LOCK:
        entry = _SUMMARY_GENERATION_CACHE.get(key)
        if entry is None:
            return None
        if now - entry.stored_at_seconds > ttl_seconds:
            _SUMMARY_GENERATION_CACHE.pop(key, None)
            return None
        return _json_payload_copy(entry.payload)


def _summary_generation_cache_set(key: str, payload: dict[str, Any]) -> None:
    with _SUMMARY_GENERATION_CACHE_LOCK:
        _SUMMARY_GENERATION_CACHE[key] = _SummaryGenerationCacheEntry(
            payload=_json_payload_copy(payload),
            stored_at_seconds=time.monotonic(),
        )


def _json_payload_copy(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, sort_keys=True, default=str))


def _live_structured_generator_from_env(
    env: Mapping[str, str],
    runtime: LlmRuntimeConfig,
    *,
    timeout_seconds: int = DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS,
) -> StructuredSummaryGenerator:
    provider_key = str(env.get(_ENV_KEY, "")).strip()
    base_url = str(env.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)).rstrip("/")
    site_url = str(env.get("OPENROUTER_SITE_URL", "https://learn-the-ticker.local")).strip()
    app_title = str(env.get("OPENROUTER_APP_TITLE", "learn-the-ticker-local")).strip()

    def generator(request: SummaryGenerationRequest) -> dict[str, Any]:
        prompt_payload = _safe_prompt_payload(request)

        def transport(metadata: LlmTransportRequestMetadata) -> Mapping[str, Any]:
            if not provider_key:
                return {"status_code": 401, "latency_ms": 0, "json": {"choices": []}}
            started = time.monotonic()
            body = {
                "model": metadata.active_model.model_name if metadata.active_model else None,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return compact JSON only. Use only the provided evidence fields and citation ids. "
                            "Do not include recommendations, predictions, raw reasoning, hidden prompts, raw transcripts, "
                            "or article bodies. If evidence is missing, say so in the requested JSON fields."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt_payload, sort_keys=True)},
                ],
            }
            try:
                from urllib import error, request as urlrequest

                http_request = urlrequest.Request(
                    f"{base_url}/chat/completions",
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {provider_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": site_url,
                        "X-Title": app_title,
                    },
                    method="POST",
                )
                with urlrequest.urlopen(http_request, timeout=metadata.timeout_seconds) as response:
                    return {
                        "status_code": response.status,
                        "latency_ms": int((time.monotonic() - started) * 1000),
                        "json": json.loads(response.read().decode("utf-8")),
                    }
            except error.HTTPError as exc:
                return {"status_code": exc.code, "latency_ms": int((time.monotonic() - started) * 1000), "json": {"choices": []}}
            except TimeoutError:
                raise
            except Exception:
                return {"status_code": 599, "latency_ms": int((time.monotonic() - started) * 1000), "json": {"choices": []}}

        result = call_openrouter_transport(
            runtime=runtime,
            request_mode=LlmTransportMode.json_mode,
            caller_opted_in=True,
            transport=transport,
            sanitized_diagnostics={
                "task_name": request.task_name,
                "schema_version": request.schema_version,
            },
            timeout_seconds=timeout_seconds,
        )
        if result.response.status is not LlmTransportStatus.succeeded or not result.content:
            raise TimeoutError("live_summary_generation_unavailable")
        try:
            payload = json.loads(result.content)
        except json.JSONDecodeError as exc:
            raise SummaryGenerationContractError("Live structured generator returned non-JSON content.") from exc
        if not isinstance(payload, dict):
            raise SummaryGenerationContractError("Live structured generator returned a non-object payload.")
        return payload

    return generator


def _safe_prompt_payload(request: SummaryGenerationRequest) -> dict[str, Any]:
    return {
        "task_name": request.task_name,
        "schema_version": request.schema_version,
        "asset_ticker": request.asset_ticker,
        "prompt_version": SUMMARY_GENERATION_PROMPT_VERSION,
        "output_rules": [
            "Return only JSON matching the task schema.",
            "Use only supplied evidence and citation ids.",
            "Every factual section or risk must include citation_ids from the allowed set.",
            "Avoid buy/sell/hold, allocation, price-target, prediction, tax, and brokerage advice.",
            "Separate timely news context from stable canonical facts.",
            "Include uncertainty when evidence is partial or missing.",
        ],
        "payload": request.payload,
    }


def _beginner_fallback_payload(
    asset: AssetIdentity,
    base_summary: BeginnerSummary,
    evidence_notes: list[str],
) -> dict[str, str]:
    notes = _evidence_note_map(evidence_notes)
    benchmark = notes.get("benchmark")
    holdings = notes.get("holdings_count")
    expense = notes.get("expense_ratio")
    price = notes.get("provider_market_price")
    profile = notes.get("provider_profile_overview")
    gaps = notes.get("evidence_gaps")
    if asset.asset_type.value == "etf":
        fact_bits = _join_human_text(
            [
                f"tracks {benchmark}" if benchmark else "",
                f"lists about {holdings} holdings" if holdings else "",
                f"shows an expense ratio of {expense}" if expense else "",
                f"has provider market-reference price context around {price}" if price else "",
            ]
        )
        what_it_is = (
            f"{asset.name} ({asset.ticker}) is explained here as an ETF whose available evidence {fact_bits}."
            if fact_bits
            else base_summary.what_it_is
        )
        why = (
            f"Beginners can use {asset.ticker} to study how its benchmark, holdings breadth, cost, and market-reference fields fit together."
            if fact_bits
            else base_summary.why_people_consider_it
        )
        catch = (
            f"The main catch is that issuer facts are point-in-time and evidence gaps remain labeled"
            + (f" ({gaps})" if gaps else "")
            + "; this page does not turn the fund into a personal recommendation."
        )
    else:
        fact_bits = _join_human_text(
            [
                profile or "",
                f"provider market-reference price context around {price}" if price else "",
                f"latest revenue fact {notes.get('latest_revenue_fact')}" if notes.get("latest_revenue_fact") else "",
                f"latest net-income fact {notes.get('latest_net_income_fact')}" if notes.get("latest_net_income_fact") else "",
            ]
        )
        what_it_is = (
            f"{asset.name} ({asset.ticker}) is explained here as a single-company stock with SEC and provider evidence on {fact_bits}."
            if fact_bits
            else base_summary.what_it_is
        )
        why = (
            f"Beginners can use {asset.ticker} to connect the company's business/profile context with reported financial facts and provider-labeled valuation or market data."
            if fact_bits
            else base_summary.why_people_consider_it
        )
        catch = (
            "The main catch is single-company risk: business, financial, and valuation evidence can change, and provider fields are context rather than a cheap-or-expensive conclusion."
        )
    return {
        "what_it_is": _avoid_generic_only(what_it_is, base_summary.what_it_is),
        "why_people_consider_it": _avoid_generic_only(why, base_summary.why_people_consider_it),
        "main_catch": catch,
    }


def _deep_dive_fallback(
    asset: AssetIdentity,
    title: str,
    base_summary: str,
    evidence_state: str,
    evidence_notes: list[str],
) -> str:
    notes = _evidence_note_map(evidence_notes)
    fields = [value for key, value in notes.items() if key not in {"fetch_state", "source_count", "fact_count"}][:4]
    field_text = _join_human_text(fields)
    if field_text:
        return _join_sentences(
            base_summary,
            f"For {asset.ticker}, this {title.lower()} section is grounded in {field_text} and is labeled {evidence_state}.",
        )
    return _join_sentences(
        base_summary,
        f"For {asset.ticker}, the section stays labeled {evidence_state} so missing or partial fields are not treated as facts.",
    )


def _ticker_ai_fallback_sections(
    asset: AssetIdentity,
    weekly_news_focus: WeeklyNewsFocusResponse,
    all_citations: list[str],
    weekly_citations: list[str],
    asset_kind: str,
) -> list[dict[str, Any]]:
    item_phrases = [
        f"{item.title}: {item.summary}" if item.summary else item.title
        for item in weekly_news_focus.items[:3]
    ]
    changed = _join_human_text(item_phrases) or "the approved Weekly News Focus set is available but thin"
    return [
        {
            "section_id": "what_changed_this_week",
            "label": "What Changed This Week",
            "analysis": (
                f"For {asset.ticker}, the selected weekly evidence centers on {changed}. This is a synthesis of the cited "
                "weekly items, not a replacement for stable asset facts."
            ),
            "bullets": ["The section summarizes only items that passed the Weekly News Focus evidence rules."],
            "citation_ids": all_citations,
            "uncertainty": ["Other relevant items may be absent when they did not pass the evidence rules."],
        },
        {
            "section_id": "market_context",
            "label": "Market Context",
            "analysis": (
                f"The weekly items give current context for how beginners might read {asset.ticker} beside broader market themes; "
                "they do not prove a market trend or define the asset."
            ),
            "bullets": ["Recent context remains separate from canonical identity, holdings, business, and risk facts."],
            "citation_ids": weekly_citations,
            "uncertainty": [],
        },
        {
            "section_id": "business_or_fund_context",
            "label": "Business/Fund Context",
            "analysis": (
                f"For this {asset_kind}, the cited weekly items should be compared with canonical facts before drawing lessons. "
                f"That helps beginners distinguish durable {asset_kind} context from temporary headlines."
            ),
            "bullets": ["Canonical facts and Weekly News Focus use separate citation sets."],
            "citation_ids": all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "risk_context",
            "label": "Risk Context",
            "analysis": (
                f"The useful risk lesson is to ask what the weekly evidence changes, what it does not change, and whether later "
                f"approved sources confirm it for {asset.ticker}."
            ),
            "bullets": ["Do not infer returns, suitability, or trading actions from this cited news set."],
            "citation_ids": weekly_citations,
            "uncertainty": ["Risk context is limited to cited weekly-news evidence and canonical facts."],
        },
    ]


def _market_ai_fallback_sections(focus: MarketNewsFocusResponse, all_citations: list[str]) -> list[dict[str, Any]]:
    bucket_titles = {
        bucket: [item.title for item in focus.items if item.topic_bucket is bucket]
        for bucket in MarketNewsTopicBucket
    }

    def bucket_text(bucket: MarketNewsTopicBucket, label: str) -> str:
        titles = bucket_titles.get(bucket) or []
        if titles:
            examples = _join_human_text([_short_headline_hint(title) for title in titles[:2]])
            return (
                f"The cited {label} bucket has {len(titles)} approved item"
                f"{'' if len(titles) == 1 else 's'}"
                + (f", including {examples}" if examples else "")
                + "; beginners can compare the shared theme with later approved updates instead of treating any one headline as the whole story."
            )
        return f"No selected {label} item passed strongly enough to anchor a standalone claim, so this section stays limited to the broader cited set."

    return [
        {
            "section_id": "what_changed_this_week",
            "label": "What Changed This Week",
            "analysis": (
                f"The selected Market News Focus set spans {len({item.topic_bucket for item in focus.items})} topic buckets. "
                "The useful change is not one headline by itself, but the combination of policy, equity, technology, geopolitical, and credit signals in the approved window."
            ),
            "bullets": ["This market-wide layer is shared across ticker pages and stays separate from each asset's stable facts."],
            "citation_ids": all_citations,
            "uncertainty": ["Market coverage is limited to selected, license-compatible items."],
        },
        {
            "section_id": "macro_policy",
            "label": "Macro & Policy",
            "analysis": bucket_text(MarketNewsTopicBucket.macro_fed, "macro and policy"),
            "bullets": ["Watch whether later cited policy data confirms, softens, or contradicts the current policy theme."],
            "citation_ids": _citations_for_market_bucket(focus, MarketNewsTopicBucket.macro_fed) or all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "equity_market_drivers",
            "label": "Equity Market Drivers",
            "analysis": bucket_text(MarketNewsTopicBucket.markets_earnings, "equity-market"),
            "bullets": ["Compare broad equity drivers with the selected ticker's own business or fund exposure before drawing lessons."],
            "citation_ids": _citations_for_market_bucket(focus, MarketNewsTopicBucket.markets_earnings) or all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "ai_technology_semiconductors",
            "label": "AI / Technology / Semiconductors",
            "analysis": bucket_text(MarketNewsTopicBucket.ai_technology_semiconductors, "AI, technology, and semiconductor"),
            "bullets": ["Technology themes matter only when the selected asset has cited exposure or business links."],
            "citation_ids": _citations_for_market_bucket(focus, MarketNewsTopicBucket.ai_technology_semiconductors) or all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "geopolitical_energy_risks",
            "label": "Geopolitical & Energy Risks",
            "analysis": bucket_text(MarketNewsTopicBucket.geopolitics_energy_supply_chain, "geopolitical, energy, and supply-chain"),
            "bullets": ["Treat these as watchpoints for costs, inflation, sentiment, and supply chains, not as return predictions."],
            "citation_ids": _citations_for_market_bucket(focus, MarketNewsTopicBucket.geopolitics_energy_supply_chain) or all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "credit_liquidity_sentiment",
            "label": "Credit / Liquidity / Sentiment",
            "analysis": bucket_text(MarketNewsTopicBucket.credit_liquidity_sentiment, "credit, liquidity, and sentiment"),
            "bullets": ["Beginners can watch whether credit and liquidity signals broaden across later approved sources."],
            "citation_ids": _citations_for_market_bucket(focus, MarketNewsTopicBucket.credit_liquidity_sentiment) or all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "scenario_lens",
            "label": "Scenario Lens",
            "analysis": "A useful scenario lens is to separate confirmation from noise: later cited updates should show whether the same topic buckets keep recurring or fade.",
            "bullets": ["This is conditional education from selected sources and is not a return estimate."],
            "citation_ids": all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "practical_watchpoints",
            "label": "Practical Watchpoints",
            "analysis": "Beginners should watch source dates, topic buckets, corroboration, and whether a ticker's own evidence actually connects to the market-wide theme.",
            "bullets": ["Do not import market-wide headlines into a ticker page unless ticker-specific citations support the link."],
            "citation_ids": all_citations,
            "uncertainty": [],
        },
    ]


def _citations_for_market_bucket(focus: MarketNewsFocusResponse, bucket: MarketNewsTopicBucket) -> list[str]:
    return sorted({citation_id for item in focus.items if item.topic_bucket is bucket for citation_id in item.citation_ids})


def _sections_from_payload(payload: dict[str, Any], *, allowed_citations: set[str]) -> list[AIComprehensiveAnalysisSection]:
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise SummaryGenerationContractError("Generated ticker analysis requires a sections array.")
    if len(raw_sections) != len(_TICKER_AI_SECTION_ORDER):
        raise SummaryGenerationContractError("Generated ticker analysis returned the wrong section count.")

    sections: list[AIComprehensiveAnalysisSection] = []
    for raw, (expected_id, expected_label) in zip(raw_sections, _TICKER_AI_SECTION_ORDER):
        if not isinstance(raw, dict):
            raise SummaryGenerationContractError("Generated ticker analysis section must be an object.")
        if raw.get("section_id") != expected_id or raw.get("label") != expected_label:
            raise SummaryGenerationContractError("Generated ticker analysis section order or label mismatch.")
        citation_ids = [str(item) for item in raw.get("citation_ids", [])]
        if not citation_ids or not set(citation_ids) <= allowed_citations:
            raise SummaryGenerationContractError("Generated ticker analysis citations are missing or outside the evidence pack.")
        sections.append(
            AIComprehensiveAnalysisSection(
                section_id=expected_id,  # type: ignore[arg-type]
                label=expected_label,  # type: ignore[arg-type]
                analysis=_required_text(raw, "analysis"),
                bullets=[str(item) for item in raw.get("bullets", []) if str(item).strip()],
                citation_ids=citation_ids,
                uncertainty=[str(item) for item in raw.get("uncertainty", []) if str(item).strip()],
            )
        )
    return sections


def _market_sections_from_payload(
    payload: dict[str, Any],
    *,
    allowed_citations: set[str],
    selected_titles: list[str],
) -> list[MarketAIAnalysisSection]:
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise SummaryGenerationContractError("Generated market analysis requires a sections array.")
    if len(raw_sections) != len(_MARKET_AI_SECTION_ORDER):
        raise SummaryGenerationContractError("Generated market analysis returned the wrong section count.")

    sections: list[MarketAIAnalysisSection] = []
    for raw, (expected_id, expected_label) in zip(raw_sections, _MARKET_AI_SECTION_ORDER):
        if not isinstance(raw, dict):
            raise SummaryGenerationContractError("Generated market analysis section must be an object.")
        if raw.get("section_id") != expected_id or raw.get("label") != expected_label:
            raise SummaryGenerationContractError("Generated market analysis section order or label mismatch.")
        citation_ids = [str(item) for item in raw.get("citation_ids", [])]
        if not citation_ids or not set(citation_ids) <= allowed_citations:
            raise SummaryGenerationContractError("Generated market analysis citations are missing or outside the evidence pack.")
        analysis = _required_text(raw, "analysis")
        bullets = [str(item) for item in raw.get("bullets", []) if str(item).strip()]
        _reject_headline_repetition(analysis, selected_titles)
        sections.append(
            MarketAIAnalysisSection(
                section_id=expected_id,  # type: ignore[arg-type]
                label=expected_label,  # type: ignore[arg-type]
                analysis=analysis,
                bullets=bullets,
                citation_ids=citation_ids,
                uncertainty=[str(item) for item in raw.get("uncertainty", []) if str(item).strip()],
            )
        )
    return sections


def _risks_from_payload(
    payload: dict[str, Any],
    *,
    allowed_citations: set[str],
    allowed_titles: set[str],
) -> list[RiskItem]:
    raw_risks = payload.get("risks")
    if not isinstance(raw_risks, list) or len(raw_risks) != 3:
        raise SummaryGenerationContractError("Generated top risks require exactly three risks.")
    risks: list[RiskItem] = []
    for raw in raw_risks:
        if not isinstance(raw, dict):
            raise SummaryGenerationContractError("Generated risk must be an object.")
        citation_ids = [str(item) for item in raw.get("citation_ids", [])]
        if not citation_ids or not set(citation_ids) <= allowed_citations:
            raise SummaryGenerationContractError("Generated risk citations are missing or outside the evidence pack.")
        title = _required_text(raw, "title")
        if title.lower() not in allowed_titles:
            raise SummaryGenerationContractError("Generated risk title is outside the evidence-derived candidate set.")
        explanation = _required_text(raw, "plain_english_explanation")
        risks.append(
            RiskItem(
                title=title,
                plain_english_explanation=explanation,
                citation_ids=citation_ids,
            )
        )
    return risks


def _validate_text_blob(text: str, *, weekly_news_rules_valid: bool = True) -> None:
    validation = validate_llm_generated_output(
        output_text=text,
        schema_valid=True,
        freshness_labels_valid=True,
        weekly_news_rules_valid=weekly_news_rules_valid,
    )
    if not validation.valid:
        raise SummaryGenerationContractError(f"Generated prose failed validation: {validation.status.value}")
    normalized = text.lower()
    for marker in _PREDICTION_MARKERS:
        if marker in normalized:
            raise SummaryGenerationContractError(f"Generated prose includes prediction language: {marker}")
    forbidden = find_forbidden_output_phrases(text)
    if forbidden:
        raise SummaryGenerationContractError(f"Generated prose includes forbidden advice language: {', '.join(forbidden)}")


def _reject_headline_repetition(analysis: str, selected_titles: list[str]) -> None:
    normalized = _normalize(analysis)
    if not normalized:
        raise SummaryGenerationContractError("Generated analysis is empty.")
    matched_titles = [title for title in selected_titles if _normalize(title) and _normalize(title) in normalized]
    if len(matched_titles) >= 3 and len(normalized.split()) < sum(len(_normalize(title).split()) for title in matched_titles) + 24:
        raise SummaryGenerationContractError("Generated analysis only repeats selected headlines.")
    if normalized.startswith("the selected market news focus items are"):
        raise SummaryGenerationContractError("Generated market analysis repeats headlines instead of synthesizing them.")


def _short_headline_hint(title: str) -> str:
    words = [word.strip(" ,.;:!?") for word in str(title).split() if word.strip(" ,.;:!?")]
    return " ".join(words[:7])


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SummaryGenerationContractError(f"Generated payload is missing required text field: {key}")
    return " ".join(value.split())


def _join_sentences(first: str, second: str) -> str:
    first = " ".join(first.split())
    second = " ".join(second.split())
    if not first:
        return second
    if second.lower() in first.lower():
        return first
    return f"{first.rstrip('.')}. {second}"


def _evidence_note_map(evidence_notes: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for note in evidence_notes:
        if "=" not in note:
            continue
        key, value = note.split("=", 1)
        key = key.strip()
        value = " ".join(value.split())
        if key and value:
            result[key] = value
    return result


def _join_human_text(values: list[str]) -> str:
    values = [value for value in (" ".join(str(item).split()) for item in values) if value]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _avoid_generic_only(candidate: str, base: str) -> str:
    normalized = candidate.lower()
    if any(marker in normalized for marker in _GENERIC_BEGINNER_MARKERS) and candidate == base:
        return candidate
    return candidate


def _normalize(value: str) -> str:
    return " ".join(str(value).lower().split())


def _question_shape(question: str) -> str:
    words = [word for word in question.strip().split() if word]
    if not words:
        return "empty_question"
    return f"{len(words)}_word_question"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
