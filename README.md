# CAD-to-CAE Automated Analysis Platform

A full-stack Python + React web application that accepts CAD file uploads, automatically detects geometry characteristics, suggests CAE analyses, runs open-source FEA/CFD solvers (CalculiX, OpenFOAM), and returns interactive 3D results with an AI-powered chatbot.

---

## 🚀 Quick Start (Local Dev — Windows, No Docker)

```bash
# 1. Copy environment file
cp .env.example .env
# (leave MOCK_SOLVER_MODE=true and MOCK_CAD_MODE=true for local dev)

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173

> **Note**: In mock mode, geometry analysis uses `trimesh` (STL/OBJ only). STEP/IGES files are parsed with a synthetic demo geometry. The solvers return physically-plausible computed results without needing CalculiX or OpenFOAM installed.

---

## 🐳 Full Stack via Docker Compose

Requires Docker Desktop (WSL2 backend on Windows):

```bash
# Copy and configure env
cp .env.example .env
# Set MOCK_SOLVER_MODE=false and MOCK_CAD_MODE=false

# Start all services
docker compose up -d

# Check status
docker compose ps
docker compose logs -f api
```

Services:
| URL | Service |
|-----|---------|
| http://localhost:5173 | React Frontend |
| http://localhost:8000 | FastAPI Backend |
| http://localhost:8000/docs | API Docs (Swagger) |
| http://localhost:5555 | Celery Flower (job monitoring) |

---

## 🏗 Project Structure

```
cad-cae-app/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Settings (pydantic-settings)
│   │   ├── database.py                # SQLAlchemy async engine
│   │   ├── models/                    # DB models + Pydantic schemas
│   │   ├── api/                       # FastAPI routers
│   │   ├── cad_import/parser.py       # CAD parsing (trimesh + pythonocc)
│   │   ├── geometry_analysis/         # Feature extraction + suggestion engine
│   │   ├── solvers/
│   │   │   ├── structural/            # CalculiX wrapper (static, modal)
│   │   │   ├── thermal/               # CalculiX thermal
│   │   │   ├── fatigue/sn_curve.py    # S-N curve + Goodman correction
│   │   │   └── cfd/openfoam_wrapper.py # OpenFOAM wrapper
│   │   ├── chatbot/                   # Claude API + RAG (ChromaDB)
│   │   └── workers/                   # Celery tasks + material seed
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx                    # React Router
│       ├── index.css                  # Full design system
│       ├── api/client.ts              # Typed API + SSE helpers
│       ├── store/index.ts             # Zustand global state
│       ├── pages/                     # HomePage, Upload, Analysis, Solver, Results
│       └── components/                # Sidebar, ChatWidget, Layout
├── solver-containers/
│   └── calculix/Dockerfile            # CalculiX 2.22 container
├── docker-compose.yml
└── .env.example
```

---

## 🔬 Supported Analyses

| Analysis | Solver | Status |
|----------|--------|--------|
| Static Structural | CalculiX | ✓ (mock + real) |
| Modal Analysis | CalculiX FREQUENCY | ✓ (mock + real) |
| Buckling | CalculiX BUCKLE | Scaffolded |
| Nonlinear Structural | CalculiX NLGEOM | Scaffolded |
| Thermal Steady-State | CalculiX HEAT TRANSFER | ✓ (mock + real) |
| Thermal Transient | CalculiX | Scaffolded |
| Fatigue (S-N) | Custom Python | ✓ (Goodman/Soderberg) |
| CFD Internal Flow | OpenFOAM simpleFoam | ✓ (mock + real) |
| CFD External Flow | OpenFOAM | Scaffolded |

---

## 🤖 AI Chatbot

The chatbot uses **Claude API** (Anthropic) with:
- Project/job context injection (geometry features, result values)
- RAG knowledge base (ChromaDB) with CAE engineering docs
- Streaming SSE response to the frontend
- Fallback stub when API key is not set

Set `ANTHROPIC_API_KEY` in `.env` to enable full responses.

---

## 📐 Geometry Feature Detection

Automatically detected from uploaded CAD:

| Feature | Detection Method |
|---------|-----------------|
| Thin-walled | Surface/volume ratio + bbox aspect ratio |
| Holes/fillets | Face normal variance (high curvature regions) |
| Internal cavity | Convex hull vs actual volume fraction |
| Symmetry | CoM vs bbox centroid offset |
| Slenderness | max_dim / min_dim ratio |

---

## ⚠ Important Disclaimer

This tool is a **decision-support aid** for engineers. It is **not a replacement** for:
- A qualified Professional Engineer's review
- Code-compliant design calculations
- Physical prototype testing

Always verify safety-critical results with licensed engineering review.

---

## 🛠 Development Notes

### Adding a New Analysis Type
1. Add enum value to `AnalysisType` in `backend/app/models/db_models.py`
2. Add solver function in `backend/app/solvers/`
3. Add dispatch branch in `backend/app/workers/tasks.py`
4. Add suggestion rule in `backend/app/geometry_analysis/suggestion_engine.py`
5. Add `AnalysisType` to frontend `client.ts` types

### Running Tests
```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

### Benchmark Validation
- **Cantilever beam**: 100×10×10mm steel, 100N tip load → δ ≈ 0.064mm, σ_max ≈ 60MPa
- **Modal (simply supported plate)**: Compare first frequency against analytical Euler-Bernoulli formula
