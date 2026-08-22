const FIELDS = [
  { key: "active_satellites", label: "Active Satellites" },
  { key: "tracked_debris", label: "Tracked Debris" },
  { key: "high_risk_objects", label: "High-Risk Objects" },
  { key: "affected_satellites", label: "Satellites at Risk" },
  { key: "active_missions", label: "Active Missions" },
];

export default function StatCluster({ stats }) {
  return (
    <aside className="intelligence-panel hud-frame">
      <div className="eyebrow panel-title">Intelligence // Overview</div>
      {FIELDS.map((f) => (
        <div className="metric-row" key={f.key}>
          <span className="eyebrow">{f.label}</span>
          <strong className="mono">{stats[f.key]}</strong>
        </div>
      ))}
    </aside>
  );
}
