from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.chat_session_repository import (
    ACCOUNTLESS_CHAT_SESSION_REPOSITORY_BOUNDARY,
    ACCOUNTLESS_CHAT_SESSION_TABLES,
    ACCOUNTLESS_CHAT_SESSION_TTL_SECONDS,
    AccountlessChatSessionContractError,
    ChatSessionCitationRefRow,
    ChatSessionDiagnosticRow,
    ChatSessionEnvelopeRow,
    ChatSessionExportMetadataRow,
    ChatSessionRepository,
    ChatSessionRepositoryRecords,
    ChatSessionSourceRefRow,
    ChatSessionTurnKind,
    ChatSessionTurnSummaryRow,
    chat_session_repository_metadata,
    validate_chat_session_records,
)
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
from backend.models import EvidenceState, FreshnessState, SourceUsePolicy


ROOT = Path(__file__).resolve().parents[2]


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


def test_compare_redirect_turn_records_preserve_route_metadata_without_sources():
    store = ChatSessionStore(id_generator=lambda: "67676767676746768767676767676767", clock=MutableClock())

    response = answer_chat_with_session("VOO", ChatRequest(question="How is QQQ different from VOO?"), store=store)
    status = get_chat_session_status(response.session.conversation_id, store=store)
    metadata, turns = chat_session_export_payload(response.session.conversation_id, store=store)

    assert response.safety_classification is SafetyClassification.compare_route_redirect
    assert response.compare_route_suggestion is not None
    assert response.citations == []
    assert response.source_documents == []
    assert status.session.latest_safety_classification is SafetyClassification.compare_route_redirect
    assert status.turn_summaries[0].compare_route_suggestion is not None
    assert status.turn_summaries[0].compare_route_suggestion.route == "/compare?left=QQQ&right=VOO"
    assert metadata.export_available is True
    assert turns[0].compare_route_suggestion is not None
    assert turns[0].compare_route_suggestion.comparison_availability_state.value == "available"


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


def _repository_records(
    *,
    conversation_id: str = "9f2c4a6d8e0b4c1f93a7d5e2b8c0a146",
    ticker: str = "VOO",
) -> ChatSessionRepositoryRecords:
    envelope = ChatSessionEnvelopeRow(
        conversation_id=conversation_id,
        selected_asset_ticker=ticker,
        selected_asset_type="etf",
        selected_asset_status="supported",
        selected_asset_identity={
            "ticker": ticker,
            "name": "Vanguard S&P 500 ETF" if ticker == "VOO" else f"{ticker} fixture asset",
            "asset_type": "etf",
            "status": "supported",
            "exchange": "NYSE Arca",
        },
        lifecycle_state=ChatSessionLifecycleState.active.value,
        deletion_status="active",
        created_at="2026-04-23T13:01:25Z",
        last_activity_at="2026-04-23T13:01:25Z",
        expires_at="2026-04-30T13:01:25Z",
        turn_count=1,
        latest_safety_classification=SafetyClassification.educational.value,
        latest_evidence_state=EvidenceState.supported.value,
        latest_freshness_state=FreshnessState.fresh.value,
        export_available=True,
    )
    turn = ChatSessionTurnSummaryRow(
        conversation_id=conversation_id,
        turn_id="turn_1",
        turn_index=1,
        submitted_at="2026-04-23T13:01:25Z",
        selected_ticker=ticker,
        turn_kind=ChatSessionTurnKind.factual_answer.value,
        safety_classification=SafetyClassification.educational.value,
        evidence_state=EvidenceState.supported.value,
        freshness_state=FreshnessState.fresh.value,
        citation_ids=[f"c_{ticker.lower()}_profile"],
        source_document_ids=[f"src_{ticker.lower()}_fact_sheet_fixture"],
        uncertainty_labels=[],
        diagnostics_metadata={"validation_code": "passed", "asset_ticker": ticker},
        exportable_factual_turn=True,
    )
    source = ChatSessionSourceRefRow(
        conversation_id=conversation_id,
        turn_id="turn_1",
        source_document_id=f"src_{ticker.lower()}_fact_sheet_fixture",
        asset_ticker=ticker,
        source_type="issuer_fact_sheet",
        source_use_policy=SourceUsePolicy.full_text_allowed.value,
        allowlist_status="allowed",
        freshness_state=FreshnessState.fresh.value,
        evidence_state=EvidenceState.supported.value,
        citation_ids=[f"c_{ticker.lower()}_profile"],
        export_allowed=True,
    )
    citation = ChatSessionCitationRefRow(
        conversation_id=conversation_id,
        turn_id="turn_1",
        citation_id=f"c_{ticker.lower()}_profile",
        source_document_id=f"src_{ticker.lower()}_fact_sheet_fixture",
        asset_ticker=ticker,
        claim_ref="claim_profile",
    )
    export = ChatSessionExportMetadataRow(
        export_id=f"chat-export-{conversation_id}",
        conversation_id=conversation_id,
        export_format="markdown",
        export_state="available",
        export_available=True,
        selected_ticker=ticker,
        turn_count=1,
        includes_factual_turns=True,
        citation_ids=[f"c_{ticker.lower()}_profile"],
        source_document_ids=[f"src_{ticker.lower()}_fact_sheet_fixture"],
    )
    diagnostic = ChatSessionDiagnosticRow(
        diagnostic_id=f"diag-{conversation_id}",
        conversation_id=conversation_id,
        turn_id="turn_1",
        category="validation",
        code="passed",
        lifecycle_state="active",
        source_document_ids=[f"src_{ticker.lower()}_fact_sheet_fixture"],
        citation_ids=[f"c_{ticker.lower()}_profile"],
        freshness_states={f"src_{ticker.lower()}_fact_sheet_fixture": "fresh"},
        compact_metadata={"validation_code": "passed", "source_count": 1},
        created_at="2026-04-23T13:01:25Z",
    )
    return ChatSessionRepositoryRecords(
        envelopes=[envelope],
        turn_summaries=[turn],
        source_refs=[source],
        citation_refs=[citation],
        export_metadata=[export],
        diagnostics=[diagnostic],
    )


