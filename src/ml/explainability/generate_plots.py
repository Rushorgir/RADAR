from __future__ import annotations

import os
import shap
import json
import pandas as pd
import numpy as np
import lightgbm as lgb

from src.ml.ranking.experiments import load_data, build_features

def main():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        print("INFO: 'matplotlib' is not installed. Skipping plot rendering.")
        return
    
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'improved', 'lightgbm_risk_model.txt'))
    schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'improved', 'feature_schema.json'))
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}.")
        return
    if not os.path.exists(schema_path):
        print(f"Feature schema not found at {schema_path}.")
        return
        
    model = lgb.Booster(model_file=model_path)
    with open(schema_path, "r") as f:
        features = json.load(f)
        
    try:
        df = load_data()
    except Exception as e:
        print(f"INFO: Could not load training data ({e}). Skipping offline plot generation.")
        return
        
    print("Loading data for SHAP analysis...")
    df_feat = build_features(df)
    
    X = df_feat[features]
    
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
    probs = np.asarray(model.predict(X_sample))
    high_risk_idx = int(np.argmax(probs[:, 2]))  # index with highest probability of HIGH risk
    
    # Local plot for that specific event
    plt.figure()
    base_values = (
        explainer.expected_value[2]
        if isinstance(explainer.expected_value, (list, np.ndarray))
        else (explainer.expected_value if explainer.expected_value is not None else 0.0)
    )
    # If shap_values is a list, class 2 is index 2
    if isinstance(shap_values, list):
        shap.waterfall_plot(shap.Explanation(values=shap_values[2][high_risk_idx], 
                                          base_values=base_values, 
                                          data=X_sample.iloc[high_risk_idx], 
                                          feature_names=features), show=False)
    else:
        shap.waterfall_plot(shap.Explanation(values=shap_values[high_risk_idx, :, 2], 
                                          base_values=base_values, 
                                          data=X_sample.iloc[high_risk_idx], 
                                          feature_names=features), show=False)
    
    plt.savefig(os.path.join(output_dir, 'shap_local_high_risk.png'), bbox_inches='tight')
    plt.close()
    print(f"SHAP plots saved to {output_dir}")

if __name__ == "__main__":
    main()
