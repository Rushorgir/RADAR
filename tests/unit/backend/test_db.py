import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.db.connection import Base
from src.backend.db.models import ConjunctionEventModel

# Setup in-memory sqlite db for tests
from sqlalchemy.pool import StaticPool
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_db_session():
    db = TestingSessionLocal()
    assert db is not None
    db.close()

def test_create_event():
    db = TestingSessionLocal()
    from datetime import datetime
    event = ConjunctionEventModel(
        primary_id="SAT1", 
        secondary_id="SAT2", 
        tca=datetime.utcnow(), 
        miss_distance_km=1.5, 
        relative_velocity_km_s=7.5,
        pc=0.001,
        pc_method="FOSTER_2D",
        primary_object_type="PAYLOAD",
        secondary_object_type="DEBRIS"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    assert event.event_id is not None
    assert event.primary_id == "SAT1"
    
    db.close()
