"""
Numpy-native batch propagation: the fast path for catalog-scale screening.

Owner: Anas (AI-1: Orbital Mechanics Lead)

`batch_propagator.propagate_catalog` returns a fully validated Pydantic object
graph (one `PropagatedState` per object per timestep) matching the AI-1 -> AI-2
interface contract exactly. That's the right shape for small runs, tests, and
for handing a specific flagged conjunction's state to another module -- but at
the catalog's target scale (500-1000 objects x ~4,320 timesteps for a 72h/60s
grid = 2-4 million individual states) materializing every single state as a
validated Pydantic object is itself a real, measured cost: profiling this
module's own dataset (800 objects, 72h/60s) showed the actual physics --
SGP4 propagation, frame rotation, covariance estimation, all fully vectorized
with numpy -- finishing in well under 10 seconds, while going on to build ~3.46M
individual PropagatedState objects and retaining all of them in memory added
well over a minute on top, growing further as GC pressure increases with more
retained objects.

AI-2's own screening design (coarse altitude-band filter, then a k-d tree over
per-timestep positions) operates on numpy arrays directly anyway -- it doesn't
need 3.46M individual Python objects, it needs `positions[:, t, :]` for a
cheap `cKDTree` query. This module provides exactly that shape, with
`to_propagated_state()` as an on-demand, contract-compliant escape hatch for
the (comparatively rare) case where a specific object/timestep's full
PropagatedState is actually needed -- e.g., packaging a flagged conjunction
event for the ConjunctionEvent output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
from loguru import logger

from src.ingestion.models import ParsedTLE
from src.propagation.covariance import estimate_covariance_6x6_batch
from src.propagation.models import SGP4ErrorCode
from src.propagation.sgp4_engine import SGP4Propagator, build_epoch_grid, build_jd_fr_grid
from src.shared.frames.transforms import apply_rotation_batch, teme_to_eci_rotation_matrices
from src.shared.interfaces.contracts import ObjectType, PropagatedState


@dataclass
class CatalogPropagationArrays:
    """
    Raw-array batch propagation result. Row order matches `object_ids`; column
    order matches `epochs`.

    positions_eci_km / velocities_eci_km_s: (n_objects, n_steps, 3)
    covariances_eci: (n_objects, n_steps, 6, 6), or None if not requested
    ok_mask: (n_objects, n_steps) bool -- False where SGP4 failed at that step
             (e.g. decayed object); positions/velocities/covariances are 0 there.
    """

    object_ids: list[str]
    object_names: list[str]
    object_types: list[ObjectType]
    tle_epochs: list[datetime]
    epochs: list[datetime]
    positions_eci_km: np.ndarray
    velocities_eci_km_s: np.ndarray
    covariances_eci: Optional[np.ndarray]
    ok_mask: np.ndarray
    error_codes: np.ndarray  # (n_objects, n_steps) int, 0 where ok

    @property
    def n_objects(self) -> int:
        return len(self.object_ids)

    @property
    def n_steps(self) -> int:
        return len(self.epochs)

    def positions_at(self, step_index: int) -> np.ndarray:
        """All objects' ECI positions at one timestep, shape (n_objects, 3) -- e.g. for a k-d tree query."""
        return self.positions_eci_km[:, step_index, :]

    def object_index(self, object_id: str) -> int:
        return self.object_ids.index(object_id)

    def to_propagated_state(self, object_index: int, step_index: int) -> PropagatedState:
        """On-demand conversion to a single contract-compliant PropagatedState."""
        if not self.ok_mask[object_index, step_index]:
            raise ValueError(
                f"No valid state for object {self.object_ids[object_index]!r} at step {step_index} "
                f"(SGP4 error: {SGP4ErrorCode(int(self.error_codes[object_index, step_index])).description})"
            )
        covariance = None
        if self.covariances_eci is not None:
            covariance = self.covariances_eci[object_index, step_index].tolist()
        return PropagatedState(
            object_id=self.object_ids[object_index],
            epoch=self.epochs[step_index],
            position_eci_km=self.positions_eci_km[object_index, step_index].tolist(),
            velocity_eci_km_s=self.velocities_eci_km_s[object_index, step_index].tolist(),
            covariance_6x6=covariance,
            hard_body_radius_km=0.005,
            cross_section_area_m2=1.0,
            object_type=self.object_types[object_index],
            object_name=self.object_names[object_index] or None,
        )


