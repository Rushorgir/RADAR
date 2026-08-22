import { useState } from "react";
import GlobeView from "./components/GlobeView";
import TopBar from "./components/TopBar";
import StatCluster from "./components/StatCluster";
import RiskPanel from "./components/RiskPanel";
import LaunchPlanner from "./components/LaunchPlanner";
import ScanSweep from "./components/ScanSweep";
import { mockObjects, mockRiskList, mockDashboardStats } from "./data/mockData";

export default function App() {
  const [mode, setMode] = useState("dashboard"); // dashboard | threat | launch
  const [showSweep, setShowSweep] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);

  function handleChangeMode(nextMode) {
    if (nextMode === "threat" && mode !== "threat") {
      setShowSweep(true);
    }
    setMode(nextMode);
  }

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <GlobeView
        objects={mockObjects}
        mode={mode}
        selectedObjectId={selectedObjectId}
        onSelectObject={setSelectedObjectId}
      />

      <TopBar
        mode={mode}
        onChangeMode={handleChangeMode}
        overallRiskStatus={mockDashboardStats.overall_risk_status}
      />

      {mode === "dashboard" && <StatCluster stats={mockDashboardStats} />}

      {mode === "threat" && (
        <RiskPanel
          riskList={mockRiskList}
          selectedEventId={selectedEventId}
          onSelectEvent={setSelectedEventId}
        />
      )}

      {mode === "launch" && <LaunchPlanner />}

      {showSweep && <ScanSweep onComplete={() => setShowSweep(false)} />}
    </div>
  );
}
