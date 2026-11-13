from pydantic import BaseModel, Field


class ProcessAnalyzeRequest(BaseModel):
    description: str = Field(min_length=3, max_length=8000)
    analysis_strategy: str = Field(default="auto", pattern="^(auto|rules|llm)$")
    analysis_language: str = Field(default="de", pattern="^(de|en)$")
    # Open-ended on purpose: the AI engine must support domains that are not in a predefined list.
    business_domain: str = Field(default="general", min_length=1, max_length=80)
