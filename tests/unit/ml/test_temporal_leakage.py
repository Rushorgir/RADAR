import pytest
import pandas as pd
import numpy as np
import os
import sys

from src.ml.ranking.experiments import build_features

def test_temporal_leakage():
    # Construct a dummy dataset simulating descending time_to_tca
    df = pd.DataFrame({
        'event_id': [1, 1, 1, 2, 2],
        'mission_id': [100, 100, 100, 200, 200],
        'time_to_tca': [5.0, 3.0, 1.0, 4.0, 2.0], # Descending per event
        'miss_distance': [1000.0, 800.0, 500.0, 2000.0, 1500.0],
        'relative_speed': [7.0, 7.1, 7.2, 14.0, 14.1],
        'risk': [-10.0, -8.0, -5.0, -9.0, -6.0], # final risks will be -5.0 and -6.0
        'mahalanobis_distance': [10.0, 20.0, 50.0, 5.0, 15.0],
        'c_object_type': ['PAYLOAD', 'PAYLOAD', 'PAYLOAD', 'DEBRIS', 'DEBRIS']
    })
    
    # Needs to be sorted explicitly like load_data does
    df = df.sort_values(by=['event_id', 'time_to_tca'], ascending=[True, False]).reset_index(drop=True)
    
    df_feat = build_features(df)
    
    # Assert previous values come from the correct chronological observation
    assert df_feat.loc[0, 'prev_risk'] == -10.0
    assert df_feat.loc[1, 'prev_risk'] == -10.0
    assert df_feat.loc[2, 'prev_risk'] == -8.0
    
    # Assert future observations cannot enter the feature vector
    assert df_feat.loc[0, 'current_risk'] == -10.0
    assert df_feat.loc[1, 'current_risk'] == -8.0
    
    from src.ml.features.extractor import FEATURES
    assert list(df_feat.columns) == ['event_id', 'target'] + FEATURES
    assert 'final_risk' not in df_feat.columns
    
    # Assert target is correctly derived
    assert df_feat.loc[0, 'target'] == 2
    assert df_feat.loc[1, 'target'] == 2
    assert df_feat.loc[2, 'target'] == 2
    
    assert df_feat.loc[3, 'target'] == 2
    assert df_feat.loc[4, 'target'] == 2

