from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from src.shared.interfaces.contracts import (
    ManeuverAdvisory,
    ObjectType,
    RiskCategory,
    SHAPFeature,
)

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int

class ManeuverAdvisoryResponse(BaseModel):
    delta_v_m_s: float
    burn_direction: str
    new_miss_distance_km: float
    fuel_cost_estimate_kg: float | None

class ConjunctionEventResponse(BaseModel):
    """Maps 1:1 to ConjunctionEventModel. Used for GET responses."""
    event_id: str
    primary_id: str
    secondary_id: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    relative_position_enc: list[float] | None = None
    combined_covariance_enc_2x2: list[list[float]] | None = None
    pc: float
    pc_method: str
    pc_confidence_lower: float | None = None
    pc_confidence_upper: float | None = None
    combined_hard_body_radius_km: float
    primary_object_type: str
    secondary_object_type: str
    validity_flags: dict[str, bool] | None = None
    
    # Enriched fields from ML
    ml_risk_score: float | None = None
    risk_category: str | None = None
    shap_top_features: list[dict[str, Any]] | None = None
    
    # Enriched fields from Maneuver
    maneuver_delta_v_m_s: float | None = None
    maneuver_burn_direction: str | None = None
    maneuver_new_miss_distance_km: float | None = None
    maneuver_fuel_cost_estimate_kg: float | None = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TLEDataResponse(BaseModel):
    """Full TLE response."""
    id: int
    object_id: str
    object_name: str | None = None
    object_type: str | None = None
    line1: str
    line2: str
    epoch: datetime
    inclination_deg: float | None = None
    eccentricity: float | None = None
    mean_motion_rev_day: float | None = None
    fetched_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ObjectPositionResponse(BaseModel):
    """Real SGP4-propagated current position for one object (src/propagation/current_positions.py)."""
    object_id: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float


class PositionsResponse(BaseModel):
    epoch: datetime
    positions: list[ObjectPositionResponse]
    # How many tracked objects were requested vs. actually got a position --
    # SGP4 can fail for a handful of objects (decayed, malformed elements);
    # this makes that visible instead of a caller silently getting fewer
    # positions than objects with no way to tell why.
    requested: int


class DashboardSummaryResponse(BaseModel):
    total_tracked_objects: int
    total_conjunction_events: int
    active_high_risk_alerts: int
    risk_distribution: dict[str, int]
    recent_high_risk_events: list[ConjunctionEventResponse]


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
    relative_position_enc: list[float] | None = None
    combined_covariance_enc_2x2: list[list[float]] | None = None
    pc: float
    pc_method: str
    pc_confidence_lower: float | None = None
    pc_confidence_upper: float | None = None
    combined_hard_body_radius_km: float
    primary_object_type: ObjectType
    secondary_object_type: ObjectType
    validity_flags: dict[str, bool] | None = None


class RiskScoreUpdate(BaseModel):
    """POST body for updating risk scores from AI-3."""
    event_id: str
    ml_risk_score: float
    risk_category: RiskCategory
    shap_top_features: list[SHAPFeature]
    maneuver_advisory: ManeuverAdvisory | None = None


class TLECreate(BaseModel):
    """POST body for ingesting TLE data from AI-1."""
    object_id: str
    object_name: str | None = None
    object_type: ObjectType | None = None
    line1: str
    line2: str
    epoch: datetime
    inclination_deg: float | None = None
    eccentricity: float | None = None
    mean_motion_rev_day: float | None = None
