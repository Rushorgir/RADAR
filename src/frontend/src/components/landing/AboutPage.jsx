import { useEffect } from "react";
import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";
import CinematicNav from "./CinematicNav";
import LandingFooter from "./LandingFooter";
import RadarLogo from "../shared/RadarLogo";

export default function AboutPage() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    document.title = "RADAR // About — Mission & Architecture";
  }, []);

  const handleEnter = () => {
    navigate(isAuthenticated ? "/dashboard" : "/sign-up");
  };

  const techStack = [
    { layer: "ORBITAL PHYSICS", items: "SGP4 Propagation, TEME/ECI/ECEF Transforms, RIC Encounter Frame, Foster 2D Pc" },
    { layer: "MACHINE LEARNING", items: "LightGBM Classifier, TreeSHAP Explainability, Feature Engineering Pipeline" },
    { layer: "BACKEND", items: "Python FastAPI, SQLAlchemy ORM, WebSocket Streaming, Background Workers" },
    { layer: "FRONTEND", items: "React 19, CesiumJS WebGL Globe, Vite Build, Custom HUD Design System" },
    { layer: "DATA", items: "SQLite Multi-Tenant DB, TLE/Ephemeris Ingestion, Conjunction Event Store" },
    { layer: "TESTING", items: "208 Unit/Integration/Workflow Tests, Skyfield Cross-Validation, CI Pipeline" },
  ];

  const teamMembers = [
    {
      role: "ORBITAL MECHANICS & AI ENGINE",
      desc: "SGP4 propagation pipeline, conjunction screening, Foster 2D collision probability, LightGBM risk classifier, SHAP explainability, and autonomous ΔV maneuver advisory.",
    },
    {
      role: "BACKEND ARCHITECTURE & API",
      desc: "FastAPI REST endpoints, SQLAlchemy database models, WebSocket real-time streaming, dataset ingestion pipeline, multi-tenant data isolation, and comprehensive test coverage.",
    },
    {
      role: "FRONTEND & 3D VISUALIZATION",
      desc: "CesiumJS digital twin, React HUD component library, cinematic landing page, authentication flow, real-time orbital visualization with day/night solar illumination.",
    },
  ];

  return (
    <div className="cinematic-page">
      <CinematicNav />

      <section className="info-page-hero info-page-hero--about">
        <div className="info-page-hero-inner">
          <RadarLogo height={60} style={{ marginBottom: 16, opacity: 0.9 }} />
          <span className="cine-eyebrow">ABOUT // PROJECT RADAR</span>
          <h1 className="info-page-title">
            The Air Traffic Control<br />System for Space
          </h1>
          <p className="info-page-subtitle">
            RADAR (Real-time Autonomous Debris Assessment & Risk) is an enterprise-grade Space Situational Awareness 
            platform combining vectorized orbital mechanics, probabilistic collision theory, and explainable machine learning.
          </p>
        </div>
      </section>

      <section className="info-page-content">
        {/* Mission */}
        <div className="about-mission-section">
          <div className="about-mission-card hud-frame">
            <span className="eyebrow" style={{ color: "var(--signal)" }}>OUR MISSION</span>
            <h2 className="about-mission-title mono">PROTECTING HUMANITY'S ORBITAL INFRASTRUCTURE</h2>
            <p className="about-mission-desc">
              Over the past decade, the cost of orbital access has plummeted by 90%. Thousands of commercial satellites 
              now crowd Low Earth Orbit — alongside 30,000+ pieces of lethal debris traveling at 28,000 km/h. 
              Every collision spawns thousands of new fragments, accelerating the Kessler Syndrome cascade that could 
              render vital orbits unusable for generations.
            </p>
            <p className="about-mission-desc">
              RADAR translates raw orbital tracking feeds into automated, explainable risk triage and fuel-optimal 
              avoidance maneuvers — protecting billion-dollar constellations with single-click intelligence.
            </p>
          </div>
        </div>

        {/* Tech Stack */}
        <div className="about-tech-section">
          <div className="section-header" style={{ marginBottom: 32 }}>
            <span className="eyebrow">ENGINEERING ARCHITECTURE</span>
            <h2 className="section-title">TECHNOLOGY STACK</h2>
          </div>
          <div className="about-tech-grid">
            {techStack.map((t) => (
              <div key={t.layer} className="about-tech-row hud-frame">
                <span className="about-tech-layer mono">{t.layer}</span>
                <span className="about-tech-items">{t.items}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Team Roles */}
        <div className="about-team-section">
          <div className="section-header" style={{ marginBottom: 32 }}>
            <span className="eyebrow">ENGINEERING DOMAINS</span>
            <h2 className="section-title">SYSTEM CONTRIBUTIONS</h2>
          </div>
          <div className="about-team-grid">
            {teamMembers.map((m, i) => (
              <div key={i} className="about-team-card hud-frame">
                <span className="eyebrow" style={{ color: "var(--signal)", fontSize: 10 }}>{m.role}</span>
                <p className="about-team-desc">{m.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Key Stats */}
        <div className="about-stats-bar hud-frame">
          <div className="about-stat-item">
            <div className="about-stat-value mono">800+</div>
            <span className="eyebrow" style={{ fontSize: 8 }}>TRACKED OBJECTS</span>
          </div>
          <div className="about-stat-item">
            <div className="about-stat-value mono">208</div>
            <span className="eyebrow" style={{ fontSize: 8 }}>PASSING TESTS</span>
          </div>
          <div className="about-stat-item">
            <div className="about-stat-value mono">72h</div>
            <span className="eyebrow" style={{ fontSize: 8 }}>LOOKAHEAD WINDOW</span>
          </div>
          <div className="about-stat-item">
            <div className="about-stat-value mono">10⁻⁸</div>
            <span className="eyebrow" style={{ fontSize: 8 }}>Pc SENSITIVITY</span>
          </div>
          <div className="about-stat-item">
            <div className="about-stat-value mono">B2B</div>
            <span className="eyebrow" style={{ fontSize: 8 }}>SaaS MODEL</span>
          </div>
        </div>

        {/* CTA */}
        <div className="info-page-cta-section">
          <div className="info-page-cta hud-frame">
            <span className="eyebrow" style={{ color: "var(--signal)" }}>READY TO BEGIN?</span>
            <h3 className="final-cta-title">REGISTER FOR OPERATOR ACCESS</h3>
            <p className="final-cta-desc">
              Create your operator clearance and gain access to the full 3D RADAR tracking and analytics console.
            </p>
            <button type="button" className="landing-btn-cta-primary mono" onClick={handleEnter}>
              CREATE OPERATOR ACCOUNT →
            </button>
          </div>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
