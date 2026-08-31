from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from src.backend.api.websocket import manager
from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import (
    ConjunctionEventCreate,
    ConjunctionEventResponse,
    RiskScoreUpdate,
    TLECreate,
    TLEDataResponse,
)

router = APIRouter(prefix="/api/ingest", tags=["Ingest"])

@router.post("/conjunction", response_model=ConjunctionEventResponse)
async def ingest_conjunction(event_data: ConjunctionEventCreate, db: Session = Depends(get_db)):
    """Receives a ConjunctionEvent from AI-2, persists it, broadcasts via WebSocket."""
    data_dict = event_data.model_dump(mode="python")

    event = crud.get_conjunction_event_by_id(db, event_data.event_id, dataset_name=event_data.dataset_name)
    if event:
        db_event = crud.update_conjunction_event(db, event_data.event_id, data_dict, dataset_name=event_data.dataset_name)
    else:
        db_event = crud.create_conjunction_event(db, data_dict)

    if not db_event:
        raise HTTPException(status_code=500, detail="Failed to persist conjunction event")

    response_model = ConjunctionEventResponse.model_validate(db_event)
    await manager.broadcast_event("NEW_CONJUNCTION", json.loads(response_model.model_dump_json()))

    logger.info(f"Ingested conjunction event {db_event.event_id}")
    return response_model


@router.post("/risk", response_model=ConjunctionEventResponse)
async def ingest_risk_score(risk_data: RiskScoreUpdate, db: Session = Depends(get_db)):
    """Receives a RiskScoreUpdate from AI-3, updates the event, broadcasts via WebSocket."""
    data_dict = risk_data.model_dump(mode="python")

    # Flatten ManeuverAdvisory into top-level DB columns
    adv = data_dict.pop("maneuver_advisory", None)
    if adv:
        data_dict["maneuver_delta_v_m_s"] = adv.get("delta_v_m_s")
        data_dict["maneuver_burn_direction"] = adv.get("burn_direction")
        data_dict["maneuver_new_miss_distance_km"] = adv.get("new_miss_distance_km")
        data_dict["maneuver_fuel_cost_estimate_kg"] = adv.get("fuel_cost_estimate_kg")

    db_event = crud.update_conjunction_event(db, risk_data.event_id, data_dict, dataset_name=risk_data.dataset_name)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found to update risk score")

    response_model = ConjunctionEventResponse.model_validate(db_event)
    await manager.broadcast_event("RISK_UPDATE", json.loads(response_model.model_dump_json()))

    logger.info(f"Updated risk score for event {db_event.event_id}")
    return response_model


@router.post("/tle", response_model=TLEDataResponse)
async def ingest_tle(tle_data: TLECreate, db: Session = Depends(get_db)):
    """Receives TLE data from AI-1, persists it."""
    data_dict = tle_data.model_dump(mode="python")
    db_tle = crud.create_tle(db, data_dict)
    logger.info(f"Ingested TLE for object {db_tle.object_id}")
    return db_tle
