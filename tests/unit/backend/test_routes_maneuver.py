from datetime import datetime

from src.backend.db import crud


def test_get_maneuver_advisory(client, db_session):
    event_data = {
        "event_id": "man-1",
        "primary_id": "1",
        "secondary_id": "2",
        "tca": datetime.utcnow(),
        "miss_distance_km": 1.0,
        "relative_velocity_km_s": 7.0,
        "pc": 1e-4,
        "pc_method": "FOSTER_2D",
        "maneuver_delta_v_m_s": 0.15,
        "maneuver_burn_direction": "ALONG_TRACK",
        "maneuver_new_miss_distance_km": 5.5,
        "maneuver_fuel_cost_estimate_kg": 0.02
    }
    crud.create_conjunction_event(db_session, event_data)
    
    response = client.get("/api/maneuver/man-1")
    assert response.status_code == 200
    data = response.json()
    assert data["delta_v_m_s"] == 0.15
    assert data["burn_direction"] == "ALONG_TRACK"

def test_get_maneuver_no_advisory(client, db_session):
    event_data = {
        "event_id": "man-2",
        "primary_id": "1",
        "secondary_id": "2",
        "tca": datetime.utcnow(),
        "miss_distance_km": 1.0,
        "relative_velocity_km_s": 7.0,
        "pc": 1e-4,
        "pc_method": "FOSTER_2D"
    }
    crud.create_conjunction_event(db_session, event_data)
    
    response = client.get("/api/maneuver/man-2")
    assert response.status_code == 404
