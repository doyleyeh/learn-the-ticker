from backend.models import (
    FreshnessState,
    SourceAllowlistStatus,
    SourceDocument,
    SourceUsePolicy,
)
from backend.overview import generate_asset_overview
from backend.retrieval import build_asset_knowledge_pack
from backend.sources import _drawer_excerpt, build_asset_source_drawer_response


def test_supported_cached_assets_return_drawer_groups_bindings_and_related_claims():
    for ticker in ["AAPL", "VOO", "QQQ"]:
        overview = generate_asset_overview(ticker)
        pack = build_asset_knowledge_pack(ticker)
        response = build_asset_source_drawer_response(ticker)

        overview_citation_ids = {citation.citation_id for citation in overview.citations}
        overview_source_ids = {source.source_document_id for source in overview.source_documents}
        pack_source_ids = {source.source_document_id for source in pack.source_documents}

        assert response.schema_version == "asset-source-drawer-v1"
        assert response.asset.ticker == ticker
        assert response.selected_asset.ticker == ticker
        assert response.drawer_state.value == "available"
        assert response.sources
        assert response.source_groups
        assert response.citation_bindings
        assert response.related_claims
        assert response.section_references
        assert {group.source_document_id for group in response.source_groups} <= overview_source_ids
        assert {group.source_document_id for group in response.source_groups} <= pack_source_ids
        assert {binding.citation_id for binding in response.citation_bindings} <= overview_citation_ids
        assert {binding.source_document_id for binding in response.citation_bindings} <= pack_source_ids
        assert all(binding.asset_ticker == ticker for binding in response.citation_bindings)
        assert all(group.title and group.publisher and group.url for group in response.source_groups)
        assert all(group.retrieved_at for group in response.source_groups)
        assert all(group.allowlist_status.value == "allowed" for group in response.source_groups)
        assert all(group.source_use_policy.value in {"full_text_allowed", "summary_allowed"} for group in response.source_groups)
        assert all(group.permitted_operations.can_export_full_text is False for group in response.source_groups)
        assert any(claim.section_id for claim in response.related_claims)
        assert any(reference.evidence_state.value in {"mixed", "unavailable", "unknown", "no_major_recent_development", "insufficient_evidence"} for reference in response.section_references)
        assert response.diagnostics.no_live_external_calls is True
        assert response.diagnostics.generated_output_created is False


def test_citation_and_source_document_filters_are_deterministic():
    full = build_asset_source_drawer_response("VOO")
    citation_id = full.citation_bindings[0].citation_id
    source_document_id = full.citation_bindings[0].source_document_id

    by_citation = build_asset_source_drawer_response("VOO", citation_id=citation_id)
    by_source = build_asset_source_drawer_response("VOO", source_document_id=source_document_id)
    by_both = build_asset_source_drawer_response("VOO", citation_id=citation_id, source_document_id=source_document_id)

    assert {binding.citation_id for binding in by_citation.citation_bindings} == {citation_id}
    assert {group.source_document_id for group in by_citation.source_groups} == {source_document_id}
    assert {group.source_document_id for group in by_source.source_groups} == {source_document_id}
    assert {binding.source_document_id for binding in by_source.citation_bindings} == {source_document_id}
    assert by_both.source_groups == by_citation.source_groups
    assert by_both.citation_bindings == by_citation.citation_bindings
    assert by_citation.diagnostics.filters_applied == {"citation_id": citation_id}
    assert by_source.diagnostics.filters_applied == {"source_document_id": source_document_id}


def test_source_use_policy_controls_allowed_excerpts():
    response = build_asset_source_drawer_response("AAPL")
    full_text_group = next(group for group in response.source_groups if group.source_use_policy is SourceUsePolicy.full_text_allowed)
    summary_group = next(group for group in response.source_groups if group.source_use_policy is SourceUsePolicy.summary_allowed)

    assert full_text_group.allowed_excerpts
    assert summary_group.allowed_excerpts
    assert all(excerpt.excerpt_allowed is True for excerpt in full_text_group.allowed_excerpts)
    assert all(excerpt.excerpt_allowed is True for excerpt in summary_group.allowed_excerpts)
    assert all(excerpt.text for excerpt in [*full_text_group.allowed_excerpts, *summary_group.allowed_excerpts])
    assert all(len(excerpt.text.split()) <= 80 for excerpt in [*full_text_group.allowed_excerpts, *summary_group.allowed_excerpts] if excerpt.text)

    metadata_only = SourceDocument(
        source_document_id="src_metadata_only",
        source_type="structured_market_data",
        title="Metadata-only provider fixture",
        publisher="Provider fixture",
        url="https://site.financialmodelingprep.com/developer/docs",
        retrieved_at="2026-04-20T00:00:00Z",
        freshness_state=FreshnessState.fresh,
        is_official=False,
        supporting_passage="Restricted provider payload text must not appear in the drawer.",
        source_use_policy=SourceUsePolicy.metadata_only,
        allowlist_status=SourceAllowlistStatus.allowed,
    )
    restricted = _drawer_excerpt(metadata_only, "c_metadata_only", "chk_metadata_only")

    assert restricted.text is None
    assert restricted.excerpt_allowed is False
    assert restricted.suppression_reason == "source_use_policy_metadata_only"


def test_non_generated_assets_return_empty_explicit_drawer_states():
    cases = {
        "SPY": "eligible_not_cached",
        "TQQQ": "unsupported",
        "GME": "out_of_scope",
        "ZZZZ": "unknown",
    }
    for ticker, expected_state in cases.items():
        response = build_asset_source_drawer_response(ticker)

        assert response.asset.ticker == ticker
        assert response.drawer_state.value == expected_state
        assert response.sources == []
        assert response.source_groups == []
        assert response.citation_bindings == []
        assert response.related_claims == []
        assert response.section_references == []
        assert response.diagnostics.unavailable_reasons
        assert response.diagnostics.unsupported_generated_output_suppressed is True
