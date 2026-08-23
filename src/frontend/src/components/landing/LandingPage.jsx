import { useEffect } from "react";
import LandingNav from "./LandingNav";
import LandingHero from "./LandingHero";
import SystemStatusStrip from "./SystemStatusStrip";
import CapabilitiesGrid from "./CapabilitiesGrid";
import LiveTrackingPreview from "./LiveTrackingPreview";
import LandingFooter from "./LandingFooter";

export default function LandingPage({ dashboardStats, objectsCount }) {
  useEffect(() => {
    document.title = "RADAR // Orbital Intelligence & Collision Avoidance";
  }, []);

  return (
    <div className="landing-container scrollbar-thin">
      {/* Subtle deep space background overlay */}
      <div className="landing-bg-starfield" />
      <div className="landing-bg-glow" />

      {/* Top Aerospace Navigation */}
      <LandingNav />

      {/* Main Landing Sections */}
      <main className="landing-content-wrap">
        <LandingHero />
        <SystemStatusStrip stats={dashboardStats} objectsCount={objectsCount} />
        <CapabilitiesGrid />
        <LiveTrackingPreview />
        <LandingFooter />
      </main>
    </div>
  );
}
