"""
Re-entry / orbital decay risk assessment.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Real orbital-decay prediction needs a real atmospheric density model
(NRLMSISE-00 or similar), solar/geomagnetic activity indices, and a
precisely-calibrated drag coefficient -- all out of scope for this
prototype (same honesty as src/propagation/covariance.py's synthetic
covariance model: physically-plausible and useful for screening/ranking,
not a substitute for an operational decay prediction like those Celestrak
or Aerospace Corp actually publish).

Instead this uses two simpler, well-established signals that need nothing
beyond the TLE itself:

1. Perigee altitude -- a TLE's mean orbital elements alone (semi-major
   axis + eccentricity, both encoded directly in the TLE, no propagation
   needed) give perigee altitude. Objects with very low perigee are, by
   definition, dipping deep enough into the atmosphere for drag to be a
   dominant force -- decay is imminent regardless of exactly how fast.
2. SGP4's own SATELLITE_HAS_DECAYED error code -- SGP4 refuses to
   propagate an object once its orbit has mathematically decayed below
   the model's validity (perigee inside the Earth). That's an unambiguous
   "this object no longer has a meaningful orbit" signal, stronger than a
   threshold guess.

`estimate_days_to_reentry` additionally folds in B* (the TLE's own drag
term) for a *rough* ranking within the WATCH/ELEVATED bands -- explicitly
a coarse order-of-magnitude estimate for sorting "which of these should
we look at first", not a delivery-date prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sgp4.api import WGS84, Satrec

from src.ingestion.models import ParsedTLE
from src.propagation.models import SGP4ErrorCode


class ReentryRiskTier(str, Enum):
    IMMINENT = "IMMINENT"  # SGP4 reports the orbit has already decayed, or perigee is in the sensible-fiery-reentry band
    ELEVATED = "ELEVATED"  # perigee low enough that drag dominates within roughly days-to-weeks
    WATCH = "WATCH"        # perigee low enough to be worth tracking, decay likely within months
    NOMINAL = "NOMINAL"    # perigee comfortably above meaningful atmospheric drag


# Perigee altitude thresholds (km). Approximate, not a physical constant --
# real decay timing depends heavily on solar-cycle-driven atmospheric
# density, ballistic coefficient, and attitude/tumbling, none of which a
# TLE alone can tell you. These bands are wide enough to be a reasonable
# triage signal despite that uncertainty.
IMMINENT_PERIGEE_KM = 120.0
ELEVATED_PERIGEE_KM = 200.0
WATCH_PERIGEE_KM = 300.0


def classify_perigee_risk(perigee_altitude_km: float) -> ReentryRiskTier:
    if perigee_altitude_km <= IMMINENT_PERIGEE_KM:
        return ReentryRiskTier.IMMINENT
    if perigee_altitude_km <= ELEVATED_PERIGEE_KM:
        return ReentryRiskTier.ELEVATED
    if perigee_altitude_km <= WATCH_PERIGEE_KM:
        return ReentryRiskTier.WATCH
    return ReentryRiskTier.NOMINAL


def estimate_days_to_reentry(perigee_altitude_km: float, bstar: float) -> float | None:
    """
    Very rough order-of-magnitude estimate, for sorting "most urgent first"
    within a risk tier -- not a real decay-time prediction (see module
    docstring). Returns None outside the WATCH/ELEVATED/IMMINENT bands,
    where decay isn't imminent enough for this kind of estimate to mean
    anything.

    Modeled as an exponential decay in perigee altitude with a rate
    proportional to B* (a bigger B* means more drag per orbit, i.e. faster
    decay) -- captures the right qualitative behavior (higher B* or lower
    starting perigee -> sooner) without pretending to real precision.
    """
    if perigee_altitude_km > WATCH_PERIGEE_KM:
        return None
    if perigee_altitude_km <= IMMINENT_PERIGEE_KM:
        return 0.0

    b = max(abs(bstar), 1e-6)  # guard against a zero/negative B* (some payloads report ~0)
    # Calibrated so a "typical" decaying-debris B* (~1e-3 /Earth-radii) puts
    # a 200km perigee at roughly a couple of weeks out and a 300km perigee
    # at a couple of months -- the right ballpark for real LEO decay
    # timescales (objects this low are usually gone within weeks to a few
    # months, not the better part of a year), not a derived physical formula.
    days = (perigee_altitude_km - IMMINENT_PERIGEE_KM) / (4000.0 * b)
    return round(min(days, 3650.0), 1)  # cap at ~10 years so a near-zero B* doesn't print nonsense


@dataclass(frozen=True)
class ReentryPrediction:
    object_id: str
    name: str
    object_type: str
    perigee_altitude_km: float
    apogee_altitude_km: float
    risk_tier: ReentryRiskTier
    estimated_days_to_reentry: float | None
    sgp4_confirmed_decayed: bool


def _is_sgp4_confirmed_decayed(tle: ParsedTLE, at: datetime) -> bool:
    """Ask SGP4 directly whether it considers this orbit already decayed at `at`."""
    try:
        satrec = Satrec.twoline2rv(tle.line1, tle.line2, WGS84)
        jd_epoch, jd_frac = _to_jd(at)
        error, _r, _v = satrec.sgp4(jd_epoch, jd_frac)
    except Exception:  # noqa: BLE001 -- a parse/propagation failure isn't a decay signal either way
        return False
    return error == SGP4ErrorCode.SATELLITE_HAS_DECAYED


def _to_jd(epoch: datetime) -> tuple[float, float]:
    from sgp4.api import jday

    if epoch.tzinfo is not None:
        epoch = epoch.astimezone(timezone.utc).replace(tzinfo=None)
    return jday(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute, epoch.second + epoch.microsecond * 1e-6)


def predict_reentry_watch(
    parsed_tles: list[ParsedTLE],
    at: datetime | None = None,
    include_nominal: bool = False,
) -> list[ReentryPrediction]:
    """
    Assess every object in `parsed_tles` for re-entry risk. Returns
    predictions sorted most-urgent-first (IMMINENT/lowest perigee first).

    `include_nominal`: if False (default), objects classified NOMINAL are
    omitted entirely -- this is meant to power a "watch list" of objects
    actually worth attention, not a full-catalog dump where the vast
    majority of entries are "nothing to see here".
    """
    at = at or datetime.now(timezone.utc)
    predictions: list[ReentryPrediction] = []

    for tle in parsed_tles:
        try:
            perigee_km = tle.perigee_altitude_km()
            apogee_km = tle.apogee_altitude_km()
        except (ValueError, ZeroDivisionError):
            continue  # malformed mean motion -- nothing meaningful to report

        decayed = _is_sgp4_confirmed_decayed(tle, at)
        tier = ReentryRiskTier.IMMINENT if decayed else classify_perigee_risk(perigee_km)

        if tier == ReentryRiskTier.NOMINAL and not include_nominal:
            continue

        predictions.append(
            ReentryPrediction(
                object_id=str(tle.norad_id),
                name=tle.name or f"OBJ-{tle.norad_id}",
                object_type=tle.object_type.value,
                perigee_altitude_km=round(perigee_km, 1),
                apogee_altitude_km=round(apogee_km, 1),
                risk_tier=tier,
                estimated_days_to_reentry=0.0 if decayed else estimate_days_to_reentry(perigee_km, tle.bstar),
                sgp4_confirmed_decayed=decayed,
            )
        )

    tier_rank = {
        ReentryRiskTier.IMMINENT: 0,
        ReentryRiskTier.ELEVATED: 1,
        ReentryRiskTier.WATCH: 2,
        ReentryRiskTier.NOMINAL: 3,
    }
    predictions.sort(key=lambda p: (tier_rank[p.risk_tier], p.perigee_altitude_km))
    return predictions
