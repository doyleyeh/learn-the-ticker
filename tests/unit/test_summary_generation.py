from pathlib import Path
from typing import Any

import pytest

import backend.summary_generation as summary_generation_module
from backend.chat import generate_chat_from_pack, validate_chat_response
from backend.llm import build_llm_runtime_config, default_openrouter_settings
from backend.llm import DEFAULT_OPENROUTER_FREE_MODEL_ORDER, DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL
from backend.market_news import fixture_market_news_candidates, select_market_news_focus
from backend.models import (
    BeginnerSummary,
    FreshnessState,
    RiskItem,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsEventType,
)
from backend.retrieval import build_asset_knowledge_pack
from backend.summary_generation import (
    CHAT_ANSWER_SCHEMA_VERSION,
    DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST,
    SUMMARY_GENERATION_BOUNDARY,
    SummaryGenerationContractError,
    HybridSummaryGenerationService,
    SummaryGenerationRequest,
    clear_summary_generation_cache,
    clear_summary_generation_live_circuit,
    _safe_prompt_payload,
)
from backend.weekly_news import (
    WeeklyNewsCandidate,
    build_ai_comprehensive_analysis,
    select_weekly_news_focus,
    validate_ai_comprehensive_analysis,
)


ROOT = Path(__file__).resolve().parents[2]


def test_default_hybrid_summary_service_generates_valid_ticker_ai_analysis_without_live_calls():
    pack = build_asset_knowledge_pack("QQQ")
    focus = _two_item_weekly_news_focus()
    service = HybridSummaryGenerationService()

    analysis = service.generate_ticker_ai_comprehensive_analysis(
        asset=pack.asset,
        weekly_news_focus=focus,
        canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
        minimum_weekly_news_item_count=2,
        weekly_news_selected_item_count=focus.selected_item_count,
    )

    assert analysis.analysis_available is True
    assert analysis.no_live_external_calls is True
    assert [section.label for section in analysis.sections] == [
        "What Changed This Week",
        "Market Context",
        "Business/Fund Context",
        "Risk Context",
    ]
    assert "c_fact_qqq_asset_identity" in analysis.citation_ids
    assert validate_ai_comprehensive_analysis(analysis, focus) == analysis
    assert all("fixture" not in section.analysis.lower() for section in analysis.sections)


def test_beginner_summary_fallback_uses_asset_specific_evidence_notes():
    service = HybridSummaryGenerationService()
    asset = build_asset_knowledge_pack("QQQ").asset

    summary = service.generate_beginner_summary(
        asset=asset,
        base_summary=BeginnerSummary(
            what_it_is="Invesco QQQ Trust (QQQ) is a U.S.-listed ETF.",
            why_people_consider_it="Beginners may study it.",
            main_catch="Issuer facts are point-in-time.",
        ),
        citation_ids=["c_fact_qqq_asset_identity"],
        evidence_notes=[
            "benchmark=Nasdaq-100 Index",
            "holdings_count=101",
            "expense_ratio=0.20",
            "provider_market_price=regularMarketPrice: 532.12; currency: USD",
        ],
    )

    joined = " ".join(summary.model_dump().values())
    assert "Nasdaq-100" in joined
    assert "101 holdings" in joined
    assert "0.20" in joined
    assert "regularMarketPrice" not in joined
    assert "provider market-reference" not in joined.lower()
    assert "available evidence" not in joined.lower()


def test_beginner_summary_fallback_humanizes_missing_field_names():
    service = HybridSummaryGenerationService()
    asset = build_asset_knowledge_pack("VOO").asset

    summary = service.generate_beginner_summary(
        asset=asset,
        base_summary=BeginnerSummary(
            what_it_is="Vanguard S&P 500 ETF (VOO) is an ETF.",
            why_people_consider_it="Beginners may study it.",
            main_catch="Issuer facts are point-in-time.",
        ),
        citation_ids=["c1"],
        evidence_notes=[
            "benchmark=S&P 500 Index",
            "holdings_count=500",
            "expense_ratio=0.03",
            "evidence_gaps=premium_discount_or_spread, summary_prospectus",
        ],
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )

    joined = " ".join(summary.model_dump().values())
    assert "premium_discount_or_spread" not in joined
    assert "summary_prospectus" not in joined
    assert "premium/discount spread data" in joined
    assert "summary prospectus" in joined


def test_beginner_summary_fallback_uses_curated_provider_profile_summary_for_etfs():
    service = HybridSummaryGenerationService()
    asset = build_asset_knowledge_pack("VOO").asset
    evidence_pack = _simple_generation_evidence_pack("VOO", ["c1"])
    evidence_pack["generation_context"]["asset_profile"]["fund_summary"] = (
        "The fund offers broad exposure to large U.S. companies by seeking to track the S&P 500 index."
    )
    evidence_pack["generation_context"]["asset_profile"]["fund_family"] = "Vanguard"
    evidence_pack["generation_context"]["asset_profile"]["category"] = "U.S. equity index ETF"
    evidence_pack["generation_context"]["identity_context"]["benchmark"] = "S&P 500 Index"
    evidence_pack["generation_context"]["identity_context"]["expense_ratio"] = "0.03"
    evidence_pack["generation_context"]["exposure_context"]["holdings_count"] = "500"

    summary = service.generate_beginner_summary(
        asset=asset,
        base_summary=BeginnerSummary(
            what_it_is="Vanguard S&P 500 ETF (VOO) is an ETF.",
            why_people_consider_it="Beginners may study it.",
            main_catch="Issuer facts are point-in-time.",
        ),
        citation_ids=["c1"],
        evidence_notes=[],
        generation_evidence_pack=evidence_pack,
    )

    assert "broad exposure to large U.S. companies" in summary.what_it_is
    assert "longBusinessSummary" not in summary.what_it_is
    assert "fixture" not in summary.what_it_is.lower()


