"""Unit tests for src.propagation.sgp4_engine (Owner: Anas)."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.models import SGP4ErrorCode
from src.propagation.sgp4_engine import SGP4Propagator, SGP4PropagationFailure

ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

EARTH_RADIUS_KM = 6378.137


@pytest.fixture
def iss_tle():
    return parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)


@pytest.fixture
def propagator(iss_tle):
    return SGP4Propagator.from_tle(iss_tle)


class TestPropagateAt:
    def test_object_id_matches_norad_id(self, propagator, iss_tle):
        assert propagator.object_id == str(iss_tle.norad_id)

    def test_state_at_epoch_has_leo_altitude(self, propagator, iss_tle):
        state = propagator.propagate_at(iss_tle.epoch)
        radius = np.linalg.norm(state.position_eci_km)
        altitude = radius - EARTH_RADIUS_KM
        assert 350 < altitude < 500  # ISS operates ~400-430 km

    def test_state_has_plausible_orbital_velocity(self, propagator, iss_tle):
        state = propagator.propagate_at(iss_tle.epoch)
        speed = np.linalg.norm(state.velocity_eci_km_s)
        assert 7.5 < speed < 7.9  # LEO circular orbital speed

    def test_object_metadata_is_propagated_through(self, propagator, iss_tle):
        state = propagator.propagate_at(iss_tle.epoch)
        assert state.object_id == str(iss_tle.norad_id)
        assert state.object_name == ISS_NAME
        assert state.object_type == iss_tle.object_type
        assert state.covariance_6x6 is None  # sgp4_engine itself attaches no covariance


class TestPropagateGrid:
    def test_produces_expected_number_of_states(self, propagator, iss_tle):
        start = iss_tle.epoch
        end = start + timedelta(hours=2)
        traj = propagator.propagate_grid(start, end, step_s=60.0)
        assert len(traj.states) == 121  # 2h / 60s + 1
        assert len(traj.errors) == 0
        assert traj.ok

    def test_states_are_chronologically_ordered(self, propagator, iss_tle):
        start = iss_tle.epoch
        traj = propagator.propagate_grid(start, start + timedelta(hours=1), step_s=300.0)
        epochs = [s.epoch for s in traj.states]
        assert epochs == sorted(epochs)

    def test_orbit_stays_within_stable_altitude_band(self, propagator, iss_tle):
        start = iss_tle.epoch
        traj = propagator.propagate_grid(start, start + timedelta(hours=6), step_s=120.0)
        radii = [np.linalg.norm(s.position_eci_km) for s in traj.states]
        altitudes = [r - EARTH_RADIUS_KM for r in radii]
        assert min(altitudes) > 350
        assert max(altitudes) < 500

    def test_invalid_time_range_raises(self, propagator, iss_tle):
        with pytest.raises(ValueError):
            propagator.propagate_grid(iss_tle.epoch, iss_tle.epoch - timedelta(hours=1), step_s=60.0)

    def test_invalid_step_raises(self, propagator, iss_tle):
        with pytest.raises(ValueError):
            propagator.propagate_grid(iss_tle.epoch, iss_tle.epoch + timedelta(hours=1), step_s=0)


class _FakeSatrec:
    """
    Stand-in for sgp4.api.Satrec: the real Satrec is a C-extension object whose
    methods are read-only and can't be monkeypatched directly, so error-path
    tests swap the whole `_satrec` attribute for one of these instead.
    """

    def __init__(self, real_satrec, sgp4_fn=None, sgp4_array_fn=None):
        self._real = real_satrec
        self._sgp4_fn = sgp4_fn
        self._sgp4_array_fn = sgp4_array_fn

    def sgp4(self, jd, fr):
        if self._sgp4_fn:
            return self._sgp4_fn(jd, fr)
        return self._real.sgp4(jd, fr)

    def sgp4_array(self, jds, frs):
        if self._sgp4_array_fn:
            return self._sgp4_array_fn(jds, frs)
        return self._real.sgp4_array(jds, frs)


class TestSgp4FailureHandling:
    def test_nonzero_error_code_raises_with_details(self, propagator, iss_tle, monkeypatch):
        fake = _FakeSatrec(propagator._satrec, sgp4_fn=lambda jd, fr: (6, (0, 0, 0), (0, 0, 0)))
        monkeypatch.setattr(propagator, "_satrec", fake)

        with pytest.raises(SGP4PropagationFailure) as excinfo:
            propagator.propagate_at(iss_tle.epoch)

        assert excinfo.value.error_code == SGP4ErrorCode.SATELLITE_HAS_DECAYED
        assert "decayed" in str(excinfo.value).lower()

    def test_grid_collects_partial_errors_instead_of_raising(self, propagator, iss_tle, monkeypatch):
        real_satrec = propagator._satrec

        def _flaky(jds, frs):
            errors, r, v = real_satrec.sgp4_array(jds, frs)
            errors = errors.copy()
            errors[0] = 6  # force the first timestep to look decayed
            return errors, r, v

        monkeypatch.setattr(propagator, "_satrec", _FakeSatrec(real_satrec, sgp4_array_fn=_flaky))

        traj = propagator.propagate_grid(iss_tle.epoch, iss_tle.epoch + timedelta(minutes=10), step_s=60.0)
        assert len(traj.errors) == 1
        assert traj.errors[0].error_code == SGP4ErrorCode.SATELLITE_HAS_DECAYED
        assert len(traj.states) == 10  # the other 10 of 11 timesteps still succeeded
        assert not traj.ok
