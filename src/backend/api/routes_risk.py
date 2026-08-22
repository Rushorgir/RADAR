from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from src.backend.db.connection import get_db
from src.backend.db import crud

router = APIRouter(prefix="/api/risk", tags=["Risk"])

@router.get("/{event_id}")
async def get_risk_score(event_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return ML-ranked risk scores and SHAP explainability payloads for an event."""
    event = crud.get_conjunction_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {
        "event_id": event.event_id,
        "ml_risk_score": event.ml_risk_score,
        "risk_category": event.risk_category,
        "shap_top_features": event.shap_top_features or []
    }
