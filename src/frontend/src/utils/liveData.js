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
// needed. Similarly, real-time lat/lon/altitude for the globe requires
// propagating each TLE (SGP4), which no endpoint returns yet and no
// client-side propagator is wired up for -- positions here are a stable
// per-object placeholder (deterministic from object_id, not random per
// render) until that exists.

import { fetchConjunctions, fetchTLEs, fetchDashboardSummary } from "./apiClient";

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
// across re-renders/refetches instead of jumping around. NOT a real orbital
// position -- see the file-level comment.
function stablePosition(seed) {
  let h = 0;
  for (const ch of String(seed)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const longitude = (h % 3600) / 10 - 180; // -180..180
  const latitude = ((h >> 8) % 1400) / 10 - 70; // -70..70
  const altitude_km = 400 + ((h >> 16) % 8000) / 10; // 400..1200
  return { longitude, latitude, altitude_km };
}

function objectTypeToGlobeType(objectType) {
  return objectType === "DEBRIS" ? "debris" : "satellite";
}

/** Real TLE list -> mockObjects shape (src/data/mockData.js). */
export function tlesToObjects(tles, riskTierByObjectId) {
  return tles.map((tle) => ({
    object_id: tle.object_id,
    name: tle.object_name || `OBJ-${tle.object_id}`,
    type: objectTypeToGlobeType(tle.object_type),
    regime: "LEO",
    ...stablePosition(tle.object_id),
    cross_sectional_area_m2: null,
    risk_tier: riskTierByObjectId.get(String(tle.object_id)) ?? "nominal",
  }));
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
  const trackedDebris = tles.filter((t) => t.object_type === "DEBRIS").length;
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
export async function loadLiveDashboardData() {
  const [summary, tleResponse, conjunctionResponse] = await Promise.all([
    fetchDashboardSummary(),
    fetchTLEs(),
    fetchConjunctions(),
  ]);

  const tles = tleResponse.items ?? [];
  const events = conjunctionResponse.items ?? [];

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
    objects: tlesToObjects(tles, riskTierByObjectId),
    riskList: conjunctionsToRiskList(events, nameByObjectId),
    dashboardStats: buildDashboardStats(summary, tles),
  };
}

function tierRank(tier) {
  return tier === "critical" ? 2 : tier === "elevated" ? 1 : 0;
}
