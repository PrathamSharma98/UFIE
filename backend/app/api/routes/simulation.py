from fastapi import APIRouter
from app.database import data_store
from app.models.schemas import RainfallSimulationRequest
from app.services.rainfall_simulation import simulate_rainfall, simulate_progressive_rainfall

router = APIRouter(prefix="/api/simulate-rainfall", tags=["Simulation"])

@router.post("/")
async def run_simulation(request: RainfallSimulationRequest):
    """Simulate a rainfall event and see flood impacts."""
    result = simulate_rainfall(
        intensity_mmh=request.intensity_mmh,
        duration_hours=request.duration_hours,
        wards_geojson=data_store.get_wards(),
        hotspots_geojson=data_store.get_hotspots(),
        drainage_geojson=data_store.get_drainage()
    )
    return result

@router.get("/progressive")
async def progressive_simulation(duration_hours: float = 3.0):
    """Run simulation at multiple rainfall intensities."""
    intensities = [10, 20, 30, 50, 75, 100, 150]
    results = simulate_progressive_rainfall(
        intensities=intensities, duration_hours=duration_hours,
        wards_geojson=data_store.get_wards(),
        hotspots_geojson=data_store.get_hotspots(),
        drainage_geojson=data_store.get_drainage()
    )
    return {"simulations": results}
