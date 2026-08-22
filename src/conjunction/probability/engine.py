from __future__ import annotations

"""
Probability of Collision (Pc) Engine

Auto-selects between Foster's 2D analytical method (primary) and Monte Carlo (fallback).
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from loguru import logger

from src.conjunction.models.encounter import EncounterGeometry, extract_position_covariance
from src.shared.interfaces.contracts import PcMethod
from src.conjunction.probability.foster_2d import foster_2d_pc
from src.conjunction.probability.monte_carlo import monte_carlo_pc
from src.shared.constants.physical import PC


@dataclass
class PcResult:
    pc: float
    method: PcMethod
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None


class PcEngine:
    """
    Computes Probability of Collision, automatically falling back to Monte Carlo
    if Foster's 2D method assumptions are violated or if numerical errors occur.
    """
    
    def compute_pc(self, encounter: EncounterGeometry) -> PcResult:
        """Compute the Pc for the given encounter geometry."""
        # Check Foster validity conditions
        if self._should_use_foster(encounter):
            try:
                pc = foster_2d_pc(
                    encounter.relative_position_enc,
                    encounter.combined_covariance_enc,
                    encounter.combined_hard_body_radius_km,
                )
                logger.debug(f"Computed Pc via Foster 2D: {pc:.2e}")
                return PcResult(pc=pc, method=PcMethod.FOSTER_2D)
            except (ValueError, np.linalg.LinAlgError) as e:
                logger.warning(f"Foster 2D failed ({e}). Falling back to Monte Carlo.")
                pass  # Fall through to Monte Carlo
        else:
            logger.debug("Foster 2D conditions not met. Using Monte Carlo fallback.")
        
        # Monte Carlo fallback
        cov1_pos = extract_position_covariance(encounter.primary_state.covariance_array())
        cov2_pos = extract_position_covariance(encounter.secondary_state.covariance_array())
        
        pc, lower, upper = monte_carlo_pc(
            r1=encounter.primary_state.position_array(),
            r2=encounter.secondary_state.position_array(),
            cov1_pos=cov1_pos,
            cov2_pos=cov2_pos,
            combined_radius_km=encounter.combined_hard_body_radius_km
        )
        logger.debug(f"Computed Pc via Monte Carlo: {pc:.2e}")
        return PcResult(
            pc=pc, 
            method=PcMethod.MONTE_CARLO,
            confidence_lower=lower, 
            confidence_upper=upper
        )
    
    def _should_use_foster(self, enc: EncounterGeometry) -> bool:
        """Check if Foster's 2D assumptions hold."""
        v_rel_ms = enc.relative_speed_km_s * 1000
        if v_rel_ms < PC.FOSTER_MIN_VREL_MS:
            return False
            
        if enc.combined_covariance_enc is None:
            return False
            
        # Check for degenerate covariance in encounter plane
        eigenvalues = np.linalg.eigvalsh(enc.combined_covariance_enc)
        if np.min(eigenvalues) < PC.COVARIANCE_SINGULARITY_TOL:
            return False
            
        return True
