from typing import Any

from pydantic import BaseModel, Field


class SubmitWorkflowAnswersRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict, max_length=30)
