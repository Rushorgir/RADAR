import importlib
import sys
from unittest.mock import MagicMock

# Some platforms (reported: Python 3.14 on macOS) hit C-extension deadlocks
# importing astropy/sgp4/erfa. The conjunction module doesn't need them (just
# numpy/scipy), so fall back to mocks there -- but only for modules that
# genuinely fail to import for real. On platforms where they import fine
# (e.g. this one), this is a no-op, so tests that actually need the real
# libraries (AI-1's propagation and coordinate-frame-transform tests) keep
# working instead of silently getting MagicMocks everywhere.
for _mod_name in (
    "astropy", "astropy.time", "astropy.coordinates", "astropy.units",
    "erfa", "sgp4", "sgp4.api", "sgp4.ext", "sgp4.earth_gravity",
):
    try:
        importlib.import_module(_mod_name)
    except Exception:  # noqa: BLE001 - deliberately broad: any import failure means "fall back to mock"
        sys.modules[_mod_name] = MagicMock()
