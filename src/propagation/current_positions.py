"""
Current-position snapshot: propagate a whole catalog to "right now" (or any
single shared epoch) and reduce straight to geodetic lat/lon/altitude, for
map/globe display.

This is deliberately separate from batch_propagator.py / batch_arrays.py,
which propagate across a *grid* of future timesteps for AI-2's conjunction
screening and carry covariance along with them. A live "where is everything
right now" query is a single-epoch, display-only case -- no covariance, no
multi-step trajectory, just plain floats a frontend can plot directly.

Owner: Anas (AI-1: Orbital Mechanics Lead)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sgp4.api import Satrec, WGS84, jday

from src.ingestion.models import ParsedTLE
from src.shared.frames.transforms import (
    ecef_to_geodetic_batch,
    eci_to_ecef_batch,
    teme_to_eci_batch,
)


@dataclass(frozen=True)
class ObjectPosition:
    object_id: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
    velocity_km_s: float | None = None


def _epoch_to_jd_fr(epoch: datetime) -> tuple[float, float]:
    if epoch.tzinfo is not None:
        epoch = epoch.astimezone(timezone.utc).replace(tzinfo=None)
    return jday(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute, epoch.second + epoch.microsecond * 1e-6)


def current_positions(parsed_tles: list[ParsedTLE], at: datetime | None = None) -> list[ObjectPosition]:
    """
    Propagate every object in `parsed_tles` to `at` (defaults to now) and
    return its geodetic position.

    Objects whose SGP4 propagation fails (decayed, malformed elements, deep-
    space edge cases, etc.) are silently skipped rather than failing the
    whole batch -- callers already treat "no position for this object" as
    "fall back to a placeholder for just this one", not a hard error (see
    src/frontend/src/utils/liveData.js).

    Frame transforms (TEME->ECI->ECEF->geodetic) are batched across the
    whole catalog rather than called once per object in a Python loop --
    same reasoning as teme_to_eci_batch elsewhere in this module: astropy's
    per-call overhead dominates at catalog scale if paid per-object instead
    of once for the batch. The SGP4 call itself (pure numpy/C, no astropy)
    stays per-object since sgp4_array requires a shared (jd, fr) *array*
    per satellite, which is overkill for a single shared epoch.
    """
    at = at or datetime.now(timezone.utc)
    jd, fr = _epoch_to_jd_fr(at)

    object_ids: list[str] = []
    r_teme_rows: list[tuple[float, float, float]] = []
    v_teme_rows: list[tuple[float, float, float]] = []
    for tle in parsed_tles:
        try:
            satrec = Satrec.twoline2rv(tle.line1, tle.line2, WGS84)
            error, r, v = satrec.sgp4(jd, fr)
        except Exception:  # noqa: BLE001 -- any malformed-element failure means "skip this one"
            continue
        if error != 0:
            continue
        object_ids.append(str(tle.norad_id))
        r_teme_rows.append(r)
        v_teme_rows.append(v)

    if not object_ids:
        return []

    r_teme = np.asarray(r_teme_rows, dtype=float)
    v_teme = np.asarray(v_teme_rows, dtype=float)

    pos_eci, vel_eci = teme_to_eci_batch(r_teme, v_teme, [at] * len(object_ids))
    pos_ecef, vel_ecef = eci_to_ecef_batch(pos_eci, vel_eci, at)
    lat_deg, lon_deg, alt_km = ecef_to_geodetic_batch(pos_ecef, at)

    vel_mag_km_s = np.linalg.norm(vel_ecef, axis=1)

    return [
        ObjectPosition(
            object_id=oid,
            latitude_deg=float(lat),
            longitude_deg=float(lon),
            altitude_km=float(alt),
            velocity_km_s=float(v)
        )
        for oid, lat, lon, alt, v in zip(object_ids, lat_deg, lon_deg, alt_km, vel_mag_km_s)
    ]
