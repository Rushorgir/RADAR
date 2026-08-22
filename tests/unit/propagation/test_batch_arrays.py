"""Unit tests for src.propagation.batch_arrays (Owner: Anas)."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.batch_arrays import propagate_catalog_arrays
from src.propagation.covariance import is_positive_definite

ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

DEBRIS_LINE1 = "1 34427U 93036SX  26233.50000000  .00001234  00000+0  12345-3 0  9999"
DEBRIS_LINE2 = "2 34427  74.0300 100.0000 0010000 100.0000 260.0000 14.20000000123459"


def _dataset():
    iss = parse_tle_lines(ISS_LINE1, ISS_LINE2, name="ISS (ZARYA)")
    debris = parse_tle_lines(DEBRIS_LINE1, DEBRIS_LINE2, name="COSMOS 2251 DEB")
    return [iss, debris]


class TestPropagateCatalogArrays:
    def test_empty_input_raises(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        with pytest.raises(ValueError):
            propagate_catalog_arrays([], start, start + timedelta(hours=1), step_s=60.0)

    def test_shapes_match_object_and_timestep_counts(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=60.0)

        assert arrays.n_objects == 2
        assert arrays.n_steps == 61  # 1h / 60s + 1
        assert arrays.positions_eci_km.shape == (2, 61, 3)
        assert arrays.velocities_eci_km_s.shape == (2, 61, 3)
        assert arrays.ok_mask.shape == (2, 61)
        assert arrays.covariances_eci.shape == (2, 61, 6, 6)

    def test_object_ids_and_order_match_input(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=60.0)
        assert arrays.object_ids == ["25544", "34427"]
        assert arrays.object_index("34427") == 1

    def test_all_steps_ok_for_healthy_objects(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=60.0)
        assert arrays.ok_mask.all()

    def test_positions_are_finite_and_leo_scale(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0)
        assert np.all(np.isfinite(arrays.positions_eci_km))
        radii = np.linalg.norm(arrays.positions_eci_km, axis=2)
        assert np.all((radii > 6500) & (radii < 8000))

    def test_covariance_is_positive_definite(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0)
        for obj_idx in range(arrays.n_objects):
            for step_idx in range(arrays.n_steps):
                assert is_positive_definite(arrays.covariances_eci[obj_idx, step_idx])

    def test_covariance_is_realistic_magnitude_for_every_object_type(self):
        """
        Regression test: the per-type grouping in propagate_catalog_arrays used
        to compare a numpy object-array of ObjectType (a `(str, Enum)` hybrid)
        against an enum *scalar* with `==`. numpy silently mis-coerces a
        (str, Enum) scalar through np.asarray before comparing, which produced
        an all-False result even for objects that really were that type --
        every group's mask ended up empty, so estimate_covariance_6x6_batch
        was *never actually called*, and every object's covariance silently
        stayed at its np.zeros(...) initial value.

        test_covariance_is_positive_definite above didn't catch this: it uses
        is_positive_definite's 1e-12 epsilon padding, which makes even an
        exact zero matrix "pass" as positive-definite. This test instead
        checks the covariance has a realistic physical magnitude (RIC sigma
        model floors are 0.05-0.20km per axis -- (0.01km)^2 is a generous
        lower bound with margin), which a degenerate zero matrix fails.
        Exercises both PAYLOAD and DEBRIS (the dataset mixes types) since the
        bug was in the per-type grouping specifically.
        """
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0)
        min_realistic_variance_km2 = 0.01 ** 2
        for obj_idx in range(arrays.n_objects):
            for step_idx in range(arrays.n_steps):
                diag = np.diag(arrays.covariances_eci[obj_idx, step_idx])[:3]
                assert np.all(diag > min_realistic_variance_km2), (
                    f"object {obj_idx} step {step_idx}: position covariance diagonal "
                    f"{diag} is at/below the degenerate-zero floor"
                )

    def test_covariance_can_be_disabled(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0, attach_covariance=False)
        assert arrays.covariances_eci is None

    def test_positions_at_returns_all_objects_for_one_timestep(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0)
        snapshot = arrays.positions_at(0)
        assert snapshot.shape == (2, 3)
        np.testing.assert_allclose(snapshot[0], arrays.positions_eci_km[0, 0])
        np.testing.assert_allclose(snapshot[1], arrays.positions_eci_km[1, 0])

    def test_to_propagated_state_matches_raw_arrays(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0)

        state = arrays.to_propagated_state(0, 5)
        assert state.object_id == "25544"
        assert state.epoch == arrays.epochs[5]
        np.testing.assert_allclose(state.position_eci_km, arrays.positions_eci_km[0, 5])
        np.testing.assert_allclose(state.velocity_eci_km_s, arrays.velocities_eci_km_s[0, 5])
        assert state.covariance_6x6 is not None

    def test_to_propagated_state_raises_for_failed_step(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        arrays = propagate_catalog_arrays(dataset, start, start + timedelta(hours=1), step_s=300.0)
        arrays.ok_mask[0, 0] = False  # simulate a failed step

        with pytest.raises(ValueError):
            arrays.to_propagated_state(0, 0)

    def test_matches_pydantic_path_numerically(self):
        """The fast array path and the pydantic path must agree on the actual physics."""
        from src.propagation.batch_propagator import propagate_catalog

        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        end = start + timedelta(hours=1)

        arrays = propagate_catalog_arrays(dataset, start, end, step_s=300.0)
        pydantic_result = propagate_catalog(dataset, start, end, step_s=300.0)

        for obj_idx, object_id in enumerate(arrays.object_ids):
            pydantic_states = pydantic_result.trajectories[object_id].states
            for step_idx, state in enumerate(pydantic_states):
                np.testing.assert_allclose(arrays.positions_eci_km[obj_idx, step_idx], state.position_eci_km, atol=1e-9)
                np.testing.assert_allclose(arrays.velocities_eci_km_s[obj_idx, step_idx], state.velocity_eci_km_s, atol=1e-9)
