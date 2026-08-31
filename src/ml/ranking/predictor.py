from __future__ import annotations

import os
import sys
import numpy as np
import lightgbm as lgb
import pandas as pd
from typing import Dict, Any

from src.ml.features.extractor import extract_features_from_conjunction_event, FEATURES
from src.ml.explainability.shap_explainer import RiskExplainer
from src.shared.interfaces.contracts import RiskScoredEvent, RiskCategory, SHAPFeature, ManeuverAdvisory
from src.maneuver.optimizer import ManeuverOptimizer

class MLRiskPredictor:
    def __init__(self, model_path: str | None = None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'improved', 'lightgbm_risk_model.txt')
        
        self.model = lgb.Booster(model_file=model_path)
        self.explainer = RiskExplainer(self.model, FEATURES)
        
        self.class_mapping = {
            0: RiskCategory.LOW,
            1: RiskCategory.MEDIUM,
            2: RiskCategory.HIGH
        }
        
    def predict_risk(self, conjunction_event: Dict[str, Any]) -> RiskScoredEvent:
        """
        Takes a ConjunctionEvent dict (or object mapped to dict) and returns a RiskScoredEvent.
        """
        event_id = conjunction_event.get('event_id', 'unknown')
        
        # Feature extraction
        df_feat = extract_features_from_conjunction_event(conjunction_event)
        
        import dateutil.parser
        tca = dateutil.parser.parse(str(conjunction_event['tca']))
        created_at = dateutil.parser.parse(str(conjunction_event['created_at']))
        time_to_tca_days = (tca - created_at).total_seconds() / 86400.0
        miss_distance_km = float(conjunction_event.get('miss_distance_km', 0.0))
        relative_velocity_km_s = float(conjunction_event.get('relative_velocity_km_s', 0.0))
        pc = float(conjunction_event.get('pc', 0.0))
        primary_id = str(conjunction_event.get('primary_id', 'unknown'))
        secondary_id = str(conjunction_event.get('secondary_id', 'unknown'))
        pca = conjunction_event.get('primary_cross_section_area_m2')
        sca = conjunction_event.get('secondary_cross_section_area_m2')
        raw_regime = conjunction_event.get('orbital_regime')
        
        # Load operating thresholds
        thresholds_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'improved', 'thresholds.json')
        if not os.path.exists(thresholds_path):
            raise FileNotFoundError(f"Threshold configuration missing at {thresholds_path}")
            
        import json
        try:
            with open(thresholds_path, 'r') as f:
                threshold_config = json.load(f)
                threshold_high = float(threshold_config['high'])
                threshold_med = float(threshold_config['med'])
            if not (0.0 <= threshold_med <= threshold_high <= 1.0):
                raise ValueError(f"Invalid threshold values: med={threshold_med}, high={threshold_high}")
        except Exception as e:
            raise ValueError(f"Malformed threshold configuration: {e}")
            
        operating_threshold_name = "Safety First"
        
        preds = np.asarray(self.model.predict(df_feat))[0]
        
        # Continuous risk score monotonic with collision danger (0.0 = safe, 1.0 = critical)
        risk_score = float(np.clip(preds[2] + 0.5 * preds[1], 0.0, 1.0))
        
        if preds[2] >= threshold_high:
            pred_class_idx = 2
        elif preds[1] >= threshold_med:
            pred_class_idx = 1
        else:
            pred_class_idx = 0
            
        risk_category = self.class_mapping[pred_class_idx]
        
        # Generate SHAP Explanation
        shap_contributions = self.explainer.explain_instance(df_feat)
        top_features = [
            SHAPFeature(feature=sc['feature'], impact=sc['impact']) 
            for sc in shap_contributions[:3] # Top 3 features
        ]
        
        # Generate Maneuver Advisory if HIGH risk
        maneuver_adv = None
        if risk_category == RiskCategory.HIGH:
            optimizer = ManeuverOptimizer(target_safety_distance_km=10.0)
            adv_res = optimizer.calculate_advisory(miss_distance_km, time_to_tca_days, relative_velocity_km_s)
            if adv_res:
                maneuver_adv = ManeuverAdvisory(
                    delta_v_m_s=adv_res.delta_v_m_s,
                    burn_direction=adv_res.burn_direction,
                    new_miss_distance_km=adv_res.new_miss_distance_km,
                    risk_reduction_factor=adv_res.risk_reduction_factor,
                    fuel_cost_estimate_kg=adv_res.fuel_cost_estimate_kg
                )
        
        # Return RiskScoredEvent
        return RiskScoredEvent(
            event_id=event_id,
            primary_id=primary_id,
            secondary_id=secondary_id,
            time_to_tca_days=time_to_tca_days,
            miss_distance_km=miss_distance_km,
            relative_velocity_km_s=relative_velocity_km_s,
            pc=pc,
            ml_risk_score=risk_score,
            risk_category=risk_category,
            risk_threshold_used=operating_threshold_name,
            shap_top_features=top_features,
            primary_cross_section_area_m2=pca,
            secondary_cross_section_area_m2=sca,
            orbital_regime=raw_regime,
            maneuver_advisory=maneuver_adv
        )

if __name__ == "__main__":
    print("Initializing predictor smoke test...")
    try:
        predictor = MLRiskPredictor()
        # Create a dummy event for smoke test
        dummy_event = {
            'event_id': 'smoke-test-1',
            'tca': '2026-08-22T10:00:00Z',
            'created_at': '2026-08-20T10:00:00Z',
            'miss_distance_km': 5.0,
            'relative_velocity_km_s': 7.5,
            'pc': 1e-4,
            'secondary_object_type': 'DEBRIS'
        }
        res = predictor.predict_risk(dummy_event)
        print(f"Smoke test successful. Predicted Category: {res.risk_category.name}")
    except Exception as e:
        print(f"Smoke test failed: {e}")
        sys.exit(1)
