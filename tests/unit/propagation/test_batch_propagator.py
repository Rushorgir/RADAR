"""Unit tests for src.propagation.batch_propagator (Owner: Anas)."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.batch_propagator import propagate_catalog, summarize_covariance_health

ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

DEBRIS_LINE1 = "1 34427U 93036SX  26233.50000000  .00001234  00000+0  12345-3 0  9999"
DEBRIS_LINE2 = "2 34427  74.0300 100.0000 0010000 100.0000 260.0000 14.20000000123459"


def _dataset():
    iss = parse_tle_lines(ISS_LINE1, ISS_LINE2, name="ISS (ZARYA)")
    debris = parse_tle_lines(DEBRIS_LINE1, DEBRIS_LINE2, name="COSMOS 2251 DEB")
    return [iss, debris]


class TestPropagateCatalog:
    def test_empty_input_returns_empty_result(self):
        result = propagate_catalog([], iss_epoch(), iss_epoch() + timedelta(hours=1), step_s=60.0)
        assert result.trajectories == {}
        assert result.epochs == []

    def test_propagates_every_object_in_catalog(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        result = propagate_catalog(dataset, start, start + timedelta(hours=1), step_s=60.0, max_workers=2)

        assert set(result.object_ids) == {"25544", "34427"}
        for traj in result.trajectories.values():
            assert traj.ok
            assert len(traj.states) == 61

    def test_attaches_positive_definite_covariance_by_default(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        result = propagate_catalog(dataset, start, start + timedelta(hours=1), step_s=300.0, attach_covariance=True)

        health = summarize_covariance_health(result)
        assert health["missing"] == 0
        assert health["degenerate"] == 0
        assert health["healthy"] > 0

    def test_covariance_can_be_disabled(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        result = propagate_catalog(dataset, start, start + timedelta(hours=1), step_s=300.0, attach_covariance=False)

        for traj in result.trajectories.values():
            for state in traj.states:
                assert state.covariance_6x6 is None

    def test_progress_callback_invoked_once_per_object(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        calls = []
        propagate_catalog(
            dataset, start, start + timedelta(minutes=30), step_s=300.0,
            progress_callback=lambda done, total: calls.append((done, total)),
        )
        assert len(calls) == len(dataset)
        assert calls[-1] == (len(dataset), len(dataset))

    def test_epoch_grid_matches_longest_trajectory(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        result = propagate_catalog(dataset, start, start + timedelta(hours=2), step_s=600.0)
        assert len(result.epochs) == 13  # 2h / 600s + 1

    def test_state_positions_are_finite_and_leo_scale(self):
        dataset = _dataset()
        start = min(t.epoch for t in dataset)
        result = propagate_catalog(dataset, start, start + timedelta(hours=1), step_s=600.0)

        for traj in result.trajectories.values():
            for state in traj.states:
                pos = np.array(state.position_eci_km)
                assert np.all(np.isfinite(pos))
                radius = np.linalg.norm(pos)
                assert 6500 < radius < 8000  # LEO regime


def iss_epoch():
    return parse_tle_lines(ISS_LINE1, ISS_LINE2, name="ISS (ZARYA)").epoch
