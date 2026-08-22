from fastapi.testclient import TestClient
from src.backend.api.main import app

client = TestClient(app)

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_tle_route(client):
    response = client.get("/api/tle/")
    assert response.status_code == 200
