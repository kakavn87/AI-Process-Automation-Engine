from typing import Any

from pydantic import BaseModel, Field


class CreateExecutionRequest(BaseModel):
    workflow: dict[str, Any]


class ExecutionDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class LiveExecutionRequest(BaseModel):
    confirm_live_execution: bool = False
