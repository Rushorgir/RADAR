const FIELDS = [
  { key: "active_satellites", label: "Active Satellites" },
  { key: "tracked_debris", label: "Tracked Debris" },
  { key: "high_risk_objects", label: "High-Risk Objects" },
  { key: "affected_satellites", label: "Satellites at Risk" },
  { key: "active_missions", label: "Active Missions" },
];

export default function StatCluster({ stats }) {
  return (
    <div
      className="hud-frame"
      style={{
        position: "absolute",
        left: 18,
        bottom: 18,
        zIndex: 20,
        display: "flex",
        gap: 0,
        padding: "16px 0",
      }}
    >
      {FIELDS.map((f, i) => (
        <div
          key={f.key}
          style={{
            padding: "0 22px",
            borderLeft: i === 0 ? "none" : "1px solid var(--hairline)",
            minWidth: 108,
          }}
        >
          <div
            className="mono"
            style={{ fontSize: 26, fontWeight: 600, color: "var(--text-primary)", lineHeight: 1 }}
          >
            {stats[f.key]}
          </div>
          <div className="eyebrow" style={{ marginTop: 8 }}>
            {f.label}
          </div>
        </div>
      ))}
    </div>
  );
}
