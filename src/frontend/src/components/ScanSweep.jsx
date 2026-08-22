import { useEffect, useState } from "react";

// Plays once, ~1.4s, then unmounts itself. This is the "system is analyzing
// the orbital environment" beat called out in the project brief.
export default function ScanSweep({ onComplete }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 1400);
    return () => clearTimeout(t);
  }, [onComplete]);

  if (!visible) return null;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 40,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "70vmin",
          height: "70vmin",
          borderRadius: "50%",
          border: "1px solid var(--signal-line)",
          position: "relative",
          overflow: "hidden",
          animation: "og-pulse 1.4s ease-out forwards",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "conic-gradient(from 0deg, transparent 0deg, var(--signal-dim) 25deg, transparent 55deg)",
            animation: "og-sweep 1.4s linear",
          }}
        />
      </div>
      <div
        className="eyebrow mono"
        style={{
          position: "absolute",
          color: "var(--signal)",
          letterSpacing: "0.2em",
          animation: "og-fade 1.4s ease-in-out",
        }}
      >
        ANALYZING ORBITAL ENVIRONMENT
      </div>
      <style>{`
        @keyframes og-sweep {
          from { transform: rotate(0deg); }
          to { transform: rotate(1080deg); }
        }
        @keyframes og-pulse {
          0% { opacity: 0; transform: scale(0.85); }
          15% { opacity: 1; }
          85% { opacity: 1; }
          100% { opacity: 0; transform: scale(1.05); }
        }
        @keyframes og-fade {
          0%, 100% { opacity: 0; }
          20%, 80% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
