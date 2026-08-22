import shap
import pandas as pd
import numpy as np
import lightgbm as lgb
from typing import List, Dict, Any

class RiskExplainer:
    def __init__(self, model: lgb.Booster, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        self.explainer = shap.TreeExplainer(model)
        
    def explain_instance(self, features: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Explain a single prediction.
        Returns a list of dicts with feature names and their impact (SHAP value)
        for the predicted class.
        """
        # SHAP values shape for multiclass: (n_samples, n_features, n_classes)
        # or list of arrays depending on shap version.
        shap_values = self.explainer.shap_values(features)
        
        # Predict to find which class was chosen
        preds = self.model.predict(features)
        predicted_class = np.argmax(preds[0])
        
        # Extract SHAP values for the predicted class
        if isinstance(shap_values, list):
            class_shap = shap_values[predicted_class][0]
        else:
            # shap >= 0.40 often returns a tensor of shape (n_samples, n_features, n_classes)
            if len(shap_values.shape) == 3:
                class_shap = shap_values[0, :, predicted_class]
            else:
                class_shap = shap_values[0]
                
        # Pair feature names with SHAP values
        contributions = []
        for name, impact in zip(self.feature_names, class_shap):
            contributions.append({'feature': name, 'impact': float(impact)})
            
        # Sort by absolute impact descending
        contributions.sort(key=lambda x: abs(x['impact']), reverse=True)
        return contributions
