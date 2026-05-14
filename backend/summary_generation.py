from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import hashlib
import json
import os
import re
from threading import RLock
import time
from collections.abc import Iterable, Mapping
from typing import Any, Callable, Protocol

from backend.analysis_pack_numeric_validation import validate_generated_numeric_integrity
from backend.citations import CitationValidationClaim, CitationValidationContext
from backend.generation_evidence import (
    GENERATION_CONTEXT_SCHEMA_VERSION,
    GENERATION_EVIDENCE_PACK_SCHEMA_VERSION,
    empty_generation_evidence_pack,
    generation_pack_allowed_asset_tickers,
    generation_pack_allowed_numeric_facts,
    generation_pack_citation_evidence,
    generation_pack_generation_context,
)
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
    GenerationDiagnostics,
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
SUMMARY_GENERATION_PROMPT_VERSION = "hybrid-summary-generation-prompt-v2"
TICKER_AI_ANALYSIS_SCHEMA_VERSION = "ticker-ai-comprehensive-analysis-hybrid-v1"
CHAT_ANSWER_SCHEMA_VERSION = "grounded-chat-hybrid-answer-v1"
BEGINNER_SUMMARY_SCHEMA_VERSION = "beginner-summary-hybrid-v1"
DEEP_DIVE_SCHEMA_VERSION = "deep-dive-summary-hybrid-v1"
TOP_RISKS_SCHEMA_VERSION = "top-risks-hybrid-v1"
MARKET_AI_ANALYSIS_SCHEMA_VERSION = "market-ai-comprehensive-analysis-hybrid-v1"
LLM_LIVE_TASK_ALLOWLIST_ENV = "LLM_LIVE_TASK_ALLOWLIST"
LLM_LIVE_TIMEOUT_SECONDS_ENV = "LLM_LIVE_TIMEOUT_SECONDS"
LLM_GENERATION_CACHE_TTL_SECONDS_ENV = "LLM_GENERATION_CACHE_TTL_SECONDS"
LLM_LIVE_FAILURE_COOLDOWN_SECONDS_ENV = "LLM_LIVE_FAILURE_COOLDOWN_SECONDS"
LLM_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS_ENV = "LLM_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS"
DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS = 4
DEFAULT_GENERATION_CACHE_TTL_SECONDS = 60 * 60
DEFAULT_LIVE_FAILURE_COOLDOWN_SECONDS = 60
DEFAULT_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS = 2
DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST = frozenset(
    {
        "beginner_summary",
        "deep_dive_summary",
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
_TASK_PROMPT_SPECS: dict[str, dict[str, Any]] = {
    "beginner_summary": {
        "objective": "Write a concise asset explanation for beginners using curated asset/profile context, not the data pipeline.",
        "output_shape": {
            "what_it_is": "string",
            "why_people_consider_it": "string",
            "main_catch": "string",
            "supporting_claims": [{"claim_text": "string", "claim_type": "factual|interpretation|risk", "citation_ids": ["id"]}],
        },
        "instructions": [
            "Use generation_context.asset_profile, identity_context, exposure_context, and canonical_facts before any timely context.",
            "Make every asset-specific factual phrase traceable to supporting_claims.",
            "Do not mention quote, chart, price, volume, RSI, MACD, KD, ADX, provider key names, fixtures, local MVP, or available evidence.",
            "Explain what the company or fund is and what a beginner can learn from it.",
        ],
        "example_output": {
            "what_it_is": "Plain-English asset identity.",
            "why_people_consider_it": "Plain-English learning reason.",
            "main_catch": "Plain-English risk or limitation.",
            "supporting_claims": [{"claim_text": "Short cited claim.", "claim_type": "factual", "citation_ids": ["allowed_id"]}],
        },
    },
    "deep_dive_summary": {
        "objective": "Add non-redundant analytical context for one section using the section evidence.",
        "output_shape": {
            "summary": "string",
            "supporting_claims": [{"claim_text": "string", "claim_type": "factual|interpretation|risk", "citation_ids": ["id"]}],
        },
        "instructions": [
            "Connect section facts to business, fund, risk, or evidence-limit implications.",
            "Do not duplicate dashboard rows without explaining why they matter.",
            "If evidence_state is partial, name the limitation in plain English.",
            "Do not describe the section as using evidence, pipeline fields, fixtures, local tests, or provider market-reference data.",
        ],
        "example_output": {
            "summary": "Plain-English section explanation.",
            "supporting_claims": [{"claim_text": "Short cited claim.", "claim_type": "factual", "citation_ids": ["allowed_id"]}],
        },
    },
    "top_3_risks": {
        "objective": "Select exactly three evidence-derived risks and explain them without advice.",
        "output_shape": {
            "risks": [
                {
                    "title": "candidate title",
                    "plain_english_explanation": "string",
                    "citation_ids": ["id"],
                    "supporting_claims": [{"claim_text": "string", "claim_type": "risk", "citation_ids": ["id"]}],
                }
            ]
        },
        "instructions": ["Use only candidate risk titles.", "No trading, allocation, or suitability recommendations."],
    },
    "market_ai_comprehensive_analysis": {
        "objective": "Synthesize selected Market News with macro indicators and allowed numeric facts.",
        "output_shape": {
            "sections": [
                {
                    "section_id": "required id",
                    "label": "required label",
                    "analysis": "string",
                    "bullets": ["string"],
                    "citation_ids": ["id"],
                    "uncertainty": ["string"],
                    "supporting_claims": [{"claim_text": "string", "claim_type": "recent|interpretation|factual", "citation_ids": ["id"]}],
                }
            ]
        },
        "instructions": [
            "Use selected market_news, generation_context.market_context, economic_indicators, and allowed_numeric_facts only; never infer from unselected headlines.",
            "Every explicit number must appear in allowed_numeric_facts.",
            "Synthesize themes across selected stories and macro indicators; do not only count buckets or repeat headlines.",
            "Use Scenario Lens as conditional education, not prediction.",
        ],
        "schema_hint": "Return a root object with exactly one sections array. Each section must include section_id, label, analysis, bullets, citation_ids, uncertainty, and supporting_claims.",
    },
    "ticker_ai_comprehensive_analysis": {
        "objective": "Connect ticker Weekly News to canonical facts, market context, macro context, and compact technical context.",
        "output_shape": {
            "sections": [
                {
                    "section_id": "required id",
                    "label": "required label",
                    "analysis": "string",
                    "bullets": ["string"],
                    "citation_ids": ["id"],
                    "uncertainty": ["string"],
                    "supporting_claims": [{"claim_text": "string", "claim_type": "recent|interpretation|risk|factual", "citation_ids": ["id"]}],
                }
            ]
        },
        "instructions": [
            "Start from weekly_news, then connect only to supplied canonical_facts, generation_context asset profile/exposure, market_news, economic_indicators, and technical_indicators.",
            "Keep stable asset identity separate from timely context.",
            "Mention technical indicators only as educational context and only when supplied.",
        ],
        "schema_hint": "Return a root object with exactly one sections array. Each section must include section_id, label, analysis, bullets, citation_ids, uncertainty, and supporting_claims.",
    },
    "grounded_chat_answer": {
        "objective": "Answer from selected same-asset evidence while preserving required claims.",
        "output_shape": {
            "direct_answer": "string",
            "why_it_matters": "string",
            "uncertainty": ["string"],
            "supporting_claims": [{"claim_text": "string", "claim_type": "factual|interpretation|risk|recent", "citation_ids": ["id"]}],
        },
        "instructions": ["Keep all required_claim_texts in direct_answer.", "No second-ticker comparison unless routed elsewhere."],
    },
}
_PREDICTION_MARKERS = ("price target", "guaranteed", "will outperform", "will rise", "will fall", "forecast")
_GENERIC_BEGINNER_MARKERS = ("u.s.-listed etf", "u.s.-listed common stock")
_RAW_FIELD_NAME_PATTERN = re.compile(r"\b[a-z][a-z0-9]+(?:_[a-z0-9]+)+\b")
_FIELD_LABEL_OVERRIDES = {
    "premium_discount_or_spread": "premium/discount spread data",
    "summary_prospectus": "summary prospectus",
    "provider_profile_overview": "provider profile overview",
    "provider_quote_stats": "provider quote statistics",
    "provider_price_chart": "provider price chart",
    "latest_revenue_fact": "latest revenue fact",
    "latest_net_income_fact": "latest net income fact",
    "latest_assets_fact": "latest assets fact",
}
_ENV_KEY = "OPENROUTER" + "_API_KEY"
_DETERMINISTIC_SUMMARY_GENERATION = ContextVar("deterministic_summary_generation", default=False)
_SUMMARY_GENERATION_DIAGNOSTICS = ContextVar("summary_generation_diagnostics", default=None)
_SUMMARY_GENERATION_CACHE_LOCK = RLock()
_SUMMARY_GENERATION_CACHE: dict[str, "_SummaryGenerationCacheEntry"] = {}
_LIVE_GENERATION_CIRCUIT_LOCK = RLock()
_LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS = 0.0
_LIVE_GENERATION_CIRCUIT_REASON: str | None = None


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
    diagnostics: GenerationDiagnostics = field(default_factory=GenerationDiagnostics)


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
        generation_evidence_pack: dict[str, Any] | None = None,
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
        generation_evidence_pack: dict[str, Any] | None = None,
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
        generation_evidence_pack: dict[str, Any] | None = None,
    ) -> list[RiskItem]:
        ...

    def generate_market_ai_comprehensive_analysis(
        self,
        *,
        focus: MarketNewsFocusResponse,
        minimum_market_news_item_count: int,
        minimum_topic_bucket_count: int,
        generation_evidence_pack: dict[str, Any] | None = None,
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
        generation_evidence_pack: dict[str, Any] | None = None,
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
        generation_evidence_pack: dict[str, Any] | None = None,
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
        live_call_timeout_seconds: int = DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS,
        live_failure_cooldown_seconds: int = DEFAULT_LIVE_FAILURE_COOLDOWN_SECONDS,
        live_slow_response_threshold_seconds: int = DEFAULT_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS,
    ) -> None:
        self.runtime = runtime or build_llm_runtime_config()
        self.structured_generator = structured_generator
        self.live_task_allowlist = None if live_task_allowlist is None else frozenset(live_task_allowlist)
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))
        self.live_call_timeout_seconds = max(1, int(live_call_timeout_seconds))
        self.live_failure_cooldown_seconds = max(0, int(live_failure_cooldown_seconds))
        self.live_slow_response_threshold_seconds = max(0, int(live_slow_response_threshold_seconds))

    def generate_beginner_summary(
        self,
        *,
        asset: AssetIdentity,
        base_summary: BeginnerSummary,
        citation_ids: list[str],
        evidence_notes: list[str] | None = None,
        generation_evidence_pack: dict[str, Any] | None = None,
    ) -> BeginnerSummary:
        evidence_pack = _generation_evidence_pack(generation_evidence_pack, asset_ticker=asset.ticker)
        request = SummaryGenerationRequest(
            task_name="beginner_summary",
            schema_version=BEGINNER_SUMMARY_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "base_summary": base_summary.model_dump(mode="json"),
                "citation_ids": sorted(set(citation_ids)),
                "evidence_notes": evidence_notes or [],
                "generation_evidence_pack": evidence_pack,
            },
        )
        fallback = _beginner_fallback_payload(asset, base_summary, evidence_notes or [], evidence_pack)
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
            generation_evidence_pack=evidence_pack,
            copy_quality_task="beginner_summary",
        )
        _validate_supporting_claims(payload, evidence_pack, output_text=" ".join(summary.model_dump().values()), required=generated.cacheable)
        record_summary_generation_diagnostics(request.task_name, generated.diagnostics)
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
        generation_evidence_pack: dict[str, Any] | None = None,
    ) -> str | None:
        if not base_summary:
            return base_summary
        evidence_pack = _generation_evidence_pack(generation_evidence_pack, asset_ticker=asset.ticker)
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
                "generation_evidence_pack": evidence_pack,
            },
        )
        fallback = {"summary": _deep_dive_fallback(asset, section_id, title, base_summary, evidence_state, evidence_notes or [])}
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        summary = _required_text(payload, "summary")
        _validate_text_blob(
            summary,
            weekly_news_rules_valid=True,
            generation_evidence_pack=evidence_pack,
            copy_quality_task="deep_dive_summary",
        )
        _validate_supporting_claims(payload, evidence_pack, output_text=summary, required=generated.cacheable)
        record_summary_generation_diagnostics(request.task_name, generated.diagnostics)
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
        generation_evidence_pack: dict[str, Any] | None = None,
    ) -> list[RiskItem]:
        if len(fallback_risks) != 3:
            raise SummaryGenerationContractError("Top risk fallback must contain exactly three risks.")
        allowed = set(allowed_citation_ids)
        evidence_pack = _generation_evidence_pack(generation_evidence_pack, asset_ticker=asset.ticker)
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
                "generation_evidence_pack": evidence_pack,
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
        risks_text = " ".join([risk.title + " " + risk.plain_english_explanation for risk in risks])
        _validate_text_blob(risks_text, generation_evidence_pack=evidence_pack)
        _validate_supporting_claims(payload, evidence_pack, output_text=risks_text, required=generated.cacheable)
        record_summary_generation_diagnostics(request.task_name, generated.diagnostics)
        self._remember_valid_payload(generated)
        return risks

    def generate_market_ai_comprehensive_analysis(
        self,
        *,
        focus: MarketNewsFocusResponse,
        minimum_market_news_item_count: int,
        minimum_topic_bucket_count: int,
        generation_evidence_pack: dict[str, Any] | None = None,
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
                generation_diagnostics=GenerationDiagnostics(
                    attempted_live=False,
                    used_fallback=True,
                    fallback_reason_codes=["insufficient_market_news_evidence"],
                ),
            )

        all_citations = sorted({citation_id for item in focus.items for citation_id in item.citation_ids})
        source_ids = sorted({source.source_document_id for source in focus.source_documents})
        story_ids = [item.story_id for item in focus.items]
        evidence_pack = _generation_evidence_pack(generation_evidence_pack, asset_ticker="MARKET", scope="market")
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
                "generation_evidence_pack": evidence_pack,
            },
        )
        fallback = {"sections": _market_ai_fallback_sections(focus, all_citations, evidence_pack)}
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        sections = _market_sections_from_payload(
            payload,
            allowed_citations=set(all_citations),
            selected_titles=[item.title for item in focus.items],
            generation_evidence_pack=evidence_pack,
            require_supporting_claims=generated.cacheable,
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
            no_live_external_calls=not generated.diagnostics.attempted_live,
            generation_diagnostics=generated.diagnostics,
        )
        _validate_text_blob(
            " ".join([section.analysis for section in sections] + [bullet for section in sections for bullet in section.bullets]),
            weekly_news_rules_valid=True,
            generation_evidence_pack=evidence_pack,
            copy_quality_task="market_ai_comprehensive_analysis",
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
        generation_evidence_pack: dict[str, Any] | None = None,
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
        weekly_items = [
            {
                "event_id": item.event_id,
                "event_type": item.event_type.value,
                "title": item.title,
                "summary": item.summary,
                "publisher": item.source.publisher,
                "source_quality": item.source.source_quality.value,
                "source_type": item.source.source_type,
                "is_official": item.source.is_official,
                "citation_ids": item.citation_ids,
                "importance_score": item.importance_score,
            }
            for item in weekly_news_focus.items
        ]
        evidence_pack = _generation_evidence_pack(generation_evidence_pack, asset_ticker=asset.ticker, scope="ticker")
        request = SummaryGenerationRequest(
            task_name="ticker_ai_comprehensive_analysis",
            schema_version=TICKER_AI_ANALYSIS_SCHEMA_VERSION,
            asset_ticker=asset.ticker,
            payload={
                "asset": asset.model_dump(mode="json"),
                "weekly_news_event_ids": event_ids,
                "weekly_news_items": weekly_items,
                "weekly_citation_ids": weekly_citations,
                "canonical_fact_citation_ids": canonical_fact_citation_ids,
                "allowed_citation_ids": all_citations,
                "required_section_order": [section_id for section_id, _label in _TICKER_AI_SECTION_ORDER],
                "analysis_style": [
                    "Synthesize patterns across the evidence instead of repeating headlines.",
                    "Explain what the evidence changes, what it does not change, and what a beginner can check next.",
                    "Keep recent news separate from stable asset identity.",
                ],
                "generation_evidence_pack": evidence_pack,
            },
        )
        fallback = {"sections": _ticker_ai_fallback_sections(asset, weekly_news_focus, all_citations, weekly_citations, asset_kind, evidence_pack)}
        generated = self._payload_or_fallback(request, fallback)
        payload = generated.payload
        sections = _sections_from_payload(
            payload,
            allowed_citations=set(all_citations),
            selected_titles=[item.title for item in weekly_news_focus.items],
            generation_evidence_pack=evidence_pack,
            require_supporting_claims=generated.cacheable,
        )
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
            no_live_external_calls=not generated.diagnostics.attempted_live,
            generation_diagnostics=generated.diagnostics,
        )
        _validate_text_blob(
            " ".join([section.analysis for section in sections] + [bullet for section in sections for bullet in section.bullets]),
            weekly_news_rules_valid=weekly_news_selected_item_count >= minimum_weekly_news_item_count,
            generation_evidence_pack=evidence_pack,
            copy_quality_task="ticker_ai_comprehensive_analysis",
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
        generation_evidence_pack: dict[str, Any] | None = None,
    ) -> GeneratedChatAnswer:
        evidence_pack = _generation_evidence_pack(generation_evidence_pack, asset_ticker=asset.ticker, scope="chat")
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
                "generation_evidence_pack": evidence_pack,
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
        answer_text = f"{answer.direct_answer} {answer.why_it_matters} {' '.join(answer.uncertainty)}"
        _validate_text_blob(answer_text, generation_evidence_pack=evidence_pack)
        _validate_supporting_claims(payload, evidence_pack, output_text=answer_text, required=generated.cacheable)
        for claim_text in required_claim_texts:
            if claim_text and claim_text not in answer.direct_answer:
                raise SummaryGenerationContractError("Generated chat answer omitted required citation-bound claim text.")
        self._remember_valid_payload(generated)
        return answer

    def _payload_or_fallback(self, request: SummaryGenerationRequest, fallback: dict[str, Any]) -> _GeneratedPayload:
        live_ready = self.runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call
        model_name = _active_generation_model_name(self.runtime)
        if (
            live_ready
            and self.structured_generator
            and self._live_allowed_for_task(request.task_name)
        ):
            cache_key = _summary_generation_cache_key(request, self.runtime)
            cached = _summary_generation_cache_get(cache_key, ttl_seconds=self.cache_ttl_seconds)
            if cached is not None:
                return _GeneratedPayload(
                    payload=cached,
                    diagnostics=GenerationDiagnostics(
                        attempted_live=True,
                        used_fallback=False,
                        model_name=model_name,
                    ),
                )
            circuit_reason = _live_generation_circuit_reason()
            if circuit_reason:
                return _GeneratedPayload(
                    payload=fallback,
                    diagnostics=GenerationDiagnostics(
                        attempted_live=False,
                        used_fallback=True,
                        fallback_reason_codes=["live_generation_circuit_open", circuit_reason],
                        model_name=model_name,
                    ),
                )
            try:
                started_seconds = time.monotonic()
                payload = _call_structured_generator_with_deadline(
                    self.structured_generator,
                    request,
                    timeout_seconds=self.live_call_timeout_seconds,
                )
                elapsed_seconds = time.monotonic() - started_seconds
                if isinstance(payload, dict):
                    payload = _normalize_live_payload_shape(request, payload)
                    if (
                        self.live_slow_response_threshold_seconds > 0
                        and elapsed_seconds >= self.live_slow_response_threshold_seconds
                    ):
                        _open_live_generation_circuit(
                            "live_generation_slow_response",
                            cooldown_seconds=self.live_failure_cooldown_seconds,
                        )
                    return _GeneratedPayload(
                        payload=payload,
                        cache_key=cache_key,
                        cacheable=True,
                        diagnostics=GenerationDiagnostics(
                            attempted_live=True,
                            used_fallback=False,
                            model_name=model_name,
                        ),
                    )
                raise SummaryGenerationContractError("Structured summary generator returned a non-object payload.")
            except TimeoutError:
                _open_live_generation_circuit(
                    "live_generation_timeout",
                    cooldown_seconds=self.live_failure_cooldown_seconds,
                )
                return _GeneratedPayload(
                    payload=fallback,
                    diagnostics=GenerationDiagnostics(
                        attempted_live=True,
                        used_fallback=True,
                        fallback_reason_codes=["live_generation_timeout"],
                        model_name=model_name,
                    ),
                )
        return _GeneratedPayload(
            payload=fallback,
            diagnostics=GenerationDiagnostics(
                attempted_live=False,
                used_fallback=True,
                fallback_reason_codes=[self._fallback_reason_for_task(request.task_name, live_ready=live_ready)],
                model_name=model_name if live_ready else None,
            ),
        )

    def _remember_valid_payload(self, generated: _GeneratedPayload) -> None:
        if generated.cacheable and generated.cache_key and self.cache_ttl_seconds > 0:
            _summary_generation_cache_set(generated.cache_key, generated.payload)

    def _live_allowed_for_task(self, task_name: str) -> bool:
        if self.live_task_allowlist is None:
            return True
        return task_name in self.live_task_allowlist

    def _fallback_reason_for_task(self, task_name: str, *, live_ready: bool) -> str:
        if _DETERMINISTIC_SUMMARY_GENERATION.get():
            return "deterministic_summary_generation"
        if not live_ready:
            return f"live_generation_not_ready:{self.runtime.readiness_status.value}"
        if self.structured_generator is None:
            return "live_generator_unavailable"
        if not self._live_allowed_for_task(task_name):
            return "task_not_allowlisted_for_live_generation"
        return "deterministic_fallback"


