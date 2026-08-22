from __future__ import annotations

"""
Physical constants and system-wide thresholds for the RADAR/OrbitGuard SSA system.

All units follow the convention:
  - Distance: kilometers (km)
  - Velocity: km/s (unless noted as m/s)
  - Time: seconds (s)
  - Mass: kilograms (kg)
  - Angles: radians
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EarthConstants:
    """WGS84 Earth parameters."""
    RADIUS_KM: float = 6378.137                    # Equatorial radius
    MU_KM3_S2: float = 398600.4418                 # Gravitational parameter
    J2: float = 1.08263e-3                          # J2 oblateness coefficient
    ROTATION_RATE_RAD_S: float = 7.2921159e-5       # Earth rotation rate
    FLATTENING: float = 1.0 / 298.257223563         # WGS84 flattening


@dataclass(frozen=True)
class ScreeningThresholds:
    """Conjunction screening algorithm parameters."""
    ALTITUDE_BAND_HALF_WIDTH_KM: float = 50.0       # Coarse filter band width
    ENCOUNTER_SPHERE_RADIUS_KM: float = 10.0        # Fine filter distance threshold
    SCREENING_TIMESTEP_S: float = 60.0              # Time discretization for screening
    PROPAGATION_HORIZON_H: float = 72.0             # How far ahead to propagate
    TCA_REFINEMENT_TOL_S: float = 0.1               # TCA interpolation tolerance


@dataclass(frozen=True)
class PcThresholds:
    """Probability of Collision engine parameters."""
    DEFAULT_COMBINED_RADIUS_KM: float = 0.015       # ~15m combined hard-body radius
    FOSTER_MIN_VREL_MS: float = 100.0               # Below this → Monte Carlo fallback
    MONTE_CARLO_SAMPLES: int = 100_000              # Default sample count
    MONTE_CARLO_CONFIDENCE: float = 0.95            # Confidence interval level
    PC_HIGH_RISK: float = 1.0e-4                    # High-risk Pc threshold
    PC_MEDIUM_RISK: float = 1.0e-6                  # Medium-risk Pc threshold
    COVARIANCE_SINGULARITY_TOL: float = 1.0e-12     # Degenerate covariance check


# Singleton instances for easy import
EARTH = EarthConstants()
SCREENING = ScreeningThresholds()
PC = PcThresholds()
