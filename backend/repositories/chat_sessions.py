from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.models import (
    ChatSessionDeletionStatus,
    ChatSessionLifecycleState,
    EvidenceState,
    FreshnessState,
    SafetyClassification,
    SourceAllowlistStatus,
    SourceUsePolicy,
)
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow


ACCOUNTLESS_CHAT_SESSION_REPOSITORY_BOUNDARY = "accountless-chat-session-repository-contract-v1"
ACCOUNTLESS_CHAT_SESSION_SCHEMA_VERSION = "accountless-chat-session-contract-v1"
ACCOUNTLESS_CHAT_SESSION_TTL_DAYS = 7
ACCOUNTLESS_CHAT_SESSION_TTL_SECONDS = ACCOUNTLESS_CHAT_SESSION_TTL_DAYS * 24 * 60 * 60
ACCOUNTLESS_CHAT_SESSION_TABLES = (
    "accountless_chat_session_envelopes",
    "accountless_chat_session_turn_summaries",
    "accountless_chat_session_source_refs",
    "accountless_chat_session_citation_refs",
    "accountless_chat_session_export_metadata",
    "accountless_chat_session_diagnostics",
)

_BLOCKED_SUPPORT_STATES = {
    "unsupported",
    "out_of_scope",
    "eligible_not_cached",
    "unknown",
    "unavailable",
    "source_policy_blocked",
    "validation_failed",
    "stale_without_label",
    "partial_without_label",
    "insufficient_evidence_without_label",
}
_TEXT_LIMITED_POLICIES = {
    SourceUsePolicy.metadata_only.value,
    SourceUsePolicy.link_only.value,
}
_FORBIDDEN_METADATA_MARKERS = (
    "authorization",
    "bearer ",
    "secret",
    "private key",
    "raw_prompt",
    "hidden_prompt",
    "raw_model_reasoning",
    "reasoning_payload",
    "raw_article_text",
    "raw_provider_payload",
    "raw_source_text",
    "raw_user_text",
    "user_question",
    "submitted_question",
    "question_text",
    "raw_answer",
    "answer_text",
    "direct_answer",
    "why_it_matters",
    "chat_transcript",
    "transcript",
    "portfolio",
    "allocation",
    "position_size",
    "signed_url",
    "public_url",
    "api" + "_key",
)


class AccountlessChatSessionContractError(ValueError):
    """Raised when dormant accountless chat session metadata would violate safety contracts."""


class ChatSessionTurnKind(str, Enum):
    factual_answer = "factual_answer"
    advice_redirect = "advice_redirect"
    comparison_redirect = "comparison_redirect"
    insufficient_evidence = "insufficient_evidence"
    unsupported_asset_redirect = "unsupported_asset_redirect"


class ChatSessionDiagnosticCategory(str, Enum):
    lifecycle = "lifecycle"
    validation = "validation"
    deletion = "deletion"
    export = "export"
    citation_binding = "citation_binding"
    source_policy = "source_policy"
    freshness = "freshness"
    comparison_redirect = "comparison_redirect"
    safety = "safety"


class ChatSessionEnvelopeRow(StrictRow):
    conversation_id: str
    schema_version: str = ACCOUNTLESS_CHAT_SESSION_SCHEMA_VERSION
    selected_asset_ticker: str
    selected_asset_type: str
    selected_asset_status: str
    selected_asset_identity: dict[str, Any]
    lifecycle_state: str
    deletion_status: str
    created_at: str
    last_activity_at: str
    expires_at: str
    deleted_at: str | None = None
    ttl_days: int = ACCOUNTLESS_CHAT_SESSION_TTL_DAYS
    ttl_seconds: int = ACCOUNTLESS_CHAT_SESSION_TTL_SECONDS
    turn_count: int = 0
    latest_safety_classification: str | None = None
    latest_evidence_state: str | None = None
    latest_freshness_state: str | None = None
    support_status: str = "supported"
    export_available: bool = False
    user_identity_stored: bool = False
    personalized_financial_context_stored: bool = False
    no_live_external_calls: bool = True
    live_database_execution: bool = False
    live_cache_execution: bool = False
    provider_or_llm_call_required: bool = False
    stores_raw_user_text: bool = False
    stores_raw_answer_text: bool = False
    stores_raw_transcript: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_secret: bool = False

    @field_validator("lifecycle_state")
    @classmethod
    def _valid_lifecycle_state(cls, value: str) -> str:
        ChatSessionLifecycleState(value)
        return value

    @field_validator("deletion_status")
    @classmethod
    def _valid_deletion_status(cls, value: str) -> str:
        ChatSessionDeletionStatus(value)
        return value


