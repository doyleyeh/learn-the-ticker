from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import NAMESPACE_URL, uuid5

from backend.chat import generate_asset_chat
from backend.data import STUB_TIMESTAMP, fallback_asset, supported_asset
from backend.models import (
    AssetIdentity,
    ChatRequest,
    ChatResponse,
    ChatSessionDeleteResponse,
    ChatSessionDeletionStatus,
    ChatSessionLifecycleState,
    ChatSessionPublicMetadata,
    ChatSessionStatusResponse,
    ChatSessionTurnSummary,
    ChatTurnRecord,
    EvidenceState,
    FreshnessState,
    SafetyClassification,
)


CHAT_SESSION_SCHEMA_VERSION = "chat-session-contract-v1"
CHAT_SESSION_TTL_DAYS = 7
CHAT_SESSION_TTL_SECONDS = CHAT_SESSION_TTL_DAYS * 24 * 60 * 60
DEFAULT_CHAT_SESSION_START = STUB_TIMESTAMP


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
) -> ChatResponse:
    selected_ticker = ticker.upper()
    if request.conversation_id:
        access = store.access(request.conversation_id, selected_ticker)
        if access.lifecycle_state is not ChatSessionLifecycleState.active or access.record is None:
            return _session_unavailable_chat(selected_ticker, access)
        response = generate_asset_chat(selected_ticker, request.question)
        response.session = store.append_turn(access.record, response)
        return response

    response = generate_asset_chat(selected_ticker, request.question)
    if not response.asset.supported:
        response.session = _unavailable_metadata(
            None,
            "Chat session was not created because the selected asset is unavailable for grounded chat.",
            selected_asset=response.asset,
        )
        return response

    record = store.create(response.asset)
    response.session = store.append_turn(record, response)
    return response


def get_chat_session_status(
    conversation_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
) -> ChatSessionStatusResponse:
    return store.status(conversation_id)


def delete_chat_session(
    conversation_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
) -> ChatSessionDeleteResponse:
    return store.delete(conversation_id)


def chat_session_export_payload(
    conversation_id: str,
    *,
    store: ChatSessionStore = DEFAULT_CHAT_SESSION_STORE,
) -> tuple[ChatSessionPublicMetadata, list[ChatTurnRecord]]:
    return store.export_turns(conversation_id)


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
