export default function SystemStatusStrip({ stats, objectsCount }) {
  const trackedCount = objectsCount || stats?.active_satellites + stats?.tracked_debris || 100;
  const activeSats = stats?.active_satellites ?? 91;
  const highRisk = stats?.high_risk_objects ?? 7;
  const overallStatus = stats?.overall_risk_status ? stats.overall_risk_status.toUpperCase() : "NOMINAL";

  return (
    <section className="system-status-strip hud-frame">
      <div className="status-strip-grid mono">
        <div className="status-strip-item">
          <span className="status-label eyebrow">TRACKING NETWORK</span>
          <div className="status-value">
            <span className="status-indicator-dot online" />
            <strong style={{ color: "var(--signal)" }}>ACTIVE (ONLINE)</strong>
          </div>
        </div>

        <div className="status-strip-item">
          <span className="status-label eyebrow">OBJECTS TRACKED</span>
          <div className="status-value">
            <strong>{trackedCount.toLocaleString()}</strong>
          </div>
        </div>

        <div className="status-strip-item">
          <span className="status-label eyebrow">ACTIVE SATELLITES</span>
          <div className="status-value">
            <strong style={{ color: "var(--signal)" }}>{activeSats.toLocaleString()}</strong>
          </div>
        </div>

        <div className="status-strip-item">
          <span className="status-label eyebrow">HIGH-RISK CONJUNCTIONS</span>
          <div className="status-value">
            <strong style={{ color: highRisk > 0 ? "var(--risk-critical)" : "var(--risk-nominal)" }}>
              {highRisk < 10 ? `0${highRisk}` : highRisk}
            </strong>
          </div>
        </div>

        <div className="status-strip-item">
          <span className="status-label eyebrow">SYSTEM HEALTH</span>
          <div className="status-value">
            <strong style={{ color: "var(--signal)" }}>{overallStatus}</strong>
          </div>
        </div>
      </div>
    </section>
  );
}
