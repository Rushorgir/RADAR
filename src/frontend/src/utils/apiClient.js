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

/** GET /api/dashboard/summary -> { total_tracked_objects, total_conjunction_events, active_high_risk_alerts, risk_distribution, recent_high_risk_events } */
export function fetchDashboardSummary() {
  return getJson("/api/dashboard/summary");
}

/**
 * GET /api/tle/ -> { items: [{ object_id, object_name, object_type, line1, line2, epoch, ... }], total, page, size }
 * Requests the API's max page size (1000) -- the route defaults to 100,
 * which silently undercounts satellite/debris totals once the catalog
 * grows past that (bit us during dev: showed "10 satellites / 90 debris"
 * out of 829 real tracked objects, since that's exactly a 100-item page).
 */
export function fetchTLEs() {
  return getJson("/api/tle/?limit=1000");
}

/** GET /api/conjunctions/ -> { items: [{ event_id, primary_id, secondary_id, tca, miss_distance_km, relative_velocity_km_s, pc, pc_method, ml_risk_score, shap_top_features, maneuver_delta_v_m_s, ... }], total, page, size } */
export function fetchConjunctions() {
  return getJson("/api/conjunctions/?limit=1000");
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

export { API_BASE };
