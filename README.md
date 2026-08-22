# 🛰️ RADAR — OrbitGuard: AI-Assisted Space Debris Collision Risk Detection & Avoidance

> **VITISH 2026 / SIH Internal Hackathon — Problem Statement #17**
> Space Technology – Space Debris Detection & Collision Avoidance

## Overview

OrbitGuard is a modular Space Situational Awareness (SSA) system that:
1. Ingests TLE data and propagates orbits via SGP4
2. Screens for conjunction events using a two-stage coarse+fine filter
3. Computes Probability of Collision (Pc) via Foster's 2D method
4. Ranks collision risks with LightGBM + SHAP explainability
5. Generates minimum-Δv maneuver advisories
6. Displays everything on an interactive 3D Cesium.js globe

---

## Team & Module Ownership

| Role | Person | Module | Directory |
|------|--------|--------|-----------|
| **AI-1** Orbital Mechanics Lead | Anas | TLE ingestion, SGP4 propagation, coordinate transforms | `src/ingestion/`, `src/propagation/`, `src/shared/frames/` |
| **AI-2** Conjunction & Math Lead | Rushaan | Conjunction screening, Pc calculation | `src/conjunction/` |
| **AI-3** ML & Decision Support | Udarsh | Feature engineering, LightGBM, SHAP, TabPFN, maneuver advisory | `src/ml/`, `src/maneuver/` |
| **Web** Full-Stack Developer | Balaganesh | FastAPI backend, React + Cesium.js frontend, DB | `src/backend/`, `src/frontend/` |
| **QA & Speaker** | Mahalakshmi | Testing, documentation, pitch, demo | `docs/`, `tests/` |

---

## 🚨 Team Workflow & Workspace Rules

To maintain modularity and avoid git merge conflicts while working in parallel:

1. **Work in your designated directory**: Each contributor MUST write their module code exclusively inside their assigned directory under `src/` as mapped in the table above.
2. **Do NOT modify other members' folders**: If you need functionality from another module, request an update via PR or use the agreed interface contracts in `src/shared/interfaces/contracts.py`.
3. **Shared Contracts**: `src/shared/` contains common constants and Pydantic interface contracts. Any proposed breaking changes to `src/shared/` MUST be announced and agreed upon by the team before committing.
4. **Unit Tests**: Place your unit tests in your dedicated subfolder under `tests/unit/<module_name>/`.

---

## Project Structure

```
RADAR/
├── src/
│   ├── ingestion/          # [AI-1: Anas] TLE fetch & parse from Celestrak
│   ├── propagation/        # [AI-1: Anas] SGP4 propagation engine
│   ├── conjunction/        # [AI-2: Rushaan] Conjunction screening + Pc
│   │   ├── models/         #   Pydantic data models (CDM schema, state vectors)
│   │   ├── screening/      #   Two-stage coarse + fine filter engine
│   │   └── probability/    #   Foster 2D Pc + Monte Carlo fallback
│   ├── ml/                 # [AI-3: Udarsh] ML risk ranking pipeline
│   │   ├── features/       #   Feature engineering from conjunction events
│   │   ├── ranking/        #   LightGBM + TabPFN model training/inference
│   │   └── explainability/ #   SHAP integration & explanations
│   ├── maneuver/           # [AI-3: Udarsh] Delta-v avoidance advisory
│   ├── backend/            # [Web: Balaganesh] FastAPI REST API
│   │   ├── api/            #   Route handlers / endpoints
│   │   ├── db/             #   PostgreSQL/SQLite models & migrations
│   │   └── schemas/        #   Pydantic request/response schemas
│   ├── frontend/           # [Web: Balaganesh] React + Cesium.js dashboard
│   │   ├── public/         #   Static assets
│   │   └── src/            #   React components, pages, utilities
│   └── shared/             # [All] Common utilities, constants, frame transforms
│       ├── frames/         #   ECI/ECEF/TEME coordinate frame helpers
│       ├── constants/      #   Physical constants, thresholds
│       └── interfaces/     #   Shared interface contracts (JSON schemas)
├── tests/
│   ├── unit/               # Per-module unit tests
│   ├── integration/        # Cross-module integration tests
│   ├── fixtures/           # Synthetic test data & known conjunctions
│   └── validation/         # Validation against ESA Kelvins CDM dataset
├── data/
│   ├── tle_cache/          # Cached TLE files from Celestrak
│   └── cdm_reference/      # ESA Kelvins 2019 CDM reference data
├── docs/                   # Architecture docs, pitch deck, demo script
├── scripts/                # Utility scripts (data download, pipeline runners)
├── config/                 # Configuration files (thresholds, API keys)
├── sources/                # Original problem statement PDFs
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
└── docker-compose.yml      # Deployment orchestration
```

