// Adapts real backend responses (src/backend/) into the exact shapes
// src/data/mockData.js already defines, so GlobeView / RiskPanel / StatCluster
// / ObjectDetailPanel need no changes to consume real data -- this is the
// "swap for real fetch() calls, keep the exact same shape" migration the
// mockData.js file comment originally called for.
//
// What's genuinely real here: object identities/types/counts (from AI-1's
// ingestion), conjunction geometry and Pc (from AI-2's screening/probability
// engines), all served live through the FastAPI backend.
//
// What's still a placeholder, and why: AI-3 (ML risk ranking, SHAP,
// maneuver advisory) hasn't been built yet, so `ml_risk_score`,
// `shap_top_features`, and the maneuver_* fields are `null` from the
// backend today -- this file passes them through as-is (empty/nominal
// defaults) rather than fabricating fake ML output, and the schema is
// already ML-ready (src/backend/schemas/api_schemas.py) so real values
// will show up automatically once AI-3 lands, with no frontend change
// needed.
//
// Globe positions ARE now real: GET /api/tle/positions runs live SGP4
// propagation server-side (src/propagation/current_positions.py) for every
// tracked object's latest TLE. It's fetched best-effort, separately from
// the rest of the live data -- if it fails, or a specific object's SGP4
// propagation fails (decayed, malformed elements), that object falls back
// to the old deterministic placeholder position rather than the whole
// dashboard falling back to mock data over a globe-only issue.

import { fetchConjunctions, fetchCurrentPositions, fetchTLEs, fetchDashboardSummary } from "./apiClient";
import { mockObjects, mockRiskList, mockDashboardStats } from "../data/mockData";


// Same thresholds as src/shared/constants/physical.py PcThresholds, so the
// frontend's risk-tier coloring agrees with the backend/AI-2's own notion
// of "high" vs "medium" risk instead of inventing a separate scale.
const PC_HIGH_RISK = 1.0e-4;
const PC_MEDIUM_RISK = 1.0e-6;

function riskTierFromPc(pc) {
  if (pc >= PC_HIGH_RISK) return "critical";
  if (pc >= PC_MEDIUM_RISK) return "elevated";
  return "nominal";
}

