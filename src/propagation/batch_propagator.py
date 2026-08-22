"""
Batch orchestrator for multi-object SGP4 propagation.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Drives src/propagation/sgp4_engine.py across an entire catalog (target: 500-1000
tracked LEO objects, per src/propagation/README.md) over a shared timestep grid,
attaches an estimated covariance to every state (src/propagation/covariance.py),
and hands back a BatchPropagationResult ready for AI-2's conjunction screening.

Performance note: the naive approach -- propagate each object, then call the
TEME->ECI astropy frame transform once per object -- pays astropy's per-call
precession/nutation computation cost redundantly for every object even though
every object shares the exact same timestep grid (measured: ~800 objects x
4321 steps took tens of minutes this way). Instead, we compute the TEME->ECI
rotation matrix ONCE per timestep (src/shared/frames/transforms.teme_to_eci_rotation_matrices)
and apply it to each object's raw TEME output with plain numpy, which turns an
O(n_objects) astropy cost into O(1) -- reducing the same workload to seconds.

Threads (not multiprocessing) are used for the per-object SGP4 propagation
step: `sgp4_array` is numeric/vectorized and releases the GIL for its bulk of
the work, so threads give a real speedup without multiprocessing's pickling
overhead for hundreds of small TLE objects.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Callable, Optional

import numpy as np
from loguru import logger

from src.ingestion.models import ParsedTLE
from src.propagation.covariance import estimate_covariance_6x6, is_positive_definite
from src.propagation.models import BatchPropagationResult, PropagationError, SGP4ErrorCode, TrajectoryResult
from src.propagation.sgp4_engine import SGP4Propagator, build_jd_fr_grid
from src.shared.frames.transforms import StateVector, apply_rotation_batch, teme_to_eci_rotation_matrices
from src.shared.interfaces.contracts import PropagatedState


def _build_epoch_grid(start: datetime, end: datetime, step_s: float) -> list[datetime]:
    if end < start:
        raise ValueError("end must be >= start")
    if step_s <= 0:
        raise ValueError("step_s must be positive")
    n_steps = int((end - start).total_seconds() // step_s) + 1
    return [start + timedelta(seconds=i * step_s) for i in range(n_steps)]


def _propagate_one_raw(parsed_tle: ParsedTLE, jds: np.ndarray, frs: np.ndarray):
    """
    SGP4-only (still TEME, no frame conversion) propagation for one object,
    against a (jd, fr) grid precomputed once for the whole catalog (see
    `propagate_catalog`) rather than rebuilt per object.
    """
    propagator = SGP4Propagator.from_tle(parsed_tle)
    r_teme, v_teme, errors = propagator.propagate_teme_raw_with_grid(jds, frs)
    return parsed_tle, r_teme, v_teme, errors


def _build_trajectory(
    parsed_tle: ParsedTLE,
    epochs: list[datetime],
    pos_eci: np.ndarray,
    vel_eci: np.ndarray,
    errors: np.ndarray,
    attach_covariance: bool,
) -> TrajectoryResult:
    object_id = str(parsed_tle.norad_id)
    ok_mask = errors == 0
    result = TrajectoryResult(object_id=object_id, object_name=parsed_tle.name, object_type=parsed_tle.object_type)

    for i, (epoch, ok) in enumerate(zip(epochs, ok_mask)):
        if not ok:
            result.errors.append(
                PropagationError(
                    object_id=object_id,
                    epoch=epoch,
                    error_code=SGP4ErrorCode(int(errors[i])),
                    message=SGP4ErrorCode(int(errors[i])).description,
                )
            )
            continue

        covariance = None
        if attach_covariance:
            hours_since_epoch = (epoch - parsed_tle.epoch).total_seconds() / 3600.0
            sv = StateVector.from_lists(pos_eci[i].tolist(), vel_eci[i].tolist())
            covariance = estimate_covariance_6x6(sv, hours_since_epoch, parsed_tle.object_type).tolist()

        result.states.append(
            PropagatedState(
                object_id=object_id,
                epoch=epoch,
                position_eci_km=pos_eci[i].tolist(),
                velocity_eci_km_s=vel_eci[i].tolist(),
                covariance_6x6=covariance,
                hard_body_radius_km=0.005,
                cross_section_area_m2=1.0,
                object_type=parsed_tle.object_type,
                object_name=parsed_tle.name or None,
            )
        )

    return result


def propagate_catalog(
    parsed_tles: list[ParsedTLE],
    start: datetime,
    end: datetime,
    step_s: float = 60.0,
    attach_covariance: bool = True,
    max_workers: int = 8,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> BatchPropagationResult:
    """
    Propagate every object in `parsed_tles` across the shared grid [start, end]
    at `step_s` resolution. Objects that fail entirely (e.g. fully decayed)
    still appear in the result with an empty `states` list and populated
    `errors`, so downstream consumers can distinguish "no conjunctions found"
    from "propagation failed".

    `progress_callback(done, total)` is invoked after each object's raw SGP4
    propagation finishes, if given.
    """
    if not parsed_tles:
        return BatchPropagationResult(epochs=[], trajectories={})

    epochs = _build_epoch_grid(start, end, step_s)
    total = len(parsed_tles)

    # Computed ONCE and shared by every object below (see build_jd_fr_grid /
    # teme_to_eci_rotation_matrices docstrings for why this matters at scale).
    jds, frs = build_jd_fr_grid(epochs)
    rotations = teme_to_eci_rotation_matrices(epochs)

    # Step 1: cheap, parallelizable per-object SGP4 propagation (still TEME).
    raw_results = []
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_propagate_one_raw, tle, jds, frs): tle for tle in parsed_tles}
        for future in as_completed(futures):
            tle = futures[future]
            try:
                raw_results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - isolate one object's crash from the whole batch
                logger.error(f"[batch_propagator] object {tle.norad_id} raised unexpectedly during SGP4: {exc}")
                raw_results.append((tle, np.zeros((len(epochs), 3)), np.zeros((len(epochs), 3)), np.full(len(epochs), -1)))
            done += 1
            if progress_callback:
                progress_callback(done, total)

    # Step 2: apply the precomputed rotation to each object (pure numpy, cheap).
    trajectories: dict[str, TrajectoryResult] = {}
    for parsed_tle, r_teme, v_teme, errors in raw_results:
        ok_mask = errors == 0
        pos_eci = np.zeros_like(r_teme)
        vel_eci = np.zeros_like(v_teme)
        if np.any(ok_mask):
            pos_eci[ok_mask], vel_eci[ok_mask] = apply_rotation_batch(rotations[ok_mask], r_teme[ok_mask], v_teme[ok_mask])

        trajectory = _build_trajectory(parsed_tle, epochs, pos_eci, vel_eci, errors, attach_covariance)
        trajectories[trajectory.object_id] = trajectory

    canonical_epochs: list[datetime] = []
    for traj in trajectories.values():
        if len(traj.states) > len(canonical_epochs):
            canonical_epochs = [s.epoch for s in traj.states]

    n_failed = sum(1 for t in trajectories.values() if not t.ok)
    logger.info(f"[batch_propagator] propagated {total} objects over {len(canonical_epochs)} timesteps; {n_failed} had errors")

    return BatchPropagationResult(epochs=canonical_epochs, trajectories=trajectories)


def summarize_covariance_health(result: BatchPropagationResult) -> dict[str, int]:
    """Count how many propagated states have a positive-definite covariance vs. not, for sanity-checking a batch run."""
    healthy, degenerate, missing = 0, 0, 0
    for traj in result.trajectories.values():
        for state in traj.states:
            if state.covariance_6x6 is None:
                missing += 1
            elif is_positive_definite(np.array(state.covariance_6x6)):
                healthy += 1
            else:
                degenerate += 1
    return {"healthy": healthy, "degenerate": degenerate, "missing": missing}
