from __future__ import annotations

"""
Stage 1 Conjunction Screening: Coarse Filter

Uses altitude band bucketing to quickly eliminate pairs of objects that can never intersect.
"""

from typing import List, Tuple
import numpy as np

from src.shared.constants.physical import EARTH, SCREENING


def compute_altitude_bands(positions_eci_km: np.ndarray, ok_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the minimum and maximum altitude (in km) across all epochs for every object.
    
    Args:
        positions_eci_km: (n_objects, n_steps, 3) ECI positions.
        ok_mask: (n_objects, n_steps) boolean mask of valid states.
        
    Returns:
        Tuple of (min_altitudes, max_altitudes) of shape (n_objects,).
    """
    # Compute radii for all points (n_objects, n_steps)
    radii = np.linalg.norm(positions_eci_km, axis=2)
    altitudes = radii - EARTH.RADIUS_KM
    
    # Where ok_mask is False, set altitudes to NaN so they don't affect min/max
    alt_masked = np.where(ok_mask, altitudes, np.nan)
    
    with np.errstate(all='ignore'): # Ignore warnings for objects with all-NaN rows (decayed)
        min_alts = np.nanmin(alt_masked, axis=1)
        max_alts = np.nanmax(alt_masked, axis=1)
        
    return min_alts, max_alts


def coarse_filter(
    positions_eci_km: np.ndarray,
    ok_mask: np.ndarray,
    object_ids: List[str],
    margin_km: float = SCREENING.ALTITUDE_BAND_HALF_WIDTH_KM,
) -> List[Tuple[str, str]]:
    """
    Find pairs of object IDs whose altitude bands overlap within the given margin.
    Uses a sweep-line algorithm to efficiently find overlapping intervals.
    
    Args:
        positions_eci_km: (n_objects, n_steps, 3) ECI positions.
        ok_mask: (n_objects, n_steps) boolean mask.
        object_ids: List of object IDs matching the row dimension.
        margin_km: Half-width of the altitude band margin.
        
    Returns:
        List of object ID pairs (id1, id2) that might conjunct.
    """
    n_objects = positions_eci_km.shape[0]
    if n_objects == 0:
        return []
        
    # 1. Compute altitude band for all objects vectorized
    min_alts, max_alts = compute_altitude_bands(positions_eci_km, ok_mask)
    
    bands = []
    for i in range(n_objects):
        if np.isnan(min_alts[i]):
            continue
        h_min = min_alts[i] - margin_km
        h_max = max_alts[i] + margin_km
        bands.append((h_min, h_max, object_ids[i]))
        
    # 2. Sort by h_min
    bands.sort(key=lambda x: x[0])
    
    # 3. Sweep-line to find overlaps
    candidate_pairs = []
    for i in range(len(bands)):
        h_min_i, h_max_i, id_i = bands[i]
        
        # Check subsequent bands until their h_min is strictly greater than our h_max
        for j in range(i + 1, len(bands)):
            h_min_j, h_max_j, id_j = bands[j]
            
            if h_min_j > h_max_i:
                break
                
            candidate_pairs.append((id_i, id_j))
            
    return candidate_pairs