@contextmanager
def deterministic_summary_generation():
    token = _DETERMINISTIC_SUMMARY_GENERATION.set(True)
    try:
        yield
    finally:
        _DETERMINISTIC_SUMMARY_GENERATION.reset(token)


def start_summary_generation_diagnostics_capture():
    return _SUMMARY_GENERATION_DIAGNOSTICS.set({})


def stop_summary_generation_diagnostics_capture(token: Any) -> None:
    _SUMMARY_GENERATION_DIAGNOSTICS.reset(token)


def current_summary_generation_diagnostics() -> dict[str, GenerationDiagnostics]:
    diagnostics = _SUMMARY_GENERATION_DIAGNOSTICS.get()
    if not isinstance(diagnostics, dict):
        return {}
    return dict(diagnostics)


def record_summary_generation_diagnostics(task_name: str, diagnostics: GenerationDiagnostics) -> None:
    captured = _SUMMARY_GENERATION_DIAGNOSTICS.get()
    if isinstance(captured, dict):
        captured[task_name] = diagnostics


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
        live_call_timeout_seconds=timeout_seconds,
        live_failure_cooldown_seconds=_live_failure_cooldown_seconds_from_env(env),
        live_slow_response_threshold_seconds=_live_slow_response_threshold_seconds_from_env(env),
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


