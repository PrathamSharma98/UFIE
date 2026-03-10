from fastapi import APIRouter
from app.database import data_store
from app.models.schemas import FloodPredictionRequest, FloodPredictionResponse
from app.ml.features import extract_features_for_prediction
from app.ml.train_model import get_or_train_model, predict_flood_risk

router = APIRouter(prefix="/api/flood-prediction", tags=["Flood Prediction"])

@router.post("/", response_model=FloodPredictionResponse)
async def predict_flood(request: FloodPredictionRequest):
    """Predict flood risk for a specific location."""
    hotspots = data_store.get_hotspots()
    model, metrics = get_or_train_model(hotspots)
    features = extract_features_for_prediction(
        lat=request.lat, lng=request.lng,
        rainfall_intensity=request.rainfall_intensity_mmh,
        elevation=request.elevation_m, slope=request.slope_deg,
        dem_grid=data_store.get_dem(), drainage=data_store.get_drainage()
    )
    result = predict_flood_risk(model, features)
    return FloodPredictionResponse(
        lat=request.lat, lng=request.lng,
        flood_probability=result["probability"],
        risk_level=result["risk_level"],
        contributing_factors=result["contributing_factors"]
    )

@router.get("/model-info")
async def get_model_info():
    """Get info about the trained model."""
    hotspots = data_store.get_hotspots()
    _, metrics = get_or_train_model(hotspots)
    return {"model_type": "xgboost", "metrics": metrics}
