const MODES = [
  { id: "dashboard", label: "Overview" },
  { id: "threat", label: "Threat Analysis" },
  { id: "launch", label: "Launch Planner" },
];

export default function TopBar({ mode, onChangeMode, overallRiskStatus }) {
  return (
    <aside className="navigation-rail hud-frame">
      <div className="brand-block">
        <strong className="brand-name">RADAR</strong>
        <span className="eyebrow">Space debris intelligence</span>
      </div>
      <span className="eyebrow nav-heading">Navigation</span>
      <nav className="mode-nav" aria-label="Primary navigation">
        {MODES.map((m) => {
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onChangeMode(m.id)}
              className={active ? "mode-button active" : "mode-button"}
            >
              {m.label}
            </button>
          );
        })}
      </nav>
      <div className="system-status">
        <span className={`status-dot risk-${overallRiskStatus === "elevated" ? "high" : overallRiskStatus}`} />
        <span className="mono">SYSTEM: ACTIVE</span>
      </div>
    </aside>
  );
}
