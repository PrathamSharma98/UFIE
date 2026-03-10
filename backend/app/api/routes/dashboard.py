from fastapi import APIRouter
from datetime import datetime
from app.database import data_store
from app.services.ward_scoring import calculate_ward_scores
from app.services.gis_analysis import get_hotspot_summary
from app.services.infrastructure_gap import detect_infrastructure_gaps

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary")
async def get_dashboard_summary():
    """Get comprehensive dashboard summary."""
    hotspots = data_store.get_hotspots()
    wards = data_store.get_wards()
    drainage = data_store.get_drainage()
    pumps = data_store.get_pumps()
    rainfall = data_store.get_rainfall()

    hotspot_summary = get_hotspot_summary(hotspots)
    ward_scores = calculate_ward_scores(wards, hotspots, drainage, pumps)
    gaps = detect_infrastructure_gaps(wards, hotspots, drainage, pumps)

    undersized = len([f for f in drainage.get("features", []) if f["properties"].get("is_undersized")])
    critical_hotspots = hotspot_summary.get("by_severity", {}).get("Critical", 0)
    avg_score = round(sum(s.get("readiness_score", 0) for s in ward_scores) / max(len(ward_scores), 1), 1)
    high_risk = len([s for s in ward_scores if s.get("readiness_score", 100) <= 30])

    return {
        "total_hotspots": hotspot_summary.get("total_count", 0),
        "critical_hotspots": critical_hotspots,
        "high_risk_wards": high_risk,
        "avg_readiness_score": avg_score,
        "total_pump_stations": len(pumps.get("features", [])),
        "undersized_drains": undersized,
        "total_wards": len(wards.get("features", [])),
        "total_drainage_segments": len(drainage.get("features", [])),
        "infrastructure_gaps": len(gaps),
        "last_updated": datetime.utcnow().isoformat(),
    }

@router.get("/wards")
async def get_wards_geojson():
    """Get ward boundaries GeoJSON."""
    return data_store.get_wards()

@router.get("/drainage")
async def get_drainage_geojson():
    """Get drainage network GeoJSON."""
    return data_store.get_drainage()

@router.get("/pumps")
async def get_pumps_geojson():
    """Get pump stations GeoJSON."""
    return data_store.get_pumps()

@router.get("/rainfall")
async def get_rainfall_data():
    """Get historical rainfall data."""
    return {"data": data_store.get_rainfall()}

@router.get("/dem")
async def get_dem_data():
    """Get DEM elevation grid."""
    return {"data": data_store.get_dem()}
