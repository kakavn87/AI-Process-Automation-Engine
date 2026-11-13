from typing import Literal

from pydantic import BaseModel, Field


BusinessDomain = Literal[
    "general",
    "finance",
    "human_resources",
    "sales",
    "procurement",
    "customer_support",
    "logistics",
    "manufacturing",
    "it_operations",
    "marketing",
    "legal_compliance",
    "project_management",
    "operations",
]


class ProcessAnalyzeRequest(BaseModel):
    description: str = Field(min_length=3, max_length=8000)
    analysis_strategy: Literal["auto", "rules", "llm"] = "auto"
    analysis_language: Literal["de", "en"] = "de"
    business_domain: BusinessDomain = "general"
