import pytest
from src.backend.db import crud
from datetime import datetime

def test_get_dashboard_summary(client, db_session):
    # Create TLE
    crud.create_tle(db_session, {
        "object_id": "1", "line1": "1...", "line2": "2...", "epoch": datetime.utcnow()
    })
    crud.create_tle(db_session, {
        "object_id": "2", "line1": "1...", "line2": "2...", "epoch": datetime.utcnow()
    })
    
    # Create Events
    crud.create_conjunction_event(db_session, {
        "event_id": "e1", "primary_id": "1", "secondary_id": "2", "tca": datetime.utcnow(),
        "miss_distance_km": 1.0, "relative_velocity_km_s": 7.0, "pc": 1e-4, "pc_method": "FOSTER_2D",
        "risk_category": "HIGH"
    })
    crud.create_conjunction_event(db_session, {
        "event_id": "e2", "primary_id": "1", "secondary_id": "3", "tca": datetime.utcnow(),
        "miss_distance_km": 5.0, "relative_velocity_km_s": 7.0, "pc": 1e-6, "pc_method": "FOSTER_2D",
        "risk_category": "LOW"
    })
    
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tracked_objects"] == 2
    assert data["total_conjunction_events"] == 2
    assert data["active_high_risk_alerts"] == 1
    assert data["risk_distribution"]["HIGH"] == 1
    assert data["risk_distribution"]["LOW"] == 1
    assert len(data["recent_high_risk_events"]) == 1
