from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import PaginatedResponse, PositionsResponse, TLEDataResponse
from src.ingestion.models import TLEParseError
from src.ingestion.tle_parser import parse_tle_lines
from src.propagation import current_positions as compute_current_positions

router = APIRouter(prefix="/api/tle", tags=["TLE"])

@router.get("/", response_model=PaginatedResponse[TLEDataResponse])
async def get_tle_catalog(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Fetch paginated tracked satellites and active debris catalog."""
    tles = crud.get_tle_catalog(db, skip=skip, limit=limit)
    total = crud.get_tle_catalog_count(db)

    return {
        "items": tles,
        "total": total,
        "page": skip // limit if limit > 0 else 0,
        "size": limit
    }

# Registered before /{object_id} -- FastAPI matches routes in declaration
# order, so a static "/positions" segment must come first or every request
# here would instead match /{object_id} with object_id="positions".
@router.get("/positions", response_model=PositionsResponse)
async def get_current_positions(
    at: datetime | None = Query(
        None,
        description="UTC timestamp to propagate to (ISO 8601). Defaults to now. "
        "Lets a caller driving a simulated clock (e.g. the frontend's timeline "
        "control) request real SGP4-propagated positions at any point along "
        "it, not just the actual current instant.",
    ),
    db: Session = Depends(get_db),
):
    """
    Real SGP4-propagated lat/lon/altitude for every tracked object at `at`
    (default: right now), computed live from each object's latest stored
    TLE. Not cached or stored -- a position is only valid for the instant
    it was computed for, so there's nothing worth persisting here.
    """
    tle_rows = crud.get_all_latest_tles(db)

    parsed_tles = []
    for row in tle_rows:
        try:
            parsed_tles.append(parse_tle_lines(row.line1, row.line2, name=row.object_name or ""))
        except TLEParseError as exc:
            logger.warning(f"Skipping object {row.object_id}, stored TLE failed to parse: {exc}")

    if at is None:
        target = datetime.now(timezone.utc)
    elif at.tzinfo is None:
        target = at.replace(tzinfo=timezone.utc)  # assume UTC rather than guessing local time
    else:
        target = at.astimezone(timezone.utc)
    positions = compute_current_positions(parsed_tles, at=target)

    return {
        "epoch": target,
        "positions": [
            {
                "object_id": p.object_id,
                "latitude_deg": p.latitude_deg,
                "longitude_deg": p.longitude_deg,
                "altitude_km": p.altitude_km,
            }
            for p in positions
        ],
        "requested": len(tle_rows),
    }

@router.get("/{object_id}", response_model=TLEDataResponse)
async def get_tle_for_object(object_id: str, db: Session = Depends(get_db)):
    """Fetch the most recent TLE for a specific object."""
    tle = crud.get_tle_by_object_id(db, object_id)
    if not tle:
        raise HTTPException(status_code=404, detail=f"TLE for object {object_id} not found")
    return tle
