from datetime import datetime, timezone
from pathlib import Path

from backend.models import (
    EvidenceState,
    FreshnessState,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsEventType,
)
from backend.retrieval import build_asset_knowledge_pack
from backend.weekly_news import (
    WeeklyNewsCandidate,
    build_ai_comprehensive_analysis,
    build_weekly_news_focus_from_pack,
    compute_weekly_news_window,
    select_weekly_news_focus,
    validate_ai_comprehensive_analysis,
)


ROOT = Path(__file__).resolve().parents[2]


def test_market_week_window_uses_explicit_eastern_as_of_date():
    window = compute_weekly_news_window("2026-04-23")

    assert window.as_of_date == "2026-04-23"
    assert window.timezone == "America/New_York"
    assert window.previous_market_week.start == "2026-04-13"
    assert window.previous_market_week.end == "2026-04-19"
    assert window.current_week_to_date.start == "2026-04-20"
    assert window.current_week_to_date.end == "2026-04-22"
    assert window.news_window_start == "2026-04-13"
    assert window.news_window_end == "2026-04-22"
    assert window.includes_current_week_to_date is True

    monday = compute_weekly_news_window("2026-04-20")
    assert monday.previous_market_week.start == "2026-04-13"
    assert monday.previous_market_week.end == "2026-04-19"
    assert monday.current_week_to_date.start is None
    assert monday.current_week_to_date.end is None
    assert monday.news_window_end == "2026-04-19"

    eastern_from_utc = compute_weekly_news_window(datetime(2026, 4, 23, 2, 0, tzinfo=timezone.utc))
    assert eastern_from_utc.as_of_date == "2026-04-22"
    assert eastern_from_utc.current_week_to_date.end == "2026-04-21"


def test_fixture_packs_render_clear_empty_weekly_news_state_without_padding():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)
        focus = build_weekly_news_focus_from_pack(pack, as_of="2026-04-23")
        analysis = build_ai_comprehensive_analysis(pack.asset, focus)

        assert focus.state is WeeklyNewsContractState.no_high_signal
        assert focus.items == []
        assert focus.empty_state is not None
        assert focus.empty_state.evidence_state is EvidenceState.no_high_signal
        assert "No major Weekly News Focus items found" in focus.empty_state.message
        assert focus.stable_facts_are_separate is True
        assert analysis.state is WeeklyNewsContractState.suppressed
        assert analysis.analysis_available is False
        assert analysis.sections == []
        assert "fewer than two high-signal" in analysis.suppression_reason


def test_weekly_news_selection_prioritizes_official_sources_and_excludes_disallowed_items():
    asset = build_asset_knowledge_pack("QQQ").asset
    focus = select_weekly_news_focus(
        asset,
        [
            _candidate("official_methodology", event_type=WeeklyNewsEventType.methodology_change, source_rank=1, source_quality=SourceQuality.issuer, is_official=True),
            _candidate("allowlisted_context", event_type=WeeklyNewsEventType.sponsor_update, source_rank=5, source_quality=SourceQuality.allowlisted),
            _candidate("duplicate_context", duplicate_of_event_id="allowlisted_context", is_duplicate=True),
            _candidate("metadata_only", source_use_policy=SourceUsePolicy.metadata_only),
            _candidate("rejected_source", allowlist_status=SourceAllowlistStatus.rejected, source_use_policy=SourceUsePolicy.rejected, source_quality=SourceQuality.rejected),
            _candidate("wrong_asset", asset_ticker="VOO"),
            _candidate("promotional", promotional=True),
            _candidate("irrelevant", irrelevant=True),
            _candidate("outside_window", event_date="2026-04-01"),
            _candidate("weak_context", event_type=WeeklyNewsEventType.other, asset_relevance="sector", source_quality=SourceQuality.provider),
        ],
        as_of="2026-04-23",
    )

    assert [item.event_id for item in focus.items] == ["official_methodology", "allowlisted_context"]
    assert focus.items[0].source.source_quality is SourceQuality.issuer
    assert focus.items[0].selection_rationale.total_score > focus.items[1].selection_rationale.total_score
    assert focus.items[0].period_bucket.value == "current_week_to_date"
    assert all(item.source.allowlist_status is SourceAllowlistStatus.allowed for item in focus.items)
    assert all(item.source.source_use_policy in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed} for item in focus.items)
    assert len(focus.items) < 5
    assert focus.empty_state is None


