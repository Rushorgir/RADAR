# RADAR / OrbitGuard: Team Directory & Workspace Guide

This document outlines the exact contents of each folder in the repository and specifies which team member owns and is responsible for each section.

> **Workspace Isolation Rule**: To avoid git merge conflicts and ensure modularity, you MUST write code ONLY in your assigned directories. If you need functionality from another module, use the shared contracts or request an update from the module owner.

---

## 🛠️ The `src/` Directory (Core Source Code)

The `src/` folder is divided into decoupled functional modules. Each team member has absolute ownership over their designated folders.

---

### 1. `src/ingestion/` & `src/propagation/`
**Owner**: Anas (AI-1: Orbital Mechanics Lead)

* **`src/ingestion/`**:
  * `tle_fetcher.py`: Automates pulling fresh Two-Line Element sets (TLEs) from Celestrak APIs for LEO satellites, debris, and rocket bodies.
  * `tle_parser.py`: Parses raw TLE text strings into structured astronomical parameters (inclination, RAAN, eccentricity, mean motion).
  * `tle_cache.py`: Local caching engine with TTL validation to prevent repetitive API requests and rate limiting.
  * `models.py`: Internal dataclasses / Pydantic models for raw and parsed TLE records.
* **`src/propagation/`**:
  * `sgp4_engine.py`: Batch SGP4/SDP4 propagation runner generating position $\vec{r} = [x, y, z]$ and velocity $\vec{v} = [v_x, v_y, v_z]$ in the ECI (J2000) frame over 72-hour forecast horizons at 60s timesteps.
  * `covariance.py`: Covariance matrix estimation and propagation algorithms representing positional uncertainty ellipses.
  * `batch_propagator.py`: Multi-threaded / vectorized orchestrator handling propagation for 500–1000 tracked LEO objects concurrently.

---

### 2. `src/conjunction/`
**Owner**: Rushaan (AI-2: Conjunction & Probability Math Lead)

* **`src/conjunction/models/`**:
  * `state.py`: Propagated state models received from AI-1 (ECI coordinates, covariance).
  * `encounter.py`: Intermediate dataclasses for 3D encounter geometry, B-plane miss vectors, and relative velocity vectors.
  * `conjunction_event.py`: Standardized CDM-compatible event output schemas.
* **`src/conjunction/screening/`**:
  * `coarse_filter.py`: Stage 1 altitude-band sweep-line filter using perigee/apogee bounds to eliminate $O(n^2)$ non-intersecting orbit pairs.
  * `fine_filter.py`: Stage 2 3D spatial indexing using `scipy.spatial.cKDTree` to detect object pairs within a 10 km encounter sphere at each timestep.
  * `tca_refiner.py`: Cubic spline / polynomial interpolation to calculate exact Time of Closest Approach (TCA) and minimum miss distance between discrete timesteps.
  * `engine.py`: Orchestrator combining Stage 1, Stage 2, and TCA refinement.
* **`src/conjunction/probability/`**:
  * `encounter_frame.py`: Computes coordinate transformation matrices from ECI to the 2D B-plane (encounter plane perpendicular to relative velocity $\vec{v}_{\text{rel}}$).
  * `foster_2d.py`: Primary analytical $P_c$ calculation integrating 2D Gaussian probability density over circular hard-body cross-sections ($R_A + R_B$).
  * `monte_carlo.py`: High-performance vectorized NumPy Monte Carlo engine ($10^5 - 10^6$ particles) with Wilson score confidence intervals.
  * `engine.py`: Auto-triggers Foster 2D or switches to Monte Carlo fallback when relative velocity $v_{\text{rel}} < 100\text{ m/s}$ or covariance is degenerate.
* **`src/conjunction/pipeline.py`**: End-to-end pipeline connecting state ingestion to output conjunction events.

---

### 3. `src/ml/` & `src/maneuver/`
**Owner**: Udarsh (AI-3: ML & Decision Support)

* **`src/ml/features/`**:
  * `extractor.py`: Extracts predictive feature vectors from conjunction events (miss distance, relative velocity, object types, cross-sectional area, covariance size, orbital regime).
  * `preprocessor.py`: Normalization, missing-value handling, and categorical encoding pipelines.
* **`src/ml/ranking/`**:
  * `train.py`: Training scripts for LightGBM gradient-boosted decision trees using historical/synthetic CDM data.
  * `predictor.py`: Real-time inference service scoring and classifying conjunction risks (High, Medium, Low).
  * `tabpfn_benchmark.py`: Benchmark evaluation comparing LightGBM against TabPFN tabular foundation models.
* **`src/ml/explainability/`**:
  * `shap_explainer.py`: Generates TreeSHAP values for each risk prediction, outputting top-3 driver features for operator transparency.
* **`src/maneuver/`**:
  * `delta_v.py`: Closed-form orbital mechanics optimization for impulsive avoidance burns (along-track, radial, cross-track).
  * `optimizer.py`: Computes minimum $\Delta v$ required to expand miss distance beyond safety thresholds while minimizing fuel mass expenditure.
  * `models.py`: Maneuver advisory data structures.

---

### 4. `src/backend/`
**Owner**: Mahalakshmi (Backend & Database Lead)

