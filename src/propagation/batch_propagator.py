"""
Batch orchestrator for multi-object SGP4 propagation.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Drives src/propagation/sgp4_engine.py across an entire catalog (target: 500-1000
tracked LEO objects, per src/propagation/README.md) over a shared timestep grid,
attaches an estimated covariance to every state (src/propagation/covariance.py),
and hands back a BatchPropagationResult ready for AI-2's conjunction screening.

Performance notes (measured, not assumed -- see AI1_IMPLEMENTATION_NOTES.md for
the full story):

1. TEME->ECI frame conversion: computing astropy's TEME->GCRS rotation once per
   *object* (paying its precession/nutation/IERS-lookup cost 800 times for
   identical timestamps) instead of once per *timestep* was the single biggest
   cost in an early version of this module. Fixed by computing the rotation
   matrix once per timestep (src/shared/frames/transforms.teme_to_eci_rotation_matrices)
   and applying it to every object with plain numpy (apply_rotation_batch):
   O(n_objects) astropy calls -> O(1).

2. Julian-date conversion: each object independently rebuilding the same (jd,
   fr) array for an identical shared epoch grid, via a per-epoch Python loop,
   redundantly repeated the same ~4,300-iteration loop 800 times. Fixed by
   `build_jd_fr_grid` computing it once (see sgp4_engine.py) and passing the
   shared arrays to every object's `Satrec.sgp4_array` call.

3. Covariance estimation: calling the covariance estimator once per propagated
   *state* (~3.4M calls for an 800-object/72h/60s catalog) is dominated by
   Python/numpy call overhead, not the actual math. Fixed by
   `estimate_covariance_6x6_batch` computing an object's whole trajectory's
   covariance in one vectorized call.

4. Threading: an earlier version ran per-object SGP4 propagation in a
   ThreadPoolExecutor, on the assumption that `sgp4_array` (implemented in C)
   would release the GIL for the bulk of its work. Measured evidence says
   otherwise for this workload -- the same 800-object catalog that runs
   sequentially end-to-end in well under a minute took 5+ minutes with an
   8-worker thread pool, consistent with GIL contention between worker
   threads dominating any real parallel work. This module therefore runs
   sequentially; do not reintroduce a thread/process pool here without
   re-measuring on the actual target workload first.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import numpy as np
from loguru import logger

from src.ingestion.models import ParsedTLE
from src.propagation.covariance import estimate_covariance_6x6_batch, is_positive_definite
from src.propagation.models import BatchPropagationResult, PropagationError, SGP4ErrorCode, TrajectoryResult
from src.propagation.sgp4_engine import SGP4Propagator, build_epoch_grid, build_jd_fr_grid
from src.shared.frames.transforms import apply_rotation_batch, teme_to_eci_rotation_matrices
from src.shared.interfaces.contracts import PropagatedState


def _build_trajectory(
    parsed_tle: ParsedTLE,
    epochs: list[datetime],
    epoch_seconds: np.ndarray,
    pos_eci: np.ndarray,
    vel_eci: np.ndarray,
    errors: np.ndarray,
    attach_covariance: bool,
) -> TrajectoryResult:
    object_id = str(parsed_tle.norad_id)
    ok_mask = errors == 0
    result = TrajectoryResult(object_id=object_id, object_name=parsed_tle.name, object_type=parsed_tle.object_type)

    for i, ok in enumerate(ok_mask):
        if not ok:
            result.errors.append(
                PropagationError(
                    object_id=object_id,
                    epoch=epochs[i],
                    error_code=SGP4ErrorCode(int(errors[i])),
                    message=SGP4ErrorCode(int(errors[i])).description,
                )
            )

    covariances: Optional[np.ndarray] = None
    if attach_covariance and np.any(ok_mask):
        # One vectorized call for every OK state of this object, instead of a
        # per-state call (see estimate_covariance_6x6_batch docstring for why
        # that matters at catalog scale). `epoch_seconds` is computed once for
        # the whole shared grid by the caller, not re-derived per object via a
        # per-timestep datetime subtraction.
        hours_since_epoch = (epoch_seconds[ok_mask] - parsed_tle.epoch.timestamp()) / 3600.0
        covariances = estimate_covariance_6x6_batch(pos_eci[ok_mask], vel_eci[ok_mask], hours_since_epoch, parsed_tle.object_type)

    ok_indices = np.flatnonzero(ok_mask)
    for row, i in enumerate(ok_indices):
        covariance = covariances[row].tolist() if covariances is not None else None

        result.states.append(
            PropagatedState(
                object_id=object_id,
                epoch=epochs[i],
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
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> BatchPropagationResult:
    """
    Propagate every object in `parsed_tles` across the shared grid [start, end]
    at `step_s` resolution. Objects that fail entirely (e.g. fully decayed)
    still appear in the result with an empty `states` list and populated
    `errors`, so downstream consumers can distinguish "no conjunctions found"
    from "propagation failed".

    Runs sequentially -- see the module docstring for why threading measured
    *worse* than sequential for this workload.

    `progress_callback(done, total)` is invoked after each object finishes, if given.
    """
    if not parsed_tles:
        return BatchPropagationResult(epochs=[], trajectories={})

    epochs = build_epoch_grid(start, end, step_s)
    total = len(parsed_tles)

    # Computed ONCE and shared by every object below (see build_jd_fr_grid /
    # teme_to_eci_rotation_matrices docstrings for why this matters at scale).
    jds, frs = build_jd_fr_grid(epochs)
    rotations = teme_to_eci_rotation_matrices(epochs)
    epoch_seconds = np.array([e.timestamp() for e in epochs])

    trajectories: dict[str, TrajectoryResult] = {}
    for done, parsed_tle in enumerate(parsed_tles, start=1):
        try:
            propagator = SGP4Propagator.from_tle(parsed_tle)
            r_teme, v_teme, errors = propagator.propagate_teme_raw_with_grid(jds, frs)

            ok_mask = errors == 0
            pos_eci = np.zeros_like(r_teme)
            vel_eci = np.zeros_like(v_teme)
            if np.any(ok_mask):
                pos_eci[ok_mask], vel_eci[ok_mask] = apply_rotation_batch(rotations[ok_mask], r_teme[ok_mask], v_teme[ok_mask])

            trajectory = _build_trajectory(parsed_tle, epochs, epoch_seconds, pos_eci, vel_eci, errors, attach_covariance)
        except Exception as exc:  # noqa: BLE001 - isolate one object's crash from the whole batch
            logger.error(f"[batch_propagator] object {parsed_tle.norad_id} raised unexpectedly: {exc}")
            trajectory = TrajectoryResult(
                object_id=str(parsed_tle.norad_id), object_name=parsed_tle.name, object_type=parsed_tle.object_type
            )

        trajectories[trajectory.object_id] = trajectory
        if progress_callback:
            progress_callback(done, total)

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
