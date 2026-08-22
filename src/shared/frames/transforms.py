"""
Coordinate frame transformation utilities.

Supports:  TEME <-> ECI (GCRS / J2000-equivalent) <-> ECEF (ITRS) <-> RIC/RTN

Owner: src/shared/ is jointly owned by the whole team (see TEAM_DIRECTORY_GUIDE.md).
This module is populated by AI-1 (Anas) as part of the "coordinate transforms"
deliverable. Any breaking change to public signatures must be announced to the team.

Design notes
------------
* SGP4 propagation (src/propagation/sgp4_engine.py) natively outputs state vectors in
  the **TEME** (True Equator, Mean Equinox) frame of epoch. Everything downstream
  (conjunction screening, visualization) expects a quasi-inertial J2000-like frame,
  so every propagated state must be rotated TEME -> ECI before leaving the
  propagation module (see contracts.PropagatedState: "Frame: ECI / J2000").
* Rather than hand-rolling IAU precession/nutation series (error prone and hard to
  verify independently), we delegate to astropy's built-in `TEME`, `GCRS`, and
  `ITRS` frame classes. GCRS is astropy's geocentric inertial frame and is the
  standard stand-in for "J2000 ECI" in modern libraries (differs from classical
  mean-equator-of-J2000 by only frame-bias terms, ~tens of mas -- negligible for
  SSA screening purposes). ITRS is the standard Earth-fixed (ECEF) frame.
* All positions are kilometers, all velocities are km/s, matching the rest of the
  codebase's unit convention (src/shared/constants/physical.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
from astropy import units as u
from astropy.coordinates import GCRS, ITRS, TEME, CartesianDifferential, CartesianRepresentation
from astropy.time import Time

# ── Core data type ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StateVector:
    """A Cartesian position/velocity pair in some (unspecified) reference frame."""

    position_km: np.ndarray = field(repr=True)
    velocity_km_s: np.ndarray = field(repr=True)

    def __post_init__(self) -> None:
        position = np.asarray(self.position_km, dtype=float).reshape(3)
        velocity = np.asarray(self.velocity_km_s, dtype=float).reshape(3)
        object.__setattr__(self, "position_km", position)
        object.__setattr__(self, "velocity_km_s", velocity)

    @classmethod
    def from_lists(cls, position: list[float], velocity: list[float]) -> StateVector:
        return cls(position_km=np.array(position, dtype=float), velocity_km_s=np.array(velocity, dtype=float))

    def as_tuple(self) -> tuple[list[float], list[float]]:
        return self.position_km.tolist(), self.velocity_km_s.tolist()


# ── Internal helpers ─────────────────────────────────────────────────────────────

def _to_astropy_time(epoch: datetime) -> Time:
    """Convert a (naive-or-aware) UTC datetime into an astropy Time in the UTC scale."""
    if epoch.tzinfo is not None:
        epoch = epoch.astimezone(timezone.utc).replace(tzinfo=None)
    return Time(epoch, scale="utc")


def _to_cartesian_rep(state: StateVector) -> CartesianRepresentation:
    return CartesianRepresentation(
        state.position_km * u.km,
        differentials=CartesianDifferential(state.velocity_km_s * u.km / u.s),
    )


def _from_frame(frame_obj) -> StateVector:
    cart = frame_obj.cartesian
    pos_km = cart.xyz.to_value(u.km)
    vel_km_s = cart.differentials["s"].d_xyz.to_value(u.km / u.s)
    return StateVector(position_km=pos_km, velocity_km_s=vel_km_s)


def _to_astropy_time_array(epochs) -> Time:
    """Accept a list[datetime] or an existing astropy Time and return a Time array."""
    if isinstance(epochs, Time):
        return epochs
    naive = [e.astimezone(timezone.utc).replace(tzinfo=None) if e.tzinfo else e for e in epochs]
    return Time(naive, scale="utc")


# ── TEME <-> ECI (GCRS) ──────────────────────────────────────────────────────────

def teme_to_eci(state: StateVector, epoch: datetime) -> StateVector:
    """Rotate a TEME state vector (raw SGP4 output) into the ECI/J2000 (GCRS) frame."""
    t = _to_astropy_time(epoch)
    teme = TEME(_to_cartesian_rep(state), obstime=t)
    gcrs = teme.transform_to(GCRS(obstime=t))
    return _from_frame(gcrs)


def eci_to_teme(state: StateVector, epoch: datetime) -> StateVector:
    """Inverse of :func:`teme_to_eci`."""
    t = _to_astropy_time(epoch)
    gcrs = GCRS(_to_cartesian_rep(state), obstime=t)
    teme = gcrs.transform_to(TEME(obstime=t))
    return _from_frame(teme)


# ── ECI (GCRS) <-> ECEF (ITRS) ────────────────────────────────────────────────────

def eci_to_ecef(state: StateVector, epoch: datetime) -> StateVector:
    """Rotate an ECI/J2000 (GCRS) state vector into the Earth-fixed ECEF (ITRS) frame."""
    t = _to_astropy_time(epoch)
    gcrs = GCRS(_to_cartesian_rep(state), obstime=t)
    itrs = gcrs.transform_to(ITRS(obstime=t))
    return _from_frame(itrs)


def ecef_to_eci(state: StateVector, epoch: datetime) -> StateVector:
    """Inverse of :func:`eci_to_ecef`."""
    t = _to_astropy_time(epoch)
    itrs = ITRS(_to_cartesian_rep(state), obstime=t)
    gcrs = itrs.transform_to(GCRS(obstime=t))
    return _from_frame(gcrs)


# ── Vectorized (batch) TEME -> ECI, for propagating many timesteps at once ──────

def teme_to_eci_batch(
    positions_km: np.ndarray,
    velocities_km_s: np.ndarray,
    epochs,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Vectorized TEME -> ECI (GCRS) rotation for many states at once.

    `positions_km` / `velocities_km_s`: shape (N, 3).
    `epochs`: list[datetime] or astropy Time of length N (one obstime per row --
    this is what SGP4 batch propagation over a timestep grid produces).

    Returns (positions_km, velocities_km_s) each shape (N, 3), in ECI/GCRS.
    Roughly an order of magnitude faster than calling `teme_to_eci` in a Python
    loop for large N, since astropy vectorizes the frame rotation internally.
    """
    positions_km = np.asarray(positions_km, dtype=float).reshape(-1, 3)
    velocities_km_s = np.asarray(velocities_km_s, dtype=float).reshape(-1, 3)
    t = _to_astropy_time_array(epochs)

    rep = CartesianRepresentation(
        positions_km.T * u.km,
        differentials=CartesianDifferential(velocities_km_s.T * u.km / u.s),
    )
    teme = TEME(rep, obstime=t)
    gcrs = teme.transform_to(GCRS(obstime=t))

    pos_out = gcrs.cartesian.xyz.to_value(u.km).T
    vel_out = gcrs.cartesian.differentials["s"].d_xyz.to_value(u.km / u.s).T
    return pos_out, vel_out


