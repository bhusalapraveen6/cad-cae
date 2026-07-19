"""
FastAPI application entry point.

# Development Prompt: Python Web Application for Multiphysics Engineering Simulation

Use this prompt to brief a developer, an AI coding agent, or yourself, when building the platform.

---

## 1. Project Goal

Build a **web-based CAE (Computer-Aided Engineering) platform** in Python that lets engineers set up,
run, monitor, and post-process a wide range of structural, dynamic, thermal, fluid, and multiphysics
simulations through a browser UI — without needing desktop software installed locally.

The platform is a **front-end + orchestration layer** over real solver engines (commercial and/or
open-source). It does not reimplement FEA/CFD math from scratch; it manages models, meshes, solver
jobs, HPC/cloud execution, and results visualization.

---

## 2. Recommended Tech Stack

**Backend**
- Python 3.11+, **FastAPI** (async REST + WebSocket API) or Django + DRF if you need a heavier admin/ORM layer
- **Celery + Redis/RabbitMQ** for long-running solver jobs (simulations can run minutes to days)
- **PostgreSQL** for project/job/user metadata; **object storage** (S3/MinIO) for meshes, result files (these are large binary files, not DB blobs)
- **SQLAlchemy** or Django ORM for data access

**Simulation / Solver Integration**
- **PyMAPDL** (ANSYS Mechanical APDL scripting from Python) — structural, thermal, modal, buckling, fatigue, fracture (SMART), composites (ACP via PyACP)
- **PyFluent** — CFD (laminar/turbulent, multiphase, turbomachinery, moving mesh)
- **PyAdditive** — additive manufacturing simulation
- **Ansys optiSLang / DesignXplorer APIs** — optimization workflows, if licensed
- Open-source fallback stack (no ANSYS license required):
  - **CalculiX** or **Code_Aster** — structural/thermal FEA
  - **FEniCSx** — custom PDE-based structural/thermal/piezoelectric models
  - **OpenFOAM** (driven via PyFoam or subprocess) — CFD, multiphase, conjugate heat transfer
  - **LIGGGHTS** — discrete element method (granular flow), as an alternative to Rocky
  - **LS-DYNA** or **CalculiX explicit** — impact/crash/blast, as an alternative to Autodyn
- **Gmsh / PyVista / meshio** for meshing and mesh format conversion
- **PyVista + VTK.js / Plotly / Three.js** for 3D result visualization in-browser

**Frontend**
- **React** (or Vue) + **Three.js / VTK.js** for interactive 3D model and results viewer
- **Plotly.js / D3.js** for 2D plots (S-N curves, frequency response, PSD, convergence history)
- Component library: Material UI or Ant Design for forms (BCs, material properties, solver settings)

**Infrastructure**
- Docker containers per solver (isolate ANSYS/OpenFOAM/LS-DYNA environments and licenses)
- Kubernetes or Slurm for scaling solver jobs across HPC/cloud nodes
- Job queue with progress streaming (WebSocket) so the UI shows live convergence/residual plots

---

## 3. Architecture Overview

```
Browser (React UI)
   │  REST/WebSocket
   ▼
FastAPI Backend
   ├── Auth & Project Management (users, projects, versioning)
   ├── Model/Mesh Service (geometry import, meshing via Gmsh)
   ├── Job Orchestration Service (Celery workers)
   │      ├── Solver Adapter: PyMAPDL (structural/thermal/modal/fatigue/fracture/ACP)
   │      ├── Solver Adapter: PyFluent / OpenFOAM (CFD, FSI, CHT)
   │      ├── Solver Adapter: Explicit (Autodyn / LS-DYNA)
   │      ├── Solver Adapter: DEM (Rocky / LIGGGHTS)
   │      ├── Solver Adapter: Maxwell (electromagnetics)
   │      └── Solver Adapter: Optimization (optiSLang / DesignXplorer / SciPy/Optuna for custom)
   ├── Results Post-Processing Service (PyVista, stress/strain/field extraction)
   └── Storage (Postgres metadata + S3 result files)
```

Each **solver adapter** is a thin Python wrapper exposing a common interface:
```python
class SolverAdapter(Protocol):
    def build_model(self, spec: SimulationSpec) -> Model: ...
    def submit(self, model: Model) -> JobHandle: ...
    def poll(self, job: JobHandle) -> JobStatus: ...
    def fetch_results(self, job: JobHandle) -> ResultSet: ...
```
This lets the UI stay analysis-agnostic while adapters handle the solver-specific API/scripting.

---

## 4. Analysis Modules to Support

Map each of the following to a solver adapter and a dedicated UI workflow (geometry → material →
boundary conditions → mesh → solve → post-process):

### Core Structural & Solid Mechanics
| Analysis | Primary Engine Option |
|---|---|
| Static Structural (linear/nonlinear) | PyMAPDL / CalculiX |
| Modal Analysis (free or pre-stressed) | PyMAPDL / CalculiX |
| Buckling (linear eigenvalue, nonlinear post-buckling) | PyMAPDL |
| Fatigue (S-N, E-N, crack growth, thermal fatigue) | PyMAPDL fatigue tools |
| Fracture Mechanics (SIF, J-integral, SMART crack growth) | PyMAPDL SMART Crack Growth |
| Composite Analysis (ply failure, delamination, ACP) | PyACP + PyMAPDL |
| Rigid Body Dynamics (mechanisms, joints, contacts) | PyMAPDL Rigid Dynamics / custom multibody lib (e.g., `pychrono`) |
| Structural Optimization (topology, shape, parameter) | DesignXplorer / optiSLang, or `SciPy`/`Optuna`/`pymoo` for custom loops |

### Dynamics & Vibration
| Analysis | Primary Engine Option |
|---|---|
| Harmonic Response | PyMAPDL |
| Response Spectrum | PyMAPDL |
| Random Vibration (PSD) | PyMAPDL |
| Transient Structural (implicit) | PyMAPDL |
| Explicit Dynamics (impact, crash, blast) | Autodyn / LS-DYNA |

### Thermal & Thermo-Mechanical
| Analysis | Primary Engine Option |
|---|---|
| Steady-State Thermal | PyMAPDL |
| Transient Thermal (incl. phase change) | PyMAPDL |
| Thermal-Structural Coupling (1-way/2-way) | PyMAPDL coupled fields |
| Thermal-Electric (Joule heating, Peltier) | PyMAPDL coupled-field elements |

### Fluid Dynamics & FSI
| Analysis | Primary Engine Option |
|---|---|
| Laminar & Turbulent Flow | PyFluent / OpenFOAM |
| Heat Transfer in Fluids / CHT | PyFluent / OpenFOAM |
| Multiphase Flow (free surface, cavitation, particle tracking) | PyFluent (VOF, DPM) / OpenFOAM |
| Turbomachinery | PyFluent (Turbo workflow) |
| Moving/Sliding Meshes | PyFluent dynamic mesh / OpenFOAM `snappyHexMesh` + dynamicMesh |
| Fluid-Structure Interaction (1-way/2-way) | PyMAPDL ⇄ PyFluent System Coupling |

### Multiphysics & Specialized
| Analysis | Primary Engine Option |
|---|---|
| Acoustic-Structure Coupling (vibro-acoustics) | PyMAPDL acoustic elements |
| Piezoelectric & MEMS | PyMAPDL coupled-field piezo elements |
| Additive Manufacturing Simulation | PyAdditive |
| Material Designer (homogenization) | PyMAPDL Material Designer / custom FEniCS homogenization |
| Discrete Element Method | Rocky API / LIGGGHTS |
| Electromagnetic-Thermal-Structural | Maxwell (via `pyaedt`) + PyMAPDL coupling |

---

## 5. Core Features for the Web UI

1. **Project workspace** — versioned projects, each holding geometry, mesh, materials, load cases, and results
2. **Geometry/mesh import** — STEP/IGES/STL upload, Gmsh-based meshing with quality checks, mesh preview in-browser
3. **Analysis wizard** — pick analysis type from the taxonomy above; guided forms for materials, BCs, loads, solver settings
4. **Job monitor** — live queue status, log tail, convergence/residual plots via WebSocket
5. **Results viewer** — 3D contour plots (stress, strain, temperature, velocity), animations, XY plots (S-N curves, frequency response, Campbell diagrams), report export (PDF/DOCX)
6. **Optimization studio** — parametric sweeps, DOE, response surfaces, topology optimization visualization
7. **Collaboration** — shared projects, comments, role-based access (viewer/engineer/admin)
8. **API-first design** — every UI action backed by a REST/WebSocket endpoint, so batch/scripted runs are possible too

---

## 6. Suggested Repository Structure

```
cae-webapp/
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI routers
│   │   ├── core/                # config, auth, security
│   │   ├── models/              # Pydantic + ORM schemas
│   │   ├── services/
│   │   │   ├── mesh_service.py
│   │   │   ├── job_service.py
│   │   │   └── results_service.py
│   │   ├── solvers/
│   │   │   ├── base.py          # SolverAdapter Protocol
│   │   │   ├── mapdl_adapter.py
│   │   │   ├── fluent_adapter.py
│   │   │   ├── openfoam_adapter.py
│   │   │   ├── explicit_adapter.py
│   │   │   ├── dem_adapter.py
│   │   │   └── maxwell_adapter.py
│   │   └── main.py
│   ├── workers/                 # Celery tasks
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/          # 3D viewer, plot widgets, forms
│   │   ├── pages/                # Project, AnalysisWizard, Results
│   │   └── api/                  # typed API client
├── docker/
│   ├── mapdl.Dockerfile
│   ├── fluent.Dockerfile
│   ├── openfoam.Dockerfile
│   └── backend.Dockerfile
└── infra/                       # k8s manifests / Terraform
```

---

## 7. Build Order (practical rollout)

1. Auth, project CRUD, file storage (foundation — no solver yet)
2. Static Structural + Modal via PyMAPDL (proves the solver-adapter pattern end to end)
3. Thermal + Thermal-Structural coupling
4. Results viewer with 3D contour rendering (PyVista → web)
5. Harmonic/Random Vibration/Transient/Response Spectrum
6. Buckling, Fatigue, Fracture (SMART)
7. Composite Analysis (ACP)
8. CFD via PyFluent/OpenFOAM, then FSI coupling
9. Explicit Dynamics, DEM, Electromagnetics (specialized, lower-frequency use cases)
10. Optimization studio (DesignXplorer/optiSLang or custom SciPy/Optuna loops) layered on top of everything else
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the 'backend' directory is in sys.path when running main.py directly
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import os
import sys
import time
from contextlib import asynccontextmanager

# ── Windows UTF-8 fix ─────────────────────────────────────────────────────────
# Ensure stdout/stderr use UTF-8 so Unicode chars in log messages (✓, …, etc.)
# don't cause UnicodeEncodeError on Windows with cp1252 default encoding.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CAD-CAE Analyzer API", env=settings.app_env)
    await init_db()
    logger.info("Database initialized")

    try:
        from app.workers.seed import seed_materials
        await seed_materials()
    except Exception as e:
        logger.warning("Material seeding skipped", error=str(e))

    if settings.chatbot_enabled and settings.gemini_api_key:
        try:
            from app.chatbot.rag_pipeline import init_knowledge_base
            await init_knowledge_base()
        except Exception as e:
            logger.warning("RAG init skipped", error=str(e))

    yield
    logger.info("Shutting down")


app = FastAPI(
    title="CAD-CAE Analyzer API",
    description="Upload CAD files, auto-detect geometry, run FEA/CFD, get AI-powered results.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter()-start)*1000:.1f}"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    logger.error("Unhandled exception", path=request.url.path, error=str(exc), traceback=tb)
    detail = str(exc)
    if settings.debug:
        detail = tb
    return JSONResponse(status_code=500, content={"success": False, "message": detail})


# ── Routers ────────────────────────────────────────────────────────────────────
from app.api.upload import router as upload_router
from app.api._routers import (
    projects_router, analysis_router, jobs_router,
    results_router, materials_router, chat_router,
    auth_router,
)

app.include_router(auth_router,      prefix=settings.api_prefix, tags=["Auth"])
app.include_router(upload_router,    prefix=settings.api_prefix, tags=["Upload"])
app.include_router(projects_router,  prefix=settings.api_prefix, tags=["Projects"])
app.include_router(analysis_router,  prefix=settings.api_prefix, tags=["Analysis"])
app.include_router(jobs_router,      prefix=settings.api_prefix, tags=["Jobs"])
app.include_router(results_router,   prefix=settings.api_prefix, tags=["Results"])
app.include_router(chat_router,      prefix=settings.api_prefix, tags=["Chat"])
app.include_router(materials_router, prefix=settings.api_prefix, tags=["Materials"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "env": settings.app_env,
        "mock_cad": settings.mock_cad_mode,
        "mock_solver": settings.mock_solver_mode,
        "chatbot_enabled": settings.chatbot_enabled and bool(settings.gemini_api_key),
    }


@app.get("/", tags=["Root"])
async def root():
    return {"name": settings.app_name, "version": "0.1.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
