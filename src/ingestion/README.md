# AI-1: Ingestion Module — Owner: Anas

## Responsibility
- Fetch TLE data from Celestrak (active satellites, debris, rocket bodies)
- Parse and validate TLE lines
- Cache TLEs locally in `data/tle_cache/`
- Provide clean TLE objects to the propagation module

## Key Files
- `tle_fetcher.py` — HTTP client to pull TLEs from Celestrak
- `tle_parser.py` — Parse two-line element sets into structured objects
- `tle_cache.py` — Local file-based caching with TTL
- `models.py` — TLE data models (Pydantic)

## Output Contract
Provides parsed TLE objects to `src/propagation/` for SGP4 propagation.
