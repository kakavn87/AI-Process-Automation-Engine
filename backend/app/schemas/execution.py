from pydantic import BaseModel

class ExecuteWorkflowRequest(BaseModel):
    approved: bool = False
