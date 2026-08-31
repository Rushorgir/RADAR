const RISK_META = {
  critical: { label: "Critical", color: "var(--risk-critical)" },
  high: { label: "High", color: "var(--risk-elevated)" },
  medium: { label: "Medium", color: "var(--risk-medium)" },
  low: { label: "Low", color: "var(--risk-nominal)" },
};

export function normalizeId(value) {
  return value === null || value === undefined ? "" : String(value);
}

export function getRiskMeta(tier, score) {
  const normalized = String(tier || "").toLowerCase();
  if (normalized === "critical") return RISK_META.critical;
  if (normalized === "elevated" || normalized === "high") return RISK_META.high;
  if (normalized === "medium") return RISK_META.medium;
  if (normalized === "nominal" || normalized === "low") return RISK_META.low;
  if (Number(score) >= 0.85) return RISK_META.critical;
  if (Number(score) >= 0.5) return RISK_META.high;
  if (Number(score) >= 0.2) return RISK_META.medium;
  return RISK_META.low;
}

function eventForObject(object, riskList) {
  const objectId = normalizeId(object.object_id);
  return riskList
    .filter((event) => [event.primary_id, event.secondary_id].some((id) => normalizeId(id) === objectId))
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0) || (b.pc ?? 0) - (a.pc ?? 0))[0];
}

export function buildObjectDetail(object, riskList) {
  if (!object) return null;
  const event = eventForObject(object, riskList);
  const hasEvent = !!event;
  const score = hasEvent ? (event.risk_score ?? object.risk_score) : "0.00 (Nominal)";
  const risk = getRiskMeta(object.risk_tier ?? event?.risk_tier ?? "nominal", hasEvent ? score : 0);
  const velocity = object.velocity_km_s;
  const relativeVelocity = hasEvent ? event?.relative_velocity_kms : "N/A (No Threat)";

  const objectId = normalizeId(object.object_id);
  const atRiskDebrisCount = riskList.filter((e) => {
    if (normalizeId(e.primary_id) === objectId && String(e.secondary_object_type).toUpperCase() === "DEBRIS") return true;
    if (normalizeId(e.secondary_id) === objectId && String(e.primary_object_type).toUpperCase() === "DEBRIS") return true;
    return false;
  }).length;

  return {
    id: objectId,
    name: object.name ?? "Unknown object",
    type: object.type ?? "unknown",
    regime: object.regime ?? "UNASSESSED",
    riskScore: score,
    collisionProbability: hasEvent ? event.pc : "< 1.00e-8 (Clear)",
    missDistance: hasEvent ? event.miss_distance_km : "> 10.00 (Safe Separation)",
    velocity,
    relativeVelocity,
    risk,
    eventId: event?.event_id,
    atRiskDebrisCount,
    hasEvent,
    shapTop3: event?.shap_top3 ?? [],
    maneuverAdvisory: event?.maneuver_advisory ?? null,
    timeToClosestApproachHr: event?.time_to_closest_approach_hr ?? null,
  };
}

export function formatNumber(value, digits = 2) {
  if (typeof value === "string") return value;
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

export function formatProbability(value) {
  if (typeof value === "string") return value;
  return typeof value === "number" && Number.isFinite(value) ? value.toExponential(2) : "—";
}

