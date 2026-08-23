import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";

export default function LiveTrackingPreview() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  const handleLaunchDashboard = () => {
    if (isAuthenticated) {
      navigate("/dashboard");
    } else {
      navigate("/sign-in");
    }
  };

  return (
    <section className="landing-live-preview" id="tracking">
      <div className="section-header">
        <span className="eyebrow">TACTICAL MISSION CONTROL</span>
        <h2 className="section-title">ORBITAL SITUATION AWARENESS</h2>
        <p className="section-subtitle">
          Real-time 3D telemetry display with interactive conjunction evaluation, maneuver planning, and orbital regime filters.
        </p>
      </div>

      <div className="preview-terminal hud-frame">
        {/* Terminal Header */}
        <div className="preview-terminal-header">
          <div className="terminal-dots">
            <span className="terminal-dot red" />
            <span className="terminal-dot yellow" />
            <span className="terminal-dot green" />
          </div>
          <div className="terminal-title mono">RADAR // ORBITAL CONSOLE PREVIEW [ACTIVE FEED]</div>
          <div className="terminal-live-badge mono">
            <span className="landing-status-dot pulse" /> LIVE TELEMETRY
          </div>
        </div>

        {/* Telemetry Mock Display Content */}
        <div className="preview-terminal-body">
          <div className="preview-terminal-grid">
            {/* Left Tracked Object Panel */}
            <div className="preview-subpanel hud-frame">
              <div className="eyebrow">PRIMARY TRACKED ASSET</div>
              <div className="mono" style={{ fontSize: 16, fontWeight: 700, marginTop: 4, color: "var(--signal)" }}>
                ISS (ZARYA) // NORAD 25544
              </div>

              <div className="preview-data-grid mono" style={{ marginTop: 12 }}>
                <div>
                  <span className="eyebrow">REGIME</span>
                  <div>LEO (418.5 KM)</div>
                </div>
                <div>
                  <span className="eyebrow">VELOCITY</span>
                  <div>7.66 KM/S</div>
                </div>
                <div>
                  <span className="eyebrow">INCLINATION</span>
                  <div>51.64°</div>
                </div>
                <div>
                  <span className="eyebrow">STATUS</span>
                  <div style={{ color: "var(--risk-nominal)" }}>NOMINAL</div>
                </div>
              </div>
            </div>

            {/* Center Conjunction Threat Flag */}
            <div className="preview-subpanel hud-frame" style={{ borderLeft: "3px solid var(--risk-critical)" }}>
              <div className="eyebrow" style={{ color: "var(--risk-critical)" }}>ACTIVE THREAT // CONJUNCTION EVENT</div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 700, marginTop: 4 }}>
                ISS × DEB-COSMOS-2251
              </div>

              <div className="preview-data-grid mono" style={{ marginTop: 12 }}>
                <div>
                  <span className="eyebrow">COLLISION PROBABILITY (Pc)</span>
                  <div style={{ color: "var(--risk-critical)", fontWeight: 700 }}>3.2 × 10⁻⁴</div>
                </div>
                <div>
                  <span className="eyebrow">MISS DISTANCE</span>
                  <div style={{ fontWeight: 700 }}>0.42 KM</div>
                </div>
                <div>
                  <span className="eyebrow">TIME TO TCA</span>
                  <div style={{ color: "var(--risk-high)" }}>T-06H 12M</div>
                </div>
                <div>
                  <span className="eyebrow">RECOMMENDED ACTION</span>
                  <div style={{ color: "var(--signal)" }}>Δv ALONG-TRACK (+0.086 M/S)</div>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive CTA overlay */}
          <div className="preview-cta-strip">
            <span className="mono" style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>
              OPERATIONAL ENVIRONMENT READY // SGP4 PROPAGATION RUNNING
            </span>
            <button
              type="button"
              className="landing-btn-primary mono"
              onClick={handleLaunchDashboard}
            >
              LAUNCH FULL CONSOLE →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
