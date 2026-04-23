from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.chat_sessions import (
    CHAT_SESSION_SCHEMA_VERSION,
    CHAT_SESSION_TTL_DAYS,
    CHAT_SESSION_TTL_SECONDS,
    ChatSessionStore,
    answer_chat_with_session,
    chat_session_export_payload,
    delete_chat_session,
    get_chat_session_status,
)
from backend.export import export_chat_session_transcript
from backend.models import (
    ChatRequest,
    ChatResponse,
    ChatSessionLifecycleState,
    ExportState,
    SafetyClassification,
)


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 4, 23, 13, 1, 25, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: int) -> None:
        self.now += timedelta(**kwargs)


def test_session_creation_uses_opaque_ticker_bound_metadata_and_safe_turn_summary():
    clock = MutableClock()
    store = ChatSessionStore(id_generator=lambda: "9f2c4a6d8e0b4c1f93a7d5e2b8c0a146", clock=clock)

    response = answer_chat_with_session("QQQ", ChatRequest(question="What is this fund?"), store=store)

    assert ChatResponse.model_validate(response.model_dump(mode="json")).session is not None
    assert response.session.schema_version == CHAT_SESSION_SCHEMA_VERSION
    assert response.session.conversation_id == "9f2c4a6d8e0b4c1f93a7d5e2b8c0a146"
    assert response.session.session_id == response.session.conversation_id
    assert response.session.lifecycle_state is ChatSessionLifecycleState.active
    assert response.session.selected_asset.ticker == "QQQ"
    assert "QQQ" not in response.session.conversation_id
    assert response.session.turn_count == 1
    assert response.session.latest_safety_classification is SafetyClassification.educational
    assert response.session.export_available is True
    assert response.session.created_at == "2026-04-23T13:01:25Z"
    assert response.session.expires_at == "2026-04-30T13:01:25Z"
    assert CHAT_SESSION_TTL_DAYS == 7
    assert CHAT_SESSION_TTL_SECONDS == 604800

    status = get_chat_session_status(response.session.conversation_id, store=store)
    assert status.session.turn_count == 1
    assert len(status.turn_summaries) == 1
    dumped = status.model_dump(mode="json")
    assert "What is this fund?" not in str(dumped)
    assert "hidden_prompt" not in str(dumped)
    assert "reasoning_details" not in str(dumped)


def test_session_continuation_refreshes_ttl_and_preserves_grounded_citations():
    clock = MutableClock()
    ids = iter(["11111111111141118111111111111111"])
    store = ChatSessionStore(id_generator=lambda: next(ids), clock=clock)
    first = answer_chat_with_session("VOO", ChatRequest(question="What is VOO?"), store=store)
    conversation_id = first.session.conversation_id

    clock.advance(hours=2)
    second = answer_chat_with_session(
        "VOO",
        ChatRequest(question="What top risk should a beginner understand?", conversation_id=conversation_id),
        store=store,
    )

    assert second.session.conversation_id == conversation_id
    assert second.session.turn_count == 2
    assert second.session.last_activity_at == "2026-04-23T15:01:25Z"
    assert second.session.expires_at == "2026-04-30T15:01:25Z"
    assert second.citations
    assert second.source_documents
    assert {citation.source_document_id for citation in second.citations} <= {
        source.source_document_id for source in second.source_documents
    }
    assert {source.source_use_policy.value for source in second.source_documents} == {"full_text_allowed"}


def test_expired_session_blocks_new_answer_and_export():
    clock = MutableClock()
    store = ChatSessionStore(id_generator=lambda: "22222222222242228222222222222222", clock=clock)
    first = answer_chat_with_session("AAPL", ChatRequest(question="What does Apple do?"), store=store)
    conversation_id = first.session.conversation_id

    clock.advance(days=8)
    expired = answer_chat_with_session(
        "AAPL",
        ChatRequest(question="What does Apple do?", conversation_id=conversation_id),
        store=store,
    )
    status = get_chat_session_status(conversation_id, store=store)
    metadata, turns = chat_session_export_payload(conversation_id, store=store)

    assert expired.session.lifecycle_state is ChatSessionLifecycleState.expired
    assert expired.citations == []
    assert expired.source_documents == []
    assert "expired" in expired.direct_answer
    assert status.session.lifecycle_state is ChatSessionLifecycleState.expired
    assert status.session.export_available is False
    assert metadata.lifecycle_state is ChatSessionLifecycleState.expired
    assert turns == []


