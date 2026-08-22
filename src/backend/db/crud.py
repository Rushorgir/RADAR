from datetime import datetime, timedelta, timezone

from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from src.backend.db.models import ConjunctionEventModel, TLEModel
from src.shared.constants.physical import PC

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

def _latest_tle_query(db: Session):
    """
    One row per tracked object -- its most recent TLE.

    TLEModel deliberately keeps every historical TLE for an object (see the
    model docstring), so a plain `SELECT * FROM tle_data` would list the same
    physical satellite/debris piece once per re-ingestion of the catalog
    instead of once per object, inflating "how many objects are we
    tracking" counts (and duplicating its dot on the globe) every time the
    ingestion pipeline is re-run. Join back to a per-object MAX(epoch)
    subquery to keep only the latest snapshot of each.
    """
    latest_epoch = (
        db.query(TLEModel.object_id, func.max(TLEModel.epoch).label("max_epoch"))
        .group_by(TLEModel.object_id)
        .subquery()
    )
    return db.query(TLEModel).join(
        latest_epoch,
        (TLEModel.object_id == latest_epoch.c.object_id)
        & (TLEModel.epoch == latest_epoch.c.max_epoch),
    )

def get_tle_catalog(db: Session, skip: int = 0, limit: int = 100):
    return _latest_tle_query(db).order_by(TLEModel.object_id).offset(skip).limit(limit).all()

def get_tle_catalog_count(db: Session) -> int:
    return db.query(func.count(func.distinct(TLEModel.object_id))).scalar() or 0

def get_all_latest_tles(db: Session):
    """
    Every tracked object's latest TLE, unpaginated -- for batch operations
    that need the whole catalog at once (e.g. propagating current positions
    for the globe), as opposed to get_tle_catalog's paginated listing for
    the TLE browsing API.
    """
    return _latest_tle_query(db).all()

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

def _effective_risk_category():
    """
    risk_category is populated by AI-3's ML ranking model, which doesn't
    exist yet -- every event AI-2's real screening pipeline produces today
    has it as null. Without a fallback, "how many high-risk events" would
    always read 0 no matter how dangerous the real conjunctions are.
    Fall back to a plain Pc threshold (same cutoffs the frontend already
    uses -- src/shared/constants/physical.py's PC singleton) so the
    dashboard reflects real risk today, while still preferring
    risk_category once AI-3 actually sets it.
    """
    return case(
        (ConjunctionEventModel.risk_category.isnot(None), ConjunctionEventModel.risk_category),
        (ConjunctionEventModel.pc >= PC.PC_HIGH_RISK, "HIGH"),
        (ConjunctionEventModel.pc >= PC.PC_MEDIUM_RISK, "MEDIUM"),
        else_="LOW",
    )

def get_risk_distribution(db: Session) -> dict[str, int]:
    category = _effective_risk_category()
    result = db.query(category, func.count(ConjunctionEventModel.event_id)).group_by(category).all()

    # Initialize with default counts
    dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for cat, count in result:
        if cat in dist:
            dist[cat] = count
    return dist

def get_total_tracked_objects(db: Session) -> int:
    return db.query(func.count(func.distinct(TLEModel.object_id))).scalar() or 0

def get_recent_high_risk_events(db: Session, hours: int = 24):
    threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.query(ConjunctionEventModel).filter(
        _effective_risk_category() == "HIGH",
        ConjunctionEventModel.created_at >= threshold_time
    ).order_by(desc(ConjunctionEventModel.created_at)).limit(10).all()
