# 🛰️ RADAR: Risk Assessment & Debris Avoidance Routing

> **VITISH 2026 / SIH Internal Hackathon — Problem Statement #17**
> Space Technology – Space Debris Detection & Collision Avoidance

## Overview

RADAR is a modular Space Situational Awareness (SSA) system that:
1. Ingests TLE data and propagates orbits via SGP4
2. Screens for conjunction events using a two-stage coarse+fine filter
3. Computes Probability of Collision (Pc) via Foster's 2D method
4. Ranks collision risks with LightGBM + SHAP explainability
5. Generates minimum-Δv maneuver advisories
6. Displays everything on an interactive 3D Cesium.js globe

---

## Project Status

| Stage | Status | Notes |
|---|---|---|
| TLE ingestion (Celestrak) | ✅ Working | Live data, cached, LEO-filtered |
| SGP4 propagation | ✅ Working | 800 objects × 72h × 60s step in ~2.5s |
| Coordinate transforms | ✅ Working | TEME ↔ ECI ↔ ECEF ↔ RIC, astropy-backed |
| Conjunction screening (coarse + fine filter) | ✅ Working | k-d tree fine filter, TCA refinement |
| Probability of Collision (Foster 2D + Monte Carlo) | ✅ Working | Auto-selects method per encounter |
| **Full AI-1 → AI-2 pipeline, end-to-end** | ✅ **Verified** | Live data, 800 objects/72h: **~5.7s total** |
| ML risk ranking (LightGBM + SHAP) | ✅ Working | Trained on ESA Kelvins data, SHAP explainability |
| Maneuver advisory | ✅ Working | Closed-form Δv via Hill's equations |
| Backend API (FastAPI) | ✅ Working | REST + WebSocket, SQLite/PostgreSQL |
| Frontend / Cesium dashboard | ✅ Working | 3D globe, real SGP4 positions, risk panels |
| Re-entry watch | ✅ Working | Orbital decay risk tiers, live from TLEs |
| Launch corridor safety | ✅ Working | Ascent corridor vs. tracked catalog |

Automated tests are organized in `tests/` — run with `python -m pytest tests/ -v`.

---

## Team & Module Ownership

| Role | Person | Module | Directory |
|------|--------|--------|-----------|
| **AI-1** Orbital Mechanics Lead | Anas | TLE ingestion, SGP4 propagation, coordinate transforms | `src/ingestion/`, `src/propagation/`, `src/shared/frames/` |
| **AI-2** Conjunction & Math Lead | Rushaan | Conjunction screening, Pc calculation | `src/conjunction/` |
| **AI-3** ML & Decision Support | Udarsh | Feature engineering, LightGBM, SHAP, TabPFN, maneuver advisory | `src/ml/`, `src/maneuver/` |
| **Frontend** Web Developer | Balaganesh | React + Cesium.js dashboard | `src/frontend/` |
| **Backend & QA** | Mahalakshmi | FastAPI backend, DB, Testing, documentation | `src/backend/`, `docs/`, `tests/` |

---

## 🚨 Team Workflow & Workspace Rules

To maintain modularity and avoid git merge conflicts while working in parallel:

1. **Work in your designated directory**: Each contributor MUST write their module code exclusively inside their assigned directory under `src/` as mapped in the table above. See [TEAM_DIRECTORY_GUIDE.md](TEAM_DIRECTORY_GUIDE.md) for full folder & component breakdowns.
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
│   │   ├── models/         #   state.py, encounter.py, conjunction_event.py
│   │   ├── screening/      #   coarse_filter.py, fine_filter.py, tca_refiner.py, engine.py
│   │   ├── probability/    #   foster_2d.py, monte_carlo.py, encounter_frame.py, engine.py
│   │   └── pipeline.py     #   End-to-end: CatalogPropagationArrays -> ConjunctionEvents
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
├── resources/              # Problem statement PDFs, team plan
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
├── AI1_IMPLEMENTATION_NOTES.md   # AI-1 module deep-dive: what was built, how it was verified, perf notes
├── TEST_SUITE_MOCK_BUG_FIX.md    # A cross-team test-infrastructure bug: found, diagnosed, fixed
└── docker-compose.yml      # Deployment orchestration
```

---

## Interface Contracts

> **Critical**: All team members must adhere to these data schemas. Changes require team-wide notification.

### AI-1 → AI-2 (Propagation → Conjunction)
> Field names below match `PropagatedState` in `src/shared/interfaces/contracts.py` exactly — that file is the source of truth; this is a human-readable mirror of it.
```json
{
  "object_id": "string (NORAD catalog ID)",
  "epoch": "ISO-8601 datetime",
  "position_eci_km": [x, y, z],        // km, J2000 ECI frame
  "velocity_eci_km_s": [vx, vy, vz],   // km/s
  "covariance_6x6": [[...]],           // 6×6 matrix (km, km/s units), or null if unavailable
  "hard_body_radius_km": 0.005,        // km
  "cross_section_area_m2": 1.0,        // m²
  "object_type": "PAYLOAD | DEBRIS | ROCKET_BODY | UNKNOWN",
  "object_name": "string | null"
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
  "combined_covariance_enc_2x2": [[...]],  // 2×2 encounter-plane covariance
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
    "delta_v_m_s": 0.15,
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

**Try the AI-1 pipeline standalone** (TLE ingestion → SGP4 propagation → ECI state vectors, no backend/frontend needed — pulls live data from Celestrak):

```bash
python scripts/run_propagation_pipeline.py --count 800 --hours 72 --step 60
```

See [AI1_IMPLEMENTATION_NOTES.md](AI1_IMPLEMENTATION_NOTES.md) for what this covers, how it was verified, and a real performance bug (5+ min → ~3-4s at full 800-object scale) that was found and fixed along the way.

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

- [ESA Kelvins Collision Avoidance Challenge](https://kelvins.esa.int/collision-avoidance-challenge/) (2019)
- Foster, J.L. & Estes, H.S., "A Parametric Analysis of Orbital Debris Collision Probability and Comparison of Deterministic and Probabilistic Methods," NASA Johnson Space Center, 1992 — [search NASA NTRS](https://ntrs.nasa.gov/search?q=parametric%20analysis%20orbital%20debris%20collision%20probability)
- [Celestrak](https://celestrak.org/) — live TLE data ([GP data formats](https://celestrak.org/NORAD/documentation/gp-data-formats.php), [TLE format reference](https://celestrak.org/NORAD/documentation/tle-fmt.php))
- [NASA Orbital Debris Program Office](https://orbitaldebris.jsc.nasa.gov/) & [ESA Space Debris Office](https://www.esa.int/Space_Safety/Space_Debris) reports
