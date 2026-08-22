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


def test_refine_tca_clamps_spline_undershoot_to_zero():
    # A cubic spline isn't constrained to stay within its sample points'
    # range between knots -- a sharp, fast flyby (real sample distances all
    # positive, one very close to zero) can make the interpolated curve dip
    # slightly negative right at the minimum even though nothing physical
    # ever measured a negative distance. Reproduced directly: this exact
    # set of points drives scipy's minimize_scalar to ~-0.045 km before
    # clamping.
    times = np.array([0.0, 60.0, 120.0, 180.0, 240.0])
    distances = np.array([40.0, 5.0, 0.3, 4.0, 45.0])

    tca_s, miss_dist = refine_tca(times, distances)

    assert miss_dist >= 0.0
    assert miss_dist == pytest.approx(0.0, abs=1e-6)
    assert 120.0 < tca_s < 180.0  # still lands near the true close-approach sample


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
