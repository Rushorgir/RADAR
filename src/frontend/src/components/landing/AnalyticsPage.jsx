import { useEffect } from "react";
import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";
import CinematicNav from "./CinematicNav";
import LandingFooter from "./LandingFooter";

export default function AnalyticsPage() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    document.title = "RADAR // Collision Analytics & Risk Intelligence";
  }, []);

  const handleEnter = () => {
    navigate(isAuthenticated ? "/dashboard" : "/sign-in");
  };

  const analyticsSections = [
    {
      code: "AN-01",
      title: "CONJUNCTION SCREENING PIPELINE",
      desc: "Two-tier screening engine: a coarse bounding-box radial filter eliminates 99.9% of non-threatening object pairs, then a fine-stage cubic spline interpolation around the Time of Closest Approach (TCA) determines exact miss distances to sub-kilometer precision.",
      stat: "72h",
      statLabel: "LOOKAHEAD WINDOW",
    },
    {
      code: "AN-02",
      title: "FOSTER 2D COLLISION PROBABILITY",
      desc: "Computes the statistical Probability of Collision (Pc) by rotating satellite covariance ellipsoids into the relative encounter plane using the RIC (Radial, In-track, Cross-track) coordinate frame and applying 2D numerical integration over the combined uncertainty region.",
      stat: "10⁻⁸",
      statLabel: "Pc SENSITIVITY",
    },
    {
      code: "AN-03",
      title: "EXPLAINABLE AI RISK RANKING",
      desc: "LightGBM gradient-boosted tree classifier trained on orbital characteristics, relative velocities, altitude regimes, and covariance geometries. TreeSHAP decomposition explains the exact mathematical contribution of each feature to every risk score.",
      stat: "SHAP",
      statLabel: "EXPLAINABILITY ENGINE",
    },
    {
      code: "AN-04",
      title: "AUTONOMOUS MANEUVER ADVISORY",
      desc: "When encounters breach safety thresholds (Pc > 10⁻⁴ or miss distance < 1 km), RADAR solves the Gauss Variational Equations to compute minimum impulsive ΔV burns — optimizing direction and magnitude while validating against secondary conjunction creation.",
      stat: "ΔV",
      statLabel: "OPTIMAL BURN VECTOR",
    },
    {
      code: "AN-05",
      title: "RISK DISTRIBUTION DASHBOARD",
      desc: "Real-time dashboard panels aggregate conjunction events by risk tier (Nominal, Elevated, Critical), displaying total active alerts, affected satellite counts, and overall constellation health status with drill-down event inspection.",
      stat: "3 TIERS",
      statLabel: "RISK CLASSIFICATION",
    },
    {
      code: "AN-06",
      title: "THREAT ANALYSIS MODE",
      desc: "Dedicated threat analysis interface with ranked conjunction event list, per-event SHAP feature breakdown, maneuver advisory details (ΔV magnitude, burn direction, resulting miss distance), and direct object selection for 3D globe fly-to inspection.",
      stat: "LIVE",
      statLabel: "THREAT MATRIX",
    },
  ];

  return (
    <div className="cinematic-page">
      <CinematicNav />

      <section className="info-page-hero info-page-hero--analytics">
        <div className="info-page-hero-inner">
          <span className="cine-eyebrow">SUBSYSTEM // RISK ANALYTICS</span>
          <h1 className="info-page-title">
            Collision Risk Intelligence<br />& Avoidance Optimization
          </h1>
          <p className="info-page-subtitle">
            From probabilistic conjunction assessment to explainable AI risk ranking 
            and autonomous fuel-optimal avoidance maneuvers — intelligence that saves missions.
          </p>
        </div>
      </section>

      <section className="info-page-content">
        <div className="info-grid">
          {analyticsSections.map((s) => (
            <div key={s.code} className="info-card hud-frame">
              <div className="info-card-header">
                <span className="capability-code mono">{s.code}</span>
              </div>
              <h3 className="info-card-title mono">{s.title}</h3>
              <p className="info-card-desc">{s.desc}</p>
              <div className="info-card-stat">
                <div className="info-card-stat-value mono">{s.stat}</div>
                <span className="eyebrow" style={{ fontSize: 8, color: "var(--text-dim)" }}>{s.statLabel}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="info-page-cta-section">
          <div className="info-page-cta hud-frame">
            <span className="eyebrow" style={{ color: "var(--signal)" }}>READY TO ANALYZE?</span>
            <h3 className="final-cta-title">ACCESS THE THREAT ANALYSIS CONSOLE</h3>
            <p className="final-cta-desc">
              Inspect every conjunction event with full SHAP explainability and receive instant avoidance maneuver recommendations.
            </p>
            <button type="button" className="landing-btn-cta-primary mono" onClick={handleEnter}>
              OPEN ANALYTICS CONSOLE →
            </button>
          </div>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
