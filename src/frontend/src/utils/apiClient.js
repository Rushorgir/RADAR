// Centralized HTTP client for the FastAPI backend (src/backend/).
//
// Base URL is configurable via VITE_API_BASE_URL (e.g. in a .env.local file);
// defaults to the backend's local dev port. See src/backend/api/main.py for
// the route definitions this calls.

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} -> ${res.status} ${res.statusText}`);
  }
  return res.json();
}

const PAGE_SIZE = 1000; // the backend's own hard ceiling (routes_tle.py/routes_conjunction.py: Query(..., le=1000))

/**
 * Fetches every item from a paginated `{ items, total, page, size }` endpoint,
 * looping pages until `total` is satisfied, instead of trusting a single
 * request with a large `limit`. A fixed "just ask for a big limit" number
 * silently truncates again the moment the catalog grows past it -- this bit
 * us twice already (the route's own 100-item default undercounted an
 * 829-object catalog, then a hardcoded limit=1000 undercounted again once
 * the catalog grew past 1000) -- so this fetches however many pages it
 * actually takes rather than picking another number to eventually outgrow.
 */
async function getAllPages(basePath) {
  const separator = basePath.includes("?") ? "&" : "?";
  const first = await getJson(`${basePath}${separator}limit=${PAGE_SIZE}&skip=0`);
  const items = [...first.items];
  while (items.length < first.total) {
    const page = await getJson(`${basePath}${separator}limit=${PAGE_SIZE}&skip=${items.length}`);
    if (page.items.length === 0) break; // guard against an unexpected total/items mismatch looping forever
    items.push(...page.items);
  }
  return { items, total: first.total };
}

async function postJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // FastAPI validation errors (422) carry a useful `detail` -- surface it
    // instead of just the generic status text so a bad request is
    // debuggable from the UI's error state alone.
    const detail = await res.json().catch(() => null);
    throw new Error(`POST ${path} -> ${res.status} ${detail?.detail ?? res.statusText}`);
  }
  return res.json();
}

/** GET /api/dashboard/summary -> { total_tracked_objects, total_conjunction_events, active_high_risk_alerts, risk_distribution, recent_high_risk_events } */
export function fetchDashboardSummary() {
  return getJson("/api/dashboard/summary");
}

/**
 * GET /api/tle/ (all pages) -> { items: [{ object_id, object_name, object_type, line1, line2, epoch, ... }], total }
 * Pages through the whole catalog -- see getAllPages for why this doesn't
 * just request one large limit.
 */
export function fetchTLEs() {
  return getAllPages("/api/tle/");
}

/** GET /api/conjunctions/ (all pages) -> { items: [{ event_id, primary_id, secondary_id, tca, miss_distance_km, relative_velocity_km_s, pc, pc_method, ml_risk_score, shap_top_features, maneuver_delta_v_m_s, ... }], total } */
export function fetchConjunctions() {
  return getAllPages("/api/conjunctions/");
}

/**
 * GET /api/tle/positions -> { epoch, requested, positions: [{ object_id, latitude_deg, longitude_deg, altitude_km }] }
 * Real SGP4-propagated "where is it right now" per object, computed live by
 * the backend from each object's latest stored TLE (src/propagation/current_positions.py).
 * `positions.length` can be less than `requested` if a handful of objects
 * fail to propagate (decayed, malformed elements) -- that's expected, not
 * an error; see liveData.js for the per-object placeholder fallback.
 */
export function fetchCurrentPositions() {
  return getJson("/api/tle/positions");
}

/**
 * GET /api/reentry/watch -> { epoch, objects_screened, predictions: [{ object_id, name, object_type,
 * perigee_altitude_km, apogee_altitude_km, risk_tier, estimated_days_to_reentry, sgp4_confirmed_decayed }] }
 * Real orbital-decay risk assessment (src/propagation/reentry.py), computed live from each
 * tracked object's own TLE elements -- only WATCH/ELEVATED/IMMINENT objects are returned,
 * not the whole catalog.
 */
export function fetchReentryWatch() {
  return getJson("/api/reentry/watch");
}

/** GET /api/launch/sites -> [{ name, latitude_deg, longitude_deg }] */
export function fetchLaunchSites() {
  return getJson("/api/launch/sites");
}

/**
 * POST /api/launch/safety-check { launch_site | (launch_lat_deg + launch_lon_deg), target_altitude_km, launch_time? }
 * -> { safe, waypoints, conflicts, objects_checked, safety_radius_km }
 * Checks a simplified ascent corridor against the real tracked catalog's SGP4-propagated
 * positions along the ascent timeline (src/propagation/launch_corridor.py).
 */
export function checkLaunchSafety(payload) {
  return postJson("/api/launch/safety-check", payload);
}

export { API_BASE };
