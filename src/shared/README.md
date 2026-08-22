# Shared Utilities — Owner: All

## Responsibility
- Common constants, coordinate frame transforms, and interface contracts
- Used by ALL modules to ensure consistency

## Sub-modules

### `frames/` — Coordinate Frame Utilities
- ECI ↔ ECEF conversions
- TEME → J2000 ECI transforms
- Rotation matrix helpers (using astropy under the hood)

### `constants/` — Physical Constants & Thresholds
- Earth radius, gravitational parameter (μ)
- Screening thresholds (altitude band width, encounter sphere radius)
- Pc method switching thresholds

### `interfaces/` — Shared Interface Contracts
- JSON schema definitions for cross-module data exchange
- Version-controlled contract files
- Any change here must be announced to ALL team members immediately
