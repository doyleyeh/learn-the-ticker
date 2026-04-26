from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pytest

from backend.models import (
    EvidenceState,
    FreshnessState,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsEventType,
    WeeklyNewsPeriodBucket,
)
from backend.retrieval import build_asset_knowledge_pack
from backend.weekly_news import (
    WEEKLY_NEWS_PERSISTED_READ_BOUNDARY,
    WeeklyNewsCandidate,
    build_ai_comprehensive_analysis,
    build_weekly_news_focus_from_pack,
    compute_weekly_news_window,
    read_persisted_weekly_news_focus,
    select_weekly_news_focus,
    validate_ai_comprehensive_analysis,
)
from backend.weekly_news_repository import (
    WEEKLY_NEWS_EVENT_EVIDENCE_REPOSITORY_BOUNDARY,
    WEEKLY_NEWS_FIXTURE_ACQUISITION_BOUNDARY,
    WEEKLY_NEWS_LIVE_ACQUISITION_READINESS_BOUNDARY,
    WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY,
    WEEKLY_NEWS_EVENT_EVIDENCE_TABLES,
    WeeklyNewsAIThresholdRow,
    WeeklyNewsDedupeGroupRow,
    WeeklyNewsDiagnosticCategory,
    WeeklyNewsDiagnosticRow,
    WeeklyNewsEventCandidateRow,
    WeeklyNewsEventEvidenceContractError,
    WeeklyNewsEventEvidenceRepository,
    WeeklyNewsEventEvidenceRepositoryRecords,
    WeeklyNewsEvidenceStateRow,
    WeeklyNewsSelectedEventRow,
    WeeklyNewsSourceRankInputRow,
    WeeklyNewsSourceRankTier,
    WeeklyNewsValidationStatusRow,
    WeeklyNewsFixtureAcquisitionBoundary,
    InMemoryWeeklyNewsEventEvidenceRepository,
    acquire_weekly_news_event_evidence_from_official_sources,
    acquire_weekly_news_event_evidence_from_fixtures,
    build_market_week_window_row,
    evaluate_weekly_news_live_acquisition_readiness,
    source_rank_tier_priority,
    validate_weekly_news_event_evidence_records,
    weekly_news_event_evidence_repository_metadata,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeWeeklyNewsReader:
    def __init__(self, records_by_ticker):
        self.records_by_ticker = records_by_ticker
        self.requests: list[str] = []

    def read_weekly_news_event_evidence_records(self, ticker: str):
        self.requests.append(ticker)
        value = self.records_by_ticker.get(ticker)
        if isinstance(value, Exception):
            raise value
        return value


class FakeDurableSession:
    def __init__(self):
        self.records = {}
        self.rows = []
        self.commits = 0

    def save_repository_record(self, collection, key, records):
        self.records[(collection, key)] = records

    def get_repository_record(self, collection, key):
        return self.records.get((collection, key))

    def add_all(self, rows):
        self.rows.extend(rows)

    def commit(self):
        self.commits += 1


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
        assert focus.configured_max_item_count == 8
        assert focus.selected_item_count == 0
        assert focus.suppressed_candidate_count >= 0
        assert focus.evidence_state is EvidenceState.no_high_signal
        assert focus.evidence_limited_state.value == "empty"
        assert focus.items == []
        assert focus.empty_state is not None
        assert focus.empty_state.evidence_state is EvidenceState.no_high_signal
        assert "No major Weekly News Focus items found" in focus.empty_state.message
        assert focus.stable_facts_are_separate is True
        assert analysis.state is WeeklyNewsContractState.suppressed
        assert analysis.analysis_available is False
        assert analysis.minimum_weekly_news_item_count == 2
        assert analysis.weekly_news_selected_item_count == 0
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
    assert focus.configured_max_item_count == 8
    assert focus.selected_item_count == 2
    assert focus.suppressed_candidate_count == 8
    assert focus.evidence_state is EvidenceState.partial
    assert focus.evidence_limited_state.value == "limited_verified_set"
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
    assert suppressed.weekly_news_selected_item_count == 1
    assert suppressed.minimum_weekly_news_item_count == 2

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
    assert analysis.weekly_news_selected_item_count == 2
    assert analysis.minimum_weekly_news_item_count == 2
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


def test_persisted_weekly_news_read_prefers_valid_same_asset_event_evidence():
    asset = build_asset_knowledge_pack("QQQ").asset
    records = _repository_records(
        [
            _repository_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing),
            _repository_candidate("issuer_update", tier=WeeklyNewsSourceRankTier.etf_issuer_announcement, source_rank=3),
        ]
    )
    reader = FakeWeeklyNewsReader({"QQQ": records})

    result = read_persisted_weekly_news_focus(asset, as_of="2026-04-23", persisted_event_reader=reader)
    focus = build_weekly_news_focus_from_pack(
        build_asset_knowledge_pack("QQQ"),
        as_of="2026-04-23",
        persisted_event_reader=reader,
    )

    assert WEEKLY_NEWS_PERSISTED_READ_BOUNDARY == "weekly-news-persisted-read-boundary-v1"
    assert result.status == "found"
    assert result.found is True
    assert result.diagnostics == ("weekly_news:persisted_hit",)
    assert reader.requests == ["QQQ", "QQQ"]
    assert result.weekly_news_focus is not None
    assert result.weekly_news_focus.selected_item_count == 2
    assert result.weekly_news_focus.suppressed_candidate_count == 0
    assert result.weekly_news_focus.evidence_limited_state.value == "limited_verified_set"
    assert [item.event_id for item in result.weekly_news_focus.items] == ["official_filing", "issuer_update"]
    assert all(item.asset_ticker == "QQQ" for item in result.weekly_news_focus.items)
    assert all(item.period_bucket is WeeklyNewsPeriodBucket.current_week_to_date for item in result.weekly_news_focus.items)
    assert all(item.source.allowlist_status is SourceAllowlistStatus.allowed for item in result.weekly_news_focus.items)
    assert all(
        item.source.source_use_policy in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed}
        for item in result.weekly_news_focus.items
    )
    assert result.high_signal_selected_item_count == 2
    assert {citation.citation_id for citation in result.weekly_news_focus.citations} == {
        "c_weekly_official_filing",
        "c_weekly_issuer_update",
    }
    assert focus.model_dump(mode="json") == result.weekly_news_focus.model_dump(mode="json")


