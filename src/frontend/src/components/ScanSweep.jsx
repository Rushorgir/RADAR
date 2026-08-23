import { useEffect, useState } from "react";

// Plays once, ~0.65s, then unmounts itself. Fast, non-intrusive orbital sweep.
export default function ScanSweep({ onComplete }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 650);
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
          animation: "og-pulse 0.65s ease-out forwards",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "conic-gradient(from 0deg, transparent 0deg, var(--signal-dim) 25deg, transparent 55deg)",
            animation: "og-sweep 0.65s linear",
          }}
        />
      </div>
      <div
        className="eyebrow mono"
        style={{
          position: "absolute",
          color: "var(--signal)",
          letterSpacing: "0.2em",
          animation: "og-fade 0.65s ease-out forwards",
        }}
      >
        ANALYZING ORBITAL ENVIRONMENT
      </div>
      <style>{`
        @keyframes og-sweep {
          from { transform: rotate(0deg); }
          to { transform: rotate(720deg); }
        }
        @keyframes og-pulse {
          0% { opacity: 0; transform: scale(0.85); }
          15% { opacity: 1; }
          65% { opacity: 0.8; }
          100% { opacity: 0; transform: scale(1.08); }
        }
        @keyframes og-fade {
          0% { opacity: 0; transform: translateY(4px); }
          15% { opacity: 1; transform: translateY(0); }
          55% { opacity: 1; }
          85%, 100% { opacity: 0; transform: translateY(-4px); }
        }
      `}</style>
    </div>
  );
}
