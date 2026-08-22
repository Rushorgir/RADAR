# AI-2: Conjunction Module — Owner: Rushaan

## Responsibility
- Two-stage conjunction screening (coarse altitude filter + fine k-d tree)
- Probability of Collision (Pc) computation (Foster's 2D + Monte Carlo fallback)
- CDM-compatible conjunction event output

## Sub-modules

### `models/` — Data Models & Interface Contracts
- Pydantic models for PropagatedState (input from AI-1)
- ConjunctionEvent / CDM schema (output to AI-3 & Backend)
- Encounter frame covariance structures

### `screening/` — Two-Stage Conjunction Screening Engine
- **Stage 1 (Coarse)**: Altitude band bucketing / apogee-perigee filters
- **Stage 2 (Fine)**: scipy.spatial.cKDTree 3D proximity search
- TCA refinement via polynomial/spline interpolation

### `probability/` — Pc Calculation Engine
- **Foster's 2D Method**: Encounter-plane projection, 2D Gaussian integration
- **Monte Carlo Fallback**: Vectorized sampling when Foster's assumptions break

## Input Contract ← AI-1 (Anas)
Propagated state vectors + covariance matrices in ECI/J2000

## Output Contract → AI-3 (Udarsh) & Backend (Balaganesh)
Structured conjunction events with TCA, miss distance, Pc, method, validity flags
