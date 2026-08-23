import { useMemo, useState, useRef, useEffect } from "react";
import RadarLogo from "./shared/RadarLogo";
import { useAuth } from "../context/AuthContext";
import { useRouter } from "../context/Router";
import DatasetManager from "./DatasetManager";

const MODES = [
  { id: "dashboard", label: "Overview" },
  { id: "threat", label: "Threat Analysis" },
  { id: "launch", label: "Launch Planner" },
  { id: "solar", label: "Solar System" },
];

export default function TopBar({ mode, onChangeMode, _overallRiskStatus, objects, onSelectObject, timeControls }) {
  const { operator, logout } = useAuth();

  const { navigate } = useRouter();

  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const searchWrapRef = useRef(null);

  const [selectedIndex, setSelectedIndex] = useState(-1);

  useEffect(() => {
    function handleClickOutside(event) {
      if (searchWrapRef.current && !searchWrapRef.current.contains(event.target)) {
        setIsFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];

    return objects
      .filter((obj) => obj.name && String(obj.name).toLowerCase().includes(q))
      .sort((a, b) => {
        const nameA = String(a.name).toLowerCase();
        const nameB = String(b.name).toLowerCase();

        // Exact match
        const exactA = nameA === q;
        const exactB = nameB === q;
        if (exactA && !exactB) return -1;
        if (!exactA && exactB) return 1;

        // Starts with query
        const startsA = nameA.startsWith(q);
        const startsB = nameB.startsWith(q);
        if (startsA && !startsB) return -1;
        if (!startsA && startsB) return 1;

        // Alphabetical
        return nameA.localeCompare(nameB);
      })
      .slice(0, 8);
  }, [objects, query]);

  useEffect(() => {
    setSelectedIndex(-1);
  }, [matches]);

  function selectResult(object) {
    onSelectObject?.(object.object_id);
    setQuery("");
    setIsFocused(false);
    setSelectedIndex(-1);
  }

  function handleKeyDown(event) {
    if (event.key === "Escape") {
      setIsFocused(false);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelectedIndex((prev) => (matches.length > 0 ? (prev + 1) % matches.length : -1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelectedIndex((prev) => (matches.length > 0 ? (prev - 1 + matches.length) % matches.length : -1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < matches.length) {
        selectResult(matches[selectedIndex]);
      } else if (matches.length > 0) {
        selectResult(matches[0]);
      }
    }
  }

  const handleSignOut = () => {
    logout();
    navigate("/");
  };

  return (
    <>
      <header className="top-header hud-frame">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            onClick={() => navigate("/")}
            style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
            title="RADAR Overview // Click to return to landing"
          >
            <RadarLogo height={42} className="radar-topbar-logo" />
          </div>
        </div>


        {timeControls}

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div className="search-wrap" ref={searchWrapRef}>
            <label className="eyebrow search-label" htmlFor="object-search">Search objects</label>
            <input
              id="object-search"
              className="object-search mono"
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setIsFocused(true);
              }}
              onFocus={() => setIsFocused(true)}
              onKeyDown={handleKeyDown}
              placeholder="Search by object name..."
              autoComplete="off"
            />
            {isFocused && matches.length > 0 && (
              <div className="search-results" role="listbox" aria-label="Matching orbital objects">
                {matches.map((object, idx) => (
                  <button
                    className={`search-result ${idx === selectedIndex ? "active" : ""}`}
                    type="button"
                    key={object.object_id}
                    onClick={() => selectResult(object)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <span><strong>{object.name}</strong><small className="mono">ID // {object.object_id}</small></span>
                    <span className="search-risk">{object.risk_tier}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Operator status & Logout */}
          <div className="topbar-operator-cluster mono">
            <div className="topbar-operator-info">
              <span className="eyebrow" style={{ fontSize: 8 }}>OPERATOR</span>
              <div style={{ fontSize: 10.5, fontWeight: 600, color: "var(--signal)", whiteSpace: "nowrap" }}>
                {operator?.callsign || "OP // AUTHORIZED"}
              </div>
            </div>
            <button
              type="button"
              className="topbar-exit-btn mono"
              onClick={handleSignOut}
              title="Sign out and return to landing"
            >
              [ EXIT ]
            </button>
          </div>
        </div>
      </header>

      <aside className="navigation-rail hud-frame">
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
        <DatasetManager />
      </aside>
    </>
  );
}
