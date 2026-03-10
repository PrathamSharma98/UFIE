from fastapi import APIRouter
from app.database import data_store
from app.services.infrastructure_gap import detect_infrastructure_gaps, generate_improvement_recommendations, get_gap_summary

router = APIRouter(prefix="/api/infrastructure", tags=["Infrastructure"])

@router.get("/gaps")
async def get_gaps():
    """Detect infrastructure gaps across all wards."""
    gaps = detect_infrastructure_gaps(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return {"gaps": gaps, "total": len(gaps)}

@router.get("/recommendations")
async def get_recommendations():
    """Get prioritized improvement recommendations."""
    gaps = detect_infrastructure_gaps(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return {"recommendations": generate_improvement_recommendations(gaps)}

@router.get("/summary")
async def get_gap_summary_endpoint():
    """Get infrastructure gap summary."""
    gaps = detect_infrastructure_gaps(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return get_gap_summary(gaps)
