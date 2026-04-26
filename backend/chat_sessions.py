from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol
from uuid import NAMESPACE_URL, uuid5

from backend.chat import generate_asset_chat
from backend.chat_session_repository import (
    AccountlessChatSessionContractError,
    ChatSessionCitationRefRow,
    ChatSessionDiagnosticRow,
    ChatSessionEnvelopeRow,
    ChatSessionExportMetadataRow,
    ChatSessionRepositoryRecords,
    ChatSessionSourceRefRow,
    ChatSessionTurnKind,
    ChatSessionTurnSummaryRow,
    validate_chat_session_records,
)
from backend.data import STUB_TIMESTAMP, fallback_asset, supported_asset
from backend.models import (
    AssetIdentity,
    ChatCitation,
    ChatCompareRouteSuggestion,
    ChatRequest,
    ChatResponse,
    ChatSourceDocument,
    ChatSessionDeleteResponse,
    ChatSessionDeletionStatus,
    ChatSessionLifecycleState,
    ChatSessionPublicMetadata,
    ChatSessionStatusResponse,
    ChatSessionTurnSummary,
    ChatTurnRecord,
    ComparisonEvidenceAvailabilityState,
    EvidenceState,
    FreshnessState,
    SafetyClassification,
    SourceAllowlistStatus,
    SourceQuality,
    SourceUsePolicy,
)


CHAT_SESSION_SCHEMA_VERSION = "chat-session-contract-v1"
CHAT_SESSION_TTL_DAYS = 7
CHAT_SESSION_TTL_SECONDS = CHAT_SESSION_TTL_DAYS * 24 * 60 * 60
DEFAULT_CHAT_SESSION_START = STUB_TIMESTAMP
CHAT_SESSION_PERSISTED_BOUNDARY = "chat-session-persisted-boundary-v1"


class PersistedChatSessionReader(Protocol):
    def read_chat_session_records(self, conversation_id: str) -> ChatSessionRepositoryRecords | None:
        ...


class PersistedChatSessionWriter(Protocol):
    def persist_chat_session_records(self, records: ChatSessionRepositoryRecords) -> ChatSessionRepositoryRecords | None:
        ...

    def mark_chat_session_deleted(self, records: ChatSessionRepositoryRecords) -> ChatSessionRepositoryRecords | None:
        ...


class DeterministicOpaqueIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def __call__(self) -> str:
        self._counter += 1
        return uuid5(NAMESPACE_URL, f"learn-the-ticker-chat-session-{self._counter}").hex


def default_chat_session_clock() -> datetime:
    return _parse_timestamp(DEFAULT_CHAT_SESSION_START)


@dataclass
class _ChatSessionRecord:
    conversation_id: str
    selected_asset: AssetIdentity
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    deleted_at: datetime | None = None
    deletion_status: ChatSessionDeletionStatus = ChatSessionDeletionStatus.active
    turns: list[ChatTurnRecord] = field(default_factory=list)


@dataclass(frozen=True)
class _SessionAccess:
    lifecycle_state: ChatSessionLifecycleState
    metadata: ChatSessionPublicMetadata
    record: _ChatSessionRecord | None = None


