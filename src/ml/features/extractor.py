import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Compatible features (baseline + new physical features)
FEATURES = [
    'time_to_tca',
    'miss_distance',
    'relative_speed',
    'current_risk',
    'mahalanobis_distance',
    'object_type_encoded',
    'prev_risk',
    'prev_miss_distance',
    'risk_delta',
    'log_miss_distance',
    'log_mahalanobis',
    'risk_speed_interaction',
    'primary_cross_section_area_m2',
    'secondary_cross_section_area_m2',
    'combined_cross_section_area_m2',
    'log_combined_cross_section_area',
    'orbital_regime_encoded'
]

# Mapping for c_object_type or secondary_object_type
OBJECT_TYPE_MAPPING = {
    'PAYLOAD': 0,
    'ROCKET_BODY': 1,
    'DEBRIS': 2,
    'UNKNOWN': 3,
    'TBA': 3  # Kelvins sometimes has TBA
}

ORBITAL_REGIME_MAPPING = {
    'LEO': 0,
    'MEO': 1,
    'GEO': 2,
    'HEO': 3,
    'UNKNOWN': 4
}

def extract_features_from_kelvins(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract baseline features from Kelvins dataset.
    """
    df_feat = pd.DataFrame()
    df_feat['event_id'] = df['event_id']
    df_feat['time_to_tca'] = df['time_to_tca']
    df_feat['miss_distance'] = df['miss_distance']
    df_feat['relative_speed'] = df['relative_speed']
    df_feat['current_risk'] = df['risk']  # Use the row's current risk
    df_feat['mahalanobis_distance'] = df['mahalanobis_distance']
    
    # Categorical encoding
    # Handle NaNs in c_object_type by treating them as UNKNOWN
    obj_types = df['c_object_type'].fillna('UNKNOWN').astype(str).str.upper()
    df_feat['object_type_encoded'] = obj_types.map(OBJECT_TYPE_MAPPING).fillna(3).astype(int)
    
    # Kelvins doesn't have cross sectional area or orbital regime natively that we can join
    # So we must populate them with NaNs to match the schema
    df_feat['primary_cross_section_area_m2'] = np.nan
    df_feat['secondary_cross_section_area_m2'] = np.nan
    df_feat['combined_cross_section_area_m2'] = np.nan
    df_feat['log_combined_cross_section_area'] = np.nan
    df_feat['orbital_regime_encoded'] = np.nan
    
    # Temporal features (not present in raw kelvins single-row extraction)
    df_feat['prev_risk'] = np.nan
    df_feat['prev_miss_distance'] = np.nan
    df_feat['risk_delta'] = np.nan
    df_feat['log_miss_distance'] = np.log1p(df_feat['miss_distance'])
    df_feat['log_mahalanobis'] = np.log1p(df_feat['mahalanobis_distance'])
    df_feat['risk_speed_interaction'] = df_feat['current_risk'] * df_feat['relative_speed']
    
    return df_feat[FEATURES]

def extract_features_from_conjunction_event(event_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Extract baseline features from a single ConjunctionEvent dictionary.
    Requires compatible mapping.
    """
    # Compute time_to_tca in days to match training data.
    import dateutil.parser
    tca = dateutil.parser.parse(str(event_dict['tca']))
    created_at = dateutil.parser.parse(str(event_dict['created_at']))
    time_to_tca_days = (tca - created_at).total_seconds() / 86400.0
    
    # Convert Pc to log10 risk scale.
    pc = event_dict.get('pc', 0.0)
    current_risk = np.log10(pc) if pc > 1e-30 else -30.0
    
    # mahalanobis_distance is unavailable in ConjunctionEvent; defaulting to NaN.
    md = np.nan
    
    obj_type = str(event_dict.get('secondary_object_type', 'UNKNOWN')).upper()
    obj_type_encoded = OBJECT_TYPE_MAPPING.get(obj_type, 3)
    
    pca = event_dict.get('primary_cross_section_area_m2')
    sca = event_dict.get('secondary_cross_section_area_m2')
    # Default missing areas to NaN
    pca_val = float(pca) if pca is not None else np.nan
    sca_val = float(sca) if sca is not None else np.nan
    
    combined_csa = np.nan
    if not np.isnan(pca_val) and not np.isnan(sca_val):
        combined_csa = pca_val + sca_val
        
    log_combined_csa = np.log1p(combined_csa) if not np.isnan(combined_csa) else np.nan
    
    raw_regime = event_dict.get('orbital_regime')
    if raw_regime is None:
        regime_encoded = np.nan
    else:
        regime = str(raw_regime).upper()
        regime_encoded = ORBITAL_REGIME_MAPPING.get(regime, 4)
    
    # Temporal features (provided from state tracking)
    prev_pc = event_dict.get('previous_pc')
    prev_risk = np.log10(prev_pc) if prev_pc and prev_pc > 1e-30 else np.nan
    prev_miss = event_dict.get('previous_miss_distance_km', np.nan)
    
    risk_delta = current_risk - prev_risk if not np.isnan(prev_risk) else np.nan
    log_miss_distance = np.log1p(event_dict.get('miss_distance_km', 0.0))
    log_mahalanobis = np.nan # np.log1p(md)
    risk_speed_interaction = current_risk * event_dict.get('relative_velocity_km_s', 0.0)
    
    data = {
        'time_to_tca': [time_to_tca_days],
        'miss_distance': [event_dict.get('miss_distance_km', 0.0)],
        'relative_speed': [event_dict.get('relative_velocity_km_s', 0.0)],
        'current_risk': [current_risk],
        'mahalanobis_distance': [md],
        'object_type_encoded': [obj_type_encoded],
        'prev_risk': [prev_risk],
        'prev_miss_distance': [prev_miss],
        'risk_delta': [risk_delta],
        'log_miss_distance': [log_miss_distance],
        'log_mahalanobis': [log_mahalanobis],
        'risk_speed_interaction': [risk_speed_interaction],
        'primary_cross_section_area_m2': [pca_val],
        'secondary_cross_section_area_m2': [sca_val],
        'combined_cross_section_area_m2': [combined_csa],
        'log_combined_cross_section_area': [log_combined_csa],
        'orbital_regime_encoded': [regime_encoded]
    }
    # Ensure column order matches FEATURES exactly
    df_out = pd.DataFrame(data)[FEATURES]
    return df_out
