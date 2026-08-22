"""
Unit tests for the end-to-end conjunction pipeline.
"""
from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from src.shared.interfaces.contracts import PropagatedState, PropagatedEpoch, ObjectType, PcMethod
from src.conjunction.pipeline import ConjunctionPipeline
from src.shared.constants.physical import EARTH


def _create_state(
    obj_id: str,
    epoch: datetime,
    pos: list[float],
    vel: list[float],
    cov: list[list[float]] = None,
    hard_body_radius_km: float = 0.015,
    obj_type: ObjectType = ObjectType.PAYLOAD,
) -> PropagatedState:
    return PropagatedState(
        object_id=obj_id,
        epoch=epoch,
        position_eci_km=pos,
        velocity_eci_km_s=vel,
        covariance_6x6_km_and_kms=cov,
        hard_body_radius_km=hard_body_radius_km,
        cross_section_area_m2=1.0,
        object_type=obj_type,
    )


def _create_cov():
    cov = np.eye(6)
    cov[:3, :3] *= 1.0
    cov[3:, 3:] *= 1e-6
    return cov.tolist()


def test_pipeline_empty_epochs():
    pipeline = ConjunctionPipeline()
    events = pipeline.run([])
    assert events == []


def test_pipeline_head_on():
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = []
    
    # 3 timesteps: t=-1, t=0, t=1
    # Altitude ~500 km
    r_alt = EARTH.RADIUS_KM + 500.0
    for dt_s in [-1.0, 0.0, 1.0]:
        epoch_time = base_time + timedelta(seconds=dt_s)
        pos_A = [r_alt + 10.0 * dt_s, 0.0, 0.0]
        pos_B = [r_alt - 10.0 * dt_s, 0.0, 0.0]
        
        state_A = _create_state("A", epoch_time, pos_A, [10.0, 0.0, 0.0], _create_cov())
        state_B = _create_state("B", epoch_time, pos_B, [-10.0, 0.0, 0.0], _create_cov())
        
        epochs.append(PropagatedEpoch(epoch=epoch_time, states=[state_A, state_B]))
        
    events = pipeline.run(epochs)
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
    epochs = []
    
    r_alt = EARTH.RADIUS_KM + 500.0
    # Miss distance of 7 km at closest approach (t=0)
    for dt_s in [-1.0, 0.0, 1.0]:
        epoch_time = base_time + timedelta(seconds=dt_s)
        pos_A = [r_alt + 10.0 * dt_s, 0.0, 0.0]
        pos_B = [r_alt - 10.0 * dt_s, 7.0, 0.0]
        
        state_A = _create_state("A", epoch_time, pos_A, [10.0, 0.0, 0.0], _create_cov())
        state_B = _create_state("B", epoch_time, pos_B, [-10.0, 0.0, 0.0], _create_cov())
        
        epochs.append(PropagatedEpoch(epoch=epoch_time, states=[state_A, state_B]))
        
    events = pipeline.run(epochs)
    assert len(events) == 1
    event = events[0]
    assert 5.0 < event.miss_distance_km <= 10.0
    assert event.pc == 0.0
    assert event.pc_method == PcMethod.FOSTER_2D


def test_pipeline_clear_miss():
    """Objects passing > 10 km apart should not produce any conjunction event."""
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = []
    
    r_alt = EARTH.RADIUS_KM + 500.0
    # Miss distance is 25 km at t=0
    for dt_s in [-1.0, 0.0, 1.0]:
        epoch_time = base_time + timedelta(seconds=dt_s)
        pos_A = [r_alt + 10.0 * dt_s, 0.0, 0.0]
        pos_B = [r_alt - 10.0 * dt_s, 25.0, 0.0]
        
        state_A = _create_state("A", epoch_time, pos_A, [10.0, 0.0, 0.0], _create_cov())
        state_B = _create_state("B", epoch_time, pos_B, [-10.0, 0.0, 0.0], _create_cov())
        
        epochs.append(PropagatedEpoch(epoch=epoch_time, states=[state_A, state_B]))
        
    events = pipeline.run(epochs)
    assert len(events) == 0


def test_pipeline_low_relative_velocity_fallback():
    """Very low relative velocity (<100 m/s) should trigger Monte Carlo method in pipeline."""
    pipeline = ConjunctionPipeline()
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = []
    
    r_alt = EARTH.RADIUS_KM + 500.0
    # Relative speed = 0.04 km/s = 40 m/s < 100 m/s threshold
    for dt_s in [-1.0, 0.0, 1.0]:
        epoch_time = base_time + timedelta(seconds=dt_s)
        pos_A = [r_alt + 0.02 * dt_s, 0.0, 0.0]
        pos_B = [r_alt - 0.02 * dt_s, 0.01, 0.0]
        
        state_A = _create_state("A", epoch_time, pos_A, [0.02, 0.0, 0.0], _create_cov())
        state_B = _create_state("B", epoch_time, pos_B, [-0.02, 0.0, 0.0], _create_cov())
        
        epochs.append(PropagatedEpoch(epoch=epoch_time, states=[state_A, state_B]))
        
    events = pipeline.run(epochs)
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
    epochs = []
    
    r_leo1 = EARTH.RADIUS_KM + 500.0
    r_leo2 = EARTH.RADIUS_KM + 900.0
    
    for dt_s in [-1.0, 0.0, 1.0]:
        epoch_time = base_time + timedelta(seconds=dt_s)
        pos_A = [r_leo1 + 10.0 * dt_s, 0.0, 0.0]
        pos_B = [r_leo1 - 10.0 * dt_s, 0.0, 0.0]
        pos_C = [r_leo2, 10.0 * dt_s, 0.0]
        
        state_A = _create_state("A", epoch_time, pos_A, [10.0, 0.0, 0.0], _create_cov())
        state_B = _create_state("B", epoch_time, pos_B, [-10.0, 0.0, 0.0], _create_cov())
        state_C = _create_state("C", epoch_time, pos_C, [0.0, 10.0, 0.0], _create_cov())
        
        epochs.append(PropagatedEpoch(epoch=epoch_time, states=[state_A, state_B, state_C]))
        
    events = pipeline.run(epochs)
    assert len(events) == 1
    assert set([events[0].primary_id, events[0].secondary_id]) == {"A", "B"}
