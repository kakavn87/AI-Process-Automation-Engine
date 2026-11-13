from abc import ABC, abstractmethod

class Connector(ABC):
    @abstractmethod
    def execute(self, config: dict, context: dict) -> dict:
        raise NotImplementedError