class ChatSessionTurnSummaryRow(StrictRow):
    conversation_id: str
    turn_id: str
    turn_index: int
    submitted_at: str
    selected_ticker: str
    turn_kind: str
    safety_classification: str
    evidence_state: str
    freshness_state: str
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    uncertainty_labels: list[str] = Field(default_factory=list)
    comparison_route_metadata: dict[str, Any] = Field(default_factory=dict)
    diagnostics_metadata: dict[str, Any] = Field(default_factory=dict)
    exportable_factual_turn: bool = False
    generated_answer_artifact_persisted: bool = False
    stores_raw_user_text: bool = False
    stores_raw_answer_text: bool = False
    stores_raw_transcript: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_secret: bool = False

    @field_validator("turn_kind")
    @classmethod
    def _valid_turn_kind(cls, value: str) -> str:
        ChatSessionTurnKind(value)
        return value

    @field_validator("safety_classification")
    @classmethod
    def _valid_safety_classification(cls, value: str) -> str:
        SafetyClassification(value)
        return value

    @field_validator("evidence_state")
    @classmethod
    def _valid_evidence_state(cls, value: str) -> str:
        EvidenceState(value)
        return value

    @field_validator("freshness_state")
    @classmethod
    def _valid_freshness_state(cls, value: str) -> str:
        FreshnessState(value)
        return value


class ChatSessionSourceRefRow(StrictRow):
    conversation_id: str
    turn_id: str
    source_document_id: str
    asset_ticker: str
    source_type: str
    source_use_policy: str
    allowlist_status: str
    freshness_state: str
    evidence_state: str
    citation_ids: list[str] = Field(default_factory=list)
    export_allowed: bool = False
    allowed_summary_or_excerpt_only: bool = True
    stores_raw_chunk_text: bool = False
    stores_unrestricted_excerpt: bool = False
    stores_raw_provider_payload: bool = False

    @field_validator("source_use_policy")
    @classmethod
    def _valid_source_use_policy(cls, value: str) -> str:
        SourceUsePolicy(value)
        return value

    @field_validator("allowlist_status")
    @classmethod
    def _valid_allowlist_status(cls, value: str) -> str:
        SourceAllowlistStatus(value)
        return value

    @field_validator("freshness_state")
    @classmethod
    def _valid_freshness_state(cls, value: str) -> str:
        FreshnessState(value)
        return value


class ChatSessionCitationRefRow(StrictRow):
    conversation_id: str
    turn_id: str
    citation_id: str
    source_document_id: str
    asset_ticker: str
    claim_ref: str | None = None
    important_claim: bool = True
    citation_validation_status: str = "passed"
    evidence_state: str = EvidenceState.supported.value
    freshness_state: str = FreshnessState.fresh.value
    uncertainty_label: str | None = None


class ChatSessionExportMetadataRow(StrictRow):
    export_id: str
    conversation_id: str
    export_format: str
    export_state: str
    export_available: bool
    selected_ticker: str
    turn_count: int
    includes_factual_turns: bool = False
    includes_comparison_redirects: bool = False
    citation_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    licensing_scope: str = "metadata_and_allowed_excerpt_only"
    generated_transcript_payload_persisted: bool = False
    stores_raw_user_text: bool = False
    stores_raw_answer_text: bool = False
    stores_raw_transcript: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False
    stores_raw_source_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_secret: bool = False


class ChatSessionDiagnosticRow(StrictRow):
    diagnostic_id: str
    conversation_id: str | None = None
    turn_id: str | None = None
    category: str
    code: str
    lifecycle_state: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    freshness_states: dict[str, str] = Field(default_factory=dict)
    compact_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    stores_secret: bool = False
    stores_user_text: bool = False
    stores_answer_text: bool = False
    stores_provider_payload: bool = False
    stores_raw_source_text: bool = False
    stores_unrestricted_excerpt: bool = False
    stores_hidden_prompt: bool = False
    stores_raw_model_reasoning: bool = False

    @field_validator("category")
    @classmethod
    def _valid_category(cls, value: str) -> str:
        ChatSessionDiagnosticCategory(value)
        return value