def live_summary_generation_ready_from_env(env: Mapping[str, str] | None = None) -> bool:
    values = dict(os.environ if env is None else env)
    if values.get("CI") or values.get("PYTEST_CURRENT_TEST"):
        return False
    return _runtime_from_env(values).readiness_status is LlmReadinessStatus.ready_for_explicit_live_call


def summary_generation_diagnostics(
    service: Any | None,
    *,
    task_name: str,
    used_fallback: bool,
    fallback_reason_codes: Iterable[str] | None = None,
    attempted_live: bool | None = None,
) -> GenerationDiagnostics:
    runtime = getattr(service, "runtime", None)
    live_ready = isinstance(runtime, LlmRuntimeConfig) and runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call
    generator_available = bool(getattr(service, "structured_generator", None))
    allowlist = getattr(service, "live_task_allowlist", DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST)
    if attempted_live is None:
        attempted_live = bool(live_ready and generator_available and (allowlist is None or task_name in allowlist))
    return GenerationDiagnostics(
        attempted_live=attempted_live,
        used_fallback=used_fallback,
        fallback_reason_codes=list(fallback_reason_codes or []),
        model_name=_active_generation_model_name(runtime) if isinstance(runtime, LlmRuntimeConfig) else None,
    )


def summary_generation_reason_codes(exc: Exception) -> list[str]:
    message = str(exc).lower()
    codes: list[str] = []
    if "schema" in message or "wrong section" in message or "sections array" in message or "required text" in message:
        codes.append("schema_validation_failed")
    if "citation" in message or "supporting claim" in message:
        codes.append("citation_validation_failed")
    if "numeric" in message:
        codes.append("numeric_validation_failed")
    if "headline" in message:
        codes.append("headline_repetition_validation_failed")
    if "safety" in message or "advice" in message or "prediction" in message:
        codes.append("safety_validation_failed")
    if "internal wording" in message or "copy" in message:
        codes.append("copy_quality_validation_failed")
    return codes or ["summary_generation_validation_failed"]


