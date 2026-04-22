from pathlib import Path
from typing import Any

from backend.models import AssetStatus, EvidenceState, MetricValue, OverviewResponse
from backend.overview import generate_asset_overview, validate_overview_response
from backend.retrieval import build_asset_knowledge_pack, build_asset_knowledge_pack_result
from backend.safety import find_forbidden_output_phrases


ROOT = Path(__file__).resolve().parents[2]


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
        assert validated.suitability_summary is not None
        assert validated.sections
        assert validated.claims
        assert validated.citations
        assert validated.source_documents
        assert _all_citation_ids(validated) <= citation_ids
        assert {citation.source_document_id for citation in validated.citations} <= source_ids
        assert all(source.supporting_passage for source in validated.source_documents)


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
    voo_cost_items = {item.item_id: item for item in voo_sections["cost_trading_context"].items}
    qqq_sections = {section.section_id: section for section in generate_asset_overview("QQQ").sections}
    assert voo_cost_items["stale_fee_snapshot_gap"].evidence_state is EvidenceState.stale
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

        assert "No high-signal recent development" in recent.title
        assert "recent" not in overview.beginner_summary.what_it_is.lower()
        assert recent.citation_ids
        assert recent.citation_ids[0].startswith("c_recent_")
        assert recent_section.citation_ids == recent.citation_ids
        assert recent_section.items[0].event_date == recent.event_date


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


def test_generated_overview_copy_avoids_forbidden_advice_phrases():
    for ticker in ["AAPL", "VOO", "QQQ", "BTC", "ZZZZ"]:
        overview = generate_asset_overview(ticker)
        assert find_forbidden_output_phrases(_flatten_text(overview.model_dump(mode="json"))) == []


def test_overview_generation_module_does_not_import_network_clients():
    overview_source = (ROOT / "backend" / "overview.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import"]:
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