def test_beginner_summary_rejects_internal_copy_from_live_generation():
    asset = build_asset_knowledge_pack("QQQ").asset

    def payload(request: Any) -> dict[str, Any]:
        return {
            "what_it_is": "QQQ is an ETF whose available evidence uses regularMarketPrice.",
            "why_people_consider_it": "Beginners can study the fund.",
            "main_catch": "Issuer facts are point-in-time.",
            "supporting_claims": [
                _supporting_claim("QQQ is an ETF.", ["c1"]),
            ],
        }

    service = HybridSummaryGenerationService(runtime=_ready_runtime(), structured_generator=payload)

    with pytest.raises(SummaryGenerationContractError):
        service.generate_beginner_summary(
            asset=asset,
            base_summary=BeginnerSummary(what_it_is="QQQ is an ETF.", why_people_consider_it="Study it.", main_catch="Risk."),
            citation_ids=["c1"],
            generation_evidence_pack=_simple_generation_evidence_pack("QQQ", ["c1"]),
        )


def test_default_live_task_allowlist_runs_deep_dive_generation_with_evidence_contract():
    asset = build_asset_knowledge_pack("VOO").asset
    calls: list[str] = []

    def payload(request: Any) -> dict[str, Any]:
        calls.append(request.task_name)
        return {
            "summary": "Live generated Deep Dive text is grounded in supplied citation evidence.",
            "supporting_claims": [
                _supporting_claim("Deep Dive text is grounded in supplied citation evidence.", ["c1"])
            ],
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=DEFAULT_LIVE_GENERATION_TASK_ALLOWLIST,
    )

    summary = service.generate_deep_dive_summary(
        asset=asset,
        section_id="construction_methodology",
        title="Construction Or Methodology",
        base_summary="Base section summary from structured evidence.",
        citation_ids=["c1"],
        evidence_state="partial",
        evidence_notes=["benchmark=S&P 500 Index"],
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )

    assert calls == ["deep_dive_summary"]
    assert summary is not None
    assert "grounded in supplied citation evidence" in summary


def test_live_generation_accepts_common_payload_wrapper_shape():
    clear_summary_generation_cache()
    clear_summary_generation_live_circuit()
    asset = build_asset_knowledge_pack("VOO").asset

    def payload(request: Any) -> dict[str, Any]:
        return {
            "payload": {
                "summary": "Wrapped live Deep Dive text is grounded in supplied citation evidence.",
                "supporting_claims": [
                    _supporting_claim("Wrapped live Deep Dive text is grounded in supplied citation evidence.", ["c1"])
                ],
            }
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
    )

    summary = service.generate_deep_dive_summary(
        asset=asset,
        section_id="construction_methodology",
        title="Construction Or Methodology",
        base_summary="Base section summary from structured evidence.",
        citation_ids=["c1"],
        evidence_state="partial",
        evidence_notes=["benchmark=S&P 500 Index"],
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )

    assert summary == "Wrapped live Deep Dive text is grounded in supplied citation evidence."


def test_live_generation_timeout_opens_short_circuit_for_followup_calls():
    clear_summary_generation_cache()
    clear_summary_generation_live_circuit()
    asset = build_asset_knowledge_pack("VOO").asset
    calls: list[str] = []

    def timeout_payload(request: Any) -> dict[str, Any]:
        calls.append(request.task_name)
        raise TimeoutError("provider timed out")

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=timeout_payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
        live_failure_cooldown_seconds=60,
    )

    try:
        first = service.generate_deep_dive_summary(
            asset=asset,
            section_id="construction_methodology",
            title="Construction Or Methodology",
            base_summary="First fallback summary.",
            citation_ids=["c1"],
            evidence_state="partial",
            evidence_notes=["benchmark=S&P 500 Index"],
            generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
        )
        second = service.generate_deep_dive_summary(
            asset=asset,
            section_id="cost_trading_context",
            title="Cost And Trading Context",
            base_summary="Second fallback summary.",
            citation_ids=["c1"],
            evidence_state="partial",
            evidence_notes=["expense_ratio=0.03"],
            generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
        )

        assert first is not None and first.startswith("First fallback summary.")
        assert second is not None and second.startswith("Second fallback summary.")
        assert calls == ["deep_dive_summary"]
    finally:
        clear_summary_generation_live_circuit()


def test_live_generation_default_timeout_allows_slower_local_models():
    assert summary_generation_module.DEFAULT_LIVE_SUMMARY_TIMEOUT_SECONDS == 75
    assert summary_generation_module._live_timeout_seconds_from_env({}) == 75
    assert summary_generation_module._live_timeout_seconds_from_env({"LLM_LIVE_TIMEOUT_SECONDS": "9"}) == 9
    assert summary_generation_module.DEFAULT_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS == 30
    assert summary_generation_module._live_slow_response_threshold_seconds_from_env({}) == 30
    assert summary_generation_module._live_slow_response_threshold_seconds_from_env(
        {"LLM_LIVE_SLOW_RESPONSE_THRESHOLD_SECONDS": "8"}
    ) == 8


