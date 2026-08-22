"""Unit tests for src.propagation.current_positions (Owner: Anas)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.current_positions import current_positions

ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"


@pytest.fixture
def iss_tle():
    return parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)


class TestCurrentPositions:
    def test_returns_plausible_geodetic_position(self, iss_tle):
        [position] = current_positions([iss_tle], at=datetime(2026, 8, 22, tzinfo=timezone.utc))

        assert position.object_id == "25544"
        assert -90.0 <= position.latitude_deg <= 90.0
        assert -180.0 <= position.longitude_deg <= 180.0
        # ISS flies at ~370-460km; a wide LEO band avoids coupling this test
        # to the exact altitude at one specific instant.
        assert 200.0 <= position.altitude_km <= 1000.0

    def test_defaults_to_now_when_epoch_omitted(self, iss_tle):
        # Should not raise, and should produce a plausible result even
        # decades past the TLE's own epoch -- SGP4 degrades gracefully in
        # accuracy over time, it doesn't hard-fail.
        [position] = current_positions([iss_tle])
        assert -90.0 <= position.latitude_deg <= 90.0

    def test_empty_input_returns_empty_list(self):
        assert current_positions([]) == []

    def test_skips_objects_that_fail_to_propagate(self, iss_tle, monkeypatch):
        """
        One malformed/decayed object shouldn't take down the whole batch --
        callers (the /api/tle/positions route, and the frontend consuming
        it) already treat a missing position as "fall back for this one
        object", not a hard error.
        """
        import importlib

        # src/propagation/__init__.py does `from .current_positions import
        # current_positions`, which -- being the same name as the submodule
        # itself -- overwrites the `current_positions` attribute normal
        # import machinery would otherwise set on the `src.propagation`
        # package to point at this submodule. `import ... as` would silently
        # bind to that shadowed function instead of the module. Go through
        # sys.modules (via import_module) to get the real submodule.
        cp_module = importlib.import_module("src.propagation.current_positions")

        real_twoline2rv = cp_module.Satrec.twoline2rv
        calls = {"n": 0}

        class FailingFirstCallSatrec:
            def __init__(self, satrec):
                self._satrec = satrec

            def sgp4(self, jd, fr):
                calls["n"] += 1
                if calls["n"] == 1:
                    return 6, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)  # SGP4ErrorCode 6: decayed
                return self._satrec.sgp4(jd, fr)

        def fake_twoline2rv(line1, line2, gravity):
            return FailingFirstCallSatrec(real_twoline2rv(line1, line2, gravity))

        monkeypatch.setattr(
            cp_module,
            "Satrec",
            type("FakeSatrecFactory", (), {"twoline2rv": staticmethod(fake_twoline2rv)}),
        )

        second_tle = iss_tle.model_copy(update={"norad_id": 99999})
        result = cp_module.current_positions([iss_tle, second_tle])

        assert len(result) == 1
        assert result[0].object_id == "99999"