def test_ai_comprehensive_analysis_requires_two_high_signal_items_and_preserves_section_order():
    asset = build_asset_knowledge_pack("QQQ").asset
    one_item = select_weekly_news_focus(
        asset,
        [_candidate("only_one", event_type=WeeklyNewsEventType.methodology_change, is_official=True)],
        as_of="2026-04-23",
    )
    suppressed = build_ai_comprehensive_analysis(asset, one_item, canonical_fact_citation_ids=["c_fact_qqq_asset_identity"])

    assert suppressed.analysis_available is False
    assert suppressed.sections == []
    assert suppressed.state is WeeklyNewsContractState.suppressed

    focus = select_weekly_news_focus(
        asset,
        [
            _candidate("methodology", event_type=WeeklyNewsEventType.methodology_change, is_official=True),
            _candidate("sponsor_update", event_type=WeeklyNewsEventType.sponsor_update, source_quality=SourceQuality.allowlisted),
        ],
        as_of="2026-04-23",
    )
    analysis = build_ai_comprehensive_analysis(
        asset,
        focus,
        canonical_fact_citation_ids=["c_fact_qqq_asset_identity"],
        canonical_source_document_ids=["src_qqq_fact_sheet_fixture"],
    )

    assert analysis.analysis_available is True
    assert [section.label for section in analysis.sections] == [
        "What Changed This Week",
        "Market Context",
        "Business/Fund Context",
        "Risk Context",
    ]
    assert analysis.weekly_news_event_ids == ["methodology", "sponsor_update"]
    assert "c_fact_qqq_asset_identity" in analysis.citation_ids
    assert all(section.citation_ids for section in analysis.sections)
    assert validate_ai_comprehensive_analysis(analysis, focus) == analysis


def test_weekly_news_module_does_not_import_live_network_clients():
    source = (ROOT / "backend" / "weekly_news.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in source


def _candidate(
    event_id: str,
    *,
    asset_ticker: str = "QQQ",
    event_type: WeeklyNewsEventType = WeeklyNewsEventType.sponsor_update,
    event_date: str = "2026-04-21",
    source_rank: int = 3,
    source_quality: SourceQuality = SourceQuality.fixture,
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed,
    source_use_policy: SourceUsePolicy = SourceUsePolicy.summary_allowed,
    is_official: bool = False,
    asset_relevance: str = "exact",
    duplicate_of_event_id: str | None = None,
    is_duplicate: bool = False,
    promotional: bool = False,
    irrelevant: bool = False,
) -> WeeklyNewsCandidate:
    return WeeklyNewsCandidate(
        event_id=event_id,
        asset_ticker=asset_ticker,
        event_type=event_type,
        title=f"{event_id.replace('_', ' ').title()} fixture",
        summary=f"Deterministic Weekly News Focus fixture summary for {event_id}.",
        event_date=event_date,
        published_at=f"{event_date}T12:00:00Z",
        retrieved_at="2026-04-23T12:00:00Z",
        source_document_id=f"src_{event_id}",
        source_chunk_id=f"chk_{event_id}",
        source_type="issuer_press_release" if is_official else "recent_development",
        source_rank=source_rank,
        source_title=f"{event_id.replace('_', ' ').title()} source",
        publisher="Fixture Publisher",
        url=f"local://fixtures/qqq/weekly-news/{event_id}",
        source_quality=source_quality,
        allowlist_status=allowlist_status,
        source_use_policy=source_use_policy,
        freshness_state=FreshnessState.fresh,
        is_official=is_official,
        supporting_text=f"Supporting fixture text for {event_id}.",
        asset_relevance=asset_relevance,
        duplicate_group_id=duplicate_of_event_id or event_id,
        duplicate_of_event_id=duplicate_of_event_id,
        is_duplicate=is_duplicate,
        promotional=promotional,
        irrelevant=irrelevant,
    )
