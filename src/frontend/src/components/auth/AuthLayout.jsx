import { useRouter } from "../../context/Router";

export default function AuthLayout({ children, title, subtitle }) {
  const { navigate } = useRouter();

  return (
    <div className="auth-container">
      {/* Background Ambience */}
      <div className="auth-bg-ambient" />
      <div className="auth-grid-overlay" />

      {/* Top Left Return Action */}
      <div className="auth-top-bar">
        <button
          type="button"
          className="auth-back-btn mono"
          onClick={() => navigate("/")}
        >
          ← RETURN TO OVERVIEW
        </button>

        <div className="auth-top-security mono">
          <span className="status-indicator-dot online" /> SECURE TERMINAL // TLS 1.3
        </div>
      </div>

      <div className="auth-frame-wrap">
        {/* Left Side: Aerospace Visual & Telemetry */}
        <div className="auth-visual-pane hud-frame">
          <div className="auth-visual-header">
            <div className="landing-logo-mark">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="var(--signal)" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.6" />
                <circle cx="12" cy="12" r="6" stroke="var(--signal)" strokeWidth="1.5" />
                <circle cx="12" cy="12" r="2" fill="var(--signal)" />
                <line x1="12" y1="2" x2="12" y2="22" stroke="var(--signal)" strokeWidth="1" opacity="0.4" />
                <line x1="2" y1="12" x2="22" y2="12" stroke="var(--signal)" strokeWidth="1" opacity="0.4" />
              </svg>
              <span className="landing-logo-text" style={{ fontSize: 18 }}>RADAR</span>
            </div>
            <div className="eyebrow" style={{ marginTop: 2 }}>ORBITAL INTELLIGENCE PLATFORM</div>
          </div>

          <div className="auth-visual-core">
            <h2 className="auth-tactical-title">
              TRACK.<br />
              ASSESS.<br />
              <span style={{ color: "var(--signal)" }}>AVOID.</span>
            </h2>

            <p className="auth-tactical-desc">
              Deterministic collision avoidance routing, SGP4 orbital propagation,
              and real-time conjunction intelligence for high-value space assets.
            </p>
          </div>

          <div className="auth-visual-telemetry mono">
            <div className="auth-telemetry-row">
              <span className="eyebrow">TERMINAL ID</span>
              <span>RADAR-TERM-09</span>
            </div>
            <div className="auth-telemetry-row">
              <span className="eyebrow">SECURITY PROTOCOL</span>
              <span>AES-256-GCM / 8192-BIT</span>
            </div>
            <div className="auth-telemetry-row">
              <span className="eyebrow">NODE STATUS</span>
              <span style={{ color: "var(--signal)" }}>ONLINE / SYNCHRONIZED</span>
            </div>
          </div>
        </div>

        {/* Right Side: Access / Registration Panel */}
        <div className="auth-panel-pane hud-frame">
          <div className="auth-panel-header">
            <span className="eyebrow">{subtitle || "SYSTEM ACCESS CONTROL"}</span>
            <h1 className="auth-panel-title mono">{title}</h1>
          </div>

          <div className="auth-panel-body">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
