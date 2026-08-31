from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db

router = APIRouter(prefix="/api/risk", tags=["Risk"])


class RiskScoreResponse(BaseModel):
    event_id: str
    ml_risk_score: float | None
    risk_category: str | None
    shap_top_features: list[dict[str, Any]]


@router.get("/{event_id}", response_model=RiskScoreResponse)
async def get_risk_score(event_id: str, dataset: str = "default", db: Session = Depends(get_db)):
    """Return ML-ranked risk scores and SHAP explainability payloads for an event."""
    event = crud.get_conjunction_event_by_id(db, event_id, dataset_name=dataset)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "event_id": event.event_id,
        "ml_risk_score": event.ml_risk_score,
        "risk_category": event.risk_category,
        "shap_top_features": event.shap_top_features or [],
    }
