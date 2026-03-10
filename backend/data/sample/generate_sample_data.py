"""Sample data generator for UFIE platform.

Generates realistic synthetic data for Delhi including:
- 2500+ flood micro-hotspots
- 30 ward boundaries with attributes
- Drainage network
- DEM elevation data
- Historical rainfall
- Pump stations
"""

import json
import math
import os
import random
from typing import Any

import numpy as np

random.seed(42)
np.random.seed(42)

# Delhi center and bounds
DELHI_CENTER = (28.6139, 77.2090)
DELHI_BOUNDS = {
    "min_lat": 28.40,
    "max_lat": 28.85,
    "min_lng": 76.85,
    "max_lng": 77.35,
}

WARD_NAMES = [
    "Connaught Place", "Karol Bagh", "Chandni Chowk", "Sadar Bazaar",
    "Paharganj", "Rajender Nagar", "Patel Nagar", "Moti Nagar",
    "Kirti Nagar", "Rajouri Garden", "Tilak Nagar", "Janakpuri",
    "Dwarka", "Vasant Kunj", "Mehrauli", "Hauz Khas",
    "Saket", "Lajpat Nagar", "Defence Colony", "Nizamuddin",
    "Mayur Vihar", "Preet Vihar", "Shahdara", "Seelampur",
    "Rohini", "Pitampura", "Ashok Vihar", "Model Town",
    "Civil Lines", "Narela"
]


def generate_ward_polygon(center_lat: float, center_lng: float,
                          radius: float = 0.02, sides: int = 8) -> list:
    """Generate an irregular polygon around a center point."""
    coords = []
    for i in range(sides):
        angle = (2 * math.pi * i / sides) + random.uniform(-0.3, 0.3)
        r = radius * random.uniform(0.7, 1.3)
        lat = center_lat + r * math.cos(angle)
        lng = center_lng + r * math.sin(angle) / math.cos(math.radians(center_lat))
        coords.append([round(lng, 6), round(lat, 6)])
    coords.append(coords[0])  # close polygon
    return coords


