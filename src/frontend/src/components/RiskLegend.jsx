import { getObjectIcon } from "../utils/objectVisuals";

const RISK_LEVELS = [
  ["critical", "Critical"],
  ["high", "High"],
  ["medium", "Medium"],
  ["low", "Low"],
];

export default function RiskLegend() {
  return (
    <div className="risk-legend hud-frame" aria-label="Risk status legend">
      <span className="eyebrow legend-title">Risk status</span>
      <span className="legend-item">
        <img className="legend-icon" src={getObjectIcon({ type: "satellite" })} alt="" aria-hidden="true" />
        <span className="mono">Satellite</span>
      </span>
      {RISK_LEVELS.map(([level, label]) => (
        <span className="legend-item" key={level}>
          <img
            className="legend-icon"
            src={getObjectIcon({ type: "debris", risk_tier: level })}
            alt=""
            aria-hidden="true"
          />
          <span className="mono">{label}</span>
        </span>
      ))}
    </div>
  );
}
