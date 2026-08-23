import asyncio
from datetime import datetime, timedelta, timezone
import json
from loguru import logger
from sqlalchemy.orm import Session

from src.backend.db.connection import Base, SessionLocal, engine
from src.backend.db.models import ConjunctionEventModel, TLEModel
from src.backend.db import crud
from src.backend.schemas.api_schemas import ConjunctionEventCreate
from src.conjunction.pipeline import ConjunctionPipeline
from src.ingestion.tle_parser import parse_tle_file, TLEParseError
from src.propagation import propagate_catalog_arrays
from src.shared.config import get_propagation_config
from src.backend.api.websocket import manager

try:
    from src.ml.ranking.predictor import MLRiskPredictor
    ML_RANKING_AVAILABLE = True
except ImportError:
    ML_RANKING_AVAILABLE = False


async def run_dataset_pipeline(dataset_name: str, tle_content: str):
    """
    Runs the full ingestion -> propagation -> conjunction screening -> ML ranking pipeline
    in the background for an uploaded TLE dataset.
    """
    logger.info(f"Starting pipeline for dataset: {dataset_name}")
    try:
        # Progress 0%: Parsing
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": 5, "status": "Parsing TLEs..."})
        
        parsed_tles = []
        for tle in parse_tle_file(tle_content):
            parsed_tles.append(tle)
        
        if not parsed_tles:
            raise ValueError("No valid TLEs found in uploaded file.")
            
        logger.info(f"[{dataset_name}] Parsed {len(parsed_tles)} TLEs.")

        # Progress 20%: Propagation
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": 20, "status": "Propagating orbits..."})
        config = get_propagation_config(screening_timestep_s=60.0, propagation_horizon_h=72.0)
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=config['propagation_horizon_h'])
        arrays = propagate_catalog_arrays(parsed_tles, start, end, step_s=config['screening_timestep_s'], attach_covariance=True)

        # Progress 50%: Conjunction Screening
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": 50, "status": "Screening for conjunctions..."})
        pipeline = ConjunctionPipeline()
        events = pipeline.run(arrays)
        logger.info(f"[{dataset_name}] Found {len(events)} conjunctions.")

        # Progress 70%: ML Risk Ranking
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": 70, "status": "Running ML risk analysis..."})
        risk_scores = {}
        if ML_RANKING_AVAILABLE and events:
            predictor = MLRiskPredictor()
            for event in events:
                event_dict = json.loads(event.model_dump_json())
                try:
                    risk_scores[event.event_id] = predictor.predict_risk(event_dict)
                except Exception as exc:
                    logger.warning(f"ML ranking failed for event {event.event_id}: {exc}")

        # Progress 90%: DB Ingestion
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": 90, "status": "Saving dataset..."})
        Base.metadata.create_all(bind=engine)
        db: Session = SessionLocal()
        try:
            # Clear previous entries for this dataset name to ensure idempotency
            db.query(TLEModel).filter(TLEModel.dataset_name == dataset_name).delete()
            db.query(ConjunctionEventModel).filter(ConjunctionEventModel.dataset_name == dataset_name).delete()
            db.commit()

            # 1. Save TLEs
            for tle in parsed_tles:
                crud.create_tle(db, {
                    "dataset_name": dataset_name,
                    "object_id": str(tle.norad_id),
                    "object_name": tle.name,
                    "object_type": tle.object_type.value,
                    "line1": tle.line1,
                    "line2": tle.line2,
                    "epoch": tle.epoch
                })
            
            # 2. Save Events
            valid_keys = {c.name for c in ConjunctionEventModel.__table__.columns}
            for event in events:
                raw_dict = event.model_dump(mode="python")
                event_dict = {k: v for k, v in raw_dict.items() if k in valid_keys}
                event_dict["dataset_name"] = dataset_name
                if hasattr(event_dict.get("primary_object_type"), "value"):
                    event_dict["primary_object_type"] = event_dict["primary_object_type"].value
                if hasattr(event_dict.get("secondary_object_type"), "value"):
                    event_dict["secondary_object_type"] = event_dict["secondary_object_type"].value
                if hasattr(event_dict.get("pc_method"), "value"):
                    event_dict["pc_method"] = event_dict["pc_method"].value
                db_event = crud.get_conjunction_event_by_id(db, event.event_id, dataset_name=dataset_name)
                if db_event:
                    crud.update_conjunction_event(db, event.event_id, event_dict, dataset_name=dataset_name)
                else:
                    crud.create_conjunction_event(db, event_dict)
            
            # 3. Save Risk Scores
            for event_id, scored in risk_scores.items():
                scored_dict = json.loads(scored.model_dump_json())
                update_payload = {
                    "ml_risk_score": scored_dict.get("ml_risk_score"),
                    "risk_category": scored_dict.get("risk_category"),
                    "shap_top_features": scored_dict.get("shap_top_features"),
                    "maneuver_delta_v_m_s": scored_dict.get("maneuver_delta_v_m_s"),
                    "maneuver_burn_direction": scored_dict.get("maneuver_burn_direction"),
                    "maneuver_new_miss_distance_km": scored_dict.get("maneuver_new_miss_distance_km"),
                    "maneuver_fuel_cost_estimate_kg": scored_dict.get("maneuver_fuel_cost_estimate_kg")
                }
                # Filter out None values just in case
                update_payload = {k: v for k, v in update_payload.items() if v is not None}
                crud.update_conjunction_event(db, event_id, update_payload, dataset_name=dataset_name)
                
        finally:
            db.close()

        # Progress 100%: Done
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": 100, "status": "Complete"})
        logger.info(f"[{dataset_name}] Pipeline completed successfully.")
        
    except Exception as e:
        logger.error(f"Dataset pipeline failed: {e}")
        await manager.broadcast_event("DATASET_IMPORT_PROGRESS", {"dataset": dataset_name, "progress": -1, "status": f"Failed: {str(e)}"})
