# AI-3: ML Risk Ranking Module — Owner: Udarsh

## Responsibility
- Feature engineering from conjunction events
- LightGBM risk ranking model (with TabPFN benchmark)
- SHAP explainability integration
- Model training, evaluation, and inference

## Sub-modules

### `features/` — Feature Engineering
- Extract features: miss distance, relative velocity, cross-section area,
  orbital regime, object type, historical Pc trend
- Feature scaling and preprocessing

### `ranking/` — Model Training & Inference
- LightGBM classifier/regressor for risk scoring
- TabPFN benchmark comparison
- Model serialization and loading

### `explainability/` — SHAP Integration
- SHAP value computation per prediction
- Top-N feature extraction for each event
- Visualization helpers for SHAP plots

## Input Contract ← AI-2 (Rushaan)
Conjunction events with miss_distance, relative_velocity, Pc, combined covariance, etc.

## Output Contract → Backend (Balaganesh)
Risk-scored events with ml_risk_score, risk_category, shap_top_features