def test_live_generation_slow_success_opens_short_circuit_for_followup_calls(monkeypatch: pytest.MonkeyPatch):
    clear_summary_generation_cache()
    clear_summary_generation_live_circuit()
    asset = build_asset_knowledge_pack("VOO").asset
    calls: list[str] = []
    monotonic_values = [100.0, 100.0, 103.0, 103.0, 103.1]

    def fake_monotonic() -> float:
        if monotonic_values:
            return monotonic_values.pop(0)
        return 103.1

    monkeypatch.setattr(summary_generation_module.time, "monotonic", fake_monotonic)

    def slow_payload(request: Any) -> dict[str, Any]:
        calls.append(request.task_name)
        return {
            "summary": "Slow live Deep Dive text is grounded in supplied citation evidence.",
            "supporting_claims": [
                _supporting_claim("Slow live Deep Dive text is grounded in supplied citation evidence.", ["c1"])
            ],
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=slow_payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
        cache_ttl_seconds=0,
        live_failure_cooldown_seconds=60,
        live_slow_response_threshold_seconds=2,
    )

    try:
        first = service.generate_deep_dive_summary(
            asset=asset,
            section_id="construction_methodology",
            title="Construction Or Methodology",
            base_summary="First fallback summary.",
            citation_ids=["c1"],
            evidence_state="partial",
            evidence_notes=["benchmark=S&P 500 Index"],
            generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
        )
        second = service.generate_deep_dive_summary(
            asset=asset,
            section_id="cost_trading_context",
            title="Cost And Trading Context",
            base_summary="Second fallback summary.",
            citation_ids=["c1"],
            evidence_state="partial",
            evidence_notes=["expense_ratio=0.03"],
            generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
        )

        assert first == "Slow live Deep Dive text is grounded in supplied citation evidence."
        assert second is not None and second.startswith("Second fallback summary.")
        assert calls == ["deep_dive_summary"]
    finally:
        clear_summary_generation_live_circuit()


def test_summary_copy_validator_rejects_raw_snake_case_field_names():
    asset = build_asset_knowledge_pack("VOO").asset

    def payload(request: Any) -> dict[str, Any]:
        return {
            "summary": "The premium_discount_or_spread field is unavailable in the supplied context.",
            "supporting_claims": [
                _supporting_claim("A limitation is present in the supplied context.", ["c1"])
            ],
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
    )

    with pytest.raises(SummaryGenerationContractError, match="raw field names"):
        service.generate_deep_dive_summary(
            asset=asset,
            section_id="cost_trading_context",
            title="Cost And Trading Context",
            base_summary="Base section summary from structured evidence.",
            citation_ids=["c1"],
            evidence_state="partial",
            evidence_notes=["premium/discount spread data is unavailable"],
            generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
        )


def test_deep_dive_live_generation_can_be_explicitly_enabled_for_local_review():
    asset = build_asset_knowledge_pack("VOO").asset
    calls: list[str] = []

    def payload(request: Any) -> dict[str, Any]:
        calls.append(request.task_name)
        return {
            "summary": "Generated section summary grounded in supplied citation ids.",
            "supporting_claims": [
                _supporting_claim("Generated section summary grounded in supplied citation ids.", ["c1"])
            ],
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
    )

    summary = service.generate_deep_dive_summary(
        asset=asset,
        section_id="construction_methodology",
        title="Construction Or Methodology",
        base_summary="Base section summary from structured evidence.",
        citation_ids=["c1"],
        evidence_state="partial",
        evidence_notes=[],
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )

    assert calls == ["deep_dive_summary"]
    assert summary == "Generated section summary grounded in supplied citation ids."


def test_valid_live_generation_is_reused_from_summary_cache():
    clear_summary_generation_cache()
    asset = build_asset_knowledge_pack("VOO").asset
    calls: list[str] = []

    def payload(request: Any) -> dict[str, Any]:
        calls.append(request.task_name)
        return {
            "summary": "Cached live section summary grounded in supplied evidence.",
            "supporting_claims": [
                _supporting_claim("Cached live section summary grounded in supplied evidence.", ["c1"])
            ],
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
        cache_ttl_seconds=300,
    )

    first = service.generate_deep_dive_summary(
        asset=asset,
        section_id="cost_trading_context",
        title="Cost And Trading Context",
        base_summary="Base summary.",
        citation_ids=["c1"],
        evidence_state="mixed",
        evidence_notes=["expense_ratio=0.03"],
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )
    second = service.generate_deep_dive_summary(
        asset=asset,
        section_id="cost_trading_context",
        title="Cost And Trading Context",
        base_summary="Base summary.",
        citation_ids=["c1"],
        evidence_state="mixed",
        evidence_notes=["expense_ratio=0.03"],
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )

    assert first == second
    assert calls == ["deep_dive_summary"]


