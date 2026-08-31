from fastapi import APIRouter, Depends, UploadFile, Form, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from src.backend.db import crud
from src.backend.db.connection import get_db
from src.backend.db.models import TLEModel, ConjunctionEventModel
from src.backend.api.dataset_pipeline import run_dataset_pipeline

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

@router.get("/")
async def list_datasets(db: Session = Depends(get_db)):
    """List all available datasets in the database."""
    datasets = db.query(TLEModel.dataset_name).distinct().all()
    names = [row[0] for row in datasets]
    if "Live LEO Catalog (Unified)" not in names:
        names.insert(0, "Live LEO Catalog (Unified)")
    return {"datasets": names}

@router.post("/import")
async def import_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    dataset_name: str = Form(...)
):
    """
    Import a raw TLE .txt file as a new dataset.
    This runs asynchronously because propagation and ML scoring takes several minutes.
    """
    content = await file.read()
    tle_content = content.decode("utf-8")
    
    # Spawn background task to process the dataset
    background_tasks.add_task(run_dataset_pipeline, dataset_name, tle_content)
    
    return {"message": "Dataset import started.", "dataset_name": dataset_name}

@router.delete("/{dataset_name}")
async def delete_dataset(dataset_name: str, db: Session = Depends(get_db)):
    """Delete a custom dataset and all associated TLEs and conjunction events."""
    if dataset_name == "Live LEO Catalog (Unified)":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the unified catalog."
        )
    
    tles_deleted = db.query(TLEModel).filter(TLEModel.dataset_name == dataset_name).delete(synchronize_session=False)
    events_deleted = db.query(ConjunctionEventModel).filter(ConjunctionEventModel.dataset_name == dataset_name).delete(synchronize_session=False)
    db.commit()
    
    return {
        "status": "deleted",
        "dataset": dataset_name,
        "tles_deleted": tles_deleted,
        "events_deleted": events_deleted
    }

