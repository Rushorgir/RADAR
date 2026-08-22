import pytest
import pandas as pd
import numpy as np
import sys
import os

from src.ml.features.extractor import extract_features_from_kelvins, extract_features_from_conjunction_event, FEATURES

def test_extract_features_from_kelvins():
    df = pd.DataFrame({
        'event_id': [1, 2],
        'time_to_tca': [2.5, 0.5],
        'miss_distance': [1000.0, 500.0],
        'relative_speed': [7.0, 14.0],
        'risk': [-10.0, -5.0],
        'mahalanobis_distance': [10.0, 50.0],
        'c_object_type': ['PAYLOAD', 'UNKNOWN']
    })
    
    df_feat = extract_features_from_kelvins(df)
    
    assert list(df_feat.columns) == FEATURES
    assert df_feat['object_type_encoded'].iloc[0] == 0
    assert df_feat['object_type_encoded'].iloc[1] == 3

def test_extract_features_from_conjunction_event():
    event = {
        'tca': '2026-08-22T10:00:00Z',
        'created_at': '2026-08-20T10:00:00Z',
        'miss_distance_km': 15.0,
        'relative_velocity_km_s': 7.5,
        'pc': 1e-5,
        'secondary_object_type': 'DEBRIS',
        'primary_cross_section_area_m2': 10.5,
        'secondary_cross_section_area_m2': 2.0,
        'orbital_regime': 'LEO'
    }
    
    df_feat = extract_features_from_conjunction_event(event)
    
    assert list(df_feat.columns) == FEATURES
    assert df_feat['time_to_tca'].iloc[0] == 2.0  # 2 days difference
    assert df_feat['miss_distance'].iloc[0] == 15.0
    assert df_feat['relative_speed'].iloc[0] == 7.5
    assert df_feat['current_risk'].iloc[0] == -5.0
    assert np.isnan(df_feat['mahalanobis_distance'].iloc[0])
    assert df_feat['object_type_encoded'].iloc[0] == 2
    assert df_feat['primary_cross_section_area_m2'].iloc[0] == 10.5
    assert df_feat['secondary_cross_section_area_m2'].iloc[0] == 2.0
    assert df_feat['combined_cross_section_area_m2'].iloc[0] == 12.5
    assert df_feat['orbital_regime_encoded'].iloc[0] == 0  # LEO is 0

def test_extract_features_missing_fields():
    event = {
        'tca': '2026-08-22T10:00:00Z',
        'created_at': '2026-08-20T10:00:00Z',
        'miss_distance_km': 15.0,
        'relative_velocity_km_s': 7.5,
        'pc': 1e-5,
        'secondary_object_type': 'DEBRIS'
    }
    
    df_feat = extract_features_from_conjunction_event(event)
    
    assert list(df_feat.columns) == FEATURES
    assert np.isnan(df_feat['primary_cross_section_area_m2'].iloc[0])
    assert np.isnan(df_feat['secondary_cross_section_area_m2'].iloc[0])
    assert np.isnan(df_feat['combined_cross_section_area_m2'].iloc[0])
    assert np.isnan(df_feat['log_combined_cross_section_area'].iloc[0])
    assert np.isnan(df_feat['orbital_regime_encoded'].iloc[0])
