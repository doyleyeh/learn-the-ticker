from __future__ import annotations

from typing import Any

from backend.cache import build_comparison_pack_freshness_input, build_knowledge_pack_freshness_input
from backend.chat import generate_asset_chat
from backend.chat_sessions import PersistedChatSessionReader, chat_session_export_payload
from backend.comparison import generate_comparison
from backend.generated_output_cache_repository import (
    GeneratedOutputArtifactCategory,
    build_deterministic_generated_output_cache_records,
    persist_generated_output_cache_records,
)
from backend.models import (
    AssetIdentity,
    AssetStatus,
    CacheEntryKind,
    CacheScope,
    ChatSourceDocument,
    ChatSessionLifecycleState,
    ChatSessionPublicMetadata,
    ChatTranscriptExportRequest,
    ChatTurnRecord,
    Citation,
    ComparisonExportRequest,
    EDUCATIONAL_DISCLAIMER,
    EvidenceState,
    ExportCitation,
    ExportContentType,
    ExportExcerpt,
    ExportFormat,
    ExportNote,
    ExportResponse,
    ExportSectionValidation,
    ExportSourceMetadata,
    ExportState,
    ExportValidation,
    ExportValidationBindingScope,
    ExportValidationCitationBinding,
    ExportValidationDiagnostics,
    ExportValidationOutcome,
    ExportValidationSourceBinding,
    ExportedItem,
    ExportedSection,
    Freshness,
    FreshnessState,
    OverviewResponse,
    OverviewSectionFreshnessValidation,
    OverviewSectionType,
    SafetyClassification,
    SearchSupportClassification,
    SectionFreshnessInput,
    SourceAllowlistStatus,
    SourceDocument,
    SourcePolicyDecisionState,
    SourceUsePolicy,
    StateMessage,
)
from backend.overview import generate_asset_overview
from backend.retrieval import build_asset_knowledge_pack, build_comparison_knowledge_pack
from backend.search import search_assets
from backend.source_policy import (
    SourcePolicyAction,
    excerpt_text_for_policy,
    resolve_source_policy,
    source_can_export_excerpt,
    source_can_export_source_metadata,
    source_can_support_markdown_json_export,
    validate_source_handoff,
)


EXPORT_LICENSING_NOTE = ExportNote(
    note_id="export_licensing_scope",
    label="Licensing and export scope",
    text=(
        "This export includes citation IDs, source attribution, freshness metadata, and short allowed "
        "fixture supporting passages. It does not export full paid-news articles, full filings, full "
        "issuer documents, or restricted provider payloads unless redistribution rights are confirmed."
    ),
)


def export_asset_page(
    ticker: str,
    export_format: ExportFormat | str = ExportFormat.markdown,
    *,
    persisted_pack_reader: Any | None = None,
    generated_output_cache_reader: Any | None = None,
    source_snapshot_reader: Any | None = None,
    generated_output_cache_writer: Any | None = None,
    persisted_weekly_news_reader: Any | None = None,
) -> ExportResponse:
    """Shape an existing deterministic asset overview into an accountless export payload."""

    blocked = _blocked_asset_response(ticker, ExportContentType.asset_page, export_format)
    if blocked is not None:
        return blocked

    overview = generate_asset_overview(
        ticker,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
        source_snapshot_reader=source_snapshot_reader,
        persisted_weekly_news_reader=persisted_weekly_news_reader,
    )
    if not overview.asset.supported:
        return _unavailable_asset_response(overview.asset, overview.state, ExportContentType.asset_page, export_format)

    sections = _asset_page_sections(overview)
    citations = _export_citations_from_overview(overview)
    sources = _export_sources(overview.source_documents)
    title = f"{overview.asset.ticker} asset page export"
    markdown = _render_markdown(title, sections, overview.source_documents, overview.freshness)

    response = ExportResponse(
        content_type=ExportContentType.asset_page,
        export_format=_coerce_format(export_format),
        export_state=ExportState.available,
        title=title,
        state=overview.state,
        asset=overview.asset,
        freshness=overview.freshness,
        sections=sections,
        citations=citations,
        source_documents=sources,
        disclaimer=EDUCATIONAL_DISCLAIMER,
        licensing_note=EXPORT_LICENSING_NOTE,
        rendered_markdown=markdown,
        metadata={
            "top_risk_count": len(overview.top_risks),
            "recent_developments_separate": True,
            "source": "local_fixture_overview",
        },
    )
    response = response.model_copy(update={"export_validation": _build_asset_export_validation(response, overview)})
    _maybe_write_asset_export_cache(response, generated_output_cache_writer)
    return response


def export_asset_source_list(
    ticker: str,
    export_format: ExportFormat | str = ExportFormat.markdown,
    *,
    persisted_pack_reader: Any | None = None,
    generated_output_cache_reader: Any | None = None,
    source_snapshot_reader: Any | None = None,
    generated_output_cache_writer: Any | None = None,
    persisted_weekly_news_reader: Any | None = None,
) -> ExportResponse:
    """Export source metadata for an asset without adding new source material."""

    blocked = _blocked_asset_response(ticker, ExportContentType.asset_source_list, export_format)
    if blocked is not None:
        return blocked

    overview = generate_asset_overview(
        ticker,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
        source_snapshot_reader=source_snapshot_reader,
        persisted_weekly_news_reader=persisted_weekly_news_reader,
    )
    if not overview.asset.supported:
        return _unavailable_asset_response(
            overview.asset,
            overview.state,
            ExportContentType.asset_source_list,
            export_format,
        )

    source_items = [
        ExportedItem(
            item_id=source.source_document_id,
            title=source.title,
            text=(
                f"{source.source_type} from {source.publisher}; freshness: {source.freshness_state.value}; "
                f"published: {source.published_at or 'unknown'}; as of: {source.as_of_date or 'unknown'}; "
                f"retrieved: {source.retrieved_at}; official source: {source.is_official}; "
                f"source-use policy: {source.source_use_policy.value}; allowlist status: {source.allowlist_status.value}."
            ),
            source_document_ids=[source.source_document_id],
            freshness_state=source.freshness_state,
            evidence_state=EvidenceState.supported,
            as_of_date=source.as_of_date,
            retrieved_at=source.retrieved_at,
            metadata={
                "url": source.url,
                "publisher": source.publisher,
                "source_type": source.source_type,
                "source_use_policy": source.source_use_policy.value,
                "allowlist_status": source.allowlist_status.value,
            },
        )
        for source in overview.source_documents
    ]
    sections = [
        ExportedSection(
            section_id="asset_source_list",
            title="Source List",
            section_type=ExportContentType.asset_source_list,
            text="Source metadata and allowed excerpt metadata for the exported asset page.",
            items=source_items,
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported,
        )
    ]
    title = f"{overview.asset.ticker} source-list export"
    markdown = _render_markdown(title, sections, overview.source_documents, overview.freshness)

    response = ExportResponse(
        content_type=ExportContentType.asset_source_list,
        export_format=_coerce_format(export_format),
        export_state=ExportState.available,
        title=title,
        state=overview.state,
        asset=overview.asset,
        freshness=overview.freshness,
        sections=sections,
        citations=_export_citations_from_overview(overview),
        source_documents=_export_sources(overview.source_documents),
        disclaimer=EDUCATIONAL_DISCLAIMER,
        licensing_note=EXPORT_LICENSING_NOTE,
        rendered_markdown=markdown,
        metadata={"source_count": len(overview.source_documents), "source": "local_fixture_overview"},
    )
    response = response.model_copy(update={"export_validation": _build_asset_export_validation(response, overview)})
    _maybe_write_asset_source_list_cache(response, generated_output_cache_writer)
    return response


def export_comparison(
    request: ComparisonExportRequest,
    *,
    persisted_pack_reader: Any | None = None,
    generated_output_cache_reader: Any | None = None,
    generated_output_cache_writer: Any | None = None,
) -> ExportResponse:
    """Shape an existing deterministic comparison into an export payload."""

    comparison = generate_comparison(
        request.left_ticker,
        request.right_ticker,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
    )
    export_format = _coerce_format(request.export_format)
    title = f"{comparison.left_asset.ticker} vs {comparison.right_asset.ticker} comparison export"

    if comparison.comparison_type == "unavailable" or comparison.state.status is not AssetStatus.supported:
        response = ExportResponse(
            content_type=ExportContentType.comparison,
            export_format=export_format,
            export_state=_export_state_from_asset_status(comparison.state.status),
            title=title,
            state=comparison.state,
            left_asset=comparison.left_asset,
            right_asset=comparison.right_asset,
            sections=[],
            citations=[],
            source_documents=[],
            disclaimer=EDUCATIONAL_DISCLAIMER,
            licensing_note=EXPORT_LICENSING_NOTE,
            rendered_markdown=_unavailable_markdown(title, comparison.state.message),
            metadata={
                "comparison_type": comparison.comparison_type,
                "source": "local_fixture_comparison",
                "generated_comparison_output": False,
            },
        )
        return response.model_copy(
            update={
                "export_validation": _build_unavailable_export_validation(
                    response,
                    binding_scope=ExportValidationBindingScope.unavailable,
                )
            }
        )

    sections = [
        ExportedSection(
            section_id="comparison_identity",
            title="Compared Assets",
            section_type=ExportContentType.comparison,
            text=(
                f"Left: {comparison.left_asset.ticker} - {comparison.left_asset.name}. "
                f"Right: {comparison.right_asset.ticker} - {comparison.right_asset.name}."
            ),
            evidence_state=EvidenceState.supported,
        ),
        ExportedSection(
            section_id="key_differences",
            title="Key Differences",
            section_type=ExportContentType.comparison,
            items=[
                ExportedItem(
                    item_id=f"comparison_{_slug(item.dimension)}",
                    title=item.dimension,
                    text=_with_citations(item.plain_english_summary, item.citation_ids),
                    citation_ids=item.citation_ids,
                    source_document_ids=_source_ids_for_citation_ids(item.citation_ids, comparison.citations),
                    freshness_state=_freshness_for_citation_ids(item.citation_ids, comparison.citations),
                    evidence_state=EvidenceState.supported,
                )
                for item in comparison.key_differences
            ],
            citation_ids=sorted({citation_id for item in comparison.key_differences for citation_id in item.citation_ids}),
            source_document_ids=sorted(
                {
                    source_id
                    for item in comparison.key_differences
                    for source_id in _source_ids_for_citation_ids(item.citation_ids, comparison.citations)
                }
            ),
            evidence_state=EvidenceState.supported,
        ),
        ExportedSection(
            section_id="beginner_bottom_line",
            title="Beginner Bottom Line",
            section_type=ExportContentType.comparison,
            text=(
                _with_citations(
                    comparison.bottom_line_for_beginners.summary,
                    comparison.bottom_line_for_beginners.citation_ids,
                )
                if comparison.bottom_line_for_beginners
                else None
            ),
            citation_ids=(
                comparison.bottom_line_for_beginners.citation_ids
                if comparison.bottom_line_for_beginners
                else []
            ),
            source_document_ids=(
                _source_ids_for_citation_ids(comparison.bottom_line_for_beginners.citation_ids, comparison.citations)
                if comparison.bottom_line_for_beginners
                else []
            ),
            evidence_state=EvidenceState.supported,
        ),
    ]
    markdown = _render_markdown(title, sections, comparison.source_documents, None)

    response = ExportResponse(
        content_type=ExportContentType.comparison,
        export_format=export_format,
        export_state=ExportState.available,
        title=title,
        state=comparison.state,
        left_asset=comparison.left_asset,
        right_asset=comparison.right_asset,
        sections=sections,
        citations=_export_citations_from_comparison(comparison),
        source_documents=_export_sources(comparison.source_documents),
        disclaimer=EDUCATIONAL_DISCLAIMER,
        licensing_note=EXPORT_LICENSING_NOTE,
        rendered_markdown=markdown,
        metadata={"comparison_type": comparison.comparison_type, "source": "local_fixture_comparison"},
    )
    response = response.model_copy(update={"export_validation": _build_comparison_export_validation(response, comparison)})
    _maybe_write_comparison_export_cache(response, generated_output_cache_writer)
    return response


