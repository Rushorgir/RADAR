"""
Global test fixtures and C-extension mock fallbacks.

Some platforms hit C-extension deadlocks importing astropy/sgp4/erfa.
The conjunction module doesn't need them (just numpy/scipy), so fall back
to mocks — but only for modules that genuinely fail to import.
"""
import importlib
import sys
from unittest.mock import MagicMock

for _mod_name in (
    "astropy", "astropy.time", "astropy.coordinates", "astropy.units",
    "erfa", "sgp4", "sgp4.api", "sgp4.ext", "sgp4.earth_gravity",
):
    try:
        importlib.import_module(_mod_name)
    except Exception:
        sys.modules[_mod_name] = MagicMock()
