import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.db.connection import Base
from src.backend.db.models import ConjunctionEventModel

# Setup in-memory sqlite db for tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_db_session():
    db = TestingSessionLocal()
    assert db is not None
    db.close()

def test_create_event():
    db = TestingSessionLocal()
    event = ConjunctionEventModel(
        primary_id="SAT1", 
        secondary_id="SAT2", 
        tca="2024-01-01 00:00:00", 
        miss_distance_km=1.5, 
        relative_velocity_km_s=7.5,
        pc=0.001,
        pc_method="FOSTER_2D"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    assert event.event_id is not None
    assert event.primary_id == "SAT1"
    
    db.close()
