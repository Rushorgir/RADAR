import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";

export default function LandingNav() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <header className="landing-header">
      <div className="landing-nav-inner">
        {/* Brand / Wordmark */}
        <div className="landing-brand" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
          <div className="landing-logo-mark">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="var(--signal)" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.6" />
              <circle cx="12" cy="12" r="6" stroke="var(--signal)" strokeWidth="1.5" />
              <circle cx="12" cy="12" r="2" fill="var(--signal)" />
              <line x1="12" y1="2" x2="12" y2="22" stroke="var(--signal)" strokeWidth="1" opacity="0.4" />
              <line x1="2" y1="12" x2="22" y2="12" stroke="var(--signal)" strokeWidth="1" opacity="0.4" />
            </svg>
            <span className="landing-logo-text">RADAR</span>
          </div>
          <span className="landing-logo-sub mono">RISK ASSESSMENT & DEBRIS AVOIDANCE ROUTING</span>
        </div>

        {/* Center Links */}
        <nav className="landing-nav-links mono">
          <button type="button" onClick={() => scrollToSection("overview")} className="landing-nav-link">
            OVERVIEW
          </button>
          <button type="button" onClick={() => scrollToSection("capabilities")} className="landing-nav-link">
            CAPABILITIES
          </button>
          <button type="button" onClick={() => scrollToSection("tracking")} className="landing-nav-link">
            TRACKING
          </button>
          <button type="button" onClick={() => scrollToSection("about")} className="landing-nav-link">
            ABOUT
          </button>
        </nav>

        {/* Right Actions */}
        <div className="landing-nav-actions mono">
          {isAuthenticated ? (
            <button
              type="button"
              className="landing-btn-primary"
              onClick={() => navigate("/dashboard")}
            >
              [ ACCESS RADAR ]
            </button>
          ) : (
            <>
              <button
                type="button"
                className="landing-nav-signin"
                onClick={() => navigate("/sign-in")}
              >
                SIGN IN
              </button>
              <button
                type="button"
                className="landing-btn-primary"
                onClick={() => navigate("/sign-in")}
              >
                [ ACCESS RADAR ]
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
