from fastapi import APIRouter
from app.database import data_store
from app.services.ward_scoring import calculate_ward_scores, get_ward_rankings, get_risk_alerts, get_category_distribution

router = APIRouter(prefix="/api/ward-score", tags=["Ward Score"])

@router.get("/")
async def get_ward_scores():
    """Get Pre-Monsoon Readiness Scores for all wards."""
    scores = calculate_ward_scores(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return {"scores": scores}

@router.get("/rankings")
async def get_rankings():
    """Get ward rankings by readiness score."""
    scores = calculate_ward_scores(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return {"rankings": get_ward_rankings(scores)}

@router.get("/alerts")
async def get_alerts():
    """Get risk alerts for critical wards."""
    scores = calculate_ward_scores(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return {"alerts": get_risk_alerts(scores)}

@router.get("/distribution")
async def get_distribution():
    """Get readiness score category distribution."""
    scores = calculate_ward_scores(
        data_store.get_wards(), data_store.get_hotspots(),
        data_store.get_drainage(), data_store.get_pumps()
    )
    return get_category_distribution(scores)
