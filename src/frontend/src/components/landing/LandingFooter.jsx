import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";

export default function LandingFooter() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  const handleEnterRadar = () => {
    if (isAuthenticated) {
      navigate("/dashboard");
    } else {
      navigate("/sign-in");
    }
  };

  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <footer className="landing-footer" id="about">
      {/* Final Call to Action Strip */}
      <div className="landing-final-cta hud-frame">
        <div className="final-cta-content">
          <span className="eyebrow" style={{ color: "var(--signal)" }}>READY TO ENTER ORBITAL CONTROL?</span>
          <h3 className="final-cta-title">ACCESS THE RADAR TRACKING ENVIRONMENT</h3>
          <p className="final-cta-desc">
            Equip your operations team with autonomous collision risk intelligence and propellant-optimized avoidance maneuvers.
          </p>
        </div>
        <button
          type="button"
          className="landing-btn-cta-primary mono"
          onClick={handleEnterRadar}
        >
          ENTER RADAR →
        </button>
      </div>

      {/* Footer Meta Grid */}
      <div className="landing-footer-grid">
        <div className="footer-brand-col">
          <div className="landing-logo-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="var(--signal)" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.6" />
              <circle cx="12" cy="12" r="6" stroke="var(--signal)" strokeWidth="1.5" />
              <circle cx="12" cy="12" r="2" fill="var(--signal)" />
            </svg>
            <span className="landing-logo-text" style={{ fontSize: 16 }}>RADAR</span>
          </div>
          <p className="footer-tagline mono">
            Risk Assessment & Debris Avoidance Routing<br />
            Defense & Commercial Space Situational Awareness
          </p>
        </div>

        <div className="footer-links-col mono">
          <span className="eyebrow">SYSTEM</span>
          <button type="button" onClick={() => scrollToSection("overview")} className="footer-link">
            Overview
          </button>
          <button type="button" onClick={() => scrollToSection("capabilities")} className="footer-link">
            Capabilities
          </button>
          <button type="button" onClick={() => scrollToSection("tracking")} className="footer-link">
            Tracking Environment
          </button>
        </div>

        <div className="footer-links-col mono">
          <span className="eyebrow">SECURITY & LEGAL</span>
          <span className="footer-link">Privacy Protocol</span>
          <span className="footer-link">Terms of Service</span>
          <span className="footer-link">Operational Security</span>
        </div>

        <div className="footer-links-col mono">
          <span className="eyebrow">SYSTEM STATUS</span>
          <div className="status-value" style={{ fontSize: 11, color: "var(--signal)" }}>
            <span className="status-indicator-dot online" /> 100% OPERATIONAL
          </div>
          <span style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 6 }}>
            LATENCY // 42MS
          </span>
        </div>
      </div>

      <div className="footer-bottom-bar mono">
        <div>© 2026 RADAR ORBITAL DYNAMICS // ALL RIGHTS RESERVED</div>
        <div style={{ color: "var(--text-dim)" }}>RESTRICTED AEROSPACE OPERATIONS INTERFACE</div>
      </div>
    </footer>
  );
}
