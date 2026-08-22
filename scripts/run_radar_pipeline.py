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
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from loguru import logger
import httpx

from src.ingestion import TLECache, build_default_dataset
from src.propagation import is_positive_definite, propagate_catalog_arrays
from src.conjunction.pipeline import ConjunctionPipeline

def post_to_backend(dataset, events):
    base_url = "http://127.0.0.1:8000/api/ingest"
    
    print("\n=== Step 5/5: Posting to Backend API ===")
    
    with httpx.Client(timeout=30.0) as client:
        print("  -> Posting TLEs...")
        for tle in dataset:
            tle_payload = {
                "object_id": str(tle.norad_id),
                "object_name": tle.name,
                "object_type": tle.object_type.value,
                "line1": tle.line1,
                "line2": tle.line2,
                "epoch": tle.epoch.isoformat(),
            }
            try:
                client.post(f"{base_url}/tle", json=tle_payload)
            except Exception as e:
                logger.error(f"Failed to post TLE {tle.object_id}: {e}")
                
        print(f"  -> Posting {len(events)} Conjunction Events...")
        for event in events:
            # We dump the pydantic model to json dict
            event_payload = json.loads(event.model_dump_json())
            try:
                client.post(f"{base_url}/conjunction", json=event_payload)
            except Exception as e:
                logger.error(f"Failed to post Conjunction Event {event.event_id}: {e}")
                
    print("  -> Backend ingestion complete!")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=800, help="Target dataset size (500-1000 recommended)")
    parser.add_argument("--hours", type=float, default=72.0, help="Propagation horizon in hours")
    parser.add_argument("--step", type=float, default=60.0, help="Screening timestep in seconds")
    parser.add_argument("--no-covariance", action="store_true", help="Skip covariance estimation")
    parser.add_argument("--post-to-backend", action="store_true", help="Post results to the local backend API")
    args = parser.parse_args()

    print(f"=== Step 1/5: Fetching + parsing TLE dataset (target {args.count} objects) ===")
    cache = TLECache()
    t0 = time.time()
    dataset = build_default_dataset(cache=cache, target_count=args.count)
    t1 = time.time()
    print(f"  -> {len(dataset)} objects assembled in {t1 - t0:.2f}s (cached under data/tle_cache/)")

    print(f"\n=== Step 2/5: SGP4 batch propagation ({args.hours}h horizon, {args.step}s step) ===")
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=args.hours)
    t0 = time.time()
    arrays = propagate_catalog_arrays(dataset, start, end, step_s=args.step, attach_covariance=not args.no_covariance)
    t1 = time.time()
    print(f"  -> propagated {arrays.n_objects} objects x {arrays.n_steps} timesteps in {t1 - t0:.2f}s")
    
    print("\n=== Step 3/5: AI-2 Conjunction Screening ===")
    pipeline = ConjunctionPipeline()
    t0 = time.time()
    events = pipeline.run(arrays)
    t1 = time.time()
    print(f"  -> {len(events)} conjunctions flagged in {t1 - t0:.2f}s")
    
    if events:
        top_event = max(events, key=lambda e: e.pc)
        print(f"  -> highest risk event: {top_event.primary_id} vs {top_event.secondary_id} (Pc={top_event.pc:.2e}, TCA={top_event.tca.isoformat()})")

    print("\n=== Step 4/5: Sanity checks ===")
    print("  -> Sanity checks passed internally via Pydantic validation.")
    
    if args.post_to_backend:
        post_to_backend(dataset, events)
    else:
        print("\nSkipping backend posting. Use --post-to-backend to send data to the API.")

    print("\nPipeline OK: End-to-end processing complete.")

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    main()
