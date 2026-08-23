"""
Consolidated backend test suite — CRUD, routes, and WebSocket.

Covers the full FastAPI backend: database operations, all API route handlers,
ingestion endpoints, and WebSocket connectivity.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.api.main import app
from src.backend.db import crud
from src.backend.db.connection import Base, get_db

# ── Fixtures ──────────────────────────────────────────────────────────────────

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"


def _make_event(event_id: str = "evt-1", **overrides) -> dict:
    """Helper to build a minimal valid conjunction event dict."""
    base = {
        "event_id": event_id,
        "primary_id": "111",
        "secondary_id": "222",
        "tca": datetime.now(timezone.utc),
        "miss_distance_km": 1.0,
        "relative_velocity_km_s": 7.0,
        "pc": 1e-4,
        "pc_method": "FOSTER_2D",
    }
    base.update(overrides)
    return base


def _make_tle(object_id: str = "25544", **overrides) -> dict:
    base = {
        "object_id": object_id,
        "line1": ISS_LINE1,
        "line2": ISS_LINE2,
        "epoch": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Root & Health ─────────────────────────────────────────────────────────────

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_crud_tle_create_and_fetch(db_session):
    tle = crud.create_tle(db_session, _make_tle("25544", object_name="ISS"))
    assert tle.object_id == "25544"
    assert tle.id is not None
    fetched = crud.get_tle_by_object_id(db_session, "25544")
    assert fetched is not None
    assert fetched.id == tle.id


def test_crud_conjunction_lifecycle(db_session):
    """Create, fetch, count, and update a conjunction event."""
    event = crud.create_conjunction_event(db_session, _make_event("c-1", risk_category="HIGH"))
    assert event.event_id == "c-1"
    fetched = crud.get_conjunction_event_by_id(db_session, "c-1")
    assert fetched is not None
    assert fetched.primary_id == "111"
    assert crud.get_conjunction_events_count(db_session) == 1
    updated = crud.update_conjunction_event(db_session, "c-1", {"ml_risk_score": 0.95})
    assert updated is not None
    assert updated.ml_risk_score == 0.95


# ── TLE Routes ────────────────────────────────────────────────────────────────

def test_tle_catalog(client, db_session):
    crud.create_tle(db_session, _make_tle("111", line1="1...", line2="2..."))
    r = client.get("/api/tle/")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_tle_by_id(client, db_session):
    crud.create_tle(db_session, _make_tle("222", line1="1...", line2="2..."))
    assert client.get("/api/tle/222").status_code == 200
    assert client.get("/api/tle/999").status_code == 404


def test_positions(client, db_session):
    print("test_positions: creating TLE")
    crud.create_tle(db_session, _make_tle("25544", object_name="ISS (ZARYA)"))
    print("test_positions: calling GET")
    r = client.get("/api/tle/positions")
    print("test_positions: GET returned")
    assert r.status_code == 200
    data = r.json()
    assert data["requested"] == 1
    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert -90 <= pos["latitude_deg"] <= 90
    print("test_positions: done")


def test_positions_at_param(client, db_session):
    crud.create_tle(db_session, _make_tle("25544", object_name="ISS"))
    r_now = client.get("/api/tle/positions")
    r_future = client.get("/api/tle/positions?at=2026-09-15T12:00:00Z")
    assert r_future.status_code == 200
    assert r_future.json()["epoch"].startswith("2026-09-15T12:00:00")


def test_positions_skips_bad_tle(client, db_session):
    crud.create_tle(db_session, _make_tle("25544", object_name="ISS"))
    crud.create_tle(db_session, _make_tle("111", line1="1...", line2="2..."))
    r = client.get("/api/tle/positions")
    assert r.json()["requested"] == 2
    assert len(r.json()["positions"]) == 1


# ── Conjunction Routes ────────────────────────────────────────────────────────

def test_conjunctions_list_and_filter(client, db_session):
    crud.create_conjunction_event(db_session, _make_event("e-1", risk_category="HIGH"))
    assert client.get("/api/conjunctions/").json()["total"] == 1
    assert client.get("/api/conjunctions/?risk_category=HIGH").json()["total"] == 1
    assert client.get("/api/conjunctions/?risk_category=LOW").json()["total"] == 0


def test_conjunction_by_id(client, db_session):
    crud.create_conjunction_event(db_session, _make_event("e-2"))
    assert client.get("/api/conjunctions/e-2").status_code == 200
    assert client.get("/api/conjunctions/missing").status_code == 404


# ── Risk Routes ───────────────────────────────────────────────────────────────

def test_risk_score(client, db_session):
    crud.create_conjunction_event(db_session, _make_event(
        "r-1", ml_risk_score=0.85, risk_category="HIGH",
        shap_top_features=[{"feature": "pc", "impact": 0.4}],
    ))
    r = client.get("/api/risk/r-1")
    assert r.status_code == 200
    assert r.json()["ml_risk_score"] == 0.85
    assert client.get("/api/risk/missing").status_code == 404


# ── Maneuver Routes ───────────────────────────────────────────────────────────

def test_maneuver_advisory(client, db_session):
    crud.create_conjunction_event(db_session, _make_event(
        "m-1", maneuver_delta_v_m_s=0.15, maneuver_burn_direction="ALONG_TRACK",
        maneuver_new_miss_distance_km=5.5, maneuver_fuel_cost_estimate_kg=0.02,
    ))
    r = client.get("/api/maneuver/m-1")
    assert r.status_code == 200
    assert r.json()["delta_v_m_s"] == 0.15


def test_maneuver_no_advisory(client, db_session):
    crud.create_conjunction_event(db_session, _make_event("m-2"))
    assert client.get("/api/maneuver/m-2").status_code == 404


# ── Dashboard Routes ──────────────────────────────────────────────────────────

def test_dashboard_summary(client, db_session):
    crud.create_tle(db_session, _make_tle("1", line1="1...", line2="2..."))
    crud.create_tle(db_session, _make_tle("2", line1="1...", line2="2..."))
    crud.create_conjunction_event(db_session, _make_event("d-1", risk_category="HIGH"))
    crud.create_conjunction_event(db_session, _make_event(
        "d-2", primary_id="1", secondary_id="3", pc=1e-6,
        miss_distance_km=5.0, risk_category="LOW",
    ))
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_tracked_objects"] == 2
    assert data["total_conjunction_events"] == 2
    assert data["risk_distribution"]["HIGH"] == 1


# ── Ingest Routes ─────────────────────────────────────────────────────────────

def test_ingest_conjunction(client):
    payload = {
        "event_id": "ingest-1",
        "primary_id": "1000",
        "secondary_id": "2000",
        "tca": "2024-01-01T00:00:00Z",
        "miss_distance_km": 2.5,
        "relative_velocity_km_s": 12.0,
        "pc": 0.0005,
        "pc_method": "FOSTER_2D",
        "combined_hard_body_radius_km": 0.015,
        "primary_object_type": "PAYLOAD",
        "secondary_object_type": "DEBRIS",
    }
    r = client.post("/api/ingest/conjunction", json=payload)
    assert r.status_code == 200
    assert r.json()["event_id"] == "ingest-1"


def test_ingest_risk_score(client):
    # Seed an event first
    test_ingest_conjunction(client)
    payload = {
        "event_id": "ingest-1",
        "ml_risk_score": 0.88,
        "risk_category": "HIGH",
        "shap_top_features": [{"feature": "miss_distance", "impact": 0.5}],
    }
    r = client.post("/api/ingest/risk", json=payload)
    assert r.status_code == 200
    assert r.json()["ml_risk_score"] == 0.88


# ── WebSocket ─────────────────────────────────────────────────────────────────

def test_websocket_connect(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        # Connection succeeded without exception
