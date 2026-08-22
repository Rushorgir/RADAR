"""Unit tests for src.ingestion.tle_cache (Owner: Anas)."""

from datetime import datetime, timedelta, timezone

from src.ingestion.tle_cache import TLECache


def test_set_then_get_roundtrips(tmp_path):
    cache = TLECache(cache_dir=tmp_path, ttl_seconds=3600)
    cache.set("active", "line one\nline two")
    assert cache.get("active") == "line one\nline two"


def test_missing_key_returns_none(tmp_path):
    cache = TLECache(cache_dir=tmp_path)
    assert cache.get("nonexistent") is None


def test_stale_entry_returns_none_without_ignore_ttl(tmp_path):
    cache = TLECache(cache_dir=tmp_path, ttl_seconds=1)
    old_time = datetime.now(timezone.utc) - timedelta(hours=1)
    cache.set("active", "stale data", fetched_at=old_time)

    assert cache.is_stale("active") is True
    assert cache.get("active") is None
    assert cache.get("active", ignore_ttl=True) == "stale data"


def test_fresh_entry_is_not_stale(tmp_path):
    cache = TLECache(cache_dir=tmp_path, ttl_seconds=3600)
    cache.set("active", "fresh data")
    assert cache.is_stale("active") is False
    assert cache.get("active") == "fresh data"


def test_clear_removes_both_files(tmp_path):
    cache = TLECache(cache_dir=tmp_path)
    cache.set("active", "data")
    cache.clear("active")
    assert cache.get("active", ignore_ttl=True) is None
    assert cache.fetched_at("active") is None


def test_keys_lists_cached_entries(tmp_path):
    cache = TLECache(cache_dir=tmp_path)
    cache.set("active", "a")
    cache.set("stations", "b")
    assert cache.keys() == ["active", "stations"]


def test_key_sanitization_handles_special_characters(tmp_path):
    cache = TLECache(cache_dir=tmp_path)
    cache.set("cosmos-2251-debris", "data")
    assert cache.get("cosmos-2251-debris") == "data"


def test_fetched_at_reads_back_meta(tmp_path):
    cache = TLECache(cache_dir=tmp_path)
    before = datetime.now(timezone.utc)
    cache.set("active", "data")
    after = datetime.now(timezone.utc)

    fetched = cache.fetched_at("active")
    assert fetched is not None
    assert before - timedelta(seconds=1) <= fetched <= after + timedelta(seconds=1)
