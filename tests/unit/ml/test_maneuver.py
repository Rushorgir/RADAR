import pytest
import math
import sys
import os

from src.maneuver.optimizer import ManeuverOptimizer, ManeuverAdvisoryResult

def test_maneuver_no_maneuver_needed():
    optimizer = ManeuverOptimizer(target_safety_distance_km=10.0)
    result = optimizer.calculate_advisory(15.0, 2.0, 7.5)
    assert result is None

def test_maneuver_too_late():
    optimizer = ManeuverOptimizer(target_safety_distance_km=10.0)
    result = optimizer.calculate_advisory(5.0, 0.0, 7.5)
    assert result is None
    result = optimizer.calculate_advisory(5.0, -1.0, 7.5)
    assert result is None

def test_maneuver_calculation():
    optimizer = ManeuverOptimizer(target_safety_distance_km=10.0, satellite_mass_kg=500.0)
    result = optimizer.calculate_advisory(5.0, 2.0, 7.5)
    assert result is not None
    assert result.burn_direction == "ALONG_TRACK"
    assert result.new_miss_distance_km == 10.0
    
    expected_dv = 5000.0 / (3.0 * 172800.0)
    assert math.isclose(result.delta_v_m_s, round(expected_dv, 4), abs_tol=1e-4)
    
    assert result.risk_reduction_factor == 4.0
    assert result.fuel_cost_estimate_kg > 0.0
