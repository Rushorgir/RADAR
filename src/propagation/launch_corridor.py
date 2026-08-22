"""
Launch corridor safety checking.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Designing a real launch-vehicle ascent trajectory (guidance, staging,
gravity-turn optimization) is a discipline of its own and out of scope
here. What this provides instead is a *conservative geometric corridor*
-- a simplified ascent path from a launch site up to a target circular
orbit altitude -- against which the currently tracked catalog can be
checked for close passes, using the same real SGP4-propagated positions
(src/propagation/current_positions.py) the globe view already shows.

The ascent profile is deliberately simple: altitude follows an eased
(smoothstep) climb from 0 to the target altitude over `duration_s`, and
the ground track holds the launch site's longitude/latitude fixed (a
"straight up" simplification -- real ascents drift downrange, but a
vertical corridor is a *conservative* stand-in: it doesn't undersell risk
by assuming a specific downrange path that might dodge a real conflict).
This is a screening aid to catch an obviously bad launch window, not a
substitute for a real flight-safety trajectory analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from src.ingestion.models import ParsedTLE
from src.propagation.current_positions import current_positions
from src.shared.constants.physical import EARTH

# Common orbital launch sites (lat/lon in degrees). Not exhaustive -- just
# enough real, correctly-located options for a meaningful corridor check
# instead of a free-text site name with no coordinates behind it.
LAUNCH_SITES: dict[str, tuple[float, float]] = {
    "Satish Dhawan Space Centre, Sriharikota, IN": (13.7199, 80.2304),
    "Kennedy Space Center, FL, US": (28.5729, -80.6490),
    "Vandenberg Space Force Base, CA, US": (34.7420, -120.5724),
    "Baikonur Cosmodrome, Kazakhstan": (45.9200, 63.3422),
    "Guiana Space Centre, Kourou, FR": (5.2360, -52.7750),
    "Tanegashima Space Center, Japan": (30.4000, 130.9700),
}

DEFAULT_ASCENT_DURATION_S = 600.0  # ~10 minutes, a typical LEO insertion timescale
# Each waypoint re-propagates the whole tracked catalog to its own clock
# time (see check_launch_corridor_safety) -- 12 keeps a full-catalog check
# to a few seconds for an on-demand "generate route" request rather than
# finer temporal resolution that mostly just adds latency.
DEFAULT_WAYPOINT_COUNT = 12
DEFAULT_SAFETY_RADIUS_KM = 25.0


@dataclass(frozen=True)
class AscentWaypoint:
    elapsed_s: float
    latitude_deg: float
    longitude_deg: float
    altitude_km: float


@dataclass(frozen=True)
class CorridorConflict:
    object_id: str
    object_name: str
    waypoint_elapsed_s: float
    distance_km: float


@dataclass(frozen=True)
class LaunchSafetyResult:
    safe: bool
    waypoints: list[AscentWaypoint]
    conflicts: list[CorridorConflict]
    objects_checked: int
    safety_radius_km: float


def _smoothstep(t: float) -> float:
    """Ease-in/ease-out from 0 to 1 -- fast climb through the thick lower
    atmosphere is unrealistic to model simply, so this just avoids the
    corridor having an unrealistic instant jump to full altitude at t=0."""
    return t * t * (3.0 - 2.0 * t)


def generate_ascent_waypoints(
    launch_lat_deg: float,
    launch_lon_deg: float,
    target_altitude_km: float,
    duration_s: float = DEFAULT_ASCENT_DURATION_S,
    n_waypoints: int = DEFAULT_WAYPOINT_COUNT,
) -> list[AscentWaypoint]:
    if n_waypoints < 2:
        raise ValueError("n_waypoints must be at least 2")
    if target_altitude_km <= 0:
        raise ValueError("target_altitude_km must be positive")

    waypoints = []
    for i in range(n_waypoints):
        frac = i / (n_waypoints - 1)
        elapsed_s = frac * duration_s
        altitude_km = _smoothstep(frac) * target_altitude_km
        waypoints.append(
            AscentWaypoint(
                elapsed_s=elapsed_s,
                latitude_deg=launch_lat_deg,
                longitude_deg=launch_lon_deg,
                altitude_km=altitude_km,
            )
        )
    return waypoints


def _waypoint_ecef_km(waypoint: AscentWaypoint) -> np.ndarray:
    """Geodetic (lat, lon, alt) -> a spherical-Earth ECEF-ish position in
    km. Approximate (spherical, not WGS84 ellipsoidal) -- fine at the
    accuracy this screening check needs; the actual object positions it's
    compared against carry the real geometric approximation."""
    lat = np.radians(waypoint.latitude_deg)
    lon = np.radians(waypoint.longitude_deg)
    r = EARTH.RADIUS_KM + waypoint.altitude_km
    return np.array([
        r * np.cos(lat) * np.cos(lon),
        r * np.cos(lat) * np.sin(lon),
        r * np.sin(lat),
    ])


def check_launch_corridor_safety(
    waypoints: list[AscentWaypoint],
    parsed_tles: list[ParsedTLE],
    launch_time: datetime | None = None,
    safety_radius_km: float = DEFAULT_SAFETY_RADIUS_KM,
) -> LaunchSafetyResult:
    """
    For each waypoint, propagate the whole tracked catalog to that
    waypoint's actual clock time (not just "now" for every waypoint -- a
    conflict 8 minutes into ascent needs the catalog's position 8 minutes
    from launch, not at launch itself) and flag any object that comes
    within `safety_radius_km` of the corridor at that instant.
    """
    launch_time = launch_time or datetime.now(timezone.utc)
    conflicts: list[CorridorConflict] = []

    for waypoint in waypoints:
        at = launch_time + timedelta(seconds=waypoint.elapsed_s)
        positions = current_positions(parsed_tles, at=at)
        if not positions:
            continue

        waypoint_ecef = _waypoint_ecef_km(waypoint)
        for pos in positions:
            lat = np.radians(pos.latitude_deg)
            lon = np.radians(pos.longitude_deg)
            r = EARTH.RADIUS_KM + pos.altitude_km
            object_ecef = np.array([
                r * np.cos(lat) * np.cos(lon),
                r * np.cos(lat) * np.sin(lon),
                r * np.sin(lat),
            ])
            distance_km = float(np.linalg.norm(waypoint_ecef - object_ecef))
            if distance_km <= safety_radius_km:
                name = next((t.name for t in parsed_tles if str(t.norad_id) == pos.object_id), pos.object_id)
                conflicts.append(
                    CorridorConflict(
                        object_id=pos.object_id,
                        object_name=name or f"OBJ-{pos.object_id}",
                        waypoint_elapsed_s=waypoint.elapsed_s,
                        distance_km=round(distance_km, 3),
                    )
                )

    return LaunchSafetyResult(
        safe=len(conflicts) == 0,
        waypoints=waypoints,
        conflicts=conflicts,
        objects_checked=len(parsed_tles),
        safety_radius_km=safety_radius_km,
    )
