import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";

export default function LandingHero() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  const handleEnterRadar = () => {
    if (isAuthenticated) {
      navigate("/dashboard");
    } else {
      navigate("/sign-in");
    }
  };

  const scrollToExplore = () => {
    const el = document.getElementById("capabilities");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="landing-hero" id="overview">
      <div className="landing-hero-content">
        <div className="landing-hero-badge mono">
          <span className="landing-status-dot" />
          <span>ORBITAL INTELLIGENCE PLATFORM // VER 2.4.0</span>
        </div>

        <h1 className="landing-hero-title">
          SEE THE THREAT<br />
          <span style={{ color: "var(--signal)" }}>BEFORE THE COLLISION.</span>
        </h1>

        <p className="landing-hero-desc">
          RADAR provides real-time orbital awareness, debris risk assessment, and
          collision-avoidance intelligence for satellites and commercial constellations in Earth orbit.
        </p>

        <div className="landing-hero-actions mono">
          <button
            type="button"
            className="landing-btn-cta-primary"
            onClick={handleEnterRadar}
          >
            ENTER RADAR →
          </button>
          <button
            type="button"
            className="landing-btn-cta-secondary"
            onClick={scrollToExplore}
          >
            EXPLORE SYSTEM ↓
          </button>
        </div>

        <div className="landing-hero-telemetry mono">
          <div className="telemetry-item">
            <span className="eyebrow">PROPAGATION ENGINE</span>
            <strong>SGP4 / WGS84 HIGH-PRECISION</strong>
          </div>
          <div className="telemetry-divider" />
          <div className="telemetry-item">
            <span className="eyebrow">RISK PIPELINE</span>
            <strong>FOSTER 2D & MONTE CARLO (100K)</strong>
          </div>
          <div className="telemetry-divider" />
          <div className="telemetry-item">
            <span className="eyebrow">LATENCY TARGET</span>
            <strong>&lt; 500MS REACTION HORIZON</strong>
          </div>
        </div>
      </div>
    </section>
  );
}
