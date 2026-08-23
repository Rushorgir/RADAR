from __future__ import annotations

import os
import json
from typing import Any
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import shap

from src.ml.features.extractor import OBJECT_TYPE_MAPPING, FEATURES

def get_target_class(final_risk):
    if final_risk >= -6.0: return 2
    elif final_risk >= -8.0: return 1
    else: return 0

DEFAULT_TRAIN_DATA_PATH = os.getenv(
    "TRAIN_DATA_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "cdm_reference", "train_data.csv")),
)
DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "improved"))

def load_data(filepath: str | None = None):
    filepath = filepath or DEFAULT_TRAIN_DATA_PATH
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Training dataset not found at {filepath}")
    df = pd.read_csv(filepath)
    # Sort by event_id and time_to_tca descending (so chronological is top-to-bottom for each event)
    df = df.sort_values(by=['event_id', 'time_to_tca'], ascending=[True, False]).reset_index(drop=True)
    return df

def build_features(df):
    df_feat = pd.DataFrame()
    df_feat['event_id'] = df['event_id']
    df_feat['time_to_tca'] = df['time_to_tca']
    df_feat['miss_distance'] = df['miss_distance']
    df_feat['relative_speed'] = df['relative_speed']
    df_feat['current_risk'] = df['risk']
    df_feat['mahalanobis_distance'] = df['mahalanobis_distance']
    obj_types = df['c_object_type'].fillna('UNKNOWN').astype(str).str.upper()
    df_feat['object_type_encoded'] = obj_types.map(OBJECT_TYPE_MAPPING).fillna(3).astype(int)
    
    # Target
    final_risks = df.groupby('event_id')['risk'].transform('last')
    df_feat['target'] = final_risks.apply(get_target_class)
    
    # Compute temporal and engineered features using only past/current information.
    # The dataframe is sorted by descending time_to_tca, so row i-1 is the chronologically previous observation.
    # Shifted features per event
    df_feat['prev_risk'] = df.groupby('event_id')['risk'].shift(1)
    df_feat['prev_miss_distance'] = df.groupby('event_id')['miss_distance'].shift(1)
    
    # Derived temporal
    df_feat['risk_delta'] = df_feat['current_risk'] - df_feat['prev_risk']
    
    # Non-linear transformations
    df_feat['log_miss_distance'] = np.log1p(df_feat['miss_distance'])
    df_feat['log_mahalanobis'] = np.log1p(df_feat['mahalanobis_distance'])
    
    # Interaction
    df_feat['risk_speed_interaction'] = df_feat['current_risk'] * df_feat['relative_speed']
    
    # Fill temporal NaNs with 0 (e.g. for the first observation)
    df_feat['prev_risk'] = df_feat['prev_risk'].fillna(df_feat['current_risk'])
    df_feat['risk_delta'] = df_feat['risk_delta'].fillna(0)
    df_feat['prev_miss_distance'] = df_feat['prev_miss_distance'].fillna(df_feat['miss_distance'])

    # The mission_id is an arbitrary label in Kelvins and does not guarantee
    # a physical match to NORAD_CAT_ID. Therefore, we must not enrich
    # historical training data with SATCAT.
    df_feat['orbital_regime_encoded'] = np.nan
    df_feat['primary_cross_section_area_m2'] = np.nan
    df_feat['secondary_cross_section_area_m2'] = np.nan
    df_feat['combined_cross_section_area_m2'] = np.nan
    df_feat['log_combined_cross_section_area'] = np.nan
    
    # Ensure correct ordering
    return df_feat[['event_id', 'target'] + FEATURES]

def evaluate_predictions(y_true, y_pred, name="Model"):
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=[0,1,2], zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0,1,2])
    
    return {
        "name": name,
        "accuracy": float(acc),
        "macro_f1": float(np.mean(f1)),
        "LOW": {"p": float(p[0]), "r": float(r[0]), "f1": float(f1[0])},
        "MEDIUM": {"p": float(p[1]), "r": float(r[1]), "f1": float(f1[1])},
        "HIGH": {"p": float(p[2]), "r": float(r[2]), "f1": float(f1[2])},
        "cm": cm.tolist()
    }

