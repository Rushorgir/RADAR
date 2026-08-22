from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.schemas.api_schemas import DashboardSummaryResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """Aggregated summary endpoints (KPIs, active alert counts, risk distributions)."""
    
    total_tracked = crud.get_total_tracked_objects(db)
    total_events = crud.get_conjunction_events_count(db)
    risk_dist = crud.get_risk_distribution(db)
    active_alerts = risk_dist.get("HIGH", 0)
    
    recent_high_risk = crud.get_recent_high_risk_events(db, hours=24)
    
    return {
        "total_tracked_objects": total_tracked,
        "total_conjunction_events": total_events,
        "active_high_risk_alerts": active_alerts,
        "risk_distribution": risk_dist,
        "recent_high_risk_events": recent_high_risk
    }
