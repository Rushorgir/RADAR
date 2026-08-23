import io
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from src.backend.api.main import app
from src.backend.api.dataset_pipeline import run_dataset_pipeline

client = TestClient(app)

def test_list_datasets():
    response = client.get("/api/datasets/")
    assert response.status_code == 200
    data = response.json()
    assert "datasets" in data
    assert "default" in data["datasets"]

def test_import_dataset_api_endpoint():
    sample_path = Path("data/sample_import.txt")
    assert sample_path.exists()
    
    with open(sample_path, "rb") as f:
        response = client.post(
            "/api/datasets/import",
            data={"dataset_name": "api_test_ds"},
            files={"file": ("sample_import.txt", f, "text/plain")}
        )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Dataset import started."
    assert response.json()["dataset_name"] == "api_test_ds"

@pytest.mark.anyio
async def test_full_dataset_workflow_and_calculations():
    """
    Comprehensive workflow test:
    1. Import custom TLE dataset.
    2. SGP4 orbit propagation calculation.
    3. Conjunction screening & Pc calculation.
    4. ML risk classification & scoring.
    5. Database multi-tenant ingestion.
    6. Retrieval across all display endpoints (TLEs, Positions, Conjunctions, Risk, Re-entry, Summary).
    7. Multi-dataset isolation validation.
    """
    dataset_alpha = "dataset_alpha"
    dataset_beta = "dataset_beta"
    
    # Dataset Alpha has 5 objects
    alpha_text = Path("data/sample_import.txt").read_text()
    # Dataset Beta has 2 objects (ISS + Poisk)
    beta_text = "\n".join(alpha_text.splitlines()[:6]) + "\n"
    
    # 1. Run full calculation pipelines for both datasets
    await run_dataset_pipeline(dataset_alpha, alpha_text)
    await run_dataset_pipeline(dataset_beta, beta_text)
    
    # 2. Verify dataset listing reflects both
    res_datasets = client.get("/api/datasets/")
    assert res_datasets.status_code == 200
    all_datasets = res_datasets.json()["datasets"]
    assert dataset_alpha in all_datasets
    assert dataset_beta in all_datasets
    
    # 3. Verify TLE Catalog Isolation
    res_alpha_tle = client.get(f"/api/tle/?dataset={dataset_alpha}")
    assert res_alpha_tle.status_code == 200
    alpha_tle_data = res_alpha_tle.json()
    assert alpha_tle_data["total"] == 5
    assert len(alpha_tle_data["items"]) == 5
    
    res_beta_tle = client.get(f"/api/tle/?dataset={dataset_beta}")
    assert res_beta_tle.status_code == 200
    beta_tle_data = res_beta_tle.json()
    assert beta_tle_data["total"] == 2
    assert len(beta_tle_data["items"]) == 2
    
    # 4. Verify Single Object Lookup scoped to Dataset
    first_obj_id = alpha_tle_data["items"][0]["object_id"]
    res_single = client.get(f"/api/tle/{first_obj_id}?dataset={dataset_alpha}")
    assert res_single.status_code == 200
    assert res_single.json()["object_id"] == first_obj_id
    
    # 5. Verify Real SGP4 Propagated Positions for Globe Rendering
    res_alpha_pos = client.get(f"/api/tle/positions?dataset={dataset_alpha}")
    assert res_alpha_pos.status_code == 200
    alpha_positions = res_alpha_pos.json()["positions"]
    assert len(alpha_positions) == 5
    for pos in alpha_positions:
        assert "latitude_deg" in pos
        assert "longitude_deg" in pos
        assert "altitude_km" in pos
        assert pos["altitude_km"] > 0
    
    res_beta_pos = client.get(f"/api/tle/positions?dataset={dataset_beta}")
    assert res_beta_pos.status_code == 200
    assert len(res_beta_pos.json()["positions"]) == 2
    
    # 6. Verify Conjunction Calculations and Event Details
    res_conj_alpha = client.get(f"/api/conjunctions/?dataset={dataset_alpha}")
    assert res_conj_alpha.status_code == 200
    conj_alpha = res_conj_alpha.json()
    assert conj_alpha["total"] == 1
    event_id = conj_alpha["items"][0]["event_id"]
    
    # Lookup by Event ID
    res_event = client.get(f"/api/conjunctions/{event_id}?dataset={dataset_alpha}")
    assert res_event.status_code == 200
    assert res_event.json()["event_id"] == event_id
    assert res_event.json()["miss_distance_km"] >= 0
    assert res_event.json()["relative_velocity_km_s"] >= 0
    
    # 7. Verify Dashboard Summary KPIs & Risk Distributions
    res_summary_alpha = client.get(f"/api/dashboard/summary?dataset={dataset_alpha}")
    assert res_summary_alpha.status_code == 200
    summary_alpha = res_summary_alpha.json()
    assert summary_alpha["total_tracked_objects"] == 5
    assert summary_alpha["total_conjunction_events"] == 1
    assert "risk_distribution" in summary_alpha
    
    res_summary_beta = client.get(f"/api/dashboard/summary?dataset={dataset_beta}")
    assert res_summary_beta.status_code == 200
    summary_beta = res_summary_beta.json()
    assert summary_beta["total_tracked_objects"] == 2
    assert summary_beta["total_conjunction_events"] >= 0
    
    # 8. Verify Re-entry Watch scoped to Dataset
    res_reentry = client.get(f"/api/reentry/watch?dataset={dataset_alpha}")
    assert res_reentry.status_code == 200
    assert "predictions" in res_reentry.json()

    # 9. Verify Deleting Dataset
    res_delete_beta = client.delete(f"/api/datasets/{dataset_beta}")
    assert res_delete_beta.status_code == 200
    assert res_delete_beta.json()["status"] == "deleted"
    assert res_delete_beta.json()["dataset"] == dataset_beta

    # Verify Beta is gone from dataset list
    res_datasets_after = client.get("/api/datasets/")
    assert dataset_beta not in res_datasets_after.json()["datasets"]
    assert dataset_alpha in res_datasets_after.json()["datasets"]

    # 10. Verify Cannot Delete Default Dataset
    res_delete_default = client.delete("/api/datasets/default")
    assert res_delete_default.status_code == 400
    assert "Cannot delete" in res_delete_default.json()["detail"]
