# RADAR / OrbitGuard: Team Directory & Workspace Guide

This document outlines the exact contents of each folder in the repository and specifies which team member owns and is responsible for each section. 

> **Workspace Isolation Rule**: To avoid git merge conflicts and ensure modularity, you MUST write code ONLY in your assigned directories. If you need functionality from another module, use the shared contracts or request an update from the module owner.

---

## 🛠️ The `src/` Directory (Core Source Code)

The `src/` folder is divided by functional modules. Each team member has absolute ownership over their designated folders.

### 1. `src/ingestion/` & `src/propagation/`
**Owner**: Anas (AI-1: Orbital Mechanics Lead)
* **`src/ingestion/`**: Contains scripts and utilities to fetch Two-Line Elements (TLEs) from Celestrak, parse the raw text, and cache them locally.
* **`src/propagation/`**: Contains the SGP4/SDP4 propagation engine (using the `sgp4` library). Responsible for taking TLEs and generating discrete state vectors (position and velocity) in the ECI/J2000 coordinate frame across future timesteps.

### 2. `src/conjunction/`
**Owner**: Rushaan (AI-2: Conjunction & Probability Math Lead)
* **`src/conjunction/models/`**: Internal data structures for encounter geometry and conjunction events.
* **`src/conjunction/screening/`**: The two-stage filter engine. Includes `coarse_filter.py` (altitude band bucketing) and `fine_filter.py` (3D spatial index / k-d tree), plus Time of Closest Approach (TCA) interpolation.
* **`src/conjunction/probability/`**: The math engine for computing Probability of Collision ($P_c$). Contains `foster_2d.py` (primary analytical method) and `monte_carlo.py` (fallback numerical method), as well as coordinate frame transformations to the encounter plane.

### 3. `src/ml/` & `src/maneuver/`
**Owner**: Udarsh (AI-3: ML & Decision Support)
* **`src/ml/features/`**: Code to extract and preprocess ML features (miss distance, relative velocity, etc.) from the physics engine's conjunction events.
* **`src/ml/ranking/`**: The LightGBM risk ranking model training and inference scripts, as well as the TabPFN benchmark.
* **`src/ml/explainability/`**: Integration with SHAP to generate feature importance values for each conjunction event.
* **`src/maneuver/`**: Closed-form orbital mechanics algorithms to compute minimum delta-v (Δv) avoidance maneuvers for flagged high-risk conjunctions.

### 4. `src/backend/` & `src/frontend/`
**Owner**: Balaganesh (Web / Full-Stack Developer)
* **`src/backend/`**: A FastAPI-based REST API. Includes route handlers (`api/`), database models and migrations (`db/`), and request/response validation schemas (`schemas/`). Acts as the glue connecting the AI modules to the dashboard.
* **`src/frontend/`**: The React-based web dashboard. Contains components (`src/components/`), views (`src/pages/`), and the crucial 3D Cesium.js globe visualization for rendering orbits, conjunction alerts, and SHAP charts.

### 5. `src/shared/`
**Owner**: ALL TEAM MEMBERS (Changes require team consensus)
* **`src/shared/constants/`**: Physical constants (Earth radius, $\mu$) and global system thresholds (screening margins, $P_c$ limits).
* **`src/shared/frames/`**: Utility functions for coordinate transformations (e.g., TEME to ECI/ECEF).
* **`src/shared/interfaces/contracts.py`**: **The most important file in the repo.** Contains the Pydantic models (JSON schemas) defining exactly how data flows between AI-1, AI-2, AI-3, and the Web backend.

---

## 📁 Root-Level Folders

These folders support the development, testing, and operation of the core code:

* **`tests/`** (Owner: Mahalakshmi & Module Owners)
  * `tests/unit/`: Dedicated subfolders for each module's unit tests (e.g., `tests/unit/conjunction/`). Module owners write their own unit tests.
  * `tests/integration/`: End-to-end pipeline tests ensuring modules talk to each other correctly.
  * `tests/fixtures/`: Synthetic test data (e.g., known head-on collisions) used for validation.
  * `tests/validation/`: Cross-checking results against the public ESA Kelvins 2019 dataset.
* **`data/`** (Owner: All)
  * `data/tle_cache/`: Local storage for downloaded TLEs (ignored by git).
  * `data/cdm_reference/`: Reference Conjunction Data Messages (CDM) for testing.
* **`docs/`** (Owner: Mahalakshmi)
  * Contains the architecture diagrams, the final pitch deck, demo scripts, and project documentation.
* **`scripts/`** (Owner: All)
  * Utility scripts for downloading datasets, bootstrapping the database, or running the full pipeline from the CLI.
* **`config/`** (Owner: All)
  * Environment configurations, `.env` templates, and `settings.toml` for configuring the pipeline thresholds.

---

## 📄 Key Root Files
* `README.md`: High-level overview and team rules.
* `TEAM_DIRECTORY_GUIDE.md`: Detailed team folder and component breakdown guide.
* `pyproject.toml` & `requirements.txt`: Python package definitions and dependencies.
* `.gitignore`: Rules for keeping secrets, virtual environments, and large data files out of version control.
