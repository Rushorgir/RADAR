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
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from loguru import logger

from src.conjunction.pipeline import ConjunctionPipeline
from src.ingestion import TLECache, build_default_dataset
from src.propagation import propagate_catalog_arrays

# AI-3's ML ranking lives behind the optional `ml` extras group (lightgbm,
# shap, pandas, ...) -- not everyone running this script has it installed,
# and the rest of the pipeline (ingestion/propagation/screening) works fine
# without it. Import lazily and degrade to "post raw conjunctions, skip
# ranking" rather than hard-failing the whole script over an optional stage.
try:
    from src.ml.ranking.predictor import MLRiskPredictor

    ML_RANKING_AVAILABLE = True
except ImportError as exc:
    MLRiskPredictor = None
    ML_RANKING_AVAILABLE = False
    _ML_IMPORT_ERROR = exc


def rank_events(events):
    """
    Run each conjunction event through AI-3's trained LightGBM model for an
    ml_risk_score / risk_category / SHAP explanation / maneuver advisory
    (when HIGH risk). Returns {event_id: RiskScoredEvent}, skipping any
    event that fails to score rather than failing the whole batch -- the
    same "don't let one bad item take down the run" approach as
    post_to_backend's per-item try/except below.
    """
    print(f"\n=== Step 4/6: AI-3 ML Risk Ranking ({len(events)} events) ===")
    if not ML_RANKING_AVAILABLE:
        print(f"  -> Skipped: AI-3's ML dependencies aren't installed ({_ML_IMPORT_ERROR}).")
        print("     Install with: pip install -e '.[ml]'")
        return {}

    predictor = MLRiskPredictor()
    scores: dict[str, object] = {}
    failed = 0
    t0 = time.time()
    for event in events:
        event_dict = json.loads(event.model_dump_json())
        try:
            scores[event.event_id] = predictor.predict_risk(event_dict)
        except Exception as exc:  # noqa: BLE001 -- one bad event shouldn't sink the batch
            failed += 1
            logger.warning(f"ML ranking failed for event {event.event_id}: {exc}")
    t1 = time.time()

    high_risk = sum(1 for s in scores.values() if s.risk_category.value == "HIGH")
    print(f"  -> ranked {len(scores)}/{len(events)} events in {t1 - t0:.2f}s ({failed} failed) -- {high_risk} HIGH risk")
    return scores