def test_deleted_session_is_idempotent_and_clears_turn_summaries():
    clock = MutableClock()
    store = ChatSessionStore(id_generator=lambda: "33333333333343338333333333333333", clock=clock)
    first = answer_chat_with_session("VOO", ChatRequest(question="What is VOO?"), store=store)
    conversation_id = first.session.conversation_id

    deleted = delete_chat_session(conversation_id, store=store)
    deleted_again = delete_chat_session(conversation_id, store=store)
    status = get_chat_session_status(conversation_id, store=store)
    continued = answer_chat_with_session(
        "VOO",
        ChatRequest(question="What is VOO?", conversation_id=conversation_id),
        store=store,
    )
    export = export_chat_session_transcript(conversation_id)

    assert deleted.deleted is True
    assert deleted_again.deleted is True
    assert status.session.lifecycle_state is ChatSessionLifecycleState.deleted
    assert status.turn_summaries == []
    assert continued.session.lifecycle_state is ChatSessionLifecycleState.deleted
    assert continued.citations == []
    assert export.export_state is ExportState.unavailable
    assert export.sections == []


def test_ticker_mismatch_does_not_append_or_generate_answer():
    clock = MutableClock()
    store = ChatSessionStore(id_generator=lambda: "44444444444444448444444444444444", clock=clock)
    first = answer_chat_with_session("VOO", ChatRequest(question="What is VOO?"), store=store)
    conversation_id = first.session.conversation_id

    mismatch = answer_chat_with_session(
        "QQQ",
        ChatRequest(question="What is this fund?", conversation_id=conversation_id),
        store=store,
    )
    status = get_chat_session_status(conversation_id, store=store)

    assert mismatch.session.lifecycle_state is ChatSessionLifecycleState.ticker_mismatch
    assert mismatch.session.selected_asset.ticker == "VOO"
    assert mismatch.asset.ticker == "QQQ"
    assert mismatch.citations == []
    assert mismatch.source_documents == []
    assert status.session.turn_count == 1


def test_unsupported_unknown_and_eligible_not_cached_assets_do_not_create_active_sessions():
    store = ChatSessionStore(id_generator=lambda: "55555555555545558555555555555555", clock=MutableClock())

    for ticker in ["BTC", "GME", "SPY", "ZZZZ"]:
        response = answer_chat_with_session(ticker, ChatRequest(question="What is this?"), store=store)

        assert response.asset.supported is False
        assert response.session.lifecycle_state is ChatSessionLifecycleState.unavailable
        assert response.session.conversation_id is None
        assert response.citations == []
        assert response.source_documents == []


def test_advice_redirect_turn_records_no_factual_sources():
    store = ChatSessionStore(id_generator=lambda: "66666666666646668666666666666666", clock=MutableClock())

    response = answer_chat_with_session("VOO", ChatRequest(question="Should I buy VOO today?"), store=store)
    status = get_chat_session_status(response.session.conversation_id, store=store)

    assert response.safety_classification is SafetyClassification.personalized_advice_redirect
    assert response.citations == []
    assert response.source_documents == []
    assert status.session.turn_count == 1
    assert status.session.latest_safety_classification is SafetyClassification.personalized_advice_redirect


def test_session_transcript_export_uses_safe_turn_records_without_question_text():
    clock = MutableClock()
    store = ChatSessionStore(id_generator=lambda: "77777777777747778777777777777777", clock=clock)
    first = answer_chat_with_session("QQQ", ChatRequest(question="What is this fund?"), store=store)
    conversation_id = first.session.conversation_id
    answer_chat_with_session(
        "QQQ",
        ChatRequest(question="What does QQQ hold?", conversation_id=conversation_id),
        store=store,
    )

    metadata, turns = chat_session_export_payload(conversation_id, store=store)

    assert metadata.export_available is True
    assert len(turns) == 2
    assert all(turn.selected_ticker == "QQQ" for turn in turns)
    assert all(turn.direct_answer for turn in turns)
    assert all(not hasattr(turn, "question") for turn in turns)
    assert "What does QQQ hold?" not in str([turn.model_dump(mode="json") for turn in turns])
