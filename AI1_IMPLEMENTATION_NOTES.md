# AI-1 (Anas) Implementation Notes — TLE Ingestion, SGP4 Propagation, Coordinate Transforms

This documents exactly what was built, how it was verified, and a real
performance bug that was found and fixed while building this out — kept as a
record for the team (and for AI-2/AI-3, who consume this module's output).

**Branch**: `feat/anas` · **Scope**: `src/ingestion/`, `src/propagation/`, `src/shared/frames/`

---

## 1. What was built

### `src/ingestion/` — TLE fetch, parse, cache

| File | What it does |
|---|---|
| `models.py` | `RawTLE` / `ParsedTLE` Pydantic models. `ParsedTLE` carries every decoded orbital element plus the raw lines (needed by SGP4) and derived helpers (`semi_major_axis_km`, `perigee_altitude_km`, `apogee_altitude_km`). |
| `tle_parser.py` | Fixed-width parsing of the two TLE lines per the NORAD column spec, the standard mod-10 checksum algorithm, the "assumed decimal point" exponential field format (B*, mean-motion 2nd derivative), and a name-based object-type classifier (`DEB`/`R/B` substrings → `DEBRIS`/`ROCKET_BODY`). |
| `tle_fetcher.py` | HTTP client for Celestrak's GP API. Retries transient failures with backoff; separately detects and handles Celestrak's own request-throttle response (see §3 below) by falling back to cache instead of treating it as an error; de-duplicates across groups by NORAD ID; filters to LEO by apogee altitude; assembles the final ~500-1000 object dataset. |
| `tle_cache.py` | File-based cache under `data/tle_cache/` with a TTL sidecar (`.meta.json`), so repeated runs don't re-hit Celestrak. |

### `src/propagation/` — SGP4 propagation, covariance, batch orchestration

| File | What it does |
|---|---|
| `sgp4_engine.py` | Wraps `sgp4.api.Satrec` per object. `propagate_at` for a single epoch, `propagate_grid` for a full timestep grid (vectorized via `sgp4_array`). Every output state is rotated TEME → ECI before being returned — nothing downstream ever sees TEME. |
| `covariance.py` | Celestrak TLEs carry no covariance at all, and real orbit-determination covariance requires actual tracking-residual filtering, which is out of scope here. Instead: an empirical RIC-frame (Radial/In-track/Cross-track) error-growth model (in-track error grows fastest — dominated by drag/B* mis-modeling, per Vallado & Cefola 2012), rotated into ECI. Object-type-dependent (debris gets wider uncertainty than active payloads). |
| `batch_propagator.py` | Sequential (see §3 — threading measured *worse*) Pydantic-object-graph orchestrator: propagates the whole catalog over one shared 72h/60s grid, returns `BatchPropagationResult` (contract-shaped `PropagatedState` per object per timestep). Best for smaller runs, tests, or wherever the full validated object is genuinely needed. |
| `batch_arrays.py` | Fast numpy-native orchestrator (`propagate_catalog_arrays`) for catalog-scale screening: same physics, returns `(n_objects, n_steps, 3)` arrays instead of millions of Pydantic objects, with `to_propagated_state(i, j)` as an on-demand contract-compliant escape hatch. See §3. |
| `models.py` | `SGP4ErrorCode` (wraps SGP4's numeric error codes with descriptions), `TrajectoryResult`, `BatchPropagationResult`. The actual per-state contract type is `src.shared.interfaces.contracts.PropagatedState` — not redefined here. |

### `src/shared/frames/transforms.py` — coordinate frame transforms

Built on astropy's built-in `TEME`/`GCRS`/`ITRS` frame classes (not hand-rolled
precession/nutation — too easy to get subtly wrong and hard to verify
independently):

- `teme_to_eci` / `eci_to_teme` — TEME ↔ ECI (GCRS stands in for J2000 ECI)
- `eci_to_ecef` / `ecef_to_eci` — ECI ↔ ECEF (ITRS)
- `ecef_to_geodetic` — ECEF → (lat, lon, altitude), for map/globe display
- `eci_to_ric` / `ric_to_eci` — ECI ↔ RIC (Hill/RTN) frame, **with the full
  rotating-frame transport-theorem velocity term**, not just a rotated
  coordinate difference — this matters for anyone using RIC for relative-motion
  analysis. Verified against numerical (finite-difference, two-body RK4)
  propagation in `tests/unit/shared/test_transforms.py`.
- `teme_to_eci_batch`, `teme_to_eci_rotation_matrices`, `apply_rotation_batch` —
  vectorized/precomputed-rotation variants added specifically for the batch
  propagator performance fix in §3.

---

## 2. Environment setup

`pyproject.toml` requires Python ≥3.10, but only Python 3.9 was installed on
this machine. Installed Python 3.11.9 via the Windows Python install manager
(`py install 3.11`), created `.venv` with it, and `pip install -r
requirements.txt` — all packages (sgp4, astropy, skyfield, pydantic, numpy,
etc.) installed cleanly. Added `.vscode/settings.json` pointing the IDE at
`.venv` so import resolution works in-editor too.

---

## 3. A real performance bug: found, diagnosed, fixed

The first end-to-end run — `propagate_catalog()` on the target 800-object
dataset over a 72h/60s grid (~4,321 timesteps, matching AI-2's screening
window) — didn't finish in 5 minutes. That's not acceptable for a system meant
to propagate 500-1000 objects, so this was tracked down rather than shipped.

**Root causes (three, stacked):**

1. **Redundant frame-transform calls.** The batch propagator called the
   TEME→ECI astropy conversion once *per object* even though every object
   shares the exact same timestep grid. Astropy's frame transform pays a fixed
   precession/nutation/IERS-lookup cost per call — paying it 800 times for
   *identical* timestamps instead of once was the single biggest cost.
   **Fix**: `teme_to_eci_rotation_matrices()` computes the TEME→GCRS rotation
   matrix once per timestep (by transforming the 3 orthonormal basis vectors,
   which is mathematically sufficient since TEME/GCRS are both inertial — no
   angular-velocity correction needed, unlike ECEF), then `apply_rotation_batch()`
   applies it to each object with plain numpy. O(n_objects) astropy calls → O(1).

2. **Redundant Julian-date conversion.** Each object's `propagate_grid` rebuilt
   its own `(jd, fr)` array for the *same* 4,321 epochs via a per-epoch Python
   loop — 800 × 4,321 ≈ 3.46M redundant Python-level calls.
   **Fix**: `build_jd_fr_grid()` computes this once; `batch_propagator` passes
   the shared arrays into each object's `Satrec.sgp4_array` call directly.

3. **Per-state covariance estimation.** `estimate_covariance_6x6` was called
   once per propagated *state* — another ~3.46M small numpy calls, each
   dominated by Python/numpy call overhead rather than actual math.
   **Fix**: `estimate_covariance_6x6_batch()` computes covariance for an
   object's entire trajectory (all ~4,321 states) in one vectorized call.

**A fourth issue, found after "fixing" the first three**: threading. The
batch propagator ran each object's SGP4 propagation in an 8-worker
`ThreadPoolExecutor`, on the documented assumption that `sgp4_array` (a C
extension) releases the GIL for its bulk of the work. That assumption was
wrong for this workload — after fixes 1-3, a *sequential*, single-threaded
run of the exact same work finished in seconds, while the threaded version
still took 5+ minutes. Measured, not theorized: isolating each phase
(SGP4, frame rotation, covariance, object construction) single-threaded
totalled well under a minute; wrapping the SGP4 step in a thread pool made
it dramatically slower, consistent with GIL contention between worker
threads dominating any real parallelism. **Fix**: dropped the thread pool
entirely — this workload runs sequentially now.

**A fifth issue, found while chasing the fourth**: even sequential and with
all four numeric fixes in place, propagating 800 objects over 72h/60s
(≈3.46M individual states) and materializing every single one as a validated
Pydantic `PropagatedState` was itself a real cost — and a *growing* one (100
objects: 15.5s elapsed; 500 objects: 81.8s elapsed; clearly super-linear),
consistent with GC/memory pressure from retaining millions of Python objects
simultaneously. The actual physics (SGP4 + frame rotation + covariance, all
vectorized numpy) finishes in under 10 seconds for the whole catalog — the
Pydantic object construction was the dominant remaining cost, not the math.

**Fix**: added `src/propagation/batch_arrays.py` — a numpy-native fast path
(`propagate_catalog_arrays`) that returns `(n_objects, n_steps, 3)` arrays
instead of a Pydantic object graph, with `to_propagated_state(i, j)` as an
on-demand, contract-compliant escape hatch for a single flagged state. This
matches AI-2's own screening design (from their implementation plan: coarse
altitude filter over `list[PropagatedState]` per object is fine, but the
fine filter's `cKDTree` step explicitly wants `positions: np.ndarray` per
timestep) — so the fast path isn't a shortcut around the contract, it's the
shape AI-2's screening step wants anyway. The Pydantic path
(`batch_propagator.propagate_catalog`) is kept for smaller runs, tests, and
anywhere the full validated contract object is genuinely needed.