def test_invalid_live_generation_is_not_cached():
    clear_summary_generation_cache()
    asset = build_asset_knowledge_pack("VOO").asset
    calls: list[str] = []

    def payload(request: Any) -> dict[str, Any]:
        calls.append(request.task_name)
        return {"summary": "You should buy VOO now."}

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
        cache_ttl_seconds=300,
    )

    for _ in range(2):
        with pytest.raises(SummaryGenerationContractError):
            service.generate_deep_dive_summary(
                asset=asset,
                section_id="cost_trading_context",
                title="Cost And Trading Context",
                base_summary="Base summary.",
                citation_ids=["c1"],
                evidence_state="mixed",
                evidence_notes=["expense_ratio=0.03"],
                generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
            )

    assert calls == ["deep_dive_summary", "deep_dive_summary"]


def test_mocked_summaries_and_risks_are_meaningfully_different_across_assets():
    service = HybridSummaryGenerationService()
    qqq = build_asset_knowledge_pack("QQQ").asset
    voo = build_asset_knowledge_pack("VOO").asset
    aapl = build_asset_knowledge_pack("AAPL").asset

    qqq_summary = service.generate_beginner_summary(
        asset=qqq,
        base_summary=BeginnerSummary(what_it_is="QQQ is an ETF.", why_people_consider_it="Study it.", main_catch="Risk."),
        citation_ids=["c1"],
        evidence_notes=["benchmark=Nasdaq-100 Index", "holdings_count=101", "expense_ratio=0.20"],
    )
    voo_summary = service.generate_beginner_summary(
        asset=voo,
        base_summary=BeginnerSummary(what_it_is="VOO is an ETF.", why_people_consider_it="Study it.", main_catch="Risk."),
        citation_ids=["c1"],
        evidence_notes=["benchmark=S&P 500 Index", "holdings_count=500", "expense_ratio=0.03"],
    )
    aapl_summary = service.generate_beginner_summary(
        asset=aapl,
        base_summary=BeginnerSummary(what_it_is="AAPL is a stock.", why_people_consider_it="Study it.", main_catch="Risk."),
        citation_ids=["c1"],
        evidence_notes=["provider_profile_overview=sector: Technology; industry: Consumer Electronics", "latest_revenue_fact=391000000000 USD"],
    )

    qqq_text = " ".join(qqq_summary.model_dump().values())
    voo_text = " ".join(voo_summary.model_dump().values())
    aapl_text = " ".join(aapl_summary.model_dump().values())
    assert "Nasdaq-100" in qqq_text
    assert "S&P 500" in voo_text
    assert "Technology" in aapl_text
    assert len({qqq_text, voo_text, aapl_text}) == 3

    qqq_risks = service.generate_top_risks(
        asset=qqq,
        candidate_risks=[
            RiskItem(title="Concentration risk", plain_english_explanation="Nasdaq-100 concentration.", citation_ids=["c1"]),
            RiskItem(title="Market risk", plain_english_explanation="Equity market risk.", citation_ids=["c1"]),
            RiskItem(title="Tracking risk", plain_english_explanation="Index tracking risk.", citation_ids=["c1"]),
        ],
        fallback_risks=[
            RiskItem(title="Concentration risk", plain_english_explanation="Nasdaq-100 concentration.", citation_ids=["c1"]),
            RiskItem(title="Market risk", plain_english_explanation="Equity market risk.", citation_ids=["c1"]),
            RiskItem(title="Tracking risk", plain_english_explanation="Index tracking risk.", citation_ids=["c1"]),
        ],
        allowed_citation_ids=["c1"],
    )
    aapl_risks = service.generate_top_risks(
        asset=aapl,
        candidate_risks=[
            RiskItem(title="Single-company risk", plain_english_explanation="Apple is one company.", citation_ids=["c1"]),
            RiskItem(title="Business and competition risk", plain_english_explanation="Consumer technology competition.", citation_ids=["c1"]),
            RiskItem(title="Financial and valuation risk", plain_english_explanation="Valuation and results can change.", citation_ids=["c1"]),
        ],
        fallback_risks=[
            RiskItem(title="Single-company risk", plain_english_explanation="Apple is one company.", citation_ids=["c1"]),
            RiskItem(title="Business and competition risk", plain_english_explanation="Consumer technology competition.", citation_ids=["c1"]),
            RiskItem(title="Financial and valuation risk", plain_english_explanation="Valuation and results can change.", citation_ids=["c1"]),
        ],
        allowed_citation_ids=["c1"],
    )
    assert [risk.title for risk in qqq_risks] != [risk.title for risk in aapl_risks]


