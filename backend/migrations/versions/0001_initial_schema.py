"""Frozen initial application schema.

This revision describes only the tables that existed before tenant support.
It deliberately does not read the live ORM metadata so future model additions
are always applied by their own migrations rather than silently appearing in
the historical baseline.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

metadata = sa.MetaData()

processes = sa.Table(
    "processes",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String(200), nullable=False),
    sa.Column("description", sa.Text, nullable=False),
)

workflows = sa.Table(
    "workflows",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String(200), nullable=False),
    sa.Column("definition", sa.Text, nullable=False),
)

executions = sa.Table(
    "executions",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("status", sa.String(50), nullable=False),
)

execution_steps = sa.Table(
    "execution_steps",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("execution_id", sa.Integer, sa.ForeignKey("executions.id", ondelete="CASCADE"), nullable=False),
    sa.Column("step_key", sa.String(80), nullable=False),
    sa.Column("step_type", sa.String(50), nullable=False),
    sa.Column("name", sa.String(200), nullable=False),
    sa.Column("description", sa.Text, nullable=False),
    sa.Column("status", sa.String(50), nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("config", sa.JSON, nullable=False),
)
sa.Index("ix_execution_steps_execution_id", execution_steps.c.execution_id)

approval_executions = sa.Table(
    "approval_executions",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("workflow_name", sa.String(200), nullable=False),
    sa.Column("workflow_definition", sa.JSON, nullable=False),
    sa.Column("status", sa.String(50), nullable=False),
    sa.Column("events", sa.JSON, nullable=False),
    sa.Column("decision_note", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)
sa.Index("ix_approval_executions_status", approval_executions.c.status)

workflow_sessions = sa.Table(
    "workflow_sessions",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("description", sa.Text, nullable=False),
    sa.Column("analysis_strategy", sa.String(12), nullable=False),
    sa.Column("language", sa.String(2), nullable=False),
    sa.Column("business_domain", sa.String(80), nullable=False),
    sa.Column("analysis", sa.JSON, nullable=False),
    sa.Column("questions", sa.JSON, nullable=False),
    sa.Column("answers", sa.JSON, nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("events", sa.JSON, nullable=False),
    sa.Column("related_execution_id", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)
sa.Index("ix_workflow_sessions_status", workflow_sessions.c.status)
sa.Index("ix_workflow_sessions_related_execution_id", workflow_sessions.c.related_execution_id)

ai_usage_events = sa.Table(
    "ai_usage_events",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("session_id", sa.String(36), sa.ForeignKey("workflow_sessions.id", ondelete="SET NULL"), nullable=True),
    sa.Column("provider", sa.String(40), nullable=False),
    sa.Column("model", sa.String(120), nullable=False),
    sa.Column("task", sa.String(80), nullable=False),
    sa.Column("status", sa.String(30), nullable=False),
    sa.Column("input_tokens", sa.Integer, nullable=True),
    sa.Column("output_tokens", sa.Integer, nullable=True),
    sa.Column("total_tokens", sa.Integer, nullable=True),
    sa.Column("estimated_cost_usd", sa.Float, nullable=True),
    sa.Column("duration_ms", sa.Integer, nullable=True),
    sa.Column("error_type", sa.String(120), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)
sa.Index("ix_ai_usage_events_session_id", ai_usage_events.c.session_id)
sa.Index("ix_ai_usage_events_status", ai_usage_events.c.status)


def upgrade() -> None:
    bind = op.get_bind()
    for table in metadata.sorted_tables:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(metadata.sorted_tables):
        table.drop(bind=bind, checkfirst=True)
