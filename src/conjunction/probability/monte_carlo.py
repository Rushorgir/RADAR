from __future__ import annotations

"""
Monte Carlo Fallback for Probability of Collision (Pc)

Uses a high-performance vectorized relative-state sampling approach to estimate Pc when Foster's 2D analytical method
cannot be used (e.g., due to low relative velocity or degenerate covariance).
"""

from typing import Tuple, Optional
import numpy as np
from scipy.special import ndtri

from src.shared.constants.physical import PC


def monte_carlo_pc(
    r1: np.ndarray,
    r2: np.ndarray,
    cov1_pos: np.ndarray,
    cov2_pos: np.ndarray,
    combined_radius_km: float,
    confidence: float = PC.MONTE_CARLO_CONFIDENCE,
    seed: Optional[int] = 42,
) -> Tuple[float, float, float]:
    """
    Monte Carlo Pc estimation with adaptive sampling (10^5 -> 10^6).
    
    Args:
        r1: (3,) primary position km
        r2: (3,) secondary position km
        cov1_pos: (3,3) primary position covariance
        cov2_pos: (3,3) secondary position covariance
        combined_radius_km: combined hard-body radius R_c (km)
        confidence: Confidence interval level (default 0.95)
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (pc_estimate, pc_lower_bound, pc_upper_bound)
    """
    rng = np.random.default_rng(seed)
    
    # Phase 1: Initial sampling (10^5 samples)
    n_samples = PC.MONTE_CARLO_SAMPLES
    pc, lower, upper = _run_mc(
        rng, r1, r2, cov1_pos, cov2_pos, combined_radius_km, n_samples, confidence
    )
    
    # Phase 2: Escalate to 10^6 if zero hits were found
    if pc == 0.0 and n_samples < 1_000_000:
        n_samples = 1_000_000
        pc, lower, upper = _run_mc(
            rng, r1, r2, cov1_pos, cov2_pos, combined_radius_km, n_samples, confidence
        )
        
    return pc, lower, upper


def _run_mc(
    rng: np.random.Generator,
    r1: np.ndarray,
    r2: np.ndarray,
    cov1: np.ndarray,
    cov2: np.ndarray,
    radius: float,
    n: int,
    confidence: float,
) -> Tuple[float, float, float]:
    """
    Run a single vectorized relative-state Monte Carlo simulation with n samples.
    
    Since r1 ~ N(r1, cov1) and r2 ~ N(r2, cov2),
    relative position delta_r = r1 - r2 ~ N(r1 - r2, cov1 + cov2).
    """
    diff_mean = r1 - r2
    cov_combined = cov1 + cov2 + np.eye(3) * 1e-12
    
    # Efficient Cholesky or spectral square-root factor
    try:
        L = np.linalg.cholesky(cov_combined)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(cov_combined)
        eigvals = np.maximum(eigvals, 1e-12)
        L = eigvecs * np.sqrt(eigvals)
        
    # Generate (n, 3) standard normal numbers and project
    z_std = rng.standard_normal((n, 3))
    samples_diff = z_std @ L.T + diff_mean
    
    # Fast squared distance evaluation
    dist_sq = np.sum(samples_diff**2, axis=1)
    
    # Count collisions
    n_collisions = int(np.sum(dist_sq <= radius**2))
    pc = n_collisions / n
    
    # Wilson score confidence interval for binomial proportion
    p_alpha = 1.0 - (1.0 - confidence) / 2.0
    z = float(ndtri(p_alpha))
    denom = 1.0 + z**2 / n
    center = (pc + z**2 / (2.0 * n)) / denom
    half_width = z * np.sqrt(pc * (1.0 - pc) / n + z**2 / (4.0 * n**2)) / denom
    
    if pc == 0.0:
        lower_bound = 0.0
        upper_bound = min(1.0, float(center + half_width))
    elif pc == 1.0:
        lower_bound = max(0.0, float(center - half_width))
        upper_bound = 1.0
    else:
        lower_bound = max(0.0, float(center - half_width))
        upper_bound = min(1.0, float(center + half_width))
        
    return pc, lower_bound, upper_bound