def test_top_risk_generation_selects_from_evidence_candidates_and_validates_citations():
    asset = build_asset_knowledge_pack("QQQ").asset
    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=lambda request: {
            "risks": [
                {
                    "title": "Concentration risk",
                    "plain_english_explanation": "QQQ tracks Nasdaq-100 exposure, so fewer large companies can drive more of the outcome.",
                    "citation_ids": ["c1"],
                    "supporting_claims": [_supporting_claim("QQQ tracks Nasdaq-100 exposure.", ["c1"], claim_type="risk")],
                },
                {
                    "title": "Methodology risk",
                    "plain_english_explanation": "The fund follows an index methodology, so benchmark rules shape what the ETF owns.",
                    "citation_ids": ["c1"],
                    "supporting_claims": [_supporting_claim("Benchmark rules shape what the ETF owns.", ["c1"], claim_type="risk")],
                },
                {
                    "title": "Trading context risk",
                    "plain_english_explanation": "Provider quote fields are context only and should not be treated as trading guidance.",
                    "citation_ids": ["c2"],
                    "supporting_claims": [_supporting_claim("Provider quote fields are context only.", ["c2"], claim_type="risk")],
                },
            ]
        },
    )
    candidates = [
        RiskItem(title="Concentration risk", plain_english_explanation="Candidate concentration.", citation_ids=["c1"]),
        RiskItem(title="Methodology risk", plain_english_explanation="Candidate methodology.", citation_ids=["c1"]),
        RiskItem(title="Trading context risk", plain_english_explanation="Candidate trading.", citation_ids=["c2"]),
    ]

    risks = service.generate_top_risks(
        asset=asset,
        candidate_risks=candidates,
        fallback_risks=candidates,
        allowed_citation_ids=["c1", "c2"],
        generation_evidence_pack=_simple_generation_evidence_pack("QQQ", ["c1", "c2"]),
    )

    assert [risk.title for risk in risks] == ["Concentration risk", "Methodology risk", "Trading context risk"]
    assert all(risk.citation_ids for risk in risks)


def test_top_risk_generation_rejects_wrong_citations():
    asset = build_asset_knowledge_pack("QQQ").asset
    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=lambda request: {
            "risks": [
                {"title": "One", "plain_english_explanation": "Supported text.", "citation_ids": ["outside"]},
                {"title": "Two", "plain_english_explanation": "Supported text.", "citation_ids": ["c1"]},
                {"title": "Three", "plain_english_explanation": "Supported text.", "citation_ids": ["c1"]},
            ]
        },
    )
    fallback = [
        RiskItem(title="One", plain_english_explanation="Fallback one.", citation_ids=["c1"]),
        RiskItem(title="Two", plain_english_explanation="Fallback two.", citation_ids=["c1"]),
        RiskItem(title="Three", plain_english_explanation="Fallback three.", citation_ids=["c1"]),
    ]

    with pytest.raises(SummaryGenerationContractError):
        service.generate_top_risks(
            asset=asset,
            candidate_risks=fallback,
            fallback_risks=fallback,
            allowed_citation_ids=["c1"],
        )


def test_market_ai_generation_rejects_headline_repetition():
    focus = select_market_news_focus(fixture_market_news_candidates(as_of="2026-04-23"), as_of="2026-04-23")
    repeated_titles = "; ".join(item.title for item in focus.items[:5])
    first_citation = focus.items[0].citation_ids[0]

    def payload(request: Any) -> dict[str, Any]:
        return {
            "sections": [
                {
                    "section_id": section_id,
                    "label": label,
                    "analysis": "The selected Market News Focus items are " + repeated_titles,
                    "bullets": ["Repeated headlines."],
                    "citation_ids": [first_citation],
                    "uncertainty": [],
                }
                for section_id, label in [
                    ("what_changed_this_week", "What Changed This Week"),
                    ("macro_policy", "Macro & Policy"),
                    ("equity_market_drivers", "Equity Market Drivers"),
                    ("ai_technology_semiconductors", "AI / Technology / Semiconductors"),
                    ("geopolitical_energy_risks", "Geopolitical & Energy Risks"),
                    ("credit_liquidity_sentiment", "Credit / Liquidity / Sentiment"),
                    ("scenario_lens", "Scenario Lens"),
                    ("practical_watchpoints", "Practical Watchpoints"),
                ]
            ]
        }

    service = HybridSummaryGenerationService(runtime=_ready_runtime(), structured_generator=payload)

    with pytest.raises(SummaryGenerationContractError):
        service.generate_market_ai_comprehensive_analysis(
            focus=focus,
            minimum_market_news_item_count=5,
            minimum_topic_bucket_count=3,
        )


def test_ticker_ai_generation_rejects_headline_repetition():
    focus = _two_item_weekly_news_focus()
    repeated_titles = "; ".join(item.title for item in focus.items)
    first_citation = focus.items[0].citation_ids[0]

    def payload(request: Any) -> dict[str, Any]:
        return _ticker_analysis_payload(
            citation_ids=[first_citation],
            analysis_text="The selected Weekly News Focus items are " + repeated_titles,
        )

    service = HybridSummaryGenerationService(runtime=_ready_runtime(), structured_generator=payload)

    with pytest.raises(SummaryGenerationContractError):
        service.generate_ticker_ai_comprehensive_analysis(
            asset=build_asset_knowledge_pack("QQQ").asset,
            weekly_news_focus=focus,
            canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
            canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
            minimum_weekly_news_item_count=2,
            weekly_news_selected_item_count=focus.selected_item_count,
        )


def test_gated_structured_summary_output_rejects_bad_citations_before_rendering():
    focus = _two_item_weekly_news_focus()
    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=lambda request: _ticker_analysis_payload(citation_ids=["outside_pack_citation"]),
    )

    with pytest.raises(SummaryGenerationContractError):
        service.generate_ticker_ai_comprehensive_analysis(
            asset=build_asset_knowledge_pack("QQQ").asset,
            weekly_news_focus=focus,
            canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
            canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
            minimum_weekly_news_item_count=2,
            weekly_news_selected_item_count=focus.selected_item_count,
        )


