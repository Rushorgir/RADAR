"""
TCA Refiner (Time of Closest Approach)

Refines the discrete timestep TCA using cubic spline interpolation to find the exact global minimum distance.
"""

from typing import Tuple
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar


def refine_tca(
    times_s: np.ndarray,
    distances_km: np.ndarray,
) -> Tuple[float, float]:
    """
    Refine TCA using cubic spline interpolation over the discrete time/distance points.
    
    Args:
        times_s: Array of timestamps in seconds from some epoch.
        distances_km: Array of distances at each timestamp.
        
    Returns:
        Tuple of (tca_seconds, miss_distance_km)
    """
    if len(times_s) < 3:
        # Cannot properly spline with < 3 points. Just return the minimum point.
        idx = np.argmin(distances_km)
        return float(times_s[idx]), float(distances_km[idx])
        
    spline = CubicSpline(times_s, distances_km)
    
    # We want to find the minimum of the spline within the bounds of our data
    result = minimize_scalar(
        spline,
        bounds=(times_s[0], times_s[-1]),
        method='bounded'
    )
    
    return float(result.x), float(spline(result.x))


def interpolate_state_at_tca(
    times_s: np.ndarray,
    positions: np.ndarray,
    velocities: np.ndarray,
    tca_s: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Interpolate position and velocity at the refined TCA.
    
    Args:
        times_s: Array of timestamps (seconds) (T,)
        positions: Array of positions (T, 3) km
        velocities: Array of velocities (T, 3) km/s
        tca_s: The exact TCA timestamp in seconds
        
    Returns:
        Tuple of (position (3,), velocity (3,)) at TCA.
    """
    if len(times_s) < 2:
        return positions[0], velocities[0]
        
    pos_interp = CubicSpline(times_s, positions, axis=0)
    vel_interp = CubicSpline(times_s, velocities, axis=0)
    
    return pos_interp(tca_s), vel_interp(tca_s)
