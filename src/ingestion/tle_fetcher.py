"""
Celestrak TLE fetcher.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Pulls Two-Line Element sets for active satellites, debris clouds, and rocket
bodies from Celestrak's GP (General Perturbations) query API, with retries,
local caching (via TLECache) as a fallback when the network is unavailable,
and de-duplication / LEO filtering to assemble the working dataset used by
src/propagation/.

Celestrak GP API reference: https://celestrak.org/NORAD/documentation/gp-data-formats.php
"""

from __future__ import annotations

import random
import time
from typing import Optional

import httpx
from loguru import logger

from src.ingestion.models import ParsedTLE, TLEFetchError, TLESource
from src.ingestion.tle_cache import TLECache
from src.ingestion.tle_parser import parse_tle_file

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"

# Curated Celestrak GROUP names that together give a reasonably realistic mix of
# payloads, debris, and rocket bodies in LEO for the ~500-1000 object propagation
# target described in src/propagation/README.md. See
# https://celestrak.org/NORAD/elements/index.php for the full catalog of groups.
CELESTRAK_GROUPS = {
    "stations": "stations",                        # crewed/large LEO payloads (ISS, Tiangong, ...)
    "active": "active",                             # all active payloads (large; filter to LEO)
    "cosmos_2251_debris": "cosmos-2251-debris",     # 2009 Iridium-Cosmos collision debris
    "iridium_33_debris": "iridium-33-debris",       # 2009 Iridium-Cosmos collision debris
    "cosmos_1408_debris": "cosmos-1408-debris",     # 2021 Russian ASAT test debris
    "fengyun_1c_debris": "fengyun-1c-debris",       # 2007 Chinese ASAT test debris
}

DEFAULT_TIMEOUT_S = 15.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_S = 1.5


class TLENotModified(TLEFetchError):
    """
    Celestrak throttles repeat downloads of the same GROUP within its ~2h update
    window and answers with HTTP 403 + an explanatory "has not updated since your
    last successful download" body. That's not a failure -- it means our existing
    cached copy is still the latest data -- so it's raised as its own type and
    must NOT be retried with backoff like a real transient error.
    """


def _is_not_modified_response(response: httpx.Response) -> bool:
    return response.status_code == 403 and "has not updated" in response.text.lower()


def fetch_group_raw(
    group: str,
    fmt: str = "tle",
    timeout_s: float = DEFAULT_TIMEOUT_S,
    retries: int = DEFAULT_RETRIES,
    client: Optional[httpx.Client] = None,
) -> str:
    """
    Fetch the raw TLE text for a single Celestrak GROUP. Retries transient
    failures with linear backoff; raises TLEFetchError if all attempts fail,
    or TLENotModified if Celestrak's own throttle reports no new data.
    """
    params = {"GROUP": group, "FORMAT": fmt}
    owns_client = client is None
    http_client = client or httpx.Client(timeout=timeout_s)

    last_error: Optional[Exception] = None
    try:
        for attempt in range(1, retries + 1):
            try:
                response = http_client.get(CELESTRAK_GP_URL, params=params)
                if _is_not_modified_response(response):
                    raise TLENotModified(f"Celestrak has no newer data for group {group!r}: {response.text.strip()}")
                response.raise_for_status()
                text = response.text
                if not text.strip():
                    raise TLEFetchError(f"Celestrak returned empty body for group {group!r}")
                return text
            except TLENotModified:
                raise  # not a transient error -- don't retry/backoff
            except (httpx.HTTPError, TLEFetchError) as exc:
                last_error = exc
                logger.warning(f"[tle_fetcher] attempt {attempt}/{retries} failed for group {group!r}: {exc}")
                if attempt < retries:
                    time.sleep(DEFAULT_BACKOFF_S * attempt)
    finally:
        if owns_client:
            http_client.close()

    raise TLEFetchError(f"Failed to fetch Celestrak group {group!r} after {retries} attempts: {last_error}")


