"""
Unit tests for the end-to-end conjunction pipeline.
"""
from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from src.shared.interfaces.contracts import PropagatedState, PropagatedEpoch, ObjectType, PcMethod
from src.conjunction.pipeline import ConjunctionPipeline

def _create_state(
    obj_id: str,
    epoch: datetime,
    pos: list[float],
    vel: list[float],
    cov: list[list[float]]
) -> PropagatedState:
    return PropagatedState(
        object_id=obj_id,
        epoch=epoch,
        position_eci_km=pos,
        velocity_eci_km_s=vel,
        covariance_6x6_km_and_kms=cov,
        hard_body_radius_km=0.015,
        cross_section_area_m2=1.0,
        object_type=ObjectType.PAYLOAD
    )

def _create_cov():
    cov = np.eye(6)
    # Give it some realistic position variance (1 km^2) and small velocity variance
    cov[:3, :3] *= 1.0
    cov[3:, 3:] *= 1e-6
    return cov.tolist()

def _create_head_on_scenario() -> list[PropagatedEpoch]:
    base_time = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    epochs = []
    
    # 3 timesteps: t=-1, t=0, t=1
    # A moves from -10 to +10 along X (vel = 10 km/s)
    # B moves from +10 to -10 along X (vel = -10 km/s)
    # TCA is exactly at t=0
    
    for dt_s in [-1.0, 0.0, 1.0]:
        epoch_time = base_time + timedelta(seconds=dt_s)
        
        pos_A = [10.0 * dt_s, 0.0, 0.0]
        pos_B = [-10.0 * dt_s, 0.0, 0.0]
        
        state_A = _create_state("A", epoch_time, pos_A, [10.0, 0.0, 0.0], _create_cov())
        state_B = _create_state("B", epoch_time, pos_B, [-10.0, 0.0, 0.0], _create_cov())
        
        epochs.append(PropagatedEpoch(
            epoch=epoch_time,
            states=[state_A, state_B]
        ))
        
    return epochs

def test_pipeline_head_on():
    pipeline = ConjunctionPipeline()
    epochs = _create_head_on_scenario()
    
    events = pipeline.run(epochs)
    
    assert len(events) == 1
    event = events[0]
    
    assert set([event.primary_id, event.secondary_id]) == {"A", "B"}
    assert event.miss_distance_km == pytest.approx(0.0, abs=1e-5)
    assert event.tca == epochs[1].epoch
    assert event.relative_velocity_km_s == pytest.approx(20.0, abs=1e-5)
    
    # Pc should be computed (using Foster 2D since it's a valid head-on)
    assert event.pc > 0.0
    assert event.pc_method == PcMethod.FOSTER_2D
    
    # Validity flags
    assert event.validity_flags.covariance_valid
    assert event.validity_flags.relative_velocity_sufficient
