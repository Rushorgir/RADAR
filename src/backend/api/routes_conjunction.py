from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import ConjunctionEventResponse, PaginatedResponse

router = APIRouter(prefix="/api/conjunctions", tags=["Conjunctions"])

@router.get("/", response_model=PaginatedResponse[ConjunctionEventResponse])
async def get_conjunction_events(
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=1000), 
    risk_category: str | None = Query(None, description="Filter by HIGH, MEDIUM, LOW"),
    sort_by: str = Query("tca", description="Sort by tca, pc, or ml_risk_score"),
    dataset: str = Query("Live LEO Catalog (Unified)", description="Dataset namespace"),
    db: Session = Depends(get_db)
):
    """Fetch paginated conjunction events."""
    events = crud.get_conjunction_events(db, skip=skip, limit=limit, risk_category=risk_category, sort_by=sort_by, dataset_name=dataset)
    total = crud.get_conjunction_events_count(db, risk_category=risk_category, dataset_name=dataset)
    
    return {
        "items": events,
        "total": total,
        "page": skip // limit if limit > 0 else 0,
        "size": limit
    }

@router.get("/{event_id}", response_model=ConjunctionEventResponse)
async def get_conjunction_event(event_id: str, dataset: str = Query("Live LEO Catalog (Unified)", description="Dataset namespace"), db: Session = Depends(get_db)):
    """Fetch full details for a specific conjunction event."""
    event = crud.get_conjunction_event_by_id(db, event_id, dataset_name=dataset)
    if not event:
        raise HTTPException(status_code=404, detail="Conjunction event not found")
    return event
