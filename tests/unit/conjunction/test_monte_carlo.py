"""
Unit tests for the Monte Carlo fallback Pc method.
"""

import numpy as np
import pytest

from src.conjunction.probability.monte_carlo import monte_carlo_pc


def test_monte_carlo_head_on():
    # Primary at origin
    r1 = np.array([0.0, 0.0, 0.0])
    cov1 = np.diag([1.0, 1.0, 1.0])
    
    # Secondary exactly at origin (perfect head-on collision point)
    r2 = np.array([0.0, 0.0, 0.0])
    cov2 = np.diag([1.0, 1.0, 1.0])
    
    radius = 1.0  # Large radius to ensure we get plenty of hits
    
    pc, lower, upper = monte_carlo_pc(r1, r2, cov1, cov2, radius, seed=42)
    
    assert pc > 0.0
    assert pc > lower
    assert pc < upper
    assert lower >= 0.0
    assert upper <= 1.0

def test_monte_carlo_clear_miss():
    # Primary at origin
    r1 = np.array([0.0, 0.0, 0.0])
    cov1 = np.diag([1.0, 1.0, 1.0])
    
    # Secondary far away
    r2 = np.array([100.0, 0.0, 0.0])
    cov2 = np.diag([1.0, 1.0, 1.0])
    
    radius = 0.015
    
    pc, lower, upper = monte_carlo_pc(r1, r2, cov1, cov2, radius, seed=42)
    
    # Should get exactly 0 hits
    assert pc == 0.0
    assert lower == 0.0
    assert upper > 0.0  # Wilson interval upper bound is always positive even with 0 hits