* **`src/backend/api/`**:
  * `main.py`: FastAPI entry point, CORS middleware, global exception handlers, and lifecycle hooks.
  * `routes_tle.py`: Endpoints for querying tracked satellites and active debris catalogs.
  * `routes_conjunction.py`: Endpoints for fetching detected conjunction events and encounter geometry.
  * `routes_risk.py`: Endpoints returning ML-ranked risk scores and SHAP explainability payloads.
  * `routes_maneuver.py`: Endpoints delivering optimal $\Delta v$ maneuver advisories.
  * `routes_dashboard.py`: Aggregated summary endpoints (KPIs, active alert counts, risk distributions).
  * `websocket.py`: Real-time WebSocket connection streaming live conjunction updates and state changes.
* **`src/backend/db/`**:
  * `connection.py`: SQLAlchemy database engine, session factory, and connection pool management (SQLite for dev / PostgreSQL for prod).
  * `models.py`: Relational ORM models for storing TLE entries, conjunction events, ML risk scores, and maneuver logs.
  * `migrations/`: Alembic migration scripts managing database schema evolution.
* **`src/backend/schemas/`**:
  * Request and response validation schemas (Pydantic) ensuring strict compliance with API contracts.

---

### 5. `src/frontend/`
**Owner**: Balaganesh (Frontend & 3D Visualization Lead)

* **`src/frontend/public/`**:
  * Static assets, CesiumJS satellite 3D models (glTF/GLB), Earth textures, space backgrounds, and icons.
* **`src/frontend/src/components/`**:
  * `Globe/`: 3D Cesium.js widget rendering Earth, orbit polylines, real-time satellite positions, and close-approach intersection markers.
  * `RiskTable/`: Interactive, sortable risk table listing conjunction events ranked by ML priority and $P_c$.
  * `ConjunctionDetail/`: Detailed view displaying B-plane encounter diagrams, miss distance, and covariance ellipses.
  * `SHAPChart/`: Visual waterfall and bar charts showing the top-3 feature contributions explaining the ML score.
  * `ManeuverPanel/`: Interactive card showing suggested $\Delta v$ burns, fuel burn estimates, and predicted post-maneuver miss distance.
  * `AlertBanner/`: Real-time toast/notification banners alerting operators to critical high-risk conjunctions.
* **`src/frontend/src/pages/`**:
  * `DashboardPage.jsx`: Main mission-control dashboard aggregating globe, risk rankings, and alerts.
  * `AnalyticsPage.jsx`: Historical conjunction trends, $P_c$ distribution charts, and catalog statistics.
* **`src/frontend/src/utils/`**:
  * `apiClient.js`: Centralized Axios/Fetch HTTP client for calling FastAPI endpoints.
  * `cesiumHelpers.js`: Coordinate conversion utilities (ECI/J2000 $\rightarrow$ ECEF $\rightarrow$ Cartographic) for accurate Cesium globe placement.
  * `formatters.js`: Date, distance, and scientific notation formatters for clean numerical display.

---

### 6. `src/shared/`
**Owner**: ALL TEAM MEMBERS (Changes require team consensus)

* **`src/shared/constants/`**:
  * `physical.py`: Physical constants (Earth radius $R_\oplus$, gravitational parameter $\mu$, $J_2$) and algorithm thresholds (encounter sphere radius, $P_c$ boundaries, altitude band width).
* **`src/shared/frames/`**:
  * `transforms.py`: Coordinate frame transformation math (TEME $\leftrightarrow$ ECI J2000 $\leftrightarrow$ ECEF $\leftrightarrow$ RIC/RTN).
* **`src/shared/interfaces/`**:
  * `contracts.py`: **Single source of truth.** Pydantic models defining exact data schemas flowing across module boundaries (AI-1 $\rightarrow$ AI-2 $\rightarrow$ AI-3 $\rightarrow$ Backend $\rightarrow$ Frontend).

---

## 📁 Root-Level Folders

* **`tests/`** (Owner: Mahalakshmi & Module Owners)
  * `tests/unit/`: Dedicated subfolders for isolated unit tests per module (`unit/conjunction/`, `unit/propagation/`, `unit/ml/`, `unit/backend/`, etc.).
  * `tests/integration/`: End-to-end tests validating data flows across module boundaries.
  * `tests/fixtures/`: Synthetic test datasets (e.g., guaranteed head-on collision, coplanar encounters, clear misses).
  * `tests/validation/`: Benchmark tests comparing computed $P_c$ values against the official ESA Kelvins 2019 CDM dataset.
* **`data/`** (Owner: All)
  * `data/tle_cache/`: Local filesystem cache for downloaded TLE files (git-ignored).
  * `data/cdm_reference/`: Reference Conjunction Data Messages from ESA for testing and validation.
* **`docs/`** (Owner: Mahalakshmi & Team)
  * System architecture diagrams, pitch deck assets, 3-minute hackathon demo script, and user guides.
* **`scripts/`** (Owner: All)
  * Standalone CLI automation scripts (e.g., downloading TLE catalogs, running offline screening benchmarks, DB seeding).
* **`config/`** (Owner: All)
  * `settings.toml`: Tunable algorithm parameters (filter thresholds, sample counts, logging levels).

---

## 📄 Key Root Files

* `README.md`: High-level system overview, setup instructions, and team rules.
* `TEAM_DIRECTORY_GUIDE.md`: This comprehensive file and folder ownership guide.
* `pyproject.toml` & `requirements.txt`: Python package dependencies and build configurations.
* `.gitignore`: Excludes caches, virtual environments, node modules, and large data dumps from git.
