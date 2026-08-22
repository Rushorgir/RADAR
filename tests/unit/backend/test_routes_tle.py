from datetime import datetime

from src.backend.db import crud

ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"


def test_get_tle_catalog(client, db_session):
    # Seed data
    tle_data = {
        "object_id": "111",
        "line1": "1...",
        "line2": "2...",
        "epoch": datetime.utcnow()
    }
    crud.create_tle(db_session, tle_data)
    
    response = client.get("/api/tle/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 1
    assert data["items"][0]["object_id"] == "111"

def test_get_tle_for_object(client, db_session):
    tle_data = {
        "object_id": "222",
        "line1": "1...",
        "line2": "2...",
        "epoch": datetime.utcnow()
    }
    crud.create_tle(db_session, tle_data)
    
    response = client.get("/api/tle/222")
    assert response.status_code == 200
    assert response.json()["object_id"] == "222"

def test_get_tle_not_found(client):
    response = client.get("/api/tle/999")
    assert response.status_code == 404

def test_get_current_positions(client, db_session):
    """
    /api/tle/positions must be registered ahead of /{object_id} -- if it
    weren't, this request would instead match /{object_id} with
    object_id="positions" and 404, rather than returning the real schema.
    """
    crud.create_tle(db_session, {
        "object_id": "25544",
        "object_name": "ISS (ZARYA)",
        "line1": ISS_LINE1,
        "line2": ISS_LINE2,
        "epoch": datetime.utcnow(),
    })

    response = client.get("/api/tle/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["requested"] == 1
    assert len(data["positions"]) == 1
    position = data["positions"][0]
    assert position["object_id"] == "25544"
    assert -90.0 <= position["latitude_deg"] <= 90.0
    assert -180.0 <= position["longitude_deg"] <= 180.0

def test_get_current_positions_skips_unparseable_tle(client, db_session):
    """A malformed stored TLE shouldn't 500 the whole endpoint -- it's
    dropped (requested still counts it; positions doesn't)."""
    crud.create_tle(db_session, {
        "object_id": "25544",
        "object_name": "ISS (ZARYA)",
        "line1": ISS_LINE1,
        "line2": ISS_LINE2,
        "epoch": datetime.utcnow(),
    })
    crud.create_tle(db_session, {
        "object_id": "111",
        "line1": "1...",
        "line2": "2...",
        "epoch": datetime.utcnow(),
    })

    response = client.get("/api/tle/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["requested"] == 2
    assert len(data["positions"]) == 1
    assert data["positions"][0]["object_id"] == "25544"
