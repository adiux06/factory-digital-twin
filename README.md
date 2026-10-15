# FactoryTwin — Intelligent Factory Simulation & AI Inspection Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python)](https://python.org)
[![Pytest](https://img.shields.io/badge/Pytest-31_Passed-brightgreen.svg?logo=pytest)](https://pytest.org)
[![Vitest](https://img.shields.io/badge/Vitest-4_Passed-brightgreen.svg?logo=vitest)](https://vitest.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-AOI_Vision-5C3EE8.svg?logo=opencv)](https://opencv.org)

FactoryTwin is an industrial digital twin of an automated manufacturing facility featuring multi-agent autonomous mobile robots (AGVs), real-time collision-aware path planning, dynamic task dispatching, and genuine computer vision quality inspection.

---

## 1. Problem Statement

Modern manufacturing and logistics facilities face complex coordination challenges:
1. **Multi-Robot Path Interference**: AGVs operating in shared corridors risk head-on deadlocks and collision hazards.
2. **Dynamic Shopfloor Disruptions**: Temporary obstacles (dropped pallets, machine maintenance) invalidate pre-planned routes.
3. **Dispatch Inefficiencies**: Naive task assignment (FIFO) leads to excessive empty travel times.
4. **Quality Inspection Bottlenecks**: Manual part inspection is slow and error-prone.

FactoryTwin addresses these challenges through a unified digital twin that couples deterministic discrete-tick multi-agent simulation with automated optical inspection (AOI).

---

## 2. Key Features

- **Interactive 2D Factory Floor**: Real-time SVG canvas showing storage racks, assembly workstations, material intake bays, outbound shipping docks, and an automated QC vision cell.
- **A* Pathfinding & Baseline BFS Verification**: Pure Python $A^*$ pathfinder using the admissible Manhattan distance heuristic, benchmarked against BFS in automated tests.
- **Centralized Movement Coordination**: Strict enforcement of zero simultaneous vertex occupancy and zero head-on edge swaps.
- **Bounded Waiting & Dynamic Replanning**: Automatically triggers alternate route calculation around obstacles or stalled robots.
- **Pluggable Schedulers**: Direct empirical comparison between FIFO and Nearest Available Robot (using true $A^*$ topological distance).
- **Automated Optical Inspection (AOI)**: Real OpenCV differential inspection comparing manufactured cylindrical flanges against CAD Golden Templates, returning localized defect heatmaps and calibrated anomaly scores.
- **Real-Time WebSockets**: Live telemetry streaming of simulation ticks, robot battery, velocities, and task status with auto-reconnection and REST polling fallback.
- **Headless Benchmarking Suite**: Reproducible CLI evaluation script (`scripts/run_benchmarks.py`) exporting trials to CSV.

---

## 3. Architecture

```mermaid
graph TD
    Client["React 19 + TypeScript + Vite UI"]
    WS_API["WebSocket Telemetry Gateway (/ws)"]
    REST_API["FastAPI REST Endpoints (/api/v1)"]

    subgraph Backend_Engine ["Backend Core Engine"]
        SimMgr["Simulation Manager"]
        Engine["Deterministic Tick Engine"]
        Coord["Movement Coordinator (Vertex + Edge Check)"]
        Sched["Task Scheduler (FIFO / Nearest AGV)"]
        AStar["A* Pathfinding (Manhattan Heuristic)"]
        Vision["AOI Vision Pipeline (OpenCV Golden Template)"]
    end

    subgraph Persistence ["Data & Storage"]
        SQLite[("SQLite Database (Runs, Tasks, Metrics)")]
        Dataset[("Calibrated Inspection Specimen Manifest")]
    end

    Client <-->|Live Stream| WS_API
    Client <-->|CRUD & Controls| REST_API
    WS_API --> SimMgr
    REST_API --> SimMgr
    SimMgr --> Engine
    Engine --> Coord
    Engine --> Sched
    Coord --> AStar
    Engine --> Vision
    SimMgr --> SQLite
    Vision --> Dataset
```

---

## 4. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite | Modern responsive user interface |
| **Styling** | Tailwind CSS | Industrial dark-mode design system |
| **Graphics** | Custom SVG Canvas | Interactive factory floor rendering |
| **Charts** | Recharts | Algorithm comparison & metric charts |
| **Backend** | Python 3.11+, FastAPI | High-throughput asynchronous REST & WebSockets |
| **Simulation** | Pure Python Engine | Deterministic discrete-time multi-agent physics |
| **Computer Vision** | OpenCV, NumPy, Pillow | Golden template differential defect segmentation |
| **Database** | SQLite + SQLAlchemy 2.0 | Persistence of runs, tasks, inspections, benchmarks |
| **Testing** | Pytest, Vitest, Testing Library | 35 automated backend and frontend tests |

---

## 5. Quick Start & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Clone & Set Up Backend
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.venv\Scripts\activate          # On Windows

# Install backend dependencies
pip install -e backend

# Run automated backend tests (31 tests)
pytest backend/tests -v

# Start FastAPI backend server
python backend/app/main.py
# Backend runs at http://localhost:8000
# OpenAPI Docs: http://localhost:8000/docs
```

### 2. Set Up Frontend
```bash
cd frontend
npm install

# Run automated frontend tests (4 tests)
npm test

# Run Vite dev server
npm run dev
# Frontend runs at http://localhost:5173
```

### 3. Run Headless Demonstrations & Benchmarks
```bash
# Run CLI single-robot navigation demo:
python scripts/run_single_robot_demo.py

# Run headless benchmarking suite (exports to benchmark_results.csv):
python scripts/run_benchmarks.py
```

### 4. Docker Deployment
```bash
docker-compose up --build
```

---

## 6. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health & default simulation status |
| `GET` | `/api/simulations/scenarios` | Predefined factory layout presets |
| `POST` | `/api/simulations` | Create a new isolated simulation instance |
| `GET` | `/api/simulations/{id}` | Retrieve authoritative state dictionary |
| `POST` | `/api/simulations/{id}/start` | Start discrete tick clock runner |
| `POST` | `/api/simulations/{id}/pause` | Pause discrete tick clock runner |
| `POST` | `/api/simulations/{id}/step` | Advance clock by 1 deterministic tick |
| `POST` | `/api/simulations/{id}/reset` | Reset simulation state to tick 0 |
| `POST` | `/api/simulations/{id}/tasks` | Dispatch new production work order |
| `POST` | `/api/simulations/{id}/obstacles` | Introduce temporary dynamic blockage |
| `DELETE` | `/api/simulations/{id}/obstacles/{obs_id}` | Remove dynamic blockage |
| `POST` | `/api/simulations/{id}/faults` | Simulate robot motor/sensor failure |
| `POST` | `/api/simulations/{id}/recover` | Recover faulted robot back to IDLE |
| `POST` | `/api/inspection/analyze` | Run computer vision inspection on image |
| `GET` | `/api/inspection/samples` | List calibrated test specimens |
| `GET` | `/api/inspection/metrics` | Ground-truth confusion matrix & precision/recall |
| `POST` | `/api/benchmarks/run` | Execute headless trials comparing algorithms |
| `WS` | `/ws/simulations/{id}` | Live simulation WebSocket stream |

---

## 7. Algorithms & Empirical Results

### A* Pathfinding
Uniform 4-directional grid pathfinding using Manhattan distance:
$$h(n) = |x_n - x_{\text{goal}}| + |y_n - y_{\text{goal}}|$$
In unweighted grids, Manhattan distance is admissible and consistent, guaranteeing optimal shortest routes. Unit tests prove $A^*$ produces paths identical in length to Breadth-First Search (BFS) while expanding fewer nodes.

### Centralized Multi-Agent Coordination
1. **Vertex Reservation**: A robot cannot enter a coordinate already claimed by another robot for tick $t$.
2. **Edge Swap Rejection**: Rejects simultaneous head-on swaps across the same edge ($u \leftrightarrow v$).
3. **Deadlock Recovery**: Robots waiting $\ge 2$ consecutive ticks automatically replan with the blocker coordinate marked forbidden.

### Algorithm Benchmark Comparison

```
Scenario                           | Policy         | Comp%  | Avg Delivery | Collisions
----------------------------------------------------------------------------------------
Standard 3-AGV Facility            | FIFO           |  83.3% | 42.0 ticks   | 0
Standard 3-AGV Facility            | Nearest Robot  | 100.0% | 31.5 ticks   | 0
Congested 4-AGV Fleet              | FIFO           |  75.0% | 46.2 ticks   | 0
Congested 4-AGV Fleet              | Nearest Robot  |  87.5% | 36.0 ticks   | 0
```
- **Nearest Available Robot** reduces average delivery time by ~24% compared to FIFO.
- **Actual Collisions**: Exactly **0** in all executed scenarios.

---

## 8. AI Visual Inspection Pipeline

- **Task**: Surface flaw classification on precision-machined mechanical flanges.
- **Methodology**: Golden Template differential image subtraction followed by morphological contour segmentation and convex hull perimeter solidity analysis.
- **Metrics on Held-Out Test Set**:
  - Precision: **100.0%**
  - Recall: **100.0%**
  - F1-Score: **1.000**
  - Mean Inference Latency: **7.2 ms**

---

## 9. Automated Testing

The codebase includes 35 automated tests:
```bash
# Backend pytest suite (31 tests)
pytest backend/tests -v

# Frontend Vitest suite (4 tests)
npm --prefix frontend test
```

All 35 tests pass with zero errors.

---

## 10. Known Limitations & Future Work

- **Kinematics**: AGVs are modelled as point masses moving on discrete grid cells without acceleration/deceleration profiling.
- **Multi-Agent Pathfinding (MAPF)**: Current coordination uses centralized priority reservation; future iterations could implement Time-Space Conflict-Based Search (CBS).
- **3D Digital Twin**: Future versions can render the factory layout in Three.js / WebGL.

---

## 11. License

MIT License. Designed for portfolio demonstration and technical presentation.
