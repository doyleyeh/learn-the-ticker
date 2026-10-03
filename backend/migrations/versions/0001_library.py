"""Initial local library, durable jobs and redacted runtime events."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("records", sa.Column("id", sa.String(200), primary_key=True), sa.Column("kind", sa.String(40), nullable=False), sa.Column("parent_id", sa.String(200)), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_records_kind", "records", ["kind"])
    op.create_index("ix_records_parent_id", "records", ["parent_id"])
    op.create_table("research_jobs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("status", sa.String(40), nullable=False), sa.Column("request", sa.JSON(), nullable=False), sa.Column("result", sa.JSON()), sa.Column("error", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"])
    op.create_table("runtime_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(36), sa.ForeignKey("research_jobs.id"), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_runtime_events_job_id", "runtime_events", ["job_id"])


def downgrade():
    raise RuntimeError("Restore a verified backup into a separate cluster; destructive in-place downgrades are disabled")
