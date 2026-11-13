"""Add tenants, users, memberships and tenant-owned data.

Existing demo records are placed into a dedicated default workspace. Tenant
columns stay nullable for compatibility with direct service tests and older
internal integrations, but authenticated API requests always write a tenant.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0002_tenant_identity"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _create_table_if_missing(bind, name: str, *columns, **kwargs) -> None:
    if not sa.inspect(bind).has_table(name):
        op.create_table(name, *columns, **kwargs)


def upgrade() -> None:
    bind = op.get_bind()

    _create_table_if_missing(
        bind,
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_table_if_missing(
        bind,
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(160), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_table_if_missing(
        bind,
        "tenant_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),
    )
    _create_table_if_missing(
        bind,
        "tenant_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    existing_tables = set(sa.inspect(bind).get_table_names())
    for table_name in ("workflow_sessions", "approval_executions", "ai_usage_events"):
        if table_name in existing_tables and not _has_column(bind, table_name, "tenant_id"):
            # SQLite cannot ALTER a table to add a foreign-key constraint.
            # Alembic's batch mode uses a safe copy-and-move table rebuild on
            # SQLite and a normal ALTER TABLE on PostgreSQL.
            with op.batch_alter_table(
                table_name,
                recreate="always" if bind.dialect.name == "sqlite" else "auto",
                naming_convention={
                    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                },
            ) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "tenant_id",
                        sa.String(36),
                        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                        nullable=True,
                    )
                )

    # Refresh after creating the identity tables so their indexes are included.
    existing_tables = set(sa.inspect(bind).get_table_names())

    indexes = (
        ("ix_tenants_slug", "tenants", ["slug"], True),
        ("ix_users_email", "users", ["email"], True),
        ("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"], False),
        ("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"], False),
        ("ix_tenant_invitations_tenant_id", "tenant_invitations", ["tenant_id"], False),
        ("ix_tenant_invitations_email", "tenant_invitations", ["email"], False),
        ("ix_tenant_invitations_token_hash", "tenant_invitations", ["token_hash"], True),
        ("ix_workflow_sessions_tenant_id", "workflow_sessions", ["tenant_id"], False),
        ("ix_approval_executions_tenant_id", "approval_executions", ["tenant_id"], False),
        ("ix_ai_usage_events_tenant_id", "ai_usage_events", ["tenant_id"], False),
    )
    current_indexes = {
        (table_name, index["name"])
        for table_name in sa.inspect(bind).get_table_names()
        for index in sa.inspect(bind).get_indexes(table_name)
    }
    for name, table_name, columns, unique in indexes:
        if table_name in existing_tables and (table_name, name) not in current_indexes:
            op.create_index(name, table_name, columns, unique=unique)

    tenants = sa.table(
        "tenants",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    if bind.execute(sa.select(tenants.c.id).where(tenants.c.id == DEFAULT_TENANT_ID)).first() is None:
        bind.execute(sa.insert(tenants).values(
            id=DEFAULT_TENANT_ID,
            name="FlowPilot Demo",
            slug="flowpilot-demo",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        ))

    for table_name in ("workflow_sessions", "approval_executions", "ai_usage_events"):
        if table_name in existing_tables and _has_column(bind, table_name, "tenant_id"):
            bind.execute(
                sa.text(f'UPDATE "{table_name}" SET tenant_id = :tenant_id WHERE tenant_id IS NULL'),
                {"tenant_id": DEFAULT_TENANT_ID},
            )


def downgrade() -> None:
    raise RuntimeError(
        "Tenant migration downgrade is intentionally blocked: removing tenant columns or tables "
        "could orphan customer data. Restore from a backup or write a reviewed forward migration."
    )
