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
import { useDataset } from "../context/DatasetContext";

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
  const { dataset } = useDataset();
  const [mode, setMode] = useState("dashboard"); // dashboard | threat | launch | solar
  const [showSweep, setShowSweep] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedBodyId, setSelectedBodyId] = useState(null);
  const [corridorWaypoints, setCorridorWaypoints] = useState(null);
  const [reentryPath, setReentryPath] = useState(null); // { waypoints, objectId, name } | null
  const [activeFilters, setActiveFilters] = useState([]);
  const [currentTime, setCurrentTime] = useState(() => Cesium.JulianDate.toDate(simulationClock.currentTime));

  const [isDatasetLoading, setIsDatasetLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingStep, setLoadingStep] = useState("");

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

  const reloadVisuals = async (targetDataset) => {
    const ds = targetDataset || dataset;
    setSelectedObjectId(null);
    setSelectedEventId(null);
    setIsDatasetLoading(true);
    setLoadingProgress(25);
    setLoadingStep(`Connecting to [${ds.toUpperCase()}] database...`);

    try {
      setLoadingProgress(50);
      setLoadingStep(`Propagating orbital ephemerides for [${ds.toUpperCase()}]...`);

      const [live] = await Promise.all([
        loadLiveDashboardData(ds),
        new Promise((resolve) => setTimeout(resolve, 400)),
      ]);

      setLoadingProgress(85);
      setLoadingStep("Projecting 3D orbital objects to visual Earth...");

      setObjects(live.objects);
      setRiskList(live.riskList);
      setDashboardStats(live.dashboardStats);
      setLoadingProgress(100);
      setLoadingStep("Dataset synchronized!");

      setTimeout(() => {
        setIsDatasetLoading(false);
      }, 200);
    } catch (err) {
      console.warn("[RADAR] Backend load failed:", err);
      setIsDatasetLoading(false);
    }
  };

  useEffect(() => {
    reloadVisuals(dataset);
  }, [dataset]);

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

  // ---- Tab sync transitions (await sync between mode changes) ----
  const [isTabSyncing, setIsTabSyncing] = useState(false);
  const [tabSyncLabel, setTabSyncLabel] = useState("");

  const handleChangeMode = async (nextMode) => {
    if (nextMode === mode) return;

    const modeLabels = {
      dashboard: "ORBITAL TRACKING & CATALOG",
      threat: "CONJUNCTION & THREAT MATRIX",
      reentry: "ATMOSPHERIC RE-ENTRY WATCH",
      launch: "LAUNCH CORRIDOR PLANNER",
      solar: "SOLAR SYSTEM ORRERY",
    };

    setIsTabSyncing(true);
    setTabSyncLabel(modeLabels[nextMode] || nextMode.toUpperCase());

    // Reset selection and mode-specific overlays
    setSelectedObjectId(null);
    setSelectedEventId(null);
    if (nextMode !== "launch") {
      setCorridorWaypoints(null);
      setReentryPath(null);
    }

    // Await sync transition so visuals reload seamlessly
    await new Promise((resolve) => setTimeout(resolve, 260));

    if (nextMode === "threat") {
      setShowSweep(true);
    }
    setMode(nextMode);
    setIsTabSyncing(false);
  };

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
      {isTabSyncing && (
        <div
          className="tab-sync-overlay"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            background: "rgba(5, 7, 12, 0.4)",
            backdropFilter: "blur(3px)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "all",
          }}
        >
          <div
            className="hud-frame"
            style={{
              padding: "1rem 2rem",
              background: "rgba(13, 19, 31, 0.95)",
              border: "1px solid var(--neon-blue, #00f0ff)",
              boxShadow: "0 0 25px rgba(0, 240, 255, 0.25)",
              borderRadius: "4px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "0.68rem", letterSpacing: "2px", color: "var(--neon-blue, #00f0ff)", marginBottom: "0.25rem", fontFamily: "var(--font-mono, monospace)" }}>
              RECONFIGURING HUD SUBSYSTEM
            </div>
            <div className="mono" style={{ color: "#f8fafc", fontSize: "0.95rem", fontWeight: "bold" }}>
              // {tabSyncLabel}
            </div>
          </div>
        </div>
      )}

      {isDatasetLoading && (
        <div
          className="dataset-loading-overlay"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            background: "rgba(5, 7, 12, 0.88)",
            backdropFilter: "blur(10px)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            pointerEvents: "all",
          }}
        >
          <div
            className="hud-frame"
            style={{
              padding: "2.5rem 3rem",
              background: "rgba(13, 19, 31, 0.95)",
              border: "1px solid var(--neon-blue, #00f0ff)",
              boxShadow: "0 0 35px rgba(0, 240, 255, 0.25)",
              borderRadius: "8px",
              minWidth: "460px",
              maxWidth: "90vw",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "0.75rem", letterSpacing: "2px", color: "var(--neon-blue, #00f0ff)", marginBottom: "0.5rem", fontFamily: "var(--font-mono, monospace)" }}>
              SYSTEM STATUS // DATASET CONTEXT SWITCH
            </div>
            <h2 className="mono" style={{ margin: "0 0 1.2rem 0", color: "#f8fafc", fontSize: "1.4rem" }}>
              LOADING [{dataset.toUpperCase()}]
            </h2>
            <p className="mono" style={{ color: "var(--text-dim, #94a3b8)", fontSize: "0.85rem", marginBottom: "1.5rem", minHeight: "1.2rem" }}>
              {loadingStep}
            </p>
            <div style={{ width: "100%", height: "6px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "3px", overflow: "hidden", marginBottom: "0.8rem" }}>
              <div
                style={{
                  width: `${loadingProgress}%`,
                  height: "100%",
                  background: "linear-gradient(90deg, #00f0ff, #38bdf8)",
                  boxShadow: "0 0 10px #00f0ff",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-dim, #64748b)", fontFamily: "var(--font-mono, monospace)" }}>
              <span>SYNCING TELEMETRY</span>
              <span>{loadingProgress}%</span>
            </div>
          </div>
        </div>
      )}

      {isSolar ? (
        <SolarSystemView
          selectedBodyId={selectedBodyId}
          onSelectBody={setSelectedBodyId}
          simulationClock={simulationClock}
        />
      ) : (
        <GlobeView
          key={`${dataset}-${mode}`}
          objects={visibleObjects}
          mode={mode}
          selectedObjectId={selectedObjectId}
          onSelectObject={selectObject}
          corridorWaypoints={corridorWaypoints}
          reentryWaypoints={reentryPath?.waypoints ?? null}
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
          <ReentryWatchPanel
            onPathChange={(waypoints, meta) =>
              setReentryPath(waypoints ? { waypoints, ...meta } : null)
            }
          />
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