def train_lgb(X_train, y_train, X_val, y_val, class_weight, features):
    if isinstance(class_weight, dict):
        w_train = y_train.map(class_weight).values
        w_val = y_val.map(class_weight).values
        train_data = lgb.Dataset(X_train[features], label=y_train, weight=w_train, categorical_feature=['object_type_encoded'])
        val_data = lgb.Dataset(X_val[features], label=y_val, weight=w_val, reference=train_data, categorical_feature=['object_type_encoded'])
        cw = None
    else:
        train_data = lgb.Dataset(X_train[features], label=y_train, categorical_feature=['object_type_encoded'])
        val_data = lgb.Dataset(X_val[features], label=y_val, reference=train_data, categorical_feature=['object_type_encoded'])
        cw = class_weight
    
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'class_weight': cw if cw is not None else '',
        'random_state': 42,
        'verbose': -1
    }
    
    callbacks: list[Any] = [lgb.early_stopping(stopping_rounds=20, verbose=False)]
    model = lgb.train(params, train_data, num_boost_round=500, valid_sets=[val_data], callbacks=callbacks)
    return model

def tune_thresholds(model, X_val, y_val, features):
    # Phase 4
    # Predict probabilities
    probs = model.predict(X_val[features])
    
    best_thresh_high = 0.5
    best_thresh_med = 0.5
    best_score = -1
    
    # We want to maximize HIGH F1 + HIGH Recall + MEDIUM Recall
    for t_high in [0.2, 0.3, 0.4, 0.5]:
        for t_med in [0.2, 0.3, 0.4, 0.5]:
            preds = []
            for p in probs:
                if p[2] >= t_high: preds.append(2)
                elif p[1] >= t_med: preds.append(1)
                else: preds.append(0)
            
            p, r, f1, _ = precision_recall_fscore_support(y_val, preds, labels=[0,1,2], zero_division=0)
            score = r[2]*2 + f1[2] + r[1]
            if score > best_score:
                best_score = score
                best_thresh_high = t_high
                best_thresh_med = t_med
                
    return best_thresh_high, best_thresh_med

def apply_thresholds(probs, t_high, t_med):
    preds = []
    for p in probs:
        if p[2] >= t_high: preds.append(2)
        elif p[1] >= t_med: preds.append(1)
        else: preds.append(0)
    return np.array(preds)