def fetch_group(
    group: str,
    cache: Optional[TLECache] = None,
    use_cache: bool = True,
    force_refresh: bool = False,
    fallback_to_stale_cache: bool = True,
) -> list[ParsedTLE]:
    """
    Fetch + parse a single Celestrak group, transparently using/populating the
    local TLE cache. If the network fetch fails, falls back to a stale cached
    copy (if any) so the pipeline degrades gracefully instead of hard-failing.
    """
    cache = cache or TLECache()
    raw_text: Optional[str] = None

    if use_cache and not force_refresh:
        raw_text = cache.get(group)
        if raw_text is not None:
            logger.debug(f"[tle_fetcher] cache hit for group {group!r}")

    if raw_text is None:
        try:
            raw_text = fetch_group_raw(group)
            if use_cache:
                cache.set(group, raw_text)
            logger.info(f"[tle_fetcher] fetched {group!r} from Celestrak ({len(raw_text.splitlines())} lines)")
        except TLENotModified as exc:
            stale = cache.get(group, ignore_ttl=True)
            if stale is not None:
                logger.info(f"[tle_fetcher] {group!r} unchanged upstream, reusing cache: {exc}")
                raw_text = stale
                cache.set(group, raw_text)  # refresh fetched_at so TTL logic doesn't re-hit the throttle
            else:
                raise
        except TLEFetchError as exc:
            if fallback_to_stale_cache:
                stale = cache.get(group, ignore_ttl=True)
                if stale is not None:
                    logger.warning(f"[tle_fetcher] network fetch failed for {group!r}, using stale cache: {exc}")
                    raw_text = stale
                else:
                    raise
            else:
                raise

    return parse_tle_file(raw_text, source=TLESource.CELESTRAK, skip_invalid=True)


def fetch_groups(groups: list[str], cache: Optional[TLECache] = None, **kwargs) -> list[ParsedTLE]:
    """Fetch multiple groups and merge, de-duplicating by NORAD ID (first occurrence wins)."""
    cache = cache or TLECache()
    seen: dict[int, ParsedTLE] = {}
    for group in groups:
        try:
            for parsed in fetch_group(group, cache=cache, **kwargs):
                seen.setdefault(parsed.norad_id, parsed)
        except TLEFetchError as exc:
            logger.error(f"[tle_fetcher] skipping group {group!r}: {exc}")
    return list(seen.values())


def filter_leo(parsed_tles: list[ParsedTLE], max_apogee_altitude_km: float = 2000.0) -> list[ParsedTLE]:
    """Keep only objects whose apogee altitude stays below the LEO threshold."""
    kept = []
    for tle in parsed_tles:
        try:
            if tle.apogee_altitude_km() <= max_apogee_altitude_km:
                kept.append(tle)
        except (ValueError, ZeroDivisionError):
            continue  # malformed mean motion; drop rather than crash the batch
    return kept


def build_default_dataset(
    cache: Optional[TLECache] = None,
    target_count: int = 800,
    random_seed: int = 42,
) -> list[ParsedTLE]:
    """
    Assemble the working LEO dataset (mix of payloads, debris, rocket bodies)
    from the curated CELESTRAK_GROUPS, capped at `target_count` objects to stay
    within the 500-1000 object propagation target.

    Objects are shuffled (with a fixed seed, for reproducible test runs) before
    capping rather than simply truncated in fetch order: `fetch_groups` returns
    objects group-by-group, so a plain `[:target_count]` slice would silently
    let whichever group happens to fetch first (or fail -- e.g. Celestrak's
    "active" group is large and easily throttled) dominate or starve the final
    mix. A shuffle keeps the capped sample representative of whatever mix of
    payloads/debris actually came back, instead of being an accident of fetch
    order/availability.
    """
    cache = cache or TLECache()
    all_objects = fetch_groups(list(CELESTRAK_GROUPS.values()), cache=cache)
    leo_objects = filter_leo(all_objects)

    random.Random(random_seed).shuffle(leo_objects)

    logger.info(
        f"[tle_fetcher] assembled dataset: {len(all_objects)} fetched -> "
        f"{len(leo_objects)} LEO -> capped at {min(len(leo_objects), target_count)}"
    )
    return leo_objects[:target_count]
