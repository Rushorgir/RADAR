"""
SGP4/SDP4 orbit propagation engine.

Owner: Anas (AI-1: Orbital Mechanics Lead)

Wraps the `sgp4` library's `Satrec` (SGP4 automatically switches to the SDP4
deep-space algorithm internally for periods >= 225 minutes, per Vallado's
reference implementation) to turn a single `ParsedTLE` into position/velocity
state vectors at arbitrary epochs, in the ECI/J2000 frame expected by the
AI-1 -> AI-2 interface contract (src/shared/interfaces/contracts.PropagatedState).

Raw SGP4 output is in the TEME frame of epoch; every state produced here is
rotated TEME -> ECI via src/shared/frames/transforms.py before being returned,
so nothing downstream ever has to think about TEME.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4.api import Satrec, WGS84, jday

from src.ingestion.models import ParsedTLE
from src.propagation.models import PropagationError, SGP4ErrorCode, TrajectoryResult
from src.shared.frames.transforms import StateVector, teme_to_eci, teme_to_eci_batch
from src.shared.interfaces.contracts import PropagatedState


class SGP4PropagationFailure(RuntimeError):
    """Raised when SGP4 fails at a specific epoch (see .error_code)."""

    def __init__(self, error_code: SGP4ErrorCode, object_id: str, epoch: datetime):
        self.error_code = error_code
        self.object_id = object_id
        self.epoch = epoch
        super().__init__(f"SGP4 failed for object {object_id} at {epoch.isoformat()}: {error_code.description}")


def _to_jday(epoch: datetime) -> tuple[float, float]:
    if epoch.tzinfo is not None:
        epoch = epoch.astimezone(timezone.utc).replace(tzinfo=None)
    return jday(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute, epoch.second + epoch.microsecond * 1e-6)


def build_jd_fr_grid(epochs: list[datetime]) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert a list of epochs into the (jd, fr) arrays `Satrec.sgp4_array` expects.

    Pulled out as its own function so batch propagation of many objects sharing
    one timestep grid (src/propagation/batch_propagator.py) can compute this
    ONCE and reuse it for every object, instead of redoing a Python-level
    per-epoch conversion loop per object -- at 800 objects x ~4300 timesteps
    that redundant loop alone (~3.4M Python calls under the GIL) dominated
    runtime far more than the actual SGP4/frame-transform math.
    """
    n = len(epochs)
    jds = np.empty(n)
    frs = np.empty(n)
    for i, epoch in enumerate(epochs):
        jds[i], frs[i] = _to_jday(epoch)
    return jds, frs


class SGP4Propagator:
    """A single object's SGP4 propagator, built from a `ParsedTLE`."""

    def __init__(self, parsed_tle: ParsedTLE):
        self.parsed_tle = parsed_tle
        self._satrec = Satrec.twoline2rv(parsed_tle.line1, parsed_tle.line2, WGS84)

    @property
    def object_id(self) -> str:
        return str(self.parsed_tle.norad_id)

    def propagate_at(self, epoch: datetime) -> PropagatedState:
        """Propagate to a single epoch. Raises SGP4PropagationFailure on SGP4 error."""
        jd, fr = _to_jday(epoch)
        error, r_teme, v_teme = self._satrec.sgp4(jd, fr)
        if error != 0:
            raise SGP4PropagationFailure(SGP4ErrorCode(error), self.object_id, epoch)

        teme_state = StateVector.from_lists(list(r_teme), list(v_teme))
        eci_state = teme_to_eci(teme_state, epoch)

        return PropagatedState(
            object_id=self.object_id,
            epoch=epoch,
            position_eci_km=eci_state.position_km.tolist(),
            velocity_eci_km_s=eci_state.velocity_km_s.tolist(),
            covariance_6x6=None,
            hard_body_radius_km=0.005,
            cross_section_area_m2=1.0,
            object_type=self.parsed_tle.object_type,
            object_name=self.parsed_tle.name or None,
        )

    def propagate_grid_teme_raw(
        self, start: datetime, end: datetime, step_s: float
    ) -> tuple[list[datetime], np.ndarray, np.ndarray, np.ndarray]:
        """
        Raw (still-TEME) vectorized propagation across a timestep grid, with no
        frame conversion applied. Returns (epochs, r_teme (N,3), v_teme (N,3),
        error_codes (N,)).

        This is split out from `propagate_grid` so that batch propagation of many
        objects (src/propagation/batch_propagator.py) can collect every object's
        raw TEME states and perform a single vectorized TEME->ECI rotation across
        the *entire catalog* at once, instead of paying astropy's fixed per-call
        overhead once per object -- which matters a lot at the 500-1000 object
        scale this engine targets (turns O(n_objects) frame-transform calls into
        O(1)).
        """
        if end < start:
            raise ValueError("end must be >= start")
        if step_s <= 0:
            raise ValueError("step_s must be positive")

        n_steps = int((end - start).total_seconds() // step_s) + 1
        epochs = [start + timedelta(seconds=i * step_s) for i in range(n_steps)]
        jds, frs = build_jd_fr_grid(epochs)

        errors, r_teme, v_teme = self._satrec.sgp4_array(jds, frs)
        return epochs, r_teme, v_teme, errors

    def propagate_teme_raw_with_grid(self, jds: np.ndarray, frs: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Like `propagate_grid_teme_raw`, but takes a precomputed (jd, fr) grid
        (see `build_jd_fr_grid`) instead of building one from a date range --
        the fast path batch propagation uses when many objects share one grid.
        """
        errors, r_teme, v_teme = self._satrec.sgp4_array(jds, frs)
        return r_teme, v_teme, errors

    def propagate_grid(self, start: datetime, end: datetime, step_s: float) -> TrajectoryResult:
        """
        Propagate a single object across a regular timestep grid [start, end]
        (inclusive of start, stepping by step_s), converting the raw TEME output
        to ECI in one vectorized batch. For propagating many objects at once,
        prefer src/propagation/batch_propagator.propagate_catalog, which shares
        a single TEME->ECI conversion across the whole catalog for much better
        throughput.
        """
        epochs, r_teme, v_teme, errors = self.propagate_grid_teme_raw(start, end, step_s)

        ok_mask = errors == 0
        result = TrajectoryResult(
            object_id=self.object_id,
            object_name=self.parsed_tle.name,
            object_type=self.parsed_tle.object_type,
        )

        if np.any(ok_mask):
            ok_epochs = [e for e, ok in zip(epochs, ok_mask) if ok]
            pos_eci, vel_eci = teme_to_eci_batch(r_teme[ok_mask], v_teme[ok_mask], ok_epochs)
            for epoch, pos, vel in zip(ok_epochs, pos_eci, vel_eci):
                result.states.append(
                    PropagatedState(
                        object_id=self.object_id,
                        epoch=epoch,
                        position_eci_km=pos.tolist(),
                        velocity_eci_km_s=vel.tolist(),
                        covariance_6x6=None,
                        hard_body_radius_km=0.005,
                        cross_section_area_m2=1.0,
                        object_type=self.parsed_tle.object_type,
                        object_name=self.parsed_tle.name or None,
                    )
                )

        for epoch, error, ok in zip(epochs, errors, ok_mask):
            if not ok:
                result.errors.append(
                    PropagationError(
                        object_id=self.object_id,
                        epoch=epoch,
                        error_code=SGP4ErrorCode(int(error)),
                        message=SGP4ErrorCode(int(error)).description,
                    )
                )

        return result

    @classmethod
    def from_tle(cls, parsed_tle: ParsedTLE) -> "SGP4Propagator":
        return cls(parsed_tle)
