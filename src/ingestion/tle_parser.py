"""
TLE (Two-Line Element) parsing.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Decodes raw NORAD two-line element text into `ParsedTLE` objects (src/ingestion/models.py),
performing structural validation (line length/prefix) and the standard mod-10 TLE checksum,
plus a best-effort object-type classification (PAYLOAD / DEBRIS / ROCKET_BODY) from the
object name, used as a placeholder until an authoritative SATCAT lookup is available.

Column layout reference: https://celestrak.org/NORAD/documentation/tle-fmt.php
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.ingestion.models import ParsedTLE, RawTLE, TLEParseError, TLESource
from src.shared.interfaces.contracts import ObjectType

# ── Checksum ─────────────────────────────────────────────────────────────────────

def _tle_checksum(line: str) -> int:
    """Standard TLE mod-10 checksum: sum of digits, '-' counts as 1, everything else as 0."""
    total = 0
    for ch in line[:-1]:  # exclude the checksum digit itself
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10


def verify_checksum(line: str) -> bool:
    if not line or not line[-1].isdigit():
        return False
    return _tle_checksum(line) == int(line[-1])


# ── Exponential-notation decimal fields (mean_motion_ddot, bstar) ───────────────

def _parse_assumed_decimal_exp(raw: str) -> float:
    """
    Parse TLE-style 'assumed decimal point' exponential fields, e.g. ' 17182-3' -> 0.17182e-3,
    '-11606-4' -> -0.11606e-4, ' 00000+0' -> 0.0.
    """
    raw = raw.strip()
    if raw == "":
        return 0.0
    sign = 1.0
    if raw[0] == "-":
        sign = -1.0
        raw = raw[1:]
    elif raw[0] == "+":
        raw = raw[1:]

    exponent_str = raw[-2:]
    mantissa_digits = raw[:-2]
    mantissa = float(f"0.{mantissa_digits}") if mantissa_digits else 0.0
    exponent = int(exponent_str)
    return sign * mantissa * (10.0 ** exponent)


def _epoch_to_datetime(epoch_year_2digit: int, epoch_day: float) -> datetime:
    """TLE epoch -> UTC datetime. Two-digit year: 57-99 -> 1957-1999, 00-56 -> 2000-2056."""
    year = 1900 + epoch_year_2digit if epoch_year_2digit >= 57 else 2000 + epoch_year_2digit
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=epoch_day - 1)


# ── Object-type classification (heuristic, from object name) ───────────────────

_DEBRIS_MARKERS = ("DEB", "DEBRIS", "FRAGMENT")
_ROCKET_BODY_MARKERS = ("R/B", "ROCKET BODY")


def classify_object_type(name: str) -> ObjectType:
    upper = (name or "").upper().strip()
    if any(marker in upper for marker in _DEBRIS_MARKERS):
        return ObjectType.DEBRIS
    if any(marker in upper for marker in _ROCKET_BODY_MARKERS):
        return ObjectType.ROCKET_BODY
    # Celestrak's own literal placeholder for its "analyst" group (uncatalogued
    # fragments Celestrak can't yet confidently identify) -- without this,
    # "UNKNOWN" isn't empty, so it fell through to the PAYLOAD default below
    # and every uncatalogued fragment got counted as an active satellite.
    if upper == "" or upper == "UNKNOWN":
        return ObjectType.UNKNOWN
    return ObjectType.PAYLOAD


# ── Main parsing entry points ────────────────────────────────────────────────────

def parse_tle_lines(
    line1: str,
    line2: str,
    name: str = "",
    source: TLESource = TLESource.CELESTRAK,
    validate_checksum: bool = True,
) -> ParsedTLE:
    """Parse a single TLE (name + two 69-char lines) into a `ParsedTLE`."""
    line1 = line1.rstrip("\n\r")
    line2 = line2.rstrip("\n\r")
    name = name.strip()

    if len(line1) != 69:
        raise TLEParseError(f"Line 1 must be 69 characters, got {len(line1)}: {line1!r}")
    if len(line2) != 69:
        raise TLEParseError(f"Line 2 must be 69 characters, got {len(line2)}: {line2!r}")
    if not line1.startswith("1 "):
        raise TLEParseError(f"Line 1 must start with '1 ': {line1!r}")
    if not line2.startswith("2 "):
        raise TLEParseError(f"Line 2 must start with '2 ': {line2!r}")

    norad_id_l1 = line1[2:7].strip()
    norad_id_l2 = line2[2:7].strip()
    if norad_id_l1 != norad_id_l2:
        raise TLEParseError(f"NORAD ID mismatch between lines: {norad_id_l1!r} != {norad_id_l2!r}")

    checksum_valid = verify_checksum(line1) and verify_checksum(line2)
    if validate_checksum and not checksum_valid:
        raise TLEParseError(f"TLE checksum mismatch for NORAD {norad_id_l1}")

    epoch_year = int(line1[18:20])
    epoch_day = float(line1[20:32])
    epoch = _epoch_to_datetime(epoch_year, epoch_day)

    eccentricity = float(f"0.{line2[26:33].strip()}")

    parsed = ParsedTLE(
        norad_id=int(norad_id_l1),
        classification=line1[7] or "U",
        intl_designator=line1[9:17].strip(),
        name=name,
        epoch=epoch,
        epoch_year=epoch_year,
        epoch_day=epoch_day,
        mean_motion_dot=float(line1[33:43]),
        mean_motion_ddot=_parse_assumed_decimal_exp(line1[44:52]),
        bstar=_parse_assumed_decimal_exp(line1[53:61]),
        ephemeris_type=int(line1[62]) if line1[62].strip() else 0,
        element_set_number=int(line1[64:68]),
        inclination_deg=float(line2[8:16]),
        raan_deg=float(line2[17:25]),
        eccentricity=eccentricity,
        arg_perigee_deg=float(line2[34:42]),
        mean_anomaly_deg=float(line2[43:51]),
        mean_motion_rev_per_day=float(line2[52:63]),
        rev_number_at_epoch=int(line2[63:68]),
        line1=line1,
        line2=line2,
        source=source,
        checksum_valid=checksum_valid,
        object_type=classify_object_type(name),
    )
    return parsed


def parse_raw_tle(raw: RawTLE, validate_checksum: bool = True) -> ParsedTLE:
    return parse_tle_lines(raw.line1, raw.line2, name=raw.name, source=raw.source, validate_checksum=validate_checksum)


def parse_tle_file(text: str, source: TLESource = TLESource.CELESTRAK, skip_invalid: bool = True) -> list[ParsedTLE]:
    """
    Parse a multi-record TLE text blob (standard Celestrak 3-line-per-record format:
    name line, line 1, line 2, repeated). Blank lines are ignored.

    If `skip_invalid`, records that fail to parse are silently skipped instead of
    raising -- useful for large bulk catalogs where an occasional malformed/truncated
    record shouldn't abort the whole batch.
    """
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]

    results: list[ParsedTLE] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            # No name line present.
            name, line1, line2 = "", lines[i], lines[i + 1]
            i += 2
        elif i + 2 < len(lines) and lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
            name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
            i += 3
        else:
            i += 1
            continue

        try:
            results.append(parse_tle_lines(line1, line2, name=name, source=source))
        except TLEParseError:
            if not skip_invalid:
                raise
            continue

    return results
