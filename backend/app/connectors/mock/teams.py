from app.connectors.base.connector import Connector

class MockTeamsConnector(Connector):
    def execute(self, config: dict, context: dict) -> dict:
        return {"status": "success", "message": "Mock Teams action executed"}
