from __future__ import annotations

from typing import Any

from backend.chat import generate_asset_chat
from backend.chat_sessions import chat_session_export_payload
from backend.comparison import generate_comparison
from backend.models import (
    AssetIdentity,
    AssetStatus,
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
    ExportSourceMetadata,
    ExportState,
    ExportedItem,
    ExportedSection,
    Freshness,
    FreshnessState,
    OverviewResponse,
    OverviewSectionType,
    SafetyClassification,
    SearchSupportClassification,
    SourceDocument,
    StateMessage,
)
from backend.overview import generate_asset_overview
from backend.search import search_assets
from backend.source_policy import excerpt_text_for_policy, resolve_source_policy, source_can_export_excerpt


EXPORT_LICENSING_NOTE = ExportNote(
    note_id="export_licensing_scope",
    label="Licensing and export scope",
    text=(
        "This export includes citation IDs, source attribution, freshness metadata, and short allowed "
        "fixture supporting passages. It does not export full paid-news articles, full filings, full "
        "issuer documents, or restricted provider payloads unless redistribution rights are confirmed."
    ),
)


def export_asset_page(ticker: str, export_format: ExportFormat | str = ExportFormat.markdown) -> ExportResponse:
    """Shape an existing deterministic asset overview into an accountless export payload."""

    blocked = _blocked_asset_response(ticker, ExportContentType.asset_page, export_format)
    if blocked is not None:
        return blocked

    overview = generate_asset_overview(ticker)
    if not overview.asset.supported:
        return _unavailable_asset_response(overview.asset, overview.state, ExportContentType.asset_page, export_format)

    sections = _asset_page_sections(overview)
    citations = _export_citations_from_overview(overview)
    sources = _export_sources(overview.source_documents)
    title = f"{overview.asset.ticker} asset page export"
    markdown = _render_markdown(title, sections, overview.source_documents, overview.freshness)

    return ExportResponse(
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


def export_asset_source_list(ticker: str, export_format: ExportFormat | str = ExportFormat.markdown) -> ExportResponse:
    """Export source metadata for an asset without adding new source material."""

    blocked = _blocked_asset_response(ticker, ExportContentType.asset_source_list, export_format)
    if blocked is not None:
        return blocked

    overview = generate_asset_overview(ticker)
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

    return ExportResponse(
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


def export_comparison(request: ComparisonExportRequest) -> ExportResponse:
    """Shape an existing deterministic comparison into an export payload."""

    comparison = generate_comparison(request.left_ticker, request.right_ticker)
    export_format = _coerce_format(request.export_format)
    title = f"{comparison.left_asset.ticker} vs {comparison.right_asset.ticker} comparison export"

    if comparison.comparison_type == "unavailable" or comparison.state.status is not AssetStatus.supported:
        return ExportResponse(
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

    return ExportResponse(
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


def export_chat_transcript(ticker: str, request: ChatTranscriptExportRequest) -> ExportResponse:
    """Export a single deterministic chat turn for a selected cached asset."""

    if request.conversation_id:
        session_export = _maybe_export_existing_chat_session(request.conversation_id, request.export_format)
        if session_export is not None:
            return session_export

    blocked = _blocked_asset_response(ticker, ExportContentType.chat_transcript, request.export_format)
    if blocked is not None:
        blocked.metadata["submitted_question"] = request.question
        blocked.metadata["generated_chat_answer"] = False
        return blocked

    chat = generate_asset_chat(ticker, request.question)
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

    return ExportResponse(
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
            "generated_chat_answer": True,
            "source": "local_fixture_chat",
        },
    )


def export_chat_session_transcript(
    conversation_id: str,
    export_format: ExportFormat | str = ExportFormat.markdown,
) -> ExportResponse:
    metadata, turns = chat_session_export_payload(conversation_id)
    return _export_chat_session_payload(metadata, turns, export_format)


def _maybe_export_existing_chat_session(
    conversation_id: str,
    export_format: ExportFormat | str,
) -> ExportResponse | None:
    metadata, turns = chat_session_export_payload(conversation_id)
    if metadata.lifecycle_state is ChatSessionLifecycleState.unavailable and metadata.selected_asset is None:
        return None
    return _export_chat_session_payload(metadata, turns, export_format)


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
        return ExportResponse(
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
                    metadata={"safety_classification": turn.safety_classification.value},
                )
                for index, turn in enumerate(turns)
            ],
            citation_ids=sorted({citation_id for turn in turns for citation_id in turn.citation_ids}),
            source_document_ids=sorted({source_id for turn in turns for source_id in turn.source_document_ids}),
            evidence_state=EvidenceState.supported,
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
    return ExportResponse(
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
        metadata=_chat_session_export_metadata(metadata, generated_chat_answer=True),
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
                "AI Comprehensive Analysis is suppressed unless at least two high-signal Weekly News Focus items exist."
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
    return ExportResponse(
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
        decision = resolve_source_policy(
            url=source.url,
            source_identifier=source.url if str(source.url).startswith("local://") else None,
        )
        excerpt_text = excerpt_text_for_policy(supporting_passage, decision)
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
                allowed_excerpt=ExportExcerpt(
                    excerpt_id=f"excerpt_{citation_id or source.source_document_id}",
                    kind="supporting_passage" if source_can_export_excerpt(decision) else "excerpt_metadata",
                    text=excerpt_text,
                    citation_id=citation_id,
                    chunk_id=chunk_id,
                    redistribution_allowed=decision.permitted_operations.can_export_excerpt,
                    source_use_policy=decision.source_use_policy,
                    allowlist_status=decision.allowlist_status,
                    note=decision.allowed_excerpt.note,
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
