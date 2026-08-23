"""
Global test fixtures and C-extension mock fallbacks.

Some platforms hit C-extension deadlocks importing astropy/sgp4/erfa.
The conjunction module doesn't need them (just numpy/scipy), so fall back
to mocks — but only for modules that genuinely fail to import.
"""
import os
import importlib
import sys
from unittest.mock import MagicMock
import pytest

# Direct all test DB operations to a separate isolated test database
os.environ["DATABASE_URL"] = "sqlite:///./data/test_radar.db"

for _mod_name in (
    "astropy", "astropy.time", "astropy.coordinates", "astropy.units",
    "erfa", "sgp4", "sgp4.api", "sgp4.ext", "sgp4.earth_gravity",
):
    try:
        importlib.import_module(_mod_name)
    except Exception:
        sys.modules[_mod_name] = MagicMock()

@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    from src.backend.db.connection import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
