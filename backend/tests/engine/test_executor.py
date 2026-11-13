import pytest

from app.engine.execution.executor import WorkflowExecutor
from app.engine.workflow.validator import validate


def sample_workflow():
    return {
        "name": "Approval demo",
        "steps": [
            {"id": "s1", "type": "trigger", "name": "Start", "config": {}},
            {"id": "s2", "type": "approval", "name": "Manager approval", "config": {}},
            {"id": "s3", "type": "notify", "name": "Send Teams update", "config": {"requiresApproval": True}},
        ],
    }


def test_requires_approval_before_execution():
    result = WorkflowExecutor().execute(sample_workflow())
    assert result["status"] == "awaiting_approval"


def test_approved_workflow_runs_in_simulation_mode():
    result = WorkflowExecutor().execute(sample_workflow(), approved=True)
    assert result["status"] == "completed"
    assert result["executionMode"] == "simulation"
    assert result["events"][-1]["status"] == "simulated"
    assert "no email, Teams message" in result["events"][-1]["message"]


def test_outbound_step_without_approval_is_rejected():
    workflow = {
        "steps": [
            {"id": "s1", "type": "trigger", "config": {}},
            {"id": "s2", "type": "notify", "config": {"requiresApproval": True}},
        ]
    }
    with pytest.raises(ValueError, match="approval step must come before"):
        validate(workflow)
