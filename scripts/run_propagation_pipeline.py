#!/usr/bin/env python
"""
End-to-end demo of the AI-1 (Anas) pipeline: TLE ingestion -> SGP4 propagation
-> coordinate transforms -> batch state vectors ready for AI-2's conjunction
screening.

Usage:
    python scripts/run_propagation_pipeline.py [--count 800] [--hours 72] [--step 60]

This is a CLI utility (owner: All, per TEAM_DIRECTORY_GUIDE.md `scripts/`), not
a unit test -- it's meant to be run by hand to sanity-check and demo the whole
AI-1 pipeline against live Celestrak data, and to (re)populate data/tle_cache/
with the working dataset the rest of the team's modules can build against.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from loguru import logger

from src.ingestion import TLECache, build_default_dataset
from src.propagation import is_positive_definite, propagate_catalog_arrays


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=800, help="Target dataset size (500-1000 recommended)")
    parser.add_argument("--hours", type=float, default=72.0, help="Propagation horizon in hours")
    parser.add_argument("--step", type=float, default=60.0, help="Screening timestep in seconds")
    parser.add_argument("--no-covariance", action="store_true", help="Skip covariance estimation")
    args = parser.parse_args()

    print(f"=== Step 1/3: Fetching + parsing TLE dataset (target {args.count} objects) ===")
    cache = TLECache()
    t0 = time.time()
    dataset = build_default_dataset(cache=cache, target_count=args.count)
    t1 = time.time()
    print(f"  -> {len(dataset)} objects assembled in {t1 - t0:.2f}s (cached under data/tle_cache/)")

    by_type: dict[str, int] = {}
    for tle in dataset:
        by_type[tle.object_type.value] = by_type.get(tle.object_type.value, 0) + 1
    print(f"  -> composition: {by_type}")

    print(f"\n=== Step 2/3: SGP4 batch propagation ({args.hours}h horizon, {args.step}s step) ===")
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=args.hours)
    t0 = time.time()
    arrays = propagate_catalog_arrays(dataset, start, end, step_s=args.step, attach_covariance=not args.no_covariance)
    t1 = time.time()
    print(f"  -> propagated {arrays.n_objects} objects x {arrays.n_steps} timesteps in {t1 - t0:.2f}s")
    n_failed = int((~arrays.ok_mask.any(axis=1)).sum())
    if n_failed:
        print(f"  -> {n_failed} objects had propagation errors")

    print("\n=== Step 3/3: Sanity checks ===")
    if not args.no_covariance:
        # Spot-check a sample of states rather than every one of the (possibly
        # millions of) object/timestep pairs -- this is a sanity check, not a
        # full audit, and a per-state Python loop over the whole catalog would
        # reintroduce exactly the kind of overhead this pipeline was fixed to avoid.
        rng = np.random.default_rng(0)
        ok_indices = np.argwhere(arrays.ok_mask)
        sample_size = min(500, len(ok_indices))
        sample_idx = ok_indices[rng.choice(len(ok_indices), size=sample_size, replace=False)]
        healthy = sum(is_positive_definite(arrays.covariances_eci[i, j]) for i, j in sample_idx)
        print(f"  -> covariance health (sample of {sample_size}): {healthy}/{sample_size} positive-definite")

    sample = arrays.to_propagated_state(0, 0)
    print(f"  -> sample state (object {sample.object_id}, {arrays.object_names[0]!r}):")
    print(f"     epoch={sample.epoch.isoformat()}")
    print(f"     position_eci_km={[round(x, 3) for x in sample.position_eci_km]}")
    print(f"     velocity_eci_km_s={[round(x, 5) for x in sample.velocity_eci_km_s]}")

    print("\nPipeline OK: ingestion -> SGP4 propagation -> ECI state vectors ready for AI-2.")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    main()
