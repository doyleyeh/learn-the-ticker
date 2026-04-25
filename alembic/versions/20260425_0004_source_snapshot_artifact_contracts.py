"""Add dormant source snapshot artifact contract tables.

Revision ID: 20260425_0004
Revises: 20260425_0003
Create Date: 2026-04-25 05:35:55 UTC

The tables defined here are an inspectable metadata contract only. Current API,
retrieval, generation, chat, comparison, export, glossary, provider, worker,
object-storage, and frontend behavior remains unchanged and does not route
through source snapshots in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0004"
down_revision: str | None = "20260425_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_SNAPSHOT_TABLE_NAMES = (
    "source_snapshot_artifacts",
    "source_snapshot_diagnostics",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "source_snapshot_artifacts",
        sa.Column("artifact_id", sa.String(), primary_key=True),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("scope_kind", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=True),
        sa.Column("comparison_id", sa.String(), nullable=True),
        sa.Column("comparison_left_ticker", sa.String(), nullable=True),
        sa.Column("comparison_right_ticker", sa.String(), nullable=True),
        sa.Column("ingestion_job_id", sa.String(), nullable=True),
        sa.Column("source_document_id", sa.String(), nullable=True),
        sa.Column("source_reference_id", sa.String(), nullable=True),
        sa.Column("source_asset_ticker", sa.String(), nullable=True),
        sa.Column("source_comparison_id", sa.String(), nullable=True),
        sa.Column("artifact_category", sa.String(), nullable=False),
        sa.Column("private_object_uri", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("retrieved_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("source_quality", sa.String(), nullable=False),
        sa.Column("permitted_operations", sa.JSON(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("support_status", sa.String(), nullable=False),
        sa.Column("approval_state", sa.String(), nullable=False),
        sa.Column("validation_state", sa.String(), nullable=False),
        sa.Column("source_policy_state", sa.String(), nullable=False),
        sa.Column("can_feed_generated_output", sa.Boolean(), nullable=False),
        sa.Column("can_support_citations", sa.Boolean(), nullable=False),
        sa.Column("cache_allowed", sa.Boolean(), nullable=False),
        sa.Column("export_allowed", sa.Boolean(), nullable=False),
        sa.Column("generated_output_available", sa.Boolean(), nullable=False),
        sa.Column("no_public_snapshot_access", sa.Boolean(), nullable=False),
        sa.Column("signed_url_created", sa.Boolean(), nullable=False),
        sa.Column("browser_readable_storage_path", sa.Boolean(), nullable=False),
        sa.Column("external_fetch_url_as_storage", sa.Boolean(), nullable=False),
        sa.Column("raw_text_stored_in_contract", sa.Boolean(), nullable=False),
        sa.Column("raw_provider_payload_stored", sa.Boolean(), nullable=False),
        sa.Column("raw_article_text_stored", sa.Boolean(), nullable=False),
        sa.Column("raw_user_text_stored", sa.Boolean(), nullable=False),
        sa.Column("unrestricted_source_excerpt_stored", sa.Boolean(), nullable=False),
        sa.Column("hidden_prompt_stored", sa.Boolean(), nullable=False),
        sa.Column("raw_model_reasoning_stored", sa.Boolean(), nullable=False),
        sa.Column("secrets_stored", sa.Boolean(), nullable=False),
        sa.Column("compact_diagnostics", sa.JSON(), nullable=False),
    )
    op.create_table(
        "source_snapshot_diagnostics",
        sa.Column("diagnostic_id", sa.String(), primary_key=True),
        sa.Column("artifact_id", sa.String(), nullable=True),
        sa.Column("ingestion_job_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("retrieval_status", sa.String(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("source_policy_ref", sa.String(), nullable=True),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("compact_metadata", sa.JSON(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.Column("stores_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_unrestricted_excerpt", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_snapshot_artifacts.artifact_id"]),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(SOURCE_SNAPSHOT_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
