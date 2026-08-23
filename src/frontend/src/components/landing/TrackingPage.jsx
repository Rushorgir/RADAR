import { useEffect } from "react";
import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";
import CinematicNav from "./CinematicNav";
import RadarLogo from "../shared/RadarLogo";

export default function TrackingPage() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    document.title = "RADAR // Real-Time Orbital Tracking";
  }, []);

  const handleEnter = () => {
    navigate(isAuthenticated ? "/dashboard" : "/sign-in");
  };

  const features = [
    {
      code: "TRK-01",
      title: "SGP4 PROPAGATION ENGINE",
      desc: "High-fidelity Simplified General Perturbations model 4 (SGP4) propagation with TEME → ECI → ECEF → WGS84 geodetic coordinate transform pipeline. Computes satellite positions every 60 seconds for the full active catalog.",
      stat: "800+ OBJECTS",
      statLabel: "CONCURRENT TRACKING",
    },
    {
      code: "TRK-02",
      title: "3D CESIUM DIGITAL TWIN",
      desc: "Photorealistic WebGL globe rendering with natural-earth textures, real-time solar illumination (day/night terminator), and per-object HUD hover telemetry displaying NORAD ID, orbital regime, velocity, and risk tier.",
      stat: "60 FPS",
      statLabel: "RENDER TARGET",
    },
    {
      code: "TRK-03",
      title: "MULTI-TENANT DATASET INGESTION",
      desc: "Operators can import proprietary satellite TLE / ephemeris files via drag-and-drop or REST API. WebSocket streaming provides live ingestion telemetry. Isolated per-tenant database partitions ensure fleet data separation.",
      stat: "< 10s",
      statLabel: "INGESTION PIPELINE",
    },
    {
      code: "TRK-04",
      title: "TEMPORAL SIMULATION CONTROLS",
      desc: "Manipulate simulation time with play/pause, variable-speed multipliers (1× to 3600×), step-forward/backward, and direct epoch seek. Observe orbital evolution and conjunction geometry across a ±30-day window.",
      stat: "±30 DAYS",
      statLabel: "SIMULATION WINDOW",
    },
    {
      code: "TRK-05",
      title: "ATMOSPHERIC RE-ENTRY WATCH",
      desc: "King-Hele atmospheric drag lifetime modeling identifies objects with decaying orbits. Perigee analysis classifies re-entry urgency tiers (Nominal → Watch → Elevated → Imminent) with estimated days-to-decay.",
      stat: "4 TIERS",
      statLabel: "DECAY CLASSIFICATION",
    },
    {
      code: "TRK-06",
      title: "LAUNCH CORRIDOR PLANNER",
      desc: "Pre-launch trajectory safety verification. Define a launch site, target altitude, and ascent profile — RADAR projects the corridor against the full catalog, screening for potential debris intersections in real-time.",
      stat: "7+ SITES",
      statLabel: "LAUNCH PRESETS",
    },
  ];

  return (
    <div className="cinematic-page">
      <CinematicNav />

      <section className="info-page-hero">
        <div className="info-page-hero-inner">
          <span className="cine-eyebrow">SUBSYSTEM // ORBITAL TRACKING</span>
          <h1 className="info-page-title">
            Real-Time Orbital<br />Situational Awareness
          </h1>
          <p className="info-page-subtitle">
            From raw Two-Line Elements to a photorealistic 3D digital twin of Earth's orbital environment — 
            track every active satellite and debris fragment with sub-kilometer precision.
          </p>
        </div>
      </section>

      <section className="info-page-content">
        <div className="info-grid">
          {features.map((f) => (
            <div key={f.code} className="info-card hud-frame">
              <div className="info-card-header">
                <span className="capability-code mono">{f.code}</span>
              </div>
              <h3 className="info-card-title mono">{f.title}</h3>
              <p className="info-card-desc">{f.desc}</p>
              <div className="info-card-stat">
                <div className="info-card-stat-value mono">{f.stat}</div>
                <span className="eyebrow" style={{ fontSize: 8, color: "var(--text-dim)" }}>{f.statLabel}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="info-page-cta-section">
          <div className="info-page-cta hud-frame">
            <span className="eyebrow" style={{ color: "var(--signal)" }}>READY TO TRACK?</span>
            <h3 className="final-cta-title">ACCESS THE REAL-TIME TRACKING CONSOLE</h3>
            <p className="final-cta-desc">
              Deploy the 3D orbital environment and begin monitoring your constellation in real time.
            </p>
            <button type="button" className="landing-btn-cta-primary mono" onClick={handleEnter}>
              LAUNCH TRACKING CONSOLE →
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