def test_dormant_chat_session_repository_metadata_is_explicit_and_importable():
    metadata = chat_session_repository_metadata()

    assert metadata.boundary == ACCOUNTLESS_CHAT_SESSION_REPOSITORY_BOUNDARY
    assert metadata.opens_connection_on_import is False
    assert metadata.creates_runtime_tables is False
    assert tuple(metadata.tables) == ACCOUNTLESS_CHAT_SESSION_TABLES
    assert set(ACCOUNTLESS_CHAT_SESSION_TABLES) == {
        "accountless_chat_session_envelopes",
        "accountless_chat_session_turn_summaries",
        "accountless_chat_session_source_refs",
        "accountless_chat_session_citation_refs",
        "accountless_chat_session_export_metadata",
        "accountless_chat_session_diagnostics",
    }
    assert "conversation_id" in metadata.tables["accountless_chat_session_envelopes"].columns
    assert "ttl_seconds" in metadata.tables["accountless_chat_session_envelopes"].columns
    assert "comparison_route_metadata" in metadata.tables["accountless_chat_session_turn_summaries"].columns
    assert "source_use_policy" in metadata.tables["accountless_chat_session_source_refs"].columns
    assert "stores_raw_transcript" in metadata.tables["accountless_chat_session_export_metadata"].columns

    revision_path = ROOT / "alembic" / "versions" / "20260425_0006_chat_session_repository_contracts.py"
    spec = importlib.util.spec_from_file_location("chat_session_revision", revision_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "20260425_0006"
    assert module.down_revision == "20260425_0005"
    assert module.ACCOUNTLESS_CHAT_SESSION_TABLE_NAMES == ACCOUNTLESS_CHAT_SESSION_TABLES


def test_dormant_chat_session_repository_validates_ttl_export_and_source_bindings():
    records = _repository_records()
    validated = ChatSessionRepository().persist(records)
    envelope = validated.envelopes[0]

    assert validated.table_names == ACCOUNTLESS_CHAT_SESSION_TABLES
    assert envelope.conversation_id == "9f2c4a6d8e0b4c1f93a7d5e2b8c0a146"
    assert "VOO" not in envelope.conversation_id
    assert envelope.ttl_seconds == ACCOUNTLESS_CHAT_SESSION_TTL_SECONDS
    assert envelope.expires_at == "2026-04-30T13:01:25Z"
    assert envelope.export_available is True
    assert validated.turn_summaries[0].exportable_factual_turn is True
    assert validated.turn_summaries[0].citation_ids == [validated.citation_refs[0].citation_id]
    assert validated.turn_summaries[0].source_document_ids == [validated.source_refs[0].source_document_id]
    assert validated.export_metadata[0].citation_ids == [validated.citation_refs[0].citation_id]

    wrong_ttl = records.envelopes[0].model_copy(update={"expires_at": "2026-04-29T13:01:25Z"})
    with pytest.raises(AccountlessChatSessionContractError, match="seven days"):
        validate_chat_session_records(records.model_copy(update={"envelopes": [wrong_ttl]}))


def test_dormant_chat_session_repository_rejects_identity_leaks_and_ticker_mismatch():
    records = _repository_records()

    ticker_in_id = records.envelopes[0].model_copy(update={"conversation_id": "session-for-voo"})
    changed_turn = records.turn_summaries[0].model_copy(update={"conversation_id": "session-for-voo"})
    changed_source = records.source_refs[0].model_copy(update={"conversation_id": "session-for-voo"})
    changed_citation = records.citation_refs[0].model_copy(update={"conversation_id": "session-for-voo"})
    changed_export = records.export_metadata[0].model_copy(update={"conversation_id": "session-for-voo"})
    changed_diagnostic = records.diagnostics[0].model_copy(update={"conversation_id": "session-for-voo"})
    with pytest.raises(AccountlessChatSessionContractError, match="opaque"):
        validate_chat_session_records(
            records.model_copy(
                update={
                    "envelopes": [ticker_in_id],
                    "turn_summaries": [changed_turn],
                    "source_refs": [changed_source],
                    "citation_refs": [changed_citation],
                    "export_metadata": [changed_export],
                    "diagnostics": [changed_diagnostic],
                }
            )
        )

    wrong_turn_ticker = records.turn_summaries[0].model_copy(update={"selected_ticker": "QQQ"})
    with pytest.raises(AccountlessChatSessionContractError, match="selected asset"):
        validate_chat_session_records(records.model_copy(update={"turn_summaries": [wrong_turn_ticker]}))


def test_dormant_chat_session_repository_preserves_deletion_and_blocked_state_rules():
    records = _repository_records()
    deleted_envelope = records.envelopes[0].model_copy(
        update={
            "lifecycle_state": "deleted",
            "deletion_status": "user_deleted",
            "deleted_at": "2026-04-23T14:01:25Z",
            "turn_count": 0,
            "export_available": False,
        }
    )
    deleted_export = records.export_metadata[0].model_copy(
        update={"export_state": "unavailable", "export_available": False, "turn_count": 0, "citation_ids": [], "source_document_ids": []}
    )
    validate_chat_session_records(
        records.model_copy(
            update={
                "envelopes": [deleted_envelope],
                "turn_summaries": [],
                "source_refs": [],
                "citation_refs": [],
                "export_metadata": [deleted_export],
                "diagnostics": [],
            }
        )
    )

    blocked = records.envelopes[0].model_copy(update={"support_status": "unsupported"})
    with pytest.raises(AccountlessChatSessionContractError, match="Blocked"):
        validate_chat_session_records(records.model_copy(update={"envelopes": [blocked]}))


def test_dormant_chat_session_repository_keeps_advice_and_compare_redirects_metadata_only():
    base = _repository_records()
    advice_turn = base.turn_summaries[0].model_copy(
        update={
            "turn_kind": ChatSessionTurnKind.advice_redirect.value,
            "safety_classification": SafetyClassification.personalized_advice_redirect.value,
            "evidence_state": EvidenceState.unsupported.value,
            "freshness_state": FreshnessState.unknown.value,
            "citation_ids": [],
            "source_document_ids": [],
            "exportable_factual_turn": False,
        }
    )
    redirect_turn = base.turn_summaries[0].model_copy(
        update={
            "turn_id": "turn_2",
            "turn_index": 2,
            "turn_kind": ChatSessionTurnKind.comparison_redirect.value,
            "safety_classification": SafetyClassification.compare_route_redirect.value,
            "evidence_state": EvidenceState.unsupported.value,
            "freshness_state": FreshnessState.unknown.value,
            "citation_ids": [],
            "source_document_ids": [],
            "comparison_route_metadata": {
                "route": "/compare?left=QQQ&right=VOO",
                "left_ticker": "QQQ",
                "right_ticker": "VOO",
                "comparison_availability_state": "available",
            },
            "exportable_factual_turn": False,
        }
    )
    envelope = base.envelopes[0].model_copy(
        update={
            "turn_count": 2,
            "latest_safety_classification": SafetyClassification.compare_route_redirect.value,
            "latest_evidence_state": EvidenceState.unsupported.value,
            "latest_freshness_state": FreshnessState.unknown.value,
            "export_available": True,
        }
    )
    export = base.export_metadata[0].model_copy(
        update={
            "turn_count": 2,
            "includes_factual_turns": False,
            "includes_comparison_redirects": True,
            "citation_ids": [],
            "source_document_ids": [],
        }
    )
    validate_chat_session_records(
        base.model_copy(
            update={
                "envelopes": [envelope],
                "turn_summaries": [advice_turn, redirect_turn],
                "source_refs": [],
                "citation_refs": [],
                "export_metadata": [export],
                "diagnostics": [],
            }
        )
    )

    leaking_advice = advice_turn.model_copy(
        update={
            "citation_ids": ["c_voo_profile"],
            "source_document_ids": ["src_voo_fact_sheet_fixture"],
        }
    )
    with pytest.raises(AccountlessChatSessionContractError, match="Advice redirect"):
        validate_chat_session_records(
            base.model_copy(update={"envelopes": [envelope], "turn_summaries": [leaking_advice, redirect_turn]})
        )

    missing_route = redirect_turn.model_copy(update={"comparison_route_metadata": {}})
    with pytest.raises(AccountlessChatSessionContractError, match="comparison route"):
        validate_chat_session_records(
            base.model_copy(
                update={
                    "envelopes": [envelope],
                    "turn_summaries": [advice_turn, missing_route],
                    "source_refs": [],
                    "citation_refs": [],
                    "export_metadata": [export],
                    "diagnostics": [],
                }
            )
        )


def test_dormant_chat_session_repository_enforces_source_use_citations_and_freshness_labels():
    records = _repository_records()

    metadata_only_raw = records.source_refs[0].model_copy(
        update={"source_use_policy": SourceUsePolicy.metadata_only.value, "stores_raw_chunk_text": True}
    )
    with pytest.raises(AccountlessChatSessionContractError, match="Limited source-use"):
        validate_chat_session_records(records.model_copy(update={"source_refs": [metadata_only_raw]}))

    missing_citation = records.turn_summaries[0].model_copy(update={"citation_ids": []})
    with pytest.raises(AccountlessChatSessionContractError, match="citation IDs"):
        validate_chat_session_records(records.model_copy(update={"turn_summaries": [missing_citation]}))

    stale_source = records.source_refs[0].model_copy(update={"freshness_state": FreshnessState.stale.value})
    with pytest.raises(AccountlessChatSessionContractError, match="Stale source"):
        validate_chat_session_records(records.model_copy(update={"source_refs": [stale_source]}))

    partial_turn = records.turn_summaries[0].model_copy(
        update={"evidence_state": EvidenceState.partial.value, "uncertainty_labels": []}
    )
    with pytest.raises(AccountlessChatSessionContractError, match="uncertainty labels"):
        validate_chat_session_records(records.model_copy(update={"turn_summaries": [partial_turn]}))


def test_dormant_chat_session_repository_rejects_raw_text_prompt_reasoning_secret_diagnostics():
    records = _repository_records()

    raw_turn = records.turn_summaries[0].model_copy(update={"stores_raw_user_text": True})
    with pytest.raises(AccountlessChatSessionContractError, match="safe metadata"):
        validate_chat_session_records(records.model_copy(update={"turn_summaries": [raw_turn]}))

    raw_export = records.export_metadata[0].model_copy(update={"generated_transcript_payload_persisted": True})
    with pytest.raises(AccountlessChatSessionContractError, match="raw transcript"):
        validate_chat_session_records(records.model_copy(update={"export_metadata": [raw_export]}))

    leaking_diagnostic = records.diagnostics[0].model_copy(update={"compact_metadata": {"raw_prompt": "hidden"}})
    with pytest.raises(AccountlessChatSessionContractError, match="sanitized"):
        validate_chat_session_records(records.model_copy(update={"diagnostics": [leaking_diagnostic]}))


def test_dormant_chat_session_repository_imports_do_not_open_live_paths():
    repository_source = (ROOT / "backend" / "repositories" / "chat_sessions.py").read_text(encoding="utf-8")
    forbidden = [
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "requests",
        "httpx",
        "redis",
        "boto3",
        "OPENROUTER",
        "openai",
        "os.environ",
        "api_key",
    ]
    for marker in forbidden:
        assert marker not in repository_source

    class BadSession:
        pass

    with pytest.raises(AccountlessChatSessionContractError, match="add_all"):
        ChatSessionRepository(session=BadSession()).persist(_repository_records())