def test_in_memory_weekly_news_repository_persists_and_reads_validated_golden_records():
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[
            _repository_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing),
            _repository_candidate("issuer_update", tier=WeeklyNewsSourceRankTier.etf_issuer_announcement, source_rank=3),
        ],
    )
    repository = InMemoryWeeklyNewsEventEvidenceRepository()

    persisted = repository.persist(records)
    read_back = repository.read_weekly_news_event_evidence_records("qqq")

    assert persisted == records
    assert read_back == records
    assert repository.read("QQQ") == records
    assert repository.get("QQQ") == records
    assert repository.read_weekly_news_event_evidence_records("VOO") is None
    assert read_back is not None
    read_back.windows[0].asset_ticker = "AAPL"
    assert repository.read_weekly_news_event_evidence_records("QQQ").windows[0].asset_ticker == "QQQ"

    focus = read_persisted_weekly_news_focus(
        build_asset_knowledge_pack("QQQ").asset,
        as_of="2026-04-23",
        persisted_event_reader=repository,
    )
    assert focus.found is True
    assert focus.weekly_news_focus is not None
    assert [item.event_id for item in focus.weekly_news_focus.items] == ["official_filing", "issuer_update"]
    assert focus.high_signal_selected_item_count == 2


def test_durable_weekly_news_repository_persists_and_reads_validated_evidence():
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[
            _repository_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing),
            _repository_candidate("issuer_update", tier=WeeklyNewsSourceRankTier.etf_issuer_announcement, source_rank=3),
        ],
    )
    session = FakeDurableSession()
    repository = WeeklyNewsEventEvidenceRepository(session=session, commit_on_write=True)

    persisted = repository.persist(records)
    read_back = repository.read_weekly_news_event_evidence_records("qqq")

    assert persisted == records
    assert read_back == records
    assert repository.read("QQQ") == records
    assert repository.get("QQQ") == records
    assert session.records[("weekly_news_event_evidence", "QQQ")] == records
    assert session.commits == 1


def test_persisted_weekly_news_read_falls_back_on_miss_failure_invalid_and_wrong_asset_records():
    asset = build_asset_knowledge_pack("QQQ").asset
    fixture = build_weekly_news_focus_from_pack(build_asset_knowledge_pack("QQQ"), as_of="2026-04-23").model_dump(mode="json")

    assert read_persisted_weekly_news_focus(asset, as_of="2026-04-23").status == "not_configured"
    assert (
        build_weekly_news_focus_from_pack(
            build_asset_knowledge_pack("QQQ"),
            as_of="2026-04-23",
            persisted_event_reader=FakeWeeklyNewsReader({}),
        ).model_dump(mode="json")
        == fixture
    )
    assert (
        build_weekly_news_focus_from_pack(
            build_asset_knowledge_pack("QQQ"),
            as_of="2026-04-23",
            persisted_event_reader=FakeWeeklyNewsReader({"QQQ": RuntimeError("controlled weekly reader failure")}),
        ).model_dump(mode="json")
        == fixture
    )

    wrong_asset_records = _repository_records([_repository_candidate("wrong_asset")])
    wrong_asset_records.windows[0].asset_ticker = "AAPL"
    invalid = read_persisted_weekly_news_focus(
        asset,
        as_of="2026-04-23",
        persisted_event_reader=FakeWeeklyNewsReader({"QQQ": wrong_asset_records}),
    )
    assert invalid.status in {"contract_error", "reader_error"}
    assert "controlled weekly reader failure" not in " ".join(invalid.diagnostics)
    assert (
        build_weekly_news_focus_from_pack(
            build_asset_knowledge_pack("QQQ"),
            as_of="2026-04-23",
            persisted_event_reader=FakeWeeklyNewsReader({"QQQ": wrong_asset_records}),
        ).model_dump(mode="json")
        == fixture
    )


