from __future__ import annotations

"""
Stage 2 Conjunction Screening: Fine Filter

Uses 3D spatial indexing (k-d tree) at each timestep to flag close approaches within a threshold sphere.
"""

from typing import List, Tuple
import numpy as np
from scipy.spatial import cKDTree

from src.shared.constants.physical import SCREENING


def fine_filter_at_epoch(
    positions: np.ndarray,
    object_ids: List[str],
    threshold_km: float = SCREENING.ENCOUNTER_SPHERE_RADIUS_KM,
) -> List[Tuple[str, str, float]]:
    """
    Find all pairs within the threshold distance at a single epoch.
    
    Args:
        positions: Numpy array of shape (N, 3) representing ECI positions in km.
        object_ids: List of N object IDs corresponding to the positions.
        threshold_km: Distance threshold for a close approach.
        
    Returns:
        List of tuples (id_i, id_j, distance) for pairs within the threshold.
    """
    if len(positions) == 0:
        return []
        
    tree = cKDTree(positions)
    # output_type='ndarray' returns an (M, 2) array of indices
    pairs_idx = tree.query_pairs(r=threshold_km, output_type='ndarray')
    
    if len(pairs_idx) == 0:
        return []
        
    results = []
    for idx_i, idx_j in pairs_idx:
        id_i = object_ids[idx_i]
        id_j = object_ids[idx_j]
        # Calculate actual distance
        pos_i = positions[idx_i]
        pos_j = positions[idx_j]
        distance = np.linalg.norm(pos_i - pos_j)
        
        # Ensure consistent ordering (e.g., alphabetically) for easier deduplication later
        if id_i > id_j:
            id_i, id_j = id_j, id_i
            
        results.append((id_i, id_j, float(distance)))
        
    return results
