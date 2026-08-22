import { useEffect, useState } from "react";
import GlobeView from "./components/GlobeView";
import TopBar from "./components/TopBar";
import StatCluster from "./components/StatCluster";
import RiskPanel from "./components/RiskPanel";
import LaunchPlanner from "./components/LaunchPlanner";
import ScanSweep from "./components/ScanSweep";
import ObjectDetailPanel from "./components/ObjectDetailPanel";
import RiskLegend from "./components/RiskLegend";
import { mockObjects, mockRiskList, mockDashboardStats } from "./data/mockData";
import { buildObjectDetail, normalizeId } from "./utils/objectDetails";
import { loadLiveDashboardData } from "./utils/liveData";

export default function App() {
  const [mode, setMode] = useState("dashboard"); // dashboard | threat | launch
  const [showSweep, setShowSweep] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);

  // Start with mock data so the UI renders immediately; swap in real data
  // from the backend if/when it loads. If the backend isn't running (e.g.
  // a frontend-only demo), this fails silently and mock data stays put --
  // see src/frontend/src/utils/liveData.js for exactly what's real vs.
  // still a placeholder (AI-3's ML risk/SHAP/maneuver output doesn't exist
  // yet, so those fields stay empty even once live data loads).
  const [objects, setObjects] = useState(mockObjects);
  const [riskList, setRiskList] = useState(mockRiskList);
  const [dashboardStats, setDashboardStats] = useState(mockDashboardStats);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadLiveDashboardData()
      .then((live) => {
        if (cancelled) return;
        setObjects(live.objects);
        setRiskList(live.riskList);
        setDashboardStats(live.dashboardStats);
        setIsLive(true);
      })
      .catch((err) => {
        console.warn("[RADAR] Backend unreachable, using mock data:", err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedObject = objects.find((object) => normalizeId(object.object_id) === normalizeId(selectedObjectId));
  const objectDetail = buildObjectDetail(selectedObject, riskList);

  function handleChangeMode(nextMode) {
    if (nextMode === "threat" && mode !== "threat") {
      setShowSweep(true);
    }
    setMode(nextMode);
  }

  return (
    <div className="radar-shell">
      <GlobeView
        objects={objects}
        mode={mode}
        selectedObjectId={selectedObjectId}
        onSelectObject={setSelectedObjectId}
      />

      <TopBar
        mode={mode}
        onChangeMode={handleChangeMode}
        overallRiskStatus={dashboardStats.overall_risk_status}
      />

      <div className="left-rail-label eyebrow">
        SPACE DEBRIS INTELLIGENCE {isLive ? "// LIVE" : "// DEMO DATA"}
      </div>
      {mode === "dashboard" && <StatCluster stats={dashboardStats} />}

      {mode === "threat" && (
        <RiskPanel
          riskList={riskList}
          selectedEventId={selectedEventId}
          onSelectEvent={setSelectedEventId}
          onSelectObject={setSelectedObjectId}
        />
      )}

      {mode === "launch" && <LaunchPlanner />}

      <ObjectDetailPanel object={objectDetail} onClose={() => setSelectedObjectId(null)} />
      <RiskLegend />

      {showSweep && <ScanSweep onComplete={() => setShowSweep(false)} />}
    </div>
  );
}
