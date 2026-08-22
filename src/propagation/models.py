"""
Data models for the SGP4 propagation engine.

Owner: Anas (AI-1: Orbital Mechanics Lead)

The actual per-timestep state vector handed downstream to AI-2 is
`src.shared.interfaces.contracts.PropagatedState` (the team-wide interface
contract) -- this module does NOT redefine it, it wraps it with the batch/error
bookkeeping needed inside the propagation engine itself.
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, Field

from src.shared.interfaces.contracts import ObjectType, PropagatedState

__all__ = [
    "PropagatedState",
    "SGP4ErrorCode",
    "PropagationError",
    "TrajectoryResult",
    "BatchPropagationResult",
]


class SGP4ErrorCode(IntEnum):
    """Error codes returned by sgp4.api.Satrec.sgp4() (0 = success)."""

    SUCCESS = 0
    MEAN_ELEMENTS_ECCENTRICITY_OUT_OF_RANGE = 1
    MEAN_MOTION_LESS_THAN_ZERO = 2
    PERT_ELEMENTS_ECCENTRICITY_OUT_OF_RANGE = 3
    SEMI_LATUS_RECTUM_NEGATIVE = 4
    EPOCH_ELEMENTS_ARE_SUBORBITAL = 5  # unused by modern sgp4, kept for completeness
    SATELLITE_HAS_DECAYED = 6

    @property
    def description(self) -> str:
        return _SGP4_ERROR_DESCRIPTIONS.get(self, "Unknown SGP4 error")


_SGP4_ERROR_DESCRIPTIONS = {
    SGP4ErrorCode.SUCCESS: "No error",
    SGP4ErrorCode.MEAN_ELEMENTS_ECCENTRICITY_OUT_OF_RANGE: "Mean eccentricity out of range (not 0 <= e < 1)",
    SGP4ErrorCode.MEAN_MOTION_LESS_THAN_ZERO: "Mean motion less than zero",
    SGP4ErrorCode.PERT_ELEMENTS_ECCENTRICITY_OUT_OF_RANGE: "Perturbed eccentricity out of range",
    SGP4ErrorCode.SEMI_LATUS_RECTUM_NEGATIVE: "Semi-latus rectum < 0",
    SGP4ErrorCode.EPOCH_ELEMENTS_ARE_SUBORBITAL: "Epoch elements are sub-orbital",
    SGP4ErrorCode.SATELLITE_HAS_DECAYED: "Satellite has decayed (re-entered)",
}


class PropagationError(BaseModel):
    """Records a single failed propagation attempt (e.g. a decayed object)."""

    object_id: str
    epoch: datetime
    error_code: SGP4ErrorCode
    message: str


class TrajectoryResult(BaseModel):
    """All successfully-propagated states (plus any errors) for one object."""

    object_id: str
    object_name: str = ""
    object_type: ObjectType = ObjectType.UNKNOWN
    states: list[PropagatedState] = Field(default_factory=list)
    errors: list[PropagationError] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.states) > 0 and len(self.errors) == 0


class BatchPropagationResult(BaseModel):
    """Output of propagating a whole catalog across a shared timestep grid."""

    epochs: list[datetime]
    trajectories: dict[str, TrajectoryResult] = Field(default_factory=dict)

    @property
    def object_ids(self) -> list[str]:
        return list(self.trajectories.keys())

    @property
    def failed_object_ids(self) -> list[str]:
        return [oid for oid, traj in self.trajectories.items() if not traj.ok]

    def states_at(self, epoch_index: int) -> list[PropagatedState]:
        """All objects' states at the epoch_index-th timestep (skips objects with gaps there)."""
        out = []
        for traj in self.trajectories.values():
            if epoch_index < len(traj.states):
                out.append(traj.states[epoch_index])
        return out
