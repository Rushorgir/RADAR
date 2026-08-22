from datetime import datetime

from src.backend.db import crud


def test_get_conjunction_events(client, db_session):
    event_data = {
        "event_id": "event-1",
        "primary_id": "1",
        "secondary_id": "2",
        "tca": datetime.utcnow(),
        "miss_distance_km": 1.0,
        "relative_velocity_km_s": 7.0,
        "pc": 1e-4,
        "pc_method": "FOSTER_2D",
        "risk_category": "HIGH"
    }
    crud.create_conjunction_event(db_session, event_data)
    
    response = client.get("/api/conjunctions/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["event_id"] == "event-1"
    
    # Test filtering
    response_high = client.get("/api/conjunctions/?risk_category=HIGH")
    assert response_high.json()["total"] == 1
    
    response_low = client.get("/api/conjunctions/?risk_category=LOW")
    assert response_low.json()["total"] == 0

def test_get_conjunction_event_by_id(client, db_session):
    event_data = {
        "event_id": "event-2",
        "primary_id": "1",
        "secondary_id": "2",
        "tca": datetime.utcnow(),
        "miss_distance_km": 1.0,
        "relative_velocity_km_s": 7.0,
        "pc": 1e-4,
        "pc_method": "FOSTER_2D",
    }
    crud.create_conjunction_event(db_session, event_data)
    
    response = client.get("/api/conjunctions/event-2")
    assert response.status_code == 200
    assert response.json()["event_id"] == "event-2"

def test_get_conjunction_not_found(client):
    response = client.get("/api/conjunctions/missing")
    assert response.status_code == 404