class ChatSessionStore:
    def __init__(
        self,
        *,
        id_generator: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._id_generator = id_generator or DeterministicOpaqueIdGenerator()
        self._clock = clock or default_chat_session_clock
        self._sessions: dict[str, _ChatSessionRecord] = {}

    def create(self, selected_asset: AssetIdentity) -> _ChatSessionRecord:
        now = self._now()
        conversation_id = self._next_conversation_id()
        record = _ChatSessionRecord(
            conversation_id=conversation_id,
            selected_asset=selected_asset,
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(seconds=CHAT_SESSION_TTL_SECONDS),
        )
        self._sessions[conversation_id] = record
        return record

    def append_turn(self, record: _ChatSessionRecord, response: ChatResponse) -> ChatSessionPublicMetadata:
        now = self._now()
        turn = _turn_record_from_response(response, len(record.turns) + 1, now)
        record.turns.append(turn)
        record.last_activity_at = now
        record.expires_at = now + timedelta(seconds=CHAT_SESSION_TTL_SECONDS)
        return self.public_metadata(record)

    def access(self, conversation_id: str, selected_ticker: str) -> _SessionAccess:
        record = self._sessions.get(conversation_id)
        if record is None:
            metadata = _unavailable_metadata(conversation_id, "Chat session was not found.")
            return _SessionAccess(ChatSessionLifecycleState.unavailable, metadata)

        state = self.lifecycle_state(record)
        if state is not ChatSessionLifecycleState.active:
            return _SessionAccess(state, self.public_metadata(record, lifecycle_state=state), record)

        if record.selected_asset.ticker != selected_ticker.upper():
            metadata = self.public_metadata(record, lifecycle_state=ChatSessionLifecycleState.ticker_mismatch)
            return _SessionAccess(ChatSessionLifecycleState.ticker_mismatch, metadata, record)

        return _SessionAccess(ChatSessionLifecycleState.active, self.public_metadata(record), record)

    def status(self, conversation_id: str) -> ChatSessionStatusResponse:
        record = self._sessions.get(conversation_id)
        if record is None:
            metadata = _unavailable_metadata(conversation_id, "Chat session was not found.")
            return ChatSessionStatusResponse(session=metadata, turn_summaries=[], message="Chat session is unavailable.")

        state = self.lifecycle_state(record)
        metadata = self.public_metadata(record, lifecycle_state=state)
        turn_summaries = [] if state is ChatSessionLifecycleState.deleted else [_turn_summary(turn) for turn in record.turns]
        return ChatSessionStatusResponse(
            session=metadata,
            turn_summaries=turn_summaries,
            message=f"Chat session state is {state.value}.",
        )

    def delete(self, conversation_id: str) -> ChatSessionDeleteResponse:
        record = self._sessions.get(conversation_id)
        if record is None:
            metadata = ChatSessionPublicMetadata(
                session_id=conversation_id,
                conversation_id=conversation_id,
                lifecycle_state=ChatSessionLifecycleState.deleted,
                deletion_status=ChatSessionDeletionStatus.user_deleted,
                export_available=False,
            )
            return ChatSessionDeleteResponse(session=metadata, deleted=True, message="Chat session is deleted.")

        if record.deleted_at is None:
            record.deleted_at = self._now()
            record.deletion_status = ChatSessionDeletionStatus.user_deleted
            record.turns.clear()

        metadata = self.public_metadata(record, lifecycle_state=ChatSessionLifecycleState.deleted)
        return ChatSessionDeleteResponse(session=metadata, deleted=True, message="Chat session is deleted.")

    def public_metadata(
        self,
        record: _ChatSessionRecord,
        *,
        lifecycle_state: ChatSessionLifecycleState | None = None,
    ) -> ChatSessionPublicMetadata:
        state = lifecycle_state or self.lifecycle_state(record)
        latest_turn = record.turns[-1] if record.turns else None
        deletion_status = record.deletion_status
        if state is ChatSessionLifecycleState.expired:
            deletion_status = ChatSessionDeletionStatus.expired
        if state is ChatSessionLifecycleState.deleted:
            deletion_status = ChatSessionDeletionStatus.user_deleted
        return ChatSessionPublicMetadata(
            session_id=record.conversation_id,
            conversation_id=record.conversation_id,
            lifecycle_state=state,
            selected_asset=record.selected_asset,
            created_at=_format_timestamp(record.created_at),
            last_activity_at=_format_timestamp(record.last_activity_at),
            expires_at=_format_timestamp(record.expires_at),
            deleted_at=_format_timestamp(record.deleted_at) if record.deleted_at else None,
            turn_count=len(record.turns),
            latest_safety_classification=latest_turn.safety_classification if latest_turn else None,
            latest_evidence_state=latest_turn.evidence_state if latest_turn else None,
            latest_freshness_state=latest_turn.freshness_state if latest_turn else None,
            export_available=state is ChatSessionLifecycleState.active and bool(record.turns),
            deletion_status=deletion_status,
        )

    def export_turns(self, conversation_id: str) -> tuple[ChatSessionPublicMetadata, list[ChatTurnRecord]]:
        record = self._sessions.get(conversation_id)
        if record is None:
            return _unavailable_metadata(conversation_id, "Chat session was not found."), []
        state = self.lifecycle_state(record)
        metadata = self.public_metadata(record, lifecycle_state=state)
        if state is not ChatSessionLifecycleState.active:
            return metadata, []
        return metadata, list(record.turns)

    def lifecycle_state(self, record: _ChatSessionRecord) -> ChatSessionLifecycleState:
        if record.deleted_at is not None:
            return ChatSessionLifecycleState.deleted
        if self._now() >= record.expires_at:
            return ChatSessionLifecycleState.expired
        return ChatSessionLifecycleState.active

    def _next_conversation_id(self) -> str:
        for _ in range(10):
            candidate = str(self._id_generator())
            if candidate not in self._sessions:
                return candidate
        raise RuntimeError("Could not allocate a unique chat session ID.")

    def _now(self) -> datetime:
        return _ensure_utc(self._clock())


DEFAULT_CHAT_SESSION_STORE = ChatSessionStore()


def answer_chat_with_session(
    ticker: str,
    request: ChatRequest,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
    persisted_reader: PersistedChatSessionReader | Any | None = None,
    persisted_writer: PersistedChatSessionWriter | Any | None = None,
    persisted_pack_reader: Any | None = None,
    generated_output_cache_reader: Any | None = None,
) -> ChatResponse:
    selected_ticker = ticker.upper()
    if request.conversation_id:
        persisted_access = _persisted_access(request.conversation_id, selected_ticker, persisted_reader, store=store)
        if persisted_access is not None:
            if persisted_access.lifecycle_state is not ChatSessionLifecycleState.active or persisted_access.record is None:
                return _session_unavailable_chat(selected_ticker, persisted_access)
            response = generate_asset_chat(
                selected_ticker,
                request.question,
                persisted_pack_reader=persisted_pack_reader,
                generated_output_cache_reader=generated_output_cache_reader,
            )
            response.session = store.append_turn(persisted_access.record, response)
            _try_persist_session_records(persisted_writer, _records_from_session_record(persisted_access.record))
            return response

        access = store.access(request.conversation_id, selected_ticker)
        if access.lifecycle_state is not ChatSessionLifecycleState.active or access.record is None:
            return _session_unavailable_chat(selected_ticker, access)
        response = generate_asset_chat(
            selected_ticker,
            request.question,
            persisted_pack_reader=persisted_pack_reader,
            generated_output_cache_reader=generated_output_cache_reader,
        )
        response.session = store.append_turn(access.record, response)
        _try_persist_session_records(persisted_writer, _records_from_session_record(access.record))
        return response

    response = generate_asset_chat(
        selected_ticker,
        request.question,
        persisted_pack_reader=persisted_pack_reader,
        generated_output_cache_reader=generated_output_cache_reader,
    )
    if not response.asset.supported:
        response.session = _unavailable_metadata(
            None,
            "Chat session was not created because the selected asset is unavailable for grounded chat.",
            selected_asset=response.asset,
        )
        return response

    record = store.create(response.asset)
    response.session = store.append_turn(record, response)
    _try_persist_session_records(persisted_writer, _records_from_session_record(record))
    return response


def get_chat_session_status(
    conversation_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
    persisted_reader: PersistedChatSessionReader | Any | None = None,
) -> ChatSessionStatusResponse:
    persisted = _persisted_status(conversation_id, persisted_reader, store=store)
    if persisted is not None:
        return persisted
    return store.status(conversation_id)


def delete_chat_session(
    conversation_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
    persisted_reader: PersistedChatSessionReader | Any | None = None,
    persisted_writer: PersistedChatSessionWriter | Any | None = None,
) -> ChatSessionDeleteResponse:
    persisted = _persisted_delete(conversation_id, persisted_reader, persisted_writer, store=store)
    if persisted is not None:
        return persisted
    return store.delete(conversation_id)


def chat_session_export_payload(
    conversation_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
    persisted_reader: PersistedChatSessionReader | Any | None = None,
) -> tuple[ChatSessionPublicMetadata, list[ChatTurnRecord]]:
    persisted = _persisted_export_payload(conversation_id, persisted_reader, store=store)
    if persisted is not None:
        return persisted
    return store.export_turns(conversation_id)


def _read_valid_persisted_records(
    conversation_id: str,
    persisted_reader: PersistedChatSessionReader | Any | None,
) -> ChatSessionRepositoryRecords | None:
    if persisted_reader is None or not hasattr(persisted_reader, "read_chat_session_records"):
        return None
    try:
        raw_records = persisted_reader.read_chat_session_records(conversation_id)
    except Exception:
        return None
    if raw_records is None:
        return None
    try:
        records = ChatSessionRepositoryRecords.model_validate(raw_records)
        records = validate_chat_session_records(records)
    except (AccountlessChatSessionContractError, ValueError, TypeError):
        return None
    envelopes = [row for row in records.envelopes if row.conversation_id == conversation_id]
    if len(envelopes) != 1:
        return None
    return records


def _persisted_access(
    conversation_id: str,
    selected_ticker: str,
    persisted_reader: PersistedChatSessionReader | Any | None,
    *,
    store: ChatSessionStore,
) -> _SessionAccess | None:
    records = _read_valid_persisted_records(conversation_id, persisted_reader)
    if records is None:
        return None
    metadata = _metadata_from_persisted_records(records, store=store)
    state = metadata.lifecycle_state
    if state is not ChatSessionLifecycleState.active:
        return _SessionAccess(state, metadata)
    if metadata.selected_asset is None or metadata.selected_asset.ticker != selected_ticker.upper():
        mismatch = metadata.model_copy(update={"lifecycle_state": ChatSessionLifecycleState.ticker_mismatch})
        return _SessionAccess(ChatSessionLifecycleState.ticker_mismatch, mismatch)
    return _SessionAccess(state, metadata, _record_from_persisted_records(records, metadata))


def _persisted_status(
    conversation_id: str,
    persisted_reader: PersistedChatSessionReader | Any | None,
    *,
    store: ChatSessionStore,
) -> ChatSessionStatusResponse | None:
    records = _read_valid_persisted_records(conversation_id, persisted_reader)
    if records is None:
        return None
    metadata = _metadata_from_persisted_records(records, store=store)
    turn_summaries = []
    if metadata.lifecycle_state is ChatSessionLifecycleState.active:
        turn_summaries = [_turn_summary_from_persisted_turn(turn) for turn in _turn_rows_for(records)]
    return ChatSessionStatusResponse(
        session=metadata,
        turn_summaries=turn_summaries,
        message=f"Chat session state is {metadata.lifecycle_state.value}.",
    )


def _persisted_delete(
    conversation_id: str,
    persisted_reader: PersistedChatSessionReader | Any | None,
    persisted_writer: PersistedChatSessionWriter | Any | None,
    *,
    store: ChatSessionStore,
) -> ChatSessionDeleteResponse | None:
    records = _read_valid_persisted_records(conversation_id, persisted_reader)
    if records is None:
        return None
    envelope = records.envelopes[0]
    deleted_at = _format_timestamp(store._now())
    deleted_envelope = envelope.model_copy(
        update={
            "lifecycle_state": ChatSessionLifecycleState.deleted.value,
            "deletion_status": ChatSessionDeletionStatus.user_deleted.value,
            "deleted_at": envelope.deleted_at or deleted_at,
            "turn_count": 0,
            "export_available": False,
            "latest_safety_classification": None,
            "latest_evidence_state": None,
            "latest_freshness_state": None,
        }
    )
    deleted_exports = [
        export.model_copy(
            update={
                "export_state": "unavailable",
                "export_available": False,
                "turn_count": 0,
                "includes_factual_turns": False,
                "includes_comparison_redirects": False,
                "citation_ids": [],
                "source_document_ids": [],
            }
        )
        for export in records.export_metadata
    ]
    deleted_records = ChatSessionRepositoryRecords(
        envelopes=[deleted_envelope],
        turn_summaries=[],
        source_refs=[],
        citation_refs=[],
        export_metadata=deleted_exports,
        diagnostics=[],
    )
    try:
        deleted_records = validate_chat_session_records(deleted_records)
    except AccountlessChatSessionContractError:
        return None
    _try_mark_persisted_session_deleted(persisted_writer, deleted_records)
    metadata = _metadata_from_persisted_records(deleted_records, store=store)
    return ChatSessionDeleteResponse(session=metadata, deleted=True, message="Chat session is deleted.")


def _persisted_export_payload(
    conversation_id: str,
    persisted_reader: PersistedChatSessionReader | Any | None,
    *,
    store: ChatSessionStore,
) -> tuple[ChatSessionPublicMetadata, list[ChatTurnRecord]] | None:
    records = _read_valid_persisted_records(conversation_id, persisted_reader)
    if records is None:
        return None
    metadata = _metadata_from_persisted_records(records, store=store)
    if metadata.lifecycle_state is not ChatSessionLifecycleState.active or not metadata.export_available:
        return metadata, []
    return metadata, [_turn_record_from_persisted_turn(turn, records) for turn in _turn_rows_for(records)]


def _metadata_from_persisted_records(
    records: ChatSessionRepositoryRecords,
    *,
    store: ChatSessionStore,
) -> ChatSessionPublicMetadata:
    envelope = records.envelopes[0]
    state = ChatSessionLifecycleState(envelope.lifecycle_state)
    deletion_status = ChatSessionDeletionStatus(envelope.deletion_status)
    if state is ChatSessionLifecycleState.active and store._now() >= _parse_timestamp(envelope.expires_at):
        state = ChatSessionLifecycleState.expired
        deletion_status = ChatSessionDeletionStatus.expired
    if state is ChatSessionLifecycleState.expired:
        deletion_status = ChatSessionDeletionStatus.expired
    if state is ChatSessionLifecycleState.deleted:
        deletion_status = ChatSessionDeletionStatus.user_deleted
    return ChatSessionPublicMetadata(
        session_id=envelope.conversation_id,
        conversation_id=envelope.conversation_id,
        lifecycle_state=state,
        selected_asset=_asset_identity_from_envelope(envelope),
        created_at=envelope.created_at,
        last_activity_at=envelope.last_activity_at,
        expires_at=envelope.expires_at,
        deleted_at=envelope.deleted_at,
        turn_count=0 if state is ChatSessionLifecycleState.deleted else envelope.turn_count,
        latest_safety_classification=(
            SafetyClassification(envelope.latest_safety_classification)
            if envelope.latest_safety_classification
            else None
        ),
        latest_evidence_state=EvidenceState(envelope.latest_evidence_state) if envelope.latest_evidence_state else None,
        latest_freshness_state=(
            FreshnessState(envelope.latest_freshness_state) if envelope.latest_freshness_state else None
        ),
        export_available=state is ChatSessionLifecycleState.active and envelope.export_available,
        deletion_status=deletion_status,
    )


def _record_from_persisted_records(
    records: ChatSessionRepositoryRecords,
    metadata: ChatSessionPublicMetadata,
) -> _ChatSessionRecord | None:
    if metadata.selected_asset is None:
        return None
    return _ChatSessionRecord(
        conversation_id=metadata.conversation_id or records.envelopes[0].conversation_id,
        selected_asset=metadata.selected_asset,
        created_at=_parse_timestamp(metadata.created_at or records.envelopes[0].created_at),
        last_activity_at=_parse_timestamp(metadata.last_activity_at or records.envelopes[0].last_activity_at),
        expires_at=_parse_timestamp(metadata.expires_at or records.envelopes[0].expires_at),
        deleted_at=_parse_timestamp(metadata.deleted_at) if metadata.deleted_at else None,
        deletion_status=metadata.deletion_status,
        turns=[_turn_record_from_persisted_turn(turn, records) for turn in _turn_rows_for(records)],
    )


def _turn_rows_for(records: ChatSessionRepositoryRecords) -> list[ChatSessionTurnSummaryRow]:
    conversation_id = records.envelopes[0].conversation_id
    return sorted(
        [turn for turn in records.turn_summaries if turn.conversation_id == conversation_id],
        key=lambda turn: turn.turn_index,
    )


def _asset_identity_from_envelope(envelope: ChatSessionEnvelopeRow) -> AssetIdentity:
    local = supported_asset(envelope.selected_asset_ticker)
    if local:
        return local["identity"]
    payload = {
        **envelope.selected_asset_identity,
        "ticker": envelope.selected_asset_ticker,
        "asset_type": envelope.selected_asset_type,
        "status": envelope.selected_asset_status,
        "supported": envelope.selected_asset_status == "supported",
    }
    return AssetIdentity.model_validate(payload)


def _turn_summary_from_persisted_turn(turn: ChatSessionTurnSummaryRow) -> ChatSessionTurnSummary:
    return ChatSessionTurnSummary(
        turn_id=turn.turn_id,
        submitted_at=turn.submitted_at,
        selected_ticker=turn.selected_ticker,
        safety_classification=SafetyClassification(turn.safety_classification),
        evidence_state=EvidenceState(turn.evidence_state),
        freshness_state=FreshnessState(turn.freshness_state),
        citation_ids=list(turn.citation_ids),
        source_document_ids=list(turn.source_document_ids),
        uncertainty_labels=list(turn.uncertainty_labels),
        compare_route_suggestion=_compare_route_from_metadata(turn),
    )


def _turn_record_from_persisted_turn(
    turn: ChatSessionTurnSummaryRow,
    records: ChatSessionRepositoryRecords,
) -> ChatTurnRecord:
    citations = [_chat_citation_from_ref(citation) for citation in records.citation_refs if citation.turn_id == turn.turn_id]
    sources = [_chat_source_from_ref(source, turn) for source in records.source_refs if source.turn_id == turn.turn_id]
    return ChatTurnRecord(
        turn_id=turn.turn_id,
        submitted_at=turn.submitted_at,
        selected_ticker=turn.selected_ticker,
        safety_classification=SafetyClassification(turn.safety_classification),
        evidence_state=EvidenceState(turn.evidence_state),
        freshness_state=FreshnessState(turn.freshness_state),
        citation_ids=list(turn.citation_ids),
        source_document_ids=list(turn.source_document_ids),
        uncertainty_labels=list(turn.uncertainty_labels),
        direct_answer=_persisted_turn_direct_answer(turn),
        why_it_matters=_persisted_turn_why_it_matters(turn),
        citations=citations,
        source_documents=sources,
        compare_route_suggestion=_compare_route_from_metadata(turn),
    )


def _chat_citation_from_ref(citation: Any) -> ChatCitation:
    return ChatCitation(
        citation_id=citation.citation_id,
        claim=citation.claim_ref or "Persisted safe chat turn metadata",
        source_document_id=citation.source_document_id,
        chunk_id=f"{citation.source_document_id}_metadata",
    )


def _chat_source_from_ref(source: ChatSessionSourceRefRow, turn: ChatSessionTurnSummaryRow) -> ChatSourceDocument:
    citation_id = source.citation_ids[0] if source.citation_ids else f"metadata_{source.source_document_id}"
    source_use_policy = SourceUsePolicy(source.source_use_policy)
    source_url = (
        f"local://fixtures/persisted-chat-source/{source.source_document_id}"
        if source_use_policy in {SourceUsePolicy.summary_allowed, SourceUsePolicy.full_text_allowed}
        else f"local://persisted-chat-source-metadata/{source.source_document_id}"
    )
    return ChatSourceDocument(
        citation_id=citation_id,
        source_document_id=source.source_document_id,
        chunk_id=f"{source.source_document_id}_metadata",
        title=f"Persisted source metadata: {source.source_document_id}",
        source_type=source.source_type,
        publisher="Persisted chat session metadata",
        url=source_url,
        retrieved_at=turn.submitted_at,
        freshness_state=FreshnessState(source.freshness_state),
        is_official=False,
        supporting_passage="Allowed excerpt unavailable from persisted chat session metadata.",
        source_quality=SourceQuality.fixture,
        allowlist_status=SourceAllowlistStatus(source.allowlist_status),
        source_use_policy=source_use_policy,
    )


def _compare_route_from_metadata(turn: ChatSessionTurnSummaryRow) -> ChatCompareRouteSuggestion | None:
    if ChatSessionTurnKind(turn.turn_kind) is not ChatSessionTurnKind.comparison_redirect:
        return None
    metadata = turn.comparison_route_metadata
    route = str(metadata.get("route", ""))
    left = str(metadata.get("left_ticker", turn.selected_ticker)).upper()
    right = str(metadata.get("right_ticker", turn.selected_ticker)).upper()
    comparison_ticker = str(metadata.get("comparison_ticker", left if left != turn.selected_ticker else right)).upper()
    availability = ComparisonEvidenceAvailabilityState(
        metadata.get("comparison_availability_state", ComparisonEvidenceAvailabilityState.unavailable.value)
    )
    return ChatCompareRouteSuggestion(
        selected_ticker=turn.selected_ticker,
        comparison_ticker=comparison_ticker,
        left_ticker=left,
        right_ticker=right,
        route=route,
        comparison_availability_state=availability,
        comparison_state_message=str(metadata.get("comparison_state_message", "Comparison route metadata is available.")),
        workflow_guidance="Open the comparison workflow to review both assets side by side.",
        grounding_explanation="Persisted chat metadata preserves this as a comparison redirect, not a single-asset answer.",
    )


def _persisted_turn_direct_answer(turn: ChatSessionTurnSummaryRow) -> str:
    kind = ChatSessionTurnKind(turn.turn_kind)
    if kind is ChatSessionTurnKind.advice_redirect:
        return "This persisted turn was an educational advice-boundary redirect, not a factual asset answer."
    if kind is ChatSessionTurnKind.comparison_redirect:
        return "This persisted turn redirected to the comparison workflow and did not create a single-asset factual answer."
    if kind is ChatSessionTurnKind.insufficient_evidence:
        return "This persisted turn had insufficient evidence for a factual chat answer."
    return "This persisted turn is reconstructed from safe chat metadata; raw question and answer text are not stored."


def _persisted_turn_why_it_matters(turn: ChatSessionTurnSummaryRow) -> str:
    return (
        f"Safety: {turn.safety_classification}; evidence: {turn.evidence_state}; "
        f"freshness: {turn.freshness_state}. The export preserves citation, source, freshness, and uncertainty metadata only."
    )


def _records_from_session_record(record: _ChatSessionRecord) -> ChatSessionRepositoryRecords:
    state = ChatSessionLifecycleState.deleted if record.deleted_at else ChatSessionLifecycleState.active
    export_available = state is ChatSessionLifecycleState.active and bool(record.turns)
    latest_turn = record.turns[-1] if record.turns else None
    envelope = ChatSessionEnvelopeRow(
        conversation_id=record.conversation_id,
        selected_asset_ticker=record.selected_asset.ticker,
        selected_asset_type=record.selected_asset.asset_type.value,
        selected_asset_status=record.selected_asset.status.value,
        selected_asset_identity=record.selected_asset.model_dump(mode="json"),
        lifecycle_state=state.value,
        deletion_status=record.deletion_status.value,
        created_at=_format_timestamp(record.created_at),
        last_activity_at=_format_timestamp(record.last_activity_at),
        expires_at=_format_timestamp(record.expires_at),
        deleted_at=_format_timestamp(record.deleted_at) if record.deleted_at else None,
        turn_count=0 if state is ChatSessionLifecycleState.deleted else len(record.turns),
        latest_safety_classification=latest_turn.safety_classification.value if latest_turn else None,
        latest_evidence_state=latest_turn.evidence_state.value if latest_turn else None,
        latest_freshness_state=latest_turn.freshness_state.value if latest_turn else None,
        export_available=export_available,
    )
    if state is ChatSessionLifecycleState.deleted:
        return ChatSessionRepositoryRecords(
            envelopes=[envelope.model_copy(update={"export_available": False, "turn_count": 0})],
            export_metadata=[_export_row(record, export_available=False, turn_count=0, citation_ids=[], source_ids=[])],
        )

    turn_rows = [_turn_row(record.conversation_id, turn, index + 1) for index, turn in enumerate(record.turns)]
    source_rows = [
        _source_row(record.conversation_id, turn.turn_id, sources)
        for turn in record.turns
        for sources in _source_documents_grouped_by_id(turn.source_documents)
    ]
    citation_rows = [
        _citation_row(record.conversation_id, turn.turn_id, citation)
        for turn in record.turns
        for citation in turn.citations
    ]
    citation_ids = sorted({citation.citation_id for turn in record.turns for citation in turn.citations})
    source_ids = sorted({source.source_document_id for turn in record.turns for source in turn.source_documents})
    return ChatSessionRepositoryRecords(
        envelopes=[envelope],
        turn_summaries=turn_rows,
        source_refs=source_rows,
        citation_refs=citation_rows,
        export_metadata=[
            _export_row(
                record,
                export_available=export_available,
                turn_count=len(record.turns),
                citation_ids=citation_ids,
                source_ids=source_ids,
            )
        ],
        diagnostics=[
            ChatSessionDiagnosticRow(
                diagnostic_id=f"diag-{record.conversation_id}",
                conversation_id=record.conversation_id,
                category="lifecycle",
                code="safe_session_metadata",
                lifecycle_state=state.value,
                source_document_ids=source_ids,
                citation_ids=citation_ids,
                freshness_states={turn.turn_id: turn.freshness_state.value for turn in record.turns},
                compact_metadata={"turn_count": len(record.turns), "boundary": CHAT_SESSION_PERSISTED_BOUNDARY},
                created_at=_format_timestamp(record.last_activity_at),
            )
        ],
    )


def _turn_row(conversation_id: str, turn: ChatTurnRecord, turn_index: int) -> ChatSessionTurnSummaryRow:
    kind = _turn_kind_for_record(turn)
    return ChatSessionTurnSummaryRow(
        conversation_id=conversation_id,
        turn_id=turn.turn_id,
        turn_index=turn_index,
        submitted_at=turn.submitted_at,
        selected_ticker=turn.selected_ticker,
        turn_kind=kind.value,
        safety_classification=turn.safety_classification.value,
        evidence_state=turn.evidence_state.value,
        freshness_state=turn.freshness_state.value,
        citation_ids=list(turn.citation_ids) if kind is ChatSessionTurnKind.factual_answer else [],
        source_document_ids=list(turn.source_document_ids) if kind is ChatSessionTurnKind.factual_answer else [],
        uncertainty_labels=list(turn.uncertainty_labels),
        comparison_route_metadata=(
            turn.compare_route_suggestion.model_dump(mode="json") if turn.compare_route_suggestion is not None else {}
        ),
        diagnostics_metadata={"turn_kind": kind.value, "selected_ticker": turn.selected_ticker},
        exportable_factual_turn=kind is ChatSessionTurnKind.factual_answer and turn.evidence_state is EvidenceState.supported,
        generated_answer_artifact_persisted=False,
    )


def _turn_kind_for_record(turn: ChatTurnRecord) -> ChatSessionTurnKind:
    if turn.safety_classification is SafetyClassification.personalized_advice_redirect:
        return ChatSessionTurnKind.advice_redirect
    if turn.safety_classification is SafetyClassification.compare_route_redirect:
        return ChatSessionTurnKind.comparison_redirect
    if turn.safety_classification is SafetyClassification.unsupported_asset_redirect:
        return ChatSessionTurnKind.unsupported_asset_redirect
    if turn.evidence_state in {EvidenceState.insufficient_evidence, EvidenceState.unknown, EvidenceState.unavailable}:
        return ChatSessionTurnKind.insufficient_evidence
    return ChatSessionTurnKind.factual_answer


def _source_documents_grouped_by_id(sources: list[ChatSourceDocument]) -> list[list[ChatSourceDocument]]:
    grouped: dict[str, list[ChatSourceDocument]] = {}
    for source in sources:
        grouped.setdefault(source.source_document_id, []).append(source)
    return list(grouped.values())


def _source_row(conversation_id: str, turn_id: str, sources: list[ChatSourceDocument]) -> ChatSessionSourceRefRow:
    source = sources[0]
    return ChatSessionSourceRefRow(
        conversation_id=conversation_id,
        turn_id=turn_id,
        source_document_id=source.source_document_id,
        asset_ticker="",
        source_type=source.source_type,
        source_use_policy=source.source_use_policy.value,
        allowlist_status=source.allowlist_status.value,
        freshness_state=source.freshness_state.value,
        evidence_state=EvidenceState.supported.value,
        citation_ids=sorted({item.citation_id for item in sources}),
        export_allowed=source.source_use_policy is not SourceUsePolicy.rejected,
    )


def _citation_row(conversation_id: str, turn_id: str, citation: ChatCitation) -> ChatSessionCitationRefRow:
    return ChatSessionCitationRefRow(
        conversation_id=conversation_id,
        turn_id=turn_id,
        citation_id=citation.citation_id,
        source_document_id=citation.source_document_id,
        asset_ticker="",
        claim_ref=citation.claim,
    )


def _export_row(
    record: _ChatSessionRecord,
    *,
    export_available: bool,
    turn_count: int,
    citation_ids: list[str],
    source_ids: list[str],
) -> ChatSessionExportMetadataRow:
    return ChatSessionExportMetadataRow(
        export_id=f"chat-export-{record.conversation_id}",
        conversation_id=record.conversation_id,
        export_format="markdown",
        export_state="available" if export_available else "unavailable",
        export_available=export_available,
        selected_ticker=record.selected_asset.ticker,
        turn_count=turn_count,
        includes_factual_turns=bool(citation_ids),
        includes_comparison_redirects=any(turn.compare_route_suggestion is not None for turn in record.turns),
        citation_ids=citation_ids,
        source_document_ids=source_ids,
    )


def _try_persist_session_records(
    persisted_writer: PersistedChatSessionWriter | Any | None,
    records: ChatSessionRepositoryRecords,
) -> None:
    if persisted_writer is None or not hasattr(persisted_writer, "persist_chat_session_records"):
        return
    try:
        validated = validate_chat_session_records(_normalize_record_asset_refs(records))
        persisted_writer.persist_chat_session_records(validated)
    except Exception:
        return


def _try_mark_persisted_session_deleted(
    persisted_writer: PersistedChatSessionWriter | Any | None,
    records: ChatSessionRepositoryRecords,
) -> None:
    if persisted_writer is None or not hasattr(persisted_writer, "mark_chat_session_deleted"):
        return
    try:
        persisted_writer.mark_chat_session_deleted(records)
    except Exception:
        return


def _normalize_record_asset_refs(records: ChatSessionRepositoryRecords) -> ChatSessionRepositoryRecords:
    if not records.envelopes:
        return records
    ticker = records.envelopes[0].selected_asset_ticker
    return records.model_copy(
        update={
            "source_refs": [source.model_copy(update={"asset_ticker": ticker}) for source in records.source_refs],
            "citation_refs": [citation.model_copy(update={"asset_ticker": ticker}) for citation in records.citation_refs],
        }
    )


def _turn_record_from_response(response: ChatResponse, turn_number: int, submitted_at: datetime) -> ChatTurnRecord:
    citation_ids = [citation.citation_id for citation in response.citations]
    source_document_ids = sorted({source.source_document_id for source in response.source_documents})
    return ChatTurnRecord(
        turn_id=f"turn_{turn_number}",
        submitted_at=_format_timestamp(submitted_at),
        selected_ticker=response.asset.ticker,
        safety_classification=response.safety_classification,
        evidence_state=_evidence_state_for_response(response),
        freshness_state=_freshness_state_for_response(response),
        citation_ids=citation_ids,
        source_document_ids=source_document_ids,
        uncertainty_labels=list(response.uncertainty),
        direct_answer=response.direct_answer,
        why_it_matters=response.why_it_matters,
        citations=list(response.citations),
        source_documents=list(response.source_documents),
        compare_route_suggestion=response.compare_route_suggestion,
    )


def _turn_summary(turn: ChatTurnRecord) -> ChatSessionTurnSummary:
    return ChatSessionTurnSummary(
        turn_id=turn.turn_id,
        submitted_at=turn.submitted_at,
        selected_ticker=turn.selected_ticker,
        safety_classification=turn.safety_classification,
        evidence_state=turn.evidence_state,
        freshness_state=turn.freshness_state,
        citation_ids=turn.citation_ids,
        source_document_ids=turn.source_document_ids,
        uncertainty_labels=turn.uncertainty_labels,
        compare_route_suggestion=turn.compare_route_suggestion,
    )


def _evidence_state_for_response(response: ChatResponse) -> EvidenceState:
    if response.safety_classification is not SafetyClassification.educational:
        return EvidenceState.unsupported
    if response.citations:
        return EvidenceState.supported
    return EvidenceState.insufficient_evidence


def _freshness_state_for_response(response: ChatResponse) -> FreshnessState:
    states = {source.freshness_state for source in response.source_documents}
    if not states:
        return FreshnessState.unknown
    if len(states) == 1:
        return next(iter(states))
    if FreshnessState.stale in states:
        return FreshnessState.stale
    if FreshnessState.unavailable in states:
        return FreshnessState.unavailable
    return FreshnessState.unknown


def _session_unavailable_chat(selected_ticker: str, access: _SessionAccess) -> ChatResponse:
    asset = _asset_identity(selected_ticker)
    state = access.lifecycle_state
    if state is ChatSessionLifecycleState.ticker_mismatch and access.metadata.selected_asset is not None:
        direct_answer = (
            f"This chat session is bound to {access.metadata.selected_asset.ticker}, "
            f"so it cannot be reused for {selected_ticker}."
        )
    elif state is ChatSessionLifecycleState.deleted:
        direct_answer = "This chat session has been deleted and is unavailable for new answers."
    elif state is ChatSessionLifecycleState.expired:
        direct_answer = "This chat session has expired and is unavailable for new answers."
    else:
        direct_answer = "This chat session is unavailable."
    return ChatResponse(
        asset=asset,
        direct_answer=direct_answer,
        why_it_matters="Session lifecycle checks run before grounded chat generation, so no asset answer is created for this state.",
        citations=[],
        source_documents=[],
        uncertainty=[f"Session lifecycle state: {state.value}."],
        safety_classification=SafetyClassification.insufficient_evidence,
        session=access.metadata,
    )


def _asset_identity(ticker: str) -> AssetIdentity:
    payload = supported_asset(ticker)
    if payload:
        return payload["identity"]
    return fallback_asset(ticker)


def _unavailable_metadata(
    conversation_id: str | None,
    message: str,
    *,
    selected_asset: AssetIdentity | None = None,
) -> ChatSessionPublicMetadata:
    return ChatSessionPublicMetadata(
        session_id=conversation_id,
        conversation_id=conversation_id,
        lifecycle_state=ChatSessionLifecycleState.unavailable,
        selected_asset=selected_asset,
        turn_count=0,
        export_available=False,
        deletion_status=ChatSessionDeletionStatus.unavailable,
    )


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return _ensure_utc(value).isoformat().replace("+00:00", "Z")
