"""Add dormant generated-output cache contract tables.

Revision ID: 20260425_0005
Revises: 20260425_0004
Create Date: 2026-04-25 18:04:25 UTC

The tables defined here are an inspectable metadata contract only. Current API,
retrieval, generation, chat, comparison, export, glossary, provider, cache,
database, worker, and frontend behavior remains unchanged and does not route
through generated-output cache persistence in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0005"
down_revision: str | None = "20260425_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENERATED_OUTPUT_CACHE_TABLE_NAMES = (
    "generated_output_cache_envelopes",
    "generated_output_cache_artifacts",
    "generated_output_cache_source_checksums",
    "generated_output_cache_knowledge_pack_hash_inputs",
    "generated_output_cache_freshness_hash_inputs",
    "generated_output_cache_validation_statuses",
    "generated_output_cache_diagnostics",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "generated_output_cache_envelopes",
        sa.Column("cache_entry_id", sa.String(), primary_key=True),
        sa.Column("cache_key", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("entry_kind", sa.String(), nullable=False),
        sa.Column("cache_scope", sa.String(), nullable=False),
        sa.Column("scope_kind", sa.String(), nullable=False),
        sa.Column("artifact_category", sa.String(), nullable=False),
        sa.Column("output_identity", sa.String(), nullable=False),
        sa.Column("mode_or_output_type", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=True),
        sa.Column("comparison_id", sa.String(), nullable=True),
        sa.Column("comparison_left_ticker", sa.String(), nullable=True),
        sa.Column("comparison_right_ticker", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("deterministic_mock_marker", sa.String(), nullable=True),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("section_ids", sa.JSON(), nullable=False),
        sa.Column("source_checksum_ids", sa.JSON(), nullable=False),
        sa.Column("knowledge_pack_freshness_hash", sa.String(), nullable=True),
        sa.Column("generated_output_freshness_hash", sa.String(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("citation_validation_status", sa.String(), nullable=False),
        sa.Column("safety_status", sa.String(), nullable=False),
        sa.Column("source_use_status", sa.String(), nullable=False),
        sa.Column("citation_coverage_status", sa.String(), nullable=False),
        sa.Column("source_freshness_states", sa.JSON(), nullable=False),
        sa.Column("section_freshness_labels", sa.JSON(), nullable=False),
        sa.Column("evidence_state_labels", sa.JSON(), nullable=False),
        sa.Column("support_status", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("cache_state", sa.String(), nullable=False),
        sa.Column("cacheable", sa.Boolean(), nullable=False),
        sa.Column("generated_output_available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=True),
        sa.Column("ttl_seconds", sa.Integer(), nullable=True),
        sa.Column("invalidation_reasons", sa.JSON(), nullable=False),
        sa.Column("blocked_reasons", sa.JSON(), nullable=False),
        sa.Column("no_live_external_calls", sa.Boolean(), nullable=False),
        sa.Column("live_database_execution", sa.Boolean(), nullable=False),
        sa.Column("live_cache_execution", sa.Boolean(), nullable=False),
        sa.Column("provider_or_llm_call_required", sa.Boolean(), nullable=False),
        sa.Column("stores_generated_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_chat_transcript", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "generated_output_cache_artifacts",
        sa.Column("artifact_id", sa.String(), primary_key=True),
        sa.Column("cache_entry_id", sa.String(), nullable=False),
        sa.Column("artifact_category", sa.String(), nullable=False),
        sa.Column("content_format", sa.String(), nullable=False),
        sa.Column("output_checksum", sa.String(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("section_freshness_labels", sa.JSON(), nullable=False),
        sa.Column("payload_metadata", sa.JSON(), nullable=False),
        sa.Column("stores_payload_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_chat_transcript", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["cache_entry_id"], ["generated_output_cache_envelopes.cache_entry_id"]),
    )
    op.create_table(
        "generated_output_cache_source_checksums",
        sa.Column("cache_entry_id", sa.String(), primary_key=True),
        sa.Column("source_document_id", sa.String(), primary_key=True),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("cache_allowed", sa.Boolean(), nullable=False),
        sa.Column("export_allowed", sa.Boolean(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=True),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("fact_bindings", sa.JSON(), nullable=False),
        sa.Column("recent_event_bindings", sa.JSON(), nullable=False),
    )
    op.create_table(
        "generated_output_cache_knowledge_pack_hash_inputs",
        sa.Column("cache_entry_id", sa.String(), primary_key=True),
        sa.Column("input_id", sa.String(), primary_key=True),
        sa.Column("asset_ticker", sa.String(), nullable=True),
        sa.Column("comparison_id", sa.String(), nullable=True),
        sa.Column("comparison_left_ticker", sa.String(), nullable=True),
        sa.Column("comparison_right_ticker", sa.String(), nullable=True),
        sa.Column("pack_identity", sa.String(), nullable=True),
        sa.Column("knowledge_pack_freshness_hash", sa.String(), nullable=False),
        sa.Column("page_freshness_state", sa.String(), nullable=False),
        sa.Column("source_checksum_hashes", sa.JSON(), nullable=False),
        sa.Column("canonical_fact_ids", sa.JSON(), nullable=False),
        sa.Column("recent_event_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_gap_ids", sa.JSON(), nullable=False),
        sa.Column("section_freshness_labels", sa.JSON(), nullable=False),
        sa.Column("evidence_state_labels", sa.JSON(), nullable=False),
    )
    op.create_table(
        "generated_output_cache_freshness_hash_inputs",
        sa.Column("cache_entry_id", sa.String(), primary_key=True),
        sa.Column("input_id", sa.String(), primary_key=True),
        sa.Column("output_identity", sa.String(), nullable=False),
        sa.Column("entry_kind", sa.String(), nullable=False),
        sa.Column("cache_scope", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("generated_output_freshness_hash", sa.String(), nullable=False),
        sa.Column("source_freshness_state", sa.String(), nullable=False),
        sa.Column("source_checksum_hashes", sa.JSON(), nullable=False),
        sa.Column("canonical_fact_ids", sa.JSON(), nullable=False),
        sa.Column("recent_event_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_gap_ids", sa.JSON(), nullable=False),
        sa.Column("section_freshness_labels", sa.JSON(), nullable=False),
        sa.Column("evidence_state_labels", sa.JSON(), nullable=False),
    )
    op.create_table(
        "generated_output_cache_validation_statuses",
        sa.Column("cache_entry_id", sa.String(), primary_key=True),
        sa.Column("validation_id", sa.String(), primary_key=True),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("citation_validation_status", sa.String(), nullable=False),
        sa.Column("safety_status", sa.String(), nullable=False),
        sa.Column("source_use_status", sa.String(), nullable=False),
        sa.Column("freshness_status", sa.String(), nullable=False),
        sa.Column("important_claim_count", sa.Integer(), nullable=False),
        sa.Column("cited_important_claim_count", sa.Integer(), nullable=False),
        sa.Column("unsupported_claim_count", sa.Integer(), nullable=False),
        sa.Column("wrong_asset_citation_count", sa.Integer(), nullable=False),
        sa.Column("wrong_pack_citation_count", sa.Integer(), nullable=False),
        sa.Column("rejected_source_count", sa.Integer(), nullable=False),
        sa.Column("permission_limited_source_count", sa.Integer(), nullable=False),
        sa.Column("advice_like_detected", sa.Boolean(), nullable=False),
        sa.Column("validated_at", sa.String(), nullable=True),
        sa.Column("rejection_reason_codes", sa.JSON(), nullable=False),
    )
    op.create_table(
        "generated_output_cache_diagnostics",
        sa.Column("diagnostic_id", sa.String(), primary_key=True),
        sa.Column("cache_entry_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("invalidation_reason", sa.String(), nullable=True),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("checksum_values", sa.JSON(), nullable=False),
        sa.Column("freshness_states", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("compact_metadata", sa.JSON(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.Column("stores_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_unrestricted_excerpt", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(GENERATED_OUTPUT_CACHE_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
