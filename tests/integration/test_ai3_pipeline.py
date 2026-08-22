import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))
from ml.ranking.predictor import MLRiskPredictor
from shared.interfaces.contracts import ConjunctionEvent, RiskCategory, OrbitalRegime, PropagatedState, ObjectType
from datetime import datetime, timedelta, timezone

def test_fallback_end_to_end_pipeline():
    """
    Test end-to-end processing of a mock ConjunctionEvent through the AI-3 ML risk pipeline.
    """
    
    # 1. Simulate AI-1 Propagated States
    primary_state = PropagatedState(
        object_id="SAT-12345",
        epoch=datetime.utcnow(),
        position_eci_km=[7000.0, 0.0, 0.0], # LEO altitude ~600km
        velocity_eci_km_s=[0.0, 7.5, 0.0],
        cross_section_area_m2=12.5,
        object_type=ObjectType.PAYLOAD
    )
    
    secondary_state = PropagatedState(
        object_id="DEB-99999",
        epoch=datetime.utcnow(),
        position_eci_km=[7000.1, 0.1, 0.1],
        velocity_eci_km_s=[0.0, -7.5, 0.0],
        cross_section_area_m2=0.5,
        object_type=ObjectType.DEBRIS
    )
    
    # 2. Simulate AI-2 Conjunction Event Creation
    # tz-aware, matching real production ConjunctionEvents (AI-2's pipeline
    # builds tca from an aware propagation epoch grid) and ConjunctionEvent's
    # own created_at default (datetime.now(timezone.utc)) -- extractor.py
    # subtracts the two to get time-to-TCA, which raises TypeError if one
    # side is naive and the other aware.
    tca_time = datetime.now(timezone.utc) + timedelta(days=2.5)
    
    conjunction_event = ConjunctionEvent(
        primary_id=primary_state.object_id,
        secondary_id=secondary_state.object_id,
        tca=tca_time,
        miss_distance_km=0.5,
        relative_velocity_km_s=15.0,
        pc=0.005, # High risk Pc
        primary_object_type=primary_state.object_type,
        secondary_object_type=secondary_state.object_type,
        primary_cross_section_area_m2=primary_state.cross_section_area_m2,
        secondary_cross_section_area_m2=secondary_state.cross_section_area_m2,
        orbital_regime=OrbitalRegime.LEO
    )
    
    # Convert to dict for predictor boundary (simulating JSON over REST API)
    event_dict = conjunction_event.model_dump(mode='json')
    
    # Inject simulated temporal tracking fields that AI-3 state tracker would provide
    event_dict['previous_pc'] = 0.001
    event_dict['previous_miss_distance_km'] = 0.8
    
    # 3. AI-3 Inference
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'ml', 'models', 'improved', 'lightgbm_risk_model.txt'))
    predictor = MLRiskPredictor(model_path)
    
    risk_scored_event = predictor.predict_risk(event_dict)
    
    # 4. Assertions (Proving integration)
    assert risk_scored_event.event_id == str(conjunction_event.event_id)
    assert risk_scored_event.primary_id == "SAT-12345"
    assert risk_scored_event.secondary_id == "DEB-99999"
    assert risk_scored_event.miss_distance_km == 0.5
    assert risk_scored_event.pc == 0.005
    assert risk_scored_event.primary_cross_section_area_m2 == 12.5
    assert risk_scored_event.orbital_regime == OrbitalRegime.LEO
    
    # Risk should be properly assigned
    assert risk_scored_event.risk_category in [RiskCategory.LOW, RiskCategory.MEDIUM, RiskCategory.HIGH]
    assert 0 <= risk_scored_event.ml_risk_score <= 1.0
    
    # SHAP feature contributions exist
    assert len(risk_scored_event.shap_top_features) > 0
    
    # Because miss_distance is 0.5km (very close) and Pc is 0.005 (high), 
    # the model might classify this as HIGH risk.
    # If it is HIGH risk, maneuver advisory must be present.
    if risk_scored_event.risk_category == RiskCategory.HIGH:
        assert risk_scored_event.maneuver_advisory is not None
        assert risk_scored_event.maneuver_advisory.delta_v_m_s > 0.0
        assert risk_scored_event.maneuver_advisory.burn_direction == "ALONG_TRACK"
        assert risk_scored_event.maneuver_advisory.new_miss_distance_km == 10.0 # Target safety distance