def generate_ward_boundaries() -> dict[str, Any]:
    """Generate GeoJSON ward boundaries for 30 wards."""
    features = []
    ward_centers = []

    # Distribute ward centers across Delhi
    grid_rows, grid_cols = 6, 5
    lat_step = (DELHI_BOUNDS["max_lat"] - DELHI_BOUNDS["min_lat"]) / grid_rows
    lng_step = (DELHI_BOUNDS["max_lng"] - DELHI_BOUNDS["min_lng"]) / grid_cols

    idx = 0
    for row in range(grid_rows):
        for col in range(grid_cols):
            if idx >= 30:
                break
            center_lat = DELHI_BOUNDS["min_lat"] + (row + 0.5) * lat_step + random.uniform(-0.02, 0.02)
            center_lng = DELHI_BOUNDS["min_lng"] + (col + 0.5) * lng_step + random.uniform(-0.02, 0.02)
            ward_centers.append((center_lat, center_lng))
            idx += 1

    for i, (clat, clng) in enumerate(ward_centers):
        population = random.randint(50000, 500000)
        area_km2 = round(random.uniform(5, 35), 2)
        urban_density = round(random.uniform(0.4, 0.98), 3)
        impervious_pct = round(random.uniform(30, 95), 1)
        drain_length_km = round(random.uniform(5, 80), 1)
        drain_capacity_m3s = round(random.uniform(2, 50), 2)
        pump_stations = random.randint(0, 8)
        emergency_shelters = random.randint(0, 5)
        historical_floods = random.randint(0, 25)
        avg_elevation = round(random.uniform(195, 260), 1)

        feature = {
            "type": "Feature",
            "properties": {
                "ward_id": i + 1,
                "ward_name": WARD_NAMES[i],
                "population": population,
                "area_km2": area_km2,
                "urban_density": urban_density,
                "impervious_surface_pct": impervious_pct,
                "drainage_length_km": drain_length_km,
                "drainage_capacity_m3s": drain_capacity_m3s,
                "pump_stations": pump_stations,
                "emergency_shelters": emergency_shelters,
                "historical_flood_events": historical_floods,
                "avg_elevation_m": avg_elevation,
                "soil_permeability": round(random.uniform(0.1, 0.8), 3),
                "green_cover_pct": round(random.uniform(2, 40), 1),
                "center_lat": round(clat, 6),
                "center_lng": round(clng, 6),
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [generate_ward_polygon(clat, clng)]
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def generate_flood_hotspots(wards: dict, count: int = 2700) -> dict[str, Any]:
    """Generate 2700 flood micro-hotspot points with risk attributes."""
    features = []
    hotspot_id = 0

    for ward_feature in wards["features"]:
        props = ward_feature["properties"]
        # More hotspots in high risk areas
        risk_factor = (props["impervious_surface_pct"] / 100 +
                       (1 - props["soil_permeability"]) +
                       props["historical_flood_events"] / 25)
        ward_count = max(30, int(count / 30 * risk_factor / 2))

        clat = props["center_lat"]
        clng = props["center_lng"]

        for _ in range(ward_count):
            hotspot_id += 1
            lat = clat + random.uniform(-0.02, 0.02)
            lng = clng + random.uniform(-0.025, 0.025)

            elevation = props["avg_elevation_m"] + random.uniform(-15, 15)
            slope = round(random.uniform(0.1, 8.0), 2)
            flow_accumulation = round(random.uniform(10, 10000), 1)
            drainage_proximity_m = round(random.uniform(5, 500), 1)
            impervious_local = min(100, max(0, props["impervious_surface_pct"] + random.uniform(-15, 15)))

            # Compute risk factors
            elev_risk = max(0, 1 - (elevation - 195) / 65)
            slope_risk = max(0, 1 - slope / 8)
            flow_risk = min(1, flow_accumulation / 8000)
            drain_risk = min(1, drainage_proximity_m / 400)
            imperv_risk = impervious_local / 100

            raw_risk = (elev_risk * 0.2 + slope_risk * 0.15 +
                        flow_risk * 0.25 + drain_risk * 0.2 + imperv_risk * 0.2)
            flood_probability = round(min(0.99, max(0.01, raw_risk + random.uniform(-0.1, 0.1))), 4)

            severity_map = {True: "Critical", False: ""}
            if flood_probability >= 0.7:
                severity = "Critical"
            elif flood_probability >= 0.5:
                severity = "High"
            elif flood_probability >= 0.3:
                severity = "Moderate"
            else:
                severity = "Low"

            feature = {
                "type": "Feature",
                "properties": {
                    "hotspot_id": hotspot_id,
                    "ward_id": props["ward_id"],
                    "ward_name": props["ward_name"],
                    "elevation_m": round(elevation, 2),
                    "slope_deg": slope,
                    "flow_accumulation": flow_accumulation,
                    "drainage_proximity_m": drainage_proximity_m,
                    "impervious_surface_pct": round(impervious_local, 1),
                    "soil_permeability": round(props["soil_permeability"] + random.uniform(-0.1, 0.1), 3),
                    "flood_probability": flood_probability,
                    "severity": severity,
                    "affected_population": random.randint(50, 5000),
                    "estimated_damage_inr_lakhs": round(random.uniform(1, 500), 1),
                    "runoff_coefficient": round(random.uniform(0.3, 0.95), 3),
                    "last_flood_year": random.choice([None, 2019, 2020, 2021, 2022, 2023, 2024, 2025]),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(lng, 6), round(lat, 6)]
                }
            }
            features.append(feature)

    # Ensure we have at least 2500
    while len(features) < 2700:
        base = random.choice(features)
        new_feature = json.loads(json.dumps(base))
        new_feature["properties"]["hotspot_id"] = len(features) + 1
        lat_off = random.uniform(-0.005, 0.005)
        lng_off = random.uniform(-0.005, 0.005)
        new_feature["geometry"]["coordinates"][0] += lng_off
        new_feature["geometry"]["coordinates"][1] += lat_off
        new_feature["properties"]["flood_probability"] = round(
            min(0.99, max(0.01, base["properties"]["flood_probability"] + random.uniform(-0.15, 0.15))), 4
        )
        features.append(new_feature)

    return {
        "type": "FeatureCollection",
        "features": features[:max(2700, len(features))]
    }


def generate_drainage_network(wards: dict) -> dict[str, Any]:
    """Generate synthetic drainage network lines."""
    features = []
    drain_id = 0

    for ward_feature in wards["features"]:
        props = ward_feature["properties"]
        clat = props["center_lat"]
        clng = props["center_lng"]
        num_drains = random.randint(8, 25)

        for _ in range(num_drains):
            drain_id += 1
            start_lat = clat + random.uniform(-0.02, 0.02)
            start_lng = clng + random.uniform(-0.025, 0.025)
            length = random.uniform(0.003, 0.015)
            angle = random.uniform(0, 2 * math.pi)

            end_lat = start_lat + length * math.cos(angle)
            end_lng = start_lng + length * math.sin(angle)

            capacity = round(random.uniform(0.5, 15), 2)
            current_load = round(capacity * random.uniform(0.3, 1.4), 2)

            feature = {
                "type": "Feature",
                "properties": {
                    "drain_id": drain_id,
                    "ward_id": props["ward_id"],
                    "capacity_m3s": capacity,
                    "current_load_m3s": current_load,
                    "utilization_pct": round(current_load / capacity * 100, 1),
                    "diameter_mm": random.choice([300, 450, 600, 900, 1200, 1500]),
                    "condition": random.choice(["Good", "Fair", "Poor", "Critical"]),
                    "age_years": random.randint(5, 60),
                    "material": random.choice(["RCC", "Brick", "HDPE", "Steel"]),
                    "is_undersized": current_load > capacity,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(start_lng, 6), round(start_lat, 6)],
                        [round(end_lng, 6), round(end_lat, 6)]
                    ]
                }
            }
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def generate_pump_stations(wards: dict) -> dict[str, Any]:
    """Generate pump station point data."""
    features = []
    pump_id = 0

    for ward_feature in wards["features"]:
        props = ward_feature["properties"]
        num_pumps = props["pump_stations"]
        clat = props["center_lat"]
        clng = props["center_lng"]

        for _ in range(num_pumps):
            pump_id += 1
            feature = {
                "type": "Feature",
                "properties": {
                    "pump_id": pump_id,
                    "ward_id": props["ward_id"],
                    "capacity_m3h": round(random.uniform(50, 2000), 0),
                    "status": random.choices(["Operational", "Under Maintenance", "Non-Functional"],
                                             weights=[0.7, 0.2, 0.1])[0],
                    "power_backup": random.choice([True, False]),
                    "last_maintenance": f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                    "year_installed": random.randint(2000, 2024),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        round(clng + random.uniform(-0.015, 0.015), 6),
                        round(clat + random.uniform(-0.015, 0.015), 6)
                    ]
                }
            }
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def generate_rainfall_data() -> list[dict]:
    """Generate 10 years of monthly rainfall data."""
    data = []
    for year in range(2016, 2027):
        for month in range(1, 13):
            # Delhi monsoon pattern: heavy rain June-September
            if month in [7, 8]:
                base = random.uniform(150, 350)
            elif month in [6, 9]:
                base = random.uniform(50, 180)
            elif month in [1, 2, 3, 10, 11, 12]:
                base = random.uniform(5, 40)
            else:
                base = random.uniform(15, 60)

            max_intensity = round(base / 10 * random.uniform(0.8, 2.5), 1)
            rainy_days = max(1, int(base / 15) + random.randint(-3, 5))

            data.append({
                "year": year,
                "month": month,
                "total_rainfall_mm": round(base, 1),
                "max_daily_mm": round(base * random.uniform(0.2, 0.5), 1),
                "max_hourly_intensity_mmh": max_intensity,
                "rainy_days": min(30, rainy_days),
                "flood_events": random.randint(0, 3) if month in [7, 8, 9] else 0,
            })
    return data


