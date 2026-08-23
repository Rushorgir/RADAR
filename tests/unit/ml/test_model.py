import pytest
import os
import sys
import lightgbm as lgb
import numpy as np

from src.ml.features.extractor import FEATURES
from src.ml.ranking.train import get_target_class
from src.ml.ranking.predictor import MLRiskPredictor
from src.shared.interfaces.contracts import RiskCategory

def test_get_target_class():
    assert get_target_class(-5.0) == 2 # HIGH
    assert get_target_class(-6.0) == 2 # HIGH
    assert get_target_class(-7.0) == 1 # MEDIUM
    assert get_target_class(-8.0) == 1 # MEDIUM
    assert get_target_class(-9.0) == 0 # LOW
    assert get_target_class(-30.0) == 0 # LOW

def test_model_loading():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'ml', 'models', 'improved', 'lightgbm_risk_model.txt'))
    if os.path.exists(model_path):
        model = lgb.Booster(model_file=model_path)
        assert model is not None
        
        # Test inference with dummy data
        dummy_data = np.zeros((1, len(FEATURES)))
        preds = np.asarray(model.predict(dummy_data))
        assert preds.shape == (1, 3)
        assert np.isclose(np.sum(preds), 1.0)
    else:
        pytest.skip("Improved model not trained yet.")

def test_ml_risk_predictor():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'ml', 'models', 'improved', 'lightgbm_risk_model.txt'))
    if not os.path.exists(model_path):
        pytest.skip("Improved model not trained yet.")
        
    predictor = MLRiskPredictor(model_path)
    
    event = {
        'event_id': 'test-123',
        'tca': '2026-08-22T10:00:00Z',
        'created_at': '2026-08-20T10:00:00Z',
        'miss_distance_km': 15.0,
        'relative_velocity_km_s': 7.5,
        'pc': 1e-5,
        'secondary_object_type': 'DEBRIS'
    }
    
    result = predictor.predict_risk(event)
    
    assert result.event_id == 'test-123'
    assert result.risk_category in [RiskCategory.LOW, RiskCategory.MEDIUM, RiskCategory.HIGH]
    assert 0.0 <= result.ml_risk_score <= 1.0
    assert len(result.shap_top_features) > 0
