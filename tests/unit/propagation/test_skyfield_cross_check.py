"""
Independent cross-validation of this module's SGP4 propagation against
skyfield (Owner: Anas).

Every other test in tests/unit/propagation/ checks this module's output
against *physical* sanity (LEO altitude/speed ranges, RIC orthonormality,
etc.) -- useful, but it can't catch a bug this module's own implementation
and its own tests happen to share a blind spot on (e.g. a subtly wrong sign
convention in the TEME->ECI rotation that "looks" physically sane but is
still wrong).

skyfield ships its own independent SGP4 implementation and its own
independent frame handling, entirely unrelated to
src/shared/frames/transforms.py's astropy-based TEME->GCRS rotation. Feeding
the exact same TLE through both and diffing the result is a genuine
second-implementation check: agreement doesn't prove either is *correct* in
an absolute sense, but it does rule out a wide class of implementation bugs
that a same-codebase test can't.

skyfield was already a pinned dependency (requirements.txt) but was unused
until this file -- see AI1_IMPLEMENTATION_NOTES.md §11 "known limitations".
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest
from skyfield.api import EarthSatellite, load

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.sgp4_engine import SGP4Propagator

ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

# How far the two independent implementations are allowed to disagree.
# Measured directly before choosing this (see the module docstring): actual
# disagreement across a 0h-72h window from epoch was 12m-187m -- this bound
# leaves better than 5x margin over the worst of that, while still being
# tight enough to catch a real bug (a wrong rotation sign or an unswapped
# axis would produce a disagreement in the hundreds to thousands of km, not
# meters).
MAX_POSITION_DIFF_KM = 1.0
MAX_VELOCITY_DIFF_KM_S = 0.01


@pytest.fixture
def iss_tle():
    return parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)


@pytest.fixture
def propagator(iss_tle):
    return SGP4Propagator.from_tle(iss_tle)


@pytest.fixture
def skyfield_satellite():
    # skyfield.EarthSatellite.at() returns position/velocity in the same
    # ICRF-equivalent frame this module's `eci` stands in for (GCRS) --
    # both are inertial and agree to sub-meter precision at LEO distances,
    # so no extra frame conversion is needed to compare them directly.
    return EarthSatellite(ISS_LINE1, ISS_LINE2, ISS_NAME, load.timescale())


class TestSkyfieldCrossCheck:
    @pytest.mark.parametrize("hours_after_epoch", [0, 1, 6, 24, 72])
    def test_position_and_velocity_agree_with_skyfield(
        self, propagator, iss_tle, skyfield_satellite, hours_after_epoch
    ):
        at = iss_tle.epoch + timedelta(hours=hours_after_epoch)

        ours = propagator.propagate_at(at)
        theirs = skyfield_satellite.at(load.timescale().from_datetime(at))

        position_diff_km = np.linalg.norm(np.array(ours.position_eci_km) - theirs.position.km)
        velocity_diff_km_s = np.linalg.norm(np.array(ours.velocity_eci_km_s) - theirs.velocity.km_per_s)

        assert position_diff_km < MAX_POSITION_DIFF_KM, (
            f"+{hours_after_epoch}h: position disagreement {position_diff_km:.3f} km "
            f"exceeds {MAX_POSITION_DIFF_KM} km -- possible frame/rotation bug"
        )
        assert velocity_diff_km_s < MAX_VELOCITY_DIFF_KM_S, (
            f"+{hours_after_epoch}h: velocity disagreement {velocity_diff_km_s:.5f} km/s "
            f"exceeds {MAX_VELOCITY_DIFF_KM_S} km/s -- possible frame/rotation bug"
        )
