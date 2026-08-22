"""Unit tests for src.propagation.covariance (Owner: Anas)."""

from __future__ import annotations

import numpy as np
import pytest

from src.propagation.covariance import DEFAULT_SIGMA_MODELS, RICSigmaModel, estimate_covariance_6x6, is_positive_definite
from src.shared.frames.transforms import StateVector
from src.shared.interfaces.contracts import ObjectType

ISS_LIKE_STATE = StateVector.from_lists([6161.10, -2866.07, -15.95], [2.01, 4.32, 6.00])


class TestRICSigmaModel:
    def test_sigmas_grow_with_time(self):
        model = RICSigmaModel()
        pos0, vel0 = model.sigmas_at(0.0)
        pos24, vel24 = model.sigmas_at(24.0)
        assert np.all(pos24 > pos0)
        assert np.all(vel24 > vel0)

    def test_negative_time_clamped_to_zero(self):
        model = RICSigmaModel()
        pos_neg, vel_neg = model.sigmas_at(-5.0)
        pos_zero, vel_zero = model.sigmas_at(0.0)
        np.testing.assert_allclose(pos_neg, pos_zero)
        np.testing.assert_allclose(vel_neg, vel_zero)

    def test_intrack_grows_fastest(self):
        model = RICSigmaModel()
        pos0, _ = model.sigmas_at(0.0)
        pos_t, _ = model.sigmas_at(10.0)
        growth = pos_t - pos0
        assert growth[1] > growth[0]  # in-track > radial
        assert growth[1] > growth[2]  # in-track > cross-track


class TestEstimateCovariance6x6:
    def test_returns_6x6_symmetric_matrix(self):
        cov = estimate_covariance_6x6(ISS_LIKE_STATE, hours_since_epoch=1.0, object_type=ObjectType.PAYLOAD)
        assert cov.shape == (6, 6)
        np.testing.assert_allclose(cov, cov.T, atol=1e-12)

    def test_is_positive_definite_for_realistic_inputs(self):
        cov = estimate_covariance_6x6(ISS_LIKE_STATE, hours_since_epoch=12.0, object_type=ObjectType.DEBRIS)
        assert is_positive_definite(cov)

    def test_uncertainty_grows_over_propagation_horizon(self):
        cov0 = estimate_covariance_6x6(ISS_LIKE_STATE, 0.0, ObjectType.DEBRIS)
        cov72 = estimate_covariance_6x6(ISS_LIKE_STATE, 72.0, ObjectType.DEBRIS)
        assert np.trace(cov72[:3, :3]) > np.trace(cov0[:3, :3])

    def test_debris_has_wider_uncertainty_than_payload_at_same_epoch(self):
        cov_payload = estimate_covariance_6x6(ISS_LIKE_STATE, 24.0, ObjectType.PAYLOAD)
        cov_debris = estimate_covariance_6x6(ISS_LIKE_STATE, 24.0, ObjectType.DEBRIS)
        assert np.trace(cov_debris[:3, :3]) > np.trace(cov_payload[:3, :3])

    def test_custom_sigma_model_is_respected(self):
        tiny_model = RICSigmaModel(
            sigma_radial_km0=1e-6, sigma_intrack_km0=1e-6, sigma_crosstrack_km0=1e-6,
            growth_radial_km_per_hr=0, growth_intrack_km_per_hr=0, growth_crosstrack_km_per_hr=0,
        )
        cov = estimate_covariance_6x6(ISS_LIKE_STATE, 100.0, sigma_model=tiny_model)
        assert np.trace(cov[:3, :3]) == pytest.approx(3e-12, rel=1e-3)

    def test_all_object_types_have_a_default_model(self):
        for object_type in ObjectType:
            assert object_type in DEFAULT_SIGMA_MODELS


class TestIsPositiveDefinite:
    def test_identity_is_positive_definite(self):
        assert is_positive_definite(np.eye(6))

    def test_zero_matrix_is_not_positive_definite(self):
        assert not is_positive_definite(np.zeros((6, 6)) - np.eye(6) * 1e-6)