# ── Precomputed rotation matrices, for propagating many objects on a shared grid ─

def _teme_to_eci_rotation_matrices_exact(t: Time) -> np.ndarray:
    """Exact TEME->GCRS rotation matrix at every epoch in `t` (no decimation)."""
    n = len(t)

    basis = np.eye(3)  # columns e_x, e_y, e_z
    # Shape (3 basis vectors, 3 xyz components, n epochs)
    basis_teme = np.broadcast_to(basis[:, :, None], (3, 3, n)).astype(float)

    rep = CartesianRepresentation(
        basis_teme[:, 0, :] * u.km,
        basis_teme[:, 1, :] * u.km,
        basis_teme[:, 2, :] * u.km,
    )
    teme = TEME(rep, obstime=t)
    gcrs = teme.transform_to(GCRS(obstime=t))
    images = gcrs.cartesian.get_xyz(xyz_axis=1).to_value(u.km)  # shape (3 basis, 3 xyz, n)

    # R[i] must satisfy R[i] @ e_k = images[k, :, i] for each basis vector e_k,
    # i.e. column k of R[i] is images[k, :, i].
    return np.transpose(images, (2, 1, 0))  # -> (n, xyz_out, basis_in)


def teme_to_eci_rotation_matrices(epochs, max_spacing_s: float = 300.0) -> np.ndarray:
    """
    Precompute the TEME -> GCRS rotation matrix at each of `epochs` ONCE, so that
    propagating many objects sharing the same timestep grid (the normal case: a
    whole catalog propagated over one 72h/60s grid) only pays astropy's frame-
    transform cost O(n_timesteps) instead of O(n_objects * n_timesteps).

    Returns an array of shape (N, 3, 3), where R[i] rotates a TEME vector at
    epochs[i] into GCRS: `v_eci = R[i] @ v_teme`.

    The same rotation matrix is used for both position and velocity: TEME and
    GCRS are both quasi-inertial (non-rotating) frames, so at a fixed instant
    re-expressing a vector between them is a pure change of basis with no
    angular-velocity correction term (unlike ECI<->ECEF, where ITRS truly
    rotates with Earth). The precession/nutation rotation itself does drift
    with time, but at ~1e-9 rad/s -- 4-5 orders of magnitude below LEO orbital
    angular rates -- so treating it as instantaneously constant contributes
    sub-mm/s velocity error, far below this system's other uncertainty sources.

    `max_spacing_s`: since that drift is so slow, computing the *exact*
    rotation at every single fine-grained timestep (e.g. every 60s over a
    multi-day grid) is unnecessary precision, and astropy's frame-transform
    call has a real per-epoch-count cost. Instead, the exact rotation is
    computed at samples no more than `max_spacing_s` apart and every epoch
    reuses its nearest sample. Measured error from this: ~3.6cm of position
    error at 10-minute spacing, ~11cm at 30 minutes -- orders of magnitude
    below this system's own covariance model (tens to hundreds of meters), so
    the default (300s) is a comfortably safe margin, not a tight tolerance.
    Pass `max_spacing_s<=0` to disable decimation and compute the exact
    rotation at every epoch (e.g. if epochs are irregularly/coarsely spaced
    already, or for validating this approximation itself).
    """
    t = _to_astropy_time_array(epochs)
    n = len(t)

    if n <= 2 or max_spacing_s <= 0:
        return _teme_to_eci_rotation_matrices_exact(t)

    epoch_seconds = t.unix
    total_span = epoch_seconds[-1] - epoch_seconds[0]
    if total_span <= 0:
        return _teme_to_eci_rotation_matrices_exact(t)

    n_samples = max(2, min(n, int(np.ceil(total_span / max_spacing_s)) + 1))
    sample_targets = np.linspace(epoch_seconds[0], epoch_seconds[-1], n_samples)
    sample_indices = np.unique(np.searchsorted(epoch_seconds, sample_targets).clip(0, n - 1))

    R_sampled = _teme_to_eci_rotation_matrices_exact(t[sample_indices])

    # Map every original epoch to its nearest sample by time (not by index --
    # samples are spaced by real time, so the nearest index isn't necessarily
    # evenly spaced if `epochs` itself isn't perfectly uniform).
    sample_seconds = epoch_seconds[sample_indices]
    insert_pos = np.searchsorted(sample_seconds, epoch_seconds).clip(1, len(sample_seconds) - 1)
    left, right = insert_pos - 1, insert_pos
    nearest = np.where(
        np.abs(epoch_seconds - sample_seconds[left]) <= np.abs(epoch_seconds - sample_seconds[right]),
        left, right,
    )
    return R_sampled[nearest]


