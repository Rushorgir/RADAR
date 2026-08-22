const FIELDS = [
  { key: "active_satellites", label: "Active Satellites" },
  { key: "tracked_debris", label: "Tracked Debris" },
  { key: "high_risk_objects", label: "High-Risk Objects" },
  { key: "affected_satellites", label: "Satellites at Risk" },
  { key: "active_missions", label: "Active Missions" },
];

export default function StatCluster({ stats, activeFilters, onToggleFilter, onSelectAll }) {
  return (
    <aside className="intelligence-panel hud-frame">
      <div className="panel-heading">
        <div className="eyebrow panel-title">Intelligence // Overview</div>
        <button type="button" className="select-all-button" onClick={onSelectAll}>Select all</button>
      </div>
      {FIELDS.map((f) => (
        <button
          type="button"
          className={`metric-row ${activeFilters.includes(f.key) ? "selected" : ""}`}
          key={f.key}
          onClick={() => onToggleFilter(f.key)}
          aria-pressed={activeFilters.includes(f.key)}
        >
          <span className="eyebrow">{f.label}</span>
          <strong className="mono">{stats[f.key]}</strong>
        </button>
      ))}
      {activeFilters.length > 0 && <div className="filter-hint eyebrow">Showing selected object groups</div>}
    </aside>
  );
}