---

## Interface Contracts

> **Critical**: All team members must adhere to these data schemas. Changes require team-wide notification.

### AI-1 → AI-2 (Propagation → Conjunction)
```json
{
  "object_id": "string (NORAD catalog ID)",
  "epoch": "ISO-8601 datetime",
  "position_eci": [x, y, z],          // km, J2000 ECI frame
  "velocity_eci": [vx, vy, vz],       // km/s
  "covariance_6x6": [[...]],          // 6×6 matrix (km, km/s units)
  "hard_body_radius": 0.005,          // km
  "cross_section_area": 1.0,          // m²
  "object_type": "PAYLOAD | DEBRIS | ROCKET_BODY"
}
```

### AI-2 → AI-3 / Backend (Conjunction → ML / API)
```json
{
  "event_id": "UUID",
  "primary_id": "string",
  "secondary_id": "string",
  "tca": "ISO-8601 datetime",
  "miss_distance_km": 0.123,
  "relative_velocity_km_s": 7.8,
  "combined_covariance_enc": [[...]],  // 2×2 encounter-plane covariance
  "pc": 1.23e-5,
  "pc_method": "FOSTER_2D | MONTE_CARLO",
  "validity_flags": {
    "covariance_valid": true,
    "relative_velocity_sufficient": true,
    "encounter_duration_short": true
  }
}
```

### AI-3 → Backend (ML → API)
```json
{
  "event_id": "UUID",
  "ml_risk_score": 0.87,
  "risk_category": "HIGH | MEDIUM | LOW",
  "shap_top_features": [
    {"feature": "miss_distance", "impact": -0.42},
    {"feature": "relative_velocity", "impact": 0.31},
    {"feature": "pc", "impact": 0.28}
  ],
  "maneuver_advisory": {
    "delta_v_ms": 0.15,
    "burn_direction": "ALONG_TRACK",
    "new_miss_distance_km": 2.5,
    "fuel_cost_estimate_kg": 0.02
  }
}
```

---

## Quick Start

```bash
# Clone and setup
git clone <repo-url> && cd RADAR
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run backend
cd src/backend && uvicorn api.main:app --reload

# Run frontend
cd src/frontend && npm install && npm run dev
```

---

## Key Libraries

| Library | Purpose | Owner |
|---------|---------|-------|
| `sgp4` | SGP4/SDP4 orbit propagation | AI-1 |
| `astropy` | Coordinate frame transforms, time | AI-1 / Shared |
| `scipy` | k-d tree, numerical integration | AI-2 |
| `numpy` | Vectorized computation | All |
| `pydantic` | Data validation & schemas | All |
| `lightgbm` | Gradient boosted tree ranking | AI-3 |
| `shap` | Model explainability | AI-3 |
| `fastapi` | REST API backend | Web |
| `cesiumjs` | 3D globe visualization | Web |
| `react` | Frontend UI framework | Web |

---

## References

- ESA Kelvins Collision Avoidance Challenge (2019)
- Foster, J.L., "A Parametric Analysis of Orbital Debris Collision Probability," NASA
- Celestrak (celestrak.org) — live TLE data
- NASA Orbital Debris Program Office & ESA Space Debris Office reports
