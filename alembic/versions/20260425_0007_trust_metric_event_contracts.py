"""Add dormant trust-metric event contract tables.

Revision ID: 20260425_0007
Revises: 20260425_0006
Create Date: 2026-04-25 20:01:27 UTC

The tables defined here are an inspectable metadata contract only. Current API,
frontend, retrieval, generation, chat, comparison, export, provider, cache,
database, analytics, and workflow behavior remains unchanged and does not route
through durable trust-metric persistence in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0007"
down_revision: str | None = "20260425_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRUST_METRIC_EVENT_TABLE_NAMES = (
    "trust_metric_event_envelopes",
    "trust_metric_validation_statuses",
    "trust_metric_aggregate_counters",
    "trust_metric_latency_summaries",
    "trust_metric_state_snapshots",
    "trust_metric_diagnostics",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "trust_metric_event_envelopes",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("event_schema_version", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("workflow_area", sa.String(), nullable=False),
        sa.Column("metric_kind", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.String(), nullable=False),
        sa.Column("client_event_id", sa.String(), nullable=True),
        sa.Column("asset_ticker", sa.String(), nullable=True),
        sa.Column("asset_support_state", sa.String(), nullable=True),
        sa.Column("comparison_left_ticker", sa.String(), nullable=True),
        sa.Column("comparison_right_ticker", sa.String(), nullable=True),
        sa.Column("generated_output_available", sa.Boolean(), nullable=False),
        sa.Column("output_kind", sa.String(), nullable=True),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("source_document_count", sa.Integer(), nullable=False),
        sa.Column("unsupported_claim_count", sa.Integer(), nullable=False),
        sa.Column("weak_citation_count", sa.Integer(), nullable=False),
        sa.Column("stale_source_count", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("citation_coverage_rate", sa.Float(), nullable=True),
        sa.Column("freshness_state", sa.String(), nullable=True),
        sa.Column("evidence_state", sa.String(), nullable=True),
        sa.Column("safety_status", sa.String(), nullable=True),
        sa.Column("sanitized_metadata", sa.JSON(), nullable=False),
        sa.Column("validation_only", sa.Boolean(), nullable=False),
        sa.Column("persistence_enabled", sa.Boolean(), nullable=False),
        sa.Column("external_analytics_enabled", sa.Boolean(), nullable=False),
        sa.Column("analytics_emitted", sa.Boolean(), nullable=False),
        sa.Column("no_live_external_calls", sa.Boolean(), nullable=False),
        sa.Column("live_database_execution", sa.Boolean(), nullable=False),
        sa.Column("provider_or_llm_call_required", sa.Boolean(), nullable=False),
        sa.Column("user_identity_stored", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_answer_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_query_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_source_url", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "trust_metric_validation_statuses",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("schema_valid", sa.Boolean(), nullable=False),
        sa.Column("catalog_valid", sa.Boolean(), nullable=False),
        sa.Column("citation_validation_status", sa.String(), nullable=False),
        sa.Column("source_use_status", sa.String(), nullable=False),
        sa.Column("freshness_status", sa.String(), nullable=False),
        sa.Column("safety_status", sa.String(), nullable=False),
        sa.Column("generated_output_state", sa.String(), nullable=False),
        sa.Column("rejection_reason_codes", sa.JSON(), nullable=False),
        sa.Column("validated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["trust_metric_event_envelopes.event_id"]),
    )
    op.create_table(
        "trust_metric_aggregate_counters",
        sa.Column("aggregate_id", sa.String(), primary_key=True),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("aggregate_kind", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("workflow_area", sa.String(), nullable=True),
        sa.Column("metric_kind", sa.String(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("numerator", sa.Integer(), nullable=True),
        sa.Column("denominator", sa.Integer(), nullable=True),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("stores_raw_event_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "trust_metric_latency_summaries",
        sa.Column("summary_id", sa.String(), primary_key=True),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("latency_scope", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("workflow_area", sa.String(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("min_ms", sa.Integer(), nullable=True),
        sa.Column("max_ms", sa.Integer(), nullable=True),
        sa.Column("average_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("stores_raw_event_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "trust_metric_state_snapshots",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("asset_support_state", sa.String(), nullable=True),
        sa.Column("generated_output_available", sa.Boolean(), nullable=False),
        sa.Column("output_kind", sa.String(), nullable=True),
        sa.Column("freshness_state", sa.String(), nullable=True),
        sa.Column("evidence_state", sa.String(), nullable=True),
        sa.Column("safety_status", sa.String(), nullable=True),
        sa.Column("citation_coverage_status", sa.String(), nullable=False),
        sa.Column("source_use_status", sa.String(), nullable=False),
        sa.Column("state_consistency_status", sa.String(), nullable=False),
        sa.Column("blocked_reason_codes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["trust_metric_event_envelopes.event_id"]),
    )
    op.create_table(
        "trust_metric_diagnostics",
        sa.Column("diagnostic_id", sa.String(), primary_key=True),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("workflow_area", sa.String(), nullable=True),
        sa.Column("freshness_states", sa.JSON(), nullable=False),
        sa.Column("compact_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.Column("stores_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_answer_text", sa.Boolean(), nullable=False),
        sa.Column("stores_query_text", sa.Boolean(), nullable=False),
        sa.Column("stores_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_source_url", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["trust_metric_event_envelopes.event_id"]),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(TRUST_METRIC_EVENT_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
