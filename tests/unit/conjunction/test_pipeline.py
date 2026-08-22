"""
Unit tests for the end-to-end conjunction pipeline.
"""
from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from src.shared.interfaces.contracts import ObjectType, PcMethod
from src.conjunction.pipeline import ConjunctionPipeline
from src.shared.constants.physical import EARTH
from src.propagation.batch_arrays import CatalogPropagationArrays


def _create_arrays(
    object_ids: list[str],
    epochs: list[datetime],
    positions: list[list[list[float]]],
    velocities: list[list[list[float]]],
) -> CatalogPropagationArrays:
    n_objects = len(object_ids)
    n_steps = len(epochs)
    
    pos_arr = np.array(positions)
    vel_arr = np.array(velocities)
    
    # Simple Identity * 0.1 for cov
    covariances = np.zeros((n_objects, n_steps, 6, 6))
    for obj_idx in range(n_objects):
        for step_idx in range(n_steps):
            np.fill_diagonal(covariances[obj_idx, step_idx], 0.1)
            
    ok_mask = np.ones((n_objects, n_steps), dtype=bool)
    
    tle_epochs = [epochs[0]] * n_objects if epochs else []
    
    return CatalogPropagationArrays(
        object_ids=object_ids,
        object_names=[f"OBJ {o}" for o in object_ids],
        object_types=[ObjectType.PAYLOAD] * n_objects,
        tle_epochs=tle_epochs,
        epochs=epochs,
        positions_eci_km=pos_arr,
        velocities_eci_km_s=vel_arr,
        covariances_eci=covariances,
        ok_mask=ok_mask,
        error_codes=np.zeros((n_objects, n_steps), dtype=int)
    )


def test_pipeline_empty_epochs():
    pipeline = ConjunctionPipeline()
    arrays = _create_arrays([], [], [], [])
    events = pipeline.run(arrays)
    assert events == []


def test_pipeline_head_on():
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = [base_time + timedelta(seconds=dt_s) for dt_s in [-1.0, 0.0, 1.0]]
    
    r_alt = EARTH.RADIUS_KM + 500.0
    
    pos_A = [[r_alt + 10.0 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    pos_B = [[r_alt - 10.0 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    
    vel_A = [[10.0, 0.0, 0.0]] * 3
    vel_B = [[-10.0, 0.0, 0.0]] * 3
    
    arrays = _create_arrays(
        object_ids=["A", "B"],
        epochs=epochs,
        positions=[pos_A, pos_B],
        velocities=[vel_A, vel_B]
    )
        
    events = pipeline.run(arrays)
    assert len(events) == 1
    event = events[0]
    
    assert set([event.primary_id, event.secondary_id]) == {"A", "B"}
    assert event.miss_distance_km == pytest.approx(0.0, abs=1e-4)
    assert event.relative_velocity_km_s == pytest.approx(20.0, abs=1e-4)
    assert event.pc > 0.0
    assert event.pc_method == PcMethod.FOSTER_2D
    assert event.validity_flags.covariance_valid
    assert event.validity_flags.relative_velocity_sufficient


def test_pipeline_log_only_tier():
    """Conjunction with miss distance between 5 km and 10 km should yield Pc = 0 (logged only)."""
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = [base_time + timedelta(seconds=dt_s) for dt_s in [-1.0, 0.0, 1.0]]
    
    r_alt = EARTH.RADIUS_KM + 500.0
    
    pos_A = [[r_alt + 10.0 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    pos_B = [[r_alt - 10.0 * dt, 7.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    
    vel_A = [[10.0, 0.0, 0.0]] * 3
    vel_B = [[-10.0, 0.0, 0.0]] * 3
    
    arrays = _create_arrays(
        object_ids=["A", "B"],
        epochs=epochs,
        positions=[pos_A, pos_B],
        velocities=[vel_A, vel_B]
    )
        
    events = pipeline.run(arrays)
    assert len(events) == 1
    event = events[0]
    assert 5.0 < event.miss_distance_km <= 10.0
    assert event.pc == 0.0
    assert event.pc_method == PcMethod.FOSTER_2D


def test_pipeline_clear_miss():
    """Objects passing > 10 km apart should not produce any conjunction event."""
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = [base_time + timedelta(seconds=dt_s) for dt_s in [-1.0, 0.0, 1.0]]
    
    r_alt = EARTH.RADIUS_KM + 500.0
    
    pos_A = [[r_alt + 10.0 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    pos_B = [[r_alt - 10.0 * dt, 25.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    
    vel_A = [[10.0, 0.0, 0.0]] * 3
    vel_B = [[-10.0, 0.0, 0.0]] * 3
    
    arrays = _create_arrays(
        object_ids=["A", "B"],
        epochs=epochs,
        positions=[pos_A, pos_B],
        velocities=[vel_A, vel_B]
    )
        
    events = pipeline.run(arrays)
    assert len(events) == 0


def test_pipeline_low_relative_velocity_fallback():
    """Very low relative velocity (<100 m/s) should trigger Monte Carlo method in pipeline."""
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = [base_time + timedelta(seconds=dt_s) for dt_s in [-1.0, 0.0, 1.0]]
    
    r_alt = EARTH.RADIUS_KM + 500.0
    
    pos_A = [[r_alt + 0.02 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    pos_B = [[r_alt - 0.02 * dt, 0.01, 0.0] for dt in [-1.0, 0.0, 1.0]]
    
    vel_A = [[0.02, 0.0, 0.0]] * 3
    vel_B = [[-0.02, 0.0, 0.0]] * 3
    
    arrays = _create_arrays(
        object_ids=["A", "B"],
        epochs=epochs,
        positions=[pos_A, pos_B],
        velocities=[vel_A, vel_B]
    )
        
    events = pipeline.run(arrays)
    assert len(events) == 1
    event = events[0]
    assert event.relative_velocity_km_s < 0.1
    assert event.pc_method == PcMethod.MONTE_CARLO
    assert event.pc_confidence_lower is not None
    assert event.pc_confidence_upper is not None


def test_pipeline_multiple_objects_selective_conjunction():
    """Three objects: A & B conjunct at 500 km, while C is at 900 km (coarse filter excludes C)."""
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = [base_time + timedelta(seconds=dt_s) for dt_s in [-1.0, 0.0, 1.0]]
    
    r_leo1 = EARTH.RADIUS_KM + 500.0
    r_leo2 = EARTH.RADIUS_KM + 900.0
    
    pos_A = [[r_leo1 + 10.0 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    pos_B = [[r_leo1 - 10.0 * dt, 0.0, 0.0] for dt in [-1.0, 0.0, 1.0]]
    pos_C = [[r_leo2, 10.0 * dt, 0.0] for dt in [-1.0, 0.0, 1.0]]
    
    vel_A = [[10.0, 0.0, 0.0]] * 3
    vel_B = [[-10.0, 0.0, 0.0]] * 3
    vel_C = [[0.0, 10.0, 0.0]] * 3
    
    arrays = _create_arrays(
        object_ids=["A", "B", "C"],
        epochs=epochs,
        positions=[pos_A, pos_B, pos_C],
        velocities=[vel_A, vel_B, vel_C]
    )
        
    events = pipeline.run(arrays)
    assert len(events) == 1
    assert set([events[0].primary_id, events[0].secondary_id]) == {"A", "B"}
