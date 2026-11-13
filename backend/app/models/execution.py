from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.execution_step import ExecutionStep

from app.core.database import Base


class Execution(Base):
    __tablename__ = "executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
    )


class ApprovalExecution(Base):
    __tablename__ = "approval_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    workflow_name: Mapped[str] = mapped_column(String(200), nullable=False)
    workflow_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
