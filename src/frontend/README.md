# RADAR Frontend

React + Vite + CesiumJS console for the space-debris collision-avoidance dashboard.
The application currently runs with mock data so frontend work can continue while the
FastAPI backend and AI services are being implemented.

## Run it

From this directory:

```bash
npm install
npm run dev
```

The development server opens at `http://localhost:5173`. The Cesium globe uses
OpenStreetMap imagery and does not require a Cesium Ion token. A Node.js version
compatible with the installed Vite/Cesium dependencies is required.

Useful commands:

- `npm run dev` — start the development server
- `npm run lint` — run Oxlint
- `npm run build` — create a production build
- `npm run preview` — preview the production build

## Application structure

- `src/App.jsx` — application state and mode composition
- `src/main.jsx` — React entry point
- `src/components/GlobeView.jsx` — Cesium globe and tracked-object entities
- `src/components/TopBar.jsx` — Overview, Threat Analysis, and Launch Planner navigation
- `src/components/StatCluster.jsx` — overview statistics
- `src/components/RiskPanel.jsx` — conjunction risks, SHAP-style factors, and advisories
- `src/components/LaunchPlanner.jsx` — launch route inputs and placeholder result
- `src/components/ScanSweep.jsx` — threat-analysis transition animation
- `src/data/mockData.js` — current UI data boundary
- `src/styles/tokens.css` — shared deep-space HUD design tokens

## Current data boundary

`App.jsx` currently imports `mockObjects`, `mockRiskList`, and `mockDashboardStats` from
`src/data/mockData.js`. Keep these view-model shapes stable until the backend endpoints
are available. When they are implemented, add an API adapter under `src/utils/` to map
the Python contracts from `src/shared/interfaces/contracts.py` to the component model
before replacing the mock imports.

## Known gaps

- The globe currently renders tracked objects as points rather than propagated orbit paths.
- The Launch Planner displays a placeholder result instead of calling a backend route.
- Satellite detail drill-down and live backend/WebSocket data are not implemented yet.
- OpenStreetMap imagery requires network access at runtime, despite the app requiring no
  Cesium Ion token.
