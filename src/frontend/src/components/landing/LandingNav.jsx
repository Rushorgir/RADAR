import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";
import RadarLogo from "../shared/RadarLogo";

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
        <div className="landing-brand" onClick={() => navigate("/")} style={{ cursor: "pointer", display: "flex", alignItems: "center" }}>
          <RadarLogo height={44} className="landing-nav-radar-logo" />
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