def generate_dem_grid() -> list[dict]:
    """Generate a coarse DEM elevation grid."""
    grid = []
    lat_steps = 30
    lng_steps = 30
    lat_range = DELHI_BOUNDS["max_lat"] - DELHI_BOUNDS["min_lat"]
    lng_range = DELHI_BOUNDS["max_lng"] - DELHI_BOUNDS["min_lng"]

    for i in range(lat_steps):
        for j in range(lng_steps):
            lat = DELHI_BOUNDS["min_lat"] + (i + 0.5) * lat_range / lat_steps
            lng = DELHI_BOUNDS["min_lng"] + (j + 0.5) * lng_range / lng_steps

            # Delhi ridge runs NNE-SSW; create elevation pattern
            ridge_dist = abs((lng - 77.1) * math.cos(math.radians(30)) -
                             (lat - 28.6) * math.sin(math.radians(30)))
            elevation = 215 + 40 * math.exp(-ridge_dist * 10) + random.uniform(-8, 8)
            # Yamuna floodplain lower
            if 77.20 < lng < 77.30 and 28.5 < lat < 28.75:
                elevation -= random.uniform(10, 25)

            grid.append({
                "lat": round(lat, 5),
                "lng": round(lng, 5),
                "elevation_m": round(elevation, 2),
                "slope_deg": round(random.uniform(0.2, 6.0), 2),
                "aspect_deg": round(random.uniform(0, 360), 1),
                "flow_accumulation": round(random.uniform(1, 10000), 0),
            })
    return grid


def generate_all_data(output_dir: str):
    """Generate all sample datasets and save to output directory."""
    os.makedirs(output_dir, exist_ok=True)

    print("Generating ward boundaries...")
    wards = generate_ward_boundaries()
    with open(os.path.join(output_dir, "ward_boundaries.geojson"), "w") as f:
        json.dump(wards, f)

    print(f"Generating flood hotspots...")
    hotspots = generate_flood_hotspots(wards, count=2700)
    print(f"  Generated {len(hotspots['features'])} hotspots")
    with open(os.path.join(output_dir, "flood_hotspots.geojson"), "w") as f:
        json.dump(hotspots, f)

    print("Generating drainage network...")
    drainage = generate_drainage_network(wards)
    with open(os.path.join(output_dir, "drainage_network.geojson"), "w") as f:
        json.dump(drainage, f)

    print("Generating pump stations...")
    pumps = generate_pump_stations(wards)
    with open(os.path.join(output_dir, "pump_stations.geojson"), "w") as f:
        json.dump(pumps, f)

    print("Generating rainfall data...")
    rainfall = generate_rainfall_data()
    with open(os.path.join(output_dir, "rainfall_history.json"), "w") as f:
        json.dump(rainfall, f)

    print("Generating DEM grid...")
    dem = generate_dem_grid()
    with open(os.path.join(output_dir, "dem_grid.json"), "w") as f:
        json.dump(dem, f)

    print("All sample data generated!")
    return {
        "wards": wards,
        "hotspots": hotspots,
        "drainage": drainage,
        "pumps": pumps,
        "rainfall": rainfall,
        "dem": dem,
    }


if __name__ == "__main__":
    output = os.path.join(os.path.dirname(__file__), ".", )
    generate_all_data(output)
