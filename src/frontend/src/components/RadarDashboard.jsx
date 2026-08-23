import { useEffect, useState } from "react";
import * as Cesium from "cesium";
import GlobeView from "./GlobeView";
import SolarSystemView from "./SolarSystemView";
import TopBar from "./TopBar";
import StatCluster from "./StatCluster";
import RiskPanel from "./RiskPanel";
import LaunchPlanner from "./LaunchPlanner";
import ReentryWatchPanel from "./ReentryWatchPanel";
import ScanSweep from "./ScanSweep";
import ObjectDetailPanel from "./ObjectDetailPanel";
import PlanetDetailPanel from "./PlanetDetailPanel";
import RiskLegend from "./RiskLegend";
import TimeControls from "./TimeControls";
import { mockObjects, mockRiskList, mockDashboardStats } from "../data/mockData";
import { buildObjectDetail, normalizeId } from "../utils/objectDetails";
import { loadLiveDashboardData } from "../utils/liveData";

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

export default function RadarDashboard() {
  const [mode, setMode] = useState("dashboard"); // dashboard | threat | launch | solar
  const [showSweep, setShowSweep] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedBodyId, setSelectedBodyId] = useState(null);
  const [corridorWaypoints, setCorridorWaypoints] = useState(null);
  const [activeFilters, setActiveFilters] = useState([]);
  const [currentTime, setCurrentTime] = useState(() => Cesium.JulianDate.toDate(simulationClock.currentTime));

  useEffect(() => {
    let lastRealTime = performance.now();
    let lastDisplayedSecond = Math.floor(Cesium.JulianDate.toDate(simulationClock.currentTime).getTime() / 1000);
    const syncTime = (clock) => {
      const now = performance.now();
      if (now - lastRealTime < 200) return; // at most 5 renders per real second
      
      const date = Cesium.JulianDate.toDate(clock.currentTime);
      const displayedSecond = Math.floor(date.getTime() / 1000);
      if (displayedSecond === lastDisplayedSecond) return;
      
      lastRealTime = now;
      lastDisplayedSecond = displayedSecond;
      setCurrentTime(date);
    };
    simulationClock.onTick.addEventListener(syncTime);
    return () => simulationClock.onTick.removeEventListener(syncTime);
  }, []);

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
            rangeStart={Cesium.JulianDate.toDate(simulationClock.startTime)}
            rangeStop={Cesium.JulianDate.toDate(simulationClock.stopTime)}
            onSeek={(date) => {
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
