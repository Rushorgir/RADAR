import sys
from unittest.mock import MagicMock

import importlib

for _mod_name in (
    "astropy", "astropy.time", "astropy.coordinates", "astropy.units",
    "erfa", "sgp4", "sgp4.api", "sgp4.ext", "sgp4.earth_gravity",
):
    try:
        importlib.import_module(_mod_name)
    except Exception:  # noqa: BLE001
        sys.modules[_mod_name] = MagicMock()
