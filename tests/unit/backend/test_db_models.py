import pytest
from src.backend.db.models import ConjunctionEventModel, TLEModel
from datetime import datetime
import json

def test_conjunction_event_model():
    event = ConjunctionEventModel(
        event_id="test-id",
        primary_id="1",
        secondary_id="2",
        tca=datetime.utcnow(),
        miss_distance_km=1.0,
        relative_velocity_km_s=7.0,
        pc=1e-4,
        pc_method="FOSTER_2D"
    )
    assert event.event_id == "test-id"
    assert event.primary_object_type == "UNKNOWN" # Check default
    assert event.combined_hard_body_radius_km == 0.015 # Check default
    
def test_tle_model():
    tle = TLEModel(
        object_id="123",
        line1="1...",
        line2="2...",
        epoch=datetime.utcnow()
    )
    assert tle.object_id == "123"
    assert tle.id is None # Before DB insertion
