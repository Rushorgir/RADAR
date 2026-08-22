"""
End-to-end Conjunction Screening and Probability Pipeline.
"""

from typing import List, Tuple
from loguru import logger
from datetime import timedelta
import numpy as np

from src.shared.interfaces.contracts import ConjunctionEvent, PcMethod, ValidityFlags
from src.shared.constants.physical import PC
from src.propagation.batch_arrays import CatalogPropagationArrays
from src.conjunction.screening.engine import ScreeningEngine
from src.conjunction.screening.tca_refiner import refine_tca, interpolate_state_at_tca
from src.conjunction.models.encounter import EncounterGeometry, extract_position_covariance
from src.conjunction.probability.encounter_frame import compute_encounter_frame, project_to_encounter_plane
from src.conjunction.probability.engine import PcEngine, PcResult


class ConjunctionPipeline:
    """
    End-to-end pipeline: CatalogPropagationArrays -> ConjunctionEvents.
    """
    
    PC_COMPUTE_THRESHOLD_KM = 5.0    # Full Pc computation
    PC_LOG_ONLY_THRESHOLD_KM = 10.0  # Log but assign Pc = 0
    
    def __init__(self):
        self.screening_engine = ScreeningEngine()
        self.pc_engine = PcEngine()
        
    def run(self, arrays: CatalogPropagationArrays) -> List[ConjunctionEvent]:
        logger.info("Starting Conjunction Pipeline.")
        
        # 1. & 2. Coarse and Fine Filters
        raw_encounters = self.screening_engine.run(arrays)
        
        events = []
        for enc_data in raw_encounters:
            idx1 = enc_data["primary_index"]
            idx2 = enc_data["secondary_index"]
            flagged_times_s = enc_data["flagged_times_s"]
            flagged_distances_km = enc_data["flagged_distances_km"]
            
            # 3. TCA Refinement
            tca_s, miss_distance_km = refine_tca(flagged_times_s, flagged_distances_km)
            
            # 4. Two-tier Pc check
            if miss_distance_km > self.PC_LOG_ONLY_THRESHOLD_KM:
                continue  # Completely discard
                
            # We need to interpolate the state at TCA
            base_epoch = enc_data["base_epoch"]
            
            # Extract the time series arrays for these two objects from the arrays directly!
            # Filter to valid steps only
            p_ok = arrays.ok_mask[idx1, :]
            s_ok = arrays.ok_mask[idx2, :]
            
            epoch_seconds = np.array([(ep - base_epoch).total_seconds() for ep in arrays.epochs])
            
            p_times = epoch_seconds[p_ok]
            p_pos = arrays.positions_eci_km[idx1, p_ok, :]
            p_vel = arrays.velocities_eci_km_s[idx1, p_ok, :]
            
            s_times = epoch_seconds[s_ok]
            s_pos = arrays.positions_eci_km[idx2, s_ok, :]
            s_vel = arrays.velocities_eci_km_s[idx2, s_ok, :]
            
            # Slice a 5-point window around TCA to make CubicSpline interpolation instant
            p_c_idx = np.argmin(np.abs(p_times - tca_s))
            s_c_idx = np.argmin(np.abs(s_times - tca_s))
            p_slice = slice(max(0, p_c_idx - 2), p_c_idx + 3)
            s_slice = slice(max(0, s_c_idx - 2), s_c_idx + 3)
            
            pos1, vel1 = interpolate_state_at_tca(
                p_times[p_slice], p_pos[p_slice], p_vel[p_slice], tca_s
            )
            pos2, vel2 = interpolate_state_at_tca(
                s_times[s_slice], s_pos[s_slice], s_vel[s_slice], tca_s
            )
            
            r_rel = pos2 - pos1
            v_rel = vel2 - vel1
            v_rel_norm = float(np.linalg.norm(v_rel))
            
            # Find closest timestep to use as base for covariance and metadata
            step_idx = np.argmin(np.abs(epoch_seconds - tca_s))
            
            # Use the escape hatch to build the actual objects for the encounter frame
            p_closest = arrays.to_propagated_state(idx1, step_idx)
            s_closest = arrays.to_propagated_state(idx2, step_idx)
            
            # Extract position covariances
            cov1 = extract_position_covariance(p_closest.covariance_array())
            cov2 = extract_position_covariance(s_closest.covariance_array())
            cov_pos_combined = cov1 + cov2
            
            combined_radius_km = p_closest.hard_body_radius_km + s_closest.hard_body_radius_km
            
            encounter = EncounterGeometry(
                primary_state=p_closest,
                secondary_state=s_closest,
                tca=base_epoch + timedelta(seconds=tca_s),
                relative_position_eci=r_rel,
                relative_velocity_eci=v_rel,
                miss_distance_km=miss_distance_km,
                relative_speed_km_s=v_rel_norm,
                combined_covariance_eci=cov_pos_combined,
                combined_hard_body_radius_km=combined_radius_km
            )
            
            if miss_distance_km > self.PC_COMPUTE_THRESHOLD_KM:
                # Log only
                pc_result = PcResult(pc=0.0, method=PcMethod.FOSTER_2D)
            else:
                # 5. Full Pc computation path
                # Encounter frame transform
                rotation = compute_encounter_frame(r_rel, v_rel)
                b_vector, cov_enc = project_to_encounter_plane(r_rel, cov_pos_combined, rotation)
                
                encounter.rotation_matrix = rotation
                encounter.relative_position_enc = b_vector
                encounter.combined_covariance_enc = cov_enc
                
                # Compute Pc
                pc_result = self.pc_engine.compute_pc(encounter)
                
            events.append(self._package_event(encounter, pc_result))
            
        logger.info(f"Pipeline finished. Produced {len(events)} conjunction events.")
        return events
        
    def _package_event(self, encounter: EncounterGeometry, pc_result: PcResult) -> ConjunctionEvent:
        """Package internal data structures into the public ConjunctionEvent contract."""
        
        validity = ValidityFlags(
            covariance_valid=(encounter.combined_covariance_enc is not None),
            relative_velocity_sufficient=(encounter.relative_speed_km_s * 1000 >= PC.FOSTER_MIN_VREL_MS),
            encounter_duration_short=True,
            covariance_positive_definite=True
        )
        if encounter.combined_covariance_enc is not None:
            eig = np.linalg.eigvalsh(encounter.combined_covariance_enc)
            if np.min(eig) < PC.COVARIANCE_SINGULARITY_TOL:
                validity.covariance_positive_definite = False
                
        # Optional fields might be None if we skipped frame transform (Log Only path)
        rel_pos_enc = encounter.relative_position_enc.tolist() if encounter.relative_position_enc is not None else None
        cov_enc = encounter.combined_covariance_enc.tolist() if encounter.combined_covariance_enc is not None else None

        return ConjunctionEvent(
            primary_id=encounter.primary_state.object_id,
            secondary_id=encounter.secondary_state.object_id,
            tca=encounter.tca,
            miss_distance_km=encounter.miss_distance_km,
            relative_velocity_km_s=encounter.relative_speed_km_s,
            relative_position_enc=rel_pos_enc,
            combined_covariance_enc_2x2=cov_enc,
            pc=pc_result.pc,
            pc_method=pc_result.method,
            pc_confidence_lower=pc_result.confidence_lower,
            pc_confidence_upper=pc_result.confidence_upper,
            combined_hard_body_radius_km=encounter.combined_hard_body_radius_km,
            primary_object_type=encounter.primary_state.object_type,
            secondary_object_type=encounter.secondary_state.object_type,
            validity_flags=validity
        )
