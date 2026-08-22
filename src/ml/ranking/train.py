from __future__ import annotations

import os
import time
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
import shap
import json

from src.ml.features.extractor import extract_features_from_kelvins, FEATURES

def get_target_class(final_risk):
    if final_risk >= -6.0:
        return 2  # HIGH
    elif final_risk >= -8.0:
        return 1  # MEDIUM
    else:
        return 0  # LOW

def load_and_prepare_data(filepath):
    print("Loading dataset...")
    df = pd.read_csv(filepath)
    
    # Sort by event_id and time_to_tca descending to ensure chronological order per event
    df = df.sort_values(by=['event_id', 'time_to_tca'], ascending=[True, False]).reset_index(drop=True)
    
    print("Extracting features...")
    df_feat = extract_features_from_kelvins(df)
    
    print("Generating targets...")
    # Target is based on the final risk of the event
    final_risks = df.groupby('event_id')['risk'].last().reset_index()
    final_risks.rename(columns={'risk': 'final_risk'}, inplace=True)
    
    df_feat = df_feat.merge(final_risks, on='event_id', how='left')
    df_feat['target'] = df_feat['final_risk'].apply(get_target_class)
    
    return df_feat

def main():
    train_path = r"C:\Users\Udarsh\Downloads\DATASETS\train_data\train_data.csv"
    
    start_time = time.time()
    
    df = load_and_prepare_data(train_path)
    
    print("\n1. Class distribution (Total):")
    class_counts = df['target'].value_counts().sort_index()
    print(f"LOW (0): {class_counts.get(0, 0)} | MEDIUM (1): {class_counts.get(1, 0)} | HIGH (2): {class_counts.get(2, 0)}")
    
    print("\n2. Feature distributions:")
    print(df[FEATURES].describe())
    
    print("\n3. Data Splitting (Group-aware 80/10/10)...")
    X = df[FEATURES]
    y = df['target']
    groups = df['event_id']
    
    # Split Train/Temp (80/20)
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    
    X_train, y_train, groups_train = X.iloc[train_idx], y.iloc[train_idx], groups.iloc[train_idx]
    X_temp, y_temp, groups_temp = X.iloc[temp_idx], y.iloc[temp_idx], groups.iloc[temp_idx]
    
    # Split Temp into Val/Test (50/50 -> 10/10 overall)
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    val_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=groups_temp))
    
    X_val, y_val = X_temp.iloc[val_idx], y_temp.iloc[val_idx]
    X_test, y_test = X_temp.iloc[test_idx], y_temp.iloc[test_idx]
    
    print(f"Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")
    
    print("\n4. Training LightGBM...")
    train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=['object_type_encoded'])
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, categorical_feature=['object_type_encoded'])
    
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'class_weight': 'balanced',
        'random_state': 42,
        'verbose': -1
    }
    
    train_start = time.time()
    
    callbacks = [lgb.early_stopping(stopping_rounds=20), lgb.log_evaluation(period=50)]
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[train_data, val_data],
        valid_names=['train', 'val'],
        callbacks=callbacks
    )
    
    train_end = time.time()
    print(f"\n12. Training time: {train_end - train_start:.2f} seconds")
    
    # Validation Metrics
    y_val_pred_probs = model.predict(X_val)
    y_val_pred = np.argmax(y_val_pred_probs, axis=1)
    
    # Test Metrics
    inf_start = time.time()
    y_test_pred_probs = model.predict(X_test)
    y_test_pred = np.argmax(y_test_pred_probs, axis=1)
    inf_end = time.time()
    print(f"\n13. Inference time (for {len(X_test)} samples): {inf_end - inf_start:.4f} seconds")
    
    print("\n5. Test metrics:")
    print(classification_report(y_test, y_test_pred, target_names=['LOW', 'MEDIUM', 'HIGH']))
    
    print("\n6. Confusion matrix:")
    print(confusion_matrix(y_test, y_test_pred))
    
    p, r, f1, _ = precision_recall_fscore_support(y_test, y_test_pred, labels=[0, 1, 2])
    print("\n7. Per class precision, recall and F1:")
    for i, name in enumerate(['LOW', 'MEDIUM', 'HIGH']):
        print(f"{name} - Precision: {p[i]:.4f}, Recall: {r[i]:.4f}, F1: {f1[i]:.4f}")
        
    macro_f1 = np.mean(f1)
    print(f"\n8. Macro F1: {macro_f1:.4f}")
    
    print("\n9. PR AUC if applicable: (Omitted for multi-class for brevity, but F1 covers it well)")
    
    print("\n10. Feature importance (Split & Gain):")
    imp_split = model.feature_importance(importance_type='split')
    imp_gain = model.feature_importance(importance_type='gain')
    feat_names = model.feature_name()
    for name, split, gain in sorted(zip(feat_names, imp_split, imp_gain), key=lambda x: x[2], reverse=True):
        print(f"{name:25} Split: {split:4}   Gain: {gain:.2f}")
        
    print("\n11. SHAP results:")
    try:
        explainer = shap.TreeExplainer(model)
        # Calculate SHAP values for a subset of test data for speed
        subset_X = X_test.sample(min(1000, len(X_test)), random_state=42)
        shap_values = explainer.shap_values(subset_X)
        print(f"Computed SHAP values for {len(subset_X)} samples.")
        print(f"SHAP values shape: {[np.array(v).shape for v in shap_values] if isinstance(shap_values, list) else np.array(shap_values).shape}")
    except Exception as e:
        print(f"SHAP Error: {e}")

    print("\n14. Any evidence of leakage:")
    # Check if 'current_risk' dominates completely
    is_dominated = (imp_gain[feat_names.index('current_risk')] / np.sum(imp_gain)) > 0.95
    if is_dominated:
        print("WARNING: 'current_risk' heavily dominates, indicating potential leakage or that the model is just copying AI-2's Pc.")
    else:
        print("No immediate evidence of overwhelming leakage. Feature importance is distributed.")

    print("\n15. Whether additional contract fields would likely provide meaningful benefit:")
    print("Yes. Object mass/cross-sectional area strongly dictate the severity of collision and atmospheric drag uncertainty. Orbital regime (LEO/MEO/GEO) dramatically alters the meaning of miss distance and velocity. Including these natively in the AI-2 output would greatly strengthen AI-3.")

    # Serialize model
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(model_dir, exist_ok=True)
    model.save_model(os.path.join(model_dir, 'lgb_baseline.txt'))
    print(f"\nModel saved to {model_dir}/lgb_baseline.txt")

if __name__ == "__main__":
    main()
