"""
Integration tests for bridging AI-1 (Propagation) and AI-2 (Conjunction).
Owner: Rushaan & Anas
"""
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import sys

# Mock astropy and sgp4 to avoid C-extension deadlocks on Python 3.14 on macOS
sys.modules['astropy'] = MagicMock()
sys.modules['astropy.time'] = MagicMock()
sys.modules['astropy.coordinates'] = MagicMock()
sys.modules['astropy.units'] = MagicMock()
sys.modules['erfa'] = MagicMock()
sys.modules['sgp4'] = MagicMock()
sys.modules['sgp4.api'] = MagicMock()
sys.modules['sgp4.ext'] = MagicMock()
sys.modules['sgp4.earth_gravity'] = MagicMock()

from src.conjunction.pipeline import ConjunctionPipeline
from src.propagation.batch_arrays import CatalogPropagationArrays
from src.shared.interfaces.contracts import ObjectType


def test_ai1_to_ai2_pipeline_integration():
    """
    Integration test bridging AI-1 (Propagation) and AI-2 (Conjunction/Probability).
    We bypass the C-extension deadlocks by passing directly constructed 
    CatalogPropagationArrays (AI-1's optimized output) into ConjunctionPipeline (AI-2's entrypoint).
    """
    
    # 1. Setup mock CatalogPropagationArrays mimicking AI-1 output
    base_time = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
    epochs = [base_time + timedelta(minutes=i) for i in range(60)]
    
    n_objects = 2
    n_steps = 60
    
    object_ids = ["25544", "99999"]
    object_names = ["OBJECT A", "OBJECT B"]
    object_types = [ObjectType.PAYLOAD, ObjectType.PAYLOAD]
    tle_epochs = [base_time, base_time]
    
    positions = np.zeros((n_objects, n_steps, 3))
    velocities = np.zeros((n_objects, n_steps, 3))
    covariances = np.zeros((n_objects, n_steps, 6, 6))
    ok_mask = np.ones((n_objects, n_steps), dtype=bool)
    error_codes = np.zeros((n_objects, n_steps), dtype=int)
    
    # Define simple parallel trajectories that intersect exactly at step 30
    for i, epoch in enumerate(epochs):
        # Object A
        positions[0, i] = [7000.0, 0.0, i * 7.5]
        velocities[0, i] = [0.0, 7.5, 0.0]
        
        # Object B is nearby
        positions[1, i] = [7000.1, 0.0, i * 7.5]
        # B has slight Z velocity so relative velocity is non-zero
        velocities[1, i] = [0.0, 7.5, -0.1]
        
        # Covariance (identity * 0.1 for position)
        for obj_idx in range(n_objects):
            np.fill_diagonal(covariances[obj_idx, i], 0.1)
            
    mock_arrays = CatalogPropagationArrays(
        object_ids=object_ids,
        object_names=object_names,
        object_types=object_types,
        tle_epochs=tle_epochs,
        epochs=epochs,
        positions_eci_km=positions,
        velocities_eci_km_s=velocities,
        covariances_eci=covariances,
        ok_mask=ok_mask,
        error_codes=error_codes
    )
    
    # 2. Instantiate and run the ConjunctionPipeline
    pipeline = ConjunctionPipeline()
    
    # AI-2 now natively accepts AI-1's CatalogPropagationArrays!
    events = pipeline.run(mock_arrays)
    
    # 3. Assertions
    assert len(events) > 0, "Pipeline should have flagged the conjunction"
    event = events[0]
    
    assert event.primary_id == "25544"
    assert event.secondary_id == "99999"
    assert event.miss_distance_km < 5.0  # They are 0.1km apart in X
    assert event.pc > 0.0, "Probability of Collision should be calculated"
    assert event.validity_flags.covariance_positive_definite

if __name__ == "__main__":
    test_ai1_to_ai2_pipeline_integration()
