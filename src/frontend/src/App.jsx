import { useEffect, useState } from "react";
import * as Cesium from "cesium";
import GlobeView from "./components/GlobeView";
import SolarSystemView from "./components/SolarSystemView";
import TopBar from "./components/TopBar";
import StatCluster from "./components/StatCluster";
import RiskPanel from "./components/RiskPanel";
import LaunchPlanner from "./components/LaunchPlanner";
import ReentryWatchPanel from "./components/ReentryWatchPanel";
import ScanSweep from "./components/ScanSweep";
import ObjectDetailPanel from "./components/ObjectDetailPanel";
import PlanetDetailPanel from "./components/PlanetDetailPanel";
import RiskLegend from "./components/RiskLegend";
import TimeControls from "./components/TimeControls";
import { mockObjects, mockRiskList, mockDashboardStats } from "./data/mockData";
import { buildObjectDetail, normalizeId } from "./utils/objectDetails";
import { loadLiveDashboardData } from "./utils/liveData";

const simulationClock = createSimulationClock();

function createSimulationClock() {
  const now = Cesium.JulianDate.now();
  return new Cesium.Clock({
    startTime: Cesium.JulianDate.addDays(now, -30, new Cesium.JulianDate()),
    currentTime: now,
    stopTime: Cesium.JulianDate.addDays(now, 30, new Cesium.JulianDate()),
    clockRange: Cesium.ClockRange.CLAMPED,
    clockStep: Cesium.ClockStep.SYSTEM_CLOCK_MULTIPLIER,
    multiplier: 1,
    shouldAnimate: true,
  });
}

