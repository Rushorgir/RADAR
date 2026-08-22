"""
Unit tests for the TCA refiner.
"""

import numpy as np
import pytest

from src.conjunction.screening.tca_refiner import refine_tca, interpolate_state_at_tca


def test_refine_tca_basic_parabola():
    # A simple parabola where min is at t=1.5
    times = np.array([0.0, 1.0, 2.0, 3.0])
    # Distances for y = (x - 1.5)^2 + 10
    distances = (times - 1.5)**2 + 10.0
    
    tca_s, miss_dist = refine_tca(times, distances)
    
    assert tca_s == pytest.approx(1.5, abs=1e-3)
    assert miss_dist == pytest.approx(10.0, abs=1e-3)


def test_refine_tca_too_few_points():
    times = np.array([0.0, 1.0])
    distances = np.array([20.0, 15.0])
    
    tca_s, miss_dist = refine_tca(times, distances)
    # Should just return the min point
    assert tca_s == 1.0
    assert miss_dist == 15.0


def test_interpolate_state_at_tca():
    times = np.array([0.0, 1.0, 2.0])
    # Position changing linearly
    positions = np.array([
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [20.0, 0.0, 0.0]
    ])
    # Velocity constant
    velocities = np.array([
        [10.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 0.0, 0.0]
    ])
    
    pos, vel = interpolate_state_at_tca(times, positions, velocities, tca_s=0.5)
    
    assert pos[0] == pytest.approx(5.0)
    assert vel[0] == pytest.approx(10.0)