def run_experiments():
    df = load_data()
    df_feat = build_features(df)
    
    base_features = ['time_to_tca', 'miss_distance', 'relative_speed', 'current_risk', 'mahalanobis_distance', 'object_type_encoded']
    all_features = FEATURES
    no_risk_features = [f for f in all_features if f not in ['current_risk', 'prev_risk', 'risk_delta', 'risk_speed_interaction']]
    
    X = df_feat.drop(columns=['target'])
    y = df_feat['target']
    groups = df_feat['event_id']
    
    # Feature missingness
    print("Feature Missingness:")
    for col in all_features:
        missing_pct = X[col].isna().mean() * 100
        print(f"  {col}: {missing_pct:.2f}%")
        
    # Target Leakage Audit
    # Target is final_risk (mapped to class). Current risk is risk at observation.
    # For the last observation of each event, current_risk == final_risk.
    last_rows = df_feat.groupby('event_id').tail(1)
    # the target is based on final risk, so we correlate current_risk with final risk.
    # final_risk wasn't saved, but we can reconstruct it from the target or just use the whole df
    corr = df_feat['current_risk'].corr(df.groupby('event_id')['risk'].transform('last'))
    print(f"\nTarget Leakage Audit: Correlation between current_risk and final_risk = {corr:.4f}")
    

    
    # 80/10/10 split
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    X_train, y_train, g_train = X.iloc[train_idx], y.iloc[train_idx], groups.iloc[train_idx]
    X_temp, y_temp, g_temp = X.iloc[temp_idx], y.iloc[temp_idx], groups.iloc[temp_idx]
    
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    val_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=g_temp))
    X_val, y_val = X_temp.iloc[val_idx], y_temp.iloc[val_idx]
    X_test, y_test = X_temp.iloc[test_idx], y_temp.iloc[test_idx]
    
    results = {}
    models = {}
    
    # A. Current balanced weighting
    print("Training Model A: Balanced Weights")
    m_a = train_lgb(X_train, y_train, X_val, y_val, 'balanced', base_features)
    preds_a = np.argmax(np.asarray(m_a.predict(X_val[base_features])), axis=1)
    results['A_Balanced'] = evaluate_predictions(y_val, preds_a, "Balanced Baseline")
    models['A_Balanced'] = m_a
    
    # B. Custom weights (1:1:1 is uniform, let's try 1:5:20)
    print("Training Model B: Custom Weights (1, 5, 20)")
    custom_wt = {0: 1.0, 1: 5.0, 2: 20.0}
    m_b = train_lgb(X_train, y_train, X_val, y_val, custom_wt, base_features)
    preds_b = np.argmax(np.asarray(m_b.predict(X_val[base_features])), axis=1)
    results['B_CustomWt'] = evaluate_predictions(y_val, preds_b, "Custom Weights (1,5,20)")
    models['B_CustomWt'] = m_b
    
    # C. Stronger HIGH (1, 10, 50)
    print("Training Model C: Stronger HIGH (1, 10, 50)")
    custom_wt2 = {0: 1.0, 1: 10.0, 2: 50.0}
    m_c = train_lgb(X_train, y_train, X_val, y_val, custom_wt2, base_features)
    preds_c = np.argmax(np.asarray(m_c.predict(X_val[base_features])), axis=1)
    results['C_StrongHigh'] = evaluate_predictions(y_val, preds_c, "Strong HIGH (1,10,50)")
    models['C_StrongHigh'] = m_c
    
    # Tune thresholds for Model C
    print("Tuning Thresholds on Model C...")
    t_high, t_med = tune_thresholds(m_c, X_val, y_val, base_features)
    preds_tuned = apply_thresholds(m_c.predict(X_val[base_features]), t_high, t_med)
    results['C_TunedThresh'] = evaluate_predictions(y_val, preds_tuned, f"Model C + Tuned Thresh (H:{t_high}, M:{t_med})")
    
    # Train model without current_risk
    print("Training Model: No current_risk")
    m_no_risk = train_lgb(X_train, y_train, X_val, y_val, 'balanced', no_risk_features)
    preds_no_risk = np.argmax(np.asarray(m_no_risk.predict(X_val[no_risk_features])), axis=1)
    results['No_Risk'] = evaluate_predictions(y_val, preds_no_risk, "No current_risk (Balanced)")
    models['No_Risk'] = m_no_risk
    
    # Train final model with all engineered features
    print("Training Model: All Engineered Features (Model D)")
    m_all = train_lgb(X_train, y_train, X_val, y_val, custom_wt2, all_features)
    # Tune thresholds for m_all
    t_high_all, t_med_all = tune_thresholds(m_all, X_val, y_val, all_features)
    preds_all = apply_thresholds(m_all.predict(X_val[all_features]), t_high_all, t_med_all)
    results['All_Features_Tuned'] = evaluate_predictions(y_val, preds_all, f"All Features + Tuned Thresh (H:{t_high_all}, M:{t_med_all})")
    models['All_Features'] = m_all
    
    # Evaluate best model (All Features + Tuned) vs Baseline on Test Set
    print("Evaluating on Test Set...")
    test_results = {}
    
    # Baseline
    preds_test_base = np.argmax(np.asarray(m_a.predict(X_test[base_features])), axis=1)
    test_results['Baseline'] = evaluate_predictions(y_test, preds_test_base, "Baseline (Test)")
    
    # Best Model (All Features + Tuned)
    preds_test_best = apply_thresholds(m_all.predict(X_test[all_features]), t_high_all, t_med_all)
    test_results['Improved'] = evaluate_predictions(y_test, preds_test_best, "Improved Model (Test)")
    
    # No Risk (Test)
    preds_test_no_risk = np.argmax(np.asarray(m_no_risk.predict(X_test[no_risk_features])), axis=1)
    test_results['No_Risk'] = evaluate_predictions(y_test, preds_test_no_risk, "No Risk Model (Test)")
    
    # Run SHAP on Best Model
    print("Running SHAP analysis...")
    explainer = shap.TreeExplainer(m_all)
    shap_values = explainer.shap_values(X_test[all_features].sample(min(1000, len(X_test)), random_state=42))
    
    # Save results
    with open('experiment_results.json', 'w') as f:
        json.dump({
            "val_results": results,
            "test_results": test_results,
            "best_thresholds": {"high": t_high_all, "med": t_med_all},
            "features": all_features
        }, f, indent=4)
        
    os.makedirs(DEFAULT_MODEL_DIR, exist_ok=True)
    m_all.save_model(os.path.join(DEFAULT_MODEL_DIR, "lightgbm_risk_model.txt"))
    
    with open(os.path.join(DEFAULT_MODEL_DIR, "feature_schema.json"), "w") as f:
        json.dump(all_features, f)
        
    with open(os.path.join(DEFAULT_MODEL_DIR, "thresholds.json"), "w") as f:
        json.dump({"high": t_high_all, "med": t_med_all}, f)

if __name__ == '__main__':
    run_experiments()
