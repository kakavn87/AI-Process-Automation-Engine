from typing import Any

from pydantic import BaseModel, Field


class CreateExecutionRequest(BaseModel):
    workflow: dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    note: str = Field(default="", max_length=2000)
