import { useState } from "react";

// Deliberately minimal: build Overview + Threat Analysis solidly first.
// This panel just captures inputs and shows a placeholder result --
// wire the "Generate Route" handler to Web's real endpoint when it exists.
export default function LaunchPlanner() {
  const [launchSite, setLaunchSite] = useState("Sriharikota, IN");
  const [targetAltitude, setTargetAltitude] = useState(550);
  const [status, setStatus] = useState("idle"); // idle | analyzing | ready

  function generateRoute() {
    setStatus("analyzing");
    setTimeout(() => setStatus("ready"), 1200); // placeholder for real API call
  }

  return (
    <div
      className="hud-frame"
      style={{
        position: "absolute",
        top: 84,
        right: 18,
        width: 340,
        zIndex: 20,
        padding: 16,
      }}
    >
      <div className="eyebrow" style={{ marginBottom: 14 }}>
        Safe Launch Route Planner
      </div>

      <label className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
        Launch Site
      </label>
      <input
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
      />

      <label className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
        Target Altitude (km)
      </label>
      <input
        type="number"
        value={targetAltitude}
        onChange={(e) => setTargetAltitude(Number(e.target.value))}
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
        disabled={status === "analyzing"}
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
        {status === "analyzing" ? "Analyzing Debris Field…" : "Generate Safe Route"}
      </button>

      {status === "ready" && (
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
          Route generated: {launchSite} → {targetAltitude} km circular orbit.
          <br />
          3 candidate trajectories screened, 1 unsafe segment discarded.
          <br />
          <span style={{ color: "var(--signal)" }}>Selected route avoids 4 tracked debris clusters.</span>
        </div>
      )}
    </div>
  );
}
