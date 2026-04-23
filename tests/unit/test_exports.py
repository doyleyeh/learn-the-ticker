from pathlib import Path
from typing import Any

from backend.export import (
    export_asset_page,
    export_asset_source_list,
    export_chat_transcript,
    export_comparison,
)
from backend.models import (
    ChatTranscriptExportRequest,
    ComparisonExportRequest,
    EDUCATIONAL_DISCLAIMER,
    ExportContentType,
    ExportResponse,
    ExportState,
)
from backend.safety import find_forbidden_output_phrases


ROOT = Path(__file__).resolve().parents[2]


def test_supported_asset_page_exports_preserve_sections_citations_sources_and_disclaimer():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        export = ExportResponse.model_validate(export_asset_page(ticker).model_dump(mode="json"))
        section_ids = [section.section_id for section in export.sections]
        citation_ids = {citation.citation_id for citation in export.citations}
        source_ids = {source.source_document_id for source in export.source_documents}

        assert export.content_type is ExportContentType.asset_page
        assert export.export_state is ExportState.available
        assert export.asset is not None
        assert export.asset.ticker == ticker
        assert export.freshness is not None
        assert export.freshness.page_last_updated_at
        assert export.disclaimer == EDUCATIONAL_DISCLAIMER
        assert export.licensing_note.note_id == "export_licensing_scope"
        assert "full paid-news articles" in export.licensing_note.text
        assert "Educational Disclaimer" in export.rendered_markdown
        assert "Licensing Note" in export.rendered_markdown
        assert "beginner_summary" in section_ids
        assert "top_risks" in section_ids
        assert "recent_developments" in section_ids
        assert "educational_suitability" in section_ids
        assert "prd_sections" in section_ids
        assert section_ids.index("top_risks") < section_ids.index("prd_sections")
        if ticker == "AAPL":
            assert {"business_overview", "products_services", "strengths", "financial_quality", "valuation_context"} <= set(section_ids)
        else:
            assert {
                "fund_objective_role",
                "holdings_exposure",
                "construction_methodology",
                "cost_trading_context",
                "etf_specific_risks",
                "similar_assets_alternatives",
            } <= set(section_ids)

        top_risks = _section(export, "top_risks")
        assert len(top_risks.items) == 3
        assert [item.metadata["rank"] for item in top_risks.items] == [1, 2, 3]
        assert all(item.citation_ids for item in top_risks.items)

        recent = _section(export, "recent_developments")
        assert recent.items
        assert "recent" in recent.text.lower()
        assert all(item.citation_ids for item in recent.items)

        prd = _section(export, "prd_sections")
        assert prd.items
        assert any(item.evidence_state.value in {"unknown", "unavailable", "mixed", "insufficient_evidence"} for item in prd.items)

        assert citation_ids
        assert source_ids
        assert _used_citation_ids(export) <= citation_ids
        assert {citation.source_document_id for citation in export.citations} <= source_ids
        assert all(source.title for source in export.source_documents)
        assert all(source.source_type for source in export.source_documents)
        assert all(source.publisher for source in export.source_documents)
        assert all(source.url for source in export.source_documents)
        assert all(source.retrieved_at for source in export.source_documents)
        assert all(source.freshness_state for source in export.source_documents)
        assert all(source.allowlist_status.value == "allowed" for source in export.source_documents)
        assert all(source.source_use_policy.value in {"full_text_allowed", "summary_allowed"} for source in export.source_documents)
        assert all(source.permitted_operations.can_export_full_text is False for source in export.source_documents)
        assert all(source.allowed_excerpt is not None for source in export.source_documents)
        assert all(source.allowed_excerpt.note for source in export.source_documents if source.allowed_excerpt)
        assert all(
            source.allowed_excerpt.source_use_policy == source.source_use_policy
            for source in export.source_documents
            if source.allowed_excerpt
        )
        assert not any("glossary" in citation.citation_id.lower() for citation in export.citations)
        assert not find_forbidden_output_phrases(_flatten_text(export.model_dump(mode="json")))


def test_asset_source_list_export_contains_source_metadata_and_allowed_excerpts():
    export = export_asset_source_list("VOO")

    assert export.content_type is ExportContentType.asset_source_list
    assert export.export_state is ExportState.available
    assert export.asset is not None
    assert export.asset.ticker == "VOO"
    assert _section(export, "asset_source_list").items
    assert export.source_documents

    source = export.source_documents[0]
    assert source.source_document_id
    assert source.title
    assert source.source_type
    assert source.publisher
    assert source.url
    assert source.published_at or source.as_of_date
    assert source.retrieved_at
    assert source.freshness_state.value == "fresh"
    assert source.is_official is True
    assert source.allowed_excerpt is not None
    assert source.allowed_excerpt.redistribution_allowed is True
    assert source.allowed_excerpt.kind == "supporting_passage"
    assert source.allowed_excerpt.note
    assert source.allowlist_status.value == "allowed"
    assert source.source_use_policy.value == "full_text_allowed"
    assert "source-use policy" in export.rendered_markdown
    assert "full paid-news articles" in export.licensing_note.text