def propagate_catalog_arrays(
    parsed_tles: list[ParsedTLE],
    start: datetime,
    end: datetime,
    step_s: float = 60.0,
    attach_covariance: bool = True,
) -> CatalogPropagationArrays:
    """
    Fast path: propagate the whole catalog across the shared grid [start, end]
    and return numpy arrays instead of a Pydantic object graph. See module
    docstring for why this exists alongside `batch_propagator.propagate_catalog`.
    """
    if not parsed_tles:
        raise ValueError("parsed_tles must be non-empty")

    epochs = build_epoch_grid(start, end, step_s)
    n_objects, n_steps = len(parsed_tles), len(epochs)

    jds, frs = build_jd_fr_grid(epochs)
    rotations = teme_to_eci_rotation_matrices(epochs)

    positions = np.zeros((n_objects, n_steps, 3))
    velocities = np.zeros((n_objects, n_steps, 3))
    error_codes = np.zeros((n_objects, n_steps), dtype=int)

    for row, tle in enumerate(parsed_tles):
        try:
            propagator = SGP4Propagator.from_tle(tle)
            r_teme, v_teme, errors = propagator.propagate_teme_raw_with_grid(jds, frs)
        except Exception as exc:  # noqa: BLE001 - isolate one object's crash from the whole batch
            logger.error(f"[batch_arrays] object {tle.norad_id} raised unexpectedly: {exc}")
            error_codes[row, :] = -1
            continue

        ok = errors == 0
        if np.any(ok):
            positions[row, ok], velocities[row, ok] = apply_rotation_batch(rotations[ok], r_teme[ok], v_teme[ok])
        error_codes[row] = errors

    ok_mask = error_codes == 0

    covariances = None
    if attach_covariance:
        covariances = np.zeros((n_objects, n_steps, 6, 6))

        # (n_objects, n_steps) hours-since-TLE-epoch, computed as one broadcast
        # subtraction instead of a per-object x per-timestep Python loop over
        # datetime subtraction -- at 800 objects x ~4300 timesteps that loop
        # was ~3.4M individual `(datetime - datetime).total_seconds()` calls,
        # comparable in cost to the SGP4 propagation itself.
        epoch_seconds = np.array([e.timestamp() for e in epochs])
        tle_epoch_seconds = np.array([tle.epoch.timestamp() for tle in parsed_tles])
        hours_since_epoch = (epoch_seconds[None, :] - tle_epoch_seconds[:, None]) / 3600.0

        # Group objects by type so each DEFAULT_SIGMA_MODELS variant is applied
        # in one vectorized call across every (object, timestep) pair of that
        # type, rather than one call per object.
        object_types = np.array([tle.object_type for tle in parsed_tles], dtype=object)
        for object_type in set(object_types):
            rows = np.flatnonzero(object_types == object_type)
            row_mask = np.zeros((n_objects, n_steps), dtype=bool)
            row_mask[rows, :] = True
            combined_mask = row_mask & ok_mask
            if not np.any(combined_mask):
                continue

            flat_hours = hours_since_epoch[combined_mask]
            flat_pos = positions[combined_mask]
            flat_vel = velocities[combined_mask]
            flat_cov = estimate_covariance_6x6_batch(flat_pos, flat_vel, flat_hours, object_type)
            covariances[combined_mask] = flat_cov

    n_failed_objects = int(np.sum(~np.any(ok_mask, axis=1)))
    logger.info(
        f"[batch_arrays] propagated {n_objects} objects x {n_steps} timesteps "
        f"({n_failed_objects} objects failed entirely)"
    )

    return CatalogPropagationArrays(
        object_ids=[str(tle.norad_id) for tle in parsed_tles],
        object_names=[tle.name for tle in parsed_tles],
        object_types=[tle.object_type for tle in parsed_tles],
        tle_epochs=[tle.epoch for tle in parsed_tles],
        epochs=epochs,
        positions_eci_km=positions,
        velocities_eci_km_s=velocities,
        covariances_eci=covariances,
        ok_mask=ok_mask,
        error_codes=error_codes,
    )
