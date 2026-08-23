import { useEffect, useRef } from "react";
import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";

export default function CinematicHero() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();
  const heroRef = useRef(null);

  // Subtle entrance animation on mount
  useEffect(() => {
    const el = heroRef.current;
    if (!el) return;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    el.style.opacity = "0";
    el.style.transform = "translateY(18px)";
    const raf = requestAnimationFrame(() => {
      el.style.transition = "opacity 0.9s ease, transform 0.9s ease";
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    });
    return () => cancelAnimationFrame(raf);
  }, []);

  // GET STARTED → sign-up for new users, dashboard for authenticated
  const handleGetStarted = () => {
    navigate(isAuthenticated ? "/dashboard" : "/sign-up");
  };

  // EXPLORE PLATFORM → tracking page (no auth required, informational)
  const handleExplore = () => {
    navigate("/tracking");
  };

  return (
    <div className="cine-hero-content" ref={heroRef} id="overview">
      {/* Eyebrow */}
      <p className="cine-eyebrow">
        RISK ASSESSMENT &amp; DEBRIS AVOIDANCE ROUTING
      </p>

      {/* Main headline */}
      <h1 className="cine-headline">
        See It. Assess It.<br />
        Avoid It.
      </h1>

      {/* Description */}
      <p className="cine-description">
        RADAR empowers space operators with real-time debris tracking,
        collision risk prediction, and intelligent avoidance routing —
        keeping missions safe in an increasingly crowded orbit.
      </p>

      {/* CTAs */}
      <div className="cine-actions">
        <button
          type="button"
          className="cine-btn-primary"
          onClick={handleGetStarted}
          id="cta-get-started"
        >
          {isAuthenticated ? "OPEN CONSOLE" : "GET STARTED"}
        </button>

        <button
          type="button"
          className="cine-btn-secondary"
          onClick={handleExplore}
          id="cta-explore"
        >
          EXPLORE PLATFORM &nbsp;→
        </button>
      </div>
    </div>
  );
}
