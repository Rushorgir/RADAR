import { useState } from "react";
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

export default function App() {
  const [mode, setMode] = useState("dashboard"); // dashboard | threat | launch
  const [showSweep, setShowSweep] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const selectedObject = mockObjects.find((object) => normalizeId(object.object_id) === normalizeId(selectedObjectId));
  const objectDetail = buildObjectDetail(selectedObject, mockRiskList);

  function handleChangeMode(nextMode) {
    if (nextMode === "threat" && mode !== "threat") {
      setShowSweep(true);
    }
    setMode(nextMode);
  }

  return (
    <div className="radar-shell">
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

      <div className="left-rail-label eyebrow">SPACE DEBRIS INTELLIGENCE</div>
      {mode === "dashboard" && <StatCluster stats={mockDashboardStats} />}

      {mode === "threat" && (
        <RiskPanel
          riskList={mockRiskList}
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
