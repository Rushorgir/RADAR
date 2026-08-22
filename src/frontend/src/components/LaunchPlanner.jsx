import { useEffect, useState } from "react";
import { checkLaunchSafety, fetchLaunchSites } from "../utils/apiClient";

// Real launch corridor safety check (src/propagation/launch_corridor.py):
// a simplified ascent path from a real launch site to a target altitude,
// checked against the currently tracked catalog's actual SGP4-propagated
// positions along the ascent timeline. Not a substitute for a real
// flight-safety trajectory analysis -- see that module's docstring for
// exactly what's simplified and why.
export default function LaunchPlanner({ onCorridorChange }) {
  const [sites, setSites] = useState([]);
  const [launchSite, setLaunchSite] = useState("");
  const [targetAltitude, setTargetAltitude] = useState(550);
  const [status, setStatus] = useState("idle"); // idle | checking | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchLaunchSites()
      .then((list) => {
        if (cancelled) return;
        setSites(list);
        setLaunchSite((current) => current || list[0]?.name || "");
      })
      .catch((err) => {
        console.warn("[RADAR] Launch sites unavailable:", err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Clear the globe's corridor overlay when this panel unmounts (leaving
  // Launch Planner mode) rather than leaving a stale path drawn over
  // whatever mode the user switches to next.
  useEffect(() => () => onCorridorChange?.(null), [onCorridorChange]);

  async function generateRoute() {
    if (!launchSite) return;
    setStatus("checking");
    setError(null);
    try {
      const safety = await checkLaunchSafety({
        launch_site: launchSite,
        target_altitude_km: Number(targetAltitude),
      });
      setResult(safety);
      setStatus("done");
      onCorridorChange?.(safety.waypoints);
    } catch (err) {
      setError(err.message);
      setStatus("error");
      onCorridorChange?.(null);
    }
  }

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 14 }}>
        Safe Launch Route Planner
      </div>

      <label className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
        Launch Site
      </label>
      <select
        value={launchSite}
        onChange={(e) => setLaunchSite(e.target.value)}
        className="mono"
        style={{
          width: "100%",
          background: "var(--panel-raised)",
          border: "1px solid var(--hairline)",
          borderRadius: 2,
          color: "var(--text-primary)",
          padding: "8px 10px",
          fontSize: 12.5,
          marginBottom: 14,
        }}
      >
        {sites.length === 0 && <option value="">Loading sites…</option>}
        {sites.map((site) => (
          <option key={site.name} value={site.name}>
            {site.name}
          </option>
        ))}
      </select>

      <label className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
        Target Altitude (km)
      </label>
      <input
        type="number"
        value={targetAltitude}
        onChange={(e) => setTargetAltitude(e.target.value)}
        min={100}
        max={2000}
        className="mono"
        style={{
          width: "100%",
          background: "var(--panel-raised)",
          border: "1px solid var(--hairline)",
          borderRadius: 2,
          color: "var(--text-primary)",
          padding: "8px 10px",
          fontSize: 12.5,
          marginBottom: 18,
        }}
      />

      <button
        onClick={generateRoute}
        disabled={status === "checking" || !launchSite}
        style={{
          width: "100%",
          background: "var(--signal-dim)",
          color: "var(--signal)",
          border: "1px solid var(--signal-line)",
          borderRadius: 2,
          padding: "10px 0",
          fontFamily: "var(--font-mono)",
          fontSize: 11.5,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        {status === "checking" ? "Screening Ascent Corridor…" : "Generate Safe Route"}
      </button>

      {status === "error" && (
        <div
          className="mono"
          style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--hairline)", fontSize: 11.5, color: "var(--risk-critical)" }}
        >
          {error}
        </div>
      )}

      {status === "done" && result && (
        <div
          className="mono"
          style={{
            marginTop: 14,
            paddingTop: 14,
            borderTop: "1px solid var(--hairline)",
            fontSize: 12,
            lineHeight: 1.7,
            color: "var(--text-secondary)",
          }}
        >
          {launchSite} → {targetAltitude} km circular orbit.
          <br />
          {result.objects_checked} tracked objects screened along the ascent corridor
          (±{result.safety_radius_km} km).
          {result.safe ? (
            <>
              <br />
              <span style={{ color: "var(--signal)" }}>
                No conflicts found — corridor is clear.
              </span>
            </>
          ) : (
            <>
              <br />
              <span style={{ color: "var(--risk-critical)" }}>
                {result.conflicts.length} conflict{result.conflicts.length === 1 ? "" : "s"} detected:
              </span>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {result.conflicts.slice(0, 5).map((c, i) => (
                  <li key={`${c.object_id}-${i}`}>
                    {c.object_name} — {c.distance_km.toFixed(1)} km at T+{Math.round(c.waypoint_elapsed_s)}s
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
