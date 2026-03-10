"""
Rainfall simulation engine for UFIE backend.

Provides pure functions to simulate rainfall events across the city,
calculate runoff using the SCS method, determine hotspot activation,
and check drainage capacity exceedance.
"""

import numpy as np


def get_activation_threshold(base_probability: float, rainfall_intensity: float) -> float:
    """
    Calculate whether a hotspot activates under given rainfall intensity.

    A hotspot activates when its base_probability + rainfall_factor > 0.5.
    rainfall_factor = min(0.5, rainfall_intensity / 200)

    Args:
        base_probability: The hotspot's baseline flood probability (0-1).
        rainfall_intensity: Rainfall intensity in mm/h.

    Returns:
        The combined activation score (base_probability + rainfall_factor).
    """
    rainfall_factor = min(0.5, rainfall_intensity / 200.0)
    return base_probability + rainfall_factor


def simulate_rainfall(
    intensity_mmh: float,
    duration_hours: float,
    wards_geojson: dict,
    hotspots_geojson: dict,
    drainage_geojson: dict,
) -> dict:
    """
    Simulate a rainfall event across the city.

    Calculates total rainfall, per-ward runoff via the SCS curve-number method,
    hotspot activation under the given intensity, drainage capacity exceedance,
    and city-wide aggregate metrics.

    Args:
        intensity_mmh: Rainfall intensity in mm/h.
        duration_hours: Duration of the rainfall event in hours.
        wards_geojson: GeoJSON FeatureCollection of ward polygons with properties
            including ward_id, ward_name, impervious_surface_pct,
            soil_permeability, area_km2, and flood_risk_score.
        hotspots_geojson: GeoJSON FeatureCollection of flood hotspot points with
            properties including ward_id, flood_probability, and severity.
        drainage_geojson: GeoJSON FeatureCollection of drainage line segments with
            properties including ward_id, capacity_m3s, current_load_m3s,
            and condition.

    Returns:
        Dict matching RainfallSimulationResponse schema.
    """
    total_rainfall_mm = intensity_mmh * duration_hours

    # ---- Index hotspots and drainage by ward ----
    hotspots_by_ward: dict[str, list[dict]] = {}
    for feature in hotspots_geojson.get("features", []):
        props = feature.get("properties", {})
        wid = str(props.get("ward_id", ""))
        hotspots_by_ward.setdefault(wid, []).append(props)

    drainage_by_ward: dict[str, list[dict]] = {}
    for feature in drainage_geojson.get("features", []):
        props = feature.get("properties", {})
        wid = str(props.get("ward_id", ""))
        drainage_by_ward.setdefault(wid, []).append(props)

    # ---- Per-ward calculations ----
    ward_impacts: list[dict] = []
    affected_wards: list[str] = []
    total_activated_hotspots = 0
    total_hotspots = 0
    city_runoff_volume_m3 = 0.0

    for feature in wards_geojson.get("features", []):
        props = feature.get("properties", {})
        ward_id = str(props.get("ward_id", ""))
        ward_name = str(props.get("ward_name", ward_id))
        impervious_pct = float(props.get("impervious_surface_pct", 50))
        soil_permeability = float(props.get("soil_permeability", 0.5))
        area_km2 = float(props.get("area_km2", 1.0))

        # --- SCS Curve Number runoff estimation ---
        # Higher impervious % and lower soil permeability -> higher CN
        cn = np.clip(
            55 + 40 * (impervious_pct / 100.0) - 15 * soil_permeability,
            30,
            98,
        )
        # Potential maximum retention S (mm)
        s_mm = (25400.0 / cn) - 254.0
        # Initial abstraction Ia (mm) — commonly 0.2 * S
        ia_mm = 0.2 * s_mm

        if total_rainfall_mm > ia_mm:
            runoff_mm = ((total_rainfall_mm - ia_mm) ** 2) / (
                total_rainfall_mm - ia_mm + s_mm
            )
        else:
            runoff_mm = 0.0

        # Convert runoff depth to volume: mm * km^2 -> m^3
        estimated_runoff_m3 = runoff_mm * area_km2 * 1_000.0  # 1 mm over 1 km^2 = 1000 m^3

        city_runoff_volume_m3 += estimated_runoff_m3

        # --- Hotspot activation for this ward ---
        ward_hotspots = hotspots_by_ward.get(ward_id, [])
        total_hotspots += len(ward_hotspots)
        ward_activated = 0
        for hs in ward_hotspots:
            base_prob = float(hs.get("flood_probability", 0.0))
            score = get_activation_threshold(base_prob, intensity_mmh)
            if score > 0.5:
                ward_activated += 1
        total_activated_hotspots += ward_activated

        # --- Drainage capacity check ---
        ward_drains = drainage_by_ward.get(ward_id, [])
        drainage_exceeded = False
        for drain in ward_drains:
            capacity = float(drain.get("capacity_m3s", 0))
            current_load = float(drain.get("current_load_m3s", 0))
            # Extra load proportional to runoff and intensity
            extra_load = (intensity_mmh / 100.0) * (area_km2 * 0.5)
            if capacity > 0 and (current_load + extra_load) > capacity:
                drainage_exceeded = True
                break

        # --- Determine flood risk label ---
        flood_risk_score = float(props.get("flood_risk_score", 0))
        if flood_risk_score >= 0.7 or (ward_activated > 0 and drainage_exceeded):
            flood_risk = "High"
        elif flood_risk_score >= 0.4 or ward_activated > 0 or drainage_exceeded:
            flood_risk = "Moderate"
        else:
            flood_risk = "Low"

        if flood_risk in ("High", "Moderate"):
            affected_wards.append(ward_name)

        ward_impacts.append(
            {
                "ward_id": ward_id,
                "ward_name": ward_name,
                "flood_risk": flood_risk,
                "activated_hotspots": ward_activated,
                "estimated_runoff_m3": round(estimated_runoff_m3, 2),
                "drainage_capacity_exceeded": drainage_exceeded,
            }
        )

    # ---- City-wide peak discharge estimate (rational method) ----
    # Q = C * i * A  (simplified, C ~ avg runoff coefficient)
    total_area_km2 = sum(
        float(f.get("properties", {}).get("area_km2", 1.0))
        for f in wards_geojson.get("features", [])
    )
    avg_runoff_coeff = (
        city_runoff_volume_m3 / (total_rainfall_mm * total_area_km2 * 1_000.0)
        if total_rainfall_mm > 0 and total_area_km2 > 0
        else 0.0
    )
    # intensity in m/s, area in m^2
    intensity_m_s = intensity_mmh / (3_600_000.0)
    area_m2 = total_area_km2 * 1e6
    peak_discharge_m3s = avg_runoff_coeff * intensity_m_s * area_m2

    return {
        "intensity_mmh": intensity_mmh,
        "duration_hours": duration_hours,
        "total_rainfall_mm": round(total_rainfall_mm, 2),
        "affected_wards": affected_wards,
        "activated_hotspots": total_activated_hotspots,
        "total_hotspots": total_hotspots,
        "runoff_volume_m3": round(city_runoff_volume_m3, 2),
        "peak_discharge_m3s": round(peak_discharge_m3s, 4),
        "ward_impacts": ward_impacts,
    }


def simulate_progressive_rainfall(
    intensities: list[float],
    duration_hours: float,
    wards_geojson: dict,
    hotspots_geojson: dict,
    drainage_geojson: dict,
) -> list[dict]:
    """
    Run the rainfall simulation at multiple intensities and return a list of results.

    Useful for scenario analysis (e.g., light rain through extreme downpour).

    Args:
        intensities: List of rainfall intensities in mm/h to simulate.
        duration_hours: Duration of the rainfall event in hours.
        wards_geojson: GeoJSON FeatureCollection of ward polygons.
        hotspots_geojson: GeoJSON FeatureCollection of flood hotspot points.
        drainage_geojson: GeoJSON FeatureCollection of drainage line segments.

    Returns:
        List of result dicts, one per intensity, each matching
        RainfallSimulationResponse schema.
    """
    results: list[dict] = []
    for intensity in intensities:
        result = simulate_rainfall(
            intensity_mmh=intensity,
            duration_hours=duration_hours,
            wards_geojson=wards_geojson,
            hotspots_geojson=hotspots_geojson,
            drainage_geojson=drainage_geojson,
        )
        results.append(result)
    return results
