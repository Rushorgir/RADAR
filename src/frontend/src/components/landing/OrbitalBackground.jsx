import { useEffect, useRef } from "react";

/**
 * SolarSystemBackground — Landing Page Only
 *
 * A cinematic top-down solar system with a slow camera pan.
 * The camera drifts through the system revealing planets in orbit.
 * Clean, minimal, premium — no clutter.
 */
export default function OrbitalBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let W = 0, H = 0;
    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    // --- Seeded random for static star placement ---
    function seededRand(seed) {
      let s = seed;
      return () => {
        s = (s * 16807) % 2147483647;
        return (s - 1) / 2147483646;
      };
    }
    const rand = seededRand(7);

    // --- Sparse background stars (very few, just depth) ---
    const STAR_COUNT = 45;
    const stars = Array.from({ length: STAR_COUNT }, () => ({
      x: rand() * 6000 - 3000,  // in world space (large area)
      y: rand() * 4000 - 2000,
      r: 0.4 + rand() * 0.7,
      opacity: 0.08 + rand() * 0.18,
    }));

    // --- Solar system definition ---
    // All distances in "world units". Sun at origin.
    // Sizes are artistic — not astronomically accurate.
    const SUN_RADIUS = 38;

    const planets = [
      // name, orbitR, radius, color, glowColor, speed(rad/s), startAngle, ringScale
      {
        name: "Mercury",
        orbitR: 80,
        radius: 3.5,
        color: "#9a9a9a",
        glow: "rgba(154,154,154,0.25)",
        speed: 0.000190,
        angle: 1.2,
        ring: 0,
      },
      {
        name: "Venus",
        orbitR: 130,
        radius: 5.5,
        color: "#d4a96a",
        glow: "rgba(212,169,106,0.25)",
        speed: 0.000074,
        angle: 3.8,
        ring: 0,
      },
      {
        name: "Earth",
        orbitR: 185,
        radius: 6,
        color: "#4a90c4",
        glow: "rgba(74,144,196,0.30)",
        speed: 0.000046,
        angle: 0.5,
        ring: 0,
      },
      {
        name: "Mars",
        orbitR: 250,
        radius: 4,
        color: "#c0614a",
        glow: "rgba(192,97,74,0.22)",
        speed: 0.000024,
        angle: 5.1,
        ring: 0,
      },
      {
        name: "Jupiter",
        orbitR: 410,
        radius: 18,
        color: "#c8a97e",
        glow: "rgba(200,169,126,0.20)",
        speed: 0.0000039,
        angle: 2.3,
        ring: 0,
      },
      {
        name: "Saturn",
        orbitR: 580,
        radius: 15,
        color: "#d6c49a",
        glow: "rgba(214,196,154,0.18)",
        speed: 0.0000016,
        angle: 4.7,
        ring: 1,    // has rings
      },
      {
        name: "Uranus",
        orbitR: 760,
        radius: 10,
        color: "#7fcfcf",
        glow: "rgba(127,207,207,0.18)",
        speed: 0.00000057,
        angle: 1.0,
        ring: 0,
      },
      {
        name: "Neptune",
        orbitR: 920,
        radius: 9,
        color: "#4a6fb5",
        glow: "rgba(74,111,181,0.18)",
        speed: 0.00000029,
        angle: 3.3,
        ring: 0,
      },
    ];

    // --- Camera path: a smooth Lissajous-like drift ---
    // The camera slowly sweeps across the solar system revealing different regions
    // Path waypoints (world x, y) it visits over ~120s loop
    const CAM_SPEED = prefersReduced ? 0 : 1;
    let camX = 0, camY = 0;
    // We drift the camera on a large slow ellipse around the solar system
    // so different planets come into view
    const CAM_PATH_RX = 380;  // how far the camera wanders horizontally
    const CAM_PATH_RY = 200;  // vertical wander
    const CAM_PERIOD = 120000; // ms for one full camera loop

    // Smooth zoom: gentle in-and-out to maintain interest
    // Base scale: fit the system in the viewport, then drift
    function getBaseScale() {
      return Math.min(W, H) / 1100;
    }

    function drawSun(cx, cy, scale) {
      // Outer aura
      const aura = ctx.createRadialGradient(cx, cy, 0, cx, cy, SUN_RADIUS * scale * 4.5);
      aura.addColorStop(0, "rgba(255, 210, 100, 0.13)");
      aura.addColorStop(0.4, "rgba(255, 180, 60, 0.06)");
      aura.addColorStop(1, "rgba(255, 150, 30, 0)");
      ctx.beginPath();
      ctx.arc(cx, cy, SUN_RADIUS * scale * 4.5, 0, Math.PI * 2);
      ctx.fillStyle = aura;
      ctx.fill();

      // Soft glow ring
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, SUN_RADIUS * scale * 2.2);
      glow.addColorStop(0, "rgba(255, 240, 170, 0.55)");
      glow.addColorStop(0.5, "rgba(255, 200, 80, 0.22)");
      glow.addColorStop(1, "rgba(255, 160, 40, 0)");
      ctx.beginPath();
      ctx.arc(cx, cy, SUN_RADIUS * scale * 2.2, 0, Math.PI * 2);
      ctx.fillStyle = glow;
      ctx.fill();

      // Sun body
      const body = ctx.createRadialGradient(
        cx - SUN_RADIUS * scale * 0.2, cy - SUN_RADIUS * scale * 0.2, 0,
        cx, cy, SUN_RADIUS * scale,
      );
      body.addColorStop(0, "#fff5c0");
      body.addColorStop(0.5, "#ffd060");
      body.addColorStop(1, "#e8900a");
      ctx.beginPath();
      ctx.arc(cx, cy, SUN_RADIUS * scale, 0, Math.PI * 2);
      ctx.fillStyle = body;
      ctx.fill();
    }

    function drawOrbitPath(cx, cy, r, scale) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, r * scale, r * scale * 0.92, 0, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(80, 110, 140, 0.10)";
      ctx.lineWidth = 0.6;
      ctx.stroke();
    }

    function drawPlanet(planet, px, py, scale) {
      const r = planet.radius * scale;

      // Glow
      if (r > 1.5) {
        const g = ctx.createRadialGradient(px, py, 0, px, py, r * 3.5);
        g.addColorStop(0, planet.glow);
        g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.beginPath();
        ctx.arc(px, py, r * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = g;
        ctx.fill();
      }

      // Saturn rings (before body so body renders on top)
      if (planet.ring) {
        ctx.save();
        ctx.translate(px, py);
        ctx.scale(1, 0.32);
        // Outer ring
        ctx.beginPath();
        ctx.ellipse(0, 0, r * 3.0, r * 3.0, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(214, 196, 154, 0.32)";
        ctx.lineWidth = r * 1.0;
        ctx.stroke();
        // Inner gap
        ctx.beginPath();
        ctx.ellipse(0, 0, r * 1.8, r * 1.8, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(0,0,0,0)";
        ctx.lineWidth = r * 0.35;
        ctx.stroke();
        ctx.restore();
      }

      // Planet body
      const body = ctx.createRadialGradient(
        px - r * 0.25, py - r * 0.25, r * 0.05,
        px, py, r,
      );
      body.addColorStop(0, lighten(planet.color, 0.4));
      body.addColorStop(1, planet.color);
      ctx.beginPath();
      ctx.arc(px, py, Math.max(r, 0.8), 0, Math.PI * 2);
      ctx.fillStyle = body;
      ctx.fill();
    }

    function lighten(hex, amount) {
      const num = parseInt(hex.replace("#", ""), 16);
      const r = Math.min(255, (num >> 16) + Math.round(255 * amount));
      const g = Math.min(255, ((num >> 8) & 0xff) + Math.round(255 * amount));
      const b = Math.min(255, (num & 0xff) + Math.round(255 * amount));
      return `rgb(${r},${g},${b})`;
    }

    // --- Draw loop ---
    let raf;
    let startTime = performance.now();

    function draw(now) {
      const elapsed = now - startTime;
      const dt = Math.min(elapsed, 16);

      ctx.clearRect(0, 0, W, H);

      // Solid deep-space base
      ctx.fillStyle = "#03060b";
      ctx.fillRect(0, 0, W, H);

      const scale = getBaseScale();

      // Camera wander: slow ellipse so different planets drift into view
      const camAngle = (elapsed / CAM_PERIOD) * Math.PI * 2;
      const targetCamX = Math.cos(camAngle) * CAM_PATH_RX;
      const targetCamY = Math.sin(camAngle * 0.7) * CAM_PATH_RY;
      // Smooth lerp toward target (very slow)
      if (!prefersReduced) {
        camX += (targetCamX - camX) * 0.003;
        camY += (targetCamY - camY) * 0.003;
      }

      // Screen center with camera offset applied
      const originX = W / 2 - camX * scale;
      const originY = H / 2 - camY * scale;

      // Draw background stars (in world space, drifting with camera)
      for (const star of stars) {
        const sx = originX + star.x * scale;
        const sy = originY + star.y * scale;
        // Only draw if on screen
        if (sx < -2 || sx > W + 2 || sy < -2 || sy > H + 2) continue;
        ctx.beginPath();
        ctx.arc(sx, sy, star.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(200, 218, 240, ${star.opacity})`;
        ctx.fill();
      }

      // Update planet angles & draw orbits + planets
      for (const planet of planets) {
        if (!prefersReduced) {
          planet.angle += planet.speed * dt * 60;
        }

        // Draw orbit ring
        drawOrbitPath(originX, originY, planet.orbitR, scale);

        // Planet position
        const px = originX + Math.cos(planet.angle) * planet.orbitR * scale;
        const py = originY + Math.sin(planet.angle) * planet.orbitR * scale * 0.9; // slight tilt

        drawPlanet(planet, px, py, scale);
      }

      // Draw Sun last (at origin, on top of distant orbit rings)
      drawSun(originX, originY, scale);

      raf = requestAnimationFrame(draw);
    }

    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 0,
        display: "block",
      }}
    />
  );
}
