"""Add dormant accountless chat session contract tables.

Revision ID: 20260425_0006
Revises: 20260425_0005
Create Date: 2026-04-25 18:55:21 UTC

The tables defined here are an inspectable metadata contract only. Current API,
chat, export, retrieval, generation, provider, cache, database, frontend, and
session lifecycle behavior remains unchanged and does not route through durable
chat session persistence in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0006"
down_revision: str | None = "20260425_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCOUNTLESS_CHAT_SESSION_TABLE_NAMES = (
    "accountless_chat_session_envelopes",
    "accountless_chat_session_turn_summaries",
    "accountless_chat_session_source_refs",
    "accountless_chat_session_citation_refs",
    "accountless_chat_session_export_metadata",
    "accountless_chat_session_diagnostics",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "accountless_chat_session_envelopes",
        sa.Column("conversation_id", sa.String(), primary_key=True),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("selected_asset_ticker", sa.String(), nullable=False),
        sa.Column("selected_asset_type", sa.String(), nullable=False),
        sa.Column("selected_asset_status", sa.String(), nullable=False),
        sa.Column("selected_asset_identity", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(), nullable=False),
        sa.Column("deletion_status", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("last_activity_at", sa.String(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
        sa.Column("deleted_at", sa.String(), nullable=True),
        sa.Column("ttl_days", sa.Integer(), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("latest_safety_classification", sa.String(), nullable=True),
        sa.Column("latest_evidence_state", sa.String(), nullable=True),
        sa.Column("latest_freshness_state", sa.String(), nullable=True),
        sa.Column("support_status", sa.String(), nullable=False),
        sa.Column("export_available", sa.Boolean(), nullable=False),
        sa.Column("user_identity_stored", sa.Boolean(), nullable=False),
        sa.Column("personalized_financial_context_stored", sa.Boolean(), nullable=False),
        sa.Column("no_live_external_calls", sa.Boolean(), nullable=False),
        sa.Column("live_database_execution", sa.Boolean(), nullable=False),
        sa.Column("live_cache_execution", sa.Boolean(), nullable=False),
        sa.Column("provider_or_llm_call_required", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_answer_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_transcript", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "accountless_chat_session_turn_summaries",
        sa.Column("conversation_id", sa.String(), primary_key=True),
        sa.Column("turn_id", sa.String(), primary_key=True),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.String(), nullable=False),
        sa.Column("selected_ticker", sa.String(), nullable=False),
        sa.Column("turn_kind", sa.String(), nullable=False),
        sa.Column("safety_classification", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("uncertainty_labels", sa.JSON(), nullable=False),
        sa.Column("comparison_route_metadata", sa.JSON(), nullable=False),
        sa.Column("diagnostics_metadata", sa.JSON(), nullable=False),
        sa.Column("exportable_factual_turn", sa.Boolean(), nullable=False),
        sa.Column("generated_answer_artifact_persisted", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_answer_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_transcript", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["accountless_chat_session_envelopes.conversation_id"]),
    )
    op.create_table(
        "accountless_chat_session_source_refs",
        sa.Column("conversation_id", sa.String(), primary_key=True),
        sa.Column("turn_id", sa.String(), primary_key=True),
        sa.Column("source_document_id", sa.String(), primary_key=True),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("export_allowed", sa.Boolean(), nullable=False),
        sa.Column("allowed_summary_or_excerpt_only", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_chunk_text", sa.Boolean(), nullable=False),
        sa.Column("stores_unrestricted_excerpt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id", "turn_id"],
            ["accountless_chat_session_turn_summaries.conversation_id", "accountless_chat_session_turn_summaries.turn_id"],
        ),
    )
    op.create_table(
        "accountless_chat_session_citation_refs",
        sa.Column("conversation_id", sa.String(), primary_key=True),
        sa.Column("turn_id", sa.String(), primary_key=True),
        sa.Column("citation_id", sa.String(), primary_key=True),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("claim_ref", sa.String(), nullable=True),
        sa.Column("important_claim", sa.Boolean(), nullable=False),
        sa.Column("citation_validation_status", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("uncertainty_label", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id", "turn_id"],
            ["accountless_chat_session_turn_summaries.conversation_id", "accountless_chat_session_turn_summaries.turn_id"],
        ),
    )
    op.create_table(
        "accountless_chat_session_export_metadata",
        sa.Column("export_id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("export_format", sa.String(), nullable=False),
        sa.Column("export_state", sa.String(), nullable=False),
        sa.Column("export_available", sa.Boolean(), nullable=False),
        sa.Column("selected_ticker", sa.String(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("includes_factual_turns", sa.Boolean(), nullable=False),
        sa.Column("includes_comparison_redirects", sa.Boolean(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("licensing_scope", sa.String(), nullable=False),
        sa.Column("generated_transcript_payload_persisted", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_answer_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_transcript", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["accountless_chat_session_envelopes.conversation_id"]),
    )
    op.create_table(
        "accountless_chat_session_diagnostics",
        sa.Column("diagnostic_id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("turn_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("lifecycle_state", sa.String(), nullable=True),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("freshness_states", sa.JSON(), nullable=False),
        sa.Column("compact_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.Column("stores_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_answer_text", sa.Boolean(), nullable=False),
        sa.Column("stores_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_unrestricted_excerpt", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["accountless_chat_session_envelopes.conversation_id"]),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(ACCOUNTLESS_CHAT_SESSION_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