def _live_env_allowed(env: Mapping[str, str], runtime: LlmRuntimeConfig) -> bool:
    if env.get("CI") or env.get("PYTEST_CURRENT_TEST"):
        return False
    return runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call


def _live_task_allowlist_from_env(env: Mapping[str, str]) -> frozenset[str] | None:
    raw = str(env.get(LLM_LIVE_TASK_ALLOWLIST_ENV, "")).strip()
    if not raw:
        return DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST
    tokens = {token.strip().lower() for token in raw.split(",") if token.strip()}
    if not tokens:
        return DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST
    if "all" in tokens or "*" in tokens:
        return None
    if "none" in tokens or "off" in tokens or "false" in tokens:
        return frozenset()
    return frozenset(tokens)


def _active_generation_model_name(runtime: LlmRuntimeConfig | None) -> str | None:
    if runtime is None or not runtime.configured_model_chain:
        return None
    return runtime.configured_model_chain[0].model_name


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


def _live_failure_cooldown_seconds_from_env(env: Mapping[str, str]) -> int:
    raw = str(env.get(LLM_LIVE_FAILURE_COOLDOWN_SECONDS_ENV, "")).strip()
    if not raw:
        return DEFAULT_LIVE_FAILURE_COOLDOWN_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_LIVE_FAILURE_COOLDOWN_SECONDS


