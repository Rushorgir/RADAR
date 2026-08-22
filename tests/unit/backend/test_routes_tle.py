from datetime import datetime

from src.backend.db import crud


def test_get_tle_catalog(client, db_session):
    # Seed data
    tle_data = {
        "object_id": "111",
        "line1": "1...",
        "line2": "2...",
        "epoch": datetime.utcnow()
    }
    crud.create_tle(db_session, tle_data)
    
    response = client.get("/api/tle/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 1
    assert data["items"][0]["object_id"] == "111"

def test_get_tle_for_object(client, db_session):
    tle_data = {
        "object_id": "222",
        "line1": "1...",
        "line2": "2...",
        "epoch": datetime.utcnow()
    }
    crud.create_tle(db_session, tle_data)
    
    response = client.get("/api/tle/222")
    assert response.status_code == 200
    assert response.json()["object_id"] == "222"

def test_get_tle_not_found(client):
    response = client.get("/api/tle/999")
    assert response.status_code == 404
