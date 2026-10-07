"""Add dormant knowledge-pack repository contract tables.

Revision ID: 20260425_0002
Revises: 20260425_0001
Create Date: 2026-04-25 04:09:50 UTC

The tables defined here are a persistence contract only. Current FastAPI,
retrieval, generation, chat, comparison, export, glossary, Weekly News Focus,
and frontend behavior remains fixture-backed and does not route through a live
database in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0002"
down_revision: str | None = "20260425_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KNOWLEDGE_PACK_TABLE_NAMES = (
    "asset_knowledge_pack_envelopes",
    "asset_knowledge_pack_source_documents",
    "asset_knowledge_pack_source_chunks",
    "asset_knowledge_pack_facts",
    "asset_knowledge_pack_recent_developments",
    "asset_knowledge_pack_evidence_gaps",
    "asset_knowledge_pack_section_freshness_inputs",
    "asset_knowledge_pack_source_checksums",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "asset_knowledge_pack_envelopes",
        sa.Column("pack_id", sa.String(), primary_key=True),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("asset", sa.JSON(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("build_state", sa.String(), nullable=False),
        sa.Column("support_status", sa.String(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("generated_output_available", sa.Boolean(), nullable=False),
        sa.Column("reusable_generated_output_cache_hit", sa.Boolean(), nullable=False),
        sa.Column("generated_route", sa.String(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("freshness", sa.JSON(), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("knowledge_pack_freshness_hash", sa.String(), nullable=True),
        sa.Column("cache_key", sa.String(), nullable=True),
        sa.Column("no_live_external_calls", sa.Boolean(), nullable=False),
        sa.Column("exports_full_source_documents", sa.Boolean(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
    )
    op.create_table(
        "asset_knowledge_pack_source_documents",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.String(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.String(), nullable=True),
        sa.Column("as_of_date", sa.String(), nullable=True),
        sa.Column("retrieved_at", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("source_quality", sa.String(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("permitted_operations", sa.JSON(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("fact_ids", sa.JSON(), nullable=False),
        sa.Column("recent_event_ids", sa.JSON(), nullable=False),
        sa.Column("chunk_ids", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("pack_id", "source_document_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )
    op.create_table(
        "asset_knowledge_pack_source_chunks",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("section_name", sa.String(), nullable=False),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("supported_claim_types", sa.JSON(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("text_storage_policy", sa.String(), nullable=False),
        sa.Column("stored_text", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("pack_id", "chunk_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )
    op.create_table(
        "asset_knowledge_pack_facts",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("fact_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("fact_type", sa.String(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("period", sa.String(), nullable=True),
        sa.Column("as_of_date", sa.String(), nullable=True),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("source_chunk_id", sa.String(), nullable=False),
        sa.Column("extraction_method", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("pack_id", "fact_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )
    op.create_table(
        "asset_knowledge_pack_recent_developments",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("event_date", sa.String(), nullable=True),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("source_chunk_id", sa.String(), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("pack_id", "event_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )
    op.create_table(
        "asset_knowledge_pack_evidence_gaps",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("gap_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=True),
        sa.Column("source_chunk_id", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("pack_id", "gap_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )
    op.create_table(
        "asset_knowledge_pack_section_freshness_inputs",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("section_id", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=True),
        sa.Column("as_of_date", sa.String(), nullable=True),
        sa.Column("retrieved_at", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("pack_id", "section_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )
    op.create_table(
        "asset_knowledge_pack_source_checksums",
        sa.Column("pack_id", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("pack_id", "source_document_id"),
        sa.ForeignKeyConstraint(["pack_id"], ["asset_knowledge_pack_envelopes.pack_id"]),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(KNOWLEDGE_PACK_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
