from datetime import datetime

from src.backend.db import crud


def test_create_and_get_tle(db_session):
    tle_data = {
        "object_id": "25544",
        "object_name": "ISS",
        "object_type": "PAYLOAD",
        "line1": "1 25544U 98067A   20300.00000000  .00000000  00000-0  00000-0 0  9999",
        "line2": "2 25544  51.6400 300.0000 0005000 100.0000 250.0000 15.50000000 12345",
        "epoch": datetime.utcnow()
    }
    tle = crud.create_tle(db_session, tle_data)
    assert tle.object_id == "25544"
    assert tle.id is not None
    
    fetched = crud.get_tle_by_object_id(db_session, "25544")
    assert fetched.id == tle.id

def test_create_and_get_conjunction(db_session):
    event_data = {
        "event_id": "test-uuid",
        "primary_id": "111",
        "secondary_id": "222",
        "tca": datetime.utcnow(),
        "miss_distance_km": 1.5,
        "relative_velocity_km_s": 7.5,
        "pc": 1e-5,
        "pc_method": "FOSTER_2D",
        "risk_category": "HIGH"
    }
    
    event = crud.create_conjunction_event(db_session, event_data)
    assert event.event_id == "test-uuid"
    
    fetched = crud.get_conjunction_event_by_id(db_session, "test-uuid")
    assert fetched.primary_id == "111"
    
    count = crud.get_conjunction_events_count(db_session)
    assert count == 1
    
    # Update test
    updated = crud.update_conjunction_event(db_session, "test-uuid", {"ml_risk_score": 0.95})
    assert updated.ml_risk_score == 0.95
