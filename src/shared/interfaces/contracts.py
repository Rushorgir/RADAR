"""
Shared interface contracts (Pydantic models) for cross-module data exchange.

These models define the EXACT data shapes flowing between:
  AI-1 (Anas) → AI-2 (Rushaan) → AI-3 (Udarsh) → Backend (Balaganesh)

⚠️  ANY CHANGE TO THESE MODELS MUST BE COMMUNICATED TO ALL TEAM MEMBERS IMMEDIATELY.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class ObjectType(str, Enum):
    PAYLOAD = "PAYLOAD"
    DEBRIS = "DEBRIS"
    ROCKET_BODY = "ROCKET_BODY"
    UNKNOWN = "UNKNOWN"


class OrbitalRegime(str, Enum):
    LEO = "LEO"       # < 2000 km altitude
    MEO = "MEO"       # 2000–35786 km
    GEO = "GEO"       # ~35786 km
    HEO = "HEO"       # Highly elliptical


class PcMethod(str, Enum):
    FOSTER_2D = "FOSTER_2D"
    MONTE_CARLO = "MONTE_CARLO"


class RiskCategory(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── AI-1 → AI-2: Propagated State Vector ──────────────────────────────────────

class PropagatedState(BaseModel):
    """
    Output from AI-1 (Anas): A single object's state at a single epoch.
    Frame: ECI / J2000.
    """
    object_id: str = Field(..., description="NORAD catalog ID or internal ID")
    epoch: datetime = Field(..., description="UTC epoch of this state")
    position_eci_km: list[float] = Field(
        ..., min_length=3, max_length=3,
        description="Position [x, y, z] in ECI J2000 frame (km)"
    )
    velocity_eci_km_s: list[float] = Field(
        ..., min_length=3, max_length=3,
        description="Velocity [vx, vy, vz] in ECI J2000 frame (km/s)"
    )
    covariance_6x6: Optional[list[list[float]]] = Field(
        None,
        description="6×6 state covariance matrix (km, km/s units). None if unavailable."
    )
    hard_body_radius_km: float = Field(
        0.005, ge=0,
        description="Object hard-body radius (km). Default ~5m."
    )
    cross_section_area_m2: float = Field(
        1.0, ge=0,
        description="Cross-sectional area (m²)"
    )
    object_type: ObjectType = ObjectType.UNKNOWN
    object_name: Optional[str] = None

    @field_validator("covariance_6x6")
    @classmethod
    def validate_covariance_shape(cls, v: Optional[list[list[float]]]) -> Optional[list[list[float]]]:
        if v is not None:
            if len(v) != 6 or any(len(row) != 6 for row in v):
                raise ValueError("Covariance must be 6×6")
        return v

    def position_array(self) -> np.ndarray:
        return np.array(self.position_eci_km)

    def velocity_array(self) -> np.ndarray:
        return np.array(self.velocity_eci_km_s)

    def covariance_array(self) -> Optional[np.ndarray]:
        if self.covariance_6x6 is None:
            return None
        return np.array(self.covariance_6x6)


# ── AI-1 → AI-2: Batch of states for one timestep ─────────────────────────────

class PropagatedEpoch(BaseModel):
    """All objects' states at a single epoch."""
    epoch: datetime
    states: list[PropagatedState]


# ── AI-2 → AI-3 / Backend: Conjunction Event ──────────────────────────────────

class ValidityFlags(BaseModel):
    """Flags indicating whether Pc computation assumptions hold."""
    covariance_valid: bool = True
    relative_velocity_sufficient: bool = True
    encounter_duration_short: bool = True
    covariance_positive_definite: bool = True


class ConjunctionEvent(BaseModel):
    """
    Output from AI-2 (Rushaan): A single conjunction event.
    CDM-compatible structure.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    primary_id: str = Field(..., description="Primary (typically more massive) object ID")
    secondary_id: str = Field(..., description="Secondary object ID")
    tca: datetime = Field(..., description="Time of Closest Approach (UTC)")
    miss_distance_km: float = Field(..., ge=0, description="Miss distance at TCA (km)")
    relative_velocity_km_s: float = Field(..., ge=0, description="Relative velocity magnitude (km/s)")

    # Encounter frame data
    relative_position_enc: Optional[list[float]] = Field(
        None, description="Relative position in encounter frame [B·R, B·T] (km)"
    )
    combined_covariance_enc_2x2: Optional[list[list[float]]] = Field(
        None, description="Combined 2×2 encounter-plane covariance (km²)"
    )

    # Pc result
    pc: float = Field(..., ge=0, le=1, description="Probability of Collision")
    pc_method: PcMethod = PcMethod.FOSTER_2D
    pc_confidence_lower: Optional[float] = Field(None, description="MC lower confidence bound")
    pc_confidence_upper: Optional[float] = Field(None, description="MC upper confidence bound")

    # Metadata
    combined_hard_body_radius_km: float = Field(0.015, ge=0)
    primary_object_type: ObjectType = ObjectType.UNKNOWN
    secondary_object_type: ObjectType = ObjectType.UNKNOWN
    validity_flags: ValidityFlags = Field(default_factory=ValidityFlags)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── AI-3 → Backend: Risk-Scored Event ─────────────────────────────────────────

class SHAPFeature(BaseModel):
    """A single SHAP feature contribution."""
    feature: str
    impact: float


class ManeuverAdvisory(BaseModel):
    """Delta-v maneuver suggestion for collision avoidance."""
    delta_v_m_s: float = Field(..., ge=0, description="Required delta-v magnitude (m/s)")
    burn_direction: str = Field(..., description="ALONG_TRACK | RADIAL | CROSS_TRACK")
    new_miss_distance_km: float = Field(..., ge=0)
    fuel_cost_estimate_kg: Optional[float] = None


class RiskScoredEvent(BaseModel):
    """Output from AI-3 (Udarsh): Conjunction event enriched with ML risk score."""
    event_id: str
    ml_risk_score: float = Field(..., ge=0, le=1)
    risk_category: RiskCategory
    shap_top_features: list[SHAPFeature] = Field(default_factory=list)
    maneuver_advisory: Optional[ManeuverAdvisory] = None
