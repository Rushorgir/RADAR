from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.backend.db.connection import get_db
from src.backend.db import crud
from src.backend.schemas.api_schemas import TLEDataResponse, PaginatedResponse

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

@router.get("/{object_id}", response_model=TLEDataResponse)
async def get_tle_for_object(object_id: str, db: Session = Depends(get_db)):
    """Fetch the most recent TLE for a specific object."""
    tle = crud.get_tle_by_object_id(db, object_id)
    if not tle:
        raise HTTPException(status_code=404, detail=f"TLE for object {object_id} not found")
    return tle
