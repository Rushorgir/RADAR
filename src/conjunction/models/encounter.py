"""
Internal data structures for encounter geometry processing and conjunction event lifecycle management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from src.shared.interfaces.contracts import PropagatedState

# Default fallback covariance: ~1 km standard deviation per axis (1 km²)
DEFAULT_POSITION_COVARIANCE_KM2 = np.diag([1.0, 1.0, 1.0])


def extract_position_covariance(cov_6x6: Optional[np.ndarray]) -> np.ndarray:
    """
    Extract the 3x3 position covariance block from a 6x6 covariance matrix.
    If the covariance is None, falls back to a default diagonal covariance.
    
    Args:
        cov_6x6: A 6x6 or 3x3 covariance matrix, or None.
        
    Returns:
        A 3x3 position covariance matrix.
    """
    if cov_6x6 is None:
        return DEFAULT_POSITION_COVARIANCE_KM2.copy()
    
    cov = np.array(cov_6x6)
    if cov.shape == (6, 6):
        return cov[:3, :3]
    elif cov.shape == (3, 3):
        return cov
    else:
        # Invalid shape, fallback to default
        return DEFAULT_POSITION_COVARIANCE_KM2.copy()


@dataclass
class EncounterGeometry:
    """
    Intermediate model representing the geometry of an encounter between two objects at TCA.
    """
    primary_state: PropagatedState
    secondary_state: PropagatedState
    tca: datetime
    relative_position_eci: np.ndarray    # (3,) km
    relative_velocity_eci: np.ndarray    # (3,) km/s
    miss_distance_km: float
    relative_speed_km_s: float
    combined_covariance_eci: np.ndarray  # (3, 3) km² - always the 3x3 position block
    combined_hard_body_radius_km: float
    
    # Encounter frame quantities (populated after frame transform)
    rotation_matrix: Optional[np.ndarray] = None          # (3, 3) ECI -> encounter rotation
    relative_position_enc: Optional[np.ndarray] = None     # (2,) B-plane [B.T, B.N] km
    combined_covariance_enc: Optional[np.ndarray] = None   # (2, 2) projected covariance km²
