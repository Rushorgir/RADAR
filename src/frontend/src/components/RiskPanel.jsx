import { getRiskColorVar } from "../data/mockData";

function FeatureBar({ feature, contribution }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10.5,
          color: "var(--text-secondary)",
          marginBottom: 3,
        }}
        className="mono"
      >
        <span>{feature.replace(/_/g, " ")}</span>
        <span>{(contribution * 100).toFixed(0)}%</span>
      </div>
      <div style={{ height: 3, background: "var(--hairline)", borderRadius: 2 }}>
        <div
          style={{
            width: `${contribution * 100}%`,
            height: "100%",
            background: "var(--signal)",
            borderRadius: 2,
          }}
        />
      </div>
    </div>
  );
}

export default function RiskPanel({ riskList, selectedEventId, onSelectEvent }) {
  return (
    <div
      className="hud-frame scrollbar-thin"
      style={{
        position: "absolute",
        top: 84,
        right: 18,
        bottom: 18,
        width: 340,
        zIndex: 20,
        overflowY: "auto",
        padding: 16,
      }}
    >
      <div className="eyebrow" style={{ marginBottom: 12 }}>
        Flagged Conjunctions // {riskList.length}
      </div>

      {riskList.map((event) => {
        const active = event.event_id === selectedEventId;
        const color = getRiskColorVar(event.risk_tier);
        return (
          <div
            key={event.event_id}
            onClick={() => onSelectEvent(active ? null : event.event_id)}
            style={{
              border: `1px solid ${active ? "var(--hairline-strong)" : "var(--hairline)"}`,
              borderLeft: `2.5px solid ${color}`,
              borderRadius: 2,
              padding: 12,
              marginBottom: 10,
              cursor: "pointer",
              background: active ? "var(--panel-raised)" : "transparent",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>
                {event.primary_name} × {event.secondary_name}
              </span>
              <span className="mono" style={{ fontSize: 10, color }}>
                {event.event_id}
              </span>
            </div>

            <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
              <div>
                <div className="eyebrow">Pc</div>
                <div className="mono" style={{ fontSize: 13 }}>
                  {event.pc.toExponential(1)}
                </div>
              </div>
              <div>
                <div className="eyebrow">Miss Dist.</div>
                <div className="mono" style={{ fontSize: 13 }}>
                  {event.miss_distance_km.toFixed(2)} km
                </div>
              </div>
              <div>
                <div className="eyebrow">Rel. Vel.</div>
                <div className="mono" style={{ fontSize: 13 }}>
                  {event.relative_velocity_kms.toFixed(1)} km/s
                </div>
              </div>
            </div>

            {active && (
              <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--hairline)" }}>
                <div className="eyebrow" style={{ marginBottom: 8 }}>
                  Top Risk Factors (SHAP)
                </div>
                {event.shap_top3.map((f) => (
                  <FeatureBar key={f.feature} {...f} />
                ))}

                {event.maneuver_advisory ? (
                  <div style={{ marginTop: 10 }}>
                    <div className="eyebrow" style={{ marginBottom: 6 }}>
                      Maneuver Advisory
                    </div>
                    <div className="mono" style={{ fontSize: 12, lineHeight: 1.6 }}>
                      Δv {event.maneuver_advisory.delta_v_ms.toFixed(3)} m/s (
                      {event.maneuver_advisory.direction}) → miss distance{" "}
                      {event.maneuver_advisory.resulting_miss_distance_km.toFixed(1)} km
                    </div>
                  </div>
                ) : (
                  <div className="mono" style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 10 }}>
                    No maneuver required at current risk level.
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