def test_comparison_exports_preserve_pack_citations_sources_and_reverse_order():
    for left, right in [("VOO", "QQQ"), ("QQQ", "VOO")]:
        export = export_comparison(ComparisonExportRequest(left_ticker=left, right_ticker=right))
        section_ids = [section.section_id for section in export.sections]

        assert export.content_type is ExportContentType.comparison
        assert export.export_state is ExportState.available
        assert export.left_asset is not None
        assert export.right_asset is not None
        assert export.left_asset.ticker == left
        assert export.right_asset.ticker == right
        assert export.metadata["comparison_type"] == "etf_vs_etf"
        assert {"comparison_identity", "key_differences", "beginner_bottom_line"} <= set(section_ids)
        assert _section(export, "key_differences").items
        assert _section(export, "beginner_bottom_line").citation_ids
        assert export.citations
        assert export.source_documents
        assert _used_citation_ids(export) <= {citation.citation_id for citation in export.citations}
        assert {citation.source_document_id for citation in export.citations} <= {
            source.source_document_id for source in export.source_documents
        }
        assert all(source.allowed_excerpt is not None for source in export.source_documents)
        assert all(source.allowlist_status.value == "allowed" for source in export.source_documents)
        assert all(source.source_use_policy.value in {"full_text_allowed", "summary_allowed"} for source in export.source_documents)
        assert not find_forbidden_output_phrases(_flatten_text(export.model_dump(mode="json")))


def test_chat_transcript_exports_preserve_answer_safety_uncertainty_and_sources():
    grounded = export_chat_transcript("QQQ", ChatTranscriptExportRequest(question="What is this fund?"))
    advice = export_chat_transcript("VOO", ChatTranscriptExportRequest(question="Should I buy VOO today?"))

    assert grounded.content_type is ExportContentType.chat_transcript
    assert grounded.export_state is ExportState.available
    assert grounded.asset is not None
    assert grounded.asset.ticker == "QQQ"
    assert grounded.metadata["submitted_question"] == "What is this fund?"
    assert grounded.metadata["safety_classification"] == "educational"
    assert _section(grounded, "chat_answer").citation_ids
    assert _section(grounded, "uncertainty_notes").items
    assert grounded.citations
    assert grounded.source_documents

    assert advice.export_state is ExportState.available
    assert advice.metadata["safety_classification"] == "personalized_advice_redirect"
    assert "educational" in advice.rendered_markdown.lower()
    assert advice.citations == []
    assert advice.source_documents == []
    assert _section(advice, "chat_answer").citation_ids == []
    assert not find_forbidden_output_phrases(_flatten_text(advice.model_dump(mode="json")))


def test_unsupported_unknown_unavailable_and_eligible_not_cached_exports_do_not_generate_facts():
    blocked_exports = [
        export_asset_page("BTC"),
        export_asset_page("ZZZZ"),
        export_asset_page("SPY"),
        export_asset_source_list("TQQQ"),
        export_comparison(ComparisonExportRequest(left_ticker="VOO", right_ticker="BTC")),
        export_comparison(ComparisonExportRequest(left_ticker="AAPL", right_ticker="VOO")),
        export_chat_transcript("BTC", ChatTranscriptExportRequest(question="What is this?")),
        export_chat_transcript("SPY", ChatTranscriptExportRequest(question="What is this?")),
    ]

    for export in blocked_exports:
        assert export.export_state in {ExportState.unsupported, ExportState.unavailable}
        assert export.sections == []
        assert export.citations == []
        assert export.source_documents == []
        assert "Export unavailable" in export.rendered_markdown
        assert "Educational Disclaimer" in export.rendered_markdown
        assert export.disclaimer == EDUCATIONAL_DISCLAIMER
        assert not find_forbidden_output_phrases(_flatten_text(export.model_dump(mode="json")))

    assert blocked_exports[0].export_state is ExportState.unsupported
    assert blocked_exports[1].export_state is ExportState.unavailable
    assert blocked_exports[2].export_state is ExportState.unavailable
    assert blocked_exports[-1].metadata["generated_chat_answer"] is False


def test_export_module_does_not_import_network_clients_or_frontend_packages():
    export_source = (ROOT / "backend" / "export.py").read_text(encoding="utf-8")

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "reportlab", "weasyprint"]:
        assert forbidden not in export_source


def _section(export: ExportResponse, section_id: str):
    return next(section for section in export.sections if section.section_id == section_id)


def _used_citation_ids(export: ExportResponse) -> set[str]:
    return {
        *{citation_id for section in export.sections for citation_id in section.citation_ids},
        *{citation_id for section in export.sections for item in section.items for citation_id in item.citation_ids},
    }


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return ""
