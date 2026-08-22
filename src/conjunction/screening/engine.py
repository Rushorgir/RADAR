"""
Screening Engine Orchestrator

Coordinates the coarse filter, fine filter, deduplication, and TCA refinement.
"""

from typing import Dict, List, Tuple
from loguru import logger
import numpy as np
from collections import defaultdict
from datetime import datetime, timezone

from src.shared.interfaces.contracts import PropagatedEpoch, PropagatedState
from src.conjunction.screening.coarse_filter import coarse_filter
from src.conjunction.screening.fine_filter import fine_filter_at_epoch
from src.conjunction.screening.tca_refiner import refine_tca, interpolate_state_at_tca


class ScreeningEngine:
    """Orchestrates the two-stage screening process."""
    
    def run(self, epoch_data: List[PropagatedEpoch]) -> List[Dict]:
        """
        Run the screening process over a series of propagated epochs.
        
        Args:
            epoch_data: List of PropagatedEpoch.
            
        Returns:
            List of dictionaries containing raw encounter data:
            - primary_id, secondary_id
            - primary_states (list of states for interpolation)
            - secondary_states
            - times_s (relative times in seconds)
            - distances_km
        """
        logger.info(f"Starting screening engine with {len(epoch_data)} epochs.")
        if not epoch_data:
            return []
            
        # 1. Reorganize data into object -> states map for coarse filter
        all_states = defaultdict(list)
        for ep in epoch_data:
            for state in ep.states:
                all_states[state.object_id].append(state)
                
        # 2. Coarse filter
        candidate_pairs = coarse_filter(all_states)
        logger.info(f"Coarse filter identified {len(candidate_pairs)} candidate pairs.")
        
        if not candidate_pairs:
            return []
            
        # 3. Fine filter across all timesteps
        # We only want to search positions of objects that are in the candidate set.
        candidate_set = {obj_id for pair in candidate_pairs for obj_id in pair}
        
        # Dictionary to track distances over time for pairs flagged by fine filter
        # Key: (id1, id2), Value: list of (time_s, dist_km)
        raw_encounters = defaultdict(list)
        
        base_epoch = epoch_data[0].epoch
        
        for ep in epoch_data:
            time_s = (ep.epoch - base_epoch).total_seconds()
            
            # Extract positions for candidates
            positions = []
            obj_ids = []
            for state in ep.states:
                if state.object_id in candidate_set:
                    positions.append(state.position_eci_km)
                    obj_ids.append(state.object_id)
                    
            if not positions:
                continue
                
            positions = np.array(positions)
            
            # Run fine filter
            pairs_at_epoch = fine_filter_at_epoch(positions, obj_ids)
            for id1, id2, dist in pairs_at_epoch:
                # To prevent duplicates from ordering, we already sorted id1, id2 in fine_filter
                raw_encounters[(id1, id2)].append((time_s, dist))
                
        logger.info(f"Fine filter flagged {len(raw_encounters)} unique close approach pairs.")
        
        # 4. Package results for TCA refinement
        results = []
        for (id1, id2), time_dist_list in raw_encounters.items():
            # Sort by time
            time_dist_list.sort(key=lambda x: x[0])
            times_s = np.array([td[0] for td in time_dist_list])
            distances_km = np.array([td[1] for td in time_dist_list])
            
            # We need the full state history for interpolation around TCA
            # Find the minimum distance index in our flagged points
            min_idx = np.argmin(distances_km)
            best_time_s = times_s[min_idx]
            
            # Grab states from the full all_states list that are close to best_time_s
            # For a cubic spline, we ideally want 4-5 points centered around the TCA.
            # For simplicity, we can pass the entire state history, or just a 5-point window.
            # Let's pass the full history (it's small enough, ~4000 points) and let the refiner handle it.
            # Actually, passing full history is best.
            
            results.append({
                "primary_id": id1,
                "secondary_id": id2,
                "primary_states": all_states[id1],
                "secondary_states": all_states[id2],
                "base_epoch": base_epoch,
                "flagged_times_s": times_s,
                "flagged_distances_km": distances_km
            })
            
        return results
