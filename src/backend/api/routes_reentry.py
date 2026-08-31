from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import ReentryWatchResponse
from src.ingestion.models import TLEParseError
from src.ingestion.tle_parser import parse_tle_lines
from src.propagation import predict_reentry_watch

router = APIRouter(prefix="/api/reentry", tags=["Re-entry"])


@router.get("/watch", response_model=ReentryWatchResponse)
async def get_reentry_watch(dataset: str = Query("Live LEO Catalog (Unified)", description="Dataset namespace"), db: Session = Depends(get_db)):
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