class ChatSessionRepositoryRecords(StrictRow):
    envelopes: list[ChatSessionEnvelopeRow] = Field(default_factory=list)
    turn_summaries: list[ChatSessionTurnSummaryRow] = Field(default_factory=list)
    source_refs: list[ChatSessionSourceRefRow] = Field(default_factory=list)
    citation_refs: list[ChatSessionCitationRefRow] = Field(default_factory=list)
    export_metadata: list[ChatSessionExportMetadataRow] = Field(default_factory=list)
    diagnostics: list[ChatSessionDiagnosticRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return ACCOUNTLESS_CHAT_SESSION_TABLES


def chat_session_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=ACCOUNTLESS_CHAT_SESSION_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="accountless_chat_session_envelopes",
                primary_key=("conversation_id",),
                columns=tuple(ChatSessionEnvelopeRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="accountless_chat_session_turn_summaries",
                primary_key=("conversation_id", "turn_id"),
                columns=tuple(ChatSessionTurnSummaryRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="accountless_chat_session_source_refs",
                primary_key=("conversation_id", "turn_id", "source_document_id"),
                columns=tuple(ChatSessionSourceRefRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="accountless_chat_session_citation_refs",
                primary_key=("conversation_id", "turn_id", "citation_id"),
                columns=tuple(ChatSessionCitationRefRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="accountless_chat_session_export_metadata",
                primary_key=("export_id",),
                columns=tuple(ChatSessionExportMetadataRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="accountless_chat_session_diagnostics",
                primary_key=("diagnostic_id",),
                columns=tuple(ChatSessionDiagnosticRow.model_fields),
            ),
        ),
    )


@dataclass
class ChatSessionRepository:
    session: Any | None = None

    def validate(self, records: ChatSessionRepositoryRecords) -> ChatSessionRepositoryRecords:
        return validate_chat_session_records(records)

    def persist(self, records: ChatSessionRepositoryRecords) -> ChatSessionRepositoryRecords:
        validated = validate_chat_session_records(records)
        if self.session is None:
            return validated
        if not hasattr(self.session, "add_all"):
            raise AccountlessChatSessionContractError("Injected chat session repository session must expose add_all(records).")
        self.session.add_all(records_to_row_list(validated))
        return validated


def validate_chat_session_records(records: ChatSessionRepositoryRecords) -> ChatSessionRepositoryRecords:
    conversation_ids = _unique("chat session conversation IDs", [row.conversation_id for row in records.envelopes])
    turn_keys = _unique("chat session turn IDs", [f"{row.conversation_id}:{row.turn_id}" for row in records.turn_summaries])
    source_keys = _unique(
        "chat session source references",
        [f"{row.conversation_id}:{row.turn_id}:{row.source_document_id}" for row in records.source_refs],
    )
    citation_keys = _unique(
        "chat session citation references",
        [f"{row.conversation_id}:{row.turn_id}:{row.citation_id}" for row in records.citation_refs],
    )
    _unique("chat session export IDs", [row.export_id for row in records.export_metadata])
    _unique("chat session diagnostic IDs", [row.diagnostic_id for row in records.diagnostics])

    for turn in records.turn_summaries:
        if turn.conversation_id not in conversation_ids:
            raise AccountlessChatSessionContractError("Chat session turns must reference known conversation IDs.")
        _validate_turn_raw_storage(turn)
        _validate_compact_metadata(turn.comparison_route_metadata)
        _validate_compact_metadata(turn.diagnostics_metadata)

    for source in records.source_refs:
        if source.conversation_id not in conversation_ids or f"{source.conversation_id}:{source.turn_id}" not in turn_keys:
            raise AccountlessChatSessionContractError("Chat session source references must bind to known turns.")
        _validate_source_ref(source)

    for citation in records.citation_refs:
        if citation.conversation_id not in conversation_ids or f"{citation.conversation_id}:{citation.turn_id}" not in turn_keys:
            raise AccountlessChatSessionContractError("Chat session citation references must bind to known turns.")
        if f"{citation.conversation_id}:{citation.turn_id}:{citation.source_document_id}" not in source_keys:
            raise AccountlessChatSessionContractError("Chat session citations must bind to same-turn source references.")
        if citation.citation_validation_status != "passed":
            raise AccountlessChatSessionContractError("Chat session citation references require passed validation.")

    for export in records.export_metadata:
        if export.conversation_id not in conversation_ids:
            raise AccountlessChatSessionContractError("Chat session export metadata must reference known conversation IDs.")
        _validate_export_metadata(export)

    for diagnostic in records.diagnostics:
        if diagnostic.conversation_id and diagnostic.conversation_id not in conversation_ids:
            raise AccountlessChatSessionContractError("Chat session diagnostics must reference known conversation IDs.")
        if diagnostic.turn_id and diagnostic.conversation_id and f"{diagnostic.conversation_id}:{diagnostic.turn_id}" not in turn_keys:
            raise AccountlessChatSessionContractError("Chat session diagnostics must reference known turns.")
        _validate_diagnostic(diagnostic)

    for envelope in records.envelopes:
        _validate_envelope(
            envelope,
            [row for row in records.turn_summaries if row.conversation_id == envelope.conversation_id],
            [row for row in records.source_refs if row.conversation_id == envelope.conversation_id],
            [row for row in records.citation_refs if row.conversation_id == envelope.conversation_id],
            [row for row in records.export_metadata if row.conversation_id == envelope.conversation_id],
        )

    if citation_keys:
        pass
    return records


def records_to_row_list(records: ChatSessionRepositoryRecords) -> list[StrictRow]:
    validate_chat_session_records(records)
    return [
        *records.envelopes,
        *records.turn_summaries,
        *records.source_refs,
        *records.citation_refs,
        *records.export_metadata,
        *records.diagnostics,
    ]


def _validate_envelope(
    envelope: ChatSessionEnvelopeRow,
    turns: list[ChatSessionTurnSummaryRow],
    sources: list[ChatSessionSourceRefRow],
    citations: list[ChatSessionCitationRefRow],
    exports: list[ChatSessionExportMetadataRow],
) -> None:
    _validate_envelope_raw_storage(envelope)
    _validate_opaque_conversation_id(envelope)
    _validate_ttl(envelope)

    if envelope.turn_count != len(turns):
        raise AccountlessChatSessionContractError("Chat session envelope turn_count must match safe turn summary rows.")
    if envelope.support_status in _BLOCKED_SUPPORT_STATES:
        if envelope.export_available or any(turn.exportable_factual_turn or turn.generated_answer_artifact_persisted for turn in turns):
            raise AccountlessChatSessionContractError("Blocked chat session states cannot create persisted factual answers or exports.")

    lifecycle = ChatSessionLifecycleState(envelope.lifecycle_state)
    deletion = ChatSessionDeletionStatus(envelope.deletion_status)
    if lifecycle is ChatSessionLifecycleState.deleted:
        if deletion is not ChatSessionDeletionStatus.user_deleted or not envelope.deleted_at or envelope.export_available:
            raise AccountlessChatSessionContractError("Deleted chat sessions must be idempotent user-deleted records without export availability.")
    elif lifecycle is ChatSessionLifecycleState.expired:
        if deletion is not ChatSessionDeletionStatus.expired or envelope.export_available:
            raise AccountlessChatSessionContractError("Expired chat sessions must preserve expired metadata without export availability.")
    elif lifecycle in {ChatSessionLifecycleState.ticker_mismatch, ChatSessionLifecycleState.unavailable}:
        if envelope.export_available:
            raise AccountlessChatSessionContractError("Ticker-mismatch and unavailable chat sessions cannot expose exports.")
    elif lifecycle is ChatSessionLifecycleState.active:
        if deletion is not ChatSessionDeletionStatus.active:
            raise AccountlessChatSessionContractError("Active chat sessions require active deletion status.")

    for turn in turns:
        _validate_turn_for_envelope(turn, envelope, sources, citations)
    for export in exports:
        if export.selected_ticker != envelope.selected_asset_ticker:
            raise AccountlessChatSessionContractError("Chat session export metadata must preserve selected-asset identity.")
        if export.export_available != envelope.export_available:
            raise AccountlessChatSessionContractError("Chat session export availability must match the session envelope.")
        if set(export.citation_ids) - {citation.citation_id for citation in citations}:
            raise AccountlessChatSessionContractError("Chat session export metadata cannot reference missing citations.")
        if set(export.source_document_ids) - {source.source_document_id for source in sources}:
            raise AccountlessChatSessionContractError("Chat session export metadata cannot reference missing sources.")


def _validate_turn_for_envelope(
    turn: ChatSessionTurnSummaryRow,
    envelope: ChatSessionEnvelopeRow,
    sources: list[ChatSessionSourceRefRow],
    citations: list[ChatSessionCitationRefRow],
) -> None:
    if turn.selected_ticker != envelope.selected_asset_ticker:
        raise AccountlessChatSessionContractError("Chat session turns must stay bound to the selected asset.")
    if turn.turn_index < 1:
        raise AccountlessChatSessionContractError("Chat session turn indexes start at one.")
    turn_sources = [source for source in sources if source.turn_id == turn.turn_id]
    turn_citations = [citation for citation in citations if citation.turn_id == turn.turn_id]
    if set(turn.source_document_ids) != {source.source_document_id for source in turn_sources}:
        raise AccountlessChatSessionContractError("Chat turn source IDs must match same-turn source reference rows.")
    if set(turn.citation_ids) != {citation.citation_id for citation in turn_citations}:
        raise AccountlessChatSessionContractError("Chat turn citation IDs must match same-turn citation reference rows.")

    safety = SafetyClassification(turn.safety_classification)
    evidence = EvidenceState(turn.evidence_state)
    freshness = FreshnessState(turn.freshness_state)
    kind = ChatSessionTurnKind(turn.turn_kind)

    if safety is SafetyClassification.personalized_advice_redirect or kind is ChatSessionTurnKind.advice_redirect:
        if turn.citation_ids or turn.source_document_ids or turn.exportable_factual_turn or turn.generated_answer_artifact_persisted:
            raise AccountlessChatSessionContractError("Advice redirect turns may persist only safe metadata without factual evidence.")
        if evidence is not EvidenceState.unsupported:
            raise AccountlessChatSessionContractError("Advice redirect turns must be marked unsupported factual evidence.")
    if safety is SafetyClassification.compare_route_redirect or kind is ChatSessionTurnKind.comparison_redirect:
        if turn.citation_ids or turn.source_document_ids or turn.exportable_factual_turn or turn.generated_answer_artifact_persisted:
            raise AccountlessChatSessionContractError("Comparison redirect turns may persist only safe route metadata.")
        route = str(turn.comparison_route_metadata.get("route", ""))
        if not route.startswith("/compare?"):
            raise AccountlessChatSessionContractError("Comparison redirect metadata must preserve a comparison route.")
    if safety is SafetyClassification.educational and turn.exportable_factual_turn:
        if evidence is EvidenceState.supported and not turn.citation_ids:
            raise AccountlessChatSessionContractError("Important factual chat turns require same-asset citation IDs.")
        if not turn.source_document_ids and evidence is EvidenceState.supported:
            raise AccountlessChatSessionContractError("Important factual chat turns require same-asset source references.")

    if evidence in {EvidenceState.partial, EvidenceState.insufficient_evidence, EvidenceState.unknown, EvidenceState.unavailable}:
        expected_label = evidence.value
        if expected_label not in " ".join(turn.uncertainty_labels).lower():
            raise AccountlessChatSessionContractError("Uncertain chat turns must preserve explicit uncertainty labels.")
    if freshness in {FreshnessState.unknown, FreshnessState.unavailable} and evidence is EvidenceState.supported:
        raise AccountlessChatSessionContractError("Supported factual turns cannot use unknown or unavailable freshness.")
    if any(source.freshness_state == FreshnessState.stale.value for source in turn_sources) and freshness is not FreshnessState.stale:
        raise AccountlessChatSessionContractError("Stale source references must be retained in turn freshness metadata.")


def _validate_source_ref(source: ChatSessionSourceRefRow) -> None:
    if source.allowlist_status != SourceAllowlistStatus.allowed.value:
        raise AccountlessChatSessionContractError("Chat session source references require allowed source status.")
    if source.source_use_policy == SourceUsePolicy.rejected.value:
        raise AccountlessChatSessionContractError("Rejected sources cannot feed chat session metadata.")
    if source.source_use_policy in _TEXT_LIMITED_POLICIES and (source.stores_raw_chunk_text or source.stores_unrestricted_excerpt):
        raise AccountlessChatSessionContractError("Limited source-use policies cannot persist raw chunk text.")
    if source.stores_raw_provider_payload:
        raise AccountlessChatSessionContractError("Chat session source references cannot persist raw provider payloads.")


def _validate_export_metadata(export: ChatSessionExportMetadataRow) -> None:
    if (
        export.generated_transcript_payload_persisted
        or export.stores_raw_user_text
        or export.stores_raw_answer_text
        or export.stores_raw_transcript
        or export.stores_hidden_prompt
        or export.stores_raw_model_reasoning
        or export.stores_raw_source_text
        or export.stores_raw_provider_payload
        or export.stores_secret
    ):
        raise AccountlessChatSessionContractError("Chat session export metadata must not persist raw transcript payloads.")
    if export.export_available and export.export_state != "available":
        raise AccountlessChatSessionContractError("Available chat session exports require available export state.")
    if not export.export_available and export.export_state == "available":
        raise AccountlessChatSessionContractError("Unavailable chat session exports cannot use available export state.")


def _validate_diagnostic(diagnostic: ChatSessionDiagnosticRow) -> None:
    _validate_compact_metadata(diagnostic.compact_metadata)
    if (
        diagnostic.stores_secret
        or diagnostic.stores_user_text
        or diagnostic.stores_answer_text
        or diagnostic.stores_provider_payload
        or diagnostic.stores_raw_source_text
        or diagnostic.stores_unrestricted_excerpt
        or diagnostic.stores_hidden_prompt
        or diagnostic.stores_raw_model_reasoning
    ):
        raise AccountlessChatSessionContractError("Chat session diagnostics must store compact sanitized metadata only.")


def _validate_turn_raw_storage(turn: ChatSessionTurnSummaryRow) -> None:
    if (
        turn.stores_raw_user_text
        or turn.stores_raw_answer_text
        or turn.stores_raw_transcript
        or turn.stores_hidden_prompt
        or turn.stores_raw_model_reasoning
        or turn.stores_raw_source_text
        or turn.stores_raw_provider_payload
        or turn.stores_secret
    ):
        raise AccountlessChatSessionContractError("Chat session turn summaries must store safe metadata only.")


def _validate_envelope_raw_storage(envelope: ChatSessionEnvelopeRow) -> None:
    if (
        envelope.user_identity_stored
        or envelope.personalized_financial_context_stored
        or not envelope.no_live_external_calls
        or envelope.live_database_execution
        or envelope.live_cache_execution
        or envelope.provider_or_llm_call_required
        or envelope.stores_raw_user_text
        or envelope.stores_raw_answer_text
        or envelope.stores_raw_transcript
        or envelope.stores_hidden_prompt
        or envelope.stores_raw_model_reasoning
        or envelope.stores_raw_source_text
        or envelope.stores_raw_provider_payload
        or envelope.stores_secret
    ):
        raise AccountlessChatSessionContractError("Chat session envelopes must be anonymous, dormant, and metadata-only.")


def _validate_opaque_conversation_id(envelope: ChatSessionEnvelopeRow) -> None:
    conversation_id = envelope.conversation_id.lower()
    ticker = envelope.selected_asset_ticker.lower()
    if not envelope.conversation_id or ticker in conversation_id:
        raise AccountlessChatSessionContractError("Chat session conversation IDs must be anonymous and opaque.")
    identity_text = repr(envelope.selected_asset_identity).lower()
    for token in identity_text.replace(",", " ").replace(".", " ").split():
        cleaned = "".join(character for character in token if character.isalnum())
        if len(cleaned) >= 4 and cleaned in conversation_id:
            raise AccountlessChatSessionContractError("Chat session conversation IDs cannot embed selected-asset identity.")


def _validate_ttl(envelope: ChatSessionEnvelopeRow) -> None:
    if envelope.ttl_days != ACCOUNTLESS_CHAT_SESSION_TTL_DAYS or envelope.ttl_seconds != ACCOUNTLESS_CHAT_SESSION_TTL_SECONDS:
        raise AccountlessChatSessionContractError("Chat session TTL metadata must remain seven days.")
    last_activity = _parse_timestamp(envelope.last_activity_at)
    expires_at = _parse_timestamp(envelope.expires_at)
    if expires_at - last_activity != timedelta(seconds=ACCOUNTLESS_CHAT_SESSION_TTL_SECONDS):
        raise AccountlessChatSessionContractError("Chat session expires_at must be seven days after last activity.")
    if _parse_timestamp(envelope.created_at) > last_activity:
        raise AccountlessChatSessionContractError("Chat session activity timestamps cannot precede creation.")


def _validate_compact_metadata(metadata: dict[str, Any]) -> None:
    text = repr(metadata).lower()
    if any(marker in text for marker in _FORBIDDEN_METADATA_MARKERS):
        raise AccountlessChatSessionContractError("Chat session metadata and diagnostics must be compact and sanitized.")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _unique(label: str, values: list[str]) -> set[str]:
    seen = set(values)
    if len(seen) != len(values):
        raise AccountlessChatSessionContractError(f"{label} must be unique.")
    return seen
