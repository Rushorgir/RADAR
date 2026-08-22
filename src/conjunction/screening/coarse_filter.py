"""
Stage 1 Conjunction Screening: Coarse Filter

Uses altitude band bucketing to quickly eliminate pairs of objects that can never intersect.
"""

from typing import Dict, List, Tuple
import numpy as np

from src.shared.interfaces.contracts import PropagatedState
from src.shared.constants.physical import EARTH, SCREENING


def compute_altitude_band(states: List[PropagatedState]) -> Tuple[float, float]:
    """
    Compute the minimum and maximum altitude (in km) across all epochs for a single object.
    
    Args:
        states: List of PropagatedState over the screening window.
        
    Returns:
        Tuple of (min_altitude, max_altitude) in km.
    """
    if not states:
        raise ValueError("Cannot compute altitude band for empty state list.")
        
    altitudes = [np.linalg.norm(s.position_array()) - EARTH.RADIUS_KM for s in states]
    return min(altitudes), max(altitudes)


def coarse_filter(
    all_states: Dict[str, List[PropagatedState]],
    margin_km: float = SCREENING.ALTITUDE_BAND_HALF_WIDTH_KM,
) -> List[Tuple[str, str]]:
    """
    Find pairs of object IDs whose altitude bands overlap within the given margin.
    Uses a sweep-line algorithm to efficiently find overlapping intervals.
    
    Args:
        all_states: Dictionary mapping object_id to a list of its PropagatedStates.
        margin_km: Half-width of the altitude band margin.
        
    Returns:
        List of object ID pairs (id1, id2) that might conjunct.
    """
    # 1. Compute altitude band for each object
    bands = []
    for obj_id, states in all_states.items():
        if not states:
            continue
        h_min, h_max = compute_altitude_band(states)
        # Expand band by margin
        h_min -= margin_km
        h_max += margin_km
        bands.append((h_min, h_max, obj_id))
        
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
                # Since bands are sorted by h_min, no further bands can overlap with i
                break
                
            # Otherwise, they overlap
            candidate_pairs.append((id_i, id_j))
            
    return candidate_pairs
