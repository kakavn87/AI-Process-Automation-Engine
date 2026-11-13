from pydantic import BaseModel, Field

class ProcessAnalyzeRequest(BaseModel):
    description: str = Field(min_length=3)