def test_live_prompt_payload_includes_task_spec_and_generation_evidence_pack():
    asset = build_asset_knowledge_pack("VOO").asset
    seen_request: SummaryGenerationRequest | None = None

    def payload(request: SummaryGenerationRequest) -> dict[str, Any]:
        nonlocal seen_request
        seen_request = request
        return {
            "summary": "Live generated Deep Dive text is grounded in supplied citation evidence.",
            "supporting_claims": [
                _supporting_claim("Live generated Deep Dive text is grounded in supplied citation evidence.", ["c1"])
            ],
        }

    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=payload,
        live_task_allowlist=frozenset({"deep_dive_summary"}),
    )

    service.generate_deep_dive_summary(
        asset=asset,
        section_id="cost_trading_context",
        title="Cost And Trading Context",
        base_summary="Base summary.",
        citation_ids=["c1"],
        evidence_state="supported",
        generation_evidence_pack=_simple_generation_evidence_pack("VOO", ["c1"]),
    )

    assert seen_request is not None
    safe_payload = _safe_prompt_payload(seen_request)
    assert safe_payload["task_prompt_spec"]["objective"]
    evidence_pack = safe_payload["payload"]["generation_evidence_pack"]
    assert evidence_pack["schema_version"] == "generation-evidence-pack-v1"
    assert evidence_pack["generation_context"]["schema_version"] == "generation-context-v1"
    assert any("generation_context" in rule for rule in safe_payload["output_rules"])
    assert evidence_pack["citation_evidence"][0]["citation_id"] == "c1"
    assert "allowed_numeric_facts" in evidence_pack


def test_generated_market_ai_rejects_unsupported_numeric_claims():
    focus = select_market_news_focus(fixture_market_news_candidates(as_of="2026-04-23"), as_of="2026-04-23")
    first_citation = focus.items[0].citation_ids[0]
    evidence_pack = _simple_generation_evidence_pack("MARKET", [first_citation])
    evidence_pack["allowed_numeric_facts"] = [
        {
            "fact_id": "economic:vix",
            "scope": "market",
            "label": "VIX Index Closing Price",
            "value": 21.0,
            "unit": "index_points",
            "aliases": ["vix", "volatility index"],
            "tolerance_abs": 0.1,
            "citation_ids": [first_citation],
            "source_document_ids": ["src_test_c1"],
        }
    ]

    def payload(request: Any) -> dict[str, Any]:
        return {
            "sections": [
                {
                    "section_id": section_id,
                    "label": label,
                    "analysis": "The VIX level is 60, which is not supported by the supplied numeric facts.",
                    "bullets": ["The VIX level is 60."],
                    "citation_ids": [first_citation],
                    "uncertainty": [],
                    "supporting_claims": [
                        _supporting_claim("The VIX level is supplied in the evidence pack.", [first_citation])
                    ],
                }
                for section_id, label in [
                    ("what_changed_this_week", "What Changed This Week"),
                    ("macro_policy", "Macro & Policy"),
                    ("equity_market_drivers", "Equity Market Drivers"),
                    ("ai_technology_semiconductors", "AI / Technology / Semiconductors"),
                    ("geopolitical_energy_risks", "Geopolitical & Energy Risks"),
                    ("credit_liquidity_sentiment", "Credit / Liquidity / Sentiment"),
                    ("scenario_lens", "Scenario Lens"),
                    ("practical_watchpoints", "Practical Watchpoints"),
                ]
            ]
        }

    service = HybridSummaryGenerationService(runtime=_ready_runtime(), structured_generator=payload)

    with pytest.raises(SummaryGenerationContractError):
        service.generate_market_ai_comprehensive_analysis(
            focus=focus,
            minimum_market_news_item_count=5,
            minimum_topic_bucket_count=3,
            generation_evidence_pack=evidence_pack,
        )


def test_weekly_news_ai_analysis_repairs_citation_failure_with_deterministic_fallback():
    focus = _two_item_weekly_news_focus()
    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=lambda request: _ticker_analysis_payload(citation_ids=["outside_pack_citation"]),
    )

    analysis = build_ai_comprehensive_analysis(
        build_asset_knowledge_pack("QQQ").asset,
        focus,
        canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
        summary_generation_service=service,
    )

    assert analysis.analysis_available is True
    assert analysis.state is WeeklyNewsContractState.available
    assert "live_generation_repaired_with_deterministic_fallback" in analysis.validation_reason_codes
    assert "citation_validation_failed" in analysis.validation_reason_codes
    assert analysis.no_live_external_calls is True
    assert analysis.generation_diagnostics.attempted_live is True
    assert analysis.generation_diagnostics.used_fallback is True
    assert "live_generation_repaired_with_deterministic_fallback" in analysis.generation_diagnostics.fallback_reason_codes
    assert "citation_validation_failed" in analysis.generation_diagnostics.fallback_reason_codes
    assert analysis.generation_diagnostics.model_name == "openai/gpt-oss-120b:free"
    assert validate_ai_comprehensive_analysis(analysis, focus) == analysis


