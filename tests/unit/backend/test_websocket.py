import pytest
from fastapi.testclient import TestClient
from src.backend.api.main import app

def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        # We don't send anything yet, but we expect the connection to succeed
        # In a real test we could mock the manager and see if connect was called.
        pass