def export_chat_transcript(
    ticker: str,
    request: ChatTranscriptExportRequest,
    *,
    persisted_session_reader: PersistedChatSessionReader | Any | None = None,
    persisted_pack_reader: Any | None = None,
    generated_output_cache_reader: Any | None = None,
    generated_output_cache_writer: Any | None = None,
) -> ExportResponse:
    """Export a single deterministic chat turn for a selected cached asset."""

    if request.conversation_id:
        session_export = _maybe_export_existing_chat_session(
            request.conversation_id,
            request.export_format,
            persisted_session_reader=persisted_session_reader,
        )
        if session_export is not None:
            return session_export

    blocked = _blocked_asset_response(ticker, ExportContentType.chat_transcript, request.export_format)
    if blocked is not None:
        blocked.metadata["submitted_question"] = request.question
        blocked.metadata["generated_chat_answer"] = False
        return blocked

    chat = generate_asset_chat(
        ticker,
        request.question,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
    )
    export_format = _coerce_format(request.export_format)
    title = f"{chat.asset.ticker} chat transcript export"
    sections = [
        ExportedSection(
            section_id="chat_context",
            title="Chat Context",
            section_type=ExportContentType.chat_transcript,
            items=[
                ExportedItem(
                    item_id="selected_ticker",
                    title="Selected Ticker",
                    text=chat.asset.ticker,
                    evidence_state=EvidenceState.supported,
                ),
                ExportedItem(
                    item_id="submitted_question",
                    title="Submitted Question",
                    text=request.question,
                    evidence_state=EvidenceState.supported,
                ),
                ExportedItem(
                    item_id="safety_classification",
                    title="Safety Classification",
                    text=chat.safety_classification.value,
                    evidence_state=EvidenceState.supported,
                    metadata={"safety_classification": chat.safety_classification.value},
                ),
            ],
            evidence_state=EvidenceState.supported,
        ),
        *(
            [
                ExportedSection(
                    section_id="comparison_redirect",
                    title="Comparison Workflow Redirect",
                    section_type=ExportContentType.chat_transcript,
                    text=chat.compare_route_suggestion.workflow_guidance,
                    items=[
                        ExportedItem(
                            item_id="compare_route",
                            title="Compare Route",
                            text=chat.compare_route_suggestion.route,
                            evidence_state=EvidenceState.supported,
                            metadata={
                                "left_ticker": chat.compare_route_suggestion.left_ticker,
                                "right_ticker": chat.compare_route_suggestion.right_ticker,
                                "comparison_ticker": chat.compare_route_suggestion.comparison_ticker,
                                "comparison_availability_state": (
                                    chat.compare_route_suggestion.comparison_availability_state.value
                                ),
                                "comparison_state_message": chat.compare_route_suggestion.comparison_state_message,
                            },
                        )
                    ],
                    evidence_state=EvidenceState.unsupported,
                )
            ]
            if chat.compare_route_suggestion is not None
            else []
        ),
        ExportedSection(
            section_id="chat_answer",
            title="Direct Answer",
            section_type=ExportContentType.chat_transcript,
            text=_with_citations(chat.direct_answer, [citation.citation_id for citation in chat.citations]),
            citation_ids=[citation.citation_id for citation in chat.citations],
            source_document_ids=sorted({citation.source_document_id for citation in chat.citations}),
            evidence_state=(
                EvidenceState.supported
                if chat.safety_classification is SafetyClassification.educational and chat.citations
                else EvidenceState.insufficient_evidence
                if chat.safety_classification is SafetyClassification.educational
                else EvidenceState.unsupported
            ),
        ),
        ExportedSection(
            section_id="why_it_matters",
            title="Why It Matters",
            section_type=ExportContentType.chat_transcript,
            text=chat.why_it_matters,
            evidence_state=EvidenceState.supported,
        ),
        ExportedSection(
            section_id="uncertainty_notes",
            title="Uncertainty Notes",
            section_type=ExportContentType.chat_transcript,
            items=[
                ExportedItem(
                    item_id=f"uncertainty_{index + 1}",
                    title=f"Uncertainty {index + 1}",
                    text=note,
                    evidence_state=EvidenceState.unknown,
                )
                for index, note in enumerate(chat.uncertainty)
            ],
            evidence_state=EvidenceState.unknown if chat.uncertainty else EvidenceState.supported,
        ),
    ]
    markdown = _render_markdown(title, sections, chat.source_documents, None)

    response = ExportResponse(
        content_type=ExportContentType.chat_transcript,
        export_format=export_format,
        export_state=ExportState.available,
        title=title,
        state=StateMessage(status=chat.asset.status, message="Chat transcript export uses the selected local asset knowledge pack."),
        asset=chat.asset,
        sections=sections,
        citations=_export_citations_from_chat(chat.citations, chat.source_documents),
        source_documents=_export_sources(chat.source_documents),
        disclaimer=EDUCATIONAL_DISCLAIMER,
        licensing_note=EXPORT_LICENSING_NOTE,
        rendered_markdown=markdown,
        metadata={
            "selected_ticker": chat.asset.ticker,
            "submitted_question": request.question,
            "conversation_id": request.conversation_id,
            "safety_classification": chat.safety_classification.value,
            "compare_route_suggestion": (
                chat.compare_route_suggestion.model_dump(mode="json")
                if chat.compare_route_suggestion is not None
                else None
            ),
            "generated_chat_answer": True,
            "source": "local_fixture_chat",
        },
    )
    response = response.model_copy(
        update={"export_validation": _build_chat_export_validation(response, asset_ticker=chat.asset.ticker)}
    )
    _maybe_write_chat_export_cache(response, generated_output_cache_writer)
    return response


def export_chat_session_transcript(
    conversation_id: str,
    export_format: ExportFormat | str = ExportFormat.markdown,
    *,
    persisted_session_reader: PersistedChatSessionReader | Any | None = None,
) -> ExportResponse:
    metadata, turns = chat_session_export_payload(conversation_id, persisted_reader=persisted_session_reader)
    return _export_chat_session_payload(metadata, turns, export_format)


def _maybe_export_existing_chat_session(
    conversation_id: str,
    export_format: ExportFormat | str,
    *,
    persisted_session_reader: PersistedChatSessionReader | Any | None = None,
) -> ExportResponse | None:
    metadata, turns = chat_session_export_payload(conversation_id, persisted_reader=persisted_session_reader)
    if metadata.lifecycle_state is ChatSessionLifecycleState.unavailable and metadata.selected_asset is None:
        return None
    return _export_chat_session_payload(metadata, turns, export_format)


