from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.shared.interfaces.contracts import (
    ConjunctionEvent, 
    RiskScoredEvent, 
    ManeuverAdvisory,
    SHAPFeature,
    RiskCategory,
    ObjectType
)

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int

class ManeuverAdvisoryResponse(BaseModel):
    delta_v_m_s: float
    burn_direction: str
    new_miss_distance_km: float
    fuel_cost_estimate_kg: Optional[float]

class ConjunctionEventResponse(BaseModel):
    """Maps 1:1 to ConjunctionEventModel. Used for GET responses."""
    event_id: str
    primary_id: str
    secondary_id: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    relative_position_enc: Optional[List[float]] = None
    combined_covariance_enc_2x2: Optional[List[List[float]]] = None
    pc: float
    pc_method: str
    pc_confidence_lower: Optional[float] = None
    pc_confidence_upper: Optional[float] = None
    combined_hard_body_radius_km: float
    primary_object_type: str
    secondary_object_type: str
    validity_flags: Optional[Dict[str, bool]] = None
    
    # Enriched fields from ML
    ml_risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    shap_top_features: Optional[List[Dict[str, Any]]] = None
    
    # Enriched fields from Maneuver
    maneuver_delta_v_m_s: Optional[float] = None
    maneuver_burn_direction: Optional[str] = None
    maneuver_new_miss_distance_km: Optional[float] = None
    maneuver_fuel_cost_estimate_kg: Optional[float] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TLEDataResponse(BaseModel):
    """Full TLE response."""
    id: int
    object_id: str
    object_name: Optional[str] = None
    object_type: Optional[str] = None
    line1: str
    line2: str
    epoch: datetime
    inclination_deg: Optional[float] = None
    eccentricity: Optional[float] = None
    mean_motion_rev_day: Optional[float] = None
    fetched_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    total_tracked_objects: int
    total_conjunction_events: int
    active_high_risk_alerts: int
    risk_distribution: Dict[str, int]
    recent_high_risk_events: List[ConjunctionEventResponse]


# --- Request Models for Ingestion ---

class ConjunctionEventCreate(BaseModel):
    """POST body for ingesting a new conjunction event from AI-2."""
    # Essentially reusing the shared contract schema, just validating it comes in correctly
    event_id: str
    primary_id: str
    secondary_id: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    relative_position_enc: Optional[List[float]] = None
    combined_covariance_enc_2x2: Optional[List[List[float]]] = None
    pc: float
    pc_method: str
    pc_confidence_lower: Optional[float] = None
    pc_confidence_upper: Optional[float] = None
    combined_hard_body_radius_km: float
    primary_object_type: ObjectType
    secondary_object_type: ObjectType
    validity_flags: Optional[Dict[str, bool]] = None


class RiskScoreUpdate(BaseModel):
    """POST body for updating risk scores from AI-3."""
    event_id: str
    ml_risk_score: float
    risk_category: RiskCategory
    shap_top_features: List[SHAPFeature]
    maneuver_advisory: Optional[ManeuverAdvisory] = None


class TLECreate(BaseModel):
    """POST body for ingesting TLE data from AI-1."""
    object_id: str
    object_name: Optional[str] = None
    object_type: Optional[ObjectType] = None
    line1: str
    line2: str
    epoch: datetime
    inclination_deg: Optional[float] = None
    eccentricity: Optional[float] = None
    mean_motion_rev_day: Optional[float] = None
