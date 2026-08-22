import os
import json
import pytest
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))
from ml.features.extractor import FEATURES

def test_feature_schema_parity():
    schema_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'ml', 'models', 'improved', 'feature_schema.json')
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    assert schema == FEATURES, "feature_schema.json does not match FEATURES in extractor.py"

def test_thresholds_configuration():
    thresh_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'ml', 'models', 'improved', 'thresholds.json')
    with open(thresh_path, 'r') as f:
        thresholds = json.load(f)
        
    high = thresholds.get("high")
    med = thresholds.get("med")
    
    assert high is not None
    assert med is not None
    
    assert 0.0 <= med <= high <= 1.0, "Invalid threshold configuration range"
