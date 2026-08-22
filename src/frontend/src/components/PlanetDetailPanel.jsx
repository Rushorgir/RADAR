import { SUN, PLANETS } from "../data/solarSystemData";

function DetailRow({ label, value, unit }) {
  return (
    <div className="detail-row">
      <span className="eyebrow">{label}</span>
      <strong className="mono">{value}{unit && <small> {unit}</small>}</strong>
    </div>
  );
}

function formatDays(days) {
  if (days >= 365) return `${(days / 365.25).toFixed(1)} yr`;
  return `${days.toFixed(0)} days`;
}

function formatDayLength(hours) {
  if (hours >= 48) return `${(hours / 24).toFixed(1)} Earth days`;
  return `${hours.toFixed(1)} hours`;
}

export default function PlanetDetailPanel({ bodyId, onClose }) {
  if (!bodyId) return null;

  if (bodyId === SUN.id) {
    return (
      <aside className="object-detail hud-frame" aria-label="Sun details">
        <div className="detail-heading">
          <div>
            <span className="eyebrow">Solar system</span>
            <h2>{SUN.name}</h2>
            <span className="mono detail-id">STAR // G-TYPE</span>
          </div>
          <button className="close-button" type="button" onClick={onClose} aria-label="Close body details">
            ×
          </button>
        </div>
        <div className="detail-grid">
          <DetailRow label="Mean radius" value={SUN.meanRadiusKm.toLocaleString()} unit="km" />
        </div>
        <div className="detail-footer eyebrow">{SUN.description}</div>
      </aside>
    );
  }

  const planet = PLANETS.find((p) => p.id === bodyId);
  if (!planet) return null;

  return (
    <aside className="object-detail hud-frame" aria-label={`${planet.name} details`}>
      <div className="detail-heading">
        <div>
          <span className="eyebrow">Solar system</span>
          <h2>{planet.name}</h2>
          <span className="mono detail-id">
            {PLANETS.indexOf(planet) + 1} // FROM SUN
          </span>
        </div>
        <button className="close-button" type="button" onClick={onClose} aria-label="Close body details">
          ×
        </button>
      </div>

      <div className="detail-grid">
        <DetailRow label="Distance from Sun" value={planet.distanceAU} unit="AU" />
        <DetailRow label="Mean radius" value={planet.meanRadiusKm.toLocaleString()} unit="km" />
        <DetailRow label="Orbital period" value={formatDays(planet.orbitalPeriodDays)} />
        <DetailRow label="Day length" value={formatDayLength(planet.dayLengthHours)} />
        <DetailRow
          label="Notable moons"
          value={planet.notableMoons.length > 0 ? planet.notableMoons.join(", ") : "None"}
        />
      </div>

      <div className="detail-footer eyebrow">{planet.description}</div>
    </aside>
  );
}
