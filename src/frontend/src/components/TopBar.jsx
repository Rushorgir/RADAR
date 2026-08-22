const MODES = [
  { id: "dashboard", label: "Overview" },
  { id: "threat", label: "Threat Analysis" },
  { id: "launch", label: "Launch Planner" },
];

export default function TopBar({ mode, onChangeMode, overallRiskStatus }) {
  return (
    <div
      style={{
        position: "absolute",
        top: 18,
        left: 18,
        right: 18,
        zIndex: 20,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        pointerEvents: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, pointerEvents: "auto" }}>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: 18,
            letterSpacing: "0.02em",
          }}
        >
          RADAR
        </span>
        <span className="eyebrow">// COLLISION RISK CONSOLE</span>
      </div>

      <div
        className="hud-frame"
        style={{
          display: "flex",
          gap: 2,
          padding: 4,
          pointerEvents: "auto",
        }}
      >
        {MODES.map((m) => {
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onChangeMode(m.id)}
              style={{
                background: active ? "var(--signal-dim)" : "transparent",
                color: active ? "var(--signal)" : "var(--text-secondary)",
                border: "none",
                borderRadius: 2,
                padding: "8px 14px",
                fontFamily: "var(--font-mono)",
                fontSize: 11.5,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                transition: "background 120ms ease, color 120ms ease",
              }}
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <div
        className="hud-frame"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 14px",
          pointerEvents: "auto",
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background:
              overallRiskStatus === "critical"
                ? "var(--risk-critical)"
                : overallRiskStatus === "elevated"
                ? "var(--risk-elevated)"
                : "var(--risk-nominal)",
            boxShadow: `0 0 8px ${
              overallRiskStatus === "critical"
                ? "var(--risk-critical)"
                : overallRiskStatus === "elevated"
                ? "var(--risk-elevated)"
                : "var(--risk-nominal)"
            }`,
          }}
        />
        <span className="mono" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          {overallRiskStatus} risk status
        </span>
      </div>
    </div>
  );
}
