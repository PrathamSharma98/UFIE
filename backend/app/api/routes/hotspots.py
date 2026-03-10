from fastapi import APIRouter, Query
from typing import Optional
from app.database import data_store
from app.services.gis_analysis import filter_hotspots, get_hotspot_summary, cluster_hotspots

router = APIRouter(prefix="/api/hotspots", tags=["Hotspots"])

@router.get("/")
async def get_hotspots(ward_id: Optional[int] = None, min_probability: Optional[float] = None, severity: Optional[str] = None, limit: int = Query(default=500, le=3000)):
    """Get flood hotspots with optional filters."""
    hotspots = data_store.get_hotspots()
    if ward_id or min_probability or severity:
        hotspots = filter_hotspots(hotspots, ward_id=ward_id, min_probability=min_probability, severity=severity)
    # Limit features
    if limit and len(hotspots.get("features", [])) > limit:
        hotspots = {**hotspots, "features": hotspots["features"][:limit]}
    return hotspots

@router.get("/summary")
async def get_summary():
    """Get hotspot summary statistics."""
    return get_hotspot_summary(data_store.get_hotspots())

@router.get("/clusters")
async def get_clusters(method: str = "dbscan"):
    """Get clustered hotspots."""
    return cluster_hotspots(data_store.get_hotspots(), method=method)
