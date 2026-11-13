from app.connectors.base.connector import Connector

class MockSpreadsheetConnector(Connector):
    def execute(self, config: dict, context: dict) -> dict:
        return {"status": "success", "message": "Mock spreadsheet action executed"}
