from app.connectors.base.connector import Connector

class MockEmailConnector(Connector):
    def execute(self, config: dict, context: dict) -> dict:
        return {"status": "success", "message": "Mock email action executed"}
