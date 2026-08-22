**Project Overview**

- **Track:** Space Debris Collision Avoidance | VITISH'26 PS-17 (SIH Internal Round, VIT Chennai)
- **SIH 2026 Mapping:** Student Innovation Open Slot — Theme: Space Technology (`SIH26209` / `SIH26226`)
- **Team & Ownership:** Anas (Orbital Mechanics), Rushaan (Conjunction/$P_c$), Udarsh (ML & Explainability), Balaganesh (Web/Full-Stack), Mahalakshmi (QA & Pitch)
- **Architecture in One Line:** Ingest CelesTrak TLEs $\rightarrow$ propagate via SGP4 $\rightarrow$ screen 500–1,000 LEO objects ($k\text{-d}$ tree over altitude bands) $\rightarrow$ compute Probability of Collision ($P_c$) using Foster's 2D method (Monte Carlo fallback) $\rightarrow$ rank/explain risk with LightGBM + SHAP (benchmarked against TabPFN) $\rightarrow$ compute closed-form minimum-$\Delta v$ maneuver advisories $\rightarrow$ render live on a Cesium.js 3D globe.

---

**1. Idea Scope**
RADAR functions as a decision-support and collision-mitigation software layer built on public orbital tracking data, reproducing institutional Space Situational Awareness (SSA) workflows at hackathon scale. Rather than pitching speculative sensor hardware, it focuses purely on data ingestion, screening, collision-probability quantification, explainable risk ranking, and automated mitigation planning.

---

**2. Core Innovations & Differentiators**

- **Disciplined Physics vs. ML Boundary:** Uses closed-form orbital mechanics for SGP4 propagation and $\Delta v$ maneuver optimization, avoiding the common pitfall of forcing ML onto deterministic physics.
- **Feature-Level Explainability (SHAP):** Unlike standard conjunction tools that output an opaque $P_c$ score, RADAR surfaces exact risk drivers (miss distance, covariance orientation, relative velocity), directly aligning with ESA’s CREAM (Collision Risk Estimation and Automated Mitigation) initiative.
- **Modern Tabular Benchmarking:** LightGBM risk ranking is explicitly benchmarked against TabPFN (a tabular foundation model tailored for datasets under 10k samples), providing an empirical, peer-reviewed baseline rationale.
- **Closed-Loop Actionability:** Extends beyond passive risk detection to calculate actionable, minimum-fuel evasive maneuvers.

---

**3. Technical Architecture & Stack**

| Pipeline Stage              | Implementation                                   | Technical Justification                                                                                              |
| --------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Ingestion & Propagation** | CelesTrak TLEs $\rightarrow$ `sgp4`/`SDP4`       | Uses `astropy` for standard $\text{TEME} \rightarrow \text{ECI} \rightarrow \text{ECEF}$ coordinate transformations. |
| **Conjunction Screening**   | Coarse altitude binning + Fine $k\text{-d}$ tree | Filters pairwise conjunctions across 500–1,000 LEO objects in sub-second runtimes.                                   |
| **Collision Risk ($P_c$)**  | Foster’s 2D Method + Monte Carlo fallback        | Fast 2D calculation for linear encounters; fallback handles non-linear/near-parallel geometries.                     |
| **ML & Explainability**     | LightGBM + TreeSHAP                              | Pre-trained and validated on ESA Kelvins 2019 Conjunction Data Messages (13k events).                                |
| **Maneuver Advisory**       | Closed-form $\Delta v$ optimization              | Solves for minimum fuel consumption under orbital constraint boundaries.                                             |
| **Platform & UI**           | FastAPI + React + Cesium.js + PostgreSQL         | Containerized via Docker Compose for real-time 3D orbit visualization and alerts.                                    |

---

**4. Toughness & Risk Mitigation**

- **Catalog Scale Scoping:** Full-catalog screening (30,000+ objects) is impractical under demo latency constraints. Benchmarking on an active 500–1,000 LEO subset demonstrates production-grade architecture without risking system hangs.
- **Foster's 2D Validity Limits:** Foster's method assumes short encounters and linear relative motion. The team must rigorously test the Monte Carlo fallback trigger conditions for slow, co-orbital approaches.
- **Integration Bottlenecks:** Because the pipeline involves sequential dependencies (Orbital Mechanics $\rightarrow$ $P_c$ Math $\rightarrow$ ML $\rightarrow$ UI), locking strict Pydantic/API schemas on Day 1 is critical to avoid integration failure. Training the ML model on ESA Kelvins data decouples ML development from backend physics delivery.

---

**5. Business Scope & Go-to-Market**

- **Institutional Alignment (India):** Directly maps to ISRO’s **IS4OM** (System for Safe and Sustainable Space Operations Management) and **Project NETRA** (₹509-crore indigenous SSA monitoring network). RADAR pitches naturally as an explainable decision-support dashboard for existing NETRA tracking infrastructure.
- **Commercial SSA Ecosystem:** Targets private constellation operators via a B2B SaaS conjunction-analytics model (analogous to Slingshot Beacon and LeoLabs tools) and integrates with the 60+ Indian space startups registered under IN-SPACe.
- **Defensible Market Positioning:** RADAR does not compete with sensor/radar operators like Digantara or LeoLabs. Instead, it positions itself as an downstream analytics and mitigation engine that ingests multi-source ephemeris data to deliver actionable, explainable avoidance plans.
