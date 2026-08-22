from fastapi.testclient import TestClient

from src.backend.api.main import app


def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("ping")
        # Connection succeeded and handled text message without exception
