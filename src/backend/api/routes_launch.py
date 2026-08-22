from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import (
    LaunchSafetyRequest,
    LaunchSafetyResponse,
    LaunchSiteResponse,
)
from src.ingestion.models import TLEParseError
from src.ingestion.tle_parser import parse_tle_lines
from src.propagation import LAUNCH_SITES, check_launch_corridor_safety, generate_ascent_waypoints

router = APIRouter(prefix="/api/launch", tags=["Launch"])


@router.get("/sites", response_model=list[LaunchSiteResponse])
async def get_launch_sites():
    """Known launch site coordinates (src/propagation/launch_corridor.py)."""
    return [
        {"name": name, "latitude_deg": lat, "longitude_deg": lon}
        for name, (lat, lon) in LAUNCH_SITES.items()
    ]


@router.post("/safety-check", response_model=LaunchSafetyResponse)
async def check_launch_safety(request: LaunchSafetyRequest, db: Session = Depends(get_db)):
    """
    Check a simplified ascent corridor from a launch site to a target
    orbital altitude against the currently tracked catalog's real,
    SGP4-propagated positions along the ascent timeline (src/propagation/
    launch_corridor.py). Not a substitute for a real flight-safety
    trajectory analysis -- see that module's docstring.
    """
    if request.launch_lat_deg is not None and request.launch_lon_deg is not None:
        lat, lon = request.launch_lat_deg, request.launch_lon_deg
    elif request.launch_site and request.launch_site in LAUNCH_SITES:
        lat, lon = LAUNCH_SITES[request.launch_site]
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either launch_lat_deg + launch_lon_deg, or a launch_site from GET /api/launch/sites",
        )

    tle_rows = crud.get_all_latest_tles(db)
    parsed_tles = []
    for row in tle_rows:
        try:
            parsed_tles.append(parse_tle_lines(row.line1, row.line2, name=row.object_name or ""))
        except TLEParseError as exc:
            logger.warning(f"Skipping object {row.object_id} in launch safety check, stored TLE failed to parse: {exc}")

    waypoints = generate_ascent_waypoints(lat, lon, target_altitude_km=request.target_altitude_km)
    result = check_launch_corridor_safety(
        waypoints, parsed_tles, launch_time=request.launch_time
    )

    return {
        "safe": result.safe,
        "waypoints": [
            {
                "elapsed_s": w.elapsed_s,
                "latitude_deg": w.latitude_deg,
                "longitude_deg": w.longitude_deg,
                "altitude_km": w.altitude_km,
            }
            for w in result.waypoints
        ],
        "conflicts": [
            {
                "object_id": c.object_id,
                "object_name": c.object_name,
                "waypoint_elapsed_s": c.waypoint_elapsed_s,
                "distance_km": c.distance_km,
            }
            for c in result.conflicts
        ],
        "objects_checked": result.objects_checked,
        "safety_radius_km": result.safety_radius_km,
    }
