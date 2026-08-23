import { useEffect } from "react";
import LandingNav from "./LandingNav";
import LandingHero from "./LandingHero";
import SystemStatusStrip from "./SystemStatusStrip";
import CapabilitiesGrid from "./CapabilitiesGrid";
import LiveTrackingPreview from "./LiveTrackingPreview";
import LandingFooter from "./LandingFooter";
import OrbitalBackground from "./OrbitalBackground";

export default function LandingPage({ dashboardStats, objectsCount }) {
  useEffect(() => {
    document.title = "RADAR // Orbital Intelligence & Collision Avoidance";
  }, []);

  return (
    <div className="landing-container scrollbar-thin">
      {/* Orbital canvas — behind all content, landing page only */}
      <OrbitalBackground />

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

