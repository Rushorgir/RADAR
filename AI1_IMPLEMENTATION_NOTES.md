# AI-1 (Anas) — Full Implementation Report

**TLE Ingestion · SGP4 Propagation · Coordinate Transforms**

This is the complete record of everything done for the AI-1 (Orbital
Mechanics Lead) role: what was built, every design decision and why, a real
performance investigation (found and fixed across two passes), how it was
tested and verified, and documentation corrections made to keep the rest of
the team accurate. Kept as a reference for the team — especially AI-2
(Rushaan) and AI-3 (Udarsh), who consume this module's output directly.

**Branch**: `feat/anas` (based on up-to-date `main`)
**Scope**: `src/ingestion/`, `src/propagation/`, `src/shared/frames/`, plus `scripts/run_propagation_pipeline.py` and this doc
**Stats**: 4 commits, 23 files, ~2,973 lines added (≈2,007 implementation + scripts, ≈966 tests)
**Tests**: 98 unit tests, all passing
**End-to-end performance**: full target scale (800 real objects, 72h horizon, 60s step) runs in **~3-4 seconds**, down from an initial run that didn't finish in 5 minutes

---

## Table of contents

1. [What was built](#1-what-was-built)
2. [Design decisions and rationale](#2-design-decisions-and-rationale)
3. [Environment setup](#3-environment-setup)
4. [Performance investigation — pass 1](#4-performance-investigation--pass-1)
5. [Performance investigation — pass 2](#5-performance-investigation--pass-2)
6. [Dataset assembly](#6-dataset-assembly)
7. [Testing](#7-testing)
8. [Documentation fixes (README)](#8-documentation-fixes-readme)
9. [Git history](#9-git-history)
10. [Current status & handoff to AI-2](#10-current-status--handoff-to-ai-2)
11. [Known limitations & suggested next steps](#11-known-limitations--suggested-next-steps)

---

## 1. What was built

### `src/ingestion/` — TLE fetch, parse, cache

| File | What it does |
|---|---|
| `models.py` | `RawTLE` / `ParsedTLE` Pydantic models. `ParsedTLE` carries every decoded orbital element plus the raw lines (needed by SGP4) and derived helpers (`semi_major_axis_km`, `perigee_altitude_km`, `apogee_altitude_km`). |
| `tle_parser.py` | Fixed-width parsing of the two TLE lines per the NORAD column spec, the standard mod-10 checksum algorithm, the "assumed decimal point" exponential field format (B*, mean-motion 2nd derivative), and a name-based object-type classifier (`DEB`/`R/B` substrings → `DEBRIS`/`ROCKET_BODY`). |
| `tle_fetcher.py` | HTTP client for Celestrak's GP API. Retries transient failures with backoff; separately detects and handles Celestrak's own request-throttle response (see §6) by falling back to cache instead of treating it as an error; de-duplicates across groups by NORAD ID; filters to LEO by apogee altitude; assembles the final ~500-1000 object dataset. |
| `tle_cache.py` | File-based cache under `data/tle_cache/` with a TTL sidecar (`.meta.json`), so repeated runs don't re-hit Celestrak. |

### `src/propagation/` — SGP4 propagation, covariance, batch orchestration

| File | What it does |
|---|---|
| `sgp4_engine.py` | Wraps `sgp4.api.Satrec` per object. `propagate_at` for a single epoch, `propagate_grid` for a full timestep grid (vectorized via `sgp4_array`). Every output state is rotated TEME → ECI before being returned — nothing downstream ever sees TEME. Also hosts `build_epoch_grid` and `build_jd_fr_grid`, the shared-grid helpers both batch orchestrators use. |
| `covariance.py` | Empirical RIC-frame (Radial/In-track/Cross-track) error-growth model, rotated into ECI. Both a scalar (`estimate_covariance_6x6`) and vectorized-batch (`estimate_covariance_6x6_batch`) version. |
| `batch_propagator.py` | Sequential Pydantic-object-graph orchestrator (`propagate_catalog`): propagates the whole catalog over one shared grid, returns `BatchPropagationResult` (contract-shaped `PropagatedState` per object per timestep). Best for smaller runs, tests, or wherever the full validated object is genuinely needed. |
| `batch_arrays.py` | Fast numpy-native orchestrator (`propagate_catalog_arrays`) for catalog-scale screening: same physics, returns `(n_objects, n_steps, 3)` arrays instead of millions of Pydantic objects, with `CatalogPropagationArrays.to_propagated_state(i, j)` as an on-demand contract-compliant escape hatch. This is the recommended entry point for AI-2's screening at full catalog scale. |
| `models.py` | `SGP4ErrorCode` (wraps SGP4's numeric error codes with human-readable descriptions), `TrajectoryResult`, `BatchPropagationResult`. The actual per-state contract type is `src.shared.interfaces.contracts.PropagatedState` — not redefined here, imported and reused. |

### `src/shared/frames/transforms.py` — coordinate frame transforms

Built on astropy's built-in `TEME`/`GCRS`/`ITRS` frame classes rather than
hand-rolled precession/nutation (too easy to get subtly wrong and hard to
verify independently):

- `teme_to_eci` / `eci_to_teme` — TEME ↔ ECI (GCRS stands in for J2000 ECI)
- `eci_to_ecef` / `ecef_to_eci` — ECI ↔ ECEF (ITRS)
- `ecef_to_geodetic` — ECEF → (lat, lon, altitude), for map/globe display
- `eci_to_ric` / `ric_to_eci` — ECI ↔ RIC (Hill/RTN) frame, **with the full
  rotating-frame transport-theorem velocity term**, not just a rotated
  coordinate difference — matters for anyone using RIC for relative-motion
  analysis. Verified against numerical (finite-difference, two-body RK4)
  propagation.
- `teme_to_eci_batch` — vectorized TEME→ECI for many states sharing one
  object's timeline.
- `teme_to_eci_rotation_matrices` / `apply_rotation_batch` — the
  catalog-scale fast path: precompute the rotation once per timestep, apply
  it to every object with plain numpy. See §4-§5.

### `scripts/run_propagation_pipeline.py`

A standalone CLI demo: fetch → parse → propagate → sanity-check, runnable
against live Celestrak data with no backend/frontend required
(`python scripts/run_propagation_pipeline.py --count 800 --hours 72 --step 60`).
Doubles as the tool used to produce every timing number in this report.

---

## 2. Design decisions and rationale

**Why astropy for frame transforms, not a hand-rolled precession/nutation series.**
IAU precession-nutation models are notoriously easy to get subtly wrong (sign
conventions, model version — IAU1980 vs IAU2000/2006 — frame-bias terms), and
a bug there would be nearly impossible to catch without an independent
reference. astropy's `TEME`/`GCRS`/`ITRS` frames are a maintained, widely-used
implementation; verification then becomes "does this match known physical
behavior" (ISS altitude, round-trip identity, RIC transport theorem) rather
than "did I re-derive 1980s IAU tables correctly."

**Why a synthetic covariance model instead of leaving it null.**
Celestrak TLEs carry zero covariance information, and real orbit-determination
covariance requires filtering actual tracking-observation residuals — entirely
out of scope for a hackathon prototype with no ground-station data. AI-2's Pc
calculation needs *some* uncertainty estimate to be exercised at all, so
`covariance.py` provides one physically-motivated placeholder: uncertainty
grows fastest in-track (dominated by drag/B* mis-modeling — the standard
result from TLE propagation-error literature), slower radially and
cross-track, and debris gets wider bounds than actively-maintained payloads
(no maneuver history, more variable area-to-mass ratio). This is explicitly
documented as a placeholder in the code, not presented as a real OD product.

**Why both a Pydantic path and a numpy-array path for batch propagation.**
The team's shared contract (`PropagatedState`) is a Pydantic model — the right
choice for a validated, typed interface between modules. But materializing
millions of them for catalog-scale screening turned out to be a real,
measured bottleneck (§5). Rather than choosing one extreme (always Pydantic =
slow at scale; always raw arrays = no validated contract), both paths exist:
`batch_propagator.propagate_catalog` for anywhere the full contract object is
wanted (small runs, tests, packaging one flagged event), `batch_arrays.propagate_catalog_arrays`
for catalog-scale numeric screening, with `to_propagated_state()` bridging
back to the contract type on demand. This also isn't an arbitrary shortcut:
AI-2's own screening design (from their implementation plan) explicitly wants
`positions: np.ndarray` per timestep for its k-d tree fine filter — the array
path is the shape their code wants anyway.

**Why the object-type classifier is a name heuristic, not a SATCAT lookup.**
Celestrak's GP API doesn't return an authoritative object-type field in the
TLE text format itself, and integrating a full SATCAT cross-reference was out
of scope for the time available. Substring matching on the object name
(`DEB`/`DEBRIS` → `DEBRIS`, `R/B`/`ROCKET BODY` → `ROCKET_BODY`, else
`PAYLOAD`) is what Celestrak's own naming convention supports, and is
explicitly called out in the code as a placeholder "until an authoritative
SATCAT lookup is available" (matching the wording already in
`src/ingestion/README.md`).

**Why the dataset is shuffled before capping to `target_count`.**
`fetch_groups` returns objects group-by-group. A plain list slice to
`target_count` would let whichever group happened to fetch successfully
first — or fail, as Celestrak's large `active` group easily gets
throttled — dominate or entirely starve the final mix. A fixed-seed shuffle
keeps the capped sample representative of whatever mix actually came back,
and keeps test runs reproducible.

---

## 3. Environment setup

`pyproject.toml` requires Python ≥3.10, but only Python 3.9 was installed on
this machine. Installed Python 3.11.9 via the Windows Python install manager
(`py install 3.11`), created `.venv` with it, and `pip install -r
requirements.txt` — all packages (sgp4, astropy, skyfield, pydantic, numpy,
etc.) installed cleanly. Added `.vscode/settings.json` pointing the IDE at
`.venv` so import resolution works in-editor too.

`skyfield` is listed as a dependency in `requirements.txt` but was not
ultimately needed — astropy's built-in TEME/GCRS/ITRS frames covered every
transform required. It remains available for future work (e.g. visibility /
rise-set calculations) if needed downstream.

---

## 4. Performance investigation — pass 1

The first end-to-end run — `propagate_catalog()` on the target 800-object
dataset over a 72h/60s grid (~4,321 timesteps, matching AI-2's stated
screening window) — **didn't finish in 5 minutes**. Not acceptable for a
system meant to propagate 500-1000 objects, so this was tracked down rather
than shipped as-is.

**Root causes, three stacked issues found first:**

1. **Redundant frame-transform calls.** The batch propagator called the
   TEME→ECI astropy conversion once *per object*, even though every object
   shares the exact same timestep grid. astropy's frame transform pays a
   fixed precession/nutation/IERS-lookup cost per call — paying it 800 times
   for *identical* timestamps instead of once was the single biggest cost.
   **Fix**: `teme_to_eci_rotation_matrices()` computes the TEME→GCRS rotation
   matrix once per timestep (by transforming the 3 orthonormal basis vectors,
   mathematically sufficient since TEME/GCRS are both inertial — no
   angular-velocity correction needed, unlike ECEF), then `apply_rotation_batch()`
   applies it to each object with plain numpy. O(n_objects) astropy calls → O(1).

2. **Redundant Julian-date conversion.** Each object's `propagate_grid`
   rebuilt its own `(jd, fr)` array for the *same* 4,321 epochs via a
   per-epoch Python loop — 800 × 4,321 ≈ 3.46M redundant Python-level calls.
   **Fix**: `build_jd_fr_grid()` computes this once; the batch orchestrators
   pass the shared arrays into each object's `Satrec.sgp4_array` call directly.

3. **Per-state covariance estimation.** `estimate_covariance_6x6` was called
   once per propagated *state* — another ~3.46M small numpy calls, each
   dominated by Python/numpy call overhead rather than actual math.
   **Fix**: `estimate_covariance_6x6_batch()` computes covariance for an
   object's entire trajectory (all ~4,321 states) in one vectorized call.

**A fourth issue, found after "fixing" the first three: threading.** The
batch propagator ran each object's SGP4 propagation in an 8-worker
`ThreadPoolExecutor`, on the documented assumption that `sgp4_array` (a C
extension) releases the GIL for its bulk of the work. That assumption was
wrong for this workload: after fixes 1-3, a *sequential*, single-threaded run
of the exact same work finished in seconds, while the threaded version still
took 5+ minutes. Measured, not theorized: isolating each phase (SGP4, frame
rotation, covariance, object construction) single-threaded totalled well
under a minute; wrapping the SGP4 step in a thread pool made it dramatically
slower, consistent with GIL contention between worker threads dominating any
real parallelism. **Fix**: dropped the thread pool entirely — this workload
runs sequentially.

**A fifth issue, found while chasing the fourth.** Even sequential and with
all four numeric fixes in place, propagating 800 objects over 72h/60s
(≈3.46M individual states) and materializing every single one as a validated
Pydantic `PropagatedState` was itself a real cost — and a *growing* one (100
objects: 15.5s elapsed; 500 objects: 81.8s elapsed; clearly super-linear),
consistent with GC/memory pressure from retaining millions of Python objects
simultaneously. The actual physics (SGP4 + frame rotation + covariance, all
vectorized numpy) finishes in under 10 seconds for the whole catalog — the
Pydantic object construction was the dominant remaining cost, not the math.

**Fix**: added `src/propagation/batch_arrays.py` — the numpy-native fast path
described in §1 and §2, with `to_propagated_state(i, j)` as the
contract-compliant escape hatch for a single flagged state.

**Checkpoint result** (800 objects, live Celestrak data, 72h/60s = 4,321
timesteps, via `scripts/run_propagation_pipeline.py`):

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
including covariance) for the full target scale.

This whole chain (redundant frame transforms → redundant date conversion →
redundant covariance calls → harmful threading → Pydantic object-graph
overhead) is the kind of thing invisible in unit tests, which necessarily use
small N, and only shows up at realistic catalog scale — worth documenting
explicitly for whoever next touches this code path, and a reminder to always
measure at target scale rather than assume a technique (threading, in this
case) helps.

---

## 5. Performance investigation — pass 2

After pass 1, `propagate_catalog_arrays` on the full 800-object dataset was
down to ~6s. Asked to push further, profiled that 6s phase-by-phase and found
two more real wins, even though the workload was already "fast enough" by
hackathon standards:

1. **`hours_since_epoch` was still a nested Python loop.** Computing each
   object's "hours since its own TLE epoch" at every timestep (needed by the
   covariance error-growth model) was a per-object list comprehension over
   `(datetime - datetime).total_seconds()` — ~3.46M individual datetime
   subtractions across the catalog, comparable in cost to the SGP4
   propagation itself. **Fix**: convert every epoch to a POSIX timestamp once
   (`datetime.timestamp()` — one array of length `n_steps`, one of length
   `n_objects`), then get the whole `(n_objects, n_steps)` matrix via one
   broadcast subtraction. Measured: **4.5s → 0.004s** for this step alone.

2. **The rotation-matrix computation from pass 1 was now the single largest
   remaining cost (~2.4s)** — computing the *exact* TEME→GCRS rotation at all
   4,321 timesteps. Precession/nutation drifts at ~1e-9 rad/s; measured
   directly (transform the same test vector with the rotation from `t` vs.
   `t+30min` and diff the result): reusing one rotation matrix across a
   10-minute window introduces **3.6cm** of position error, 30 minutes
   introduces **11cm** — utterly negligible next to this system's own
   covariance model (tens to hundreds of meters of 1-sigma uncertainty).
   **Fix**: `teme_to_eci_rotation_matrices` now takes a `max_spacing_s`
   parameter (default 300s / 5 minutes — a comfortably safe margin, not a
   tight tolerance): it computes the exact rotation at samples no more than
   that far apart in real time, and every timestep reuses its nearest
   sample, instead of computing the exact rotation at every single one.
   `max_spacing_s<=0` disables this and recovers the original
   exact-every-epoch behavior — exercised by a dedicated test confirming the
   decimated result stays within millimeters of the exact one.

Also checked, before assuming it would help: whether `sgp4.api.SatrecArray`
(propagating multiple satellites against one time grid in a single call)
would beat the simple per-object Python loop. Measured directly — it didn't
(1.64s vs. 1.21s for 800 objects) — so the per-object loop was kept rather
than "optimized" into something slower.

**Result of this second pass**, full 800-object/72h/60s/covariance-on run,
3 consecutive trials: **3.12s, 3.27s, 3.73s** (down from ~6.08s after pass 1).
Combined across both passes, that's roughly **100x** faster than the original
"didn't finish in 5 minutes" baseline:

```text
=== Step 1/3: Fetching + parsing TLE dataset (target 800 objects) ===
  -> 800 objects assembled in 0.87s (cache hit)
  -> composition: {'PAYLOAD': 683, 'DEBRIS': 117}

=== Step 2/3: SGP4 batch propagation (72.0h horizon, 60.0s step) ===
  -> propagated 800 objects x 4321 timesteps in 3.99s

=== Step 3/3: Sanity checks ===
  -> covariance health (sample of 500): 500/500 positive-definite
  -> sample state (object 52470, 'STARLINK-3859'):
     epoch=2026-08-22T10:20:47.949795+00:00
     position_eci_km=[-6299.984, -1902.551, 1861.483]
     velocity_eci_km_s=[-0.19334, -5.01978, -5.75355]

Pipeline OK: ingestion -> SGP4 propagation -> ECI state vectors ready for AI-2.
```

---

## 6. Dataset assembly

`build_default_dataset()` pulls from a curated set of Celestrak GP groups:
`stations`, `active` (filtered to LEO), and four real debris-cloud groups
(`cosmos-2251-debris`, `iridium-33-debris`, `cosmos-1408-debris`,
`fengyun-1c-debris` — actual historical collision/ASAT-test debris, not
synthetic). Objects are de-duplicated by NORAD ID, filtered to LEO (apogee
altitude ≤ 2000 km), shuffled with a fixed seed (see §2 for why), then capped
at the target count (500-1000).

**A quirk discovered along the way**: Celestrak doesn't just rate-limit with
a generic error — repeat requests for a GROUP within its ~2h update window
get a `403` with an explanatory body ("GP data has not updated since your
last successful download..."). This isn't a failure, it means the cache is
already current. `TLENotModified` is raised as its own exception type (not
retried with backoff like a real transient error), and the fetcher falls
back to the existing cache instead of treating it as an outage.

---

## 7. Testing

98 unit tests, all passing, across:

- `tests/unit/ingestion/` (39 tests) — checksum validation, exact field
  decoding against a real ISS TLE, epoch decoding, object-type
  classification, multi-record file parsing, cache TTL behavior, fetcher
  retry/fallback logic (network mocked — no live-network dependency in the
  test suite itself).
- `tests/unit/propagation/` (40 tests) — SGP4 propagation sanity (LEO
  altitude/speed ranges), SGP4 error-code handling (via a fake `Satrec`,
  since the real one is a read-only C extension), covariance
  growth/positive-definiteness, batch orchestration (object coverage,
  covariance attachment, progress callback, epoch grid), and the
  array-native fast path (shapes, covariance health, and a direct numerical
  cross-check against the Pydantic path to 1e-9).
- `tests/unit/shared/` (19 tests) — TEME/ECI/ECEF round-trips, geodetic
  conversion sanity (equator/pole points), RIC rotation orthonormality, the
  RIC velocity transport-theorem term validated against finite-difference
  two-body propagation, and the rotation-matrix decimation's accuracy
  against the exact (non-decimated) computation.

All of this runs against **real fetched Celestrak data** where practical
(ISS TLE cross-checked: ~413-423 km altitude, ~7.5-7.9 km/s orbital speed —
matches reality), not just synthetic fixtures.

---

## 8. Documentation fixes (README)

While confirming the interface contract description in `README.md` was
accurate, found real drift between it and the actual
`src/shared/interfaces/contracts.py` (the team's agreed source of truth) —
fixed rather than left, since a wrong field name in a "must adhere to"
contract doc is a real integration risk for whoever builds against it next:

- AI-1 → AI-2 block used `position_eci`, `velocity_eci`, `hard_body_radius`,
  `cross_section_area` — actual fields are `position_eci_km`,
  `velocity_eci_km_s`, `hard_body_radius_km`, `cross_section_area_m2`
  (and the doc was missing `object_name` entirely).
- AI-2 → AI-3/Backend block: `combined_covariance_enc` →
  `combined_covariance_enc_2x2` (matches `ConjunctionEvent`).
- AI-3 → Backend block: `delta_v_ms` → `delta_v_m_s` (matches
  `ManeuverAdvisory`).

Also added: a Quick Start command for the working AI-1 demo script (so the
team has something runnable today without waiting on backend/frontend), a
link to this document, and a References section with links — verified live
before adding, not assumed. One candidate NASA NTRS citation ID for the
Foster Pc paper was checked and turned out to be an unrelated paper on
viscoplasticity, so a search-query link was used instead of guessing a
citation.

---

## 9. Git history

| Commit | Summary |
|---|---|
| `81b57c3` | Full ingestion + propagation + shared/frames implementation and initial 82-test suite. |
| `2f5279f` | Performance pass 1 (§4): shared rotation/jd-grid, batched covariance, dropped threading, numpy-native `batch_arrays.py` fast path. 93 tests. |
| `37d3678` | Performance pass 2 (§5): vectorized `hours_since_epoch`, decimated rotation matrices. 98 tests. |
| `b06405a` | README interface-contract fixes and verified reference links (§8). |

All four commits are on `feat/anas`, pushed to `origin/feat/anas`. Branch is
based on up-to-date `main` (no rebasing needed as of this writing).

---

## 10. Current status & handoff to AI-2

**Ready to consume today**: `src/propagation/batch_arrays.propagate_catalog_arrays()`
returns everything AI-2's screening design (per their implementation plan)
needs directly — `positions_at(t)` for the k-d tree fine filter, per-object
`ok_mask`/altitude data for the coarse filter, and `to_propagated_state(i, j)`
to get a fully validated `PropagatedState` for a specific flagged encounter
(e.g. when packaging a `ConjunctionEvent`).

**Worth flagging directly to Rushaan** (not just left in this doc): the
README contract fixes in §8 — `combined_covariance_enc_2x2` in particular,
since that's the field name his `ConjunctionEvent` output already uses, and
the old README text would have been actively misleading if referenced while
building `src/conjunction/`.

**Interface contract compliance**: every `PropagatedState` produced by either
propagation path passes the exact Pydantic validation in
`src/shared/interfaces/contracts.py` — no local reinterpretation of that
schema exists anywhere in this module.

---

## 11. Known limitations & suggested next steps

Documented honestly rather than glossed over:

- **Covariance is a synthetic placeholder** (§2), not derived from real
  tracking data. Fine for exercising AI-2's Pc pipeline end-to-end; not a
  substitute for real OD covariance if this ever needed to be operationally
  accurate.
- **Object-type classification is a name heuristic**, not an authoritative
  SATCAT lookup (§2). Works for Celestrak's own naming convention; would
  misclassify an object with an unconventional name.
- ~~SGP4 decayed-object handling is only tested via a mocked `Satrec`~~ —
  **closed**: `tests/unit/propagation/test_sgp4_engine.py::TestSgp4FailureHandling::test_real_satrec_reports_decay_for_a_genuinely_decayed_extrapolation`
  now exercises the real (unmocked) `Satrec.sgp4` against the same real,
  unmodified ISS TLE the rest of the suite uses, propagated ~10 years past
  its own epoch — far enough that its real B* drag term, extrapolated that
  far by SGP4's own model, legitimately predicts decay
  (`SATELLITE_HAS_DECAYED`), rather than a fabricated "historical" TLE.
- ~~No independent second-implementation cross-check yet~~ — **closed**:
  `tests/unit/propagation/test_skyfield_cross_check.py` runs the same real
  ISS TLE through skyfield's independent SGP4 implementation at 5 offsets
  (epoch, +1h, +6h, +24h, +72h) and diffs against this module's output.
  Measured agreement: 12m-187m position, comfortably inside a 1km bound —
  rules out a wide class of frame/rotation bugs this module's own tests
  can't, since skyfield shares none of this module's frame-transform code.
- ~~`config/settings.toml` isn't wired up yet~~ — **closed**:
  `src/shared/config.py` loads it (with CLI-arg and env-var override
  support, 6 tests in `tests/unit/shared/test_config.py`), and
  `scripts/run_radar_pipeline.py` reads `propagation_horizon_h` /
  `screening_timestep_s` from it instead of hardcoding them.
- **No PR was ever opened for `feat/anas` against `main`** — moot now:
  `feat/anas` (and every other feature branch this project used) has since
  been merged directly into `main`, so there's nothing left to open a PR
  against.