def apply_rotation_batch(rotations: np.ndarray, positions_km: np.ndarray, velocities_km_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply a per-row rotation matrix (from `teme_to_eci_rotation_matrices`) to a
    batch of position/velocity vectors. `rotations`: (N,3,3), `positions_km` /
    `velocities_km_s`: (N,3). Pure numpy -- no astropy call, so this is cheap
    enough to run once per object in a batch propagation loop.
    """
    pos_out = np.einsum("nij,nj->ni", rotations, positions_km)
    vel_out = np.einsum("nij,nj->ni", rotations, velocities_km_s)
    return pos_out, vel_out


# ── TEME <-> ECEF convenience composites ─────────────────────────────────────────

def teme_to_ecef(state: StateVector, epoch: datetime) -> StateVector:
    return eci_to_ecef(teme_to_eci(state, epoch), epoch)


def ecef_to_teme(state: StateVector, epoch: datetime) -> StateVector:
    return eci_to_teme(ecef_to_eci(state, epoch), epoch)


# ── ECEF -> geodetic (lat/lon/alt), useful for map/globe display ────────────────

def ecef_to_geodetic(state: StateVector, epoch: datetime | None = None) -> tuple[float, float, float]:
    """Return (latitude_deg, longitude_deg, altitude_km) for an ECEF position (WGS84)."""
    t = _to_astropy_time(epoch) if epoch is not None else Time.now()
    itrs = ITRS(
        CartesianRepresentation(state.position_km * u.km),
        obstime=t,
    )
    geodetic = itrs.earth_location.geodetic
    return (
        float(geodetic.lat.to_value(u.deg)),
        float(geodetic.lon.to_value(u.deg)),
        float(geodetic.height.to_value(u.km)),
    )


# ── Vectorized (batch) ECI -> ECEF and ECEF -> geodetic, for many objects at a
#    single shared epoch (e.g. "current position of the whole catalog right
#    now") -- mirrors teme_to_eci_batch above for the same reason: astropy's
#    per-call frame-transform overhead dominates if paid once per object in a
#    Python loop instead of once for the whole batch. ─────────────────────────

def eci_to_ecef_batch(
    positions_km: np.ndarray,
    velocities_km_s: np.ndarray,
    epoch: datetime,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Vectorized ECI/J2000 (GCRS) -> ECEF (ITRS) rotation for many objects that
    all share one epoch. `positions_km` / `velocities_km_s`: shape (N, 3).
    Returns (positions_km, velocities_km_s) each shape (N, 3), in ECEF/ITRS.
    """
    positions_km = np.asarray(positions_km, dtype=float).reshape(-1, 3)
    velocities_km_s = np.asarray(velocities_km_s, dtype=float).reshape(-1, 3)
    t = _to_astropy_time(epoch)

    rep = CartesianRepresentation(
        positions_km.T * u.km,
        differentials=CartesianDifferential(velocities_km_s.T * u.km / u.s),
    )
    gcrs = GCRS(rep, obstime=t)
    itrs = gcrs.transform_to(ITRS(obstime=t))

    pos_out = itrs.cartesian.xyz.to_value(u.km).T
    vel_out = itrs.cartesian.differentials["s"].d_xyz.to_value(u.km / u.s).T
    return pos_out, vel_out


def ecef_to_geodetic_batch(
    positions_km: np.ndarray,
    epoch: datetime | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Vectorized ECEF -> geodetic (WGS84) for many positions at a single shared
    epoch. `positions_km`: shape (N, 3). Returns (latitude_deg, longitude_deg,
    altitude_km), each shape (N,).
    """
    positions_km = np.asarray(positions_km, dtype=float).reshape(-1, 3)
    t = _to_astropy_time(epoch) if epoch is not None else Time.now()

    itrs = ITRS(CartesianRepresentation(positions_km.T * u.km), obstime=t)
    geodetic = itrs.earth_location.geodetic
    lat_deg = np.atleast_1d(geodetic.lat.to_value(u.deg))
    lon_deg = np.atleast_1d(geodetic.lon.to_value(u.deg))
    alt_km = np.atleast_1d(geodetic.height.to_value(u.km))
    return lat_deg, lon_deg, alt_km


# ── ECI -> RIC / RTN (Radial-Intrack-Crosstrack, aka Hill frame) ────────────────

def ric_rotation_matrix(reference: StateVector) -> np.ndarray:
    """
    3x3 rotation matrix from ECI into the RIC (Radial / In-track / Cross-track)
    frame centered on `reference` (also known as the RTN or Hill frame).

    Row 0 = Radial (along reference position vector)
    Row 1 = In-track (completes the right-handed triad; ~along-velocity for
            near-circular orbits)
    Row 2 = Cross-track (along the orbit angular momentum vector)
    """
    r = reference.position_km
    v = reference.velocity_km_s
    r_norm = np.linalg.norm(r)
    if r_norm == 0:
        raise ValueError("Reference position vector has zero magnitude")
    r_hat = r / r_norm

    h = np.cross(r, v)
    h_norm = np.linalg.norm(h)
    if h_norm == 0:
        raise ValueError("Reference state is degenerate (r parallel to v); angular momentum is zero")
    c_hat = h / h_norm

    i_hat = np.cross(c_hat, r_hat)

    return np.vstack([r_hat, i_hat, c_hat])


def eci_to_ric(state: StateVector, reference: StateVector) -> StateVector:
    """
    Express `state` relative to `reference` (both in ECI) in the RIC frame
    instantaneously co-moving with `reference`.

    Uses the standard rotating-frame transport theorem so the returned velocity
    is the true RIC-frame relative velocity (not just a rotated coordinate
    difference), which matters when using this for relative-motion / encounter
    geometry analysis. Validated against numerical (finite-difference)
    propagation in tests/unit/shared/test_transforms.py.
    """
    Q = ric_rotation_matrix(reference)

    r_ref, v_ref = reference.position_km, reference.velocity_km_s
    h = np.cross(r_ref, v_ref)
    omega_eci = h / np.dot(r_ref, r_ref)  # angular velocity of the RIC frame, in ECI components

    rel_pos_eci = state.position_km - r_ref
    rel_vel_eci = state.velocity_km_s - v_ref

    p_ric = Q @ rel_pos_eci
    omega_ric = Q @ omega_eci
    v_ric = Q @ rel_vel_eci - np.cross(omega_ric, p_ric)

    return StateVector(position_km=p_ric, velocity_km_s=v_ric)


def ric_to_eci(state_ric: StateVector, reference: StateVector) -> StateVector:
    """Inverse of :func:`eci_to_ric`: RIC-relative state -> absolute ECI state."""
    Q = ric_rotation_matrix(reference)
    Q_inv = Q.T  # rotation matrices are orthonormal

    r_ref, v_ref = reference.position_km, reference.velocity_km_s
    h = np.cross(r_ref, v_ref)
    omega_eci = h / np.dot(r_ref, r_ref)
    omega_ric = Q @ omega_eci

    rel_vel_eci = Q_inv @ (state_ric.velocity_km_s + np.cross(omega_ric, state_ric.position_km))
    rel_pos_eci = Q_inv @ state_ric.position_km

    return StateVector(position_km=r_ref + rel_pos_eci, velocity_km_s=v_ref + rel_vel_eci)
