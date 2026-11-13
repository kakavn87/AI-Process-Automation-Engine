"""Create the current application schema.

This baseline is intentionally check-first: the public demo historically created
its tables with SQLAlchemy metadata during application startup. Existing SQLite
installations therefore keep their data, while a fresh PostgreSQL database gets
all currently mapped tables. Follow-up schema changes must use explicit Alembic
operations in new revisions.
"""

from typing import Sequence, Union

from alembic import op

from app.core.database import Base
# Import all mapped models before using Base.metadata.
from app.models.execution import ApprovalExecution, Execution  # noqa: F401
from app.models.execution_step import ExecutionStep  # noqa: F401
from app.models.process import Process  # noqa: F401
from app.models.workflow import Workflow  # noqa: F401
from app.models.workflow_session import AIUsageEvent, WorkflowSession  # noqa: F401

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Downgrading this baseline removes application tables and their data.
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
