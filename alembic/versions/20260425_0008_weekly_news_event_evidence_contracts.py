"""Add dormant Weekly News Focus event evidence contract tables.

Revision ID: 20260425_0008
Revises: 20260425_0007
Create Date: 2026-04-25 20:37:25 UTC

The tables defined here are inspectable contract metadata only. Current API,
frontend, retrieval, generation, chat, comparison, export, provider, cache,
database, and workflow behavior remains unchanged and does not route through
persisted Weekly News Focus evidence in this task.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0008"
down_revision: str | None = "20260425_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WEEKLY_NEWS_EVENT_EVIDENCE_TABLE_NAMES = (
    "weekly_news_market_week_windows",
    "weekly_news_event_candidates",
    "weekly_news_source_rank_inputs",
    "weekly_news_dedupe_groups",
    "weekly_news_selected_events",
    "weekly_news_evidence_states",
    "weekly_news_ai_thresholds",
    "weekly_news_validation_statuses",
    "weekly_news_diagnostics",
)


def upgrade() -> None:
    op, sa = _migration_modules()
    op.create_table(
        "weekly_news_market_week_windows",
        sa.Column("window_id", sa.String(), primary_key=True),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("previous_market_week_start", sa.String(), nullable=False),
        sa.Column("previous_market_week_end", sa.String(), nullable=False),
        sa.Column("current_week_to_date_start", sa.String(), nullable=True),
        sa.Column("current_week_to_date_end", sa.String(), nullable=True),
        sa.Column("news_window_start", sa.String(), nullable=False),
        sa.Column("news_window_end", sa.String(), nullable=False),
        sa.Column("includes_current_week_to_date", sa.Boolean(), nullable=False),
        sa.Column("configured_max_item_count", sa.Integer(), nullable=False),
        sa.Column("minimum_ai_analysis_item_count", sa.Integer(), nullable=False),
        sa.Column("no_live_external_calls", sa.Boolean(), nullable=False),
        sa.Column("live_database_execution", sa.Boolean(), nullable=False),
        sa.Column("provider_or_llm_call_required", sa.Boolean(), nullable=False),
        sa.Column("generated_output_changed", sa.Boolean(), nullable=False),
        sa.Column("stable_facts_are_separate", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "weekly_news_event_candidates",
        sa.Column("candidate_event_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("source_asset_ticker", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_date", sa.String(), nullable=True),
        sa.Column("published_at", sa.String(), nullable=True),
        sa.Column("retrieved_at", sa.String(), nullable=False),
        sa.Column("period_bucket", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("source_chunk_id", sa.String(), nullable=True),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("citation_asset_tickers", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=False),
        sa.Column("source_rank_tier", sa.String(), nullable=False),
        sa.Column("source_quality", sa.String(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("importance_score", sa.Integer(), nullable=False),
        sa.Column("high_signal", sa.Boolean(), nullable=False),
        sa.Column("important_event_claim", sa.Boolean(), nullable=False),
        sa.Column("license_allowed", sa.Boolean(), nullable=False),
        sa.Column("recognized_source", sa.Boolean(), nullable=False),
        sa.Column("promotional", sa.Boolean(), nullable=False),
        sa.Column("irrelevant", sa.Boolean(), nullable=False),
        sa.Column("duplicate_group_id", sa.String(), nullable=True),
        sa.Column("duplicate_of_event_id", sa.String(), nullable=True),
        sa.Column("candidate_decision", sa.String(), nullable=False),
        sa.Column("suppression_reason_codes", sa.JSON(), nullable=False),
        sa.Column("title_checksum", sa.String(), nullable=True),
        sa.Column("evidence_checksum", sa.String(), nullable=True),
        sa.Column("stores_raw_article_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_unrestricted_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
    )
    op.create_table(
        "weekly_news_source_rank_inputs",
        sa.Column("candidate_event_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("source_rank_tier", sa.String(), nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=False),
        sa.Column("source_quality_weight", sa.Integer(), nullable=False),
        sa.Column("event_type_weight", sa.Integer(), nullable=False),
        sa.Column("recency_weight", sa.Integer(), nullable=False),
        sa.Column("asset_relevance_weight", sa.Integer(), nullable=False),
        sa.Column("duplicate_penalty", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("minimum_display_score", sa.Integer(), nullable=False),
        sa.Column("selected_by_score", sa.Boolean(), nullable=False),
        sa.Column("source_policy_allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
        sa.ForeignKeyConstraint(["candidate_event_id"], ["weekly_news_event_candidates.candidate_event_id"]),
    )
    op.create_table(
        "weekly_news_dedupe_groups",
        sa.Column("dedupe_group_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("canonical_event_key", sa.String(), nullable=False),
        sa.Column("retained_candidate_event_id", sa.String(), nullable=True),
        sa.Column("duplicate_candidate_event_ids", sa.JSON(), nullable=False),
        sa.Column("dedupe_status", sa.String(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
    )
    op.create_table(
        "weekly_news_selected_events",
        sa.Column("selected_event_id", sa.String(), primary_key=True),
        sa.Column("candidate_event_id", sa.String(), nullable=False),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("period_bucket", sa.String(), nullable=False),
        sa.Column("event_date", sa.String(), nullable=True),
        sa.Column("published_at", sa.String(), nullable=True),
        sa.Column("retrieved_at", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("source_chunk_id", sa.String(), nullable=True),
        sa.Column("citation_ids", sa.JSON(), nullable=False),
        sa.Column("citation_asset_tickers", sa.JSON(), nullable=False),
        sa.Column("source_quality", sa.String(), nullable=False),
        sa.Column("allowlist_status", sa.String(), nullable=False),
        sa.Column("source_use_policy", sa.String(), nullable=False),
        sa.Column("freshness_state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("importance_score", sa.Integer(), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("configured_max_item_count", sa.Integer(), nullable=False),
        sa.Column("selected_item_count", sa.Integer(), nullable=False),
        sa.Column("suppressed_candidate_count", sa.Integer(), nullable=False),
        sa.Column("dedupe_group_id", sa.String(), nullable=True),
        sa.Column("canonical_event_key", sa.String(), nullable=False),
        sa.Column("suppression_reason_codes", sa.JSON(), nullable=False),
        sa.Column("generated_output_state", sa.String(), nullable=False),
        sa.Column("no_generated_analysis_change", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
        sa.ForeignKeyConstraint(["candidate_event_id"], ["weekly_news_event_candidates.candidate_event_id"]),
    )
    op.create_table(
        "weekly_news_evidence_states",
        sa.Column("evidence_state_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("evidence_state", sa.String(), nullable=False),
        sa.Column("evidence_limited_state", sa.String(), nullable=False),
        sa.Column("configured_max_item_count", sa.Integer(), nullable=False),
        sa.Column("selected_item_count", sa.Integer(), nullable=False),
        sa.Column("suppressed_candidate_count", sa.Integer(), nullable=False),
        sa.Column("empty_state_valid", sa.Boolean(), nullable=False),
        sa.Column("limited_state_valid", sa.Boolean(), nullable=False),
        sa.Column("missing_evidence_label", sa.String(), nullable=True),
        sa.Column("stable_facts_are_separate", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
    )
    op.create_table(
        "weekly_news_ai_thresholds",
        sa.Column("threshold_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("asset_ticker", sa.String(), nullable=False),
        sa.Column("minimum_weekly_news_item_count", sa.Integer(), nullable=False),
        sa.Column("selected_item_count", sa.Integer(), nullable=False),
        sa.Column("high_signal_selected_item_count", sa.Integer(), nullable=False),
        sa.Column("analysis_allowed", sa.Boolean(), nullable=False),
        sa.Column("analysis_state", sa.String(), nullable=False),
        sa.Column("suppression_reason_code", sa.String(), nullable=True),
        sa.Column("selected_event_ids", sa.JSON(), nullable=False),
        sa.Column("canonical_fact_citation_ids", sa.JSON(), nullable=False),
        sa.Column("generated_analysis_state", sa.String(), nullable=False),
        sa.Column("no_generated_analysis_change", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
    )
    op.create_table(
        "weekly_news_validation_statuses",
        sa.Column("validation_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("citation_validation_status", sa.String(), nullable=False),
        sa.Column("source_use_status", sa.String(), nullable=False),
        sa.Column("freshness_status", sa.String(), nullable=False),
        sa.Column("generated_output_status", sa.String(), nullable=False),
        sa.Column("rejection_reason_codes", sa.JSON(), nullable=False),
        sa.Column("validated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
    )
    op.create_table(
        "weekly_news_diagnostics",
        sa.Column("diagnostic_id", sa.String(), primary_key=True),
        sa.Column("window_id", sa.String(), nullable=False),
        sa.Column("candidate_event_id", sa.String(), nullable=True),
        sa.Column("selected_event_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("compact_metadata", sa.JSON(), nullable=False),
        sa.Column("freshness_labels", sa.JSON(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column("event_ids", sa.JSON(), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("rank_inputs", sa.JSON(), nullable=False),
        sa.Column("suppression_reason_codes", sa.JSON(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("stores_raw_article_text", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_provider_payload", sa.Boolean(), nullable=False),
        sa.Column("stores_unrestricted_source_text", sa.Boolean(), nullable=False),
        sa.Column("stores_hidden_prompt", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_model_reasoning", sa.Boolean(), nullable=False),
        sa.Column("stores_raw_user_text", sa.Boolean(), nullable=False),
        sa.Column("stores_secret", sa.Boolean(), nullable=False),
        sa.Column("stores_public_or_signed_url", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["weekly_news_market_week_windows.window_id"]),
    )


def downgrade() -> None:
    op, _sa = _migration_modules()
    for table_name in reversed(WEEKLY_NEWS_EVENT_EVIDENCE_TABLE_NAMES):
        op.drop_table(table_name)


def _migration_modules():
    try:
        from alembic import op
        import sqlalchemy as sa
    except ModuleNotFoundError as exc:  # pragma: no cover - import inspection path.
        raise RuntimeError("Alembic and SQLAlchemy are required to run this migration.") from exc
    return op, sa
