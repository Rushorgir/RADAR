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
      {RISK_LEVELS.map(([level, label]) => (
        <span className="legend-item" key={level}>
          <span className={`legend-dot risk-${level}`} />
          <span className="mono">{label}</span>
        </span>
      ))}
    </div>
  );
}
