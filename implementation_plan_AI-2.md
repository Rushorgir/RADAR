# Implementation Plan: AI-2 Conjunction Screening & Probability of Collision Engine

**Owner**: Rushaan (AI-2: Conjunction & Probability Math Lead)  
**Module**: `src/conjunction/` — Screening, Pc Calculation, Data Models  
**Branch**: `feat/rushaan-conjunction-pc`

---

## Overview

This module is the **core physics engine** of OrbitGuard. It sits between AI-1's propagated state vectors and AI-3's ML risk ranking, performing two critical computations:

1. **Conjunction Screening** — identify which pairs of objects, out of potentially ~500k pairwise combinations (for 1000 objects), are actually on close-approach trajectories
2. **Probability of Collision (Pc)** — for each flagged conjunction, compute the quantitative collision risk using the combined position uncertainty

The design uses a **two-stage screening architecture** (coarse altitude filter → fine k-d tree spatial search) to avoid the $O(n^2)$ brute-force cost, followed by a **dual-method Pc engine** (Foster's 2D analytical primary, Monte Carlo numerical fallback).

---

## Design Decisions (Locked In)

| # | Decision | Resolution |
|---|----------|------------|
| 1 | **Covariance dimensionality** | Accept 6×6, extract 3×3 position block. If AI-1 sends `None`, auto-generate default diagonal covariance (σ_pos ≈ 1 km for LEO). |
| 2 | **Miss distance threshold for Pc** | Two-tier: full Pc for < 5 km, log-only for 5–10 km (assign Pc ≈ 0), discard > 10 km. |
| 3 | **Monte Carlo sample count** | Adaptive: start with 10⁵ samples, escalate to 10⁶ if 0 hits, then report Pc = 0 with Wilson upper bound. |
| 4 | **Foster integration method** | `scipy.integrate.dblquad` with eigendecomposition primary. Chan's series as future optimization if bottleneck. |
| 5 | **Screening timestep** | 60 seconds across 72-hour propagation window (~4,320 timesteps). |
| 6 | **Duplicate encounter handling** | One ConjunctionEvent per object pair, at the global minimum miss distance TCA. |
| 7 | **Parallelism** | None — single-threaded with NumPy vectorization. No multiprocessing. |
| 8 | **Logging** | `loguru` structured logging at pipeline milestones (filter counts, Pc values, method used). |
| 9 | **ESA Kelvins validation** | Dropped from AI-2 scope. Udarsh (AI-3) downloads it independently for ML training. |
| 10 | **Unit tests** | Minimal but meaningful tests for core algorithms (Foster accuracy, MC convergence, frame orthonormality). |

---

## File Structure

```
src/conjunction/
├── __init__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── state.py              # PropagatedState input model (re-exports from shared)
│   ├── conjunction_event.py   # ConjunctionEvent output model
│   └── encounter.py           # EncounterGeometry intermediate model
├── screening/
│   ├── __init__.py
│   ├── coarse_filter.py       # Stage 1: Altitude band bucketing
│   ├── fine_filter.py         # Stage 2: k-d tree spatial proximity
│   ├── tca_refiner.py         # TCA interpolation/refinement
│   └── engine.py              # Orchestrator combining both stages
├── probability/
│   ├── __init__.py
│   ├── encounter_frame.py     # Coordinate transform to encounter plane
│   ├── foster_2d.py           # Foster's 2D analytical Pc method
│   ├── monte_carlo.py         # Monte Carlo Pc fallback
│   └── engine.py              # Pc engine with auto-method selection
└── pipeline.py                # End-to-end pipeline: states → conjunction events

tests/unit/conjunction/
├── __init__.py
├── test_coarse_filter.py
├── test_fine_filter.py
├── test_encounter_frame.py
├── test_foster_2d.py
├── test_monte_carlo.py
└── test_pipeline.py

tests/fixtures/
├── synthetic_head_on.json
├── synthetic_coplanar.json
└── synthetic_clear_miss.json
```

---

## Detailed Component Design

### 1. Data Models (`src/conjunction/models/`)

> [!NOTE]
> Primary data models live in `src/shared/interfaces/contracts.py` and are re-exported here. Module-internal intermediate models live in this directory.

#### [NEW] `encounter.py`

```python
@dataclass
class EncounterGeometry:
    primary_state: PropagatedState
    secondary_state: PropagatedState
    tca: datetime
    relative_position_eci: np.ndarray   # (3,) km
    relative_velocity_eci: np.ndarray   # (3,) km/s
    miss_distance_km: float
    relative_speed_km_s: float
    combined_covariance_eci: np.ndarray  # (3,3) km² — always 3×3 position block
    combined_hard_body_radius_km: float
    # Encounter frame quantities (populated after frame transform)
    rotation_matrix: np.ndarray | None = None       # (3,3) ECI→encounter rotation
    relative_position_enc: np.ndarray | None = None  # (2,) B-plane [B·T, B·N] km
    combined_covariance_enc: np.ndarray | None = None # (2,2) projected covariance km²
```

#### Covariance Fallback Logic

```python
DEFAULT_POSITION_COVARIANCE_KM2 = np.diag([1.0, 1.0, 1.0])  # σ ≈ 1 km per axis

def extract_position_covariance(cov_6x6: np.ndarray | None) -> np.ndarray:
    """Extract 3×3 position block from 6×6. Fallback to default if None."""
    if cov_6x6 is None:
        return DEFAULT_POSITION_COVARIANCE_KM2.copy()
    cov = np.array(cov_6x6)
    if cov.shape == (6, 6):
        return cov[:3, :3]
    elif cov.shape == (3, 3):
        return cov
    else:
        return DEFAULT_POSITION_COVARIANCE_KM2.copy()
```

---

### 2. Stage 1: Coarse Filter (`screening/coarse_filter.py`)

#### Algorithm

Eliminates object pairs that **cannot geometrically intersect** based on altitude ranges.

For each object, compute altitude range over the screening window:
- $h_{\min} = \|\vec{r}\|_{\min} - R_\oplus$ (perigee altitude)
- $h_{\max} = \|\vec{r}\|_{\max} - R_\oplus$ (apogee altitude)

Two objects can only conjunct if altitude bands **overlap** with margin $\delta = 50$ km:

$$[h_{\min,i} - \delta, \; h_{\max,i} + \delta] \;\cap\; [h_{\min,j} - \delta, \; h_{\max,j} + \delta] \neq \emptyset$$

#### Implementation

```python
def compute_altitude_band(states: list[PropagatedState]) -> tuple[float, float]:
    """Compute min/max altitude across all epochs for a single object."""
    altitudes = [np.linalg.norm(s.position_array()) - EARTH.RADIUS_KM for s in states]
    return min(altitudes), max(altitudes)

def coarse_filter(
    all_states: dict[str, list[PropagatedState]],
    margin_km: float = SCREENING.ALTITUDE_BAND_HALF_WIDTH_KM,
) -> list[tuple[str, str]]:
    """Return pairs of object IDs whose altitude bands overlap (sweep-line)."""
    # 1. Compute altitude band per object
    # 2. Sort by h_min
    # 3. Sweep-line: for each object, find all others with overlapping band
    # Complexity: O(n log n) sort + O(n·k) where k = avg overlaps
```

**Expected reduction**: ~500k pairs → ~10k–50k (90–98% reduction).

---

### 3. Stage 2: Fine Filter (`screening/fine_filter.py`)

#### Algorithm

Build a 3D spatial index per timestep from Stage 1 candidate positions.

For each timestep $t_k$:
1. Collect positions $\vec{r}_i(t_k)$ for candidate objects
2. Build `scipy.spatial.cKDTree`
3. `tree.query_pairs(r=10 km)` to find close pairs
4. Record pair, timestep, and distance

#### Implementation

```python
from scipy.spatial import cKDTree

def fine_filter_at_epoch(
    positions: np.ndarray,            # (N, 3) km, ECI
    object_ids: list[str],
    threshold_km: float = SCREENING.ENCOUNTER_SPHERE_RADIUS_KM,
) -> list[tuple[str, str, float]]:
    """Find all pairs within threshold distance at a single epoch."""
    tree = cKDTree(positions)
    pairs = tree.query_pairs(r=threshold_km, output_type='ndarray')
    # Return (id_i, id_j, distance) for each pair
```

**Complexity**: $O(n \log n)$ per timestep × 4,320 timesteps.

---

### 4. TCA Refinement (`screening/tca_refiner.py`)

#### Algorithm

Refine TCA between discrete 60s timesteps using cubic spline interpolation.

**Deduplication**: For each unique pair, collect all flagged timesteps, find the **global minimum** distance region, then interpolate to exact TCA.

```python
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar

def refine_tca(
    times_s: np.ndarray,
    distances_km: np.ndarray,
) -> tuple[float, float]:
    """Returns (tca_seconds, miss_distance_km)."""
    spline = CubicSpline(times_s, distances_km)
    result = minimize_scalar(spline, bounds=(times_s[0], times_s[-1]), method='bounded')
    return result.x, float(spline(result.x))

def interpolate_state_at_tca(
    times_s: np.ndarray,
    positions: np.ndarray,    # (T, 3) km
    velocities: np.ndarray,   # (T, 3) km/s
    tca_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate position and velocity at refined TCA."""
    pos_interp = CubicSpline(times_s, positions, axis=0)
    vel_interp = CubicSpline(times_s, velocities, axis=0)
    return pos_interp(tca_s), vel_interp(tca_s)
```

---

### 5. Encounter Frame Transform (`probability/encounter_frame.py`)

#### Mathematical Foundation

Encounter frame axes (right-handed orthonormal basis):

$$\hat{e}_w = \frac{\vec{v}_{\text{rel}}}{\|\vec{v}_{\text{rel}}\|}, \quad \hat{e}_n = \frac{\vec{v}_{\text{rel}} \times \vec{r}_{\text{rel}}}{\|\vec{v}_{\text{rel}} \times \vec{r}_{\text{rel}}\|}, \quad \hat{e}_t = \hat{e}_n \times \hat{e}_w$$

Rotation matrix ECI → encounter: $\mathbf{R} = [\hat{e}_t^T; \hat{e}_n^T; \hat{e}_w^T]$

Miss vector (B-plane): $\vec{b} = [\hat{e}_t \cdot \vec{r}_{\text{rel}}, \; \hat{e}_n \cdot \vec{r}_{\text{rel}}]$

Covariance projection: $\mathbf{C}_{\text{enc}} = \mathbf{P} \, (\mathbf{C}_{\text{pos},1} + \mathbf{C}_{\text{pos},2}) \, \mathbf{P}^T$ where $\mathbf{P} = [\hat{e}_t^T; \hat{e}_n^T]$ (2×3)

#### Implementation

```python
def compute_encounter_frame(r_rel, v_rel) -> np.ndarray:
    """Compute 3×3 rotation matrix from ECI to encounter frame."""
    e_w = v_rel / np.linalg.norm(v_rel)
    cross = np.cross(v_rel, r_rel)
    e_n = cross / np.linalg.norm(cross)
    e_t = np.cross(e_n, e_w)
    return np.vstack([e_t, e_n, e_w])

def project_to_encounter_plane(r_rel, cov_pos_combined, rotation):
    """Project to 2D encounter plane. Returns (b_vector(2,), cov_enc(2,2))."""
    r_enc = rotation @ r_rel
    b_vector = r_enc[:2]
    P = rotation[:2, :]
    cov_enc = P @ cov_pos_combined @ P.T
    return b_vector, cov_enc
```

---

### 6. Foster's 2D Pc Method (`probability/foster_2d.py`)

#### Mathematical Foundation

$$P_c = \frac{1}{2\pi\sqrt{\det \mathbf{C}_{\text{enc}}}} \iint_{u_T^2 + u_N^2 \le R_c^2} \exp\left(-\frac{1}{2}(\vec{u} - \vec{b})^T \mathbf{C}_{\text{enc}}^{-1} (\vec{u} - \vec{b})\right) du_T \, du_N$$

**Eigendecomposition approach**: $\mathbf{C}_{\text{enc}} = \mathbf{V}\mathbf{\Lambda}\mathbf{V}^T$, transform $\vec{b}' = \mathbf{V}^T\vec{b}$, integrate in principal axes.

#### Implementation

```python
from scipy.integrate import dblquad

def foster_2d_pc(b_vector, cov_enc, combined_radius_km) -> float:
    eigenvalues, eigenvectors = np.linalg.eigh(cov_enc)
    sigma1_sq, sigma2_sq = eigenvalues
    if sigma1_sq < 1e-12 or sigma2_sq < 1e-12:
        raise ValueError("Degenerate covariance — use Monte Carlo fallback")
    b_prime = eigenvectors.T @ b_vector

    def integrand(y, x):
        exp_term = (x - b_prime[0])**2 / (2*sigma1_sq) + (y - b_prime[1])**2 / (2*sigma2_sq)
        return np.exp(-exp_term) / (2 * np.pi * np.sqrt(sigma1_sq * sigma2_sq))

    def y_lower(x):
        return -np.sqrt(max(0, combined_radius_km**2 - x**2)) if abs(x) < combined_radius_km else 0.0
    def y_upper(x):
        return np.sqrt(max(0, combined_radius_km**2 - x**2)) if abs(x) < combined_radius_km else 0.0

    pc, _ = dblquad(integrand, -combined_radius_km, combined_radius_km,
                     y_lower, y_upper, epsabs=1e-12, epsrel=1e-10)
    return float(pc)
```

---

### 7. Monte Carlo Fallback (`probability/monte_carlo.py`)

#### Auto-Trigger Conditions

| Condition | Threshold | Reason |
|-----------|-----------|--------|
| Low relative velocity | $v_{\text{rel}} < 100$ m/s | Rectilinear motion assumption fails |
| Degenerate covariance | $\lambda_{\min} < 10^{-12}$ | Gaussian projection singular |
| Foster raises exception | Any `ValueError` / `LinAlgError` | Numerical failure |

#### Adaptive Sampling Implementation

```python
def monte_carlo_pc(r1, r2, cov1_pos, cov2_pos, combined_radius_km,
                    confidence=0.95, seed=42) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    
    # Phase 1: 10⁵ samples
    n_samples = 100_000
    pc, lower, upper = _run_mc(rng, r1, r2, cov1_pos, cov2_pos,
                                combined_radius_km, n_samples, confidence)
    
    # Phase 2: Escalate to 10⁶ if zero hits
    if pc == 0.0:
        n_samples = 1_000_000
        pc, lower, upper = _run_mc(rng, r1, r2, cov1_pos, cov2_pos,
                                    combined_radius_km, n_samples, confidence)
    
    return pc, lower, upper

def _run_mc(rng, r1, r2, cov1, cov2, radius, n, confidence):
    samples_r1 = rng.multivariate_normal(r1, cov1, size=n)
    samples_r2 = rng.multivariate_normal(r2, cov2, size=n)
    distances = np.linalg.norm(samples_r1 - samples_r2, axis=1)
    n_collisions = np.sum(distances <= radius)
    pc = n_collisions / n
    # Wilson score interval
    z = scipy.stats.norm.ppf(1 - (1 - confidence) / 2)
    denom = 1 + z**2 / n
    center = (pc + z**2 / (2 * n)) / denom
    half_width = z * np.sqrt(pc * (1-pc) / n + z**2 / (4*n**2)) / denom
    return pc, max(0, center - half_width), min(1, center + half_width)
```

---

### 8. Pc Engine with Auto-Method Selection (`probability/engine.py`)

```python
class PcEngine:
    def compute_pc(self, encounter: EncounterGeometry) -> PcResult:
        if self._should_use_foster(encounter):
            try:
                pc = foster_2d_pc(encounter.relative_position_enc,
                                   encounter.combined_covariance_enc,
                                   encounter.combined_hard_body_radius_km)
                return PcResult(pc=pc, method=PcMethod.FOSTER_2D)
            except (ValueError, np.linalg.LinAlgError):
                pass  # Fall through to Monte Carlo

        pc, lower, upper = monte_carlo_pc(
            encounter.primary_state.position_array(),
            encounter.secondary_state.position_array(),
            extract_position_covariance(encounter.primary_state.covariance_array()),
            extract_position_covariance(encounter.secondary_state.covariance_array()),
            encounter.combined_hard_body_radius_km)
        return PcResult(pc=pc, method=PcMethod.MONTE_CARLO,
                        confidence_lower=lower, confidence_upper=upper)

    def _should_use_foster(self, enc: EncounterGeometry) -> bool:
        if enc.relative_speed_km_s * 1000 < PC.FOSTER_MIN_VREL_MS:
            return False
        if enc.combined_covariance_enc is None:
            return False
        eigenvalues = np.linalg.eigvalsh(enc.combined_covariance_enc)
        if np.min(eigenvalues) < PC.COVARIANCE_SINGULARITY_TOL:
            return False
        return True
```

---

### 9. Pipeline Orchestrator (`pipeline.py`)

```python
class ConjunctionPipeline:
    """
    End-to-end: PropagatedEpochs → ConjunctionEvents.
    
    1. Coarse filter (altitude banding)
    2. Fine filter (k-d tree per timestep, 60s interval)
    3. Deduplicate: one event per pair at global min distance
    4. Two-tier Pc: full Pc for < 5 km, log-only for 5–10 km
    5. TCA refinement (spline interpolation)
    6. Encounter frame transform
    7. Pc computation (Foster 2D or Monte Carlo)
    8. Package as ConjunctionEvent
    """
    PC_COMPUTE_THRESHOLD_KM = 5.0   # Full Pc computation
    PC_LOG_ONLY_THRESHOLD_KM = 10.0  # Log but assign Pc ≈ 0

    def run(self, epoch_data: list[PropagatedEpoch]) -> list[ConjunctionEvent]:
        candidate_pairs = self.coarse_filter.run(epoch_data)
        raw_encounters = self.fine_filter.run(epoch_data, candidate_pairs)
        deduplicated = self._deduplicate(raw_encounters)  # One per pair

        events = []
        for encounter in deduplicated:
            if encounter.miss_distance_km > self.PC_LOG_ONLY_THRESHOLD_KM:
                continue  # Discard
            if encounter.miss_distance_km > self.PC_COMPUTE_THRESHOLD_KM:
                events.append(self._package_event(encounter, PcResult(pc=0.0)))
                continue  # Log only

            # Full Pc computation path
            refined = self.tca_refiner.refine(encounter)
            self.encounter_frame.compute(refined)
            pc_result = self.pc_engine.compute_pc(refined)
            events.append(self._package_event(refined, pc_result))

        return events
```

---

## Validation & Testing Strategy

### Synthetic Test Fixtures

| Fixture | Setup | Expected Result |
|---------|-------|-----------------|
| **Head-on** | 14 km/s relative velocity, 50m miss, σ ≈ 25m, R_c = 15m | Pc ≈ 10⁻² |
| **Grazing** | 1 km/s relative velocity, 200m miss, σ ≈ 100m, R_c = 15m | Pc ≈ 10⁻⁵ |
| **Clear miss** | 500 km miss, any covariance | Pc ≈ 0 |

### Cross-Validation

Run both Foster 2D and Monte Carlo on the **same** encounters. They must agree within 1 order of magnitude (MC variance permitting). This proves both methods are correctly implemented without needing external reference data.

### Unit Test Coverage

| Test File | What It Validates |
|-----------|-------------------|
| `test_coarse_filter.py` | Different altitudes excluded; overlapping bands kept |
| `test_fine_filter.py` | k-d tree identifies pairs within threshold; misses pairs outside |
| `test_encounter_frame.py` | Rotation matrix orthonormal; projection preserves geometry |
| `test_foster_2d.py` | Known head-on and co-planar Pc values; degenerate covariance raises error |
| `test_monte_carlo.py` | Convergence toward analytical Pc as N grows; confidence bounds contain true value |
| `test_pipeline.py` | End-to-end from PropagatedStates to ConjunctionEvents |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | ≥1.24 | Array operations, linear algebra |
| `scipy` | ≥1.11 | `cKDTree`, `CubicSpline`, `dblquad`, `minimize_scalar` |
| `pydantic` | ≥2.0 | Data validation, interface contracts |
| `loguru` | ≥0.7 | Structured logging |

---

## Key Mathematical Summary

### Encounter Plane Basis Vectors

$$\hat{e}_w = \frac{\vec{v}_{\text{rel}}}{\|\vec{v}_{\text{rel}}\|}, \quad \hat{e}_n = \frac{\vec{v}_{\text{rel}} \times \vec{r}_{\text{rel}}}{\|\vec{v}_{\text{rel}} \times \vec{r}_{\text{rel}}\|}, \quad \hat{e}_t = \hat{e}_n \times \hat{e}_w$$

### Miss Vector (B-plane)

$$\vec{b} = \begin{bmatrix} \hat{e}_t \cdot \vec{r}_{\text{rel}} \\ \hat{e}_n \cdot \vec{r}_{\text{rel}} \end{bmatrix}$$

### Covariance Projection

$$\mathbf{C}_{\text{enc}} = \mathbf{P} \, (\mathbf{C}_{\text{pos},1} + \mathbf{C}_{\text{pos},2}) \, \mathbf{P}^T, \quad \mathbf{P} = \begin{bmatrix} \hat{e}_t^T \\ \hat{e}_n^T \end{bmatrix}$$

### Foster 2D Pc Integral

$$P_c = \frac{1}{2\pi\sqrt{\det \mathbf{C}_{\text{enc}}}} \iint_{u_T^2 + u_N^2 \le R_c^2} \exp\left(-\frac{1}{2}(\vec{u} - \vec{b})^T \mathbf{C}_{\text{enc}}^{-1} (\vec{u} - \vec{b})\right) du_T \, du_N$$

### Monte Carlo Estimator

$$\hat{P}_c = \frac{1}{N}\sum_{k=1}^N \mathbf{1}\!\left[\|\vec{r}_1^{(k)} - \vec{r}_2^{(k)}\| \le R_c\right], \quad \vec{r}_i^{(k)} \sim \mathcal{N}(\vec{r}_i, \mathbf{C}_{\text{pos},i})$$
