"""
Data models for the TLE ingestion pipeline.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Two levels of representation:
  * RawTLE    -- exactly what we downloaded (name + two 69-char lines + provenance).
  * ParsedTLE -- every field of the TLE decoded into typed, physically-meaningful
                 values, ready to be handed to src/propagation/sgp4_engine.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from src.shared.interfaces.contracts import ObjectType


class TLESource(str, Enum):
    """Where a TLE was obtained from."""
    CELESTRAK = "CELESTRAK"
    CACHE = "CACHE"
    MANUAL = "MANUAL"


class RawTLE(BaseModel):
    """A TLE exactly as retrieved, before any field-level parsing."""

    name: str = Field(..., description="Object name (from the 0-line / catalog), whitespace-stripped")
    line1: str = Field(..., min_length=69, max_length=69, description="TLE line 1 (69 chars)")
    line2: str = Field(..., min_length=69, max_length=69, description="TLE line 2 (69 chars)")
    source: TLESource = TLESource.CELESTRAK
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("line1")
    @classmethod
    def _line1_starts_correctly(cls, v: str) -> str:
        if not v.startswith("1 "):
            raise ValueError("TLE line 1 must start with '1 '")
        return v

    @field_validator("line2")
    @classmethod
    def _line2_starts_correctly(cls, v: str) -> str:
        if not v.startswith("2 "):
            raise ValueError("TLE line 2 must start with '2 '")
        return v

    @property
    def norad_id(self) -> int:
        return int(self.line1[2:7])


class ParsedTLE(BaseModel):
    """
    Fully decoded TLE fields (per the standard NORAD two-line element format),
    plus the raw lines needed for SGP4 propagation and a best-effort object
    classification used until an authoritative SATCAT lookup is wired in.
    """

    # Identity
    norad_id: int = Field(..., description="NORAD catalog number")
    classification: str = Field("U", description="U=Unclassified, C=Classified, S=Secret")
    intl_designator: str = Field(..., description="International designator (YYNNNPPP)")
    name: str = ""

    # Epoch
    epoch: datetime = Field(..., description="TLE epoch, UTC")
    epoch_year: int
    epoch_day: float

    # Mean-motion derivatives / drag
    mean_motion_dot: float = Field(..., description="First derivative of mean motion / 2 (rev/day^2)")
    mean_motion_ddot: float = Field(..., description="Second derivative of mean motion / 6 (rev/day^3)")
    bstar: float = Field(..., description="B* drag term (1/Earth radii)")

    # Orbital elements
    inclination_deg: float = Field(..., ge=0, le=180)
    raan_deg: float = Field(..., ge=0, lt=360, description="Right ascension of ascending node")
    eccentricity: float = Field(..., ge=0, lt=1)
    arg_perigee_deg: float = Field(..., ge=0, lt=360)
    mean_anomaly_deg: float = Field(..., ge=0, lt=360)
    mean_motion_rev_per_day: float = Field(..., gt=0)
    rev_number_at_epoch: int = 0
    ephemeris_type: int = 0
    element_set_number: int = 0

    # Provenance / raw lines (SGP4 needs the exact original lines)
    line1: str
    line2: str
    source: TLESource = TLESource.CELESTRAK
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checksum_valid: bool = True

    object_type: ObjectType = ObjectType.UNKNOWN

    def semi_major_axis_km(self) -> float:
        """Approximate semi-major axis (km) from mean motion via Kepler's third law."""
        from src.shared.constants.physical import EARTH

        n_rad_s = self.mean_motion_rev_per_day * 2.0 * 3.14159265358979 / 86400.0
        return (EARTH.MU_KM3_S2 / (n_rad_s ** 2)) ** (1.0 / 3.0)

    def perigee_altitude_km(self) -> float:
        from src.shared.constants.physical import EARTH

        a = self.semi_major_axis_km()
        return a * (1 - self.eccentricity) - EARTH.RADIUS_KM

    def apogee_altitude_km(self) -> float:
        from src.shared.constants.physical import EARTH

        a = self.semi_major_axis_km()
        return a * (1 + self.eccentricity) - EARTH.RADIUS_KM


class TLEParseError(ValueError):
    """Raised when a TLE line pair fails structural or checksum validation."""


class TLEFetchError(RuntimeError):
    """Raised when fetching TLE data from a remote source fails."""