def test_persisted_weekly_news_empty_and_limited_states_do_not_pad_items():
    asset = build_asset_knowledge_pack("QQQ").asset
    empty_records = _repository_records([], include_selected=False)
    limited_records = _repository_records([_repository_candidate("single_official")])

    empty = read_persisted_weekly_news_focus(
        asset,
        as_of="2026-04-23",
        persisted_event_reader=FakeWeeklyNewsReader({"QQQ": empty_records}),
    )
    limited = read_persisted_weekly_news_focus(
        asset,
        as_of="2026-04-23",
        persisted_event_reader=FakeWeeklyNewsReader({"QQQ": limited_records}),
    )

    assert empty.found is True
    assert empty.weekly_news_focus is not None
    assert empty.weekly_news_focus.items == []
    assert empty.weekly_news_focus.empty_state is not None
    assert empty.weekly_news_focus.evidence_limited_state.value == "empty"
    assert empty.high_signal_selected_item_count == 0

    assert limited.found is True
    assert limited.weekly_news_focus is not None
    assert [item.event_id for item in limited.weekly_news_focus.items] == ["single_official"]
    assert limited.weekly_news_focus.selected_item_count == 1
    assert limited.weekly_news_focus.configured_max_item_count == 8
    assert limited.weekly_news_focus.evidence_limited_state.value == "limited_verified_set"
    assert limited.high_signal_selected_item_count == 1


def test_persisted_weekly_news_rejects_disconnected_threshold_and_sanitizes_diagnostics():
    asset = build_asset_knowledge_pack("QQQ").asset
    records = _repository_records([_repository_candidate("official_filing")])
    records.ai_thresholds[0].selected_event_ids = []

    result = read_persisted_weekly_news_focus(
        asset,
        as_of="2026-04-23",
        persisted_event_reader=FakeWeeklyNewsReader({"QQQ": records}),
    )

    assert result.status == "contract_error"
    assert result.weekly_news_focus is None
    diagnostics = " ".join(result.diagnostics)
    for forbidden in ["raw_article", "provider_payload", "raw_user_text", "secret", "https://"]:
        assert forbidden not in diagnostics


def test_fixture_acquisition_boundary_selects_ranked_deduped_weekly_news_evidence():
    candidates = [
        _repository_candidate("allowlisted_context", tier=WeeklyNewsSourceRankTier.allowlisted_news, source_rank=20, source_quality=SourceQuality.allowlisted),
        _repository_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing, source_rank=1),
        _repository_candidate(
            "duplicate_context",
            tier=WeeklyNewsSourceRankTier.allowlisted_news,
            source_rank=20,
            source_quality=SourceQuality.allowlisted,
            duplicate_group_id="allowlisted_context",
        ),
        _repository_candidate("metadata_only", source_use_policy=SourceUsePolicy.metadata_only),
        _repository_candidate("rejected_source", source_use_policy=SourceUsePolicy.rejected, allowlist_status=SourceAllowlistStatus.rejected, source_quality=SourceQuality.rejected),
        _repository_candidate("not_allowlisted", allowlist_status=SourceAllowlistStatus.not_allowlisted),
        _repository_candidate("promotional", promotional=True),
        _repository_candidate("irrelevant", irrelevant=True),
        _repository_candidate("outside_window", event_date="2026-04-01"),
        _repository_candidate("wrong_asset").model_copy(update={"asset_ticker": "AAPL", "source_asset_ticker": "AAPL"}),
    ]

    records = WeeklyNewsFixtureAcquisitionBoundary().select(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=candidates,
    )

    assert WEEKLY_NEWS_FIXTURE_ACQUISITION_BOUNDARY == "weekly-news-fixture-acquisition-boundary-v1"
    assert validate_weekly_news_event_evidence_records(records) == records
    assert [row.candidate_event_id for row in records.selected_events] == ["official_filing", "allowlisted_context"]
    assert records.evidence_states[0].selected_item_count == 2
    assert records.evidence_states[0].suppressed_candidate_count == 8
    assert records.evidence_states[0].evidence_limited_state == "limited_verified_set"
    assert records.ai_thresholds[0].analysis_allowed is True
    assert records.ai_thresholds[0].selected_item_count == 2
    assert records.ai_thresholds[0].high_signal_selected_item_count == 2
    assert records.dedupe_groups
    assert any(row.duplicate_candidate_event_ids == ["duplicate_context"] for row in records.dedupe_groups)

    suppressed = {row.candidate_event_id: row.suppression_reason_codes for row in records.candidates if row.candidate_decision == "suppressed"}
    assert "source_policy_blocked" in suppressed["metadata_only"]
    assert "rejected_source" in suppressed["rejected_source"]
    assert "non_allowlisted_source" in suppressed["not_allowlisted"]
    assert "promotional" in suppressed["promotional"]
    assert "irrelevant" in suppressed["irrelevant"]
    assert "outside_market_week_window" in suppressed["outside_window"]
    assert "duplicate" in suppressed["duplicate_context"]
    assert "wrong_asset" not in {row.candidate_event_id for row in records.candidates}

    diagnostic = records.diagnostics[0]
    assert diagnostic.compact_metadata["skipped_wrong_asset_count"] == 1
    assert diagnostic.compact_metadata["selected_count"] == 2
    assert "AAPL" not in repr(diagnostic)
    assert all(row.stores_raw_article_text is False for row in records.candidates)
    assert all(row.stores_raw_provider_payload is False for row in records.candidates)
    assert all(row.stores_unrestricted_source_text is False for row in records.candidates)
    assert diagnostic.stores_hidden_prompt is False
    assert diagnostic.stores_secret is False
    assert "https://" not in repr(records).lower()


