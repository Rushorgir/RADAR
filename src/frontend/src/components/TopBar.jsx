import { useMemo, useState } from "react";
import logoUrl from "../assets/radar-logo.svg";

const MODES = [
  { id: "dashboard", label: "Overview" },
  { id: "threat", label: "Threat Analysis" },
  { id: "launch", label: "Launch Planner" },
  { id: "solar", label: "Solar System" },
];

export default function TopBar({ mode, onChangeMode, overallRiskStatus, objects, onSelectObject }) {
  const [query, setQuery] = useState("");
  const matches = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return [];
    return objects
      .filter((object) => `${object.object_id} ${object.name} ${object.type}`.toLowerCase().includes(normalizedQuery))
      .slice(0, 8);
  }, [objects, query]);

  function selectResult(object) {
    onSelectObject?.(object.object_id);
    setQuery("");
  }

  return (
    <>
      <header className="top-header hud-frame">
        <img className="radar-logo" src={logoUrl} alt="RADAR — Risk Assessment and Debris Avoidance Routing" />
        <div className="search-wrap">
          <label className="eyebrow search-label" htmlFor="object-search">Search objects</label>
          <input
            id="object-search"
            className="object-search mono"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search satellite / debris ID"
            autoComplete="off"
          />
          {matches.length > 0 && (
            <div className="search-results" role="listbox" aria-label="Matching orbital objects">
              {matches.map((object) => (
                <button className="search-result" type="button" key={object.object_id} onClick={() => selectResult(object)}>
                  <span><strong>{object.name}</strong><small className="mono">ID // {object.object_id}</small></span>
                  <span className="search-risk">{object.risk_tier}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="header-status"><span className={`status-dot risk-${overallRiskStatus === "elevated" ? "high" : overallRiskStatus}`} /><span className="mono">SYSTEM: ACTIVE</span></div>
      </header>
      <aside className="navigation-rail hud-frame">
        <div className="brand-block">
          <strong className="brand-name">RADAR</strong>
          <span className="eyebrow">Space debris intelligence</span>
        </div>
      <span className="eyebrow nav-heading">Navigation</span>
      <nav className="mode-nav" aria-label="Primary navigation">
        {MODES.map((m) => {
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onChangeMode(m.id)}
              className={active ? "mode-button active" : "mode-button"}
            >
              {m.label}
            </button>
          );
        })}
      </nav>
      <div className="system-status">
        <span className={`status-dot risk-${overallRiskStatus === "elevated" ? "high" : overallRiskStatus}`} />
        <span className="mono">SYSTEM: ACTIVE</span>
      </div>
      </aside>
    </>
  );
}
