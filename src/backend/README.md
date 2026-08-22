# RADAR Backend Service

**Owner:** Mahalakshmi (Backend & Database Lead)  
**Branch:** `feat/mahalakshmi-backend`

This document outlines the architecture, data models, and API endpoints for the RADAR/OrbitGuard backend. It acts as the central REST API and persistence layer, sitting downstream of the AI pipelines and upstream of the frontend dashboard.

---

## 🏗 Architecture & Design Decisions

The backend is built using **FastAPI** and **SQLAlchemy**.

1. **Full-Fidelity Database:** We store all fields defined in the shared `contracts.py`. No data is lost.
2. **JSON Columns:** Complex nested data (like encounter plane matrices, covariance, and SHAP feature arrays) are stored in `JSON` columns. This ensures seamless portability between SQLite (for local dev) and PostgreSQL (for production).
3. **Clean CRUD Layer:** Database queries are isolated in `src/backend/db/crud.py`, keeping the routing layer thin and testable.
4. **Real-time WebSockets:** When the AI pipelines ingest new conjunction events or risk scores via POST endpoints, the backend instantly broadcasts these updates to all connected frontend clients via WebSockets.
5. **Structured Error Handling & Logging:** A global exception handler is registered in `main.py`, and `loguru` is used for robust, structured logging.

---

## 📂 File Structure

```text
src/backend/
├── __init__.py
├── README.md                  <-- This file
├── api/
│   ├── main.py                # FastAPI lifecycle, global handlers, and router registration
│   ├── routes_conjunction.py  # GET /api/conjunctions/ (Paginated, filtered)
│   ├── routes_dashboard.py    # GET /api/dashboard/summary (KPIs and aggregations)
│   ├── routes_ingest.py       # POST /api/ingest/* (Data entry from AI pipelines)
│   ├── routes_maneuver.py     # GET /api/maneuver/{event_id}
│   ├── routes_risk.py         # GET /api/risk/{event_id}
│   ├── routes_tle.py          # GET /api/tle/ (Paginated catalog)
│   └── websocket.py           # ws://.../ws (Connection manager & broadcasting)
├── db/
│   ├── connection.py          # Engine, SessionLocal, get_db dependency
│   ├── crud.py                # Reusable database queries
│   └── models.py              # Full-fidelity SQLAlchemy ORM models
└── schemas/
    └── api_schemas.py         # Pydantic validation for requests/responses
```

---

## 🗄️ Database Models

Defined in `db/models.py`.

- **`ConjunctionEventModel`**: The core table. Tracks primary/secondary NORAD IDs, TCA (Time of Closest Approach), Probability of Collision (Pc), risk categories, and ML insights.
- **`TLEModel`**: Tracks specific Two-Line Element data parsed into distinct orbital elements for querying.

*Note: The SQLite database file (`radar.db`) is automatically created at the project root on startup.*

---

## 🚀 API Endpoints

### Data Retrieval (GET)
- **`GET /api/dashboard/summary`**: Returns aggregated KPIs (total tracked, active alerts, risk distribution pie chart data).
- **`GET /api/conjunctions/`**: Returns a paginated list of conjunction events. Supports `?risk_category=HIGH` filtering.
- **`GET /api/conjunctions/{event_id}`**: Full details of a single event.
- **`GET /api/tle/`**: Paginated catalog of all parsed TLEs.
- **`GET /api/risk/{event_id}`**: Retrieves the ML risk score and SHAP feature array.
- **`GET /api/maneuver/{event_id}`**: Retrieves the maneuver advisory (Delta-V, burn direction, fuel cost).

### Pipeline Ingestion (POST)
These endpoints are designed for the AI pipelines to push data into the backend.
- **`POST /api/ingest/tle`**: Ingests fresh TLE catalogs.
- **`POST /api/ingest/conjunction`**: Ingests new geometrical conjunction calculations (AI-2).
- **`POST /api/ingest/risk`**: Updates an existing event with ML risk scores and maneuver advisories (AI-3).

*Pushing data to the `conjunction` or `risk` endpoints automatically triggers a WebSocket broadcast.*

### Real-Time Streams (WebSocket)
- **`WS /ws`**: Connect here from the React frontend to receive live JSON payloads whenever new events are ingested.

---

## 🛠️ How to Run & Test Locally

**1. Seed the Database with Synthetic Data**
We provide a seeding script to populate the local database with 50 TLEs and 30 Conjunction Events (spanning HIGH, MEDIUM, and LOW risks).
```bash
python scripts/seed_database.py
```

**2. Start the Server**
```bash
uvicorn src.backend.api.main:app --reload
```
The server will run on `http://127.0.0.1:8000`.

**3. Explore the Interactive API Docs**
Navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser to view the Swagger UI, test the endpoints, and inspect the Pydantic schemas.

**4. Run the Unit Tests**
The entire backend is covered by Pytest unit tests located in `tests/unit/backend/`.
```bash
python -m pytest tests/unit/backend/ -v
```