def test_fixture_acquisition_boundary_supports_empty_limited_and_ai_threshold_states():
    empty = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="VOO",
        as_of="2026-04-20",
        created_at="2026-04-20T12:00:00Z",
        candidates=[
            _repository_candidate("future_item", event_date="2026-04-20").model_copy(
                update={"asset_ticker": "VOO", "source_asset_ticker": "VOO", "citation_asset_tickers": {"c_weekly_future_item": "VOO"}}
            )
        ],
    )

    assert empty.windows[0].news_window_end == "2026-04-19"
    assert empty.selected_events == []
    assert empty.evidence_states[0].empty_state_valid is True
    assert empty.evidence_states[0].evidence_limited_state == "empty"
    assert empty.ai_thresholds[0].analysis_allowed is False
    assert empty.ai_thresholds[0].suppression_reason_code == "fewer_than_two_high_signal_items"

    one_item = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[_repository_candidate("only_one")],
    )

    assert one_item.selected_events[0].selected_item_count == 1
    assert one_item.evidence_states[0].limited_state_valid is True
    assert one_item.ai_thresholds[0].analysis_allowed is False
    assert one_item.ai_thresholds[0].high_signal_selected_item_count == 1


def test_weekly_news_live_acquisition_readiness_is_explicit_and_sanitized():
    candidates = [_repository_candidate("official_filing")]

    blocked = evaluate_weekly_news_live_acquisition_readiness("QQQ", candidates=candidates)
    ready = evaluate_weekly_news_live_acquisition_readiness(
        "QQQ",
        opt_in_enabled=True,
        official_source_configured=True,
        rate_limit_ready=True,
        repository_writer_ready=True,
        candidates=candidates,
    )
    unsupported = evaluate_weekly_news_live_acquisition_readiness(
        "TQQQ",
        opt_in_enabled=True,
        official_source_configured=True,
        rate_limit_ready=True,
        repository_writer_ready=True,
        candidates=[],
    )
    invalid_source = evaluate_weekly_news_live_acquisition_readiness(
        "QQQ",
        opt_in_enabled=True,
        official_source_configured=True,
        rate_limit_ready=True,
        repository_writer_ready=True,
        candidates=[_repository_candidate("allowlisted_news", tier=WeeklyNewsSourceRankTier.allowlisted_news, source_rank=20)],
    )

    assert blocked.boundary == WEEKLY_NEWS_LIVE_ACQUISITION_READINESS_BOUNDARY
    assert blocked.status == "blocked"
    assert blocked.can_attempt_live_acquisition is False
    assert "explicit_live_weekly_news_acquisition_opt_in_missing" in blocked.blocked_reasons
    assert "weekly_news_evidence_repository_writer_not_ready" in blocked.blocked_reasons
    assert ready.status == "ready"
    assert ready.can_attempt_live_acquisition is True
    assert unsupported.status == "blocked"
    assert "unsupported_asset" in unsupported.blocked_reasons
    assert invalid_source.status == "blocked"
    assert "official_source_use_validation_failed" in invalid_source.blocked_reasons

    serialized = repr(ready.sanitized_diagnostics)
    for forbidden in ["raw_article", "provider_payload", "raw_user_text", "secret", "https://"]:
        assert forbidden not in serialized


