from app.connectors.mock.email import MockEmailConnector

def test_mock_email():
    assert MockEmailConnector().execute({}, {})["status"] == "success"
