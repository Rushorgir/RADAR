# OrbitGuard — Frontend

React + Vite + CesiumJS console for the space-debris collision-avoidance dashboard.
Built against **mock data** so it never blocks on the backend/AI team — see
`src/data/mockData.js` for the exact shape everything expects.

## Run it

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`. No Cesium Ion token required — it uses OpenStreetMap
imagery so it works offline-friendly out of the box. If you want nicer terrain/imagery
later, sign up for a free Ion token at cesium.com/ion and pass it via
`Cesium.Ion.defaultAccessToken` in `GlobeView.jsx`.

## What's built

- **Overview mode** — globe + stat cluster (active satellites, tracked debris, high-risk
  count, etc.)
- **Threat Analysis mode** — radar-sweep transition, dimmed nominal debris, red/amber
  highlighted risk objects, side panel with per-event SHAP-style risk factors and
  maneuver advisory
- **Launch Planner** — input form + placeholder result (lowest priority, build last)
- Click any tracked object on the globe to fly the camera to it (satellite
  drill-down groundwork — wire a detail panel to `selectedObjectId` in `App.jsx`
  when that's next up)

## Swapping mock data for the real backend

Everything in `src/data/mockData.js` is shaped to match the interface contract from
the team plan:

- `mockObjects` -> AI-1's state vectors (position/velocity per object)
- `mockRiskList` -> AI-3's ranked risk list (Pc, ML risk score, SHAP top-3, maneuver
  advisory)
- `mockDashboardStats` -> aggregate counts for the overview cards

When Web's FastAPI endpoints are live, replace the imports in `App.jsx` with `fetch()`
calls (or a small `useEffect` + `useState` per endpoint) returning the **same shape**.
No component below `App.jsx` needs to change if the shape matches — that's the whole
point of locking the contract on Day 1.

## Design system

Tokens live in `src/styles/tokens.css` — deep-space console palette (near-black,
signal teal, critical red / elevated amber for risk tiers), Space Grotesk for display
type, Inter for body, JetBrains Mono for telemetry/data. The `.hud-frame` class is the
signature bracket-corner panel style used everywhere — reuse it for any new panel
instead of inventing a new container style.

## Known gaps / next up

- Orbit paths are currently just points, not propagated trajectories — swap in real
  paths once AI-1's propagation output is flowing (a `Cesium.SampledPositionProperty`
  per object, or a static polyline if paths are precomputed server-side)
- Satellite detail drill-down panel (Section 3 of the brief) — `selectedObjectId` is
  already wired up in `App.jsx`, just needs a panel component
- Launch Planner's "Generate Route" is a placeholder timeout — wire to the real
  endpoint when AI trio + Web have it ready
