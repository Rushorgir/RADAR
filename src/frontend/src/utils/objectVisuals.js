const COLORS = {
  satellite: "#35D9FF",
  low: "#8A9BAA",
  medium: "#FFB020",
  high: "#FF6333",
  critical: "#FF3030",
};

const RISK_META = {
  low: { label: "Low risk", color: COLORS.low, cssVar: "--risk-low" },
  medium: { label: "Medium risk", color: COLORS.medium, cssVar: "--risk-medium" },
  high: { label: "High risk", color: COLORS.high, cssVar: "--risk-high" },
  critical: { label: "Critical risk", color: COLORS.critical, cssVar: "--risk-critical" },
};

export function getVisualRiskTier(object) {
  if (object?.type !== "debris") return "satellite";
  const tier = String(object.risk_tier || "low").toLowerCase();
  if (tier === "critical") return "critical";
  if (tier === "elevated" || tier === "high") return "high";
  if (tier === "medium") return "medium";
  return "low";
}

export function getVisualMeta(object) {
  const tier = getVisualRiskTier(object);
  return tier === "satellite"
    ? { label: "Satellite", color: COLORS.satellite, cssVar: "--risk-satellite" }
    : RISK_META[tier];
}

function svgDataUri(svg) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function satelliteSvg(color) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
    <g fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round">
      <rect x="19" y="19" width="10" height="10" rx="1" fill="#07131c"/>
      <rect x="2" y="20" width="14" height="8" fill="#07131c"/>
      <rect x="32" y="20" width="14" height="8" fill="#07131c"/>
      <path d="M16 24h3M29 24h3M24 19V8M24 29v11"/>
      <path d="M21 8h6M21 40h6"/>
    </g>
    <circle cx="24" cy="24" r="2.5" fill="${color}"/>
  </svg>`;
}

function debrisSvg(color, risk) {
  const warning = risk === "high" || risk === "critical";
  const badgeSize = risk === "critical" ? 13 : 10;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
    <g transform="translate(5 7)" fill="${color}" stroke="${color}" stroke-linejoin="round">
      <path d="M8 25 2 17l7-10 10 3 8-6 8 8-4 11-10 7Z" fill="#080b12" stroke-width="2"/>
      <path d="m9 9 10 3-3 11-8 2-4-8Z" fill="${color}" opacity=".85" stroke="none"/>
      <path d="m19 12 8-5 5 5-8 8Z" fill="${color}" opacity=".55" stroke="none"/>
    </g>
    ${warning ? `<circle cx="37" cy="11" r="${badgeSize / 2 + 2}" fill="#080b12" stroke="${color}" stroke-width="1.5"/><text x="37" y="16" text-anchor="middle" fill="${color}" font-family="Arial,sans-serif" font-size="${badgeSize}" font-weight="700">!</text>` : ""}
  </svg>`;
}

function ringSvg(color, dashed = false) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="24" fill="none" stroke="${color}" stroke-width="1.5" ${dashed ? 'stroke-dasharray="4 4"' : ""}/><circle cx="32" cy="32" r="28" fill="none" stroke="${color}" stroke-width=".7" opacity=".55" ${dashed ? 'stroke-dasharray="1 7"' : ""}/></svg>`;
}

const iconCache = new Map();
export function getObjectIcon(object) {
  const tier = getVisualRiskTier(object);
  const key = `icon:${tier}`;
  if (!iconCache.has(key)) {
    iconCache.set(key, svgDataUri(tier === "satellite" ? satelliteSvg(COLORS.satellite) : debrisSvg(COLORS[tier], tier)));
  }
  return iconCache.get(key);
}

export function getSelectionRing(object) {
  const meta = getVisualMeta(object);
  const key = `selection:${meta.color}`;
  if (!iconCache.has(key)) iconCache.set(key, svgDataUri(ringSvg(meta.color)));
  return iconCache.get(key);
}

export function getWarningRing(object) {
  const tier = getVisualRiskTier(object);
  const meta = getVisualMeta(object);
  const key = `warning:${tier}`;
  if (!iconCache.has(key)) iconCache.set(key, svgDataUri(ringSvg(meta.color, true)));
  return iconCache.get(key);
}

export function getBaseIconScale(object) {
  const tier = getVisualRiskTier(object);
  if (tier === "satellite") return 0.52;
  if (tier === "critical") return 0.52;
  if (tier === "high") return 0.44;
  if (tier === "medium") return 0.36;
  return 0.27;
}

export function isAnimatedRisk(object) {
  const tier = getVisualRiskTier(object);
  return tier === "medium" || tier === "high" || tier === "critical";
}

export function getTooltipData(object) {
  const meta = getVisualMeta(object);
  return {
    object,
    label: meta.label,
    color: meta.color,
    id: object?.name ?? `OBJ-${object?.object_id ?? "—"}`,
    type: object?.type === "satellite" ? "SATELLITE" : `${meta.label.toUpperCase()} DEBRIS`,
    altitude: typeof object?.altitude_km === "number" ? `${object.altitude_km.toFixed(0)} KM` : "—",
    velocity: typeof object?.velocity_km_s === "number" && Number.isFinite(object.velocity_km_s) ? `${object.velocity_km_s.toFixed(1)} KM/S` : "—",
  };
}
