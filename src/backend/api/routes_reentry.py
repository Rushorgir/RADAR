from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import ReentryPathResponse, ReentryWatchResponse
from src.ingestion.models import TLEParseError
from src.ingestion.tle_parser import parse_tle_lines
from src.propagation import current_positions, generate_descent_waypoints, predict_reentry_watch

router = APIRouter(prefix="/api/reentry", tags=["Re-entry"])


@router.get("/watch", response_model=ReentryWatchResponse)
async def get_reentry_watch(dataset: str = Query("default", description="Dataset namespace"), db: Session = Depends(get_db)):
    """
    Re-entry / orbital decay risk for the currently tracked catalog
    (src/propagation/reentry.py), computed live from each object's latest
    stored TLE. Only objects worth watching are returned -- see that
    module's docstring for how risk tiers and the decay-time estimate are
    derived, and what they honestly can't tell you.
    """
    tle_rows = crud.get_all_latest_tles(db, dataset_name=dataset)

    parsed_tles = []
    for row in tle_rows:
        try:
            parsed_tles.append(parse_tle_lines(str(row.line1), str(row.line2), name=str(row.object_name or "")))
        except TLEParseError as exc:
            logger.warning(f"Skipping object {row.object_id} in re-entry watch, stored TLE failed to parse: {exc}")

    predictions = predict_reentry_watch(parsed_tles)

    return {
        "epoch": datetime.now(timezone.utc),
        "predictions": [
            {
                "object_id": p.object_id,
                "name": p.name,
                "object_type": p.object_type,
                "perigee_altitude_km": p.perigee_altitude_km,
                "apogee_altitude_km": p.apogee_altitude_km,
                "risk_tier": p.risk_tier.value,
                "estimated_days_to_reentry": p.estimated_days_to_reentry,
                "sgp4_confirmed_decayed": p.sgp4_confirmed_decayed,
            }
            for p in predictions
        ],
        "objects_screened": len(parsed_tles),
    }


@router.get("/{object_id}/path", response_model=ReentryPathResponse)
async def get_reentry_path(
    object_id: str,
    dataset: str = Query("default", description="Dataset namespace"),
    db: Session = Depends(get_db),
):
    """
    A simplified descent-path visualization for one watched object
    (src/propagation/reentry.py generate_descent_waypoints): eases from its
    real, SGP4-propagated current altitude down to 0, holding the ground
    track fixed at its current sub-satellite point. See that module's
    docstring for exactly what this simplification does and doesn't claim.
    """
    row = crud.get_tle_by_object_id(db, object_id, dataset_name=dataset)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Object {object_id} not found in dataset '{dataset}'")

    try:
        tle = parse_tle_lines(str(row.line1), str(row.line2), name=str(row.object_name or ""))
    except TLEParseError as exc:
        raise HTTPException(status_code=422, detail=f"Stored TLE for {object_id} failed to parse: {exc}") from exc

    positions = current_positions([tle])
    if not positions:
        raise HTTPException(
            status_code=409,
            detail=f"Object {object_id} has no current SGP4-propagatable position (likely already decayed)",
        )
    position = positions[0]

    if position.altitude_km <= 0:
        raise HTTPException(status_code=409, detail=f"Object {object_id} has no positive altitude to descend from")

    waypoints = generate_descent_waypoints(
        latitude_deg=position.latitude_deg,
        longitude_deg=position.longitude_deg,
        current_altitude_km=position.altitude_km,
    )

    return {
        "object_id": object_id,
        "name": row.object_name or f"OBJ-{object_id}",
        "current_altitude_km": position.altitude_km,
        "waypoints": [
            {
                "elapsed_s": w.elapsed_s,
                "latitude_deg": w.latitude_deg,
                "longitude_deg": w.longitude_deg,
                "altitude_km": w.altitude_km,
            }
            for w in waypoints
        ],
    }
