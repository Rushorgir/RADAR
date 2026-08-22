from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import ManeuverAdvisoryResponse

router = APIRouter(prefix="/api/maneuver", tags=["Maneuver"])

@router.get("/{event_id}", response_model=ManeuverAdvisoryResponse)
async def get_maneuver_advisory(event_id: str, db: Session = Depends(get_db)):
    """Deliver optimal Delta-v maneuver advisories for a given event."""
    event = crud.get_conjunction_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    if event.maneuver_delta_v_m_s is None:
        raise HTTPException(status_code=404, detail="No maneuver advisory available for this event")
        
    return {
        "delta_v_m_s": event.maneuver_delta_v_m_s,
        "burn_direction": event.maneuver_burn_direction,
        "new_miss_distance_km": event.maneuver_new_miss_distance_km,
        "fuel_cost_estimate_kg": event.maneuver_fuel_cost_estimate_kg
    }
