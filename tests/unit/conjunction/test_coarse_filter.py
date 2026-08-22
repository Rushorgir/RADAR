"""
Unit tests for the Stage 1 coarse filter.
"""
from datetime import datetime, timezone
import pytest

from src.shared.interfaces.contracts import PropagatedState, ObjectType
from src.conjunction.screening.coarse_filter import compute_altitude_band, coarse_filter
from src.shared.constants.physical import EARTH


def _make_state(obj_id: str, x: float, y: float, z: float) -> PropagatedState:
    return PropagatedState(
        object_id=obj_id,
        epoch=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        position_eci_km=[x, y, z],
        velocity_eci_km_s=[0.0, 0.0, 0.0],
        hard_body_radius_km=0.015,
        cross_section_area_m2=1.0,
        object_type=ObjectType.PAYLOAD
    )


def test_compute_altitude_band():
    r1 = EARTH.RADIUS_KM + 400.0
    s1 = _make_state("A", r1, 0.0, 0.0)
    
    r2 = EARTH.RADIUS_KM + 450.0
    s2 = _make_state("A", 0.0, r2, 0.0)
    
    h_min, h_max = compute_altitude_band([s1, s2])
    assert h_min == pytest.approx(400.0)
    assert h_max == pytest.approx(450.0)


def test_coarse_filter_overlapping():
    r1 = EARTH.RADIUS_KM + 400.0
    s_a = [_make_state("A", r1, 0.0, 0.0)]
    
    r2 = EARTH.RADIUS_KM + 440.0
    s_b = [_make_state("B", r2, 0.0, 0.0)]
    
    all_states = {"A": s_a, "B": s_b}
    
    # Margin is 50. 
    # A band: [350, 450]
    # B band: [390, 490]
    pairs = coarse_filter(all_states, margin_km=50.0)
    assert len(pairs) == 1
    assert set(pairs[0]) == {"A", "B"}


def test_coarse_filter_non_overlapping():
    r1 = EARTH.RADIUS_KM + 400.0
    s_a = [_make_state("A", r1, 0.0, 0.0)]
    
    r3 = EARTH.RADIUS_KM + 600.0
    s_c = [_make_state("C", r3, 0.0, 0.0)]
    
    all_states = {"A": s_a, "C": s_c}
    
    # Margin is 50.
    # A band: [350, 450]
    # C band: [550, 650]
    pairs = coarse_filter(all_states, margin_km=50.0)
    assert len(pairs) == 0


def test_coarse_filter_multiple():
    r_a = EARTH.RADIUS_KM + 400.0
    r_b = EARTH.RADIUS_KM + 420.0
    r_c = EARTH.RADIUS_KM + 510.0
    
    all_states = {
        "A": [_make_state("A", r_a, 0.0, 0.0)],
        "B": [_make_state("B", r_b, 0.0, 0.0)],
        "C": [_make_state("C", r_c, 0.0, 0.0)],
    }
    
    # A band: [350, 450]
    # B band: [370, 470]
    # C band: [460, 560]
    # Overlaps: A-B, B-C
    pairs = coarse_filter(all_states, margin_km=50.0)
    assert len(pairs) == 2
    
    pairs_set = {tuple(sorted(p)) for p in pairs}
    assert ("A", "B") in pairs_set
    assert ("B", "C") in pairs_set
    assert ("A", "C") not in pairs_set
