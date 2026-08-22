"""
Monte Carlo Fallback for Probability of Collision (Pc)

Uses a vectorized sampling approach to estimate Pc when Foster's 2D analytical method cannot be used
(e.g., due to low relative velocity or degenerate covariance).
"""

from typing import Tuple, Optional
import numpy as np
import scipy.stats

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
        combined_radius_km: combined hard-body radius R_c
        confidence: Confidence interval level (default 0.95)
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (pc_estimate, pc_lower_bound, pc_upper_bound)
    """
    rng = np.random.default_rng(seed)
    
    # Phase 1: Initial sampling
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
    """Run a single vectorized Monte Carlo simulation with n samples."""
    # Ensure covariance matrices are symmetric and semi-positive definite
    # by adding a tiny jitter to the diagonal
    cov1_safe = cov1 + np.eye(3) * 1e-12
    cov2_safe = cov2 + np.eye(3) * 1e-12
    
    # Vectorized sampling
    samples_r1 = rng.multivariate_normal(r1, cov1_safe, size=n, method='eigh')
    samples_r2 = rng.multivariate_normal(r2, cov2_safe, size=n, method='eigh')
    
    # Vectorized distance computation
    diffs = samples_r1 - samples_r2
    distances = np.linalg.norm(diffs, axis=1)
    
    # Count collisions
    n_collisions = int(np.sum(distances <= radius))
    pc = n_collisions / n
    
    # Wilson score confidence interval for binomial proportion
    z = scipy.stats.norm.ppf(1 - (1 - confidence) / 2)
    denom = 1 + z**2 / n
    center = (pc + z**2 / (2 * n)) / denom
    half_width = z * np.sqrt(pc * (1 - pc) / n + z**2 / (4 * n**2)) / denom
    
    return pc, max(0.0, float(center - half_width)), min(1.0, float(center + half_width))