def test_weekly_news_ai_analysis_suppresses_invalid_generated_output():
    focus = _two_item_weekly_news_focus()
    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=lambda request: _ticker_analysis_payload(
            citation_ids=[focus.items[0].citation_ids[0]],
            analysis_text="The price target is guaranteed to be higher.",
        ),
    )

    analysis = build_ai_comprehensive_analysis(
        build_asset_knowledge_pack("QQQ").asset,
        focus,
        canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
        summary_generation_service=service,
    )

    assert analysis.state is WeeklyNewsContractState.suppressed
    assert analysis.analysis_available is False
    assert analysis.sections == []
    assert "failed schema, citation, freshness, or safety validation" in str(analysis.suppression_reason)


def test_chat_hybrid_generation_falls_back_when_structured_output_is_unsafe():
    pack = build_asset_knowledge_pack("VOO")
    service = HybridSummaryGenerationService(
        runtime=_ready_runtime(),
        structured_generator=lambda request: {
            "direct_answer": "You should buy VOO now because the evidence says so.",
            "why_it_matters": "This is unsafe advice copy.",
            "uncertainty": [],
        },
    )

    response = generate_chat_from_pack(pack, "What does it hold?", summary_generation_service=service)

    assert "You should buy" not in response.direct_answer
    assert "about 500" in response.direct_answer
    assert "deterministic citation-bound answer" in " ".join(response.uncertainty)
    assert validate_chat_response(response, pack).valid


def test_chat_advice_redirect_happens_before_hybrid_generation():
    pack = build_asset_knowledge_pack("VOO")

    def fail_if_called(request: Any) -> dict[str, Any]:
        raise AssertionError("advice redirects must not call summary generation")

    service = HybridSummaryGenerationService(runtime=_ready_runtime(), structured_generator=fail_if_called)

    response = generate_chat_from_pack(pack, "Should I buy VOO?", summary_generation_service=service)

    assert response.citations == []
    assert response.source_documents == []
    assert response.safety_classification.value == "personalized_advice_redirect"


def test_summary_generation_module_stays_deterministic_without_network_clients():
    source = (ROOT / "backend" / "summary_generation.py").read_text(encoding="utf-8")

    assert SUMMARY_GENERATION_BOUNDARY == "hybrid-summary-generation-orchestrator-v1"
    assert CHAT_ANSWER_SCHEMA_VERSION == "grounded-chat-hybrid-answer-v1"
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
        assert forbidden not in source


def test_openrouter_live_body_uses_models_fallback_chain_without_single_model():
    runtime = _ready_runtime()
    request = SummaryGenerationRequest(
        task_name="beginner_summary",
        schema_version="beginner-summary-test-v1",
        asset_ticker="VOO",
        payload={},
    )

    body = summary_generation_module._openrouter_chat_completion_body(
        request,
        summary_generation_module._safe_prompt_payload(request),
        runtime,
    )

    assert body["models"] == [*DEFAULT_OPENROUTER_FREE_MODEL_ORDER, DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL]
    assert body["route"] == "fallback"
    assert "model" not in body
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["required"] == [
        "what_it_is",
        "why_people_consider_it",
        "main_catch",
        "supporting_claims",
    ]


def test_openrouter_live_body_omits_paid_fallback_when_disabled():
    runtime = build_llm_runtime_config(
        {**default_openrouter_settings(), "OPENROUTER_PAID_FALLBACK_ENABLED": "false"},
        server_side_key_present=True,
    )
    request = SummaryGenerationRequest(
        task_name="deep_dive_summary",
        schema_version="deep-dive-test-v1",
        asset_ticker="VOO",
        payload={},
    )

    body = summary_generation_module._openrouter_chat_completion_body(
        request,
        summary_generation_module._safe_prompt_payload(request),
        runtime,
    )

    assert body["models"] == list(DEFAULT_OPENROUTER_FREE_MODEL_ORDER)
    assert DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL not in body["models"]
    assert "model" not in body


def _ready_runtime():
    return build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True)


def _two_item_weekly_news_focus():
    asset = build_asset_knowledge_pack("QQQ").asset
    return select_weekly_news_focus(
        asset,
        [
            _candidate("methodology", event_type=WeeklyNewsEventType.methodology_change, is_official=True),
            _candidate("sponsor_update", event_type=WeeklyNewsEventType.sponsor_update),
        ],
        as_of="2026-04-23",
    )


def _candidate(
    event_id: str,
    *,
    event_type: WeeklyNewsEventType = WeeklyNewsEventType.sponsor_update,
    is_official: bool = False,
) -> WeeklyNewsCandidate:
    return WeeklyNewsCandidate(
        event_id=event_id,
        asset_ticker="QQQ",
        event_type=event_type,
        title=f"{event_id.replace('_', ' ').title()} fixture",
        summary=f"Deterministic Weekly News Focus fixture summary for {event_id}.",
        event_date="2026-04-21",
        published_at="2026-04-21T12:00:00Z",
        retrieved_at="2026-04-23T12:00:00Z",
        source_document_id=f"src_{event_id}",
        source_chunk_id=f"chk_{event_id}",
        source_type="issuer_press_release" if is_official else "recent_development",
        source_rank=1 if is_official else 3,
        source_title=f"{event_id.replace('_', ' ').title()} source",
        publisher="Fixture Publisher",
        url=f"local://fixtures/qqq/weekly-news/{event_id}",
        source_quality=SourceQuality.official if is_official else SourceQuality.fixture,
        allowlist_status=SourceAllowlistStatus.allowed,
        source_use_policy=SourceUsePolicy.summary_allowed,
        freshness_state=FreshnessState.fresh,
        is_official=is_official,
        supporting_text=f"Supporting fixture text for {event_id}.",
        duplicate_group_id=event_id,
    )


