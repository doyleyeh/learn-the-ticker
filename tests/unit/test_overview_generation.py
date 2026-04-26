from pathlib import Path
from typing import Any

from backend.models import (
    AssetStatus,
    EvidenceState,
    FreshnessState,
    MetricValue,
    OverviewResponse,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsContractState,
    WeeklyNewsEventType,
)
from backend.cache import (
    build_cache_key,
    build_generated_output_freshness_input,
    build_knowledge_pack_freshness_input,
    cache_entry_metadata_from_generated_output,
    compute_generated_output_freshness_hash,
    compute_knowledge_pack_freshness_hash,
)
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    InMemoryGeneratedOutputCacheRepository,
    build_generated_output_cache_records,
)
from backend.knowledge_pack_repository import AssetKnowledgePackRepository
from backend.models import CacheEntryKind, CacheKeyMetadata, CacheScope, KnowledgePackFreshnessInput
from backend.overview import (
    OVERVIEW_PERSISTED_READ_BOUNDARY,
    build_overview_section_freshness_validation,
    generate_asset_overview,
    read_persisted_overview_response,
    validate_overview_response,
)
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.safety import find_forbidden_output_phrases
from backend.weekly_news_repository import (
    WeeklyNewsEventCandidateRow,
    WeeklyNewsSourceRankTier,
    acquire_weekly_news_event_evidence_from_fixtures,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeKnowledgePackReader:
    def __init__(self, records_by_ticker):
        self.records_by_ticker = records_by_ticker
        self.requests: list[str] = []

    def read_knowledge_pack_records(self, ticker: str):
        self.requests.append(ticker)
        return self.records_by_ticker.get(ticker)


class FakeGeneratedOutputCacheReader:
    def __init__(self, records_by_ticker):
        self.records_by_ticker = records_by_ticker
        self.requests: list[str] = []

    def read_generated_output_cache_records(self, ticker: str):
        self.requests.append(ticker)
        return self.records_by_ticker.get(ticker)


class FailingGeneratedOutputCacheReader:
    def read_generated_output_cache_records(self, ticker: str):
        raise RuntimeError(f"controlled cache miss for {ticker}")


class FakeWeeklyNewsReader:
    def __init__(self, records_by_ticker):
        self.records_by_ticker = records_by_ticker
        self.requests: list[str] = []

    def read_weekly_news_event_evidence_records(self, ticker: str):
        self.requests.append(ticker)
        return self.records_by_ticker.get(ticker)


def test_supported_asset_overviews_are_schema_valid_and_source_backed():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        overview = generate_asset_overview(ticker)
        validated = OverviewResponse.model_validate(overview.model_dump(mode="json"))
        citation_ids = {citation.citation_id for citation in validated.citations}
        source_ids = {source.source_document_id for source in validated.source_documents}

        assert validated.asset.ticker == ticker
        assert validated.asset.status is AssetStatus.supported
        assert validated.state.status is AssetStatus.supported
        assert validated.freshness.facts_as_of
        assert validated.freshness.recent_events_as_of
        assert validated.beginner_summary is not None
        assert validated.beginner_summary.what_it_is
        assert validated.beginner_summary.why_people_consider_it
        assert validated.beginner_summary.main_catch
        assert len(validated.top_risks) == 3
        assert validated.recent_developments
        assert validated.weekly_news_focus is not None
        assert validated.weekly_news_focus.window.news_window_start == "2026-04-13"
        assert validated.weekly_news_focus.window.news_window_end == "2026-04-22"
        assert validated.weekly_news_focus.configured_max_item_count == 8
        assert validated.weekly_news_focus.selected_item_count == 0
        assert validated.weekly_news_focus.evidence_state is EvidenceState.no_high_signal
        assert validated.weekly_news_focus.evidence_limited_state.value == "empty"
        assert validated.weekly_news_focus.items == []
        assert validated.weekly_news_focus.empty_state is not None
        assert validated.ai_comprehensive_analysis is not None
        assert validated.ai_comprehensive_analysis.analysis_available is False
        assert validated.ai_comprehensive_analysis.minimum_weekly_news_item_count == 2
        assert validated.ai_comprehensive_analysis.weekly_news_selected_item_count == 0
        assert validated.ai_comprehensive_analysis.sections == []
        assert validated.suitability_summary is not None
        assert validated.sections
        assert validated.section_freshness_validation
        assert validated.claims
        assert validated.citations
        assert validated.source_documents
        validation_by_id = {
            item.section_id: item
            for item in validated.section_freshness_validation
        }
        assert {section.section_id for section in validated.sections} <= set(validation_by_id)
        assert {"weekly_news_focus", "ai_comprehensive_analysis"} <= set(validation_by_id)
        assert all(item.validation_outcome.value in {"validated", "validated_with_limitations"} for item in validation_by_id.values())
        assert all(item.diagnostics.derived_from_existing_local_evidence_only is True for item in validation_by_id.values())
        assert _all_citation_ids(validated) <= citation_ids
        assert {citation.source_document_id for citation in validated.citations} <= source_ids
        assert all(source.supporting_passage for source in validated.source_documents)


def test_persisted_overview_read_boundary_prefers_valid_same_asset_records():
    pack_records, cache_records = _persisted_overview_records("VOO")
    pack_reader = FakeKnowledgePackReader({"VOO": pack_records})
    cache_reader = FakeGeneratedOutputCacheReader({"VOO": cache_records})
    fixture = generate_asset_overview("VOO")

    read_result = read_persisted_overview_response(
        "voo",
        persisted_pack_reader=pack_reader,
        generated_output_cache_reader=cache_reader,
    )
    generated = generate_asset_overview(
        "voo",
        persisted_pack_reader=pack_reader,
        generated_output_cache_reader=cache_reader,
    )

    assert OVERVIEW_PERSISTED_READ_BOUNDARY == "overview-persisted-read-boundary-v1"
    assert read_result.status == "found"
    assert read_result.found is True
    assert read_result.diagnostics == ("overview:persisted_hit",)
    assert pack_reader.requests == ["VOO", "VOO"]
    assert cache_reader.requests == ["VOO", "VOO"]
    assert read_result.overview is not None
    assert read_result.overview.model_dump(mode="json") == fixture.model_dump(mode="json")
    assert generated.model_dump(mode="json") == fixture.model_dump(mode="json")


def test_valid_overview_generation_writes_metadata_only_cache_records_when_configured():
    writer = InMemoryGeneratedOutputCacheRepository()
    fixture = generate_asset_overview("VOO")
    generated = generate_asset_overview("VOO", generated_output_cache_writer=writer)
    records = writer.read_asset_overview_records("VOO")

    assert generated.model_dump(mode="json") == fixture.model_dump(mode="json")
    assert records is not None
    envelope = records.envelopes[0]
    assert envelope.asset_ticker == "VOO"
    assert envelope.artifact_category == GeneratedOutputArtifactCategory.asset_overview_section.value
    assert envelope.cacheable is True
    assert envelope.generated_output_available is True
    assert envelope.stores_generated_payload is False
    assert envelope.stores_raw_source_text is False
    assert "unavailable" in set(envelope.section_freshness_labels.values())
    assert set(envelope.citation_ids) <= {citation for row in records.source_checksums for citation in row.citation_ids}


def test_overview_uses_injected_persisted_weekly_news_and_ai_threshold_metadata():
    records = acquire_weekly_news_event_evidence_from_fixtures(
        asset_ticker="QQQ",
        as_of="2026-04-23",
        created_at="2026-04-23T12:00:00Z",
        candidates=[
            _weekly_candidate("official_filing", tier=WeeklyNewsSourceRankTier.official_filing),
            _weekly_candidate("issuer_update", tier=WeeklyNewsSourceRankTier.etf_issuer_announcement, source_rank=3),
        ],
    )
    reader = FakeWeeklyNewsReader({"QQQ": records})

    overview = generate_asset_overview("QQQ", persisted_weekly_news_reader=reader)

    assert reader.requests == ["QQQ"]
    assert overview.weekly_news_focus is not None
    assert overview.weekly_news_focus.selected_item_count == 2
    assert [item.event_id for item in overview.weekly_news_focus.items] == ["official_filing", "issuer_update"]
    assert overview.ai_comprehensive_analysis.analysis_available is True
    assert overview.ai_comprehensive_analysis.weekly_news_selected_item_count == 2
    freshness_by_id = {item.section_id: item for item in overview.section_freshness_validation}
    assert freshness_by_id["weekly_news_focus"].validation_outcome.value in {"validated", "validated_with_limitations"}
    assert freshness_by_id["ai_comprehensive_analysis"].validation_outcome.value in {"validated", "validated_with_limitations"}

    suppressed_threshold = records.ai_thresholds[0].model_copy(
        update={
            "high_signal_selected_item_count": 1,
            "analysis_allowed": False,
            "analysis_state": WeeklyNewsContractState.suppressed.value,
            "suppression_reason_code": "fewer_than_two_high_signal_items",
        }
    )
    suppressed_records = records.model_copy(update={"ai_thresholds": [suppressed_threshold]})
    suppressed = generate_asset_overview(
        "QQQ",
        persisted_weekly_news_reader=FakeWeeklyNewsReader({"QQQ": suppressed_records}),
    )

    assert suppressed.weekly_news_focus is not None
    assert suppressed.weekly_news_focus.selected_item_count == 2
    assert suppressed.ai_comprehensive_analysis.analysis_available is False
    assert suppressed.ai_comprehensive_analysis.weekly_news_selected_item_count == 2
    assert "fewer than two high-signal" in suppressed.ai_comprehensive_analysis.suppression_reason


def test_persisted_overview_falls_back_on_unconfigured_missing_and_failing_readers():
    pack_records, cache_records = _persisted_overview_records("VOO")
    fixture = generate_asset_overview("VOO").model_dump(mode="json")

    assert generate_asset_overview("VOO").model_dump(mode="json") == fixture
    assert (
        generate_asset_overview(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({"VOO": cache_records}),
        ).model_dump(mode="json")
        == fixture
    )
    assert (
        generate_asset_overview(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({"VOO": pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({}),
        ).model_dump(mode="json")
        == fixture
    )
    assert (
        generate_asset_overview(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({"VOO": pack_records}),
            generated_output_cache_reader=FailingGeneratedOutputCacheReader(),
        ).model_dump(mode="json")
        == fixture
    )

    not_configured = read_persisted_overview_response("VOO")
    assert not_configured.status == "not_configured"
    assert not_configured.diagnostics == ("reader:not_configured",)


def test_persisted_overview_rejects_invalid_cache_metadata_and_freshness_mismatch():
    pack_records, cache_records = _persisted_overview_records("VOO")
    fixture = generate_asset_overview("VOO").model_dump(mode="json")
    wrong_hash = cache_records.envelopes[0].model_copy(update={"knowledge_pack_freshness_hash": "stale-hash"})
    stale_without_label = cache_records.envelopes[0].model_copy(
        update={
            "source_freshness_states": {
                cache_records.source_checksums[0].source_document_id: FreshnessState.stale.value
            },
            "section_freshness_labels": {"page": FreshnessState.fresh.value},
        }
    )

    for invalid_records in [
        cache_records.model_copy(update={"envelopes": [wrong_hash]}),
        cache_records.model_copy(update={"envelopes": [stale_without_label]}),
    ]:
        read_result = read_persisted_overview_response(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({"VOO": pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({"VOO": invalid_records}),
        )
        fallback = generate_asset_overview(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({"VOO": pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({"VOO": invalid_records}),
        )

        assert read_result.status == "contract_error"
        assert read_result.overview is None
        assert fallback.model_dump(mode="json") == fixture


def test_persisted_overview_rejects_wrong_asset_sources_citations_and_source_policy_blocks():
    pack_records, cache_records = _persisted_overview_records("VOO")
    fixture = generate_asset_overview("VOO").model_dump(mode="json")

    wrong_asset_source = cache_records.source_checksums[0].model_copy(update={"asset_ticker": "QQQ"})
    wrong_source_records = cache_records.model_copy(
        update={"source_checksums": [wrong_asset_source, *cache_records.source_checksums[1:]]}
    )
    wrong_citation = cache_records.envelopes[0].model_copy(update={"citation_ids": ["c_wrong_asset"]})
    wrong_citation_records = cache_records.model_copy(update={"envelopes": [wrong_citation]})
    source_policy_block = cache_records.source_checksums[0].model_copy(update={"source_use_policy": "metadata_only"})
    source_policy_records = cache_records.model_copy(
        update={"source_checksums": [source_policy_block, *cache_records.source_checksums[1:]]}
    )

    for records in [wrong_source_records, wrong_citation_records, source_policy_records]:
        read_result = read_persisted_overview_response(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({"VOO": pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({"VOO": records}),
        )
        fallback = generate_asset_overview(
            "VOO",
            persisted_pack_reader=FakeKnowledgePackReader({"VOO": pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({"VOO": records}),
        )

        assert read_result.status == "contract_error"
        assert fallback.model_dump(mode="json") == fixture


def test_persisted_overview_blocks_non_generated_asset_states():
    for ticker in ["SPY", "BTC", "ZZZZ"]:
        pack_records = AssetKnowledgePackRepository().serialize(build_asset_knowledge_pack_result(ticker))
        _, cache_records = _persisted_overview_records("VOO")
        result = read_persisted_overview_response(
            ticker,
            persisted_pack_reader=FakeKnowledgePackReader({ticker: pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({ticker: cache_records}),
        )

        assert result.status == "blocked_state"
        assert result.overview is None
        assert generate_asset_overview(
            ticker,
            persisted_pack_reader=FakeKnowledgePackReader({ticker: pack_records}),
            generated_output_cache_reader=FakeGeneratedOutputCacheReader({ticker: cache_records}),
        ).model_dump(mode="json") == generate_asset_overview(ticker).model_dump(mode="json")


def test_persisted_overview_safety_blocks_and_diagnostics_are_sanitized():
    pack_records, cache_records = _persisted_overview_records("VOO")
    unsafe_fact = pack_records.normalized_facts[0].model_copy(update={"value": "You should buy VOO now."})
    unsafe_pack_records = pack_records.model_copy(update={"normalized_facts": [unsafe_fact, *pack_records.normalized_facts[1:]]})

    result = read_persisted_overview_response(
        "VOO",
        persisted_pack_reader=FakeKnowledgePackReader({"VOO": unsafe_pack_records}),
        generated_output_cache_reader=FakeGeneratedOutputCacheReader({"VOO": cache_records}),
    )
    diagnostics_text = " ".join(result.diagnostics)

    assert result.status == "contract_error"
    assert result.overview is None
    assert "You should buy VOO now" not in diagnostics_text
    for forbidden in ["raw_prompt", "raw_model_reasoning", "raw_user_text", "secret", "OPENROUTER"]:
        assert forbidden not in diagnostics_text


def test_generated_overview_citations_validate_against_same_asset_pack():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        pack = build_asset_knowledge_pack(ticker)
        overview = generate_asset_overview(ticker)
        report = validate_overview_response(overview, pack)

        assert report.valid, [issue.message for issue in report.issues]


def test_knowledge_pack_builder_does_not_change_overview_output():
    before = generate_asset_overview("VOO").model_dump(mode="json")
    build_result = build_asset_knowledge_pack_result("VOO")
    after = generate_asset_overview("VOO").model_dump(mode="json")

    assert build_result.build_state.value == "available"
    assert after == before


def test_stock_overview_exposes_prd_sections_with_explicit_gaps():
    overview = generate_asset_overview("AAPL")
    sections = {section.section_id: section for section in overview.sections}

    assert {
        "business_overview",
        "products_services",
        "strengths",
        "financial_quality",
        "valuation_context",
        "top_risks",
        "recent_developments",
        "educational_suitability",
    } <= set(sections)
    assert sections["business_overview"].evidence_state is EvidenceState.supported
    assert sections["products_services"].evidence_state is EvidenceState.mixed
    assert sections["strengths"].evidence_state is EvidenceState.supported
    assert sections["financial_quality"].evidence_state is EvidenceState.mixed
    assert sections["valuation_context"].evidence_state is EvidenceState.mixed
    assert sections["valuation_context"].citation_ids
    assert sections["valuation_context"].source_document_ids
    assert {item.item_id for item in sections["products_services"].items} >= {"products_and_services", "business_segments"}
    assert {item.item_id for item in sections["financial_quality"].items} >= {
        "net_sales_trend",
        "financial_quality_detail_gap",
    }
    assert {item.item_id for item in sections["valuation_context"].items} >= {
        "valuation_data_limitation",
        "valuation_metrics_gap",
    }
    assert sections["top_risks"].items[:3]
    assert len(sections["top_risks"].items) == 3


def test_etf_overviews_expose_prd_sections_and_gap_states():
    required_sections = {
        "fund_objective_role",
        "holdings_exposure",
        "construction_methodology",
        "cost_trading_context",
        "etf_specific_risks",
        "similar_assets_alternatives",
        "recent_developments",
        "educational_suitability",
    }

    for ticker in ["VOO", "QQQ"]:
        overview = generate_asset_overview(ticker)
        sections = {section.section_id: section for section in overview.sections}

        assert required_sections <= set(sections)
        assert sections["fund_objective_role"].evidence_state is EvidenceState.supported
        assert sections["holdings_exposure"].evidence_state is EvidenceState.mixed
        assert sections["construction_methodology"].evidence_state is EvidenceState.mixed
        assert sections["cost_trading_context"].evidence_state is EvidenceState.mixed
        assert "holdings_exposure_detail" in {item.item_id for item in sections["holdings_exposure"].items}
        assert "construction_methodology" in {item.item_id for item in sections["construction_methodology"].items}
        assert "trading_data_limitation" in {item.item_id for item in sections["cost_trading_context"].items}
        assert sections["holdings_exposure"].citation_ids
        assert sections["construction_methodology"].citation_ids
        assert sections["cost_trading_context"].citation_ids
        assert len(sections["etf_specific_risks"].items) == 3
        assert sections["recent_developments"].evidence_state is EvidenceState.no_major_recent_development
        assert sections["recent_developments"].items[0].retrieved_at
        assert sections["recent_developments"].items[0].as_of_date

    voo_sections = {section.section_id: section for section in generate_asset_overview("VOO").sections}
    voo_validation = {
        item.section_id: item
        for item in generate_asset_overview("VOO").section_freshness_validation
    }
    voo_cost_items = {item.item_id: item for item in voo_sections["cost_trading_context"].items}
    qqq_sections = {section.section_id: section for section in generate_asset_overview("QQQ").sections}
    assert voo_cost_items["stale_fee_snapshot_gap"].evidence_state is EvidenceState.stale
    assert voo_validation["cost_trading_context"].displayed_freshness_state.value == "stale"
    assert voo_validation["cost_trading_context"].validated_freshness_state.value == "stale"
    assert voo_validation["cost_trading_context"].validation_outcome.value == "validated_with_limitations"
    assert "evidence_gaps" in voo_validation["cost_trading_context"].diagnostics.matched_knowledge_pack_section_ids
    assert qqq_sections["similar_assets_alternatives"].evidence_state is EvidenceState.insufficient_evidence


def test_new_section_citations_bind_to_same_asset_source_documents():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        overview = generate_asset_overview(ticker)
        citation_ids = {citation.citation_id for citation in overview.citations}
        source_ids = {source.source_document_id for source in overview.source_documents}
        pack_source_ids = {source.source_document_id for source in build_asset_knowledge_pack(ticker).source_documents}

        assert _section_citation_ids(overview) <= citation_ids
        assert _section_source_document_ids(overview) <= source_ids
        assert _section_source_document_ids(overview) <= pack_source_ids


def test_generated_overviews_keep_recent_context_separate_and_explicit():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        overview = generate_asset_overview(ticker)
        recent = overview.recent_developments[0]
        recent_section = next(section for section in overview.sections if section.section_id == "recent_developments")
        freshness_validation = {
            item.section_id: item
            for item in overview.section_freshness_validation
        }

        assert "No high-signal recent development" in recent.title
        assert "recent" not in overview.beginner_summary.what_it_is.lower()
        assert recent.citation_ids
        assert recent.citation_ids[0].startswith("c_recent_")
        assert recent_section.citation_ids == recent.citation_ids
        assert recent_section.items[0].event_date == recent.event_date
        assert overview.weekly_news_focus is not None
        assert overview.weekly_news_focus.stable_facts_are_separate is True
        assert overview.ai_comprehensive_analysis is not None
        assert overview.ai_comprehensive_analysis.stable_facts_are_separate is True
        assert freshness_validation["recent_developments"].displayed_as_of_date == overview.freshness.recent_events_as_of
        assert freshness_validation["weekly_news_focus"].displayed_as_of_date == overview.weekly_news_focus.window.as_of_date
        assert freshness_validation["weekly_news_focus"].validation_outcome.value == "validated_with_limitations"
        assert freshness_validation["ai_comprehensive_analysis"].displayed_as_of_date == overview.freshness.recent_events_as_of
        assert freshness_validation["ai_comprehensive_analysis"].displayed_freshness_state.value == "fresh"
        assert freshness_validation["ai_comprehensive_analysis"].displayed_evidence_state.value == "insufficient_evidence"


def test_unknown_and_unsupported_overviews_do_not_generate_facts_or_citations():
    for ticker, expected_status in [("BTC", AssetStatus.unsupported), ("ZZZZ", AssetStatus.unknown)]:
        overview = generate_asset_overview(ticker)

        assert overview.asset.status is expected_status
        assert overview.state.status is expected_status
        assert overview.snapshot == {}
        assert overview.beginner_summary is None
        assert overview.top_risks == []
        assert overview.recent_developments == []
        assert overview.suitability_summary is None
        assert overview.claims == []
        assert overview.citations == []
        assert overview.source_documents == []
        assert overview.sections == []
        assert overview.section_freshness_validation == []


def test_section_freshness_validation_detects_mismatched_displayed_label():
    pack = build_asset_knowledge_pack("VOO")
    overview = generate_asset_overview("VOO")
    mutated_sections = [
        section.model_copy(update={"freshness_state": FreshnessState.fresh})
        if section.section_id == "cost_trading_context"
        else section
        for section in overview.sections
    ]
    mutated = overview.model_copy(update={"sections": mutated_sections})

    validation = {
        item.section_id: item
        for item in build_overview_section_freshness_validation(
            overview=mutated,
            pack=pack,
        )
    }

    assert validation["cost_trading_context"].displayed_freshness_state.value == "fresh"
    assert validation["cost_trading_context"].validated_freshness_state.value == "stale"
    assert validation["cost_trading_context"].validation_outcome.value == "mismatch"
    assert "displayed_freshness_state_not_supported" in validation["cost_trading_context"].diagnostics.mismatch_reasons


def test_generated_overview_copy_avoids_forbidden_advice_phrases():
    for ticker in ["AAPL", "VOO", "QQQ", "BTC", "ZZZZ"]:
        overview = generate_asset_overview(ticker)
        assert find_forbidden_output_phrases(_flatten_text(overview.model_dump(mode="json"))) == []


def test_overview_generation_module_does_not_import_network_clients():
    overview_source = (ROOT / "backend" / "overview.py").read_text(encoding="utf-8")

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "redis",
        "OPENROUTER",
        "openai",
        "api_key",
    ]:
        assert forbidden not in overview_source


def _all_citation_ids(overview: OverviewResponse) -> set[str]:
    citation_ids: set[str] = set()
    citation_ids.update(citation_id for claim in overview.claims for citation_id in claim.citation_ids)
    citation_ids.update(citation_id for risk in overview.top_risks for citation_id in risk.citation_ids)
    citation_ids.update(
        citation_id for development in overview.recent_developments for citation_id in development.citation_ids
    )
    citation_ids.update(_snapshot_citation_ids(overview.snapshot))
    citation_ids.update(_section_citation_ids(overview))
    return citation_ids


def _section_citation_ids(overview: OverviewResponse) -> set[str]:
    citation_ids: set[str] = set()
    citation_ids.update(citation_id for section in overview.sections for citation_id in section.citation_ids)
    citation_ids.update(
        citation_id for section in overview.sections for item in section.items for citation_id in item.citation_ids
    )
    citation_ids.update(
        citation_id for section in overview.sections for metric in section.metrics for citation_id in metric.citation_ids
    )
    return citation_ids


def _section_source_document_ids(overview: OverviewResponse) -> set[str]:
    source_ids: set[str] = set()
    source_ids.update(source_id for section in overview.sections for source_id in section.source_document_ids)
    source_ids.update(
        source_id for section in overview.sections for item in section.items for source_id in item.source_document_ids
    )
    source_ids.update(
        source_id for section in overview.sections for metric in section.metrics for source_id in metric.source_document_ids
    )
    return source_ids


def _snapshot_citation_ids(snapshot: dict[str, Any]) -> set[str]:
    citation_ids: set[str] = set()
    for value in snapshot.values():
        if isinstance(value, MetricValue):
            citation_ids.update(value.citation_ids)
    return citation_ids


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""


def _weekly_candidate(
    event_id: str,
    *,
    tier: WeeklyNewsSourceRankTier,
    source_rank: int = 1,
) -> WeeklyNewsEventCandidateRow:
    return WeeklyNewsEventCandidateRow(
        candidate_event_id=event_id,
        window_id="wnf_window:QQQ:2026-04-23",
        asset_ticker="QQQ",
        source_asset_ticker="QQQ",
        event_type=WeeklyNewsEventType.methodology_change.value,
        event_date="2026-04-21",
        published_at="2026-04-21T12:00:00Z",
        retrieved_at="2026-04-23T12:00:00Z",
        period_bucket="current_week_to_date",
        source_document_id=f"src_{event_id}",
        source_chunk_id=f"chk_{event_id}",
        citation_ids=[f"c_weekly_{event_id}"],
        citation_asset_tickers={f"c_weekly_{event_id}": "QQQ"},
        source_type=tier.value,
        source_rank=source_rank,
        source_rank_tier=tier.value,
        source_quality=SourceQuality.official.value,
        allowlist_status=SourceAllowlistStatus.allowed.value,
        source_use_policy=SourceUsePolicy.summary_allowed.value,
        freshness_state=FreshnessState.fresh.value,
        evidence_state=EvidenceState.supported.value,
        importance_score=10,
        duplicate_group_id=event_id,
        title_checksum=f"sha256:title:{event_id}",
        evidence_checksum=f"sha256:evidence:{event_id}",
    )


def _persisted_overview_records(ticker: str):
    pack = build_asset_knowledge_pack(ticker)
    response = build_asset_knowledge_pack_result(ticker)
    pack_records = AssetKnowledgePackRepository().serialize(response, retrieval_pack=pack)
    full_knowledge_input = build_knowledge_pack_freshness_input(pack, section_freshness_labels=response.section_freshness)
    full_knowledge_hash = compute_knowledge_pack_freshness_hash(full_knowledge_input)
    cacheable_knowledge_input = KnowledgePackFreshnessInput(
        **{
            **full_knowledge_input.model_dump(mode="json"),
            "source_checksums": [
                checksum
                for checksum in full_knowledge_input.source_checksums
                if checksum.freshness_state is FreshnessState.fresh
            ],
        }
    )
    generated_input = build_generated_output_freshness_input(
        output_identity=f"asset:{ticker}",
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        prompt_version="asset-page-prompt-v1",
        model_name="deterministic-fixture-model",
        knowledge_input=cacheable_knowledge_input,
    )
    generated_hash = compute_generated_output_freshness_hash(generated_input)
    cache_key = build_cache_key(
        CacheKeyMetadata(
            entry_kind=CacheEntryKind.asset_page,
            scope=CacheScope.asset,
            asset_ticker=ticker,
            mode_or_output_type="beginner-overview",
            schema_version="asset-page-v1",
            source_freshness_state=generated_input.source_freshness_state,
            prompt_version="asset-page-prompt-v1",
            model_name="deterministic-fixture-model",
            input_freshness_hash=generated_hash,
        )
    )
    cache_metadata = cache_entry_metadata_from_generated_output(
        cache_key=cache_key,
        freshness_input=generated_input,
        freshness_hash=generated_hash,
        citation_ids=[citation for checksum in generated_input.source_checksums for citation in checksum.citation_ids],
        created_at="2026-04-25T18:20:04Z",
        cache_allowed=True,
        export_allowed=False,
    )
    cache_records = build_generated_output_cache_records(
        cache_entry_id=f"generated-output-{ticker.lower()}-overview",
        output_identity=f"asset:{ticker}",
        mode_or_output_type="beginner-overview",
        artifact_category=GeneratedOutputArtifactCategory.asset_overview_section,
        cache_metadata=cache_metadata,
        generated_freshness_input=generated_input,
        knowledge_freshness_input=cacheable_knowledge_input,
        knowledge_pack_freshness_hash=full_knowledge_hash,
        created_at="2026-04-25T18:20:04Z",
    )
    return pack_records, cache_records
