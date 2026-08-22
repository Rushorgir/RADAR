"""
Screening Engine Orchestrator

Coordinates the coarse filter, fine filter, deduplication, and TCA refinement.
"""

from typing import Dict, List, Tuple
from loguru import logger
import numpy as np
from collections import defaultdict

from src.propagation.batch_arrays import CatalogPropagationArrays
from src.conjunction.screening.coarse_filter import coarse_filter
from src.conjunction.screening.fine_filter import fine_filter_at_epoch


class ScreeningEngine:
    """Orchestrates the two-stage screening process."""
    
    def run(self, arrays: CatalogPropagationArrays) -> List[Dict]:
        """
        Run the screening process over a batch propagation array result.
        
        Args:
            arrays: CatalogPropagationArrays containing physics arrays for all objects/epochs.
            
        Returns:
            List of dictionaries containing raw encounter data:
            - primary_index, secondary_index (int)
            - base_epoch (datetime)
            - flagged_times_s (relative times in seconds)
            - flagged_distances_km
        """
        logger.info(f"Starting screening engine with {arrays.n_objects} objects x {arrays.n_steps} epochs.")
        if arrays.n_objects == 0 or arrays.n_steps == 0:
            return []
            
        # 1. Coarse filter (uses fast vectorization)
        candidate_pairs = coarse_filter(
            positions_eci_km=arrays.positions_eci_km,
            ok_mask=arrays.ok_mask,
            object_ids=arrays.object_ids
        )
        logger.info(f"Coarse filter identified {len(candidate_pairs)} candidate pairs.")
        
        if not candidate_pairs:
            return []
            
        # 2. Fine filter across all timesteps
        # We only want to search positions of objects that are in the candidate set.
        candidate_set = {obj_id for pair in candidate_pairs for obj_id in pair}
        
        # Build candidate mask / indices
        candidate_indices = []
        candidate_ids = []
        for i, obj_id in enumerate(arrays.object_ids):
            if obj_id in candidate_set:
                candidate_indices.append(i)
                candidate_ids.append(obj_id)
                
        candidate_indices = np.array(candidate_indices)
        
        # Dictionary to track distances over time for pairs flagged by fine filter
        # Key: (id1, id2), Value: list of (time_s, dist_km)
        raw_encounters = defaultdict(list)
        
        base_epoch = arrays.epochs[0]
        epoch_seconds = np.array([(ep - base_epoch).total_seconds() for ep in arrays.epochs])
        
        for step_idx in range(arrays.n_steps):
            time_s = epoch_seconds[step_idx]
            
            # Extract positions for candidates using fast numpy indexing
            # Mask out invalid states at this step
            step_ok = arrays.ok_mask[candidate_indices, step_idx]
            
            # Only test valid ones
            valid_indices = candidate_indices[step_ok]
            
            if len(valid_indices) == 0:
                continue
                
            positions = arrays.positions_eci_km[valid_indices, step_idx, :]
            obj_ids = [arrays.object_ids[idx] for idx in valid_indices]
            
            # Run fine filter
            pairs_at_epoch = fine_filter_at_epoch(positions, obj_ids)
            for id1, id2, dist in pairs_at_epoch:
                raw_encounters[(id1, id2)].append((time_s, dist))
                
        logger.info(f"Fine filter flagged {len(raw_encounters)} unique close approach pairs.")
        
        # 3. Package results for TCA refinement
        results = []
        for (id1, id2), time_dist_list in raw_encounters.items():
            # Sort by time
            time_dist_list.sort(key=lambda x: x[0])
            times_s = np.array([td[0] for td in time_dist_list])
            distances_km = np.array([td[1] for td in time_dist_list])
            
            idx1 = arrays.object_index(id1)
            idx2 = arrays.object_index(id2)
            
            results.append({
                "primary_index": idx1,
                "secondary_index": idx2,
                "base_epoch": base_epoch,
                "flagged_times_s": times_s,
                "flagged_distances_km": distances_km
            })
            
        return results
