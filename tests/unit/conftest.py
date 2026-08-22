import sys
from unittest.mock import MagicMock

# Mock astropy and sgp4 to avoid C-extension deadlocks on Python 3.14 on macOS
sys.modules['astropy'] = MagicMock()
sys.modules['astropy.time'] = MagicMock()
sys.modules['astropy.coordinates'] = MagicMock()
sys.modules['astropy.units'] = MagicMock()
sys.modules['erfa'] = MagicMock()
sys.modules['sgp4'] = MagicMock()
sys.modules['sgp4.api'] = MagicMock()
sys.modules['sgp4.ext'] = MagicMock()
sys.modules['sgp4.earth_gravity'] = MagicMock()
