import { formatNumber, formatProbability } from "../utils/objectDetails";

function DetailRow({ label, value, unit }) {
  return (
    <div className="detail-row">
      <span className="eyebrow">{label}</span>
      <strong className="mono">{value}{unit && <small> {unit}</small>}</strong>
    </div>
  );
}

export default function ObjectDetailPanel({ object, onClose }) {
  if (!object) return null;

  const isSatellite = String(object.type).toLowerCase() === "satellite" || String(object.type).toLowerCase() === "payload";

  return (
    <aside className="object-detail hud-frame" aria-label={`${object.name} details`}>
      <div className="detail-heading">
        <div>
          <span className="eyebrow">Selected orbital object</span>
          <h2>{object.name}</h2>
          <span className="mono detail-id">ID // {object.id}</span>
        </div>
        <button className="close-button" type="button" onClick={onClose} aria-label="Close object details">
          ×
        </button>
      </div>

      <div className="risk-badge" style={{ color: object.risk.color, borderColor: object.risk.color }}>
        <span className="risk-dot" style={{ background: object.risk.color }} />
        {object.risk.label} risk
      </div>

      <div className="detail-grid">
        <DetailRow label="Risk score" value={formatNumber(object.riskScore, 2)} />
        <DetailRow label="Collision probability" value={formatProbability(object.collisionProbability)} />
        <DetailRow label="Miss distance" value={formatNumber(object.missDistance, 2)} unit={typeof object.missDistance === 'string' ? '' : 'km'} />
        <DetailRow label="Velocity" value={formatNumber(object.velocity, 1)} unit="km/s" />
        <DetailRow label="Rel. velocity" value={formatNumber(object.relativeVelocity, 1)} unit={typeof object.relativeVelocity === 'string' ? '' : 'km/s'} />
        <DetailRow label="Object type" value={object.type} />
        <DetailRow label="Orbital regime" value={object.regime} />
        {isSatellite && <DetailRow label="At-risk debris" value={object.atRiskDebrisCount} />}
      </div>
      
      {object.hasEvent && object.shapTop3?.length > 0 && (
        <div style={{ marginTop: '1rem', borderTop: '1px solid var(--hairline)', paddingTop: '1rem' }}>
          <span className="eyebrow" style={{ display: 'block', marginBottom: '0.5rem' }}>Top Risk Factors (SHAP)</span>
          {object.shapTop3.map((f, i) => (
            <DetailRow key={i} label={f.feature} value={formatNumber(f.contribution, 1)} unit="%" />
          ))}
        </div>
      )}

      {object.hasEvent && object.maneuverAdvisory && (
        <div style={{ marginTop: '1rem', borderTop: '1px solid var(--hairline)', paddingTop: '1rem' }}>
          <span className="eyebrow" style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--risk-nominal)' }}>Maneuver Advisory</span>
          <DetailRow label="Δv Required" value={formatNumber(object.maneuverAdvisory.delta_v_ms, 2)} unit="m/s" />
          <DetailRow label="Burn Direction" value={object.maneuverAdvisory.direction} />
          <DetailRow label="New Miss Dist." value={formatNumber(object.maneuverAdvisory.resulting_miss_distance_km, 2)} unit="km" />
        </div>
      )}

      <div className="detail-footer eyebrow">
        {object.hasEvent ? `Conjunction // ${object.eventId}` : "72h Horizon Clear"}
      </div>
    </aside>
  );
}
