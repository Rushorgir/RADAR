import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.backend.db.connection import SessionLocal
from src.backend.db.models import ConjunctionEventModel
from src.ml.ranking.predictor import MLRiskPredictor

def rescore():
    print("Initializing predictor...")
    predictor = MLRiskPredictor()
    
    with SessionLocal() as db:
        events = db.query(ConjunctionEventModel).all()
        print(f"Found {len(events)} events to rescore.")
        
        for e in events:
            event_dict = {
                'event_id': e.event_id,
                'tca': e.tca.isoformat(),
                'created_at': e.created_at.isoformat(),
                'miss_distance_km': e.miss_distance_km,
                'relative_velocity_km_s': e.relative_velocity_km_s,
                'pc': e.pc,
                'primary_id': e.primary_id,
                'secondary_id': e.secondary_id,
                'primary_object_type': e.primary_object_type,
                'secondary_object_type': e.secondary_object_type,
            }
            
            try:
                scored = predictor.predict_risk(event_dict)
                e.ml_risk_score = scored.ml_risk_score
                e.risk_category = scored.risk_category.value
                e.shap_top_features = [f.model_dump() if hasattr(f, 'model_dump') else dict(f) for f in scored.shap_top_features]
                
                if scored.maneuver_advisory:
                    e.maneuver_delta_v_m_s = scored.maneuver_advisory.delta_v_m_s
                    e.maneuver_burn_direction = scored.maneuver_advisory.burn_direction
                    e.maneuver_new_miss_distance_km = scored.maneuver_advisory.new_miss_distance_km
                    e.maneuver_fuel_cost_estimate_kg = scored.maneuver_advisory.fuel_cost_estimate_kg
                else:
                    e.maneuver_delta_v_m_s = None
                    e.maneuver_burn_direction = None
                    e.maneuver_new_miss_distance_km = None
                    e.maneuver_fuel_cost_estimate_kg = None
            except Exception as exc:
                print(f"Failed to rescore event {e.event_id}: {exc}")
                
        db.commit()
        print("Database rescoring complete.")

if __name__ == "__main__":
    rescore()
