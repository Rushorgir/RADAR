"""Unit tests for src.propagation.reentry (Owner: Anas)."""

from __future__ import annotations

import pytest

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.reentry import (
    ReentryRiskTier,
    classify_perigee_risk,
    estimate_days_to_reentry,
    predict_reentry_watch,
)

ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

# A genuinely decayed-orbit TLE: same as ISS's but with mean motion cranked
# to 17.0 rev/day (columns 53-63 of line 2, the only field changed), which
# puts perigee at ~6km altitude by the TLE's own elements alone --
# comfortably below IMMINENT_PERIGEE_KM, and low enough that SGP4 itself
# refuses to propagate it (SATELLITE_HAS_DECAYED).
DECAYED_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
DECAYED_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 17.00000000581927"


@pytest.fixture
def iss_tle():
    return parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)


class TestClassifyPerigeeRisk:
    def test_imminent_at_low_perigee(self):
        assert classify_perigee_risk(100.0) == ReentryRiskTier.IMMINENT

    def test_elevated_band(self):
        assert classify_perigee_risk(180.0) == ReentryRiskTier.ELEVATED

    def test_watch_band(self):
        assert classify_perigee_risk(280.0) == ReentryRiskTier.WATCH

    def test_nominal_above_watch_band(self):
        assert classify_perigee_risk(550.0) == ReentryRiskTier.NOMINAL

    def test_boundaries_are_inclusive_of_the_riskier_tier(self):
        # A boundary value should fall into the more urgent tier, not
        # silently slip into the calmer one on a strict-vs-non-strict
        # inequality mismatch.
        from src.propagation.reentry import (
            ELEVATED_PERIGEE_KM,
            IMMINENT_PERIGEE_KM,
            WATCH_PERIGEE_KM,
        )

        assert classify_perigee_risk(IMMINENT_PERIGEE_KM) == ReentryRiskTier.IMMINENT
        assert classify_perigee_risk(ELEVATED_PERIGEE_KM) == ReentryRiskTier.ELEVATED
        assert classify_perigee_risk(WATCH_PERIGEE_KM) == ReentryRiskTier.WATCH


class TestEstimateDaysToReentry:
    def test_none_above_watch_band(self):
        assert estimate_days_to_reentry(400.0, bstar=1e-4) is None

    def test_zero_at_or_below_imminent_band(self):
        assert estimate_days_to_reentry(100.0, bstar=1e-4) == 0.0

    def test_higher_drag_means_sooner(self):
        low_drag = estimate_days_to_reentry(250.0, bstar=1e-5)
        high_drag = estimate_days_to_reentry(250.0, bstar=1e-3)
        assert high_drag < low_drag

    def test_lower_perigee_means_sooner(self):
        higher_perigee = estimate_days_to_reentry(280.0, bstar=1e-4)
        lower_perigee = estimate_days_to_reentry(180.0, bstar=1e-4)
        assert lower_perigee < higher_perigee

    def test_handles_zero_bstar_without_crashing(self):
        # Some payloads report a B* of exactly 0 -- shouldn't divide by zero.
        result = estimate_days_to_reentry(250.0, bstar=0.0)
        assert result is not None and result > 0


class TestPredictReentryWatch:
    def test_healthy_object_omitted_by_default(self, iss_tle):
        # ISS orbits at ~400km, comfortably NOMINAL.
        predictions = predict_reentry_watch([iss_tle])
        assert predictions == []

    def test_healthy_object_included_when_requested(self, iss_tle):
        predictions = predict_reentry_watch([iss_tle], include_nominal=True)
        assert len(predictions) == 1
        assert predictions[0].risk_tier == ReentryRiskTier.NOMINAL

    def test_decayed_object_flagged_imminent(self):
        decayed = parse_tle_lines(DECAYED_LINE1, DECAYED_LINE2, name="DECAYED TEST OBJECT", validate_checksum=False)
        predictions = predict_reentry_watch([decayed])
        assert len(predictions) == 1
        assert predictions[0].risk_tier == ReentryRiskTier.IMMINENT
        assert predictions[0].estimated_days_to_reentry == 0.0

    def test_sorted_most_urgent_first(self, iss_tle):
        decayed = parse_tle_lines(DECAYED_LINE1, DECAYED_LINE2, name="DECAYED TEST OBJECT", validate_checksum=False)
        predictions = predict_reentry_watch([iss_tle, decayed], include_nominal=True)
        assert predictions[0].risk_tier == ReentryRiskTier.IMMINENT
        assert predictions[-1].risk_tier == ReentryRiskTier.NOMINAL
