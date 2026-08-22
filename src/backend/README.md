# Backend Module — Owner: Balaganesh

## Responsibility
- FastAPI REST API serving all modules
- PostgreSQL/SQLite database for event persistence
- Pydantic request/response schemas matching interface contracts
- WebSocket support for live dashboard updates

## Sub-modules

### `api/` — Route Handlers
- `main.py` — FastAPI app factory, CORS, middleware
- `routes_tle.py` — TLE ingestion endpoints
- `routes_conjunction.py` — Conjunction event endpoints
- `routes_risk.py` — ML risk ranking endpoints
- `routes_maneuver.py` — Maneuver advisory endpoints
- `routes_dashboard.py` — Dashboard data aggregation endpoints

### `db/` — Database Layer
- `models.py` — SQLAlchemy ORM models
- `connection.py` — DB connection & session management
- `migrations/` — Alembic migrations

### `schemas/` — API Schemas
- Pydantic models for all request/response payloads
- Maps to the shared interface contracts

## Endpoints (Planned)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tle/objects` | List tracked objects |
| GET | `/api/conjunctions` | List conjunction events |
| GET | `/api/conjunctions/{id}` | Get conjunction detail |
| GET | `/api/risk/ranked` | Get ML-ranked risk list |
| GET | `/api/maneuver/{event_id}` | Get maneuver advisory |
| WS | `/ws/live` | Live event stream |
