from pydantic import BaseModel

class WorkflowStep(BaseModel):
    type: str
    name: str
    config: dict = {}

class WorkflowDefinition(BaseModel):
    name: str
    steps: list[WorkflowStep]
