"""
Unit tests for PcEngine auto-selector logic and fallbacks.
"""

from datetime import datetime, timezone
import numpy as np
import pytest

from src.conjunction.models.encounter import EncounterGeometry
from src.conjunction.probability.engine import PcEngine
from src.shared.interfaces.contracts import PropagatedState, ObjectType, PcMethod


def _make_encounter(
    rel_speed_km_s: float = 10.0,
    enc_cov: np.ndarray = np.eye(2),
    rel_pos_enc: np.ndarray = np.array([0.01, 0.01]),
    combined_radius_km: float = 0.015,
) -> EncounterGeometry:
    s1 = PropagatedState(
        object_id="P1",
        epoch=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        position_eci_km=[7000.0, 0.0, 0.0],
        velocity_eci_km_s=[0.0, 7.5, 0.0],
        covariance_6x6_km_and_kms=np.eye(6).tolist(),
        hard_body_radius_km=0.0075,
        cross_section_area_m2=1.0,
        object_type=ObjectType.PAYLOAD,
    )
    s2 = PropagatedState(
        object_id="P2",
        epoch=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        position_eci_km=[7000.0, 0.02, 0.0],
        velocity_eci_km_s=[0.0, -7.5, 0.0],
        covariance_6x6_km_and_kms=np.eye(6).tolist(),
        hard_body_radius_km=0.0075,
        cross_section_area_m2=1.0,
        object_type=ObjectType.DEBRIS,
    )

    return EncounterGeometry(
        primary_state=s1,
        secondary_state=s2,
        tca=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        relative_position_eci=np.array([0.0, 0.02, 0.0]),
        relative_velocity_eci=np.array([0.0, -15.0, 0.0]),
        miss_distance_km=0.02,
        relative_speed_km_s=rel_speed_km_s,
        combined_covariance_eci=np.eye(3) * 2.0,
        combined_hard_body_radius_km=combined_radius_km,
        rotation_matrix=np.eye(3),
        relative_position_enc=rel_pos_enc,
        combined_covariance_enc=enc_cov,
    )


def test_pc_engine_selects_foster_normal_case():
    engine = PcEngine()
    enc = _make_encounter(rel_speed_km_s=10.0, enc_cov=np.eye(2))

    res = engine.compute_pc(enc)
    assert res.method == PcMethod.FOSTER_2D
    assert 0.0 <= res.pc <= 1.0
    assert res.confidence_lower is None
    assert res.confidence_upper is None


def test_pc_engine_falls_back_on_low_relative_velocity():
    engine = PcEngine()
    # 0.05 km/s = 50 m/s < 100 m/s threshold
    enc = _make_encounter(rel_speed_km_s=0.05, enc_cov=np.eye(2))

    res = engine.compute_pc(enc)
    assert res.method == PcMethod.MONTE_CARLO
    assert 0.0 <= res.pc <= 1.0
    assert res.confidence_lower is not None
    assert res.confidence_upper is not None
    assert res.confidence_lower <= res.pc <= res.confidence_upper


def test_pc_engine_falls_back_on_singular_covariance():
    engine = PcEngine()
    # Degenerate covariance
    singular_cov = np.array([[1.0, 1.0], [1.0, 1.0]])
    enc = _make_encounter(rel_speed_km_s=10.0, enc_cov=singular_cov)

    res = engine.compute_pc(enc)
    assert res.method == PcMethod.MONTE_CARLO
    assert 0.0 <= res.pc <= 1.0


def test_pc_engine_falls_back_when_enc_cov_none():
    engine = PcEngine()
    enc = _make_encounter(rel_speed_km_s=10.0)
    enc.combined_covariance_enc = None

    res = engine.compute_pc(enc)
    assert res.method == PcMethod.MONTE_CARLO
    assert 0.0 <= res.pc <= 1.0
