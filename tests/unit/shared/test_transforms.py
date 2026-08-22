"""
Unit tests for src.shared.frames.transforms.

This module is jointly owned (src/shared/), but since Anas (AI-1) is the one
populating it as part of the "coordinate transforms" deliverable, its tests
live alongside the other AI-1 unit tests here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from src.shared.frames.transforms import (
    StateVector,
    apply_rotation_batch,
    ecef_to_eci,
    ecef_to_geodetic,
    eci_to_ecef,
    eci_to_ric,
    eci_to_teme,
    ric_rotation_matrix,
    ric_to_eci,
    teme_to_eci,
    teme_to_eci_batch,
    teme_to_eci_rotation_matrices,
)

EPOCH = datetime(2026, 8, 22, 0, 0, 0, tzinfo=timezone.utc)

# Approximate ISS TEME state (km, km/s).
ISS_TEME = StateVector.from_lists([6161.10, -2866.07, -15.95], [2.01, 4.32, 6.00])


def _two_body_accel(r: np.ndarray, mu: float = 398600.4418) -> np.ndarray:
    return -mu * r / np.linalg.norm(r) ** 3


def _rk4_step(r: np.ndarray, v: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    def deriv(r, v):
        return v, _two_body_accel(r)

    k1r, k1v = deriv(r, v)
    k2r, k2v = deriv(r + 0.5 * dt * k1r, v + 0.5 * dt * k1v)
    k3r, k3v = deriv(r + 0.5 * dt * k2r, v + 0.5 * dt * k2v)
    k4r, k4v = deriv(r + dt * k3r, v + dt * k3v)
    r2 = r + dt / 6 * (k1r + 2 * k2r + 2 * k3r + k4r)
    v2 = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
    return r2, v2


class TestStateVector:
    def test_accepts_lists_and_flattens_to_shape_3(self):
        sv = StateVector(position_km=[1, 2, 3], velocity_km_s=[4, 5, 6])
        assert sv.position_km.shape == (3,)
        assert sv.velocity_km_s.shape == (3,)

    def test_from_lists_and_as_tuple_roundtrip(self):
        sv = StateVector.from_lists([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        pos, vel = sv.as_tuple()
        assert pos == [1.0, 2.0, 3.0]
        assert vel == [4.0, 5.0, 6.0]


class TestTemeEciRoundtrip:
    def test_teme_to_eci_preserves_vector_magnitude(self):
        eci = teme_to_eci(ISS_TEME, EPOCH)
        assert np.linalg.norm(eci.position_km) == pytest.approx(np.linalg.norm(ISS_TEME.position_km), rel=1e-6)

    def test_roundtrip_teme_eci_teme_is_identity(self):
        eci = teme_to_eci(ISS_TEME, EPOCH)
        back = eci_to_teme(eci, EPOCH)
        np.testing.assert_allclose(back.position_km, ISS_TEME.position_km, atol=1e-6)
        np.testing.assert_allclose(back.velocity_km_s, ISS_TEME.velocity_km_s, atol=1e-9)

    def test_batch_matches_scalar_for_identical_epochs(self):
        n = 4
        positions = np.tile(ISS_TEME.position_km, (n, 1))
        velocities = np.tile(ISS_TEME.velocity_km_s, (n, 1))
        epochs = [EPOCH + timedelta(minutes=i) for i in range(n)]

        batch_pos, batch_vel = teme_to_eci_batch(positions, velocities, epochs)

        for i, epoch in enumerate(epochs):
            scalar = teme_to_eci(ISS_TEME, epoch)
            np.testing.assert_allclose(batch_pos[i], scalar.position_km, atol=1e-6)
            np.testing.assert_allclose(batch_vel[i], scalar.velocity_km_s, atol=1e-9)


class TestEciEcefRoundtrip:
    def test_roundtrip_eci_ecef_eci_is_identity(self):
        eci = teme_to_eci(ISS_TEME, EPOCH)
        ecef = eci_to_ecef(eci, EPOCH)
        back = ecef_to_eci(ecef, EPOCH)
        np.testing.assert_allclose(back.position_km, eci.position_km, atol=1e-6)
        np.testing.assert_allclose(back.velocity_km_s, eci.velocity_km_s, atol=1e-9)

    def test_ecef_position_magnitude_matches_eci(self):
        eci = teme_to_eci(ISS_TEME, EPOCH)
        ecef = eci_to_ecef(eci, EPOCH)
        assert np.linalg.norm(ecef.position_km) == pytest.approx(np.linalg.norm(eci.position_km), rel=1e-6)


class TestEcefToGeodetic:
    def test_point_on_equator_prime_meridian(self):
        earth_radius_km = 6378.137
        sv = StateVector.from_lists([earth_radius_km, 0.0, 0.0], [0.0, 0.0, 0.0])
        lat, lon, alt = ecef_to_geodetic(sv, EPOCH)
        assert lat == pytest.approx(0.0, abs=1e-6)
        assert lon == pytest.approx(0.0, abs=1e-6)
        assert alt == pytest.approx(0.0, abs=1e-3)

    def test_point_over_north_pole(self):
        sv = StateVector.from_lists([0.0, 0.0, 6500.0], [0.0, 0.0, 0.0])
        lat, _lon, _alt = ecef_to_geodetic(sv, EPOCH)
        assert lat == pytest.approx(90.0, abs=1e-3)


class TestRicFrame:
    def test_rotation_matrix_is_orthonormal(self):
        reference = StateVector.from_lists([7000.0, 0.0, 0.0], [0.0, 7.5, 1.0])
        Q = ric_rotation_matrix(reference)
        np.testing.assert_allclose(Q @ Q.T, np.eye(3), atol=1e-10)
        assert np.linalg.det(Q) == pytest.approx(1.0, abs=1e-10)

    def test_zero_position_raises(self):
        reference = StateVector.from_lists([0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        with pytest.raises(ValueError):
            ric_rotation_matrix(reference)

    def test_reference_relative_to_itself_is_origin(self):
        reference = StateVector.from_lists([7000.0, 0.0, 0.0], [0.0, 7.5, 1.0])
        result = eci_to_ric(reference, reference)
        np.testing.assert_allclose(result.position_km, [0, 0, 0], atol=1e-10)
        np.testing.assert_allclose(result.velocity_km_s, [0, 0, 0], atol=1e-10)

    def test_ric_roundtrip_is_identity(self):
        reference = StateVector.from_lists([7000.0, 0.0, 0.0], [0.0, 7.5, 1.0])
        target = StateVector.from_lists([7000.5, 2.0, 0.3], [0.001, 7.548, 1.0005])

        ric = eci_to_ric(target, reference)
        back = ric_to_eci(ric, reference)

        np.testing.assert_allclose(back.position_km, target.position_km, atol=1e-9)
        np.testing.assert_allclose(back.velocity_km_s, target.velocity_km_s, atol=1e-9)

    def test_ric_velocity_matches_finite_difference_two_body_propagation(self):
        """
        Regression test for the RIC transport-theorem formula: propagate chief and
        target a small dt forward under two-body dynamics and check the analytic
        RIC velocity matches the finite-difference derivative of RIC position.
        """
        r_c = np.array([7000.0, 0.0, 0.0])
        v_c = np.array([0.0, 7.5460491, 1.0])
        r_t = r_c + np.array([0.5, 2.0, 0.3])
        v_t = v_c + np.array([0.001, -0.002, 0.0005])

        chief = StateVector(position_km=r_c, velocity_km_s=v_c)
        target = StateVector(position_km=r_t, velocity_km_s=v_t)

        ric = eci_to_ric(target, chief)

        dt = 0.01
        r_c2, v_c2 = _rk4_step(r_c, v_c, dt)
        r_t2, v_t2 = _rk4_step(r_t, v_t, dt)
        chief2 = StateVector(position_km=r_c2, velocity_km_s=v_c2)
        target2 = StateVector(position_km=r_t2, velocity_km_s=v_t2)
        ric2 = eci_to_ric(target2, chief2)

        v_ric_fd = (ric2.position_km - ric.position_km) / dt
        np.testing.assert_allclose(ric.velocity_km_s, v_ric_fd, atol=1e-6)


class TestTemeToEciRotationMatrices:
    def test_disabling_decimation_matches_per_epoch_teme_to_eci(self):
        epochs = [EPOCH + timedelta(minutes=i) for i in range(5)]
        rotations = teme_to_eci_rotation_matrices(epochs, max_spacing_s=0)

        for i, epoch in enumerate(epochs):
            expected = teme_to_eci(ISS_TEME, epoch)
            got_pos, got_vel = apply_rotation_batch(
                rotations[i][None, :, :], ISS_TEME.position_km[None, :], ISS_TEME.velocity_km_s[None, :]
            )
            np.testing.assert_allclose(got_pos[0], expected.position_km, atol=1e-9)
            np.testing.assert_allclose(got_vel[0], expected.velocity_km_s, atol=1e-9)

    def test_decimation_is_a_close_approximation_of_the_exact_rotation(self):
        """
        Decimated (default max_spacing_s=300) rotations must stay extremely
        close to the exact per-epoch rotation -- centimeters of position
        error at most, per the module docstring's measured bound.
        """
        epochs = [EPOCH + timedelta(seconds=60 * i) for i in range(180)]  # 3 hours @ 60s

        exact = teme_to_eci_rotation_matrices(epochs, max_spacing_s=0)
        decimated = teme_to_eci_rotation_matrices(epochs, max_spacing_s=300.0)

        r = ISS_TEME.position_km
        pos_exact, _ = apply_rotation_batch(exact, np.tile(r, (len(epochs), 1)), np.tile(r, (len(epochs), 1)))
        pos_decimated, _ = apply_rotation_batch(decimated, np.tile(r, (len(epochs), 1)), np.tile(r, (len(epochs), 1)))

        position_error_km = np.linalg.norm(pos_exact - pos_decimated, axis=1)
        assert np.max(position_error_km) < 0.001  # < 1 meter, per the measured ~11cm/30min bound

    def test_decimation_reduces_number_of_distinct_matrices(self):
        epochs = [EPOCH + timedelta(seconds=60 * i) for i in range(180)]  # 3 hours @ 60s -> would be 180 exact samples
        decimated = teme_to_eci_rotation_matrices(epochs, max_spacing_s=300.0)
        distinct = {tuple(np.round(decimated[i].ravel(), 12)) for i in range(len(epochs))}
        assert len(distinct) < len(epochs)  # fewer unique matrices than timesteps -- decimation actually happened

    def test_single_epoch_does_not_crash(self):
        rotations = teme_to_eci_rotation_matrices([EPOCH], max_spacing_s=300.0)
        assert rotations.shape == (1, 3, 3)

    def test_two_epochs_does_not_crash(self):
        rotations = teme_to_eci_rotation_matrices([EPOCH, EPOCH + timedelta(hours=1)], max_spacing_s=300.0)
        assert rotations.shape == (2, 3, 3)