// Deterministic pseudo-position from an id, so a given object stays put
// across re-renders/refetches instead of jumping around. Fallback ONLY for
// an object GET /api/tle/positions didn't return a real position for (see
// the file-level comment) -- NOT the primary source of truth anymore.
function stablePosition(seed) {
  let h = 0;
  for (const ch of String(seed)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const longitude = (h % 3600) / 10 - 180; // -180..180
  const latitude = ((h >> 8) % 1400) / 10 - 70; // -70..70
  const altitude_km = 400 + ((h >> 16) % 8000) / 10; // 400..1200
  return { longitude, latitude, altitude_km };
}

function objectTypeToGlobeType(objectType) {
  // Anything that isn't a confirmed active payload reads as "debris" for
  // this satellite-vs-debris visualization -- catches ROCKET_BODY and
  // UNKNOWN (Celestrak's "analyst" group: real tracked fragments it can't
  // yet confidently identify) the same way DEBRIS already was, rather than
  // defaulting them to "satellite" just because they aren't literally
  // tagged DEBRIS.
  return objectType === "PAYLOAD" ? "satellite" : "debris";
}

/** Real TLE list -> mockObjects shape (src/data/mockData.js). */
export function tlesToObjects(tles, riskTierByObjectId, positionByObjectId = new Map()) {
  return tles.map((tle) => {
    const realPosition = positionByObjectId.get(String(tle.object_id));
    const position = realPosition
      ? { longitude: realPosition.longitude_deg, latitude: realPosition.latitude_deg, altitude_km: realPosition.altitude_km }
      : stablePosition(tle.object_id);
    return {
      object_id: tle.object_id,
      name: tle.object_name || `OBJ-${tle.object_id}`,
      type: objectTypeToGlobeType(tle.object_type),
      regime: "LEO",
      ...position,
      velocity_km_s: realPosition?.velocity_km_s,
      cross_sectional_area_m2: null,
      risk_tier: riskTierByObjectId.get(String(tle.object_id)) ?? "nominal",
    };
  });
}

/** Real conjunction events -> mockRiskList shape (src/data/mockData.js). */
export function conjunctionsToRiskList(events, nameByObjectId) {
  return events.map((event) => ({
    // Real event_id is a full UUID (backend/src/shared/interfaces/contracts.py) --
    // fine as a stable React key, but RiskPanel's layout was built around
    // short mock ids like "CDM-0091" and a full UUID crowds/wraps the
    // object-name pair next to it. Shorten for display only.
    event_id: `CDM-${event.event_id.slice(0, 8)}`,
    primary_id: event.primary_id,
    primary_name: nameByObjectId.get(String(event.primary_id)) ?? `OBJ-${event.primary_id}`,
    secondary_id: event.secondary_id,
    secondary_name: nameByObjectId.get(String(event.secondary_id)) ?? `OBJ-${event.secondary_id}`,
    pc: event.pc,
    risk_score: event.ml_risk_score ?? 0,
    risk_tier: riskTierFromPc(event.pc),
    miss_distance_km: event.miss_distance_km,
    relative_velocity_kms: event.relative_velocity_km_s,
    primary_object_type: event.primary_object_type,
    secondary_object_type: event.secondary_object_type,
    time_to_closest_approach_hr: (new Date(event.tca).getTime() - Date.now()) / 3.6e6,
    regime: "LEO",
    // AI-3 not built yet -- always [] (never null/undefined), since
    // RiskPanel calls .map() on this unconditionally.
    shap_top3: (event.shap_top_features ?? []).map((f) => ({
      feature: f.feature,
      contribution: f.impact,
    })),
    maneuver_advisory: event.maneuver_delta_v_m_s == null ? null : {
      delta_v_ms: event.maneuver_delta_v_m_s,
      direction: event.maneuver_burn_direction,
      resulting_miss_distance_km: event.maneuver_new_miss_distance_km,
    },
  }));
}

/** Real dashboard summary + TLE type counts -> mockDashboardStats shape. */
export function buildDashboardStats(summary, tles) {
  const activeSatellites = tles.filter((t) => t.object_type === "PAYLOAD").length;
  // Everything not a confirmed active payload -- DEBRIS, ROCKET_BODY, and
  // UNKNOWN (Celestrak's "analyst" group of uncatalogued fragments) -- so
  // this always sums with active_satellites back to the real total instead
  // of silently undercounting whenever a non-DEBRIS, non-PAYLOAD type shows
  // up in the catalog.
  const trackedDebris = tles.length - activeSatellites;
  const highRisk = summary.risk_distribution?.HIGH ?? 0;
  return {
    active_satellites: activeSatellites,
    tracked_debris: trackedDebris,
    high_risk_objects: highRisk,
    affected_satellites: summary.active_high_risk_alerts ?? 0,
    overall_risk_status: highRisk > 0 ? "critical" : summary.total_conjunction_events > 0 ? "elevated" : "nominal",
    active_missions: activeSatellites,
  };
}

/**
 * Fetch everything the dashboard needs from the real backend and reshape it
 * into mockData.js's exact shapes. Throws if the backend is unreachable --
 * callers should catch this and fall back to mock data (see App.jsx).
 */
export async function loadLiveDashboardData(dataset) {
  const [summary, tleResponse, conjunctionResponse, positionsResponse] = await Promise.all([
    fetchDashboardSummary(dataset),
    fetchTLEs(dataset),
    fetchConjunctions(dataset),
    // Best-effort, on its own catch: a positions-endpoint hiccup should
    // degrade to placeholder positions for the globe, not take down the
    // whole live dashboard (which is what a shared Promise.all rejection
    // would do).
    fetchCurrentPositions(undefined, dataset).catch((err) => {
      console.warn("[RADAR] Live positions unavailable, using placeholder positions:", err.message);
      return { positions: [] };
    }),
  ]);

  const tles = tleResponse.items ?? [];
  const events = conjunctionResponse.items ?? [];

  if (tles.length === 0) {
    return {
      objects: mockObjects,
      riskList: mockRiskList,
      dashboardStats: mockDashboardStats,
    };
  }

  const positionByObjectId = new Map(
    (positionsResponse.positions ?? []).map((p) => [String(p.object_id), p])
  );

  const nameByObjectId = new Map(tles.map((t) => [String(t.object_id), t.object_name || `OBJ-${t.object_id}`]));
  const riskTierByObjectId = new Map();
  for (const event of events) {
    const tier = riskTierFromPc(event.pc);
    for (const id of [event.primary_id, event.secondary_id]) {
      const existing = riskTierByObjectId.get(String(id));
      // Keep the worst tier seen if an object appears in multiple events.
      if (!existing || tierRank(tier) > tierRank(existing)) {
        riskTierByObjectId.set(String(id), tier);
      }
    }
  }

  return {
    objects: tlesToObjects(tles, riskTierByObjectId, positionByObjectId),
    riskList: conjunctionsToRiskList(events, nameByObjectId),
    dashboardStats: buildDashboardStats(summary, tles),
  };
}

function tierRank(tier) {
  return tier === "critical" ? 2 : tier === "elevated" ? 1 : 0;
}
