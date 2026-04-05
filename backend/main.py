import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db
from backend.routers import profile, weight, menu, workout, meal_log, recommendation, dish_catalog
from backend.services.ollama_service import check_ollama_available, get_available_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Weight Assistant", version="0.1.0")

# Include routers
app.include_router(profile.router)
app.include_router(weight.router)
app.include_router(menu.router)
app.include_router(workout.router)
app.include_router(meal_log.router)
app.include_router(recommendation.router)
app.include_router(dish_catalog.router)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
def startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized.")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/status")
async def get_status():
    ollama_ok = await check_ollama_available()
    models = await get_available_models() if ollama_ok else []
    return {
        "status": "ok",
        "ollama_available": ollama_ok,
        "ollama_models": models,
    }
