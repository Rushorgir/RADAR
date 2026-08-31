import React, { useState, useEffect, useRef } from "react";
import { useDataset } from "../context/DatasetContext";
import { fetchDatasets, deleteDatasetApi, API_BASE } from "../utils/apiClient";

export default function DatasetManager() {
  const { dataset, setDataset } = useDataset();
  const [datasets, setDatasets] = useState(["default"]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [progress, setProgress] = useState(-1); // -1 = idle or error, 0-100 = active
  const [errorMsg, setErrorMsg] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const fileInputRef = useRef(null);
  const newDatasetNameRef = useRef(null);
  const dropdownRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    loadDatasets();
    setupWebSocket();

    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) { }
      }
    };
  }, []);

  async function loadDatasets() {
    try {
      const data = await fetchDatasets();
      setDatasets(data.datasets || ["default"]);
    } catch (err) {
      console.error("Failed to load datasets", err);
    }
  }

  async function handleDelete(nameToDelete, e) {
    e.stopPropagation();
    if (nameToDelete === "default") return;

    try {
      await deleteDatasetApi(nameToDelete);
      await loadDatasets();
      // Always reset back to default as requested
      setDataset("default");
      setIsDropdownOpen(false);
    } catch (err) {
      console.error("Failed to delete dataset", err);
    }
  }

  function setupWebSocket() {
    try {
      const wsUrl = API_BASE.replace(/^http/, "ws") + "/ws";
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "DATASET_IMPORT_PROGRESS") {
            const { dataset: activeDataset, progress: val, status } = msg.data;
            if (val === -1) {
              setErrorMsg(status || "Dataset processing failed.");
              setUploadStatus("");
              setProgress(-1);
            } else if (val === 100) {
              setProgress(100);
              setUploadStatus(`[${activeDataset}] ${status}`);
              setIsSuccess(true);
              loadDatasets();
              setDataset(activeDataset);
              setTimeout(() => {
                setIsModalOpen(false);
                setUploadStatus("");
                setProgress(-1);
                setIsSuccess(false);
                setErrorMsg("");
              }, 1800);
            } else {
              setErrorMsg("");
              setUploadStatus(`[${activeDataset}] ${status}`);
              setProgress(val);
            }
          }
        } catch (e) { }
      };
      ws.onerror = () => {
        // Fallback reconnection after delay
        setTimeout(setupWebSocket, 3000);
      };
      wsRef.current = ws;
    } catch (e) { }
  }

  function openModal() {
    setErrorMsg("");
    setUploadStatus("");
    setProgress(-1);
    setIsSuccess(false);
    setIsModalOpen(true);
  }

  async function handleImport(e) {
    e.preventDefault();
    setErrorMsg("");
    setIsSuccess(false);

    const file = fileInputRef.current?.files?.[0];
    const name = newDatasetNameRef.current?.value?.trim();

    if (!name) {
      setErrorMsg("Please enter a name for the dataset.");
      return;
    }
    if (!file) {
      setErrorMsg("Please select a valid .txt TLE file.");
      return;
    }

    setUploadStatus("Uploading file to pipeline...");
    setProgress(5);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("dataset_name", name);

    try {
      const response = await fetch(`${API_BASE}/api/datasets/import`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Server returned status ${response.status}`);
      }
    } catch (error) {
      setErrorMsg(`Import failed: ${error.message}`);
      setUploadStatus("");
      setProgress(-1);
    }
  }

  const isProcessing = progress >= 0 && progress < 100;

  return (
    <div className="dataset-manager">
      <div className="dataset-selector" style={{ marginTop: "1.5rem" }}>
        <span className="eyebrow nav-heading">Active Dataset</span>

        <div ref={dropdownRef} style={{ position: "relative", marginTop: "0.5rem" }}>
          <button
            type="button"
            className="mono"
            onClick={() => {
              loadDatasets();
              setIsDropdownOpen(!isDropdownOpen);
            }}
            style={{
              width: "100%",
              padding: "0.5rem 0.75rem",
              background: "rgba(10, 16, 26, 0.9)",
              color: "var(--text-primary, #e2e8f0)",
              border: isDropdownOpen ? "1px solid var(--neon-blue, #00f0ff)" : "1px solid var(--border-color, rgba(0, 240, 255, 0.3))",
              borderRadius: "4px",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
              boxShadow: isDropdownOpen ? "0 0 10px rgba(0, 240, 255, 0.2)" : "none",
              transition: "all 0.2s ease",
            }}
          >
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {dataset}
            </span>
            <span style={{ fontSize: "0.7rem", color: "var(--neon-blue, #00f0ff)", marginLeft: "0.5rem" }}>
              {isDropdownOpen ? "▲" : "▼"}
            </span>
          </button>

          {isDropdownOpen && (
            <div
              className="hud-frame"
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                left: 0,
                right: 0,
                maxHeight: "220px",
                overflowY: "auto",
                background: "rgba(13, 19, 31, 0.98)",
                backdropFilter: "blur(12px)",
                border: "1px solid var(--neon-blue, #00f0ff)",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.7), 0 0 15px rgba(0, 240, 255, 0.2)",
                borderRadius: "4px",
                zIndex: 1000,
                padding: "0.25rem 0",
              }}
            >
              {datasets.map((d) => {
                const isSelected = d === dataset;
                const isDefault = d === "default";
                return (
                  <div
                    key={d}
                    onClick={() => {
                      setDataset(d);
                      setIsDropdownOpen(false);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "0.5rem 0.75rem",
                      cursor: "pointer",
                      background: isSelected ? "rgba(0, 240, 255, 0.15)" : "transparent",
                      borderLeft: isSelected ? "3px solid var(--neon-blue, #00f0ff)" : "3px solid transparent",
                      transition: "background 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.background = "transparent";
                    }}
                  >
                    <span
                      className="mono"
                      style={{
                        fontSize: "0.85rem",
                        color: isSelected ? "var(--neon-blue, #00f0ff)" : "var(--text-primary, #e2e8f0)",
                        fontWeight: isSelected ? "bold" : "normal",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        marginRight: "0.5rem",
                      }}
                    >
                      {d}
                    </span>

                    {!isDefault && (
                      <button
                        type="button"
                        onClick={(e) => handleDelete(d, e)}
                        title={`Delete ${d}`}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "var(--text-dim, #94a3b8)",
                          fontSize: "0.85rem",
                          lineHeight: 1,
                          padding: "2px 6px",
                          borderRadius: "3px",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                        onMouseEnter={(e) => {
                          e.stopPropagation();
                          e.currentTarget.style.color = "#ef4444";
                          e.currentTarget.style.background = "rgba(239, 68, 68, 0.15)";
                          e.currentTarget.style.boxShadow = "0 0 8px rgba(239, 68, 68, 0.4)";
                        }}
                        onMouseLeave={(e) => {
                          e.stopPropagation();
                          e.currentTarget.style.color = "var(--text-dim, #94a3b8)";
                          e.currentTarget.style.background = "transparent";
                          e.currentTarget.style.boxShadow = "none";
                        }}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <button
          className="mode-button"
          style={{
            marginTop: "0.75rem",
            width: "100%",
            border: "1px dashed var(--neon-blue, #00f0ff)",
            background: "rgba(0, 240, 255, 0.05)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
          }}
          onClick={openModal}
        >
          <span>＋</span> Import Data
        </button>
      </div>

      {isModalOpen && (
        <div
          className="modal-overlay"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.85)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !isProcessing) {
              setIsModalOpen(false);
            }
          }}
        >
          <div
            className="modal-content hud-frame"
            style={{
              background: "var(--panel-bg, #0d131f)",
              border: "1px solid var(--neon-blue, #00f0ff)",
              boxShadow: "0 0 20px rgba(0, 240, 255, 0.2)",
              padding: "2rem",
              width: "440px",
              maxWidth: "90vw",
              borderRadius: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2 className="mono" style={{ margin: 0, color: "var(--neon-blue, #00f0ff)", fontSize: "1.2rem" }}>
                Import Custom Dataset
              </h2>
              {!isProcessing && (
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-dim, #64748b)",
                    fontSize: "1.2rem",
                    cursor: "pointer",
                  }}
                >
                  ✕
                </button>
              )}
            </div>

            <p style={{ color: "var(--text-dim, #94a3b8)", marginBottom: "1.5rem", fontSize: "0.85rem", lineHeight: 1.4 }}>
              Upload a raw TLE (.txt) file. RADAR will automatically propagate orbits (SGP4), detect conjunctions, and run ML risk scoring.
            </p>

            <form onSubmit={handleImport}>
              <div style={{ marginBottom: "1rem" }}>
                <label className="eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                  Dataset Name
                </label>
                <input
                  ref={newDatasetNameRef}
                  type="text"
                  placeholder="e.g. Starlink Constellation"
                  disabled={isProcessing}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "0.6rem 0.8rem",
                    background: "rgba(0,0,0,0.6)",
                    color: "white",
                    border: "1px solid rgba(255,255,255,0.2)",
                    borderRadius: "4px",
                    outline: "none",
                  }}
                />
              </div>

              <div style={{ marginBottom: "1.5rem" }}>
                <label className="eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                  TLE File (.txt)
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt"
                  disabled={isProcessing}
                  style={{
                    width: "100%",
                    color: "#cbd5e1",
                    fontSize: "0.9rem",
                  }}
                />
              </div>

              {errorMsg && (
                <div
                  style={{
                    marginBottom: "1.2rem",
                    padding: "0.6rem 0.8rem",
                    background: "rgba(239, 68, 68, 0.15)",
                    border: "1px solid #ef4444",
                    borderRadius: "4px",
                    color: "#fca5a5",
                    fontSize: "0.85rem",
                  }}
                >
                  ⚠ {errorMsg}
                </div>
              )}

              {isSuccess && (
                <div
                  style={{
                    marginBottom: "1.2rem",
                    padding: "0.6rem 0.8rem",
                    background: "rgba(34, 197, 94, 0.15)",
                    border: "1px solid #22c55e",
                    borderRadius: "4px",
                    color: "#86efac",
                    fontSize: "0.85rem",
                  }}
                >
                  ✓ Import Complete! Switching view...
                </div>
              )}

              {progress >= 0 && (
                <div style={{ marginBottom: "1.5rem" }}>
                  <div className="eyebrow" style={{ marginBottom: "0.4rem", display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--neon-blue, #00f0ff)" }}>{uploadStatus}</span>
                    <span>{progress}%</span>
                  </div>
                  <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${progress}%`,
                        height: "100%",
                        background: progress === 100 ? "#22c55e" : "var(--neon-blue, #00f0ff)",
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>
              )}

              <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
                {!isProcessing && (
                  <button
                    type="button"
                    className="mode-button"
                    onClick={() => setIsModalOpen(false)}
                    style={{ padding: "0.5rem 1rem" }}
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="submit"
                  className="mode-button active"
                  style={{
                    padding: "0.5rem 1.2rem",
                    opacity: isProcessing ? 0.7 : 1,
                    cursor: isProcessing ? "not-allowed" : "pointer",
                  }}
                  disabled={isProcessing}
                >
                  {isProcessing ? "Processing..." : "Import"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
