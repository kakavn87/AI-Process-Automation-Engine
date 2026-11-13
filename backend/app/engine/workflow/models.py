from dataclasses import dataclass

@dataclass
class WorkflowStep:
    type: str
    name: str
    config: dict
