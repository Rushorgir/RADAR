from datetime import datetime

from src.backend.db import crud


def test_get_risk_score(client, db_session):
    event_data = {
        "event_id": "risk-1",
        "primary_id": "1",
        "secondary_id": "2",
        "tca": datetime.utcnow(),
        "miss_distance_km": 1.0,
        "relative_velocity_km_s": 7.0,
        "pc": 1e-4,
        "pc_method": "FOSTER_2D",
        "ml_risk_score": 0.85,
        "risk_category": "HIGH",
        "shap_top_features": [{"feature": "pc", "impact": 0.4}]
    }
    crud.create_conjunction_event(db_session, event_data)
    
    response = client.get("/api/risk/risk-1")
    assert response.status_code == 200
    data = response.json()
    assert data["ml_risk_score"] == 0.85
    assert data["risk_category"] == "HIGH"
    assert len(data["shap_top_features"]) == 1

def test_get_risk_not_found(client):
    response = client.get("/api/risk/missing")
    assert response.status_code == 404