def _maybe_write_asset_export_cache(response: ExportResponse, writer: Any | None) -> None:
    if writer is None or response.asset is None or response.export_state is not ExportState.available or not response.citations:
        return
    try:
        pack = build_asset_knowledge_pack(response.asset.ticker)
        source_ids = {source.source_document_id for source in response.source_documents}
        citations_by_source = _citations_by_source(response)
        section_labels = [
            *_section_freshness_inputs_from_export(response),
            *[
                SectionFreshnessInput(
                    section_id=f"source_list_{source.source_document_id}",
                    freshness_state=source.freshness_state,
                    evidence_state=EvidenceState.supported.value,
                    as_of_date=source.as_of_date,
                    retrieved_at=source.retrieved_at,
                )
                for source in response.source_documents
            ],
        ]
        knowledge_input = build_knowledge_pack_freshness_input(
            pack,
            section_freshness_labels=section_labels,
        )
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum.model_copy(
                        update={"citation_ids": sorted(citations_by_source.get(checksum.source_document_id, []))}
                    )
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in source_ids
                ]
            }
        )
        records = build_deterministic_generated_output_cache_records(
            cache_entry_id=f"generated-output-{response.asset.ticker.lower()}-asset-export",
            output_identity=f"asset:{response.asset.ticker}:export:asset_page",
            mode_or_output_type="asset-page-export-metadata",
            artifact_category=GeneratedOutputArtifactCategory.export_payload_metadata,
            entry_kind=CacheEntryKind.export_payload,
            scope=CacheScope.asset,
            schema_version="export-payload-v1",
            prompt_version="export-payload-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=[citation.citation_id for citation in response.citations],
            created_at=response.freshness.page_last_updated_at if response.freshness else "2026-04-25T18:33:44Z",
            ttl_seconds=604800,
            asset_ticker=response.asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


def _maybe_write_asset_source_list_cache(response: ExportResponse, writer: Any | None) -> None:
    if writer is None or response.asset is None or response.export_state is not ExportState.available:
        return
    try:
        pack = build_asset_knowledge_pack(response.asset.ticker)
        source_ids = {source.source_document_id for source in response.source_documents}
        citations_by_source = _citations_by_source(response)
        section_labels = [
            *_section_freshness_inputs_from_export(response),
            *[
                SectionFreshnessInput(
                    section_id=f"source_list_{source.source_document_id}",
                    freshness_state=source.freshness_state,
                    evidence_state=EvidenceState.supported.value,
                    as_of_date=source.as_of_date,
                    retrieved_at=source.retrieved_at,
                )
                for source in response.source_documents
            ],
        ]
        knowledge_input = build_knowledge_pack_freshness_input(
            pack,
            section_freshness_labels=section_labels,
        )
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum.model_copy(
                        update={"citation_ids": sorted(citations_by_source.get(checksum.source_document_id, []))}
                    )
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in source_ids
                ]
            }
        )
        records = build_deterministic_generated_output_cache_records(
            cache_entry_id=f"generated-output-{response.asset.ticker.lower()}-source-list",
            output_identity=f"asset:{response.asset.ticker}:source-list-metadata",
            mode_or_output_type="source-list-export-metadata",
            artifact_category=GeneratedOutputArtifactCategory.source_list_export_metadata,
            entry_kind=CacheEntryKind.source_list,
            scope=CacheScope.asset,
            schema_version="source-list-v1",
            prompt_version="source-list-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=[citation.citation_id for citation in response.citations],
            created_at=response.freshness.page_last_updated_at if response.freshness else "2026-04-25T18:33:44Z",
            ttl_seconds=604800,
            asset_ticker=response.asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


def _maybe_write_comparison_export_cache(response: ExportResponse, writer: Any | None) -> None:
    if (
        writer is None
        or response.left_asset is None
        or response.right_asset is None
        or response.export_state is not ExportState.available
        or not response.citations
    ):
        return
    try:
        pack = build_comparison_knowledge_pack(response.left_asset.ticker, response.right_asset.ticker)
        source_ids = {source.source_document_id for source in response.source_documents}
        citations_by_source = _citations_by_source(response)
        knowledge_input = build_comparison_pack_freshness_input(
            pack,
            section_freshness_labels=_section_freshness_inputs_from_export(response),
        )
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum.model_copy(
                        update={"citation_ids": sorted(citations_by_source.get(checksum.source_document_id, []))}
                    )
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in source_ids
                ]
            }
        )
        records = build_deterministic_generated_output_cache_records(
            cache_entry_id=(
                f"generated-output-{response.left_asset.ticker.lower()}-"
                f"{response.right_asset.ticker.lower()}-comparison-export"
            ),
            output_identity=f"comparison:{response.left_asset.ticker}-to-{response.right_asset.ticker}:export",
            mode_or_output_type="comparison-export-metadata",
            artifact_category=GeneratedOutputArtifactCategory.export_payload_metadata,
            entry_kind=CacheEntryKind.export_payload,
            scope=CacheScope.comparison,
            schema_version="export-payload-v1",
            prompt_version="export-payload-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=[citation.citation_id for citation in response.citations],
            created_at="2026-04-25T18:33:44Z",
            ttl_seconds=604800,
            comparison_id=pack.comparison_pack_id,
            comparison_left_ticker=response.left_asset.ticker,
            comparison_right_ticker=response.right_asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


def _maybe_write_chat_export_cache(response: ExportResponse, writer: Any | None) -> None:
    if (
        writer is None
        or response.asset is None
        or response.export_state is not ExportState.available
        or response.metadata.get("safety_classification") != SafetyClassification.educational.value
        or not response.citations
    ):
        return
    try:
        pack = build_asset_knowledge_pack(response.asset.ticker)
        source_ids = {source.source_document_id for source in response.source_documents}
        citations_by_source = _citations_by_source(response)
        knowledge_input = build_knowledge_pack_freshness_input(
            pack,
            section_freshness_labels=_section_freshness_inputs_from_export(response),
        )
        knowledge_input = knowledge_input.model_copy(
            update={
                "source_checksums": [
                    checksum.model_copy(
                        update={"citation_ids": sorted(citations_by_source.get(checksum.source_document_id, []))}
                    )
                    for checksum in knowledge_input.source_checksums
                    if checksum.source_document_id in source_ids
                ]
            }
        )
        records = build_deterministic_generated_output_cache_records(
            cache_entry_id=f"generated-output-{response.asset.ticker.lower()}-chat-export",
            output_identity=f"asset:{response.asset.ticker}:chat-export-metadata",
            mode_or_output_type="chat-transcript-export-metadata",
            artifact_category=GeneratedOutputArtifactCategory.export_payload_metadata,
            entry_kind=CacheEntryKind.export_payload,
            scope=CacheScope.chat,
            schema_version="export-payload-v1",
            prompt_version="export-payload-prompt-v1",
            knowledge_input=knowledge_input,
            citation_ids=[citation.citation_id for citation in response.citations],
            created_at="2026-04-25T18:33:44Z",
            ttl_seconds=604800,
            asset_ticker=response.asset.ticker,
        )
        persist_generated_output_cache_records(writer, records)
    except Exception:
        return


def _section_freshness_inputs_from_export(response: ExportResponse) -> list[SectionFreshnessInput]:
    return [
        SectionFreshnessInput(
            section_id=section.section_id,
            freshness_state=section.freshness_state or FreshnessState.fresh,
            evidence_state=section.evidence_state.value if section.evidence_state else EvidenceState.supported.value,
            as_of_date=section.as_of_date,
            retrieved_at=section.retrieved_at,
        )
        for section in response.sections
    ] or [
        SectionFreshnessInput(
            section_id="export_metadata",
            freshness_state=FreshnessState.fresh,
            evidence_state=EvidenceState.supported.value,
        )
    ]


def _citations_by_source(response: ExportResponse) -> dict[str, list[str]]:
    citations_by_source: dict[str, list[str]] = {}
    for citation in response.citations:
        citations_by_source.setdefault(citation.source_document_id, []).append(citation.citation_id)
    return citations_by_source


def _export_chat_session_payload(
    metadata: ChatSessionPublicMetadata,
    turns: list[ChatTurnRecord],
    export_format: ExportFormat | str,
) -> ExportResponse:
    resolved_format = _coerce_format(export_format)
    conversation_id = metadata.conversation_id or "unavailable"
    title = f"Chat session {conversation_id} transcript export"

    if metadata.lifecycle_state is not ChatSessionLifecycleState.active or not turns:
        message = f"Chat transcript export is unavailable because the session state is {metadata.lifecycle_state.value}."
        response = ExportResponse(
            content_type=ExportContentType.chat_transcript,
            export_format=resolved_format,
            export_state=ExportState.unavailable,
            title=title,
            state=StateMessage(
                status=metadata.selected_asset.status if metadata.selected_asset else AssetStatus.unknown,
                message=message,
            ),
            asset=metadata.selected_asset,
            sections=[],
            citations=[],
            source_documents=[],
            disclaimer=EDUCATIONAL_DISCLAIMER,
            licensing_note=EXPORT_LICENSING_NOTE,
            rendered_markdown=_unavailable_markdown(title, message),
            metadata=_chat_session_export_metadata(metadata, generated_chat_answer=False),
        )
        return response.model_copy(
            update={
                "export_validation": _build_unavailable_export_validation(
                    response,
                    binding_scope=ExportValidationBindingScope.unavailable,
                )
            }
        )

    all_citations = _dedupe_by_id([citation for turn in turns for citation in turn.citations], "citation_id")
    all_sources = _dedupe_by_id([source for turn in turns for source in turn.source_documents], "citation_id")
    sections = [
        ExportedSection(
            section_id="chat_session_metadata",
            title="Chat Session Metadata",
            section_type=ExportContentType.chat_transcript,
            items=[
                ExportedItem(
                    item_id="conversation_id",
                    title="Conversation ID",
                    text=conversation_id,
                    evidence_state=EvidenceState.supported,
                ),
                ExportedItem(
                    item_id="selected_ticker",
                    title="Selected Ticker",
                    text=metadata.selected_asset.ticker if metadata.selected_asset else "unknown",
                    evidence_state=EvidenceState.supported if metadata.selected_asset else EvidenceState.unknown,
                ),
                ExportedItem(
                    item_id="session_lifecycle_state",
                    title="Session State",
                    text=metadata.lifecycle_state.value,
                    evidence_state=EvidenceState.supported,
                ),
                ExportedItem(
                    item_id="expires_at",
                    title="Expires At",
                    text=metadata.expires_at or "unknown",
                    evidence_state=EvidenceState.supported if metadata.expires_at else EvidenceState.unknown,
                ),
            ],
            evidence_state=EvidenceState.supported,
        ),
        ExportedSection(
            section_id="chat_turns",
            title="Chat Turns",
            section_type=ExportContentType.chat_transcript,
            items=[
                ExportedItem(
                    item_id=turn.turn_id,
                    title=f"Turn {index + 1}",
                    text=_with_citations(
                        f"{turn.direct_answer} Why it matters: {turn.why_it_matters}",
                        turn.citation_ids,
                    ),
                    citation_ids=turn.citation_ids,
                    source_document_ids=turn.source_document_ids,
                    freshness_state=turn.freshness_state,
                    evidence_state=turn.evidence_state,
                    metadata={
                        "safety_classification": turn.safety_classification.value,
                        "compare_route_suggestion": (
                            turn.compare_route_suggestion.model_dump(mode="json")
                            if turn.compare_route_suggestion is not None
                            else None
                        ),
                    },
                )
                for index, turn in enumerate(turns)
            ],
            citation_ids=sorted({citation_id for turn in turns for citation_id in turn.citation_ids}),
            source_document_ids=sorted({source_id for turn in turns for source_id in turn.source_document_ids}),
            evidence_state=EvidenceState.supported,
        ),
        *(
            [
                ExportedSection(
                    section_id="comparison_redirects",
                    title="Comparison Workflow Redirects",
                    section_type=ExportContentType.chat_transcript,
                    text="Comparison redirects are preserved as workflow guidance only and do not export multi-asset factual evidence.",
                    items=[
                        ExportedItem(
                            item_id=f"{turn.turn_id}_compare_route",
                            title=f"{turn.turn_id} compare route",
                            text=turn.compare_route_suggestion.route,
                            evidence_state=EvidenceState.supported,
                            metadata={
                                "left_ticker": turn.compare_route_suggestion.left_ticker,
                                "right_ticker": turn.compare_route_suggestion.right_ticker,
                                "comparison_ticker": turn.compare_route_suggestion.comparison_ticker,
                                "comparison_availability_state": (
                                    turn.compare_route_suggestion.comparison_availability_state.value
                                ),
                                "comparison_state_message": turn.compare_route_suggestion.comparison_state_message,
                            },
                        )
                        for turn in turns
                        if turn.compare_route_suggestion is not None
                    ],
                    evidence_state=EvidenceState.unsupported,
                )
            ]
            if any(turn.compare_route_suggestion is not None for turn in turns)
            else []
        ),
        ExportedSection(
            section_id="uncertainty_notes",
            title="Uncertainty Notes",
            section_type=ExportContentType.chat_transcript,
            items=[
                ExportedItem(
                    item_id=f"{turn.turn_id}_uncertainty_{index + 1}",
                    title=f"{turn.turn_id} uncertainty {index + 1}",
                    text=note,
                    evidence_state=EvidenceState.unknown,
                )
                for turn in turns
                for index, note in enumerate(turn.uncertainty_labels)
            ],
            evidence_state=EvidenceState.unknown,
        ),
    ]
    markdown = _render_markdown(title, sections, all_sources, None)
    response = ExportResponse(
        content_type=ExportContentType.chat_transcript,
        export_format=resolved_format,
        export_state=ExportState.available,
        title=title,
        state=StateMessage(
            status=metadata.selected_asset.status if metadata.selected_asset else AssetStatus.unknown,
            message="Chat transcript export uses safe session turn records from the selected asset knowledge pack.",
        ),
        asset=metadata.selected_asset,
        sections=sections,
        citations=_export_citations_from_chat(all_citations, all_sources),
        source_documents=_export_sources(all_sources),
        disclaimer=EDUCATIONAL_DISCLAIMER,
        licensing_note=EXPORT_LICENSING_NOTE,
        rendered_markdown=markdown,
        metadata={
            **_chat_session_export_metadata(metadata, generated_chat_answer=True),
            "compare_route_suggestions": [
                turn.compare_route_suggestion.model_dump(mode="json")
                for turn in turns
                if turn.compare_route_suggestion is not None
            ],
        },
    )
    return response.model_copy(
        update={
            "export_validation": _build_chat_export_validation(
                response,
                asset_ticker=metadata.selected_asset.ticker if metadata.selected_asset else None,
            )
        }
    )


def _chat_session_export_metadata(
    metadata: ChatSessionPublicMetadata,
    *,
    generated_chat_answer: bool,
) -> dict[str, Any]:
    return {
        "conversation_id": metadata.conversation_id,
        "session_lifecycle_state": metadata.lifecycle_state.value,
        "selected_ticker": metadata.selected_asset.ticker if metadata.selected_asset else None,
        "created_at": metadata.created_at,
        "last_activity_at": metadata.last_activity_at,
        "expires_at": metadata.expires_at,
        "deleted_at": metadata.deleted_at,
        "turn_count": metadata.turn_count,
        "latest_safety_classification": (
            metadata.latest_safety_classification.value if metadata.latest_safety_classification else None
        ),
        "latest_evidence_state": metadata.latest_evidence_state.value if metadata.latest_evidence_state else None,
        "latest_freshness_state": metadata.latest_freshness_state.value if metadata.latest_freshness_state else None,
        "export_available": metadata.export_available,
        "deletion_status": metadata.deletion_status.value,
        "generated_chat_answer": generated_chat_answer,
        "source": "local_accountless_chat_session",
    }


def _asset_page_sections(overview: OverviewResponse) -> list[ExportedSection]:
    sections: list[ExportedSection] = [
        ExportedSection(
            section_id="asset_identity",
            title="Asset Identity",
            section_type=OverviewSectionType.stable_facts,
            text=(
                f"{overview.asset.ticker} is {overview.asset.name}; asset type: "
                f"{overview.asset.asset_type.value}; exchange: {overview.asset.exchange or 'unknown'}."
            ),
            citation_ids=_claim_citation_ids(overview, "claim_factual_canonical_asset_identity"),
            source_document_ids=_source_ids_for_citation_ids(
                _claim_citation_ids(overview, "claim_factual_canonical_asset_identity"),
                overview.citations,
            ),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported,
        ),
        ExportedSection(
            section_id="page_freshness",
            title="Page Freshness",
            section_type=OverviewSectionType.stable_facts,
            text=(
                f"Page last updated: {overview.freshness.page_last_updated_at}; "
                f"facts as of: {overview.freshness.facts_as_of or 'unknown'}; "
                f"holdings as of: {overview.freshness.holdings_as_of or 'unknown'}; "
                f"recent events as of: {overview.freshness.recent_events_as_of or 'unknown'}; "
                f"freshness state: {overview.freshness.freshness_state.value}."
            ),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported,
        ),
    ]

    if overview.beginner_summary is not None:
        beginner_citations = _claim_citation_ids(overview, "claim_factual_beginner_summary")
        sections.append(
            ExportedSection(
                section_id="beginner_summary",
                title="Beginner Summary",
                section_type=OverviewSectionType.stable_facts,
                items=[
                    ExportedItem(
                        item_id="what_it_is",
                        title="What It Is",
                        text=_with_citations(overview.beginner_summary.what_it_is, beginner_citations),
                        citation_ids=beginner_citations,
                        source_document_ids=_source_ids_for_citation_ids(beginner_citations, overview.citations),
                        freshness_state=overview.freshness.freshness_state,
                        evidence_state=EvidenceState.supported,
                    ),
                    ExportedItem(
                        item_id="why_people_consider_it",
                        title="Why People Consider It",
                        text=overview.beginner_summary.why_people_consider_it,
                        freshness_state=overview.freshness.freshness_state,
                        evidence_state=EvidenceState.supported,
                    ),
                    ExportedItem(
                        item_id="main_catch",
                        title="Main Catch",
                        text=overview.beginner_summary.main_catch,
                        freshness_state=overview.freshness.freshness_state,
                        evidence_state=EvidenceState.supported,
                    ),
                ],
                citation_ids=beginner_citations,
                source_document_ids=_source_ids_for_citation_ids(beginner_citations, overview.citations),
                freshness_state=overview.freshness.freshness_state,
                evidence_state=EvidenceState.supported,
            )
        )

    sections.append(
        ExportedSection(
            section_id="top_risks",
            title="Top Risks",
            section_type=OverviewSectionType.risk,
            text="Exactly three top risks are exported first before any detailed risk expansion.",
            items=[
                ExportedItem(
                    item_id=f"top_risk_{index + 1}",
                    title=risk.title,
                    text=_with_citations(risk.plain_english_explanation, risk.citation_ids),
                    citation_ids=risk.citation_ids,
                    source_document_ids=_source_ids_for_citation_ids(risk.citation_ids, overview.citations),
                    freshness_state=_freshness_for_citation_ids(risk.citation_ids, overview.citations),
                    evidence_state=EvidenceState.supported,
                    metadata={"rank": index + 1},
                )
                for index, risk in enumerate(overview.top_risks[:3])
            ],
            citation_ids=sorted({citation_id for risk in overview.top_risks[:3] for citation_id in risk.citation_ids}),
            source_document_ids=sorted(
                {
                    source_id
                    for risk in overview.top_risks[:3]
                    for source_id in _source_ids_for_citation_ids(risk.citation_ids, overview.citations)
                }
            ),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported if len(overview.top_risks) == 3 else EvidenceState.insufficient_evidence,
        )
    )

    sections.append(
        ExportedSection(
            section_id="stable_claims",
            title="Stable Facts",
            section_type=OverviewSectionType.stable_facts,
            text="Stable fixture-backed claims are separated from recent-development context.",
            items=[
                ExportedItem(
                    item_id=claim.claim_id,
                    title=claim.claim_id,
                    text=_with_citations(claim.claim_text, claim.citation_ids),
                    citation_ids=claim.citation_ids,
                    source_document_ids=_source_ids_for_citation_ids(claim.citation_ids, overview.citations),
                    freshness_state=_freshness_for_citation_ids(claim.citation_ids, overview.citations),
                    evidence_state=EvidenceState.supported,
                )
                for claim in overview.claims
                if not claim.claim_id.startswith("claim_recent_")
            ],
            citation_ids=sorted(
                {
                    citation_id
                    for claim in overview.claims
                    if not claim.claim_id.startswith("claim_recent_")
                    for citation_id in claim.citation_ids
                }
            ),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported,
        )
    )

    sections.append(
        ExportedSection(
            section_id="weekly_news_focus",
            title="Weekly News Focus",
            section_type=OverviewSectionType.weekly_news_focus,
            text=(
                "Weekly News Focus is exported as timely context separate from stable facts. "
                f"Window: {overview.weekly_news_focus.window.news_window_start} through "
                f"{overview.weekly_news_focus.window.news_window_end}."
                if overview.weekly_news_focus
                else "Weekly News Focus is unavailable in this deterministic export."
            ),
            items=[
                ExportedItem(
                    item_id=item.event_id,
                    title=item.title,
                    text=_with_citations(item.summary, item.citation_ids),
                    citation_ids=item.citation_ids,
                    source_document_ids=[item.source.source_document_id],
                    freshness_state=item.freshness_state,
                    evidence_state=EvidenceState.supported,
                    event_date=item.event_date,
                    retrieved_at=item.source.retrieved_at,
                    metadata={
                        "period_bucket": item.period_bucket.value,
                        "source_quality": item.source.source_quality.value,
                        "source_use_policy": item.source.source_use_policy.value,
                        "allowlist_status": item.source.allowlist_status.value,
                        "importance_score": item.importance_score,
                    },
                )
                for item in (overview.weekly_news_focus.items if overview.weekly_news_focus else [])
            ],
            citation_ids=sorted(
                {citation_id for item in (overview.weekly_news_focus.items if overview.weekly_news_focus else []) for citation_id in item.citation_ids}
            ),
            source_document_ids=sorted(
                {item.source.source_document_id for item in (overview.weekly_news_focus.items if overview.weekly_news_focus else [])}
            ),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported
            if overview.weekly_news_focus and overview.weekly_news_focus.items
            else EvidenceState.no_high_signal,
            as_of_date=overview.weekly_news_focus.window.news_window_end if overview.weekly_news_focus else None,
        )
    )

    sections.append(
        ExportedSection(
            section_id="ai_comprehensive_analysis",
            title="AI Comprehensive Analysis",
            section_type=OverviewSectionType.ai_comprehensive_analysis,
            text=(
                "AI Comprehensive Analysis is suppressed unless at least two approved Weekly News Focus items exist."
                if overview.ai_comprehensive_analysis and not overview.ai_comprehensive_analysis.analysis_available
                else "AI Comprehensive Analysis is exported as cited timely context separate from stable facts."
            ),
            items=[
                ExportedItem(
                    item_id=section.section_id,
                    title=section.label,
                    text=_with_citations(
                        " ".join([section.analysis, *section.bullets, *section.uncertainty]),
                        section.citation_ids,
                    ),
                    citation_ids=section.citation_ids,
                    source_document_ids=overview.ai_comprehensive_analysis.source_document_ids,
                    freshness_state=overview.freshness.freshness_state,
                    evidence_state=EvidenceState.supported,
                    metadata={"analysis_section_label": section.label},
                )
                for section in (overview.ai_comprehensive_analysis.sections if overview.ai_comprehensive_analysis else [])
            ],
            citation_ids=overview.ai_comprehensive_analysis.citation_ids if overview.ai_comprehensive_analysis else [],
            source_document_ids=overview.ai_comprehensive_analysis.source_document_ids if overview.ai_comprehensive_analysis else [],
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.supported
            if overview.ai_comprehensive_analysis and overview.ai_comprehensive_analysis.analysis_available
            else EvidenceState.insufficient_evidence,
            limitations=overview.ai_comprehensive_analysis.suppression_reason if overview.ai_comprehensive_analysis else None,
        )
    )

    sections.append(
        ExportedSection(
            section_id="recent_developments",
            title="Recent Developments",
            section_type=OverviewSectionType.recent_developments,
            text="Recent developments are exported separately from stable facts.",
            items=[
                ExportedItem(
                    item_id=f"recent_development_{index + 1}",
                    title=recent.title,
                    text=_with_citations(recent.summary, recent.citation_ids),
                    citation_ids=recent.citation_ids,
                    source_document_ids=_source_ids_for_citation_ids(recent.citation_ids, overview.citations),
                    freshness_state=recent.freshness_state,
                    evidence_state=EvidenceState.no_major_recent_development,
                    event_date=recent.event_date,
                )
                for index, recent in enumerate(overview.recent_developments)
            ],
            citation_ids=sorted({citation_id for recent in overview.recent_developments for citation_id in recent.citation_ids}),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.no_major_recent_development,
        )
    )

    if overview.suitability_summary is not None:
        suitability_citations = _claim_citation_ids(overview, "claim_risk_suitability_framing")
        sections.append(
            ExportedSection(
                section_id="educational_suitability",
                title="Educational Suitability",
                section_type=OverviewSectionType.educational_suitability,
                items=[
                    ExportedItem(
                        item_id="may_fit",
                        title="May Fit Learning About",
                        text=overview.suitability_summary.may_fit,
                        evidence_state=EvidenceState.supported,
                    ),
                    ExportedItem(
                        item_id="may_not_fit",
                        title="May Not Fit Learning About",
                        text=overview.suitability_summary.may_not_fit,
                        evidence_state=EvidenceState.supported,
                    ),
                    ExportedItem(
                        item_id="learn_next",
                        title="Learn Next",
                        text=overview.suitability_summary.learn_next,
                        citation_ids=suitability_citations,
                        source_document_ids=_source_ids_for_citation_ids(suitability_citations, overview.citations),
                        freshness_state=_freshness_for_citation_ids(suitability_citations, overview.citations),
                        evidence_state=EvidenceState.supported,
                    ),
                ],
                citation_ids=suitability_citations,
                source_document_ids=_source_ids_for_citation_ids(suitability_citations, overview.citations),
                freshness_state=overview.freshness.freshness_state,
                evidence_state=EvidenceState.supported,
            )
        )

    existing_section_ids = {section.section_id for section in sections}
    sections.extend(
        _export_overview_section(section)
        for section in overview.sections
        if section.section_id not in existing_section_ids
    )

    sections.append(
        ExportedSection(
            section_id="prd_sections",
            title="PRD Section Summaries",
            section_type=OverviewSectionType.stable_facts,
            text="Each item preserves its section evidence state, freshness state, source IDs, and citation IDs.",
            items=[
                _export_prd_section_item(section)
                for section in overview.sections
            ],
            citation_ids=sorted({citation_id for section in overview.sections for citation_id in section.citation_ids}),
            source_document_ids=sorted({source_id for section in overview.sections for source_id in section.source_document_ids}),
            freshness_state=overview.freshness.freshness_state,
            evidence_state=EvidenceState.mixed
            if any(section.evidence_state is not EvidenceState.supported for section in overview.sections)
            else EvidenceState.supported,
        )
    )

    return sections


def _export_overview_section(section: Any) -> ExportedSection:
    section_items = [
        ExportedItem(
            item_id=item.item_id,
            title=item.title,
            text=_with_citations(item.summary, item.citation_ids),
            citation_ids=item.citation_ids,
            source_document_ids=item.source_document_ids,
            freshness_state=item.freshness_state,
            evidence_state=item.evidence_state,
            event_date=item.event_date,
            as_of_date=item.as_of_date,
            retrieved_at=item.retrieved_at,
            metadata={"limitations": item.limitations} if item.limitations else {},
        )
        for item in section.items
    ]
    section_items.extend(
        ExportedItem(
            item_id=metric.metric_id,
            title=metric.label,
            text=_with_citations(_metric_value(metric.value, metric.unit), metric.citation_ids),
            citation_ids=metric.citation_ids,
            source_document_ids=metric.source_document_ids,
            freshness_state=metric.freshness_state,
            evidence_state=metric.evidence_state,
            as_of_date=metric.as_of_date,
            retrieved_at=metric.retrieved_at,
            metadata={"limitations": metric.limitations} if metric.limitations else {},
        )
        for metric in section.metrics
    )
    return ExportedSection(
        section_id=section.section_id,
        title=section.title,
        section_type=section.section_type,
        text=section.beginner_summary,
        items=section_items,
        citation_ids=section.citation_ids,
        source_document_ids=section.source_document_ids,
        freshness_state=section.freshness_state,
        evidence_state=section.evidence_state,
        as_of_date=section.as_of_date,
        retrieved_at=section.retrieved_at,
        limitations=section.limitations,
    )


def _export_prd_section_item(section: Any) -> ExportedItem:
    evidence_parts = [f"Evidence state: {section.evidence_state.value}."]
    if section.beginner_summary:
        evidence_parts.append(section.beginner_summary)
    if section.limitations:
        evidence_parts.append(f"Limitations: {section.limitations}")
    if section.items:
        evidence_parts.extend(f"{item.title}: {item.summary}" for item in section.items)
    if section.metrics:
        evidence_parts.extend(
            f"{metric.label}: {_metric_value(metric.value, metric.unit)}; evidence state: {metric.evidence_state.value}."
            for metric in section.metrics
        )
    return ExportedItem(
        item_id=section.section_id,
        title=section.title,
        text=_with_citations(" ".join(evidence_parts), section.citation_ids),
        citation_ids=section.citation_ids,
        source_document_ids=section.source_document_ids,
        freshness_state=section.freshness_state,
        evidence_state=section.evidence_state,
        as_of_date=section.as_of_date,
        retrieved_at=section.retrieved_at,
        metadata={
            "section_type": section.section_type.value,
            "item_count": len(section.items),
            "metric_count": len(section.metrics),
        },
    )


def _blocked_asset_response(
    ticker: str,
    content_type: ExportContentType,
    export_format: ExportFormat | str,
) -> ExportResponse | None:
    search = search_assets(ticker)
    result = search.results[0]
    if result.support_classification is SearchSupportClassification.cached_supported:
        return None

    asset_status = (
        AssetStatus.unsupported
        if result.support_classification is SearchSupportClassification.recognized_unsupported
        else AssetStatus.unknown
    )
    asset = AssetIdentity(
        ticker=result.ticker,
        name=result.name,
        asset_type=result.asset_type,
        exchange=result.exchange,
        issuer=result.issuer,
        status=asset_status,
        supported=False,
    )
    state = StateMessage(status=asset_status, message=result.message or search.state.message)
    title = f"{asset.ticker} {content_type.value.replace('_', ' ')} export"
    return _unavailable_asset_response(asset, state, content_type, export_format)


def _unavailable_asset_response(
    asset: AssetIdentity,
    state: StateMessage,
    content_type: ExportContentType,
    export_format: ExportFormat | str,
) -> ExportResponse:
    title = f"{asset.ticker} {content_type.value.replace('_', ' ')} export"
    response = ExportResponse(
        content_type=content_type,
        export_format=_coerce_format(export_format),
        export_state=_export_state_from_asset_status(state.status),
        title=title,
        state=state,
        asset=asset,
        sections=[],
        citations=[],
        source_documents=[],
        disclaimer=EDUCATIONAL_DISCLAIMER,
        licensing_note=EXPORT_LICENSING_NOTE,
        rendered_markdown=_unavailable_markdown(title, state.message),
        metadata={"generated_asset_output": False, "source": "local_fixture_export_block"},
    )
    return response.model_copy(
        update={
            "export_validation": _build_unavailable_export_validation(
                response,
                binding_scope=ExportValidationBindingScope.unavailable,
            )
        }
    )


def _export_citations_from_overview(overview: OverviewResponse) -> list[ExportCitation]:
    claim_by_citation = _claim_by_citation_id(
        [(claim.claim_text, claim.citation_ids) for claim in overview.claims]
        + [(risk.plain_english_explanation, risk.citation_ids) for risk in overview.top_risks]
        + [(recent.summary, recent.citation_ids) for recent in overview.recent_developments]
    )
    return [
        _export_citation(citation, claim_by_citation.get(citation.citation_id))
        for citation in overview.citations
    ]


def _export_citations_from_comparison(comparison: Any) -> list[ExportCitation]:
    claim_by_citation = _claim_by_citation_id(
        [(item.plain_english_summary, item.citation_ids) for item in comparison.key_differences]
        + (
            [(comparison.bottom_line_for_beginners.summary, comparison.bottom_line_for_beginners.citation_ids)]
            if comparison.bottom_line_for_beginners
            else []
        )
    )
    return [_export_citation(citation, claim_by_citation.get(citation.citation_id)) for citation in comparison.citations]


def _export_citations_from_chat(citations: list[Any], sources: list[ChatSourceDocument]) -> list[ExportCitation]:
    sources_by_citation_id = {source.citation_id: source for source in sources}
    exported: list[ExportCitation] = []
    for citation in citations:
        source = sources_by_citation_id.get(citation.citation_id)
        exported.append(
            ExportCitation(
                citation_id=citation.citation_id,
                source_document_id=citation.source_document_id,
                title=source.title if source else None,
                publisher=source.publisher if source else None,
                freshness_state=source.freshness_state if source else None,
                claim=citation.claim,
            )
        )
    return exported


def _export_citation(citation: Citation, claim: str | None) -> ExportCitation:
    return ExportCitation(
        citation_id=citation.citation_id,
        source_document_id=citation.source_document_id,
        title=citation.title,
        publisher=citation.publisher,
        freshness_state=citation.freshness_state,
        claim=claim,
    )


def _export_sources(sources: list[Any]) -> list[ExportSourceMetadata]:
    exported: list[ExportSourceMetadata] = []
    seen: set[tuple[str, str | None]] = set()
    for source in sources:
        citation_id = getattr(source, "citation_id", None)
        key = (source.source_document_id, citation_id)
        if key in seen:
            continue
        seen.add(key)
        chunk_id = getattr(source, "chunk_id", None)
        supporting_passage = getattr(source, "supporting_passage", "")
        decision = _decision_from_source_like(source)
        if decision.decision is not SourcePolicyDecisionState.allowed:
            continue
        handoff = validate_source_handoff(_source_like_with_policy(source, decision), action=SourcePolicyAction.diagnostics)
        if not handoff.allowed:
            continue
        excerpt_text = excerpt_text_for_policy(supporting_passage, decision)
        excerpt_decision = decision if source_can_export_excerpt(decision) else _resolved_decision_from_source_like(source)
        exported.append(
            ExportSourceMetadata(
                source_document_id=source.source_document_id,
                title=source.title,
                source_type=source.source_type,
                publisher=source.publisher,
                url=source.url,
                published_at=source.published_at,
                as_of_date=source.as_of_date,
                retrieved_at=source.retrieved_at,
                freshness_state=source.freshness_state,
                is_official=source.is_official,
                source_quality=getattr(source, "source_quality", decision.source_quality),
                allowlist_status=getattr(source, "allowlist_status", decision.allowlist_status),
                source_use_policy=getattr(source, "source_use_policy", decision.source_use_policy),
                permitted_operations=decision.permitted_operations,
                source_identity=getattr(source, "source_identity", None) or getattr(source, "url", None),
                storage_rights=getattr(source, "storage_rights", "raw_snapshot_allowed"),
                export_rights=getattr(source, "export_rights", "excerpts_allowed"),
                review_status=getattr(source, "review_status", "approved"),
                approval_rationale=getattr(
                    source,
                    "approval_rationale",
                    "Deterministic fixture source passed local source-use policy review.",
                ),
                parser_status=getattr(source, "parser_status", "parsed"),
                parser_failure_diagnostics=getattr(source, "parser_failure_diagnostics", None),
                allowed_excerpt=ExportExcerpt(
                    excerpt_id=f"excerpt_{citation_id or source.source_document_id}",
                    kind="supporting_passage" if source_can_export_excerpt(decision) else "excerpt_metadata",
                    text=excerpt_text,
                    citation_id=citation_id,
                    chunk_id=chunk_id,
                    redistribution_allowed=decision.permitted_operations.can_export_excerpt,
                    source_use_policy=excerpt_decision.source_use_policy,
                    allowlist_status=excerpt_decision.allowlist_status,
                    note=excerpt_decision.allowed_excerpt.note,
                ),
            )
        )
    return exported


def _render_markdown(
    title: str,
    sections: list[ExportedSection],
    sources: list[Any],
    freshness: Freshness | None,
) -> str:
    lines = [f"# {title}", ""]
    if freshness is not None:
        lines.extend(
            [
                f"Freshness: {freshness.freshness_state.value}",
                f"Page last updated: {freshness.page_last_updated_at}",
                "",
            ]
        )
    for section in sections:
        lines.extend([f"## {section.title}", ""])
        if section.text:
            lines.extend([section.text, ""])
        if section.evidence_state is not None:
            lines.append(f"Evidence state: {section.evidence_state.value}")
        if section.freshness_state is not None:
            lines.append(f"Freshness state: {section.freshness_state.value}")
        if section.citation_ids:
            lines.append(f"Citations: {', '.join(section.citation_ids)}")
        if section.source_document_ids:
            lines.append(f"Sources: {', '.join(section.source_document_ids)}")
        if section.items:
            lines.append("")
            for item in section.items:
                lines.append(f"- {item.title}: {item.text}")
                if item.citation_ids:
                    lines.append(f"  Citations: {', '.join(item.citation_ids)}")
                if item.freshness_state is not None:
                    lines.append(f"  Freshness: {item.freshness_state.value}")
                if item.evidence_state is not None:
                    lines.append(f"  Evidence: {item.evidence_state.value}")
        lines.append("")
    if sources:
        lines.extend(["## Sources", ""])
        for source in sources:
            lines.append(
                f"- {source.source_document_id}: {source.title} ({source.publisher}); "
                f"type: {source.source_type}; retrieved: {source.retrieved_at}; "
                f"freshness: {source.freshness_state.value}; "
                f"source-use policy: {getattr(source, 'source_use_policy', None).value if getattr(source, 'source_use_policy', None) else 'unknown'}; "
                f"allowlist status: {getattr(source, 'allowlist_status', None).value if getattr(source, 'allowlist_status', None) else 'unknown'}; "
                f"URL: {source.url}"
            )
        lines.append("")
    lines.extend(["## Licensing Note", EXPORT_LICENSING_NOTE.text, "", "## Educational Disclaimer", EDUCATIONAL_DISCLAIMER])
    return "\n".join(lines)


def _unavailable_markdown(title: str, message: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "Export unavailable.",
            "",
            message,
            "",
            "## Licensing Note",
            EXPORT_LICENSING_NOTE.text,
            "",
            "## Educational Disclaimer",
            EDUCATIONAL_DISCLAIMER,
        ]
    )