**Final verification, real numbers, full target scale** (800 objects, live
Celestrak data — 683 payloads + 117 debris that run, composition varies by
what's live — 72h horizon, 60s step = 4,321 timesteps, run via
`scripts/run_propagation_pipeline.py`):

```text
=== Step 1/3: Fetching + parsing TLE dataset (target 800 objects) ===
  -> 800 objects assembled in 6.58s (cached under data/tle_cache/)
  -> composition: {'PAYLOAD': 683, 'DEBRIS': 117}

=== Step 2/3: SGP4 batch propagation (72.0h horizon, 60.0s step) ===
  -> propagated 800 objects x 4321 timesteps in 6.08s

=== Step 3/3: Sanity checks ===
  -> covariance health (sample of 500): 500/500 positive-definite
  -> sample state (object 52470, 'STARLINK-3859'):
     epoch=2026-08-22T10:07:34.627502+00:00
     position_eci_km=[-3851.41, 2277.999, 5164.776]
     velocity_eci_km_s=[-5.56962, -4.82137, -2.02163]

Pipeline OK: ingestion -> SGP4 propagation -> ECI state vectors ready for AI-2.
```

From "didn't finish in 5 minutes" to **~13s total** (fetch + propagate,
including covariance) for the full target scale. All 93 unit tests
(82 original + 11 new for `batch_arrays.py`, including a test that the fast
array path and the Pydantic path agree numerically to 1e-9) stayed green
through every stage of this.

