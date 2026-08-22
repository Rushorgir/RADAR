from __future__ import annotations

import os
import sys
import shap
import json
import pandas as pd
import numpy as np
import lightgbm as lgb
import matplotlib.pyplot as plt

from src.ml.ranking.experiments import load_data, build_features

def main():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'improved', 'lightgbm_risk_model.txt'))
    schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'improved', 'feature_schema.json'))
    
    if not os.path.exists(model_path):
        print("Model not found.")
        return
        
    model = lgb.Booster(model_file=model_path)
    with open(schema_path, "r") as f:
        features = json.load(f)
        
    print("Loading data for SHAP analysis...")
    df = load_data()
    df_feat = build_features(df)
    
    X = df_feat[features]
    y = df_feat['target']
    
    # We only need a subset for SHAP plots (background data)
    X_sample = X.sample(1000, random_state=42)
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'docs', 'images'))
    os.makedirs(output_dir, exist_ok=True)
    
    # Global Plot: Summary Plot (Bar) for all classes
    plt.figure()
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.savefig(os.path.join(output_dir, 'shap_summary_global.png'), bbox_inches='tight')
    plt.close()
    
    # Find a highly severe event in the sample
    probs = model.predict(X_sample)
    high_risk_idx = np.argmax(probs[:, 2]) # index with highest probability of HIGH risk
    
    # Local plot for that specific event
    event_shap = [s[high_risk_idx] for s in shap_values] if isinstance(shap_values, list) else shap_values[high_risk_idx, :, :]
    
    plt.figure()
    # If shap_values is a list, class 2 is index 2
    if isinstance(shap_values, list):
        shap.waterfall_plot(shap.Explanation(values=shap_values[2][high_risk_idx], 
                                          base_values=explainer.expected_value[2], 
                                          data=X_sample.iloc[high_risk_idx], 
                                          feature_names=features), show=False)
    else:
        shap.waterfall_plot(shap.Explanation(values=shap_values[high_risk_idx, :, 2], 
                                          base_values=explainer.expected_value[2], 
                                          data=X_sample.iloc[high_risk_idx], 
                                          feature_names=features), show=False)
    
    plt.savefig(os.path.join(output_dir, 'shap_local_high_risk.png'), bbox_inches='tight')
    plt.close()
    print(f"SHAP plots saved to {output_dir}")

if __name__ == "__main__":
    main()
