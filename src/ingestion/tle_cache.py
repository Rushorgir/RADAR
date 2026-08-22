"""
Local file-based TLE cache with TTL.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Avoids hammering Celestrak on every run: raw TLE text for a given cache key
(typically a Celestrak group name, e.g. "active") is written to
`data/tle_cache/<key>.tle` alongside a `<key>.meta.json` sidecar recording
when it was fetched. `get()` returns cached text only while it's within the
configured TTL; otherwise callers should re-fetch and `set()` again.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "tle_cache"
DEFAULT_TTL_SECONDS = 6 * 3600  # 6 hours: Celestrak updates most catalogs a few times/day

_SAFE_KEY_RE = re.compile(r"[^A-Za-z0-9_.\-]+")


def _sanitize_key(key: str) -> str:
    safe = _SAFE_KEY_RE.sub("_", key.strip())
    if not safe:
        raise ValueError(f"Cache key sanitizes to empty string: {key!r}")
    return safe


class TLECache:
    """File-based cache mapping a string key -> raw TLE text, with TTL expiry."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, key: str) -> tuple[Path, Path]:
        safe = _sanitize_key(key)
        return self.cache_dir / f"{safe}.tle", self.cache_dir / f"{safe}.meta.json"

    def fetched_at(self, key: str) -> Optional[datetime]:
        _, meta_path = self._paths(key)
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return datetime.fromisoformat(meta["fetched_at"])
        except (KeyError, ValueError, json.JSONDecodeError):
            return None

    def is_stale(self, key: str) -> bool:
        fetched_at = self.fetched_at(key)
        if fetched_at is None:
            return True
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age > self.ttl_seconds

    def get(self, key: str, ignore_ttl: bool = False) -> Optional[str]:
        """Return cached raw TLE text for `key`, or None if missing/stale."""
        data_path, _ = self._paths(key)
        if not data_path.exists():
            return None
        if not ignore_ttl and self.is_stale(key):
            return None
        return data_path.read_text(encoding="utf-8")

    def set(self, key: str, raw_text: str, fetched_at: Optional[datetime] = None) -> None:
        data_path, meta_path = self._paths(key)
        data_path.write_text(raw_text, encoding="utf-8")
        meta = {
            "key": key,
            "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(),
            "size_bytes": len(raw_text.encode("utf-8")),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def clear(self, key: str) -> None:
        data_path, meta_path = self._paths(key)
        data_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)

    def keys(self) -> list[str]:
        return sorted(p.stem for p in self.cache_dir.glob("*.tle"))