This whole chain (redundant frame transforms → redundant date conversion →
redundant covariance calls → harmful threading → Pydantic object-graph
overhead) is the kind of thing that's invisible in unit tests, which
necessarily use small N, and only shows up at realistic catalog scale —
worth documenting explicitly for whoever next touches this code path, and a
reminder to always measure at target scale rather than assume a technique
(threading, in this case) helps.

---

## 4. Dataset assembly

`build_default_dataset()` pulls from a curated set of Celestrak GP groups:
`stations`, `active` (filtered to LEO), and four real debris-cloud groups
(`cosmos-2251-debris`, `iridium-33-debris`, `cosmos-1408-debris`,
`fengyun-1c-debris` — actual historical collision/ASAT-test debris, not
synthetic). Objects are de-duplicated by NORAD ID, filtered to LEO (apogee
altitude ≤ 2000 km), **shuffled with a fixed seed**, then capped at the target
count (500-1000).

The shuffle matters: `fetch_groups` returns objects group-by-group, so a plain
list slice would let whichever group happened to fetch successfully first (or
fail — Celestrak's `active` group is large and gets throttled easily, see
below) dominate or starve the final mix. A fixed-seed shuffle keeps the capped
sample representative and the result reproducible for tests.

**A quirk discovered along the way**: Celestrak doesn't just rate-limit with a
generic error — repeat requests for a GROUP within its ~2h update window get a
`403` with an explanatory body ("GP data has not updated since your last
successful download..."). This isn't a failure, it means the cache is already
current. `TLENotModified` is raised as its own exception type (not retried
with backoff like a real transient error) and the fetcher falls back to the
existing cache instead of treating it as an outage.

---

## 5. Testing

82 unit tests, all passing, across:

- `tests/unit/ingestion/` (39 tests) — checksum validation, exact field
  decoding against a real ISS TLE, epoch decoding, object-type classification,
  multi-record file parsing, cache TTL behavior, fetcher retry/fallback logic
  (network mocked — no live-network dependency in the test suite itself).
- `tests/unit/propagation/` (29 tests) — SGP4 propagation sanity (LEO
  altitude/speed ranges), SGP4 error-code handling (via a fake `Satrec`, since
  the real one is a read-only C extension), covariance growth/positive-
  definiteness, batch orchestration (object coverage, covariance attachment,
  progress callback, epoch grid).
- `tests/unit/shared/` (14 tests) — TEME/ECI/ECEF round-trips, geodetic
  conversion sanity (equator/pole points), RIC rotation orthonormality, and
  the RIC velocity transport-theorem term validated against finite-difference
  two-body propagation.

All of this runs against **real fetched Celestrak data** where practical
(ISS TLE cross-checked: ~413-423 km altitude, ~7.5-7.9 km/s orbital speed —
matches reality), not just synthetic fixtures.

---

## 6. Git

- Branch `feat/anas`, based on up-to-date `main`.
- Commit `81b57c3`: full ingestion + propagation + shared/frames implementation
  and test suite, pushed to `origin/feat/anas`.
- The performance fix in §3 lands as a follow-up commit (see git log on this
  branch for the exact hash).
