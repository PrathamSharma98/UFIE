"""Pydantic schemas for the UFIE flood intelligence platform."""

from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Hotspot & Ward schemas
# ---------------------------------------------------------------------------

class HotspotResponse(BaseModel):
    """A single flood hotspot with geospatial and risk attributes."""

    hotspot_id: str = Field(..., description="Unique identifier for the hotspot")
    ward_id: str = Field(..., description="Ward in which the hotspot falls")
    ward_name: str = Field(..., description="Human-readable ward name")
    lat: float = Field(..., description="Latitude (WGS-84)")
    lng: float = Field(..., description="Longitude (WGS-84)")
    elevation_m: float = Field(..., description="Elevation in metres above MSL")
    slope_deg: float = Field(..., description="Terrain slope in degrees")
    flow_accumulation: float = Field(
        ..., description="Upstream contributing cells (flow accumulation)"
    )
    drainage_proximity_m: float = Field(
        ..., description="Distance to nearest drainage channel in metres"
    )
    impervious_surface_pct: float = Field(
        ..., description="Percentage of impervious surface cover (0-100)"
    )
    soil_permeability: float = Field(
        ..., description="Soil permeability index (0 = impermeable, 1 = fully permeable)"
    )
    flood_probability: float = Field(
        ..., ge=0.0, le=1.0, description="ML-predicted flood probability (0-1)"
    )
    severity: str = Field(
        ..., description="Risk category: critical | high | moderate | low"
    )
    affected_population: int = Field(
        ..., description="Estimated population at risk"
    )
    estimated_damage_inr_lakhs: float = Field(
        ..., description="Estimated monetary damage in INR lakhs"
    )
    runoff_coefficient: float = Field(
        ..., ge=0.0, le=1.0, description="Runoff coefficient (0-1)"
    )


class WardScore(BaseModel):
    """Ward-level flood readiness score card."""

    ward_id: str
    ward_name: str
    readiness_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall readiness score (0-100)"
    )
    drainage_capacity_index: float = Field(
        ..., description="Drainage capacity index (0-1)"
    )
    emergency_infrastructure_coverage: float = Field(
        ..., description="Coverage fraction of emergency infrastructure (0-1)"
    )
    flood_hotspot_density: float = Field(
        ..., description="Hotspots per sq-km"
    )
    rainfall_vulnerability: float = Field(
        ..., description="Rainfall vulnerability index (0-1)"
    )
    pump_station_availability: float = Field(
        ..., description="Pump station availability fraction (0-1)"
    )
    category: str = Field(
        ..., description="Readiness category: well-prepared | moderate | under-prepared | critical"
    )
    population: int = Field(..., description="Ward population")
    area_km2: float = Field(..., description="Ward area in sq-km")


# ---------------------------------------------------------------------------
# Flood prediction schemas
# ---------------------------------------------------------------------------

class FloodPredictionRequest(BaseModel):
    """Request body for a point-level flood prediction."""

    lat: float = Field(..., description="Latitude of the query point")
    lng: float = Field(..., description="Longitude of the query point")
    rainfall_intensity_mmh: float = Field(
        ..., gt=0, description="Rainfall intensity in mm/h"
    )
    elevation_m: Optional[float] = Field(
        None, description="Elevation in metres (auto-derived if omitted)"
    )
    slope_deg: Optional[float] = Field(
        None, description="Slope in degrees (auto-derived if omitted)"
    )


class FloodPredictionResponse(BaseModel):
    """Response for a point-level flood prediction."""

    lat: float
    lng: float
    flood_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Predicted probability of flooding (0-1)"
    )
    risk_level: str = Field(
        ..., description="Risk level: critical | high | moderate | low"
    )
    contributing_factors: dict = Field(
        default_factory=dict,
        description="Key factors contributing to the prediction",
    )


# ---------------------------------------------------------------------------
# Rainfall simulation schemas
# ---------------------------------------------------------------------------

class WardImpact(BaseModel):
    """Per-ward impact detail within a rainfall simulation response."""

    ward_id: str
    ward_name: str
    flood_risk: str = Field(
        ..., description="Risk level: critical | high | moderate | low"
    )
    activated_hotspots: int = Field(
        ..., description="Number of hotspots activated in this ward"
    )
    estimated_runoff_m3: float = Field(
        ..., description="Estimated surface runoff volume in cubic metres"
    )
    drainage_capacity_exceeded: bool = Field(
        ..., description="Whether the drainage capacity is exceeded"
    )


class RainfallSimulationRequest(BaseModel):
    """Request body for a rainfall simulation scenario."""

    intensity_mmh: float = Field(
        ..., gt=0, description="Rainfall intensity in mm/h"
    )
    duration_hours: float = Field(
        3.0, gt=0, description="Duration of the rainfall event in hours"
    )


class RainfallSimulationResponse(BaseModel):
    """Response for a rainfall simulation scenario."""

    intensity_mmh: float
    duration_hours: float
    total_rainfall_mm: float = Field(
        ..., description="Total rainfall (intensity x duration)"
    )
    affected_wards: list[str] = Field(
        default_factory=list, description="List of ward IDs affected"
    )
    activated_hotspots: int = Field(
        ..., description="Number of flood hotspots activated"
    )
    total_hotspots: int = Field(
        ..., description="Total number of hotspots in the system"
    )
    runoff_volume_m3: float = Field(
        ..., description="Total surface runoff volume in cubic metres"
    )
    peak_discharge_m3s: float = Field(
        ..., description="Peak discharge in cubic metres per second"
    )
    ward_impacts: list[WardImpact] = Field(
        default_factory=list, description="Per-ward impact details"
    )


# ---------------------------------------------------------------------------
# AI assistant schemas
# ---------------------------------------------------------------------------

class AIQueryRequest(BaseModel):
    """Request body for an AI-assisted query."""

    query: str = Field(..., min_length=1, description="User question in natural language")
    context: Optional[str] = Field(
        None, description="Optional additional context for the AI model"
    )


class AIQueryResponse(BaseModel):
    """Response for an AI-assisted query."""

    query: str
    response: str = Field(..., description="AI-generated answer")
    sources: list[str] = Field(
        default_factory=list, description="Data sources referenced"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Follow-up question suggestions"
    )


# ---------------------------------------------------------------------------
# Infrastructure gap schemas
# ---------------------------------------------------------------------------

class InfrastructureGap(BaseModel):
    """A single infrastructure gap identified in a ward."""

    ward_id: str
    ward_name: str
    gap_type: str = Field(
        ..., description="Type of gap: drainage | pump | shelter | road | medical"
    )
    description: str = Field(..., description="Human-readable description of the gap")
    severity: str = Field(
        ..., description="Severity: critical | high | moderate | low"
    )
    recommended_action: str = Field(
        ..., description="Recommended remediation action"
    )
    estimated_cost_inr_crores: float = Field(
        ..., ge=0.0, description="Estimated remediation cost in INR crores"
    )


# ---------------------------------------------------------------------------
# Dashboard summary schema
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    """High-level dashboard metrics."""

    total_hotspots: int
    critical_hotspots: int
    high_risk_wards: int
    avg_readiness_score: float
    total_pump_stations: int
    undersized_drains: int
    last_updated: str = Field(
        ..., description="ISO-8601 timestamp of the last data refresh"
    )
