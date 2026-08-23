export default function CapabilitiesGrid() {
  const capabilities = [
    {
      id: "tracking",
      code: "CAP-01",
      title: "ORBITAL TRACKING",
      desc: "Continuous high-precision SGP4 propagation and state-vector monitoring across active payloads and catalogued debris fields in LEO, MEO, and GEO.",
      metrics: "60s Ephemeris Refreshes // WGS84 Geodetic Frame",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--signal)" strokeWidth="1.5">
          <circle cx="12" cy="12" r="9" strokeDasharray="2 2" />
          <ellipse cx="12" cy="12" rx="9" ry="3.5" transform="rotate(-30 12 12)" />
          <circle cx="12" cy="12" r="3" fill="rgba(53, 217, 255, 0.2)" stroke="var(--signal)" />
          <circle cx="17" cy="8" r="1.5" fill="var(--signal)" />
        </svg>
      ),
    },
    {
      id: "assessment",
      code: "CAP-02",
      title: "RISK ASSESSMENT",
      desc: "Automated conjunction assessment utilizing Foster 2D encounter-frame probability, Monte Carlo validation, and ML explainability models.",
      metrics: "Pc Sensitivity Down to 10⁻⁸ // SHAP Explainability",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--risk-critical)" strokeWidth="1.5">
          <polygon points="12 2 22 20 2 20 12 2" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <circle cx="12" cy="17" r="1" fill="var(--risk-critical)" />
        </svg>
      ),
    },
    {
      id: "avoidance",
      code: "CAP-03",
      title: "COLLISION AVOIDANCE",
      desc: "Optimal impulsive avoidance maneuver generation offering along-track, radial, and cross-track delta-V burns balanced against fuel budgets.",
      metrics: "Multi-Strategy Optimizer // Fuel Optimization",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--signal)" strokeWidth="1.5">
          <path d="M12 2L15 9H9L12 2Z" />
          <path d="M12 9V22" strokeDasharray="3 3" />
          <path d="M7 16L12 12L17 16" />
        </svg>
      ),
    },
    {
      id: "simulation",
      code: "CAP-04",
      title: "TEMPORAL SIMULATION",
      desc: "Simulate lookahead encounters up to 72 hours in advance, inspect orbital decay trajectories, and analyze launch corridor clearances.",
      metrics: "Reentry Monitoring // Launch Corridor Screening",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--signal)" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
          <path d="M18 2L22 6" />
        </svg>
      ),
    },
  ];

  return (
    <section className="landing-capabilities" id="capabilities">
      <div className="section-header">
        <span className="eyebrow">AEROSPACE CAPABILITIES</span>
        <h2 className="section-title">ORBITAL SITUATION INTELLIGENCE</h2>
        <p className="section-subtitle">
          Engineered for mission operators, space agencies, and satellite constellation managers
          requiring deterministic collision avoidance solutions.
        </p>
      </div>

      <div className="capabilities-grid">
        {capabilities.map((cap) => (
          <div key={cap.id} className="capability-card hud-frame">
            <div className="capability-card-top">
              <div className="capability-icon-wrap">{cap.icon}</div>
              <span className="capability-code mono">{cap.code}</span>
            </div>

            <h3 className="capability-title mono">{cap.title}</h3>
            <p className="capability-desc">{cap.desc}</p>

            <div className="capability-footer mono">
              <span className="eyebrow" style={{ fontSize: 9 }}>SPECIFICATION</span>
              <div style={{ color: "var(--signal)", fontSize: 11, marginTop: 2 }}>{cap.metrics}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
