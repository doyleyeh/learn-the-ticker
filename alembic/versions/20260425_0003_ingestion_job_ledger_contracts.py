"""Add dormant ingestion job ledger contract tables.

Revision ID: 20260425_0003
Revises: 20260425_0002
Create Date: 2026-04-25 05:05:56 UTC

The tables defined here are a persistence contract only. Current FastAPI,
retrieval, generation, chat, comparison, export, glossary, frontend, provider,
worker, and fixture behavior remains unchanged and does not route through a
live database in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0003"
down_revision: str | None = "20260425_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INGESTION_JOB_LEDGER_TABLE_NAMES = (
    "ingestion_job_ledger_records",
    "ingestion_job_ledger_source_refs",
    "ingestion_job_ledger_diagnostics",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "ingestion_job_ledger_records",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("job_category", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("job_state", sa.String(), nullable=False),
        sa.Column("worker_status", sa.String(), nullable=True),
        sa.Column("scope_decision", sa.String(), nullable=False),
        sa.Column("support_status", sa.String(), nullable=False),
        sa.Column("approval_basis", sa.String(), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("generated_route", sa.String(), nullable=True),
        sa.Column("generated_output_available", sa.Boolean(), nullable=False),
        sa.Column("can_open_generated_page", sa.Boolean(), nullable=False),
        sa.Column("can_answer_chat", sa.Boolean(), nullable=False),
        sa.Column("can_compare", sa.Boolean(), nullable=False),
        sa.Column("can_request_ingestion", sa.Boolean(), nullable=False),
        sa.Column("status_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
        sa.Column("started_at", sa.String(), nullable=True),
        sa.Column("finished_at", sa.String(), nullable=True),
        sa.Column("batch_id", sa.String(), nullable=True),
        sa.Column("launch_group", sa.String(), nullable=True),
        sa.Column("compact_metadata", sa.JSON(), nullable=False),
        sa.Column("no_live_external_calls", sa.Boolean(), nullable=False),
        sa.Column("raw_provider_payload_stored", sa.Boolean(), nullable=False),
        sa.Column("raw_article_text_stored", sa.Boolean(), nullable=False),
        sa.Column("raw_user_text_stored", sa.Boolean(), nullable=False),
        sa.Column("unrestricted_source_text_stored", sa.Boolean(), nullable=False),
        sa.Column("secrets_stored", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "ingestion_job_ledger_source_refs",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("source_ref_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("source_policy_ref", sa.String(), nullable=True),
        sa.Column("retrieved_at", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("stores_raw_text", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("job_id", "source_ref_id"),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_job_ledger_records.job_id"]),
    )
    op.create_table(
        "ingestion_job_ledger_diagnostics",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("diagnostic_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("sanitized_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.String(), nullable=True),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.Column("stores_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("job_id", "diagnostic_id"),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_job_ledger_records.job_id"]),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(INGESTION_JOB_LEDGER_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
