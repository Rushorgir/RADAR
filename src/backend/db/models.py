import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON
from src.backend.db.connection import Base


class ConjunctionEventModel(Base):
    """
    Full-fidelity ORM model mapping to ConjunctionEvent and downstream ML/Maneuver outputs.
    Using JSON columns for arrays/nested objects to ensure SQLite/Postgres compatibility.
    """
    __tablename__ = "conjunction_events"

    # Core Event Data
    event_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    primary_id = Column(String, index=True, nullable=False)
    secondary_id = Column(String, index=True, nullable=False)
    tca = Column(DateTime, nullable=False, index=True)
    miss_distance_km = Column(Float, nullable=False)
    relative_velocity_km_s = Column(Float, nullable=False)

    # Encounter Geometry (JSON stored as list of floats or 2x2 list of lists)
    relative_position_enc = Column(JSON, nullable=True)
    combined_covariance_enc_2x2 = Column(JSON, nullable=True)

    # Probability of Collision
    pc = Column(Float, nullable=False)
    pc_method = Column(String, nullable=False)
    pc_confidence_lower = Column(Float, nullable=True)
    pc_confidence_upper = Column(Float, nullable=True)

    # Metadata & Flags
    combined_hard_body_radius_km = Column(Float, nullable=False, default=0.015)
    primary_object_type = Column(String, nullable=False, default="UNKNOWN")
    secondary_object_type = Column(String, nullable=False, default="UNKNOWN")
    validity_flags = Column(JSON, nullable=True)  # Store dict of boolean flags

    # ML Risk Scores (Updated by AI-3 pipeline)
    ml_risk_score = Column(Float, nullable=True)
    risk_category = Column(String, nullable=True, index=True)
    shap_top_features = Column(JSON, nullable=True)  # Store list of dicts

    # Maneuver Advisory (Updated by AI-3 pipeline)
    maneuver_delta_v_m_s = Column(Float, nullable=True)
    maneuver_burn_direction = Column(String, nullable=True)
    maneuver_new_miss_distance_km = Column(Float, nullable=True)
    maneuver_fuel_cost_estimate_kg = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class TLEModel(Base):
    """
    ORM model mapping to parsed TLE records.
    Uses surrogate ID to allow tracking historical TLEs for the same object.
    """
    __tablename__ = "tle_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(String, index=True, nullable=False)
    object_name = Column(String, nullable=True)
    object_type = Column(String, nullable=True)
    
    line1 = Column(String, nullable=False)
    line2 = Column(String, nullable=False)
    epoch = Column(DateTime, nullable=False, index=True)
    
    # Optional parsed orbital elements for direct querying
    inclination_deg = Column(Float, nullable=True)
    eccentricity = Column(Float, nullable=True)
    mean_motion_rev_day = Column(Float, nullable=True)

    fetched_at = Column(DateTime, default=datetime.utcnow)
