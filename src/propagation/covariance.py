"""
Covariance matrix generation/estimation.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Real orbit-determination covariances come from filtering actual tracking
observations (batch least-squares / EKF residuals), which is out of scope for
this hackathon prototype -- Celestrak TLEs carry no covariance information at
all. Instead we synthesize a physically-plausible 6x6 ECI covariance using a
standard empirical error-growth model expressed in the RIC (Radial/In-track/
Cross-track) frame, then rotate it into ECI via
src/shared/frames/transforms.ric_rotation_matrix.

Rationale for the RIC growth model: along-track position error dominates SGP4
propagation error budgets (driven mainly by B*/drag mis-modeling and mean-motion
uncertainty), while radial and cross-track errors grow much more slowly -- see
Vallado & Cefola, "Two-Line Element Sets -- Practice and Use" (2012). Position
and velocity blocks are treated as uncorrelated diagonal in RIC, which is a
simplifying assumption appropriate for this fidelity level (screening / Pc
sensitivity analysis), not a substitute for a real covariance realization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.shared.frames.transforms import StateVector, ric_rotation_matrix
from src.shared.interfaces.contracts import ObjectType


@dataclass(frozen=True)
class RICSigmaModel:
    """1-sigma error-growth model (km for position, km/s for velocity), in the RIC frame."""

    sigma_radial_km0: float = 0.05
    sigma_intrack_km0: float = 0.10
    sigma_crosstrack_km0: float = 0.05
    growth_radial_km_per_hr: float = 0.01
    growth_intrack_km_per_hr: float = 0.20  # along-track error dominates (drag/mean-motion uncertainty)
    growth_crosstrack_km_per_hr: float = 0.01
    sigma_vel_radial_km_s0: float = 1.0e-5
    sigma_vel_intrack_km_s0: float = 5.0e-5
    sigma_vel_crosstrack_km_s0: float = 1.0e-5
    velocity_growth_fraction_per_hr: float = 0.02  # relative growth of velocity sigmas

    def sigmas_at(self, hours_since_epoch: float) -> tuple[np.ndarray, np.ndarray]:
        t = max(hours_since_epoch, 0.0)
        pos_sigma = np.array([
            self.sigma_radial_km0 + self.growth_radial_km_per_hr * t,
            self.sigma_intrack_km0 + self.growth_intrack_km_per_hr * t,
            self.sigma_crosstrack_km0 + self.growth_crosstrack_km_per_hr * t,
        ])
        vel_scale = 1.0 + self.velocity_growth_fraction_per_hr * t
        vel_sigma = vel_scale * np.array([
            self.sigma_vel_radial_km_s0,
            self.sigma_vel_intrack_km_s0,
            self.sigma_vel_crosstrack_km_s0,
        ])
        return pos_sigma, vel_sigma


# Uncontrolled / poorly-characterized objects get wider default uncertainty than
# actively-maintained payloads (no maneuver history, more variable area-to-mass ratio).
DEFAULT_SIGMA_MODELS: dict[ObjectType, RICSigmaModel] = {
    ObjectType.PAYLOAD: RICSigmaModel(),
    ObjectType.ROCKET_BODY: RICSigmaModel(sigma_intrack_km0=0.15, growth_intrack_km_per_hr=0.30),
    ObjectType.DEBRIS: RICSigmaModel(
        sigma_radial_km0=0.08, sigma_intrack_km0=0.20, sigma_crosstrack_km0=0.08,
        growth_intrack_km_per_hr=0.40,
    ),
    ObjectType.UNKNOWN: RICSigmaModel(sigma_intrack_km0=0.20, growth_intrack_km_per_hr=0.40),
}


def estimate_covariance_6x6(
    state: StateVector,
    hours_since_epoch: float,
    object_type: ObjectType = ObjectType.UNKNOWN,
    sigma_model: Optional[RICSigmaModel] = None,
) -> np.ndarray:
    """
    Build a diagonal-in-RIC 6x6 covariance for `state` at `hours_since_epoch` and
    rotate it into the ECI frame `state` itself is expressed in (the RIC frame is
    defined instantaneously from `state`'s own position/velocity).
    """
    model = sigma_model or DEFAULT_SIGMA_MODELS.get(object_type, RICSigmaModel())
    pos_sigma, vel_sigma = model.sigmas_at(hours_since_epoch)

    cov_ric = np.zeros((6, 6))
    cov_ric[0, 0], cov_ric[1, 1], cov_ric[2, 2] = pos_sigma ** 2
    cov_ric[3, 3], cov_ric[4, 4], cov_ric[5, 5] = vel_sigma ** 2

    eci_to_ric = ric_rotation_matrix(state)
    ric_to_eci = eci_to_ric.T
    rotation_6x6 = np.zeros((6, 6))
    rotation_6x6[:3, :3] = ric_to_eci
    rotation_6x6[3:, 3:] = ric_to_eci

    return rotation_6x6 @ cov_ric @ rotation_6x6.T


def estimate_covariance_6x6_batch(
    positions_km: np.ndarray,
    velocities_km_s: np.ndarray,
    hours_since_epoch: np.ndarray,
    object_type: ObjectType = ObjectType.UNKNOWN,
    sigma_model: Optional[RICSigmaModel] = None,
) -> np.ndarray:
    """
    Vectorized form of `estimate_covariance_6x6` for N states at once (all from
    the same object/sigma model, e.g. one object's whole propagated trajectory).
    `positions_km` / `velocities_km_s`: (N,3). `hours_since_epoch`: (N,).
    Returns (N,6,6).

    Calling the scalar version once per state in a Python loop is the wrong
    shape for this at catalog scale: batch-propagating ~800 objects over a
    72h/60s grid means ~3.4M individual states, and 3.4M small numpy calls is
    dominated by per-call Python/numpy overhead rather than actual math. This
    does the same computation with array ops instead of a per-row loop.
    """
    model = sigma_model or DEFAULT_SIGMA_MODELS.get(object_type, RICSigmaModel())
    n = positions_km.shape[0]
    t = np.maximum(hours_since_epoch, 0.0)

    pos_sigma = np.stack([
        model.sigma_radial_km0 + model.growth_radial_km_per_hr * t,
        model.sigma_intrack_km0 + model.growth_intrack_km_per_hr * t,
        model.sigma_crosstrack_km0 + model.growth_crosstrack_km_per_hr * t,
    ], axis=1)  # (N, 3)

    vel_scale = 1.0 + model.velocity_growth_fraction_per_hr * t  # (N,)
    base_vel_sigma = np.array([
        model.sigma_vel_radial_km_s0, model.sigma_vel_intrack_km_s0, model.sigma_vel_crosstrack_km_s0,
    ])
    vel_sigma = vel_scale[:, None] * base_vel_sigma[None, :]  # (N, 3)

    cov_ric = np.zeros((n, 6, 6))
    diag_idx = np.arange(3)
    cov_ric[:, diag_idx, diag_idx] = pos_sigma ** 2
    cov_ric[:, diag_idx + 3, diag_idx + 3] = vel_sigma ** 2

    r = positions_km
    v = velocities_km_s
    r_hat = r / np.linalg.norm(r, axis=1, keepdims=True)
    h = np.cross(r, v)
    c_hat = h / np.linalg.norm(h, axis=1, keepdims=True)
    i_hat = np.cross(c_hat, r_hat)
    eci_to_ric = np.stack([r_hat, i_hat, c_hat], axis=1)  # (N, 3, 3)
    ric_to_eci = np.transpose(eci_to_ric, (0, 2, 1))

    rotation_6x6 = np.zeros((n, 6, 6))
    rotation_6x6[:, :3, :3] = ric_to_eci
    rotation_6x6[:, 3:, 3:] = ric_to_eci

    return rotation_6x6 @ cov_ric @ np.transpose(rotation_6x6, (0, 2, 1))


def is_positive_definite(covariance_6x6: np.ndarray, tol: float = 1e-12) -> bool:
    """Cheap positive-definiteness check (Cholesky) used to flag degenerate covariances."""
    try:
        np.linalg.cholesky(covariance_6x6 + np.eye(6) * tol)
        return True
    except np.linalg.LinAlgError:
        return False