def _claim_by_citation_id(claims: list[tuple[str, list[str]]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for claim_text, citation_ids in claims:
        for citation_id in citation_ids:
            result.setdefault(citation_id, claim_text)
    return result


def _claim_citation_ids(overview: OverviewResponse, claim_id: str) -> list[str]:
    for claim in overview.claims:
        if claim.claim_id == claim_id:
            return claim.citation_ids
    return []


def _source_ids_for_citation_ids(citation_ids: list[str], citations: list[Citation]) -> list[str]:
    source_ids = {
        citation.source_document_id
        for citation in citations
        if citation.citation_id in set(citation_ids)
    }
    return sorted(source_ids)


def _dedupe_by_id(items: list[Any], id_field: str) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for item in items:
        item_id = getattr(item, id_field)
        if item_id in seen:
            continue
        seen.add(item_id)
        result.append(item)
    return result


def _freshness_for_citation_ids(citation_ids: list[str], citations: list[Citation]) -> FreshnessState | None:
    states = [citation.freshness_state for citation in citations if citation.citation_id in set(citation_ids)]
    if not states:
        return None
    if any(state is FreshnessState.stale for state in states):
        return FreshnessState.stale
    if any(state is FreshnessState.unavailable for state in states):
        return FreshnessState.unavailable
    if any(state is FreshnessState.unknown for state in states):
        return FreshnessState.unknown
    return FreshnessState.fresh


def _with_citations(text: str, citation_ids: list[str]) -> str:
    if not citation_ids:
        return text
    return f"{text} [{', '.join(citation_ids)}]"


def _build_asset_export_validation(
    export: ExportResponse,
    overview: OverviewResponse,
) -> ExportValidation:
    citation_sections, source_sections = _collect_export_section_maps(export.sections)
    source_bindings, source_binding_ids_by_source = _build_export_source_bindings(
        export.source_documents,
        source_sections,
        binding_scope=ExportValidationBindingScope.same_asset,
        asset_ticker=overview.asset.ticker,
    )
    citation_bindings, citation_binding_ids_by_citation = _build_export_citation_bindings(
        export.citations,
        export.source_documents,
        citation_sections,
        binding_scope=ExportValidationBindingScope.same_asset,
        asset_ticker=overview.asset.ticker,
    )
    overview_validations = {
        validation.section_id: validation
        for validation in overview.section_freshness_validation
    }
    section_validations = [
        _build_export_section_validation(
            section,
            citation_binding_ids_by_citation=citation_binding_ids_by_citation,
            source_binding_ids_by_source=source_binding_ids_by_source,
            overview_validation=overview_validations.get(section.section_id),
        )
        for section in export.sections
        if _section_requires_export_validation(section)
    ]
    return _finalize_export_validation(
        export,
        binding_scope=ExportValidationBindingScope.same_asset,
        citation_bindings=citation_bindings,
        source_bindings=source_bindings,
        section_validations=section_validations,
        diagnostics=ExportValidationDiagnostics(
            same_asset_citation_bindings_only=True,
            same_asset_source_bindings_only=True,
            used_existing_overview_contract=True,
        ),
    )


def _build_comparison_export_validation(
    export: ExportResponse,
    comparison: Any,
) -> ExportValidation:
    comparison_id = (
        comparison.evidence_availability.comparison_id
        if getattr(comparison, "evidence_availability", None) is not None
        else f"{comparison.left_asset.ticker}_vs_{comparison.right_asset.ticker}"
    )
    citation_sections, source_sections = _collect_export_section_maps(export.sections)
    evidence = getattr(comparison, "evidence_availability", None)
    source_asset_tickers = {
        source.source_document_id: source.asset_ticker
        for source in (evidence.source_references if evidence is not None else [])
    }
    supported_citation_ids = {
        binding.citation_id
        for binding in (evidence.citation_bindings if evidence is not None else [])
    }
    supported_source_ids = {
        source.source_document_id
        for source in (evidence.source_references if evidence is not None else [])
    }
    source_bindings, source_binding_ids_by_source = _build_export_source_bindings(
        export.source_documents,
        source_sections,
        binding_scope=ExportValidationBindingScope.same_comparison_pack,
        comparison_id=comparison_id,
        source_asset_tickers_by_id=source_asset_tickers,
    )
    citation_bindings, citation_binding_ids_by_citation = _build_export_citation_bindings(
        export.citations,
        export.source_documents,
        citation_sections,
        binding_scope=ExportValidationBindingScope.same_comparison_pack,
        comparison_id=comparison_id,
        source_asset_tickers_by_id=source_asset_tickers,
    )
    missing_citations = sorted(
        citation.citation_id for citation in export.citations if citation.citation_id not in supported_citation_ids
    )
    missing_sources = sorted(
        source.source_document_id for source in export.source_documents if source.source_document_id not in supported_source_ids
    )
    section_validations = [
        _build_export_section_validation(
            section,
            citation_binding_ids_by_citation=citation_binding_ids_by_citation,
            source_binding_ids_by_source=source_binding_ids_by_source,
        )
        for section in export.sections
        if _section_requires_export_validation(section)
    ]
    diagnostics = ExportValidationDiagnostics(
        same_comparison_pack_citation_bindings_only=not missing_citations,
        same_comparison_pack_source_bindings_only=not missing_sources,
        used_existing_comparison_contract=evidence is not None,
        mismatch_reasons=[
            *(
                [f"Comparison export citations missing from local comparison-pack evidence: {', '.join(missing_citations)}"]
                if missing_citations
                else []
            ),
            *(
                [f"Comparison export sources missing from local comparison-pack evidence: {', '.join(missing_sources)}"]
                if missing_sources
                else []
            ),
        ],
    )
    return _finalize_export_validation(
        export,
        binding_scope=ExportValidationBindingScope.same_comparison_pack,
        citation_bindings=citation_bindings,
        source_bindings=source_bindings,
        section_validations=section_validations,
        diagnostics=diagnostics,
    )


def _build_chat_export_validation(
    export: ExportResponse,
    *,
    asset_ticker: str | None,
) -> ExportValidation:
    citation_sections, source_sections = _collect_export_section_maps(export.sections)
    if export.citations or export.source_documents:
        source_bindings, source_binding_ids_by_source = _build_export_source_bindings(
            export.source_documents,
            source_sections,
            binding_scope=ExportValidationBindingScope.same_asset,
            asset_ticker=asset_ticker,
        )
        citation_bindings, citation_binding_ids_by_citation = _build_export_citation_bindings(
            export.citations,
            export.source_documents,
            citation_sections,
            binding_scope=ExportValidationBindingScope.same_asset,
            asset_ticker=asset_ticker,
        )
        section_validations = [
            _build_export_section_validation(
                section,
                citation_binding_ids_by_citation=citation_binding_ids_by_citation,
                source_binding_ids_by_source=source_binding_ids_by_source,
            )
            for section in export.sections
            if _section_requires_export_validation(section)
        ]
        diagnostics = ExportValidationDiagnostics(
            same_asset_citation_bindings_only=True,
            same_asset_source_bindings_only=True,
            used_existing_chat_contract=True,
        )
        return _finalize_export_validation(
            export,
            binding_scope=ExportValidationBindingScope.same_asset,
            citation_bindings=citation_bindings,
            source_bindings=source_bindings,
            section_validations=section_validations,
            diagnostics=diagnostics,
        )

    safety_classification = export.metadata.get("safety_classification")
    compare_route_suggestion = export.metadata.get("compare_route_suggestion") or export.metadata.get("compare_route_suggestions")
    limitation = "This available chat export does not include source-backed factual content."
    if safety_classification == SafetyClassification.personalized_advice_redirect.value:
        limitation = "Safety redirect export does not include same-asset factual citations, source documents, or freshness support."
    if safety_classification == SafetyClassification.compare_route_redirect.value or compare_route_suggestion:
        limitation = (
            "Comparison redirect export preserves workflow guidance and compare-route metadata only; "
            "it does not export cross-asset factual citations, source documents, or generated comparison content."
        )
    section_validations = [
        ExportSectionValidation(
            section_id="chat_answer",
            section_type=ExportContentType.chat_transcript,
            displayed_evidence_state=EvidenceState.unsupported
            if safety_classification
            in {
                SafetyClassification.personalized_advice_redirect.value,
                SafetyClassification.compare_route_redirect.value,
            }
            else EvidenceState.insufficient_evidence,
            validated_evidence_state=EvidenceState.unsupported
            if safety_classification
            in {
                SafetyClassification.personalized_advice_redirect.value,
                SafetyClassification.compare_route_redirect.value,
            }
            else EvidenceState.insufficient_evidence,
            validated_freshness_state=FreshnessState.unknown,
            validation_outcome=ExportValidationOutcome.validated_with_limitations,
            limitation_message=limitation,
        )
    ]
    return _finalize_export_validation(
        export,
        binding_scope=ExportValidationBindingScope.no_factual_evidence,
        citation_bindings=[],
        source_bindings=[],
        section_validations=section_validations,
        diagnostics=ExportValidationDiagnostics(
            used_existing_chat_contract=True,
            empty_factual_evidence_export=True,
            limitation_reasons=[limitation],
        ),
        default_evidence_state=(
            EvidenceState.unsupported
            if safety_classification
            in {
                SafetyClassification.personalized_advice_redirect.value,
                SafetyClassification.compare_route_redirect.value,
            }
            else EvidenceState.insufficient_evidence
        ),
    )


def _build_unavailable_export_validation(
    export: ExportResponse,
    *,
    binding_scope: ExportValidationBindingScope,
) -> ExportValidation:
    evidence_state = (
        EvidenceState.unsupported
        if export.export_state is ExportState.unsupported
        else EvidenceState.unavailable
    )
    limitation = f"Export state {export.export_state.value} has no exportable local evidence payload."
    return _finalize_export_validation(
        export,
        binding_scope=binding_scope,
        citation_bindings=[],
        source_bindings=[],
        section_validations=[],
        diagnostics=ExportValidationDiagnostics(
            empty_factual_evidence_export=True,
            limitation_reasons=[limitation],
        ),
        default_evidence_state=evidence_state,
        limitation_message=limitation,
    )


def _finalize_export_validation(
    export: ExportResponse,
    *,
    binding_scope: ExportValidationBindingScope,
    citation_bindings: list[ExportValidationCitationBinding],
    source_bindings: list[ExportValidationSourceBinding],
    section_validations: list[ExportSectionValidation],
    diagnostics: ExportValidationDiagnostics,
    default_evidence_state: EvidenceState | None = None,
    limitation_message: str | None = None,
) -> ExportValidation:
    restriction_messages = sorted(
        {
            message
            for binding in source_bindings
            for message in [binding.restricted_content_message, binding.omitted_content_message]
            if message
        }
    )
    section_limitations = [item.limitation_message for item in section_validations if item.limitation_message]
    diagnostics = diagnostics.model_copy(
        update={
            "restricted_content_messages": restriction_messages,
            "limitation_reasons": sorted({*diagnostics.limitation_reasons, *section_limitations, *restriction_messages}),
            "mismatch_reasons": sorted(
                {
                    *diagnostics.mismatch_reasons,
                    *[item.mismatch_message for item in section_validations if item.mismatch_message],
                }
            ),
        }
    )
    mismatch_message = "; ".join(diagnostics.mismatch_reasons) or None
    combined_limitation = limitation_message or "; ".join(diagnostics.limitation_reasons) or None
    overall_outcome = _overall_export_validation_outcome(section_validations, diagnostics)
    validated_evidence_state = _overall_validated_evidence_state(section_validations, default_evidence_state)
    return ExportValidation(
        content_type=export.content_type,
        export_state=export.export_state,
        binding_scope=binding_scope,
        validation_outcome=overall_outcome,
        validated_evidence_state=validated_evidence_state,
        citation_bindings=citation_bindings,
        source_bindings=source_bindings,
        section_validations=section_validations,
        limitation_message=combined_limitation,
        mismatch_message=mismatch_message,
        diagnostics=diagnostics,
    )


def _collect_export_section_maps(
    sections: list[ExportedSection],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    citation_sections: dict[str, set[str]] = {}
    source_sections: dict[str, set[str]] = {}
    for section in sections:
        citation_ids = set(section.citation_ids)
        source_ids = set(section.source_document_ids)
        for item in section.items:
            citation_ids.update(item.citation_ids)
            source_ids.update(item.source_document_ids)
        for citation_id in citation_ids:
            citation_sections.setdefault(citation_id, set()).add(section.section_id)
        for source_id in source_ids:
            source_sections.setdefault(source_id, set()).add(section.section_id)
    return citation_sections, source_sections


def _build_export_source_bindings(
    sources: list[ExportSourceMetadata],
    source_sections: dict[str, set[str]],
    *,
    binding_scope: ExportValidationBindingScope,
    asset_ticker: str | None = None,
    comparison_id: str | None = None,
    source_asset_tickers_by_id: dict[str, str] | None = None,
) -> tuple[list[ExportValidationSourceBinding], dict[str, list[str]]]:
    bindings: list[ExportValidationSourceBinding] = []
    binding_ids_by_source: dict[str, list[str]] = {}
    for index, source in enumerate(sources):
        excerpt = source.allowed_excerpt
        binding_id = f"source_binding_{index + 1}_{source.source_document_id}"
        restricted_message = (
            "Full source text remains unavailable for export under the current source-use policy."
            if source.permitted_operations.can_export_full_text is False
            else None
        )
        omitted_message = None
        if not source_can_export_source_metadata(
            _decision_from_export_source(source)
        ):
            omitted_message = "Source metadata is restricted to policy-safe attribution fields only."
        if excerpt is not None and excerpt.kind == "excerpt_metadata":
            omitted_message = omitted_message or "Only metadata or bounded excerpt metadata is exportable for this source."
        bindings.append(
            ExportValidationSourceBinding(
                binding_id=binding_id,
                source_document_id=source.source_document_id,
                asset_ticker=(
                    asset_ticker
                    if asset_ticker is not None
                    else (source_asset_tickers_by_id or {}).get(source.source_document_id)
                ),
                comparison_id=comparison_id,
                section_ids=sorted(source_sections.get(source.source_document_id, set())),
                source_type=source.source_type,
                freshness_state=source.freshness_state,
                published_at=source.published_at,
                as_of_date=source.as_of_date,
                retrieved_at=source.retrieved_at,
                source_use_policy=source.source_use_policy,
                allowlist_status=source.allowlist_status,
                permitted_operations=source.permitted_operations,
                allowed_excerpt_id=excerpt.excerpt_id if excerpt is not None else None,
                allowed_excerpt_kind=excerpt.kind if excerpt is not None else None,
                excerpt_exported=bool(excerpt and excerpt.text),
                excerpt_metadata_only=bool(excerpt and excerpt.kind == "excerpt_metadata"),
                restricted_content_message=restricted_message,
                omitted_content_message=omitted_message or (excerpt.note if excerpt and excerpt.kind == "excerpt_metadata" else None),
            )
        )
        binding_ids_by_source.setdefault(source.source_document_id, []).append(binding_id)
    return bindings, binding_ids_by_source


def _build_export_citation_bindings(
    citations: list[ExportCitation],
    sources: list[ExportSourceMetadata],
    citation_sections: dict[str, set[str]],
    *,
    binding_scope: ExportValidationBindingScope,
    asset_ticker: str | None = None,
    comparison_id: str | None = None,
    source_asset_tickers_by_id: dict[str, str] | None = None,
) -> tuple[list[ExportValidationCitationBinding], dict[str, list[str]]]:
    source_lookup = _source_lookup_for_citations(sources)
    fallback_decision = resolve_source_policy()
    bindings: list[ExportValidationCitationBinding] = []
    binding_ids_by_citation: dict[str, list[str]] = {}
    for citation in citations:
        source = source_lookup.get(citation.citation_id) or source_lookup.get(citation.source_document_id)
        binding_id = f"citation_binding_{citation.citation_id}"
        bindings.append(
            ExportValidationCitationBinding(
                binding_id=binding_id,
                citation_id=citation.citation_id,
                source_document_id=citation.source_document_id,
                asset_ticker=(
                    asset_ticker
                    if asset_ticker is not None
                    else (source_asset_tickers_by_id or {}).get(citation.source_document_id)
                ),
                comparison_id=comparison_id,
                section_ids=sorted(citation_sections.get(citation.citation_id, set())),
                freshness_state=citation.freshness_state,
                source_use_policy=source.source_use_policy if source is not None else fallback_decision.source_use_policy,
                allowlist_status=source.allowlist_status if source is not None else fallback_decision.allowlist_status,
                permitted_operations=source.permitted_operations if source is not None else fallback_decision.permitted_operations,
                scope=binding_scope,
                supports_exported_content=bool(
                    source is not None
                    and source_can_support_markdown_json_export(_decision_from_export_source(source))
                    and validate_source_handoff(source, action=SourcePolicyAction.markdown_json_section_export).allowed
                ),
            )
        )
        binding_ids_by_citation.setdefault(citation.citation_id, []).append(binding_id)
    return bindings, binding_ids_by_citation


def _source_lookup_for_citations(sources: list[ExportSourceMetadata]) -> dict[str, ExportSourceMetadata]:
    lookup: dict[str, ExportSourceMetadata] = {}
    for source in sources:
        lookup.setdefault(source.source_document_id, source)
        if source.allowed_excerpt and source.allowed_excerpt.citation_id:
            lookup[source.allowed_excerpt.citation_id] = source
    return lookup


def _decision_from_source_like(source: Any) -> Any:
    resolved = _resolved_decision_from_source_like(source)
    allowlist_status = getattr(source, "allowlist_status", None)
    source_use_policy = getattr(source, "source_use_policy", None)
    permitted_operations = getattr(source, "permitted_operations", None)
    if allowlist_status is None or source_use_policy is None or permitted_operations is None:
        return resolved

    normalized_allowlist = (
        allowlist_status
        if isinstance(allowlist_status, SourceAllowlistStatus)
        else SourceAllowlistStatus(str(allowlist_status))
    )
    normalized_policy = (
        source_use_policy if isinstance(source_use_policy, SourceUsePolicy) else SourceUsePolicy(str(source_use_policy))
    )
    decision_state = (
        SourcePolicyDecisionState.allowed
        if normalized_allowlist is SourceAllowlistStatus.allowed
        else SourcePolicyDecisionState.rejected
        if normalized_allowlist is SourceAllowlistStatus.rejected
        else SourcePolicyDecisionState.pending_review
    )
    return resolved.model_copy(
        update={
            "decision": decision_state,
            "source_quality": getattr(source, "source_quality", resolved.source_quality),
            "allowlist_status": normalized_allowlist,
            "source_use_policy": normalized_policy,
            "permitted_operations": permitted_operations,
        }
    )


def _source_like_with_policy(source: Any, decision: Any) -> dict[str, Any]:
    return {
        "source_document_id": getattr(source, "source_document_id", None),
        "source_identity": getattr(source, "source_identity", None) or getattr(source, "url", None) or getattr(source, "source_document_id", None),
        "url": getattr(source, "url", None),
        "source_type": getattr(source, "source_type", None),
        "is_official": getattr(source, "is_official", False),
        "source_quality": getattr(source, "source_quality", decision.source_quality),
        "allowlist_status": getattr(source, "allowlist_status", decision.allowlist_status),
        "source_use_policy": getattr(source, "source_use_policy", decision.source_use_policy),
        "permitted_operations": getattr(source, "permitted_operations", decision.permitted_operations),
        "storage_rights": getattr(source, "storage_rights", "raw_snapshot_allowed"),
        "export_rights": getattr(source, "export_rights", "excerpts_allowed"),
        "review_status": getattr(source, "review_status", "approved"),
        "approval_rationale": getattr(source, "approval_rationale", decision.reason),
        "parser_status": getattr(source, "parser_status", "parsed"),
        "parser_failure_diagnostics": getattr(source, "parser_failure_diagnostics", None),
        "freshness_state": getattr(source, "freshness_state", FreshnessState.fresh),
        "as_of_date": getattr(source, "as_of_date", None),
        "published_at": getattr(source, "published_at", None),
        "retrieved_at": getattr(source, "retrieved_at", None),
        "cache_allowed": getattr(source, "cache_allowed", True),
        "export_allowed": getattr(source, "export_allowed", True),
    }


def _resolved_decision_from_source_like(source: Any) -> Any:
    return resolve_source_policy(
        url=getattr(source, "url", None),
        source_identifier=(
            getattr(source, "url", None)
            if str(getattr(source, "url", "")).startswith("local://")
            else None
        ),
        provider_name=getattr(source, "provider_name", None),
    )


def _decision_from_export_source(source: ExportSourceMetadata) -> Any:
    return _decision_from_source_like(source).model_copy(
        update={
            "source_quality": source.source_quality,
            "allowlist_status": source.allowlist_status,
            "source_use_policy": source.source_use_policy,
            "permitted_operations": source.permitted_operations,
        }
    )


def _build_export_section_validation(
    section: ExportedSection,
    *,
    citation_binding_ids_by_citation: dict[str, list[str]],
    source_binding_ids_by_source: dict[str, list[str]],
    overview_validation: OverviewSectionFreshnessValidation | None = None,
) -> ExportSectionValidation:
    citation_binding_ids = _binding_ids_for_section_citations(section, citation_binding_ids_by_citation)
    source_binding_ids = _binding_ids_for_section_sources(section, source_binding_ids_by_source)
    if overview_validation is not None:
        return ExportSectionValidation(
            section_id=section.section_id,
            section_type=section.section_type,
            displayed_freshness_state=overview_validation.displayed_freshness_state,
            displayed_evidence_state=overview_validation.displayed_evidence_state,
            displayed_as_of_date=overview_validation.displayed_as_of_date,
            displayed_retrieved_at=overview_validation.displayed_retrieved_at,
            validated_freshness_state=overview_validation.validated_freshness_state,
            validated_evidence_state=overview_validation.displayed_evidence_state,
            validated_as_of_date=overview_validation.validated_as_of_date,
            validated_retrieved_at=overview_validation.validated_retrieved_at,
            validation_outcome=_map_overview_validation_outcome(overview_validation),
            citation_binding_ids=citation_binding_ids,
            source_binding_ids=source_binding_ids,
            limitation_message=overview_validation.limitation_message or section.limitations,
            mismatch_message=overview_validation.mismatch_message,
        )

    validated_freshness = _derived_section_freshness(section)
    validated_evidence = _derived_section_evidence(section)
    validated_as_of = _derived_section_as_of(section)
    validated_retrieved = _derived_section_retrieved_at(section)
    limitation_message = _section_limitation_message(
        section,
        has_bindings=bool(citation_binding_ids or source_binding_ids),
        validated_freshness=validated_freshness,
        validated_evidence=validated_evidence,
    )
    validation_outcome = (
        ExportValidationOutcome.validated_with_limitations
        if limitation_message
        else ExportValidationOutcome.validated
    )
    return ExportSectionValidation(
        section_id=section.section_id,
        section_type=section.section_type,
        displayed_freshness_state=section.freshness_state,
        displayed_evidence_state=section.evidence_state,
        displayed_as_of_date=section.as_of_date,
        displayed_retrieved_at=section.retrieved_at,
        validated_freshness_state=validated_freshness,
        validated_evidence_state=validated_evidence,
        validated_as_of_date=validated_as_of,
        validated_retrieved_at=validated_retrieved,
        validation_outcome=validation_outcome,
        citation_binding_ids=citation_binding_ids,
        source_binding_ids=source_binding_ids,
        limitation_message=limitation_message,
    )


def _binding_ids_for_section_citations(
    section: ExportedSection,
    binding_ids_by_citation: dict[str, list[str]],
) -> list[str]:
    citation_ids = set(section.citation_ids)
    for item in section.items:
        citation_ids.update(item.citation_ids)
    return sorted({binding_id for citation_id in citation_ids for binding_id in binding_ids_by_citation.get(citation_id, [])})


def _binding_ids_for_section_sources(
    section: ExportedSection,
    binding_ids_by_source: dict[str, list[str]],
) -> list[str]:
    source_ids = set(section.source_document_ids)
    for item in section.items:
        source_ids.update(item.source_document_ids)
    return sorted({binding_id for source_id in source_ids for binding_id in binding_ids_by_source.get(source_id, [])})


def _map_overview_validation_outcome(
    validation: OverviewSectionFreshnessValidation,
) -> ExportValidationOutcome:
    if validation.validation_outcome.value == ExportValidationOutcome.mismatch.value:
        return ExportValidationOutcome.mismatch
    if validation.validation_outcome.value == ExportValidationOutcome.validated_with_limitations.value:
        return ExportValidationOutcome.validated_with_limitations
    return ExportValidationOutcome.validated


def _section_requires_export_validation(section: ExportedSection) -> bool:
    if section.section_id == "page_freshness":
        return True
    if section.citation_ids or section.source_document_ids:
        return True
    if section.freshness_state is not None or section.as_of_date is not None or section.retrieved_at is not None:
        return True
    return any(
        item.citation_ids
        or item.source_document_ids
        or item.freshness_state is not None
        or item.as_of_date is not None
        or item.retrieved_at is not None
        for item in section.items
    )


def _derived_section_freshness(section: ExportedSection) -> FreshnessState | None:
    states = [section.freshness_state] if section.freshness_state is not None else []
    states.extend(item.freshness_state for item in section.items if item.freshness_state is not None)
    if not states:
        return None
    if FreshnessState.stale in states:
        return FreshnessState.stale
    if FreshnessState.unavailable in states:
        return FreshnessState.unavailable
    if FreshnessState.unknown in states:
        return FreshnessState.unknown
    return FreshnessState.fresh


def _derived_section_evidence(section: ExportedSection) -> EvidenceState | None:
    if section.evidence_state is not None:
        return section.evidence_state
    item_states = [item.evidence_state for item in section.items if item.evidence_state is not None]
    if not item_states:
        return None
    unique_states = set(item_states)
    if len(unique_states) == 1:
        return item_states[0]
    return EvidenceState.mixed


def _derived_section_as_of(section: ExportedSection) -> str | None:
    if section.as_of_date is not None:
        return section.as_of_date
    item_dates = {item.as_of_date for item in section.items if item.as_of_date}
    return sorted(item_dates)[0] if len(item_dates) == 1 else None


def _derived_section_retrieved_at(section: ExportedSection) -> str | None:
    if section.retrieved_at is not None:
        return section.retrieved_at
    item_dates = {item.retrieved_at for item in section.items if item.retrieved_at}
    return sorted(item_dates)[0] if len(item_dates) == 1 else None


def _section_limitation_message(
    section: ExportedSection,
    *,
    has_bindings: bool,
    validated_freshness: FreshnessState | None,
    validated_evidence: EvidenceState | None,
) -> str | None:
    reasons: list[str] = []
    if section.limitations:
        reasons.append(section.limitations)
    if validated_freshness in {FreshnessState.stale, FreshnessState.unknown, FreshnessState.unavailable}:
        reasons.append(f"Section freshness remains {validated_freshness.value}.")
    if validated_evidence is not None and validated_evidence is not EvidenceState.supported:
        reasons.append(f"Section evidence remains {validated_evidence.value}.")
    if not has_bindings and section.section_id not in {"page_freshness"}:
        reasons.append("No exportable citation or source bindings are attached to this section.")
    return "; ".join(dict.fromkeys(reasons)) or None


def _overall_export_validation_outcome(
    section_validations: list[ExportSectionValidation],
    diagnostics: ExportValidationDiagnostics,
) -> ExportValidationOutcome:
    if diagnostics.mismatch_reasons or any(
        item.validation_outcome is ExportValidationOutcome.mismatch for item in section_validations
    ):
        return ExportValidationOutcome.mismatch
    if diagnostics.limitation_reasons or any(
        item.validation_outcome is ExportValidationOutcome.validated_with_limitations for item in section_validations
    ):
        return ExportValidationOutcome.validated_with_limitations
    return ExportValidationOutcome.validated


def _overall_validated_evidence_state(
    section_validations: list[ExportSectionValidation],
    default: EvidenceState | None,
) -> EvidenceState:
    states = [item.validated_evidence_state for item in section_validations if item.validated_evidence_state is not None]
    if not states:
        return default or EvidenceState.unavailable
    unique_states = set(states)
    if len(unique_states) == 1:
        return states[0]
    return EvidenceState.mixed


def _metric_value(value: Any, unit: str | None) -> str:
    if value is None:
        return "unknown"
    if unit:
        return f"{value}{unit}"
    return str(value)


def _coerce_format(export_format: ExportFormat | str) -> ExportFormat:
    if isinstance(export_format, ExportFormat):
        return export_format
    return ExportFormat(str(export_format))


def _export_state_from_asset_status(status: AssetStatus) -> ExportState:
    return ExportState.unsupported if status is AssetStatus.unsupported else ExportState.unavailable


def _slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())
