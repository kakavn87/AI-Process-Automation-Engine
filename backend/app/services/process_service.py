from sqlalchemy.orm import Session
from app.engine.analyzer.process_analyzer import ProcessAnalyzer

class ProcessService:
    def __init__(self, db: Session):
        self.db = db
        self.analyzer = ProcessAnalyzer()

    def analyze(self, description: str) -> dict:
        return self.analyzer.analyze(description)
