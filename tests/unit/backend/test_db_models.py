from datetime import datetime

from src.backend.db.models import ConjunctionEventModel, TLEModel


def test_conjunction_event_model():
    event = ConjunctionEventModel(
        event_id="test-id",
        primary_id="12345",
        secondary_id="67890",
        tca=datetime.utcnow(),
        miss_distance_km=0.5,
        relative_velocity_km_s=15.0,
        pc=0.01,
        pc_method="FOSTER_2D",
        primary_object_type="PAYLOAD",
        secondary_object_type="DEBRIS"
    )
    assert event.event_id == "test-id"
    assert event.primary_object_type == "PAYLOAD"
    
def test_tle_model():
    tle = TLEModel(
        object_id="123",
        line1="1...",
        line2="2...",
        epoch=datetime.utcnow()
    )
    assert tle.object_id == "123"
    assert tle.id is None # Before DB insertion