def test_weekly_news_official_source_live_acquisition_uses_mocked_golden_paths_only():
    candidates = [
        _repository_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing, source_rank=1),
        _repository_candidate("investor_relations", tier=WeeklyNewsSourceRankTier.investor_relations_release, source_rank=2),
        _repository_candidate("duplicate", tier=WeeklyNewsSourceRankTier.investor_relations_release, source_rank=3, duplicate_group_id="investor_relations"),
        _repository_candidate("promotional", tier=WeeklyNewsSourceRankTier.official_filing, promotional=True),
        _repository_candidate("metadata_only", tier=WeeklyNewsSourceRankTier.official_filing, source_use_policy=SourceUsePolicy.metadata_only),
        _repository_candidate("outside_window", tier=WeeklyNewsSourceRankTier.official_filing, event_date="2026-04-01"),
    ]

    result = acquire_weekly_news_event_evidence_from_official_sources(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=candidates,
        opt_in_enabled=True,
        official_source_configured=True,
        rate_limit_ready=True,
        repository_writer_ready=True,
    )

    assert result.boundary == WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY
    assert result.status == "acquired"
    assert result.readiness.can_attempt_live_acquisition is True
    assert result.records is not None
    assert validate_weekly_news_event_evidence_records(result.records) == result.records
    assert [row.candidate_event_id for row in result.records.selected_events] == ["official_filing", "investor_relations"]
    assert result.selected_event_count == 2
    assert result.evidence_limited_state == "limited_verified_set"
    assert result.ai_analysis_allowed is True
    assert result.records.evidence_states[0].selected_item_count == 2
    assert result.records.evidence_states[0].configured_max_item_count == 8
    assert result.records.ai_thresholds[0].analysis_allowed is True
    assert result.records.diagnostics[0].compact_metadata["selected_count"] == 2
    suppressed = {row.candidate_event_id: row.suppression_reason_codes for row in result.records.candidates if row.candidate_decision == "suppressed"}
    assert "duplicate" in suppressed["duplicate"]
    assert "promotional" in suppressed["promotional"]
    assert "source_policy_blocked" in suppressed["metadata_only"]
    assert "outside_market_week_window" in suppressed["outside_window"]
    assert "https://" not in repr(result.sanitized_diagnostics).lower()


def test_weekly_news_official_source_live_acquisition_covers_aapl_voo_and_qqq_states():
    cases = {
        "AAPL": [
            _repository_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing).model_copy(
                update={
                    "asset_ticker": "AAPL",
                    "source_asset_ticker": "AAPL",
                    "citation_asset_tickers": {"c_weekly_official_filing": "AAPL"},
                }
            )
        ],
        "VOO": [
            _repository_candidate("issuer_announcement", tier=WeeklyNewsSourceRankTier.etf_issuer_announcement).model_copy(
                update={
                    "asset_ticker": "VOO",
                    "source_asset_ticker": "VOO",
                    "citation_asset_tickers": {"c_weekly_issuer_announcement": "VOO"},
                    "source_quality": SourceQuality.issuer.value,
                }
            ),
            _repository_candidate("fact_sheet", tier=WeeklyNewsSourceRankTier.fact_sheet_change).model_copy(
                update={
                    "asset_ticker": "VOO",
                    "source_asset_ticker": "VOO",
                    "citation_asset_tickers": {"c_weekly_fact_sheet": "VOO"},
                    "source_quality": SourceQuality.issuer.value,
                }
            ),
        ],
        "QQQ": [
            _repository_candidate("prospectus", tier=WeeklyNewsSourceRankTier.prospectus_update).model_copy(
                update={"source_quality": SourceQuality.issuer.value}
            )
        ],
    }

    results = {
        ticker: acquire_weekly_news_event_evidence_from_official_sources(
            asset_ticker=ticker,
            as_of="2026-04-23",
            created_at="2026-04-23T12:00:00Z",
            candidates=candidates,
            opt_in_enabled=True,
            official_source_configured=True,
            rate_limit_ready=True,
            repository_writer_ready=True,
        )
        for ticker, candidates in cases.items()
    }

    assert results["AAPL"].status == "acquired"
    assert results["AAPL"].selected_event_count == 1
    assert results["AAPL"].ai_analysis_allowed is False
    assert results["VOO"].selected_event_count == 2
    assert results["VOO"].ai_analysis_allowed is True
    assert results["QQQ"].selected_event_count == 1
    assert results["QQQ"].evidence_limited_state == "limited_verified_set"
    assert all(result.records is not None for result in results.values())


def test_weekly_news_official_source_live_acquisition_blocks_invalid_checksum_and_missing_opt_in():
    invalid = _repository_candidate("bad_checksum")
    invalid.evidence_checksum = "md5:not-allowed"

    blocked = acquire_weekly_news_event_evidence_from_official_sources(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[_repository_candidate("official_filing")],
    )
    bad_checksum = acquire_weekly_news_event_evidence_from_official_sources(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[invalid],
        opt_in_enabled=True,
        official_source_configured=True,
        rate_limit_ready=True,
        repository_writer_ready=True,
    )

    assert blocked.status == "blocked"
    assert blocked.records is None
    assert "explicit_live_weekly_news_acquisition_opt_in_missing" in blocked.readiness.blocked_reasons
    assert bad_checksum.status == "blocked"
    assert bad_checksum.records is None
    assert "official_source_use_validation_failed" in bad_checksum.readiness.blocked_reasons


