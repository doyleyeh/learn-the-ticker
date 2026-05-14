"""Add durable repository record contract table.

Revision ID: 20260513_0009
Revises: 20260425_0008
Create Date: 2026-05-13 18:45:00 UTC

The table defined here is a local durable repository-record adapter for
validated repository payloads. It does not add provider calls, public object
storage, browser-visible database settings, generated content, or source
approval by retrieval alone.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260513_0009"
down_revision: str | None = "20260425_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DURABLE_REPOSITORY_RECORD_TABLE_NAMES = ("durable_repository_records",)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "durable_repository_records",
        sa.Column("collection", sa.String(length=240), nullable=False),
        sa.Column("record_key", sa.String(length=240), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("model_type", sa.String(length=240), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_checksum", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("collection", "record_key"),
    )
    op.create_index(
        "ix_durable_repository_records_updated_at",
        "durable_repository_records",
        ["updated_at"],
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    op.drop_index("ix_durable_repository_records_updated_at", table_name="durable_repository_records")
    op.drop_table("durable_repository_records")


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
