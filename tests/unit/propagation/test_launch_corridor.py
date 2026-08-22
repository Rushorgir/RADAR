"""Unit tests for src.propagation.launch_corridor (Owner: Anas)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.launch_corridor import (
    LAUNCH_SITES,
    check_launch_corridor_safety,
    generate_ascent_waypoints,
)

ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"


@pytest.fixture
def iss_tle():
    return parse_tle_lines(ISS_LINE1, ISS_LINE2, name="ISS (ZARYA)")


class TestGenerateAscentWaypoints:
    def test_starts_at_ground_ends_at_target_altitude(self):
        waypoints = generate_ascent_waypoints(13.7, 80.2, target_altitude_km=500.0, n_waypoints=5)
        assert waypoints[0].altitude_km == pytest.approx(0.0, abs=1e-6)
        assert waypoints[-1].altitude_km == pytest.approx(500.0, abs=1e-6)

    def test_altitude_is_monotonically_non_decreasing(self):
        waypoints = generate_ascent_waypoints(13.7, 80.2, target_altitude_km=500.0, n_waypoints=10)
        altitudes = [w.altitude_km for w in waypoints]
        assert altitudes == sorted(altitudes)

    def test_ground_track_holds_launch_site_fixed(self):
        waypoints = generate_ascent_waypoints(13.7, 80.2, target_altitude_km=500.0, n_waypoints=5)
        assert all(w.latitude_deg == 13.7 and w.longitude_deg == 80.2 for w in waypoints)

    def test_elapsed_time_spans_the_full_duration(self):
        waypoints = generate_ascent_waypoints(13.7, 80.2, target_altitude_km=500.0, duration_s=600.0, n_waypoints=5)
        assert waypoints[0].elapsed_s == 0.0
        assert waypoints[-1].elapsed_s == 600.0

    def test_rejects_too_few_waypoints(self):
        with pytest.raises(ValueError):
            generate_ascent_waypoints(13.7, 80.2, target_altitude_km=500.0, n_waypoints=1)

    def test_rejects_non_positive_target_altitude(self):
        with pytest.raises(ValueError):
            generate_ascent_waypoints(13.7, 80.2, target_altitude_km=0.0, n_waypoints=5)


class TestLaunchSites:
    def test_known_sites_have_plausible_coordinates(self):
        for name, (lat, lon) in LAUNCH_SITES.items():
            assert -90.0 <= lat <= 90.0, name
            assert -180.0 <= lon <= 180.0, name


class TestCheckLaunchCorridorSafety:
    def test_no_conflicts_far_from_a_tight_corridor(self, iss_tle):
        # ISS's real orbit isn't anywhere near a Sriharikota-launched
        # vertical corridor at this specific instant -- a tight safety
        # radius should find nothing.
        lat, lon = LAUNCH_SITES["Satish Dhawan Space Centre, Sriharikota, IN"]
        waypoints = generate_ascent_waypoints(lat, lon, target_altitude_km=500.0, n_waypoints=4)
        result = check_launch_corridor_safety(
            waypoints, [iss_tle], launch_time=datetime(2026, 8, 22, tzinfo=timezone.utc), safety_radius_km=1.0
        )
        assert result.safe
        assert result.conflicts == []
        assert result.objects_checked == 1

    def test_flags_conflict_with_a_generous_radius(self, iss_tle):
        # Any tracked object is "within" an absurdly large safety radius --
        # this just proves the distance check actually fires, rather than
        # every real-data test coincidentally finding zero conflicts.
        lat, lon = LAUNCH_SITES["Satish Dhawan Space Centre, Sriharikota, IN"]
        waypoints = generate_ascent_waypoints(lat, lon, target_altitude_km=500.0, n_waypoints=4)
        result = check_launch_corridor_safety(
            waypoints,
            [iss_tle],
            launch_time=datetime(2026, 8, 22, tzinfo=timezone.utc),
            safety_radius_km=50_000.0,
        )
        assert not result.safe
        assert len(result.conflicts) > 0
        assert result.conflicts[0].object_id == "25544"

    def test_empty_catalog_is_trivially_safe(self):
        lat, lon = LAUNCH_SITES["Satish Dhawan Space Centre, Sriharikota, IN"]
        waypoints = generate_ascent_waypoints(lat, lon, target_altitude_km=500.0, n_waypoints=4)
        result = check_launch_corridor_safety(waypoints, [], safety_radius_km=25.0)
        assert result.safe
        assert result.objects_checked == 0