def test_weekly_news_module_does_not_import_live_network_clients():
    source = (ROOT / "backend" / "weekly_news.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in source

    repository_source = (ROOT / "backend" / "repositories" / "weekly_news.py").read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in repository_source


def test_weekly_news_event_evidence_repository_metadata_and_migration_are_inspectable():
    metadata = weekly_news_event_evidence_repository_metadata()

    assert metadata.boundary == WEEKLY_NEWS_EVENT_EVIDENCE_REPOSITORY_BOUNDARY
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == WEEKLY_NEWS_EVENT_EVIDENCE_TABLES
    assert metadata.tables["weekly_news_event_candidates"].primary_key == ("candidate_event_id",)
    assert "source_use_policy" in metadata.tables["weekly_news_selected_events"].columns
    assert "suppression_reason_codes" in metadata.tables["weekly_news_diagnostics"].columns

    migration_path = ROOT / "alembic" / "versions" / "20260425_0008_weekly_news_event_evidence_contracts.py"
    spec = importlib.util.spec_from_file_location("weekly_news_event_evidence_contracts", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0008"
    assert module.down_revision == "20260425_0007"
    assert module.WEEKLY_NEWS_EVENT_EVIDENCE_TABLE_NAMES == WEEKLY_NEWS_EVENT_EVIDENCE_TABLES


def test_weekly_news_event_evidence_contract_validates_limited_state_and_ai_threshold():
    records = _repository_records([_repository_candidate("official_filing"), _repository_candidate("allowlisted_news", tier=WeeklyNewsSourceRankTier.allowlisted_news, source_rank=20)])
    validated = validate_weekly_news_event_evidence_records(records)

    assert validated.table_names == WEEKLY_NEWS_EVENT_EVIDENCE_TABLES
    assert validated.windows[0].previous_market_week_start == "2026-04-13"
    assert validated.windows[0].current_week_to_date_end == "2026-04-22"
    assert [row.candidate_event_id for row in validated.selected_events] == ["official_filing", "allowlisted_news"]
    assert validated.evidence_states[0].evidence_limited_state == "limited_verified_set"
    assert validated.evidence_states[0].limited_state_valid is True
    assert validated.ai_thresholds[0].analysis_allowed is True
    assert validated.ai_thresholds[0].analysis_state == "available"


def test_weekly_news_event_evidence_contract_supports_empty_state_without_padding():
    window = build_market_week_window_row(asset_ticker="VOO", as_of="2026-04-23", created_at="2026-04-23T12:00:00Z")
    records = WeeklyNewsEventEvidenceRepositoryRecords(
        windows=[window],
        evidence_states=[
            WeeklyNewsEvidenceStateRow(
                evidence_state_id="empty:VOO",
                window_id=window.window_id,
                asset_ticker="VOO",
                state=WeeklyNewsContractState.no_high_signal.value,
                evidence_state=EvidenceState.no_high_signal.value,
                evidence_limited_state="empty",
                configured_max_item_count=8,
                selected_item_count=0,
                suppressed_candidate_count=0,
                empty_state_valid=True,
                missing_evidence_label="no_high_signal",
                created_at="2026-04-23T12:00:00Z",
            )
        ],
        ai_thresholds=[
            WeeklyNewsAIThresholdRow(
                threshold_id="threshold:VOO",
                window_id=window.window_id,
                asset_ticker="VOO",
                selected_item_count=0,
                high_signal_selected_item_count=0,
                analysis_allowed=False,
                analysis_state=WeeklyNewsContractState.suppressed.value,
                suppression_reason_code="fewer_than_two_high_signal_items",
                created_at="2026-04-23T12:00:00Z",
            )
        ],
    )

    validated = validate_weekly_news_event_evidence_records(records)

    assert validated.selected_events == []
    assert validated.evidence_states[0].empty_state_valid is True
    assert validated.ai_thresholds[0].analysis_allowed is False


def test_weekly_news_event_evidence_rejects_blocked_wrong_asset_and_unlabeled_records():
    blocked = _repository_records(
        [
            _repository_candidate(
                "metadata_only",
                source_use_policy=SourceUsePolicy.metadata_only,
                suppression_reason_codes=["source_policy_blocked"],
            )
        ]
    )
    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="source-policy"):
        validate_weekly_news_event_evidence_records(blocked)

    wrong_asset = _repository_records([_repository_candidate("wrong_asset", source_asset_ticker="AAPL")], include_selected=False)
    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="same-asset"):
        validate_weekly_news_event_evidence_records(wrong_asset)

    stale_without_label = _repository_records(
        [
            _repository_candidate(
                "stale_without_label",
                freshness_state=FreshnessState.stale,
                evidence_state=EvidenceState.supported,
            )
        ],
        include_selected=False,
    )
    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="stale label"):
        validate_weekly_news_event_evidence_records(stale_without_label)


