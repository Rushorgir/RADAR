from __future__ import annotations

"""TLE ingestion: fetch from Celestrak, parse, and cache locally."""

from src.ingestion.models import ParsedTLE, RawTLE, TLEFetchError, TLEParseError, TLESource
from src.ingestion.tle_cache import TLECache
from src.ingestion.tle_fetcher import (
    CELESTRAK_GROUPS,
    build_default_dataset,
    fetch_group,
    fetch_groups,
    filter_leo,
)
from src.ingestion.tle_parser import classify_object_type, parse_tle_file, parse_tle_lines, verify_checksum

__all__ = [
    "ParsedTLE",
    "RawTLE",
    "TLEFetchError",
    "TLEParseError",
    "TLESource",
    "TLECache",
    "CELESTRAK_GROUPS",
    "build_default_dataset",
    "fetch_group",
    "fetch_groups",
    "filter_leo",
    "classify_object_type",
    "parse_tle_file",
    "parse_tle_lines",
    "verify_checksum",
]
