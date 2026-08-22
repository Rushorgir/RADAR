import { useEffect, useState } from "react";
import { fetchReentryWatch } from "../utils/apiClient";

const TIER_COLOR_VAR = {
  IMMINENT: "--risk-critical",
  ELEVATED: "--risk-elevated",
  WATCH: "--risk-medium",
};

function formatDaysToReentry(days) {
  if (days === null || days === undefined) return "—";
  if (days <= 0) return "imminent";
  if (days < 1) return "<1 day";
  return `~${Math.round(days)} day${Math.round(days) === 1 ? "" : "s"}`;
}

// Real orbital-decay risk assessment (src/propagation/reentry.py), computed
// live from each tracked object's own TLE elements. See that module's
// docstring for exactly what "estimated days to re-entry" honestly can and
// can't tell you -- it's a coarse triage ranking, not a delivery date.
export default function ReentryWatchPanel() {
  const [predictions, setPredictions] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | done | error

  useEffect(() => {
    let cancelled = false;
    fetchReentryWatch()
      .then((data) => {
        if (cancelled) return;
        setPredictions(data.predictions);
        setStatus("done");
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn("[RADAR] Re-entry watch unavailable:", err.message);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 12 }}>
        Re-entry Watch {status === "done" && `// ${predictions.length}`}
      </div>

      {status === "loading" && (
        <div className="mono" style={{ fontSize: 11.5, color: "var(--text-dim)" }}>
          Screening catalog for decaying orbits…
        </div>
      )}

      {status === "error" && (
        <div className="mono" style={{ fontSize: 11.5, color: "var(--text-dim)" }}>
          Re-entry watch unavailable (backend unreachable).
        </div>
      )}

      {status === "done" && predictions.length === 0 && (
        <div className="mono" style={{ fontSize: 11.5, color: "var(--text-dim)" }}>
          No tracked objects currently flagged for decay watch.
        </div>
      )}

      {predictions.map((p) => {
        const color = `var(${TIER_COLOR_VAR[p.risk_tier] ?? "--text-dim"})`;
        return (
          <div
            key={p.object_id}
            style={{
              border: "1px solid var(--hairline)",
              borderLeft: `2.5px solid ${color}`,
              borderRadius: 2,
              padding: 10,
              marginBottom: 8,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span className="mono" style={{ fontSize: 12, fontWeight: 600 }}>
                {p.name}
              </span>
              <span className="mono eyebrow" style={{ color }}>
                {p.risk_tier}
              </span>
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
              <div>
                <div className="eyebrow">Perigee</div>
                <div className="mono" style={{ fontSize: 12.5 }}>{p.perigee_altitude_km.toFixed(0)} km</div>
              </div>
              <div>
                <div className="eyebrow">Est. Re-entry</div>
                <div className="mono" style={{ fontSize: 12.5 }}>
                  {p.sgp4_confirmed_decayed ? "confirmed decayed" : formatDaysToReentry(p.estimated_days_to_reentry)}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