def test_weekly_news_event_evidence_rejects_duplicate_selected_items_and_bad_counts():
    duplicate = _repository_records(
        [
            _repository_candidate("first"),
            _repository_candidate("second"),
        ],
        canonical_event_key="QQQ:methodology:2026-04-21:same",
    )
    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="Duplicate selected"):
        validate_weekly_news_event_evidence_records(duplicate)

    malformed_counts = _repository_records([_repository_candidate("one")])
    malformed_counts.selected_events[0].selected_item_count = 2
    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="selected-vs-configured"):
        validate_weekly_news_event_evidence_records(malformed_counts)


def test_weekly_news_event_evidence_rejects_unsanitized_diagnostics_and_live_flags():
    records = _repository_records([_repository_candidate("official_filing")])
    records.diagnostics.append(
        WeeklyNewsDiagnosticRow(
            diagnostic_id="diag:bad",
            window_id=records.windows[0].window_id,
            category=WeeklyNewsDiagnosticCategory.privacy.value,
            code="raw_article_body",
            created_at="2026-04-23T12:00:00Z",
            compact_metadata={"raw_article_body": "unrestricted article body"},
        )
    )

    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="sanitized"):
        validate_weekly_news_event_evidence_records(records)

    live = _repository_records([_repository_candidate("official_filing")])
    live.windows[0].provider_or_llm_call_required = True
    with pytest.raises(WeeklyNewsEventEvidenceContractError, match="dormant"):
        validate_weekly_news_event_evidence_records(live)


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


def _repository_candidate(
    event_id: str,
    *,
    tier: WeeklyNewsSourceRankTier = WeeklyNewsSourceRankTier.official_filing,
    source_rank: int = 1,
    source_quality: SourceQuality = SourceQuality.official,
    source_use_policy: SourceUsePolicy = SourceUsePolicy.summary_allowed,
    allowlist_status: SourceAllowlistStatus = SourceAllowlistStatus.allowed,
    source_asset_ticker: str = "QQQ",
    freshness_state: FreshnessState = FreshnessState.fresh,
    evidence_state: EvidenceState = EvidenceState.supported,
    event_date: str = "2026-04-21",
    duplicate_group_id: str | None = None,
    promotional: bool = False,
    irrelevant: bool = False,
    suppression_reason_codes: list[str] | None = None,
) -> WeeklyNewsEventCandidateRow:
    return WeeklyNewsEventCandidateRow(
        candidate_event_id=event_id,
        window_id="wnf_window:QQQ:2026-04-23",
        asset_ticker="QQQ",
        source_asset_ticker=source_asset_ticker,
        event_type=WeeklyNewsEventType.methodology_change.value,
        event_date=event_date,
        published_at=f"{event_date}T12:00:00Z",
        retrieved_at="2026-04-23T12:00:00Z",
        period_bucket="current_week_to_date",
        source_document_id=f"src_{event_id}",
        source_chunk_id=f"chk_{event_id}",
        citation_ids=[f"c_weekly_{event_id}"],
        citation_asset_tickers={f"c_weekly_{event_id}": "QQQ"},
        source_type=tier.value,
        source_rank=source_rank,
        source_rank_tier=tier.value,
        source_quality=source_quality.value,
        allowlist_status=allowlist_status.value,
        source_use_policy=source_use_policy.value,
        freshness_state=freshness_state.value,
        evidence_state=evidence_state.value,
        importance_score=10,
        promotional=promotional,
        irrelevant=irrelevant,
        duplicate_group_id=duplicate_group_id or event_id,
        candidate_decision="selected",
        suppression_reason_codes=suppression_reason_codes or [],
        title_checksum=f"sha256:title:{event_id}",
        evidence_checksum=f"sha256:evidence:{event_id}",
    )


