// Centralized HTTP client for the FastAPI backend (src/backend/).
//
// Base URL is configurable via VITE_API_BASE_URL (e.g. in a .env.local file);
// defaults to the backend's local dev port. See src/backend/api/main.py for
// the route definitions this calls.

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

let currentDataset = "default";

export function setDataset(dataset) {
  currentDataset = dataset;
}

export function getDataset() {
  return currentDataset;
}

function appendDataset(path, explicitDataset) {
  const ds = explicitDataset || currentDataset;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}dataset=${encodeURIComponent(ds)}`;
}

async function getJson(path, explicitDataset) {
  const finalPath = appendDataset(path, explicitDataset);
  const res = await fetch(`${API_BASE}${finalPath}`);
  if (!res.ok) {
    throw new Error(`GET ${path} -> ${res.status} ${res.statusText}`);
  }
  return res.json();
}

const PAGE_SIZE = 1000; // the backend's own hard ceiling (routes_tle.py/routes_conjunction.py: Query(..., le=1000))

async function getAllPages(basePath, explicitDataset) {
  const separator = basePath.includes("?") ? "&" : "?";
  const first = await getJson(`${basePath}${separator}limit=${PAGE_SIZE}&skip=0`, explicitDataset);
  const items = [...first.items];
  while (items.length < first.total) {
    const page = await getJson(`${basePath}${separator}limit=${PAGE_SIZE}&skip=${items.length}`, explicitDataset);
    if (page.items.length === 0) break; // guard against an unexpected total/items mismatch looping forever
    items.push(...page.items);
  }
  return { items, total: first.total };
}

async function postJson(path, body, explicitDataset) {
  const finalPath = appendDataset(path, explicitDataset);
  const res = await fetch(`${API_BASE}${finalPath}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(`POST ${path} -> ${res.status} ${detail?.detail ?? res.statusText}`);
  }
  return res.json();
}

/** GET /api/dashboard/summary -> { total_tracked_objects, total_conjunction_events, active_high_risk_alerts, risk_distribution, recent_high_risk_events } */
export function fetchDashboardSummary(dataset) {
  return getJson("/api/dashboard/summary", dataset);
}

/**
 * GET /api/tle/ (all pages) -> { items: [{ object_id, object_name, object_type, line1, line2, epoch, ... }], total }
 */
export function fetchTLEs(dataset) {
  return getAllPages("/api/tle/", dataset);
}

/** GET /api/conjunctions/ (all pages) -> { items: [{ event_id, primary_id, secondary_id, tca, miss_distance_km, relative_velocity_km_s, pc, pc_method, ml_risk_score, shap_top_features, maneuver_delta_v_m_s, ... }], total } */
export function fetchConjunctions(dataset) {
  return getAllPages("/api/conjunctions/", dataset);
}

/**
 * GET /api/tle/positions[?at=<ISO8601>] -> { epoch, requested, positions: [{ object_id, latitude_deg, longitude_deg, altitude_km }] }
 */
export function fetchCurrentPositions(at, dataset) {
  const query = at ? `?at=${encodeURIComponent(at.toISOString())}` : "";
  return getJson(`/api/tle/positions${query}`, dataset);
}

/**
 * GET /api/reentry/watch -> { epoch, objects_screened, predictions: [{ object_id, name, object_type,
 * perigee_altitude_km, apogee_altitude_km, risk_tier, estimated_days_to_reentry, sgp4_confirmed_decayed }] }
 */
export function fetchReentryWatch(dataset) {
  return getJson("/api/reentry/watch", dataset);
}

/** GET /api/launch/sites -> [{ name, latitude_deg, longitude_deg }] */
export function fetchLaunchSites(dataset) {
  return getJson("/api/launch/sites", dataset);
}

/**
 * POST /api/launch/safety-check { launch_site | (launch_lat_deg + launch_lon_deg), target_altitude_km, launch_time? }
 */
export function checkLaunchSafety(payload, dataset) {
  return postJson("/api/launch/safety-check", payload, dataset);
}

export { API_BASE };

export function fetchDatasets() {
  return getJson("/api/datasets/");
}

export async function deleteDatasetApi(datasetName) {
  const res = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetName)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(`DELETE /api/datasets/${datasetName} -> ${res.status} ${detail?.detail ?? res.statusText}`);
  }
  return res.json();
}
