import React, { createContext, useContext, useState, useEffect } from "react";
import { setDataset as setApiDataset } from "../utils/apiClient";

const DatasetContext = createContext();

export function DatasetProvider({ children }) {
  const [dataset, setDatasetState] = useState(() => {
    const saved = localStorage.getItem("selectedDataset") || "Live LEO Catalog (Unified)";
    setApiDataset(saved);
    return saved;
  });

  const setDataset = (newDataset) => {
    setApiDataset(newDataset);
    try {
      localStorage.setItem("selectedDataset", newDataset);
    } catch (e) {}
    setDatasetState(newDataset);
  };

  useEffect(() => {
    setApiDataset(dataset);
  }, [dataset]);

  return (
    <DatasetContext.Provider value={{ dataset, setDataset }}>
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset() {
  return useContext(DatasetContext);
}
