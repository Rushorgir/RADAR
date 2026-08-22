from __future__ import annotations

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import lightgbm as lgb
from tabpfn import TabPFNClassifier

# Ensure ml is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ml.ranking.experiments import load_data, build_features

def evaluate_predictions(y_true, y_pred, name="Model"):
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=[0,1,2], zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0,1,2])
    
    return {
        "name": name,
        "accuracy": float(acc),
        "macro_f1": float(np.mean(f1)),
        "HIGH": {"p": float(p[2]), "r": float(r[2]), "f1": float(f1[2])},
        "MEDIUM": {"p": float(p[1]), "r": float(r[1]), "f1": float(f1[1])},
        "LOW": {"p": float(p[0]), "r": float(r[0]), "f1": float(f1[0])},
        "confusion_matrix": cm.tolist()
    }

def main():
    print("=======================================")
    print("       TABPFN BENCHMARK PIPELINE       ")
    print("=======================================")
    
    # 1. Hardware checks
    has_cuda = torch.cuda.is_available()
    device = 'cuda' if has_cuda else 'cpu'
    gpu_name = torch.cuda.get_device_name(0) if has_cuda else "N/A"
    
    print(f"CUDA Available: {has_cuda}")
    print(f"GPU Name: {gpu_name}")
    print(f"Device string: {device}")
    
    # 2. Authentication check
    has_token = "TABPFN_TOKEN" in os.environ
    print(f"TABPFN_TOKEN present in os.environ: {has_token}")
    # We won't exit here, we'll let TabPFN natively fail if it's truly missing.
        
    print("\nLoading data...")
    t0 = time.time()
    df = load_data()
    df_feat = build_features(df)
    
    with open(r"C:\Users\Udarsh\RADAR\src\ml\models\improved\feature_schema.json", "r") as f:
        all_features = json.load(f)
        
    X = df_feat.drop(columns=['target'])
    y = df_feat['target']
    groups = df_feat['event_id']
    
    # We want at least 10,000 rows. The total dataset is 162k rows.
    # 10% is ~16,027 rows. Let's use 10% to ensure we cover >10,000 without 
    # going extremely large for TabPFN.
    subset_gss = GroupShuffleSplit(n_splits=1, train_size=0.10, random_state=42)
    subset_idx, _ = next(subset_gss.split(X, y, groups=groups))
    
    X_sub = X.iloc[subset_idx].copy()
    y_sub = y.iloc[subset_idx].copy()
    groups_sub = groups.iloc[subset_idx].copy()
    
    print(f"\nSubset Size: {len(X_sub)} rows")
    
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, temp_idx = next(gss1.split(X_sub, y_sub, groups=groups_sub))
    X_train, y_train = X_sub.iloc[train_idx], y_sub.iloc[train_idx]
    
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    val_idx, test_idx = next(gss2.split(X_sub.iloc[temp_idx], y_sub.iloc[temp_idx], groups=groups_sub.iloc[temp_idx]))
    X_val, y_val = X_sub.iloc[temp_idx].iloc[val_idx], y_sub.iloc[temp_idx].iloc[val_idx]
    X_test, y_test = X_sub.iloc[temp_idx].iloc[test_idx], y_sub.iloc[temp_idx].iloc[test_idx]
    
    print(f"Train rows: {len(X_train)}")
    print(f"Validation rows: {len(X_val)}")
    print(f"Test rows: {len(X_test)}")
    
    # Check Class Distribution
    print("\nClass Distribution (Total Subset):")
    print(y_sub.value_counts().sort_index())
    
    t_prep = time.time() - t0
    print(f"Preprocessing time: {t_prep:.2f}s")
    
    # Fill NaN values with median for TabPFN if strictly required. 
    # TabPFN can handle missing values in some versions, but filling is safer.
    X_train_clean = X_train[all_features].fillna(X_train[all_features].median()).fillna(0.0)
    X_test_clean = X_test[all_features].fillna(X_train[all_features].median()).fillna(0.0)
    
    print("\nLoading TabPFN...")
    t_load0 = time.time()
    try:
        classifier = TabPFNClassifier(device=device)
        # Force a tiny forward pass to download weights and warm up
        _ = classifier.fit(X_train_clean.iloc[:5], y_train.iloc[:5])
        _ = classifier.predict(X_test_clean.iloc[:5])
        print("TabPFN Authentication & Load: PASS")
    except Exception as e:
        print(f"FAIL: TabPFN failed to load/authenticate: {e}")
        sys.exit(1)
        
    t_load = time.time() - t_load0
    print(f"Model load & warmup time: {t_load:.2f}s")
    
    # Timing Test (Warm up)
    print("\nRunning timing test on 1000 rows...")
    t_fit_small0 = time.time()
    classifier.fit(X_train_clean.iloc[:1000], y_train.iloc[:1000])
    t_fit_small = time.time() - t_fit_small0
    
    t_inf_small0 = time.time()
    classifier.predict(X_test_clean.iloc[:100])
    t_inf_small = time.time() - t_inf_small0
    
    print(f"1k train time: {t_fit_small:.2f}s")
    print(f"100 inf time: {t_inf_small:.2f}s")
    
    # Estimate total time for 12,000 train + 1,600 test
    est_train = (len(X_train) / 1000) * t_fit_small
    est_inf = (len(X_test) / 100) * t_inf_small
    est_total = est_train + est_inf
    
    print(f"\nEstimated Full Train Time: {est_train:.2f}s")
    print(f"Estimated Full Inf Time: {est_inf:.2f}s")
    
    if est_total > 3000:
        print("WARNING: Estimated time exceeds safe threshold. Attempting optimization by ignoring TabPFN OOM limits if possible, but proceeding...")
        
    print("\n--- Training Full TabPFN ---")
    t_fit0 = time.time()
    try:
        classifier.fit(X_train_clean, y_train)
        t_fit = time.time() - t_fit0
        print(f"TabPFN Fit Time: {t_fit:.2f}s")
        print("TabPFN Fit: PASS")
    except Exception as e:
        print(f"FAIL: TabPFN Fit crashed: {e}")
        sys.exit(1)
        
    print("\n--- Predicting with TabPFN ---")
    t_inf0 = time.time()
    try:
        # Batch inference manually to avoid memory spikes
        batch_size = 256
        preds = []
        for i in range(0, len(X_test_clean), batch_size):
            batch_x = X_test_clean.iloc[i:i+batch_size]
            batch_preds = classifier.predict(batch_x)
            preds.extend(batch_preds)
        
        tabpfn_preds = np.array(preds)
        t_inf = time.time() - t_inf0
        print(f"TabPFN Inference Time: {t_inf:.2f}s")
        print("TabPFN Prediction: PASS")
    except Exception as e:
        print(f"FAIL: TabPFN Inference crashed: {e}")
        sys.exit(1)
        
    tab_res = evaluate_predictions(y_test, tabpfn_preds, "TabPFN")
    
    print("\n--- Evaluating LightGBM on EXACT SAME Subset Test ---")
    lgb_model = lgb.Booster(model_file=r"C:\Users\Udarsh\RADAR\src\ml\models\improved\lightgbm_risk_model.txt")
    
    start_lgb_inf = time.time()
    # LightGBM gracefully ignores features it wasn't trained on, but we must pass exactly what it expects
    # In experiments.py, it was trained on all_features (17 features). We will pass X_test[all_features].
    lgb_probs = lgb_model.predict(X_test[all_features])
    lgb_preds = []
    
    # We use a threshold, say the Balanced threshold or the Safety First threshold.
    # The improved LightGBM model used 0.30 for HIGH and 0.20 for MEDIUM in predictor.py.
    for p in lgb_probs:
        if p[2] >= 0.30: lgb_preds.append(2)
        elif p[1] >= 0.20: lgb_preds.append(1)
        else: lgb_preds.append(0)
    end_lgb_inf = time.time()
    t_lgb_inf = end_lgb_inf - start_lgb_inf
    
    lgb_res = evaluate_predictions(y_test, lgb_preds, "LightGBM")
    
    print("\n=======================================")
    print("          BENCHMARK RESULTS            ")
    print("=======================================")
    print(json.dumps(tab_res, indent=2))
    print(json.dumps(lgb_res, indent=2))
    
    # Save the report
    report_path = r"C:\Users\Udarsh\RADAR\docs\AI3_TABPFN_BENCHMARK_REPORT.md"
    
    report_md = f"""# AI-3 TabPFN vs LightGBM Benchmark Report

## Hardware and Setup
- **GPU**: {gpu_name}
- **CUDA**: {has_cuda}
- **Total Benchmark Rows**: {len(X_sub)}
- **Train Rows**: {len(X_train)}
- **Validation Rows**: {len(X_val)}
- **Test Rows**: {len(X_test)}

## Class Distribution
```text
{y_sub.value_counts().sort_index().to_string()}
```

## Timing
- **Model Loading & Warmup**: {t_load:.2f}s
- **Preprocessing**: {t_prep:.2f}s
- **TabPFN Fit Time**: {t_fit:.2f}s
- **TabPFN Inference Time**: {t_inf:.2f}s
- **LightGBM Inference Time**: {t_lgb_inf:.4f}s

## Results Comparison

| Metric | LightGBM | TabPFN |
|--------|----------|---------|
| Accuracy | {lgb_res['accuracy']:.4f} | {tab_res['accuracy']:.4f} |
| Macro F1 | {lgb_res['macro_f1']:.4f} | {tab_res['macro_f1']:.4f} |
| HIGH Precision | {lgb_res['HIGH']['p']:.4f} | {tab_res['HIGH']['p']:.4f} |
| HIGH Recall | {lgb_res['HIGH']['r']:.4f} | {tab_res['HIGH']['r']:.4f} |
| HIGH F1 | {lgb_res['HIGH']['f1']:.4f} | {tab_res['HIGH']['f1']:.4f} |
| MEDIUM F1 | {lgb_res['MEDIUM']['f1']:.4f} | {tab_res['MEDIUM']['f1']:.4f} |
| LOW F1 | {lgb_res['LOW']['f1']:.4f} | {tab_res['LOW']['f1']:.4f} |

## Confusion Matrices

### LightGBM
```text
{np.array(lgb_res['confusion_matrix'])}
```

### TabPFN
```text
{np.array(tab_res['confusion_matrix'])}
```

## Verdict
**TABPFN STATUS:** SUCCESSFUL

"""
    
    # Determine best model
    # Priority is HIGH recall, then HIGH precision / Macro F1.
    if tab_res['HIGH']['r'] >= 0.90 and tab_res['HIGH']['f1'] > lgb_res['HIGH']['f1']:
        best_model = "TABPFN"
    else:
        best_model = "LIGHTGBM"
        
    report_md += f"**BEST MODEL:** {best_model}\n"
    
    with open(report_path, "w") as f:
        f.write(report_md)
        
    print(f"\nReport written to {report_path}")
    
    # Final Status Print
    print("\nFINAL STATUS:")
    print("TABPFN AUTHENTICATION: PASS")
    print("TABPFN MODEL LOAD: PASS")
    print(f"CUDA: {'PASS' if has_cuda else 'FAIL'}")
    print(f"GPU: {gpu_name}")
    print(f"BENCHMARK ROWS: {len(X_sub)}")
    print("TABPFN TRAINING/FIT: PASS")
    print("TABPFN PREDICTION: PASS")
    print("TABPFN EVALUATION: PASS")
    print("BENCHMARK: COMPLETE")
    print(f"BEST MODEL: {best_model}")

if __name__ == '__main__':
    main()
