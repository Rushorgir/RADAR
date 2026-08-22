from __future__ import annotations

"""
Foster's 2D Method for Probability of Collision (Pc)

Computes Pc by integrating the 2D Gaussian probability density (representing combined position uncertainty)
over a circular collision cross-section in the encounter plane.
"""

import numpy as np
from scipy.integrate import dblquad

from src.shared.constants.physical import PC


def foster_2d_pc(
    b_vector: np.ndarray,
    cov_enc: np.ndarray,
    combined_radius_km: float,
) -> float:
    """
    Compute Probability of Collision using Foster's 2D analytical method.
    
    Args:
        b_vector: (2,) miss vector in the encounter plane (km).
        cov_enc: (2,2) combined covariance matrix in the encounter plane (km^2).
        combined_radius_km: combined hard-body radius R_A + R_B (km).
        
    Returns:
        Probability of collision (float between 0 and 1).
        
    Raises:
        ValueError: if the covariance is degenerate (requires Monte Carlo fallback).
    """
    # Eigendecompose covariance for numerical stability (transform to principal axes)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_enc)
    sigma1_sq, sigma2_sq = eigenvalues
    
    # Check for degenerate covariance
    if sigma1_sq < PC.COVARIANCE_SINGULARITY_TOL or sigma2_sq < PC.COVARIANCE_SINGULARITY_TOL:
        raise ValueError("Degenerate covariance — use Monte Carlo fallback")
        
    # Transform miss vector to principal axes
    b_prime = eigenvectors.T @ b_vector
    
    # 2D Gaussian PDF in principal frame
    def integrand(y, x):
        exp_term = (
            (x - b_prime[0])**2 / (2 * sigma1_sq)
            + (y - b_prime[1])**2 / (2 * sigma2_sq)
        )
        return np.exp(-exp_term) / (2 * np.pi * np.sqrt(sigma1_sq * sigma2_sq))
        
    # Integration bounds: circle of radius R_c
    def y_lower(x):
        # max(0, ...) protects against floating point issues causing negative square roots
        val = combined_radius_km**2 - x**2
        if val <= 0:
            return 0.0
        return -np.sqrt(val)
        
    def y_upper(x):
        val = combined_radius_km**2 - x**2
        if val <= 0:
            return 0.0
        return np.sqrt(val)
        
    # Perform numerical integration
    pc, _error = dblquad(
        integrand,
        -combined_radius_km, combined_radius_km,
        y_lower, y_upper,
        epsabs=1e-12, epsrel=1e-10,
    )
    
    return float(pc)
