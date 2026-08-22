// Mock data shaped to match the interface contract in the team execution plan:
// AI-1 -> AI-2: state vectors (position, velocity, epoch, covariance) per object
// AI-2 -> AI-3: conjunction events (miss distance, rel. velocity, Pc, metadata)
// AI-3 -> Web:  ranked risk list (Pc, ML risk score, SHAP top-3, maneuver advisory)
//
// Swap the functions below for real fetch() calls once Web's FastAPI endpoints
// are live -- keep the exact same shape so components never need to change.

function rand(min, max) {
  return Math.random() * (max - min) + min;
}

function makeObject(id, type, riskTier) {
  return {
    object_id: id,
    name: type === "satellite" ? `SAT-${id}` : `DEB-${id}`,
    type, // "satellite" | "debris"
    regime: "LEO",
    longitude: rand(-180, 180),
    latitude: rand(-70, 70),
    altitude_km: rand(400, 1200),
    cross_sectional_area_m2: type === "satellite" ? rand(2, 12) : rand(0.01, 1.5),
    risk_tier: riskTier, // "critical" | "elevated" | "nominal"
  };
}

export const mockObjects = [
  ...Array.from({ length: 14 }, (_, i) => makeObject(1000 + i, "satellite", "nominal")),
  ...Array.from({ length: 55 }, (_, i) => makeObject(2000 + i, "debris", "nominal")),
  makeObject(2101, "debris", "critical"),
  makeObject(2102, "debris", "critical"),
  makeObject(2103, "debris", "elevated"),
  makeObject(2104, "debris", "elevated"),
  makeObject(1010, "satellite", "critical"),
  makeObject(1011, "satellite", "elevated"),
];

export const mockRiskList = [
  {
    event_id: "CDM-0091",
    primary_id: 1010,
    primary_name: "SAT-1010",
    secondary_id: 2101,
    secondary_name: "DEB-2101",
    pc: 3.2e-3,
    risk_score: 0.94,
    risk_tier: "critical",
    miss_distance_km: 0.42,
    relative_velocity_kms: 11.7,
    time_to_closest_approach_hr: 6.2,
    regime: "LEO",
    shap_top3: [
      { feature: "miss_distance", contribution: 0.41 },
      { feature: "relative_velocity", contribution: 0.27 },
      { feature: "combined_covariance", contribution: 0.18 },
    ],
    maneuver_advisory: {
      delta_v_ms: 0.083,
      direction: "radial",
      resulting_miss_distance_km: 4.1,
    },
  },
  {
    event_id: "CDM-0088",
    primary_id: 1011,
    primary_name: "SAT-1011",
    secondary_id: 2102,
    secondary_name: "DEB-2102",
    pc: 8.7e-4,
    risk_score: 0.71,
    risk_tier: "elevated",
    miss_distance_km: 1.1,
    relative_velocity_kms: 9.4,
    time_to_closest_approach_hr: 14.8,
    regime: "LEO",
    shap_top3: [
      { feature: "relative_velocity", contribution: 0.33 },
      { feature: "miss_distance", contribution: 0.31 },
      { feature: "object_area", contribution: 0.12 },
    ],
    maneuver_advisory: {
      delta_v_ms: 0.041,
      direction: "along-track",
      resulting_miss_distance_km: 3.6,
    },
  },
  {
    event_id: "CDM-0075",
    primary_id: 1010,
    primary_name: "SAT-1010",
    secondary_id: 2103,
    secondary_name: "DEB-2103",
    pc: 6.1e-5,
    risk_score: 0.38,
    risk_tier: "elevated",
    miss_distance_km: 3.8,
    relative_velocity_kms: 7.9,
    time_to_closest_approach_hr: 27.3,
    regime: "LEO",
    shap_top3: [
      { feature: "miss_distance", contribution: 0.44 },
      { feature: "orbital_regime", contribution: 0.2 },
      { feature: "object_area", contribution: 0.09 },
    ],
    maneuver_advisory: null,
  },
  {
    event_id: "CDM-0061",
    primary_id: 1004,
    primary_name: "SAT-1004",
    secondary_id: 2104,
    secondary_name: "DEB-2104",
    pc: 2.0e-5,
    risk_score: 0.19,
    risk_tier: "nominal",
    miss_distance_km: 6.2,
    relative_velocity_kms: 5.1,
    time_to_closest_approach_hr: 40.1,
    regime: "LEO",
    shap_top3: [
      { feature: "miss_distance", contribution: 0.51 },
      { feature: "relative_velocity", contribution: 0.19 },
      { feature: "combined_covariance", contribution: 0.08 },
    ],
    maneuver_advisory: null,
  },
];

export const mockDashboardStats = {
  active_satellites: 14,
  tracked_debris: 59,
  high_risk_objects: 2,
  affected_satellites: 2,
  overall_risk_status: "elevated", // "nominal" | "elevated" | "critical"
  active_missions: 3,
};

export function getRiskColorVar(tier) {
  if (tier === "critical") return "var(--risk-critical)";
  if (tier === "elevated") return "var(--risk-elevated)";
  return "var(--risk-nominal)";
}
