import { useRouter } from "../../context/Router";
import RadarLogo from "../shared/RadarLogo";

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
            <div style={{ marginBottom: 6 }}>
              <RadarLogo height={44} className="auth-radar-logo" />
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
