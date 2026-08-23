from __future__ import annotations

import os
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

from src.ml.features.extractor import OBJECT_TYPE_MAPPING
from src.ml.ranking.experiments import load_data, build_features, get_target_class

def evaluate_thresholds(y_true, probs, t_high, t_med):
    preds = []
    for p in probs:
        if p[2] >= t_high: preds.append(2)
        elif p[1] >= t_med: preds.append(1)
        else: preds.append(0)
    
    acc = accuracy_score(y_true, preds)
    p, r, f1, _ = precision_recall_fscore_support(y_true, preds, labels=[0,1,2], zero_division=0)
    cm = confusion_matrix(y_true, preds, labels=[0,1,2])
    
    num_high = sum(1 for x in preds if x == 2)
    pct_high = num_high / len(preds) * 100
    
    return {
        "t_high": t_high,
        "t_med": t_med,
        "acc": acc,
        "macro_f1": np.mean(f1),
        "HIGH_p": p[2], "HIGH_r": r[2], "HIGH_f1": f1[2],
        "MED_p": p[1], "MED_r": r[1], "MED_f1": f1[1],
        "LOW_f1": f1[0],
        "num_high": num_high,
        "pct_high": pct_high
    }

DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "improved"))

def main():
    print("Loading data...")
    try:
        df = load_data()
    except FileNotFoundError as e:
        print(f"ERROR: Could not load training dataset ({e}).")
        print("Please place train_data.csv in data/cdm_reference/ or set TRAIN_DATA_PATH env var.")
        return
        
    df_feat = build_features(df)
    
    schema_path = os.path.join(DEFAULT_MODEL_DIR, "feature_schema.json")
    if not os.path.exists(schema_path):
        print(f"ERROR: Feature schema not found at {schema_path}.")
        return
        
    with open(schema_path, "r") as f:
        all_features = json.load(f)
        
    X = df_feat.drop(columns=['target'])
    y = df_feat['target']
    groups = df_feat['event_id']
    
    # Same split as experiments.py
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    X_temp, y_temp, g_temp = X.iloc[temp_idx], y.iloc[temp_idx], groups.iloc[temp_idx]
    
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    val_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=g_temp))
    X_val, y_val = X_temp.iloc[val_idx], y_temp.iloc[val_idx]
    X_test, y_test = X_temp.iloc[test_idx], y_temp.iloc[test_idx]
    
    # Load model
    model_path = os.path.join(DEFAULT_MODEL_DIR, "lightgbm_risk_model.txt")
    model = lgb.Booster(model_file=model_path)
    
    val_probs = model.predict(X_val[all_features])
    
    thresholds_path = os.path.join(DEFAULT_MODEL_DIR, "thresholds.json")
    with open(thresholds_path, "r") as f:
        thresholds_config = json.load(f)
        prod_t_high = float(thresholds_config["high"])
        prod_t_med = float(thresholds_config["med"])
        
    if not (0.0 <= prod_t_med <= prod_t_high <= 1.0):
        raise ValueError(f"Invalid production thresholds: med={prod_t_med}, high={prod_t_high}")
        
    # Always include the exact production high threshold in the sweep
    thresholds = sorted(list(set([0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80] + [prod_t_high])))
    
    print("\n--- Validation Results ---")
    results = []
    prod_res = None
    
    for t_high in thresholds:
        if t_high < prod_t_med:
            continue
            
        res = evaluate_thresholds(y_val, val_probs, t_high, prod_t_med)
        results.append(res)
        marker = " <--- PROD" if abs(t_high - prod_t_high) < 1e-5 else ""
        print(f"H_Thresh: {t_high:.2f}{marker} | H_Recall: {res['HIGH_r']:.4f} | H_Prec: {res['HIGH_p']:.4f} | H_F1: {res['HIGH_f1']:.4f} | Acc: {res['acc']:.4f} | Alerts: {res['pct_high']:.2f}%")
        
        if abs(t_high - prod_t_high) < 1e-5:
            prod_res = res
            
    print("\n--- Production Config Exact Evaluation ---")
    print(f"Production HIGH threshold: {prod_t_high}")
    print(f"Production MEDIUM threshold: {prod_t_med}")
    print(f"Validation HIGH recall: {prod_res['HIGH_r']}")
    print(f"Validation HIGH precision: {prod_res['HIGH_p']}")
    print(f"Validation HIGH F1: {prod_res['HIGH_f1']}")
    print(f"Validation MEDIUM recall: {prod_res['MED_r']}")
    print(f"Validation MEDIUM precision: {prod_res['MED_p']}")
    print(f"Validation MEDIUM F1: {prod_res['MED_f1']}")
    print(f"Validation accuracy: {prod_res['acc']}")

    test_probs = model.predict(X_test[all_features])
    
    with open("threshold_analysis_data.json", "w") as f:
        json.dump({
            "val_results": results,
            "y_test": y_test.tolist(),
            "test_probs": test_probs.tolist()
        }, f)

if __name__ == '__main__':
    main()
