from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.backend.db.models import ConjunctionEventModel, TLEModel

# --- Conjunction Event CRUD ---

def get_conjunction_events(db: Session, skip: int = 0, limit: int = 100, risk_category: str | None = None, sort_by: str = "tca"):
    query = db.query(ConjunctionEventModel)
    
    if risk_category:
        query = query.filter(ConjunctionEventModel.risk_category == risk_category)
        
    if sort_by == "tca":
        query = query.order_by(ConjunctionEventModel.tca)
    elif sort_by == "pc":
        query = query.order_by(desc(ConjunctionEventModel.pc))
    elif sort_by == "ml_risk_score":
        query = query.order_by(desc(ConjunctionEventModel.ml_risk_score))
        
    return query.offset(skip).limit(limit).all()

def get_conjunction_events_count(db: Session, risk_category: str | None = None) -> int:
    query = db.query(func.count(ConjunctionEventModel.event_id))
    if risk_category:
        query = query.filter(ConjunctionEventModel.risk_category == risk_category)
    return query.scalar() or 0

def get_conjunction_event_by_id(db: Session, event_id: str) -> ConjunctionEventModel | None:
    return db.query(ConjunctionEventModel).filter(ConjunctionEventModel.event_id == event_id).first()

def create_conjunction_event(db: Session, event_data: dict) -> ConjunctionEventModel:
    db_event = ConjunctionEventModel(**event_data)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def update_conjunction_event(db: Session, event_id: str, update_data: dict) -> ConjunctionEventModel | None:
    db_event = get_conjunction_event_by_id(db, event_id)
    if not db_event:
        return None
        
    for key, value in update_data.items():
        setattr(db_event, key, value)
        
    db.commit()
    db.refresh(db_event)
    return db_event


# --- TLE Data CRUD ---

def get_tle_catalog(db: Session, skip: int = 0, limit: int = 100):
    return db.query(TLEModel).order_by(TLEModel.object_id).offset(skip).limit(limit).all()

def get_tle_catalog_count(db: Session) -> int:
    return db.query(func.count(TLEModel.id)).scalar() or 0

def get_tle_by_object_id(db: Session, object_id: str) -> TLEModel | None:
    # Returns the most recent TLE for the object
    return db.query(TLEModel).filter(TLEModel.object_id == object_id).order_by(desc(TLEModel.epoch)).first()

def create_tle(db: Session, tle_data: dict) -> TLEModel:
    db_tle = TLEModel(**tle_data)
    db.add(db_tle)
    db.commit()
    db.refresh(db_tle)
    return db_tle


# --- Dashboard Aggregations ---

def get_risk_distribution(db: Session) -> dict[str, int]:
    result = db.query(
        ConjunctionEventModel.risk_category,
        func.count(ConjunctionEventModel.event_id)
    ).group_by(ConjunctionEventModel.risk_category).all()
    
    # Initialize with default counts
    dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for category, count in result:
        if category in dist:
            dist[category] = count
    return dist

def get_total_tracked_objects(db: Session) -> int:
    return db.query(func.count(func.distinct(TLEModel.object_id))).scalar() or 0

def get_recent_high_risk_events(db: Session, hours: int = 24):
    threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.query(ConjunctionEventModel).filter(
        ConjunctionEventModel.risk_category == "HIGH",
        ConjunctionEventModel.created_at >= threshold_time
    ).order_by(desc(ConjunctionEventModel.created_at)).limit(10).all()
