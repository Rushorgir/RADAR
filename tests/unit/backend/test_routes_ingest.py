
def test_ingest_conjunction(client):
    payload = {
        "event_id": "uuid-1234",
        "primary_id": "1000",
        "secondary_id": "2000",
        "tca": "2024-01-01T00:00:00Z",
        "miss_distance_km": 2.5,
        "relative_velocity_km_s": 12.0,
        "pc": 0.0005,
        "pc_method": "FOSTER_2D",
        "combined_hard_body_radius_km": 0.015,
        "primary_object_type": "PAYLOAD",
        "secondary_object_type": "DEBRIS"
    }
    
    response = client.post("/api/ingest/conjunction", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "uuid-1234"
    assert data["primary_object_type"] == "PAYLOAD"

def test_ingest_risk_score(client):
    # First create an event
    test_ingest_conjunction(client)
    
    payload = {
        "event_id": "uuid-1234",
        "ml_risk_score": 0.88,
        "risk_category": "HIGH",
        "shap_top_features": [
            {"feature": "miss_distance", "impact": 0.5}
        ]
    }
    
    response = client.post("/api/ingest/risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ml_risk_score"] == 0.88
    assert data["risk_category"] == "HIGH"
    assert data["shap_top_features"][0]["feature"] == "miss_distance"
