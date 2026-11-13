from app.engine.execution.executor import WorkflowExecutor

def test_requires_approval():
    result = WorkflowExecutor().execute({"steps": []})
    assert result["status"] == "awaiting_approval"
