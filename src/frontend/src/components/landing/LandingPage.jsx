import { useEffect } from "react";
import CinematicNav from "./CinematicNav";
import CinematicHero from "./CinematicHero";
import LandingFooter from "./LandingFooter";
import heroBg from "../../assets/hero-bg.jpg";

export default function LandingPage() {
  useEffect(() => {
    document.title = "RADAR // Risk Assessment & Debris Avoidance Routing";
  }, []);

  return (
    <div className="cinematic-page">
      {/* Full-viewport hero */}
      <section className="cinematic-hero-section">
        {/* Background image */}
        <div
          className="cinematic-bg"
          style={{ backgroundImage: `url(${heroBg})` }}
          aria-hidden="true"
        />

        {/* Cinematic overlay — stronger left/bottom for text, fades right to reveal station */}
        <div className="cinematic-overlay" aria-hidden="true" />

        {/* Navigation sits over the image */}
        <CinematicNav />

        {/* Thin 1px divider line below nav */}
        <div className="cinematic-nav-rule" aria-hidden="true" />

        {/* Hero copy — left-aligned */}
        <CinematicHero />
      </section>

      <LandingFooter />
    </div>
  );
}
