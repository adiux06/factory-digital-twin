import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
STORAGE_DIR = BACKEND_DIR / "storage"

class Settings(BaseModel):
    PROJECT_NAME: str = "FactoryTwin"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR}/factorytwin.db")
    WS_TICK_RATE_MS: int = 250
    DEFAULT_GRID_WIDTH: int = 20
    DEFAULT_GRID_HEIGHT: int = 15

settings = Settings()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "uploads").mkdir(parents=True, exist_ok=True)
