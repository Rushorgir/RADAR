import { useEffect, useRef } from "react";

/**
 * OrbitalBackground — Landing Page Only
 * A subtle, realistic orbital environment rendered on a single Canvas.
 * Approximately 40-80 stars, 2-4 orbital paths, a handful of tracked objects,
 * and one infrequent tracking pulse event. Respects prefers-reduced-motion.
 */
export default function OrbitalBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    // --- Reduced-motion check ---
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // --- Resize handler ---
    let W = 0, H = 0;
    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    // --- Seeded pseudo-random (deterministic layout across resizes) ---
    function seededRand(seed) {
      let s = seed;
      return function () {
        s = (s * 16807 + 0) % 2147483647;
        return (s - 1) / 2147483646;
      };
    }
    const rand = seededRand(42);

    // --- Stars (three tiers for natural depth) ---
    // Tier 1: distant dust — tiny, very dim, static
    const DUST_COUNT = 100;
    // Tier 2: mid-field — small, moderate opacity, rare twinkle
    const MID_COUNT = 60;
    // Tier 3: foreground — slightly larger, brighter, occasional twinkle
    const NEAR_COUNT = 20;
    const STAR_COUNT = DUST_COUNT + MID_COUNT + NEAR_COUNT;

    const stars = [
      ...Array.from({ length: DUST_COUNT }, () => ({
        x: rand() * 1920,
        y: rand() * 1080,
        r: 0.3 + rand() * 0.3,
        opacity: 0.06 + rand() * 0.12,
        twinkle: false,
        twinkleOffset: 0,
        twinkleSpeed: 0,
      })),
      ...Array.from({ length: MID_COUNT }, () => ({
        x: rand() * 1920,
        y: rand() * 1080,
        r: 0.5 + rand() * 0.5,
        opacity: 0.14 + rand() * 0.20,
        twinkle: rand() < 0.12,
        twinkleOffset: rand() * Math.PI * 2,
        twinkleSpeed: 0.25 + rand() * 0.45,
      })),
      ...Array.from({ length: NEAR_COUNT }, () => ({
        x: rand() * 1920,
        y: rand() * 1080,
        r: 0.9 + rand() * 0.6,
        opacity: 0.28 + rand() * 0.25,
        twinkle: rand() < 0.25,
        twinkleOffset: rand() * Math.PI * 2,
        twinkleSpeed: 0.2 + rand() * 0.4,
      })),
    ];

    // --- Orbital paths: 3 ellipses, biased toward right/upper-right ---
    const orbits = [
      // cx, cy (normalized 0-1), rx, ry, tilt (rad), opacity
      { cx: 0.72, cy: 0.38, rx: 0.30, ry: 0.14, tilt: -0.22, color: "rgba(80, 115, 145, 0.09)" },
      { cx: 0.80, cy: 0.60, rx: 0.22, ry: 0.10, tilt: 0.18,  color: "rgba(70, 100, 130, 0.07)" },
      { cx: 0.60, cy: 0.25, rx: 0.35, ry: 0.08, tilt: -0.10, color: "rgba(85, 120, 150, 0.06)" },
    ];

    // --- Tracked objects: move along orbits ---
    const objects = [
      // orbitIndex, t (0-1 position), speed, type: "satellite"|"debris"
      { orbit: 0, t: 0.12, speed: prefersReduced ? 0 : 0.000035, type: "satellite" },
      { orbit: 0, t: 0.68, speed: prefersReduced ? 0 : 0.000018, type: "debris" },
      { orbit: 1, t: 0.40, speed: prefersReduced ? 0 : 0.000052, type: "satellite" },
      { orbit: 1, t: 0.80, speed: prefersReduced ? 0 : 0.000022, type: "debris" },
      { orbit: 2, t: 0.05, speed: prefersReduced ? 0 : 0.000015, type: "debris" },
      { orbit: 2, t: 0.55, speed: prefersReduced ? 0 : 0.000008, type: "debris" },
    ];

    // --- Tracking pulse state ---
    let pulse = null;
    let lastPulseTime = -30000; // wait 30s before first pulse

    function getOrbitPos(orbit, t) {
      const angle = t * Math.PI * 2;
      const ox = Math.cos(angle) * orbit.rx * W;
      const oy = Math.sin(angle) * orbit.ry * W;
      // rotate by tilt
      const cosT = Math.cos(orbit.tilt);
      const sinT = Math.sin(orbit.tilt);
      return {
        x: orbit.cx * W + ox * cosT - oy * sinT,
        y: orbit.cy * H + ox * sinT + oy * cosT,
      };
    }

    // --- Main draw loop ---
    let raf;
    let lastTime = performance.now();

    function draw(now) {
      const dt = now - lastTime;
      lastTime = now;
      ctx.clearRect(0, 0, W, H);

      // --- Draw stars ---
      for (const star of stars) {
        const sx = (star.x / 1920) * W;
        const sy = (star.y / 1080) * H;
        let alpha = star.opacity;
        if (!prefersReduced && star.twinkle) {
          const flicker = Math.sin(now * 0.001 * star.twinkleSpeed + star.twinkleOffset);
          alpha = Math.max(0.05, alpha + flicker * 0.08);
        }
        ctx.beginPath();
        ctx.arc(sx, sy, star.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(210, 225, 240, ${alpha})`;
        ctx.fill();
      }

      // --- Draw orbital paths ---
      for (const orbit of orbits) {
        ctx.save();
        ctx.translate(orbit.cx * W, orbit.cy * H);
        ctx.rotate(orbit.tilt);
        ctx.beginPath();
        ctx.ellipse(0, 0, orbit.rx * W, orbit.ry * W, 0, 0, Math.PI * 2);
        ctx.strokeStyle = orbit.color;
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.restore();
      }

      // --- Update & draw tracked objects ---
      for (const obj of objects) {
        if (!prefersReduced) {
          obj.t = (obj.t + obj.speed * dt) % 1;
        }
        const pos = getOrbitPos(orbits[obj.orbit], obj.t);

        if (obj.type === "satellite") {
          // cyan/white core with tiny glow
          const grad = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, 5);
          grad.addColorStop(0, "rgba(180, 230, 255, 0.85)");
          grad.addColorStop(0.4, "rgba(100, 200, 240, 0.2)");
          grad.addColorStop(1, "rgba(53, 200, 255, 0)");
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, 5, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.fill();
          // solid core
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, 1.5, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(200, 240, 255, 0.9)";
          ctx.fill();

          // --- Trigger pulse occasionally near satellite ---
          if (!prefersReduced && now - lastPulseTime > 18000 + Math.random() * 12000) {
            pulse = { x: pos.x, y: pos.y, r: 0, maxR: 18, alpha: 0.55, startTime: now };
            lastPulseTime = now;
          }
        } else {
          // debris: muted blue-gray point, no glow
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, 1.2, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(120, 145, 165, 0.65)";
          ctx.fill();
        }
      }

      // --- Draw tracking pulse ---
      if (pulse && !prefersReduced) {
        const age = now - pulse.startTime;
        const progress = Math.min(age / 900, 1);
        pulse.r = progress * pulse.maxR;
        pulse.alpha = 0.55 * (1 - progress);
        if (pulse.alpha > 0.01) {
          ctx.beginPath();
          ctx.arc(pulse.x, pulse.y, pulse.r, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(53, 210, 255, ${pulse.alpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        } else {
          pulse = null;
        }
      }

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
