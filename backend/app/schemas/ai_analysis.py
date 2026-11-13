from typing import Literal

from pydantic import BaseModel, Field


class LLMOpportunity(BaseModel):
    title: str
    description: str
    impact: Literal["high", "medium", "low"]


class LLMIntegration(BaseModel):
    name: str
    purpose: str
    status: Literal["planned_not_connected"]


class LLMWorkflowStep(BaseModel):
    type: Literal["trigger", "collect", "extract", "transform", "validate", "generate", "approval", "notify"]
    name: str
    description: str
    connector: str
    requires_approval: bool


class LLMProcessAnalysis(BaseModel):
    automation_score: int = Field(description="Estimated automation potential from 0 to 100.")
    signals: list[str]
    summary: str
    current_process: list[str]
    automation_opportunities: list[LLMOpportunity]
    integrations: list[LLMIntegration]
    approval_required: bool
    approval_reason: str
    approval_gate_before: str
    risks: list[str]
    assumptions: list[str]
    questions: list[str]
    workflow_name: str
    workflow_trigger: str
    workflow_steps: list[LLMWorkflowStep]
