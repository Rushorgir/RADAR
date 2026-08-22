"""
Integration tests for bridging AI-1 (Propagation) and AI-2 (Conjunction).
Owner: Rushaan & Anas
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
import sys

sys.modules['astropy'] = MagicMock()
sys.modules['astropy.time'] = MagicMock()
sys.modules['astropy.coordinates'] = MagicMock()
sys.modules['astropy.units'] = MagicMock()
sys.modules['erfa'] = MagicMock()
sys.modules['sgp4'] = MagicMock()
sys.modules['sgp4.api'] = MagicMock()
sys.modules['sgp4.ext'] = MagicMock()
sys.modules['sgp4.earth_gravity'] = MagicMock()

# We mock the propagation engine completely to bypass C-extension deadlocks on Python 3.14
# The focus of this integration test is on the *bridging* between AI-1 output and AI-2 input,
# and verifying the downstream ConjunctionPipeline math.

from src.ingestion.tle_parser import parse_tle_lines
from src.propagation.models import BatchPropagationResult, TrajectoryResult
from src.shared.interfaces.contracts import PropagatedEpoch, PropagatedState
from src.conjunction.pipeline import ConjunctionPipeline


# TLEs for testing parsing (though propagation itself is mocked)
ISS_NAME_1 = "OBJECT A"
ISS_LINE1_1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2_1 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

ISS_NAME_2 = "OBJECT B"
ISS_LINE1_2 = "1 99999U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2_2 = "2 99999  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"


@patch('src.propagation.batch_propagator.propagate_catalog')
def test_ai1_to_ai2_pipeline_integration(mock_propagate):
    """
    End-to-end integration test:
    1. AI-1 Parses TLEs
    2. AI-1 Propagates Catalog (Mocked to generate intersecting orbits)
    3. Bridge logic regroups by Epoch
    4. AI-2 Screens and computes Pc
    """
    
    # 1. Parsing
    tle1 = parse_tle_lines(ISS_LINE1_1, ISS_LINE2_1, name=ISS_NAME_1, validate_checksum=False)
    tle2 = parse_tle_lines(ISS_LINE1_2, ISS_LINE2_2, name=ISS_NAME_2, validate_checksum=False)
    
    start = tle1.epoch
    end = start + timedelta(hours=1)
    step_s = 60.0
    epochs = [start + timedelta(seconds=i * step_s) for i in range(60)]
    
    # Setup mock Trajectory Results (simulate two objects that are ~100m apart)
    traj1 = TrajectoryResult(object_id="25544", object_name="OBJECT A", object_type="PAYLOAD")
    traj2 = TrajectoryResult(object_id="99999", object_name="OBJECT B", object_type="PAYLOAD")
    
    cov = np.eye(6).tolist()
    
    for epoch in epochs:
        # Object A is at [x, 0, 0] moving along Y
        r1 = [7000.0, 0.0, 0.0]
        v1 = [0.0, 7.5, 0.0]
        
        # Object B is 100 meters away in X and has slight Z velocity
        r2 = [7000.1, 0.0, 0.0]
        v2 = [0.0, 7.5, -0.1]
        
        traj1.states.append(PropagatedState(
            object_id="25544", epoch=epoch, position_eci_km=r1, velocity_eci_km_s=v1, 
            covariance_6x6=cov, hard_body_radius_km=0.005, cross_section_area_m2=1.0, 
            object_type="PAYLOAD", object_name="OBJECT A"
        ))
        traj2.states.append(PropagatedState(
            object_id="99999", epoch=epoch, position_eci_km=r2, velocity_eci_km_s=v2, 
            covariance_6x6=cov, hard_body_radius_km=0.005, cross_section_area_m2=1.0, 
            object_type="PAYLOAD", object_name="OBJECT B"
        ))
        
    mock_result = BatchPropagationResult(
        epochs=epochs,
        trajectories={"25544": traj1, "99999": traj2},
        errors={}
    )
    mock_propagate.return_value = mock_result
    
    # 2. Trigger Propagation
    batch_result = mock_propagate([tle1, tle2], start=start, end=end, step_s=step_s, attach_covariance=True)
    
    assert len(batch_result.epochs) == 60
    
    # 3. Bridge logic (Tested here: converting AI-1's object-oriented dict into AI-2's time-oriented list)
    pipeline_input = []
    for i, epoch_time in enumerate(batch_result.epochs):
        epoch_states = batch_result.states_at(i)
        pipeline_input.append(PropagatedEpoch(epoch=epoch_time, states=epoch_states))
        
    assert len(pipeline_input) == 60
    assert len(pipeline_input[0].states) == 2
    
    # 4. Conjunction Screening & Probability (AI-2 Pipeline)
    pipeline = ConjunctionPipeline()
    events = pipeline.run(pipeline_input)
    
    # Assertions
    assert len(events) >= 1, "Pipeline failed to detect conjunction"
    
    event = events[0]
    assert set([event.primary_id, event.secondary_id]) == {"25544", "99999"}
    assert event.miss_distance_km == pytest.approx(0.1, abs=1e-3) # 100m
    
if __name__ == "__main__":
    test_ai1_to_ai2_pipeline_integration(MagicMock())
