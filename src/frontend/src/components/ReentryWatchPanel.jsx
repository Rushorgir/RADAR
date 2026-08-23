import { useEffect, useState } from "react";
import { fetchReentryPath, fetchReentryWatch } from "../utils/apiClient";

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
//
// Clicking a watched object additionally fetches its descent path
// (GET /api/reentry/{id}/path, src/propagation/reentry.py
// generate_descent_waypoints -- a simplified "current altitude down to 0,
// same ground track" corridor, the descent mirror of the launch corridor
// above it) and hands the waypoints up to GlobeView via onPathChange to draw
// on the globe.
export default function ReentryWatchPanel({ onPathChange }) {
  const [predictions, setPredictions] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | done | error
  const [selectedId, setSelectedId] = useState(null);
  const [pathStatus, setPathStatus] = useState("idle"); // idle | loading | error
  const [pathError, setPathError] = useState(null);

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

  // Clear the globe's descent-path overlay when this panel unmounts, same
  // reasoning as LaunchPlanner's corridor cleanup -- don't leave a stale
  // path drawn over whatever mode the user switches to next.
  useEffect(() => () => onPathChange?.(null), [onPathChange]);

  async function selectPrediction(p) {
    if (selectedId === p.object_id) {
      setSelectedId(null);
      setPathStatus("idle");
      onPathChange?.(null);
      return;
    }
    setSelectedId(p.object_id);
    setPathStatus("loading");
    setPathError(null);
    try {
      const path = await fetchReentryPath(p.object_id);
      setPathStatus("done");
      onPathChange?.(path.waypoints, { objectId: path.object_id, name: path.name });
    } catch (err) {
      setPathStatus("error");
      setPathError(err.message);
      onPathChange?.(null);
    }
  }

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

      {status === "done" && predictions.length > 0 && (
        <div className="mono" style={{ fontSize: 10.5, color: "var(--text-dim)", marginBottom: 10 }}>
          Select an object to plot its descent path on the globe.
        </div>
      )}

      {predictions.map((p) => {
        const color = `var(${TIER_COLOR_VAR[p.risk_tier] ?? "--text-dim"})`;
        const isSelected = selectedId === p.object_id;
        return (
          <div key={p.object_id}>
            <button
              type="button"
              onClick={() => selectPrediction(p)}
              aria-pressed={isSelected}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                background: isSelected ? "var(--panel-raised)" : "transparent",
                border: "1px solid var(--hairline)",
                borderLeft: `2.5px solid ${color}`,
                borderRadius: 2,
                padding: 10,
                marginBottom: isSelected ? 0 : 8,
                cursor: "pointer",
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
            </button>

            {isSelected && (
              <div
                className="mono"
                style={{
                  fontSize: 11,
                  padding: "8px 10px",
                  marginBottom: 8,
                  border: "1px solid var(--hairline)",
                  borderTop: "none",
                  borderLeft: `2.5px solid ${color}`,
                  borderRadius: "0 0 2px 2px",
                  color: "var(--text-dim)",
                }}
              >
                {pathStatus === "loading" && "Plotting descent path…"}
                {pathStatus === "error" && (
                  <span style={{ color: "var(--risk-critical)" }}>{pathError}</span>
                )}
                {pathStatus === "done" && (
                  <span style={{ color: "var(--signal)" }}>
                    Descent path plotted on the globe (current altitude → surface, ground track held fixed).
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
