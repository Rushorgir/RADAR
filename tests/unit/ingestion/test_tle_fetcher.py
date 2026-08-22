"""
Unit tests for src.ingestion.tle_fetcher (Owner: Anas).

All tests monkeypatch the network boundary (`fetch_group_raw`) so the suite
never depends on internet access or Celestrak's live throttle behavior.
"""

from __future__ import annotations

import pytest

from src.ingestion import tle_fetcher
from src.ingestion.models import TLEFetchError
from src.ingestion.tle_cache import TLECache
from src.ingestion.tle_fetcher import TLENotModified, build_default_dataset, fetch_group, fetch_groups, filter_leo
from src.ingestion.tle_parser import parse_tle_lines

ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"
ISS_BLOCK = "\n".join([ISS_NAME, ISS_LINE1, ISS_LINE2])

# A synthetic GEO-altitude object (mean motion ~1 rev/day) for LEO-filter tests.
GEO_LINE1 = "1 99999U 26001A   26233.50000000  .00000010  00000+0  00000+0 0  9994"
GEO_LINE2 = "2 99999   0.0100 100.0000 0001000 100.0000 260.0000  1.00270000123454"
GEO_BLOCK = "\n".join(["SYNTHETIC GEO", GEO_LINE1, GEO_LINE2])


class TestFetchGroup:
    def test_fetches_and_caches_on_success(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path)
        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", lambda group, **kw: ISS_BLOCK)

        result = fetch_group("stations", cache=cache)

        assert len(result) == 1
        assert result[0].norad_id == 25544
        assert cache.get("stations") == ISS_BLOCK

    def test_uses_cache_without_hitting_network(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path)
        cache.set("stations", ISS_BLOCK)

        def _boom(*a, **kw):
            raise AssertionError("network should not be called when cache is fresh")

        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", _boom)

        result = fetch_group("stations", cache=cache)
        assert len(result) == 1

    def test_not_modified_falls_back_to_cache_and_refreshes_ttl(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path, ttl_seconds=0)  # force cache to look stale
        cache.set("stations", ISS_BLOCK)

        def _not_modified(*a, **kw):
            raise TLENotModified("has not updated since your last successful download")

        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", _not_modified)

        result = fetch_group("stations", cache=cache, use_cache=True)
        assert len(result) == 1
        assert result[0].norad_id == 25544

    def test_network_failure_falls_back_to_stale_cache(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path, ttl_seconds=0)
        cache.set("stations", ISS_BLOCK)
        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", lambda *a, **kw: (_ for _ in ()).throw(TLEFetchError("down")))

        result = fetch_group("stations", cache=cache, fallback_to_stale_cache=True)
        assert len(result) == 1

    def test_network_failure_without_cache_raises(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path)
        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", lambda *a, **kw: (_ for _ in ()).throw(TLEFetchError("down")))

        with pytest.raises(TLEFetchError):
            fetch_group("stations", cache=cache)


class TestFetchGroups:
    def test_merges_and_dedupes_by_norad_id(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path)
        responses = {"stations": ISS_BLOCK, "active": ISS_BLOCK}  # overlapping ISS entry
        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", lambda group, **kw: responses[group])

        result = fetch_groups(["stations", "active"], cache=cache)
        assert len(result) == 1  # de-duplicated

    def test_one_failing_group_does_not_abort_others(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path)

        def _raw(group, **kw):
            if group == "broken":
                raise TLEFetchError("simulated failure")
            return ISS_BLOCK

        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", _raw)

        result = fetch_groups(["broken", "stations"], cache=cache)
        assert len(result) == 1


class TestFilterLeo:
    def test_keeps_leo_and_drops_geo(self):
        iss = parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)
        geo = parse_tle_lines(GEO_LINE1, GEO_LINE2, name="SYNTHETIC GEO")

        kept = filter_leo([iss, geo], max_apogee_altitude_km=2000.0)

        assert iss in kept
        assert geo not in kept


class TestBuildDefaultDataset:
    def test_caps_at_target_count_and_prefers_leo(self, tmp_path, monkeypatch):
        cache = TLECache(cache_dir=tmp_path)
        block = "\n".join([ISS_BLOCK, GEO_BLOCK])
        monkeypatch.setattr(tle_fetcher, "fetch_group_raw", lambda group, **kw: block)

        dataset = build_default_dataset(cache=cache, target_count=1)

        assert len(dataset) == 1
        assert dataset[0].norad_id == 25544  # the GEO object was filtered out before capping
