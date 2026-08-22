# AI-1: Propagation Module — Owner: Anas

## Responsibility
- SGP4/SDP4 orbit propagation using the `sgp4` library
- Propagate 500–1000 LEO objects across discretized future timesteps
- Generate state vectors (position, velocity) in ECI/J2000 frame
- Compute covariance matrices (3×3 position or 6×6 full state)
- Output propagated states in the shared interface format

## Key Files
- `sgp4_engine.py` — Batch SGP4 propagation across timesteps
- `covariance.py` — Covariance matrix generation/estimation
- `batch_propagator.py` — Orchestrator for multi-object propagation
- `models.py` — PropagatedState data models

## Output Contract → AI-2 (Rushaan)
```python
PropagatedState:
  object_id: str
  epoch: datetime
  position_eci: [x, y, z]       # km, J2000
  velocity_eci: [vx, vy, vz]    # km/s
  covariance_6x6: 6×6 matrix    # km, km/s units
  hard_body_radius: float        # km
  cross_section_area: float      # m²
  object_type: str               # PAYLOAD | DEBRIS | ROCKET_BODY
```
