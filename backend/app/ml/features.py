"""
Feature engineering module for UFIE flood prediction.

Extracts and constructs feature vectors from hotspot GeoJSON data and
raw geospatial inputs (elevation, slope, drainage proximity, etc.) for
use with the flood-risk classification models in train_model.py.
"""

import numpy as np
from typing import Optional

# ── Canonical feature order used by every model in this package ──────────
FEATURE_NAMES: list[str] = [
    "elevation_m",
    "slope_deg",
    "flow_accumulation",
    "drainage_proximity_m",
    "impervious_surface_pct",
    "soil_permeability",
    "runoff_coefficient",
]


# ── Default / fallback values when a property is missing ─────────────────
_DEFAULTS: dict[str, float] = {
    "elevation_m": 50.0,
    "slope_deg": 2.0,
    "flow_accumulation": 500.0,
    "drainage_proximity_m": 200.0,
    "impervious_surface_pct": 40.0,
    "soil_permeability": 0.5,
    "runoff_coefficient": 0.55,
}


def extract_features_from_hotspots(
    hotspots_geojson: dict,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract a feature matrix **X** and target vector **y** from hotspot GeoJSON.

    Parameters
    ----------
    hotspots_geojson : dict
        A GeoJSON FeatureCollection.  Each Feature's ``properties`` dict
        should contain keys matching :pydata:`FEATURE_NAMES` plus a
        ``flood_probability`` value in [0, 1].

    Returns
    -------
    X : np.ndarray, shape (n_samples, n_features)
        Feature matrix in the canonical column order.
    y : np.ndarray, shape (n_samples,)
        Continuous flood-probability target (0-1).

    Notes
    -----
    * Missing feature values are replaced with the built-in defaults.
    * Features with ``flood_probability`` missing or ``None`` are skipped.
    """
    features_list: list[list[float]] = []
    targets: list[float] = []

    raw_features = hotspots_geojson.get("features", [])

    for feature in raw_features:
        props = feature.get("properties", {})

        # Target ──────────────────────────────────────────────────────────
        flood_prob = props.get("flood_probability")
        if flood_prob is None:
            continue
        flood_prob = float(flood_prob)

        # Feature vector ──────────────────────────────────────────────────
        row: list[float] = []
        for fname in FEATURE_NAMES:
            val = props.get(fname, _DEFAULTS[fname])
            try:
                row.append(float(val))
            except (TypeError, ValueError):
                row.append(_DEFAULTS[fname])

        features_list.append(row)
        targets.append(flood_prob)

    if not features_list:
        # Return empty arrays with the correct column count so downstream
        # code can still inspect .shape without crashing.
        return np.empty((0, len(FEATURE_NAMES))), np.empty((0,))

    X = np.array(features_list, dtype=np.float64)
    y = np.array(targets, dtype=np.float64)
    return X, y


def extract_features_for_prediction(
    lat: float,
    lng: float,
    rainfall_intensity: float,
    elevation: Optional[float] = None,
    slope: Optional[float] = None,
    dem_grid: Optional[dict] = None,
    drainage: Optional[dict] = None,
) -> np.ndarray:
    """Build a single-row feature vector for on-the-fly prediction.

    The function fills in missing values by:

    1. Using explicitly supplied *elevation* / *slope* when provided.
    2. Estimating from *dem_grid* and *drainage* context dicts when the
       explicit values are ``None`` but context is available.
    3. Falling back to rule-of-thumb estimates derived from
       ``rainfall_intensity``.

    Parameters
    ----------
    lat, lng : float
        Query coordinates (WGS-84 decimal degrees).
    rainfall_intensity : float
        Current or forecast rainfall intensity (mm/h).
    elevation : float | None
        Ground elevation in metres.  Estimated if *None*.
    slope : float | None
        Terrain slope in degrees.  Estimated if *None*.
    dem_grid : dict | None
        Optional dict with keys ``"elevations"`` (2-D list/array),
        ``"lat_min"``, ``"lat_max"``, ``"lng_min"``, ``"lng_max"``
        describing a local DEM tile that the point falls inside.
    drainage : dict | None
        Optional dict with keys ``"features"`` (list of GeoJSON line
        features representing drainage channels).

    Returns
    -------
    features : np.ndarray, shape (1, n_features)
        Feature row ready for ``model.predict()``.
    """
    # ── Elevation ────────────────────────────────────────────────────────
    if elevation is not None:
        elev = float(elevation)
    elif dem_grid is not None:
        elev = _sample_dem(lat, lng, dem_grid)
    else:
        elev = _DEFAULTS["elevation_m"]

    # ── Slope ────────────────────────────────────────────────────────────
    if slope is not None:
        slp = float(slope)
    elif dem_grid is not None:
        slp = _estimate_slope_from_dem(lat, lng, dem_grid)
    else:
        slp = _DEFAULTS["slope_deg"]

    # ── Flow accumulation (proxy via rainfall + slope) ───────────────────
    flow_acc = _estimate_flow_accumulation(rainfall_intensity, slp, elev)

    # ── Drainage proximity ───────────────────────────────────────────────
    if drainage is not None:
        drain_prox = _nearest_drainage_distance(lat, lng, drainage)
    else:
        drain_prox = _DEFAULTS["drainage_proximity_m"]

    # ── Impervious surface (heuristic: lower elevation / urban areas) ────
    impervious = _estimate_impervious(elev, drain_prox)

    # ── Soil permeability (inverse relationship with imperviousness) ─────
    soil_perm = max(0.0, min(1.0, 1.0 - impervious / 100.0))

    # ── Runoff coefficient ───────────────────────────────────────────────
    runoff_coeff = _estimate_runoff_coefficient(
        rainfall_intensity, impervious, slp
    )

    row = [elev, slp, flow_acc, drain_prox, impervious, soil_perm, runoff_coeff]
    return np.array([row], dtype=np.float64)


# ── Private helpers ──────────────────────────────────────────────────────


def _sample_dem(lat: float, lng: float, dem_grid: dict) -> float:
    """Bilinear-interpolate an elevation from a DEM grid dict."""
    try:
        elevations = np.asarray(dem_grid["elevations"], dtype=np.float64)
        rows, cols = elevations.shape

        lat_min = float(dem_grid["lat_min"])
        lat_max = float(dem_grid["lat_max"])
        lng_min = float(dem_grid["lng_min"])
        lng_max = float(dem_grid["lng_max"])

        # Normalise position inside the grid (0..1)
        y_frac = (lat - lat_min) / max(lat_max - lat_min, 1e-9)
        x_frac = (lng - lng_min) / max(lng_max - lng_min, 1e-9)

        y_frac = np.clip(y_frac, 0.0, 1.0)
        x_frac = np.clip(x_frac, 0.0, 1.0)

        r = y_frac * (rows - 1)
        c = x_frac * (cols - 1)

        r0 = int(np.floor(r))
        c0 = int(np.floor(c))
        r1 = min(r0 + 1, rows - 1)
        c1 = min(c0 + 1, cols - 1)

        dr = r - r0
        dc = c - c0

        val = (
            elevations[r0, c0] * (1 - dr) * (1 - dc)
            + elevations[r0, c1] * (1 - dr) * dc
            + elevations[r1, c0] * dr * (1 - dc)
            + elevations[r1, c1] * dr * dc
        )
        return float(val)
    except Exception:
        return _DEFAULTS["elevation_m"]


def _estimate_slope_from_dem(lat: float, lng: float, dem_grid: dict) -> float:
    """Finite-difference slope estimate from a DEM grid dict."""
    try:
        elevations = np.asarray(dem_grid["elevations"], dtype=np.float64)
        rows, cols = elevations.shape

        lat_min = float(dem_grid["lat_min"])
        lat_max = float(dem_grid["lat_max"])
        lng_min = float(dem_grid["lng_min"])
        lng_max = float(dem_grid["lng_max"])

        y_frac = np.clip(
            (lat - lat_min) / max(lat_max - lat_min, 1e-9), 0.0, 1.0
        )
        x_frac = np.clip(
            (lng - lng_min) / max(lng_max - lng_min, 1e-9), 0.0, 1.0
        )

        r = int(round(y_frac * (rows - 1)))
        c = int(round(x_frac * (cols - 1)))

        # Central differences (fall back to forward/backward at edges)
        r_lo = max(r - 1, 0)
        r_hi = min(r + 1, rows - 1)
        c_lo = max(c - 1, 0)
        c_hi = min(c + 1, cols - 1)

        dz_dy = (elevations[r_hi, c] - elevations[r_lo, c]) / max(r_hi - r_lo, 1)
        dz_dx = (elevations[r, c_hi] - elevations[r, c_lo]) / max(c_hi - c_lo, 1)

        # Cell size in metres (~111 km per degree latitude)
        cell_m = 111_000.0 * (lat_max - lat_min) / max(rows - 1, 1)
        gradient = np.sqrt((dz_dx / cell_m) ** 2 + (dz_dy / cell_m) ** 2)
        slope_deg = float(np.degrees(np.arctan(gradient)))
        return slope_deg
    except Exception:
        return _DEFAULTS["slope_deg"]


def _estimate_flow_accumulation(
    rainfall_intensity: float, slope: float, elevation: float
) -> float:
    """Rough proxy for flow accumulation based on rainfall and terrain."""
    # Higher rainfall + lower slope + lower elevation -> more accumulation
    base = rainfall_intensity * 20.0
    slope_factor = max(0.1, 1.0 - slope / 45.0)
    elev_factor = max(0.1, 1.0 - elevation / 1000.0)
    return max(0.0, base * slope_factor * elev_factor)


def _nearest_drainage_distance(
    lat: float, lng: float, drainage: dict
) -> float:
    """Approximate Euclidean distance (metres) to nearest drainage line."""
    try:
        min_dist = float("inf")
        for feat in drainage.get("features", []):
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            if geom.get("type") == "LineString":
                segments = [coords]
            elif geom.get("type") == "MultiLineString":
                segments = coords
            else:
                continue

            for seg in segments:
                for coord in seg:
                    dlng = (coord[0] - lng) * 111_000.0 * np.cos(np.radians(lat))
                    dlat = (coord[1] - lat) * 111_000.0
                    dist = np.sqrt(dlng**2 + dlat**2)
                    if dist < min_dist:
                        min_dist = dist

        return min_dist if np.isfinite(min_dist) else _DEFAULTS["drainage_proximity_m"]
    except Exception:
        return _DEFAULTS["drainage_proximity_m"]


def _estimate_impervious(elevation: float, drainage_proximity: float) -> float:
    """Heuristic impervious-surface percentage.

    Lower elevations close to drainage channels are assumed to be more
    urbanised (and therefore more impervious).
    """
    elev_component = max(0.0, 70.0 - elevation * 0.3)
    drain_component = max(0.0, 30.0 - drainage_proximity * 0.05)
    return np.clip(elev_component + drain_component, 0.0, 100.0)


def _estimate_runoff_coefficient(
    rainfall_intensity: float,
    impervious_pct: float,
    slope: float,
) -> float:
    """SCS-style runoff coefficient estimate (0-1)."""
    base = 0.3
    imperv_contrib = (impervious_pct / 100.0) * 0.4
    slope_contrib = min(slope / 45.0, 1.0) * 0.15
    rain_contrib = min(rainfall_intensity / 100.0, 1.0) * 0.15
    return float(np.clip(base + imperv_contrib + slope_contrib + rain_contrib, 0.0, 1.0))
