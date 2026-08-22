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
        <DetailRow label="Miss distance" value={formatNumber(object.missDistance, 2)} unit="km" />
        <DetailRow label={object.velocityLabel} value={formatNumber(object.velocity, 1)} unit="km/s" />
        <DetailRow label="Object type" value={object.type} />
        <DetailRow label="Orbital regime" value={object.regime} />
      </div>

      <div className="detail-footer eyebrow">
        {object.eventId ? `Conjunction // ${object.eventId}` : "No active conjunction assessment"}
      </div>
    </aside>
  );
}
