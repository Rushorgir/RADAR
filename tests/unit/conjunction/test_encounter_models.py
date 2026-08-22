"""
Unit tests for EncounterGeometry data model and covariance extraction utilities.
"""

from datetime import datetime, timezone
import numpy as np
import pytest

from src.conjunction.models.encounter import (
    EncounterGeometry,
    extract_position_covariance,
    DEFAULT_POSITION_COVARIANCE_KM2,
)
from src.shared.interfaces.contracts import PropagatedState, ObjectType


def _make_dummy_state(obj_id: str, cov=None) -> PropagatedState:
    return PropagatedState(
        object_id=obj_id,
        epoch=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        position_eci_km=[7000.0, 0.0, 0.0],
        velocity_eci_km_s=[0.0, 7.5, 0.0],
        covariance_6x6_km_and_kms=cov,
        hard_body_radius_km=0.015,
        cross_section_area_m2=1.0,
        object_type=ObjectType.PAYLOAD,
    )


def test_extract_position_covariance_6x6():
    cov_6x6 = np.zeros((6, 6))
    cov_6x6[:3, :3] = np.diag([2.0, 3.0, 4.0])
    cov_6x6[3:, 3:] = np.eye(3) * 0.01

    pos_cov = extract_position_covariance(cov_6x6)
    assert pos_cov.shape == (3, 3)
    np.testing.assert_allclose(pos_cov, np.diag([2.0, 3.0, 4.0]))


def test_extract_position_covariance_3x3():
    cov_3x3 = np.diag([5.0, 6.0, 7.0])
    pos_cov = extract_position_covariance(cov_3x3)
    assert pos_cov.shape == (3, 3)
    np.testing.assert_allclose(pos_cov, cov_3x3)


def test_extract_position_covariance_none_fallback():
    pos_cov = extract_position_covariance(None)
    assert pos_cov.shape == (3, 3)
    np.testing.assert_allclose(pos_cov, DEFAULT_POSITION_COVARIANCE_KM2)


def test_extract_position_covariance_invalid_shape():
    invalid_cov = np.ones((4, 4))
    pos_cov = extract_position_covariance(invalid_cov)
    assert pos_cov.shape == (3, 3)
    np.testing.assert_allclose(pos_cov, DEFAULT_POSITION_COVARIANCE_KM2)


def test_encounter_geometry_instantiation():
    s1 = _make_dummy_state("SAT-1")
    s2 = _make_dummy_state("SAT-2")
    tca = datetime(2026, 8, 22, 12, 5, tzinfo=timezone.utc)
    rel_pos = np.array([0.1, 0.2, 0.3])
    rel_vel = np.array([0.0, 10.0, 0.0])
    comb_cov = np.eye(3) * 2.0

    enc = EncounterGeometry(
        primary_state=s1,
        secondary_state=s2,
        tca=tca,
        relative_position_eci=rel_pos,
        relative_velocity_eci=rel_vel,
        miss_distance_km=float(np.linalg.norm(rel_pos)),
        relative_speed_km_s=10.0,
        combined_covariance_eci=comb_cov,
        combined_hard_body_radius_km=0.03,
    )

    assert enc.primary_state.object_id == "SAT-1"
    assert enc.secondary_state.object_id == "SAT-2"
    assert enc.miss_distance_km == pytest.approx(np.sqrt(0.1**2 + 0.2**2 + 0.3**2))
    assert enc.rotation_matrix is None
    assert enc.relative_position_enc is None
    assert enc.combined_covariance_enc is None