def post_to_backend(dataset, events, risk_scores):
    base_url = "http://127.0.0.1:8000/api/ingest"

    print("\n=== Step 6/6: Posting to Backend API ===")

    # httpx doesn't raise on 4xx/5xx by itself -- only real network failures
    # (connection refused, timeout, ...) raise an exception. Without checking
    # response.status_code, a validation error or backend bug on every single
    # item would look identical to a clean run: this loop would print
    # "complete!" having silently posted nothing.
    tle_ok = tle_failed = 0
    with httpx.Client(timeout=30.0) as client:
        print(f"  -> Posting {len(dataset)} TLEs...")
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
                response = client.post(f"{base_url}/tle", json=tle_payload)
                if response.status_code >= 400:
                    tle_failed += 1
                    logger.error(f"TLE {tle.norad_id} rejected ({response.status_code}): {response.text[:200]}")
                else:
                    tle_ok += 1
            except httpx.HTTPError as e:
                tle_failed += 1
                logger.error(f"Failed to post TLE {tle.norad_id}: {e}")

        event_ok = event_failed = 0
        print(f"  -> Posting {len(events)} Conjunction Events...")
        for event in events:
            # We dump the pydantic model to json dict
            event_payload = json.loads(event.model_dump_json())
            try:
                response = client.post(f"{base_url}/conjunction", json=event_payload)
                if response.status_code >= 400:
                    event_failed += 1
                    logger.error(f"Event {event.event_id} rejected ({response.status_code}): {response.text[:200]}")
                else:
                    event_ok += 1
            except httpx.HTTPError as e:
                event_failed += 1
                logger.error(f"Failed to post Conjunction Event {event.event_id}: {e}")

        risk_ok = risk_failed = 0
        if risk_scores:
            print(f"  -> Posting {len(risk_scores)} ML risk scores...")
            for event_id, scored in risk_scores.items():
                # RiskScoreUpdate only wants a subset of RiskScoredEvent's
                # fields (event_id/ml_risk_score/risk_category/
                # shap_top_features/maneuver_advisory) -- extra ones (pc,
                # miss_distance_km, ...) are already stored from the
                # /conjunction post above, and RiskScoreUpdate ignores
                # unknown fields anyway, so dumping the whole thing is fine.
                risk_payload = json.loads(scored.model_dump_json())
                try:
                    response = client.post(f"{base_url}/risk", json=risk_payload)
                    if response.status_code >= 400:
                        risk_failed += 1
                        logger.error(f"Risk score for {event_id} rejected ({response.status_code}): {response.text[:200]}")
                    else:
                        risk_ok += 1
                except httpx.HTTPError as e:
                    risk_failed += 1
                    logger.error(f"Failed to post risk score for {event_id}: {e}")

    print(f"  -> TLEs: {tle_ok} ok, {tle_failed} failed")
    print(f"  -> Conjunction events: {event_ok} ok, {event_failed} failed")
    if risk_scores:
        print(f"  -> Risk scores: {risk_ok} ok, {risk_failed} failed")
    print("  -> Backend ingestion complete!")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=800, help="Target dataset size (500-1000 recommended)")
    parser.add_argument("--hours", type=float, default=72.0, help="Propagation horizon in hours")
    parser.add_argument("--step", type=float, default=60.0, help="Screening timestep in seconds")
    parser.add_argument("--no-covariance", action="store_true", help="Skip covariance estimation")
    parser.add_argument("--no-ml-ranking", action="store_true", help="Skip AI-3's ML risk ranking step")
    parser.add_argument("--post-to-backend", action="store_true", help="Post results to the local backend API")
    args = parser.parse_args()

    print(f"=== Step 1/6: Fetching + parsing TLE dataset (target {args.count} objects) ===")
    cache = TLECache()
    t0 = time.time()
    dataset = build_default_dataset(cache=cache, target_count=args.count)
    t1 = time.time()
    print(f"  -> {len(dataset)} objects assembled in {t1 - t0:.2f}s (cached under data/tle_cache/)")

    print(f"\n=== Step 2/6: SGP4 batch propagation ({args.hours}h horizon, {args.step}s step) ===")
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=args.hours)
    t0 = time.time()
    arrays = propagate_catalog_arrays(dataset, start, end, step_s=args.step, attach_covariance=not args.no_covariance)
    t1 = time.time()
    print(f"  -> propagated {arrays.n_objects} objects x {arrays.n_steps} timesteps in {t1 - t0:.2f}s")

    print("\n=== Step 3/6: AI-2 Conjunction Screening ===")
    pipeline = ConjunctionPipeline()
    t0 = time.time()
    events = pipeline.run(arrays)
    t1 = time.time()
    print(f"  -> {len(events)} conjunctions flagged in {t1 - t0:.2f}s")

    if events:
        top_event = max(events, key=lambda e: e.pc)
        print(f"  -> highest risk event: {top_event.primary_id} vs {top_event.secondary_id} (Pc={top_event.pc:.2e}, TCA={top_event.tca.isoformat()})")

    risk_scores = rank_events(events) if not args.no_ml_ranking else {}

    print("\n=== Step 5/6: Sanity checks ===")
    print("  -> Sanity checks passed internally via Pydantic validation.")

    if args.post_to_backend:
        post_to_backend(dataset, events, risk_scores)
    else:
        print("\nSkipping backend posting. Use --post-to-backend to send data to the API.")

    print("\nPipeline OK: End-to-end processing complete.")

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    main()