def _live_slow_response_threshold_seconds_from_env(env: Mapping[str, str]) -> int:
    raw = str(env.get(LLM_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS_ENV, "")).strip()
    if not raw:
        return DEFAULT_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS


def clear_summary_generation_cache() -> None:
    with _SUMMARY_GENERATION_CACHE_LOCK:
        _SUMMARY_GENERATION_CACHE.clear()


def clear_summary_generation_live_circuit() -> None:
    global _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS, _LIVE_GENERATION_CIRCUIT_REASON
    with _LIVE_GENERATION_CIRCUIT_LOCK:
        _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS = 0.0
        _LIVE_GENERATION_CIRCUIT_REASON = None


def _call_structured_generator_with_deadline(
    generator: StructuredSummaryGenerator,
    request: SummaryGenerationRequest,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ltt-live-summary")
    future = executor.submit(generator, request)
    try:
        payload = future.result(timeout=max(1, int(timeout_seconds)))
    except FutureTimeoutError as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError("live_summary_generation_timeout") from exc
    except Exception:
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    executor.shutdown(wait=True, cancel_futures=True)
    return payload


def _live_generation_circuit_reason() -> str | None:
    global _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS, _LIVE_GENERATION_CIRCUIT_REASON
    with _LIVE_GENERATION_CIRCUIT_LOCK:
        if _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS <= time.monotonic():
            _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS = 0.0
            _LIVE_GENERATION_CIRCUIT_REASON = None
            return None
        return _LIVE_GENERATION_CIRCUIT_REASON or "live_generation_recent_failure"


def _open_live_generation_circuit(reason: str, *, cooldown_seconds: int) -> None:
    global _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS, _LIVE_GENERATION_CIRCUIT_REASON
    if cooldown_seconds <= 0:
        return
    with _LIVE_GENERATION_CIRCUIT_LOCK:
        _LIVE_GENERATION_CIRCUIT_OPEN_UNTIL_SECONDS = time.monotonic() + cooldown_seconds
        _LIVE_GENERATION_CIRCUIT_REASON = reason


def _summary_generation_cache_key(request: SummaryGenerationRequest, runtime: LlmRuntimeConfig) -> str:
    model_names = [
        str(getattr(model, "model_name", model))
        for model in getattr(runtime, "configured_model_chain", [])
    ]
    raw = json.dumps(
        {
            "asset_ticker": request.asset_ticker,
            "generation_context_schema_version": GENERATION_CONTEXT_SCHEMA_VERSION,
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
                            "Return compact JSON only. Act as Learn the Ticker's evidence-bound educational "
                            "analysis layer: use only the supplied generation evidence pack, curated generation "
                            "context, citation ids, allowed numeric facts, selected news, macro data, and compact technical context. "
                            "Do not include recommendations, predictions, raw reasoning, hidden prompts, raw "
                            "transcripts, raw OHLCV series, raw provider payloads, raw provider key names, article bodies, "
                            "or internal pipeline wording. If evidence is missing, label the limitation in the requested JSON fields."
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
        return _normalize_live_payload_shape(request, payload)

    return generator


def _normalize_live_payload_shape(request: SummaryGenerationRequest, payload: dict[str, Any]) -> dict[str, Any]:
    if _payload_matches_task_shape(request.task_name, payload):
        return payload
    for wrapper_key in ("payload", "output", "result", "data"):
        wrapped = payload.get(wrapper_key)
        if isinstance(wrapped, dict) and _payload_matches_task_shape(request.task_name, wrapped):
            return wrapped
    return payload


def _payload_matches_task_shape(task_name: str, payload: dict[str, Any]) -> bool:
    if task_name in {"market_ai_comprehensive_analysis", "ticker_ai_comprehensive_analysis"}:
        return isinstance(payload.get("sections"), list)
    if task_name == "beginner_summary":
        return all(isinstance(payload.get(key), str) for key in ("what_it_is", "why_people_consider_it", "main_catch"))
    if task_name == "deep_dive_summary":
        return isinstance(payload.get("summary"), str)
    if task_name == "top_3_risks":
        return isinstance(payload.get("risks"), list)
    if task_name == "grounded_chat_answer":
        return all(isinstance(payload.get(key), str) for key in ("direct_answer", "why_it_matters"))
    return True


def _safe_prompt_payload(request: SummaryGenerationRequest) -> dict[str, Any]:
    return {
        "task_name": request.task_name,
        "schema_version": request.schema_version,
        "asset_ticker": request.asset_ticker,
        "prompt_version": SUMMARY_GENERATION_PROMPT_VERSION,
        "task_prompt_spec": _TASK_PROMPT_SPECS.get(request.task_name, {}),
        "output_rules": [
            "Return only JSON matching the task schema.",
            "Use only supplied evidence and citation ids.",
            "Every factual section, risk, or summary must include citation_ids from the allowed set.",
            "Every live-generated factual output must include supporting_claims that cite the exact evidence ids used.",
            "Every explicit numeric claim must match allowed_numeric_facts in the generation evidence pack.",
            "Avoid buy/sell/hold, allocation, price-target, prediction, tax, and brokerage advice.",
            "Separate timely news context from stable canonical facts.",
            "Use a more analytical plain-English style: connect facts, news, macro, and technical context without forecasting.",
            "Include uncertainty when evidence is partial or missing.",
            "Use generation_context for clean asset/profile/exposure framing and generation_evidence_pack for citations and validation.",
            "Do not use internal wording such as fixture, local MVP, available evidence, provider market-reference, raw provider keys, or this section uses.",
            "Beginner Summary must explain the asset and must not use raw quote, chart, price, volume, or technical indicators as its main evidence.",
            "Market AI must synthesize selected stories with Economic Indicators and allowed numeric facts; do not merely count buckets or repeat headlines.",
            "Return the task output as the JSON root object; do not wrap it inside payload, data, output, result, markdown, or prose.",
            "For AI analysis sections, include every required section exactly once in the provided order.",
        ],
        "payload": request.payload,
    }


def _beginner_fallback_payload(
    asset: AssetIdentity,
    base_summary: BeginnerSummary,
    evidence_notes: list[str],
    generation_evidence_pack: dict[str, Any] | None = None,
) -> dict[str, str]:
    notes = _evidence_note_map(evidence_notes)
    context = generation_pack_generation_context(generation_evidence_pack)
    asset_profile = _context_dict(context, "asset_profile")
    identity_context = _context_dict(context, "identity_context")
    exposure_context = _context_dict(context, "exposure_context")
    evidence_limits = _context_dict(context, "evidence_limits")
    benchmark = _first_text(identity_context.get("benchmark"), notes.get("benchmark"))
    holdings = _first_text(exposure_context.get("holdings_count"), notes.get("holdings_count"))
    expense = _first_text(identity_context.get("expense_ratio"), notes.get("expense_ratio"))
    fund_family = _first_text(asset_profile.get("fund_family"), identity_context.get("issuer"), getattr(asset, "issuer", None))
    category = _first_text(asset_profile.get("category"))
    fund_summary = _first_text(asset_profile.get("fund_summary"))
    sector = _first_text(asset_profile.get("sector"), _profile_note_value(notes.get("provider_profile_overview"), "sector"))
    industry = _first_text(asset_profile.get("industry"), _profile_note_value(notes.get("provider_profile_overview"), "industry"))
    business_summary = _first_text(asset_profile.get("business_summary"))
    gaps = _humanize_field_list(notes.get("evidence_gaps"))
    if asset.asset_type.value == "etf":
        holdings_phrase = f"{holdings} holdings" if holdings else ""
        cost_phrase = f"an expense ratio of {expense}" if expense else ""
        fact_bits = _join_human_text(
            [
                f"tracks {benchmark}" if benchmark else "",
                holdings_phrase,
                cost_phrase,
                f"is categorized as {category}" if category else "",
            ]
        )
        issuer_phrase = f" from {fund_family}" if fund_family else ""
        what_it_is = (
            f"{asset.name} ({asset.ticker}) is an ETF{issuer_phrase}"
            + (f" that {fact_bits}." if fact_bits else ".")
            if fact_bits
            else _join_sentences(base_summary.what_it_is, _truncate(fund_summary, 180) if fund_summary else "")
        )
        why = (
            f"Beginners can use {asset.ticker} to study how a fund's benchmark, holdings breadth"
            + (", category" if category else "")
            + (", and cost" if expense else "")
            + " shape exposure in one ticker."
        )
        catch = (
            "The main catch is that ETF facts are point-in-time and missing fields stay labeled"
            + (
                f" ({gaps or _humanize_field_list(evidence_limits.get('missing_fields', [])[:3])})"
                if (gaps or evidence_limits.get("missing_fields"))
                else ""
            )
            + "; this page does not turn the fund into a personal recommendation."
        )
    else:
        business_phrase = _truncate(business_summary, 220) if business_summary else ""
        sector_phrase = _join_human_text([sector or "", industry or ""])
        official_fact_phrase = (
            " using SEC-filed facts"
            if notes.get("latest_revenue_fact") or notes.get("latest_net_income_fact")
            else ""
        )
        fact_bits = _join_human_text(
            [
                f"in {sector_phrase}" if sector_phrase else "",
                business_phrase,
            ]
        )
        what_it_is = (
            f"{asset.name} ({asset.ticker}) is a single-company stock{official_fact_phrase}"
            + (f" {fact_bits}." if fact_bits else ".")
            if fact_bits
            else _join_sentences(base_summary.what_it_is, "SEC facts are preferred when available.")
        )
        why = (
            f"Beginners can use {asset.ticker} to connect what the company does with reported financial facts, business context, and clearly labeled valuation context."
            if fact_bits
            else base_summary.why_people_consider_it
        )
        catch = (
            "The main catch is single-company risk: business, financial, and valuation evidence can change, and context fields do not prove whether the stock is cheap or expensive."
        )
    return {
        "what_it_is": _avoid_generic_only(what_it_is, base_summary.what_it_is),
        "why_people_consider_it": _avoid_generic_only(why, base_summary.why_people_consider_it),
        "main_catch": catch,
    }


def _deep_dive_fallback(
    asset: AssetIdentity,
    section_id: str,
    title: str,
    base_summary: str,
    evidence_state: str,
    evidence_notes: list[str],
) -> str:
    notes = _evidence_note_map(evidence_notes)
    fields = [
        _humanize_public_text(value)
        for key, value in notes.items()
        if key not in {
            "fetch_state",
            "source_count",
            "fact_count",
            "section_id",
            "evidence_state",
            "limitations",
            "provider_market_price",
            "provider_quote_stats",
            "provider_price_chart",
        }
    ][:4]
    field_text = _join_human_text(fields)
    if section_id != "evidence_limits" and not field_text:
        return base_summary
    if field_text:
        if section_id != "evidence_limits":
            return _join_sentences(
                base_summary,
                (
                    f"For {asset.ticker}, these details matter because they connect the section to the "
                    "asset's business or fund structure while keeping partial fields labeled."
                ),
            )
        return _join_sentences(
            base_summary,
            (
                f"For {asset.ticker}, the useful beginner takeaway is {field_text}. "
                "Missing or partial details stay labeled instead of becoming conclusions."
            ),
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
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    context = generation_pack_generation_context(generation_evidence_pack)
    profile_phrase = _asset_profile_phrase(asset, context)
    exposure_phrase = _exposure_context_phrase(context)
    market_phrase = _market_context_phrase(context)
    event_mix = _weekly_event_mix(weekly_news_focus)
    source_mix = _weekly_source_mix(weekly_news_focus)
    item_count = len(weekly_news_focus.items)
    change_anchor = (
        f"{item_count} approved ticker-specific item{'' if item_count == 1 else 's'} covering {event_mix}"
        if event_mix
        else f"{item_count} approved ticker-specific Weekly News Focus item{'' if item_count == 1 else 's'}"
    )
    market_lens = (
        "For a fund, the useful market lens is whether the items relate to flows, fees, index rules, holdings, or sponsor updates."
        if asset.asset_type.value == "etf"
        else "For a stock, the useful market lens is whether the items relate to demand, products, customers, regulation, or reported results."
    )
    business_lens = (
        "fund construction, benchmark exposure, costs, and holdings evidence"
        if asset_kind == "fund"
        else "the company's products, customers, financial profile, and filing-backed business description"
    )
    return [
        {
            "section_id": "what_changed_this_week",
            "label": "What Changed This Week",
            "analysis": (
                f"For {asset.ticker}, the change to study this week is the pattern across {change_anchor}. "
                f"The source mix is {source_mix}, so this is timely context rather than a new definition of the asset."
            ),
            "bullets": [
                "Use the cited set to identify what new evidence appeared, then compare it with the stable asset facts."
            ],
            "citation_ids": weekly_citations,
            "uncertainty": ["Relevant items may be absent when they did not pass the Weekly News Focus evidence rules."],
        },
        {
            "section_id": "market_context",
            "label": "Market Context",
            "analysis": (
                f"{market_lens} {market_phrase} The cited weekly evidence can explain why {asset.ticker} is being discussed now, "
                "but it does not prove a broad market trend or a future outcome."
            ),
            "bullets": ["Recent context remains separate from canonical identity, holdings, business, and risk facts."],
            "citation_ids": weekly_citations,
            "uncertainty": [],
        },
        {
            "section_id": "business_or_fund_context",
            "label": "Business/Fund Context",
            "analysis": (
                f"For this {asset_kind}, the beginner question is how the weekly evidence connects to {business_lens}. "
                f"{profile_phrase}{exposure_phrase} "
                "The useful lesson is the relationship between current events and durable facts, not the headline by itself."
            ),
            "bullets": ["Canonical facts and Weekly News Focus use separate citation sets."],
            "citation_ids": all_citations,
            "uncertainty": [],
        },
        {
            "section_id": "risk_context",
            "label": "Risk Context",
            "analysis": (
                f"The risk lens is to separate what the cited items newly highlight from what remains unchanged about {asset.ticker}. "
                "Useful watchpoints are confirmation from later approved sources, whether the item affects core facts, and whether the evidence is only metadata-level."
            ),
            "bullets": ["Do not infer returns, suitability, or trading actions from this cited news set."],
            "citation_ids": weekly_citations,
            "uncertainty": ["Risk context is limited to cited weekly-news evidence and canonical facts."],
        },
    ]


def _weekly_event_mix(weekly_news_focus: WeeklyNewsFocusResponse) -> str:
    labels: list[str] = []
    for item in weekly_news_focus.items:
        label = item.event_type.value.replace("_", " ")
        if label not in labels:
            labels.append(label)
    return _join_human_text(labels[:4])


def _weekly_source_mix(weekly_news_focus: WeeklyNewsFocusResponse) -> str:
    official_count = sum(1 for item in weekly_news_focus.items if item.source.is_official)
    third_party_count = len(weekly_news_focus.items) - official_count
    parts: list[str] = []
    if official_count:
        parts.append(f"{official_count} official item{'' if official_count == 1 else 's'}")
    if third_party_count:
        parts.append(f"{third_party_count} source-labeled third-party or provider item{'' if third_party_count == 1 else 's'}")
    return _join_human_text(parts) or "source-labeled weekly evidence"


def _market_ai_fallback_sections(
    focus: MarketNewsFocusResponse,
    all_citations: list[str],
    generation_evidence_pack: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    context = generation_pack_generation_context(generation_evidence_pack)
    macro_phrase = _market_context_phrase(context)
    bucket_titles = {
        bucket: [item.title for item in focus.items if item.topic_bucket is bucket]
        for bucket in MarketNewsTopicBucket
    }

    def bucket_text(bucket: MarketNewsTopicBucket, label: str) -> str:
        titles = bucket_titles.get(bucket) or []
        if titles:
            examples = _join_human_text([_short_headline_hint(title) for title in titles[:2]])
            return (
                f"The cited {label} stories point to {examples or 'a shared market theme'}. "
                "Beginners can compare that theme with later approved updates instead of treating any one headline as the whole story."
            )
        return f"No selected {label} item passed strongly enough to anchor a standalone claim, so this section stays limited to the broader cited set."

    return [
        {
            "section_id": "what_changed_this_week",
            "label": "What Changed This Week",
            "analysis": (
                "The useful change this week is the mix of policy, equity, technology, geopolitical, and credit signals in the approved market window. "
                f"{macro_phrase}"
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


def _sections_from_payload(
    payload: dict[str, Any],
    *,
    allowed_citations: set[str],
    selected_titles: list[str] | None = None,
    generation_evidence_pack: dict[str, Any] | None = None,
    require_supporting_claims: bool = False,
) -> list[AIComprehensiveAnalysisSection]:
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
        analysis = _required_text(raw, "analysis")
        _reject_headline_repetition(analysis, selected_titles or [])
        _validate_supporting_claims(raw, generation_evidence_pack, output_text=analysis, required=require_supporting_claims)
        sections.append(
            AIComprehensiveAnalysisSection(
                section_id=expected_id,  # type: ignore[arg-type]
                label=expected_label,  # type: ignore[arg-type]
                analysis=analysis,
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
    generation_evidence_pack: dict[str, Any] | None = None,
    require_supporting_claims: bool = False,
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
        _validate_supporting_claims(raw, generation_evidence_pack, output_text=" ".join([analysis, *bullets]), required=require_supporting_claims)
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


def _generation_evidence_pack(
    pack: dict[str, Any] | None,
    *,
    asset_ticker: str,
    scope: str = "asset",
) -> dict[str, Any]:
    if isinstance(pack, dict) and pack.get("schema_version") == GENERATION_EVIDENCE_PACK_SCHEMA_VERSION:
        return pack
    return empty_generation_evidence_pack(asset_ticker=asset_ticker, scope=scope)


def _validate_supporting_claims(
    payload: dict[str, Any],
    generation_evidence_pack: dict[str, Any] | None,
    *,
    output_text: str,
    required: bool,
) -> None:
    if not required:
        return
    supporting_claims = _collect_supporting_claims(payload)
    if not supporting_claims:
        raise SummaryGenerationContractError("Live generated output requires supporting_claims.")
    evidence = generation_pack_citation_evidence(generation_evidence_pack)
    if not evidence:
        raise SummaryGenerationContractError("Live generated output requires citation evidence.")
    claims = [
        CitationValidationClaim(
            claim_id=f"generated_supporting_claim_{index}",
            claim_text=_required_text(claim, "claim_text"),
            claim_type=str(claim.get("claim_type") or "factual"),
            citation_ids=[str(item) for item in claim.get("citation_ids", [])],
        )
        for index, claim in enumerate(supporting_claims, start=1)
        if isinstance(claim, dict)
    ]
    if len(claims) != len(supporting_claims):
        raise SummaryGenerationContractError("supporting_claims must be objects.")
    allowed_assets = generation_pack_allowed_asset_tickers(
        generation_evidence_pack,
        fallback=str((generation_evidence_pack or {}).get("asset_ticker") or "MARKET"),
    )
    validation = validate_llm_generated_output(
        output_text=output_text,
        schema_valid=True,
        claims=claims,
        evidence=evidence,
        citation_context=CitationValidationContext(allowed_asset_tickers=allowed_assets),
    )
    if not validation.valid:
        raise SummaryGenerationContractError(f"Generated supporting claims failed validation: {validation.status.value}")


def _collect_supporting_claims(value: Any) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        raw = value.get("supporting_claims")
        if isinstance(raw, list):
            claims.extend(item for item in raw if isinstance(item, dict))
        for child in value.values():
            if child is not raw:
                claims.extend(_collect_supporting_claims(child))
    elif isinstance(value, list):
        for child in value:
            claims.extend(_collect_supporting_claims(child))
    return claims


def _validate_text_blob(
    text: str,
    *,
    weekly_news_rules_valid: bool = True,
    generation_evidence_pack: dict[str, Any] | None = None,
    copy_quality_task: str | None = None,
) -> None:
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
    if copy_quality_task:
        _validate_copy_quality(text, copy_quality_task)
    numeric_reason_codes = validate_generated_numeric_integrity(
        [text],
        generation_pack_allowed_numeric_facts(generation_evidence_pack),
    )
    if numeric_reason_codes:
        raise SummaryGenerationContractError(
            "Generated prose failed numeric validation: " + ", ".join(numeric_reason_codes)
        )


def _reject_headline_repetition(analysis: str, selected_titles: list[str]) -> None:
    normalized = _normalize(analysis)
    if not normalized:
        raise SummaryGenerationContractError("Generated analysis is empty.")
    matched_titles = [title for title in selected_titles if _normalize(title) and _normalize(title) in normalized]
    if len(matched_titles) >= 2 and len(normalized.split()) < sum(len(_normalize(title).split()) for title in matched_titles) + 24:
        raise SummaryGenerationContractError("Generated analysis only repeats selected headlines.")
    if normalized.startswith("the selected market news focus items are") or normalized.startswith("the selected weekly news focus items are"):
        raise SummaryGenerationContractError("Generated market analysis repeats headlines instead of synthesizing them.")


def _validate_copy_quality(text: str, task_name: str) -> None:
    normalized = _normalize(text)
    internal_markers = {
        "fixture",
        "local mvp",
        "local-mvp",
        "local test",
        "local-test",
        "available evidence",
        "provider market-reference",
        "regularmarketprice",
        "chartpreviousclose",
        "fetch pipeline",
        "this section uses",
    }
    for marker in internal_markers:
        if marker in normalized:
            raise SummaryGenerationContractError(f"Generated {task_name} copy includes internal wording: {marker}")
    if task_name in {
        "beginner_summary",
        "deep_dive_summary",
        "market_ai_comprehensive_analysis",
        "ticker_ai_comprehensive_analysis",
    }:
        raw_field_names = sorted({match.group(0) for match in _RAW_FIELD_NAME_PATTERN.finditer(text)})
        if raw_field_names:
            raise SummaryGenerationContractError(
                "Generated copy includes raw field names: " + ", ".join(raw_field_names[:5])
            )
    if task_name == "beginner_summary":
        quote_only_markers = ("provider market price", "provider quote", "quote field", "chart field", "raw price", "raw quote")
        if any(marker in normalized for marker in quote_only_markers):
            raise SummaryGenerationContractError("Beginner Summary cannot be based on chart or quote-only facts.")
    if task_name == "market_ai_comprehensive_analysis":
        low_value_markers = (
            "selected market news focus set spans",
            "topic bucket has",
            "bucket has",
            "approved items, including",
            "approved item, including",
        )
        if any(marker in normalized for marker in low_value_markers):
            raise SummaryGenerationContractError("Market AI analysis must synthesize evidence instead of counting buckets.")


def _short_headline_hint(title: str) -> str:
    words = [word.strip(" ,.;:!?") for word in str(title).split() if word.strip(" ,.;:!?")]
    return " ".join(words[:7])


def _humanize_field_name(value: str) -> str:
    text = str(value).strip()
    if not text:
        return ""
    return _FIELD_LABEL_OVERRIDES.get(text, text.replace("_", " "))


def _humanize_field_list(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        raw_items = [str(item).strip() for item in value if str(item).strip()]
    else:
        raw_items = [str(value).strip()]
    return _join_human_text([_humanize_field_name(item) for item in raw_items if item])


def _humanize_public_text(value: str) -> str:
    text = str(value)
    for raw in sorted(set(_RAW_FIELD_NAME_PATTERN.findall(text)), key=len, reverse=True):
        text = text.replace(raw, _humanize_field_name(raw))
    return text


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


def _context_dict(context: dict[str, Any], key: str) -> dict[str, Any]:
    value = context.get(key)
    return value if isinstance(value, dict) else {}


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value in (None, ""):
            continue
        text = " ".join(str(value).split())
        if text:
            return text
    return None


def _profile_note_value(note: str | None, field_name: str) -> str | None:
    if not note:
        return None
    marker = field_name + ":"
    lowered = note.lower()
    start = lowered.find(marker)
    if start < 0:
        return None
    raw = note[start + len(marker):].split(";", 1)[0].strip()
    return raw or None


def _asset_profile_phrase(asset: AssetIdentity, context: dict[str, Any]) -> str:
    profile = _context_dict(context, "asset_profile")
    if asset.asset_type.value == "etf":
        pieces = [
            f"Fund profile context identifies {profile.get('fund_family')} as the fund family" if profile.get("fund_family") else "",
            f"{profile.get('category')} as the category" if profile.get("category") else "",
        ]
        phrase = _join_human_text(pieces)
        return f"{phrase}." if phrase else ""
    pieces = [
        f"{profile.get('sector')} sector" if profile.get("sector") else "",
        f"{profile.get('industry')} industry" if profile.get("industry") else "",
    ]
    phrase = _join_human_text(pieces)
    return f"Profile context places {asset.ticker} in {phrase}." if phrase else ""


def _exposure_context_phrase(context: dict[str, Any]) -> str:
    exposure = _context_dict(context, "exposure_context")
    pieces = [
        f"{exposure.get('holdings_count')} holdings" if exposure.get("holdings_count") else "",
        str(exposure.get("concentration_signal") or ""),
    ]
    phrase = _join_human_text(pieces)
    return f" Exposure context highlights {phrase}." if phrase else ""


def _market_context_phrase(context: dict[str, Any]) -> str:
    market = _context_dict(context, "market_context")
    indicators = market.get("economic_indicators")
    if isinstance(indicators, list) and indicators:
        names = [
            str(item.get("name"))
            for item in indicators
            if isinstance(item, dict) and item.get("name")
        ][:4]
        if names:
            return "Economic Indicators in the context include " + _join_human_text(names) + "."
    topic_coverage = market.get("topic_coverage")
    if isinstance(topic_coverage, dict) and topic_coverage:
        labels = [key.replace("_", " ") for key in topic_coverage.keys()]
        return "The selected market context covers " + _join_human_text(labels[:4]) + "."
    return "Market context remains limited to the selected cited stories."


def _truncate(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


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