def _repository_records(
    candidates: list[WeeklyNewsEventCandidateRow],
    *,
    include_selected: bool = True,
    canonical_event_key: str | None = None,
) -> WeeklyNewsEventEvidenceRepositoryRecords:
    window = build_market_week_window_row(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
    )
    selected_events = [
        WeeklyNewsSelectedEventRow(
            selected_event_id=f"selected:{candidate.candidate_event_id}",
            candidate_event_id=candidate.candidate_event_id,
            window_id=window.window_id,
            asset_ticker=candidate.asset_ticker,
            event_type=candidate.event_type,
            period_bucket=candidate.period_bucket,
            event_date=candidate.event_date,
            published_at=candidate.published_at,
            retrieved_at=candidate.retrieved_at,
            source_document_id=candidate.source_document_id,
            source_chunk_id=candidate.source_chunk_id,
            citation_ids=candidate.citation_ids,
            citation_asset_tickers=candidate.citation_asset_tickers,
            source_quality=candidate.source_quality,
            allowlist_status=candidate.allowlist_status,
            source_use_policy=candidate.source_use_policy,
            freshness_state=candidate.freshness_state,
            evidence_state=candidate.evidence_state,
            importance_score=candidate.importance_score,
            rank_position=index,
            configured_max_item_count=8,
            selected_item_count=len(candidates),
            suppressed_candidate_count=0,
            dedupe_group_id=candidate.duplicate_group_id,
            canonical_event_key=canonical_event_key or f"QQQ:methodology:2026-04-21:{candidate.candidate_event_id}",
        )
        for index, candidate in enumerate(candidates, start=1)
    ] if include_selected else []
    selected_count = len(selected_events)
    evidence_limited_state = "empty" if selected_count == 0 else "limited_verified_set"
    return WeeklyNewsEventEvidenceRepositoryRecords(
        windows=[window],
        candidates=candidates,
        source_rank_inputs=[
            WeeklyNewsSourceRankInputRow(
                candidate_event_id=candidate.candidate_event_id,
                window_id=window.window_id,
                asset_ticker=candidate.asset_ticker,
                source_rank_tier=candidate.source_rank_tier,
                source_rank=candidate.source_rank,
                source_quality_weight=5,
                event_type_weight=5,
                recency_weight=3,
                asset_relevance_weight=3,
                total_score=16,
                selected_by_score=True,
                source_policy_allowed=candidate.source_use_policy in {SourceUsePolicy.summary_allowed.value, SourceUsePolicy.full_text_allowed.value}
                and candidate.allowlist_status == SourceAllowlistStatus.allowed.value,
                created_at="2026-04-23T12:00:00Z",
            )
            for candidate in candidates
        ],
        dedupe_groups=[
            WeeklyNewsDedupeGroupRow(
                dedupe_group_id=candidate.duplicate_group_id or candidate.candidate_event_id,
                window_id=window.window_id,
                asset_ticker=candidate.asset_ticker,
                canonical_event_key=canonical_event_key or f"QQQ:methodology:2026-04-21:{candidate.candidate_event_id}",
                retained_candidate_event_id=candidate.candidate_event_id,
                created_at="2026-04-23T12:00:00Z",
            )
            for candidate in candidates
        ],
        selected_events=selected_events,
        evidence_states=[
            WeeklyNewsEvidenceStateRow(
                evidence_state_id="evidence:QQQ",
                window_id=window.window_id,
                asset_ticker="QQQ",
                state=WeeklyNewsContractState.available.value if selected_count else WeeklyNewsContractState.no_high_signal.value,
                evidence_state=EvidenceState.partial.value if selected_count else EvidenceState.no_high_signal.value,
                evidence_limited_state=evidence_limited_state,
                configured_max_item_count=8,
                selected_item_count=selected_count,
                suppressed_candidate_count=0,
                empty_state_valid=selected_count == 0,
                limited_state_valid=0 < selected_count < 8,
                missing_evidence_label=None if selected_count else "no_high_signal",
                created_at="2026-04-23T12:00:00Z",
            )
        ],
        ai_thresholds=[
            WeeklyNewsAIThresholdRow(
                threshold_id="threshold:QQQ",
                window_id=window.window_id,
                asset_ticker="QQQ",
                selected_item_count=selected_count,
                high_signal_selected_item_count=selected_count,
                analysis_allowed=selected_count >= 2,
                analysis_state=WeeklyNewsContractState.available.value if selected_count >= 2 else WeeklyNewsContractState.suppressed.value,
                suppression_reason_code=None if selected_count >= 2 else "fewer_than_two_high_signal_items",
                selected_event_ids=[row.selected_event_id for row in selected_events],
                created_at="2026-04-23T12:00:00Z",
            )
        ],
        validation_statuses=[
            WeeklyNewsValidationStatusRow(
                validation_id="validation:QQQ",
                window_id=window.window_id,
                subject_type="window",
                subject_id=window.window_id,
                validated_at="2026-04-23T12:00:00Z",
            )
        ],
        diagnostics=[
            WeeklyNewsDiagnosticRow(
                diagnostic_id="diag:QQQ",
                window_id=window.window_id,
                category=WeeklyNewsDiagnosticCategory.ranking.value,
                code="rank_inputs_recorded",
                created_at="2026-04-23T12:00:00Z",
                compact_metadata={"selected_count": selected_count, "source_priority": source_rank_tier_priority(candidates[0].source_rank_tier) if candidates else 0},
                event_ids=[candidate.candidate_event_id for candidate in candidates],
                rank_inputs={"configured_max_item_count": 8},
            )
        ],
    )