def _ticker_analysis_payload(
    *,
    citation_ids: list[str],
    analysis_text: str = "Generated text stays grounded in selected weekly-news evidence.",
) -> dict[str, Any]:
    return {
        "sections": [
            {
                "section_id": "what_changed_this_week",
                "label": "What Changed This Week",
                "analysis": analysis_text,
                "bullets": ["A cited weekly item anchors this section."],
                "citation_ids": citation_ids,
                "uncertainty": [],
                "supporting_claims": [_supporting_claim("A cited weekly item anchors this section.", citation_ids)],
            },
            {
                "section_id": "market_context",
                "label": "Market Context",
                "analysis": "Market context is limited to the same selected evidence.",
                "bullets": ["No market-wide claim is added without cited evidence."],
                "citation_ids": citation_ids,
                "uncertainty": [],
                "supporting_claims": [_supporting_claim("Market context is limited to the same selected evidence.", citation_ids)],
            },
            {
                "section_id": "business_or_fund_context",
                "label": "Business/Fund Context",
                "analysis": "Fund context stays separate from stable asset identity.",
                "bullets": ["Canonical facts remain distinct from weekly news."],
                "citation_ids": citation_ids,
                "uncertainty": [],
                "supporting_claims": [_supporting_claim("Fund context stays separate from stable asset identity.", citation_ids)],
            },
            {
                "section_id": "risk_context",
                "label": "Risk Context",
                "analysis": "Risk context is educational and does not make a personal decision.",
                "bullets": ["The cited items define the scope of this context."],
                "citation_ids": citation_ids,
                "uncertainty": [],
                "supporting_claims": [_supporting_claim("Risk context is educational.", citation_ids, claim_type="risk")],
            },
        ]
    }


def _simple_generation_evidence_pack(ticker: str, citation_ids: list[str]) -> dict[str, Any]:
    normalized = ticker.upper()
    allowed_assets = [normalized]
    if normalized != "MARKET":
        allowed_assets.append("MARKET")
    return {
        "schema_version": "generation-evidence-pack-v1",
        "scope": "asset" if normalized != "MARKET" else "market",
        "asset_ticker": normalized,
        "allowed_asset_tickers": allowed_assets,
        "source_documents": [
            {
                "source_document_id": f"src_test_{citation_id}",
                "source_type": "normalized_fact",
                "title": "Test source",
                "publisher": "Fixture Publisher",
                "freshness_state": "fresh",
                "is_official": True,
                "source_quality": "fixture",
                "allowlist_status": "allowed",
                "source_use_policy": "summary_allowed",
            }
            for citation_id in citation_ids
        ],
        "canonical_facts": [],
        "source_passages": [],
        "market_news": [],
        "weekly_news": [],
        "economic_indicators": [],
        "technical_indicators": {},
        "allowed_numeric_facts": [],
        "generation_context": {
            "schema_version": "generation-context-v1",
            "asset_ticker": normalized,
            "scope": "asset" if normalized != "MARKET" else "market",
            "asset_profile": {
                "ticker": normalized,
                "name": normalized,
                "asset_type": "etf" if normalized in {"QQQ", "VOO", "MARKET"} else "stock",
                "sector": "Technology" if normalized == "AAPL" else None,
                "industry": "Consumer Electronics" if normalized == "AAPL" else None,
            },
            "identity_context": {
                "ticker": normalized,
                "name": normalized,
                "asset_type": "etf" if normalized in {"QQQ", "VOO", "MARKET"} else "stock",
            },
            "exposure_context": {},
            "market_context": {},
            "ticker_context": {},
            "evidence_limits": {"missing_fields": [], "partial_fields": [], "fallback_labels": [], "notes": []},
        },
        "citation_evidence": [
            {
                "citation_id": citation_id,
                "asset_ticker": normalized,
                "source_document_id": f"src_test_{citation_id}",
                "source_type": "normalized_fact",
                "evidence_kind": "normalized_fact",
                "freshness_state": "fresh",
                "supported_claim_types": ["factual", "interpretation", "risk", "recent"],
                "supporting_text": "Test citation evidence supports generated factual and analytical claims.",
                "supports_claim": True,
                "is_recent": True,
                "allowlist_status": "allowed",
                "source_use_policy": "summary_allowed",
                "source_identity": f"local://test/{citation_id}",
                "is_official": True,
                "source_quality": "fixture",
                "storage_rights": "summary_allowed",
                "export_rights": "excerpts_allowed",
                "review_status": "approved",
                "approval_rationale": "Unit-test evidence pack fixture.",
                "parser_status": "parsed",
            }
            for citation_id in citation_ids
        ],
        "evidence_notes": [],
        "rules": {
            "use_supplied_evidence_only": True,
            "numeric_claims_must_match_allowed_numeric_facts": True,
            "no_buy_sell_hold_allocation_tax_brokerage_or_price_target": True,
        },
    }


def _supporting_claim(
    claim_text: str,
    citation_ids: list[str],
    *,
    claim_type: str = "factual",
) -> dict[str, Any]:
    return {"claim_text": claim_text, "claim_type": claim_type, "citation_ids": citation_ids}
