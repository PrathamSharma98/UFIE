"""Urban Flood Intelligence Engine - FastAPI Application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import data_store
from app.api.routes import hotspots, flood_prediction, ward_score, simulation, ai_query, infrastructure, dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Urban Flood Intelligence Engine...")
    data_store.load_data()
    logger.info(f"Loaded {len(data_store.get_hotspots().get('features', []))} hotspots")
    logger.info(f"Loaded {len(data_store.get_wards().get('features', []))} wards")
    yield
    logger.info("Shutting down UFIE...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-driven GIS platform for urban flood risk prediction and management",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard.router)
app.include_router(hotspots.router)
app.include_router(flood_prediction.router)
app.include_router(ward_score.router)
app.include_router(simulation.router)
app.include_router(ai_query.router)
app.include_router(infrastructure.router)

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
