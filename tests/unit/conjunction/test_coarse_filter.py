"""
Unit tests for the Stage 1 coarse filter.
"""
import numpy as np
import pytest

from src.conjunction.screening.coarse_filter import compute_altitude_bands, coarse_filter
from src.shared.constants.physical import EARTH


def test_compute_altitude_bands():
    r1 = EARTH.RADIUS_KM + 400.0
    r2 = EARTH.RADIUS_KM + 450.0
    
    positions = np.zeros((1, 2, 3))
    positions[0, 0] = [r1, 0.0, 0.0]
    positions[0, 1] = [0.0, r2, 0.0]
    
    ok_mask = np.ones((1, 2), dtype=bool)
    
    min_alts, max_alts = compute_altitude_bands(positions, ok_mask)
    assert min_alts[0] == pytest.approx(400.0)
    assert max_alts[0] == pytest.approx(450.0)


def test_coarse_filter_overlapping():
    r1 = EARTH.RADIUS_KM + 400.0
    r2 = EARTH.RADIUS_KM + 440.0
    
    positions = np.zeros((2, 1, 3))
    positions[0, 0] = [r1, 0.0, 0.0]
    positions[1, 0] = [r2, 0.0, 0.0]
    
    ok_mask = np.ones((2, 1), dtype=bool)
    object_ids = ["A", "B"]
    
    # Margin is 50. 
    # A band: [350, 450]
    # B band: [390, 490]
    pairs = coarse_filter(positions, ok_mask, object_ids, margin_km=50.0)
    assert len(pairs) == 1
    assert set(pairs[0]) == {"A", "B"}


def test_coarse_filter_non_overlapping():
    r1 = EARTH.RADIUS_KM + 400.0
    r2 = EARTH.RADIUS_KM + 600.0
    
    positions = np.zeros((2, 1, 3))
    positions[0, 0] = [r1, 0.0, 0.0]
    positions[1, 0] = [r2, 0.0, 0.0]
    
    ok_mask = np.ones((2, 1), dtype=bool)
    object_ids = ["A", "C"]
    
    # Margin is 50.
    # A band: [350, 450]
    # C band: [550, 650]
    pairs = coarse_filter(positions, ok_mask, object_ids, margin_km=50.0)
    assert len(pairs) == 0


def test_coarse_filter_multiple():
    r_a = EARTH.RADIUS_KM + 400.0
    r_b = EARTH.RADIUS_KM + 420.0
    r_c = EARTH.RADIUS_KM + 510.0
    
    positions = np.zeros((3, 1, 3))
    positions[0, 0] = [r_a, 0.0, 0.0]
    positions[1, 0] = [r_b, 0.0, 0.0]
    positions[2, 0] = [r_c, 0.0, 0.0]
    
    ok_mask = np.ones((3, 1), dtype=bool)
    object_ids = ["A", "B", "C"]
    
    # A band: [350, 450]
    # B band: [370, 470]
    # C band: [460, 560]
    # Overlaps: A-B, B-C
    pairs = coarse_filter(positions, ok_mask, object_ids, margin_km=50.0)
    assert len(pairs) == 2
    
    pairs_set = {tuple(sorted(p)) for p in pairs}
    assert ("A", "B") in pairs_set
    assert ("B", "C") in pairs_set
    assert ("A", "C") not in pairs_set

