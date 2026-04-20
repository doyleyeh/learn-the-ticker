from pathlib import Path
from typing import Any

from backend.models import AssetStatus, MetricValue, OverviewResponse
from backend.overview import generate_asset_overview, validate_overview_response
from backend.retrieval import build_asset_knowledge_pack
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


def test_generated_overviews_keep_recent_context_separate_and_explicit():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        overview = generate_asset_overview(ticker)
        recent = overview.recent_developments[0]

        assert "No high-signal recent development" in recent.title
        assert "recent" not in overview.beginner_summary.what_it_is.lower()
        assert recent.citation_ids
        assert recent.citation_ids[0].startswith("c_recent_")


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
    return citation_ids


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
