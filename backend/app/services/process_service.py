from sqlalchemy.orm import Session

from app.engine.analyzer.process_analyzer import ProcessAnalyzer
from app.engine.workflow.generator import WorkflowGenerator
from app.engine.workflow.validator import validate


class ProcessService:
    def __init__(self, db: Session):
        self.db = db
        self.analyzer = ProcessAnalyzer()
        self.workflow_generator = WorkflowGenerator()

    def analyze(self, description: str) -> dict:
        analysis = self.analyzer.analyze(description)
        workflow = self.workflow_generator.generate(description, analysis["signals"])
        validate(workflow)
        analysis["proposedWorkflow"] = workflow
        return analysis
