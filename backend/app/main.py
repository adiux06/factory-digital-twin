import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, DATASETS_DIR, STORAGE_DIR
from app.db.session import init_db
from app.inspection.dataset import create_industrial_inspection_dataset
from app.api.simulations import router as simulations_router
from app.api.inspection import router as inspection_router
from app.api.benchmarks import router as benchmarks_router
from app.websocket.router import router as websocket_router
from app.services.simulation_manager import simulation_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database & Sample Datasets
    init_db()
    create_industrial_inspection_dataset(DATASETS_DIR.parent)
    
    # Pre-instantiate a primary default simulation for instant frontend connection
    default_sim = simulation_manager.create_simulation(
        scheduling_policy="NEAREST_ROBOT",
        num_robots=3,
        scenario_id="default_factory",
    )
    app.state.default_sim_id = default_sim.id
    print(f"FactoryTwin initialized with default simulation ID: {default_sim.id}")
    
    yield
    # Shutdown logic if any
    pass


app = FastAPI(
    title="FactoryTwin API",
    description="Intelligent Factory Simulation and AI Inspection Platform Backend API",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS middleware for modern frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for inspection images and uploads
samples_path = DATASETS_DIR / "inspection" / "samples"
samples_path.mkdir(parents=True, exist_ok=True)
app.mount("/static/samples", StaticFiles(directory=str(samples_path)), name="samples")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FactoryTwin Simulation Platform",
        "version": settings.VERSION,
        "default_simulation_id": getattr(app.state, "default_sim_id", None),
    }


# Include Routers
app.include_router(simulations_router, prefix=settings.API_V1_PREFIX)
app.include_router(inspection_router, prefix=settings.API_V1_PREFIX)
app.include_router(benchmarks_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, app_dir=backend_root)