export default function App() {
  const [mode, setMode] = useState("dashboard"); // dashboard | threat | launch | solar
  const [showSweep, setShowSweep] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedBodyId, setSelectedBodyId] = useState(null);
  const [corridorWaypoints, setCorridorWaypoints] = useState(null);
  const [activeFilters, setActiveFilters] = useState([]);
  const [currentTime, setCurrentTime] = useState(() => Cesium.JulianDate.toDate(simulationClock.currentTime));

  useEffect(() => {
    // onTick fires on every render frame (~60/sec) while the globe's Cesium
    // Viewer is running -- setCurrentTime unconditionally on every tick was
    // forcing a full re-render of the entire dashboard tree (TopBar,
    // StatCluster, RiskPanel, GlobeView, ...) 60 times a second, which is
    // exactly the kind of thing that reads as "laggy," and gets worse the
    // faster the simulated clock runs (more visually-distinct seconds
    // passing, same 60 renders/sec either way). TimeControls only ever
    // displays whole seconds, so only re-render when the displayed second
    // actually changes -- typically ~1/sec at real-time speed instead of 60.
    let lastDisplayedSecond = Math.floor(Cesium.JulianDate.toDate(simulationClock.currentTime).getTime() / 1000);
    const syncTime = (clock) => {
      const date = Cesium.JulianDate.toDate(clock.currentTime);
      const displayedSecond = Math.floor(date.getTime() / 1000);
      if (displayedSecond === lastDisplayedSecond) return;
      lastDisplayedSecond = displayedSecond;
      setCurrentTime(date);
    };
    simulationClock.onTick.addEventListener(syncTime);
    return () => simulationClock.onTick.removeEventListener(syncTime);
  }, []);

  // Start with mock data so the UI renders immediately; swap in real data
  // from the backend if/when it loads. If the backend isn't running (e.g.
  // a frontend-only demo), this fails silently and mock data stays put --
  // see src/frontend/src/utils/liveData.js for exactly what's real vs.
  // still a placeholder (AI-3's ML risk/SHAP/maneuver output doesn't exist
  // yet, so those fields stay empty even once live data loads).
  const [objects, setObjects] = useState(mockObjects);
  const [riskList, setRiskList] = useState(mockRiskList);
  const [dashboardStats, setDashboardStats] = useState(mockDashboardStats);

  useEffect(() => {
    let cancelled = false;
    loadLiveDashboardData()
      .then((live) => {
        if (cancelled) return;
        setObjects(live.objects);
        setRiskList(live.riskList);
        setDashboardStats(live.dashboardStats);
      })
      .catch((err) => {
        console.warn("[RADAR] Backend unreachable, using mock data:", err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleObjects = activeFilters.length === 0 ? objects : objects.filter((object) => {
    const isSatellite = object.type === "satellite";
    const isHighRisk = ["critical", "elevated", "high"].includes(object.risk_tier);
    return activeFilters.some((filter) => {
      if (filter === "active_satellites" || filter === "active_missions") return isSatellite;
      if (filter === "tracked_debris") return !isSatellite;
      if (filter === "high_risk_objects") return isHighRisk;
      if (filter === "affected_satellites") return isSatellite && isHighRisk;
      return true;
    });
  });
  const selectedObject = objects.find((object) => normalizeId(object.object_id) === normalizeId(selectedObjectId));
  const objectDetail = buildObjectDetail(selectedObject, riskList);

  function handleChangeMode(nextMode) {
    if (nextMode === "threat" && mode !== "threat") {
      setShowSweep(true);
    }
    setMode(nextMode);
  }

  function handleFilterChange(filterKey) {
    setActiveFilters((current) => current.includes(filterKey)
      ? current.filter((filter) => filter !== filterKey)
      : [...current, filterKey]);
  }

  function selectObject(objectId) {
    setActiveFilters([]);
    setSelectedObjectId(objectId);
  }

  const isSolar = mode === "solar";

  return (
    <div className="radar-shell">
      {isSolar ? (
        <SolarSystemView
          selectedBodyId={selectedBodyId}
          onSelectBody={setSelectedBodyId}
          simulationClock={simulationClock}
        />
      ) : (
        <GlobeView
          objects={visibleObjects}
          mode={mode}
          selectedObjectId={selectedObjectId}
          onSelectObject={selectObject}
          corridorWaypoints={corridorWaypoints}
          simulationClock={simulationClock}
        />
      )}

      <TopBar
        mode={mode}
        onChangeMode={handleChangeMode}
        overallRiskStatus={dashboardStats.overall_risk_status}
        objects={objects}
        onSelectObject={selectObject}
        timeControls={
          <TimeControls
            currentTime={currentTime}
            playing={simulationClock.shouldAnimate}
            playbackRate={simulationClock.multiplier}
            onTogglePlay={() => { simulationClock.shouldAnimate = !simulationClock.shouldAnimate; setCurrentTime(Cesium.JulianDate.toDate(simulationClock.currentTime)); }}
            onSetRate={(rate) => { simulationClock.multiplier = rate; simulationClock.shouldAnimate = true; }}
            onStep={(milliseconds) => {
              simulationClock.currentTime = Cesium.JulianDate.addSeconds(
                simulationClock.currentTime,
                milliseconds / 1000,
                new Cesium.JulianDate(),
              );
              setCurrentTime(Cesium.JulianDate.toDate(simulationClock.currentTime));
            }}
            onSelectDate={(date) => {
              simulationClock.currentTime = Cesium.JulianDate.fromDate(date);
              setCurrentTime(date);
            }}
          />
        }
      />

      {mode === "dashboard" && (
        <StatCluster
          stats={dashboardStats}
          activeFilters={activeFilters}
          onToggleFilter={handleFilterChange}
          onSelectAll={() => setActiveFilters([])}
        />
      )}

      {mode === "threat" && (
        <RiskPanel
          riskList={riskList}
          selectedEventId={selectedEventId}
          onSelectEvent={setSelectedEventId}
          onSelectObject={setSelectedObjectId}
        />
      )}

      {mode === "launch" && (
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
          <LaunchPlanner onCorridorChange={setCorridorWaypoints} />
          <div style={{ height: 24, borderTop: "1px solid var(--hairline)", marginBottom: 16 }} />
          <ReentryWatchPanel />
        </div>
      )}

      {isSolar ? (
        <PlanetDetailPanel bodyId={selectedBodyId} onClose={() => setSelectedBodyId(null)} />
      ) : (
        <>
          <ObjectDetailPanel object={objectDetail} onClose={() => setSelectedObjectId(null)} />
          <RiskLegend />
        </>
      )}

      {showSweep && <ScanSweep onComplete={() => setShowSweep(false)} />}
    </div>
  );
}
