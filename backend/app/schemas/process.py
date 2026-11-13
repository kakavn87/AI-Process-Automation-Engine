from typing import Literal

from pydantic import BaseModel, Field


class ProcessAnalyzeRequest(BaseModel):
    description: str = Field(min_length=3, max_length=8000)
    analysis_strategy: Literal["auto", "rules", "llm"] = "auto"
