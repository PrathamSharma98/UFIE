"""GIS Analysis Service for the Urban Flood Intelligence Engine.

Pure-function module that operates on in-memory GeoJSON / dict data
loaded from ``InMemoryDataStore``.  Every public function accepts raw
data structures and returns results -- no database or filesystem
side-effects.

Dependencies:
    numpy, scikit-learn (sklearn)
"""

from __future__ import annotations

import copy
import logging
import math
from collections import defaultdict
from typing import Any, Optional

import numpy as np
from sklearn.cluster import DBSCAN, KMeans

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# D8 direction offsets: (row_delta, col_delta) for each of the 8 neighbours.
# Ordered clockwise from north.
_D8_OFFSETS: list[tuple[int, int]] = [
    (-1, 0),   # N
    (-1, 1),   # NE
    (0, 1),    # E
    (1, 1),    # SE
    (1, 0),    # S
    (1, -1),   # SW
    (0, -1),   # W
    (-1, -1),  # NW
]

# Distance multiplier for diagonal vs cardinal neighbours.
_D8_DISTANCES: list[float] = [
    1.0,
    math.sqrt(2),
    1.0,
    math.sqrt(2),
    1.0,
    math.sqrt(2),
    1.0,
    math.sqrt(2),
]


def _build_grid_matrix(
    dem_grid: list[dict],
) -> tuple[np.ndarray, dict[tuple[int, int], int], int, int]:
    """Convert a flat list of DEM cells into a 2-D numpy elevation matrix.

    Each cell dict is expected to carry at minimum:
        ``row``, ``col``, ``elevation`` (or ``elevation_m``).

    Returns
    -------
    elev : np.ndarray of shape (nrows, ncols)
        Elevation matrix (NaN where no data).
    idx_map : dict mapping (row, col) -> index in the original *dem_grid* list.
    nrows, ncols : grid dimensions.
    """
    if not dem_grid:
        return np.empty((0, 0)), {}, 0, 0

    rows = []
    cols = []
    for cell in dem_grid:
        rows.append(int(cell.get("row", 0)))
        cols.append(int(cell.get("col", 0)))

    min_row, max_row = min(rows), max(rows)
    min_col, max_col = min(cols), max(cols)
    nrows = max_row - min_row + 1
    ncols = max_col - min_col + 1

    elev = np.full((nrows, ncols), np.nan)
    idx_map: dict[tuple[int, int], int] = {}

    for i, cell in enumerate(dem_grid):
        r = int(cell.get("row", 0)) - min_row
        c = int(cell.get("col", 0)) - min_col
        e = cell.get("elevation", cell.get("elevation_m", 0.0))
        elev[r, c] = float(e)
        idx_map[(r, c)] = i

    return elev, idx_map, nrows, ncols


def _get_steepest_descent(
    elev: np.ndarray, r: int, c: int, nrows: int, ncols: int
) -> Optional[tuple[int, int]]:
    """Return the (row, col) of the neighbour with the steepest downhill
    gradient from cell (r, c), or ``None`` if the cell is a local minimum."""
    max_drop = 0.0
    target: Optional[tuple[int, int]] = None

    for (dr, dc), dist in zip(_D8_OFFSETS, _D8_DISTANCES):
        nr, nc = r + dr, c + dc
        if 0 <= nr < nrows and 0 <= nc < ncols and not np.isnan(elev[nr, nc]):
            drop = (elev[r, c] - elev[nr, nc]) / dist
            if drop > max_drop:
                max_drop = drop
                target = (nr, nc)

    return target


# ---------------------------------------------------------------------------
# 1. Flow accumulation (D8 approximation)
# ---------------------------------------------------------------------------

def calculate_flow_accumulation(dem_grid: list[dict]) -> list[dict]:
    """Compute flow accumulation on a DEM grid using the D8 algorithm.

    Each cell in the returned list is a **copy** of the original dict with an
    added ``flow_accumulation`` key representing the count of upstream cells
    that ultimately drain through it.

    Parameters
    ----------
    dem_grid : list[dict]
        Flat list of grid cells.  Required keys per cell:
        ``row``, ``col``, ``elevation`` (or ``elevation_m``).

    Returns
    -------
    list[dict]
        Grid cells augmented with ``flow_accumulation`` values.
    """
    if not dem_grid:
        return []

    elev, idx_map, nrows, ncols = _build_grid_matrix(dem_grid)
    acc = np.ones((nrows, ncols), dtype=np.float64)  # each cell counts itself

    # Build a sorted list of cells from highest to lowest elevation so that
    # when we process a cell all cells that drain *into* it have already
    # propagated their accumulation.
    cells_sorted: list[tuple[float, int, int]] = []
    for r in range(nrows):
        for c in range(ncols):
            if not np.isnan(elev[r, c]):
                cells_sorted.append((elev[r, c], r, c))

    # Sort descending by elevation (highest first).
    cells_sorted.sort(key=lambda x: -x[0])

    for _e, r, c in cells_sorted:
        target = _get_steepest_descent(elev, r, c, nrows, ncols)
        if target is not None:
            acc[target[0], target[1]] += acc[r, c]

    # Merge results back into cell dicts.
    result: list[dict] = []
    for cell in dem_grid:
        out = dict(cell)  # shallow copy
        r = int(cell.get("row", 0)) - (min(int(c.get("row", 0)) for c in dem_grid))
        c_col = int(cell.get("col", 0)) - (min(int(c.get("col", 0)) for c in dem_grid))
        out["flow_accumulation"] = float(acc[r, c_col])
        result.append(out)

    return result


# ---------------------------------------------------------------------------
# 2. Slope calculation
# ---------------------------------------------------------------------------

def calculate_slope(
    dem_grid: list[dict],
    cell_size_m: float = 111.0,
) -> list[dict]:
    """Calculate terrain slope (in degrees) for every cell using a 3x3
    finite-difference approximation (Horn's method).

    Parameters
    ----------
    dem_grid : list[dict]
        Flat list of grid cells with ``row``, ``col``, ``elevation``
        (or ``elevation_m``) keys.
    cell_size_m : float
        Approximate real-world size of one grid cell in metres.  Defaults to
        111 m (roughly 0.001 degree at the equator).

    Returns
    -------
    list[dict]
        Grid cells augmented with ``slope_deg`` (degrees) and ``slope_pct``
        (percent rise) values.
    """
    if not dem_grid:
        return []

    elev, idx_map, nrows, ncols = _build_grid_matrix(dem_grid)

    # Pad the elevation matrix with NaN so border pixels can be computed.
    padded = np.pad(elev, pad_width=1, mode="edge")

    # Horn's method finite-difference kernels.
    dz_dx = np.full((nrows, ncols), 0.0)
    dz_dy = np.full((nrows, ncols), 0.0)

    for r in range(nrows):
        for c in range(ncols):
            if np.isnan(elev[r, c]):
                continue
            # Indices into the padded array (offset by 1).
            pr, pc = r + 1, c + 1
            a = padded[pr - 1, pc - 1]
            b = padded[pr - 1, pc]
            cc_ = padded[pr - 1, pc + 1]
            d = padded[pr, pc - 1]
            f = padded[pr, pc + 1]
            g = padded[pr + 1, pc - 1]
            h = padded[pr + 1, pc]
            ii = padded[pr + 1, pc + 1]

            dz_dx[r, c] = ((cc_ + 2 * f + ii) - (a + 2 * d + g)) / (8 * cell_size_m)
            dz_dy[r, c] = ((g + 2 * h + ii) - (a + 2 * b + cc_)) / (8 * cell_size_m)

    slope_rad = np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))
    slope_deg = np.degrees(slope_rad)
    slope_pct = np.tan(slope_rad) * 100.0

    # Compute min row/col once for index mapping.
    min_row = min(int(cell.get("row", 0)) for cell in dem_grid)
    min_col = min(int(cell.get("col", 0)) for cell in dem_grid)

    result: list[dict] = []
    for cell in dem_grid:
        out = dict(cell)
        r = int(cell.get("row", 0)) - min_row
        c = int(cell.get("col", 0)) - min_col
        out["slope_deg"] = round(float(slope_deg[r, c]), 4)
        out["slope_pct"] = round(float(slope_pct[r, c]), 4)
        result.append(out)

    return result


# ---------------------------------------------------------------------------
# 3. Watershed identification
# ---------------------------------------------------------------------------

def identify_watersheds(
    dem_grid: list[dict],
    hotspots: dict,
) -> list[dict]:
    """Assign hotspots to simple watershed regions derived from the DEM.

    The algorithm:
    1. Trace flow from every DEM cell to its local minimum (pour point)
       using the D8 steepest-descent rule.
    2. Each unique pour point defines a watershed basin.
    3. For each hotspot, find the nearest DEM cell and inherit its basin id.

    Parameters
    ----------
    dem_grid : list[dict]
        DEM grid cells with ``row``, ``col``, ``elevation`` (or
        ``elevation_m``), and optionally ``lat``/``lng``.
    hotspots : dict
        GeoJSON FeatureCollection of flood hotspots.

    Returns
    -------
    list[dict]
        One dict per hotspot with keys ``hotspot_id``, ``lat``, ``lng``,
        ``watershed_id``, ``pour_point_row``, ``pour_point_col``,
        ``pour_point_elevation``.
    """
    if not dem_grid:
        return []

    features = hotspots.get("features", [])
    if not features:
        return []

    elev, idx_map, nrows, ncols = _build_grid_matrix(dem_grid)

    # -- Step 1: trace each cell to its pour point --------------------------
    pour_point_cache: dict[tuple[int, int], tuple[int, int]] = {}

    def _trace_to_pour(r: int, c: int) -> tuple[int, int]:
        """Follow steepest descent until a local minimum is reached."""
        if (r, c) in pour_point_cache:
            return pour_point_cache[(r, c)]

        visited: list[tuple[int, int]] = []
        cr, cc = r, c
        while True:
            if (cr, cc) in pour_point_cache:
                pp = pour_point_cache[(cr, cc)]
                for v in visited:
                    pour_point_cache[v] = pp
                return pp
            visited.append((cr, cc))
            nxt = _get_steepest_descent(elev, cr, cc, nrows, ncols)
            if nxt is None:
                # Local minimum found.
                for v in visited:
                    pour_point_cache[v] = (cr, cc)
                return (cr, cc)
            cr, cc = nxt

    # Assign a numeric watershed_id to each unique pour point.
    pour_to_id: dict[tuple[int, int], int] = {}
    basin_map = np.full((nrows, ncols), -1, dtype=int)

    for r in range(nrows):
        for c in range(ncols):
            if np.isnan(elev[r, c]):
                continue
            pp = _trace_to_pour(r, c)
            if pp not in pour_to_id:
                pour_to_id[pp] = len(pour_to_id) + 1
            basin_map[r, c] = pour_to_id[pp]

    # -- Step 2: build spatial lookup for DEM cells -------------------------
    min_row = min(int(cell.get("row", 0)) for cell in dem_grid)
    min_col = min(int(cell.get("col", 0)) for cell in dem_grid)

    # Build arrays of lat/lng for each grid cell for nearest-neighbour lookup.
    cell_coords: list[tuple[float, float, int, int]] = []
    for cell in dem_grid:
        lat = float(cell.get("lat", 0.0))
        lng = float(cell.get("lng", 0.0))
        r = int(cell.get("row", 0)) - min_row
        c = int(cell.get("col", 0)) - min_col
        cell_coords.append((lat, lng, r, c))

    cell_lats = np.array([x[0] for x in cell_coords])
    cell_lngs = np.array([x[1] for x in cell_coords])

    # -- Step 3: assign each hotspot to the nearest DEM cell ----------------
    results: list[dict] = []
    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        h_lng, h_lat = float(coords[0]), float(coords[1])

        # Nearest cell by Euclidean distance on lat/lng (sufficient for
        # city-scale grids).
        dists = np.sqrt((cell_lats - h_lat) ** 2 + (cell_lngs - h_lng) ** 2)
        nearest_idx = int(np.argmin(dists))
        _, _, nr, nc = cell_coords[nearest_idx]

        wid = int(basin_map[nr, nc]) if basin_map[nr, nc] >= 0 else 0
        pp = None
        for pp_coord, pp_id in pour_to_id.items():
            if pp_id == wid:
                pp = pp_coord
                break

        results.append(
            {
                "hotspot_id": props.get("hotspot_id", ""),
                "lat": h_lat,
                "lng": h_lng,
                "watershed_id": wid,
                "pour_point_row": pp[0] + min_row if pp else None,
                "pour_point_col": pp[1] + min_col if pp else None,
                "pour_point_elevation": (
                    float(elev[pp[0], pp[1]]) if pp and not np.isnan(elev[pp[0], pp[1]]) else None
                ),
            }
        )

    return results


# ---------------------------------------------------------------------------
# 4. Hotspot spatial clustering
# ---------------------------------------------------------------------------

def cluster_hotspots(
    hotspots: dict,
    method: str = "dbscan",
    *,
    eps: float = 0.005,
    min_samples: int = 3,
    n_clusters: int = 5,
) -> dict:
    """Apply spatial clustering to hotspot coordinates.

    Parameters
    ----------
    hotspots : dict
        GeoJSON FeatureCollection of flood hotspots.
    method : str
        Clustering algorithm -- ``"dbscan"`` (default) or ``"kmeans"``.
    eps : float
        DBSCAN neighbourhood radius in decimal degrees (default ~500 m).
    min_samples : int
        DBSCAN minimum neighbours to form a core point.
    n_clusters : int
        Number of clusters for KMeans.

    Returns
    -------
    dict
        A *copy* of the input FeatureCollection with ``cluster_id`` added to
        each feature's ``properties``.  For DBSCAN, noise points receive
        ``cluster_id = -1``.  A top-level ``"cluster_summary"`` key is also
        added with per-cluster statistics.
    """
    features = hotspots.get("features", [])
    if not features:
        return copy.deepcopy(hotspots)

    coords = np.array(
        [
            [
                feat["geometry"]["coordinates"][1],  # lat
                feat["geometry"]["coordinates"][0],  # lng
            ]
            for feat in features
        ]
    )

    method_lower = method.lower().strip()
    if method_lower == "kmeans":
        effective_k = min(n_clusters, len(coords))
        model = KMeans(n_clusters=effective_k, random_state=42, n_init="auto")
        labels = model.fit_predict(coords)
    else:
        # Default to DBSCAN.
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(coords)

    labels = labels.tolist()

    # Build output FeatureCollection.
    out_features: list[dict] = []
    for feat, cid in zip(features, labels):
        new_feat = copy.deepcopy(feat)
        new_feat.setdefault("properties", {})["cluster_id"] = int(cid)
        out_features.append(new_feat)

    # Per-cluster summary.
    cluster_summary: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "avg_lat": 0.0, "avg_lng": 0.0, "severities": defaultdict(int)}
    )
    for feat, cid in zip(out_features, labels):
        props = feat.get("properties", {})
        cs = cluster_summary[int(cid)]
        cs["count"] += 1
        geom = feat.get("geometry", {})
        c = geom.get("coordinates", [0.0, 0.0])
        cs["avg_lat"] += float(c[1])
        cs["avg_lng"] += float(c[0])
        sev = props.get("severity", "unknown")
        cs["severities"][sev] += 1

    # Compute averages.
    serialisable_summary: dict[str, Any] = {}
    for cid, cs in cluster_summary.items():
        if cs["count"] > 0:
            cs["avg_lat"] /= cs["count"]
            cs["avg_lng"] /= cs["count"]
        serialisable_summary[str(cid)] = {
            "count": cs["count"],
            "avg_lat": round(cs["avg_lat"], 6),
            "avg_lng": round(cs["avg_lng"], 6),
            "severities": dict(cs["severities"]),
        }

    result = copy.deepcopy(hotspots)
    result["features"] = out_features
    result["cluster_summary"] = serialisable_summary
    result["clustering_method"] = method_lower
    return result


# ---------------------------------------------------------------------------
# 5. Runoff estimation (SCS Curve Number method)
# ---------------------------------------------------------------------------

def calculate_runoff(
    rainfall_mm: float,
    area_km2: float,
    impervious_pct: float,
    soil_permeability: float,
) -> dict:
    """Estimate surface runoff using the SCS Curve Number method.

    The Curve Number (CN) is derived from the ``impervious_pct`` and
    ``soil_permeability`` parameters so that:
        CN = 98 * (impervious_pct / 100) + CN_pervious * (1 - impervious_pct / 100)
    where CN_pervious is mapped from soil_permeability (0 -> CN 94, 1 -> CN 40).

    Parameters
    ----------
    rainfall_mm : float
        Total rainfall depth in millimetres.
    area_km2 : float
        Catchment / ward area in square kilometres.
    impervious_pct : float
        Percentage of impervious surface cover (0-100).
    soil_permeability : float
        Soil permeability index (0 = impermeable, 1 = fully permeable).

    Returns
    -------
    dict with keys:
        ``curve_number``, ``initial_abstraction_mm``,
        ``max_retention_mm``, ``runoff_mm``, ``runoff_volume_m3``,
        ``peak_discharge_m3s`` (estimated via the SCS triangular
        hydrograph approximation for a 1-hour storm).
    """
    # Clamp inputs.
    rainfall_mm = max(rainfall_mm, 0.0)
    area_km2 = max(area_km2, 0.0)
    impervious_pct = np.clip(impervious_pct, 0.0, 100.0)
    soil_permeability = np.clip(soil_permeability, 0.0, 1.0)

    # -- Derive Curve Number ------------------------------------------------
    # Fully impervious surface: CN ~ 98.
    cn_impervious = 98.0
    # Pervious CN: linearly mapped from soil_permeability.
    #   permeability=0 -> CN 94  (clay / very poor infiltration)
    #   permeability=1 -> CN 40  (sandy / excellent infiltration)
    cn_pervious = 94.0 - 54.0 * float(soil_permeability)
    frac_imperv = float(impervious_pct) / 100.0
    cn = cn_impervious * frac_imperv + cn_pervious * (1.0 - frac_imperv)

    # Ensure CN stays within physical bounds.
    cn = float(np.clip(cn, 30.0, 100.0))

    # -- SCS equations ------------------------------------------------------
    # Maximum potential retention S (mm).
    if cn >= 100.0:
        s_mm = 0.0
    else:
        s_mm = 25400.0 / cn - 254.0

    # Initial abstraction Ia (mm) -- typically 0.2 * S.
    ia_mm = 0.2 * s_mm

    # Runoff depth Q (mm).
    if rainfall_mm <= ia_mm:
        q_mm = 0.0
    else:
        q_mm = (rainfall_mm - ia_mm) ** 2 / (rainfall_mm - ia_mm + s_mm)

    # Runoff volume (m3).
    # 1 mm over 1 km2 = 1000 m3.
    runoff_vol_m3 = q_mm * area_km2 * 1000.0

    # Peak discharge estimate using the SCS triangular unit hydrograph.
    # Qp = 0.208 * A * Q / Tp  where A in km2, Q in mm, Tp in hours.
    # Assume time-to-peak Tp ~ 0.6 * storm duration.  Default 1-h storm.
    storm_duration_h = 1.0
    tp_h = 0.6 * storm_duration_h
    if tp_h > 0 and q_mm > 0:
        peak_discharge = 0.208 * area_km2 * q_mm / tp_h
    else:
        peak_discharge = 0.0

    return {
        "curve_number": round(cn, 2),
        "initial_abstraction_mm": round(ia_mm, 2),
        "max_retention_mm": round(s_mm, 2),
        "runoff_mm": round(q_mm, 2),
        "runoff_volume_m3": round(runoff_vol_m3, 2),
        "peak_discharge_m3s": round(peak_discharge, 4),
    }


# ---------------------------------------------------------------------------
# 6. Drainage capacity analysis
# ---------------------------------------------------------------------------

def analyze_drainage_capacity(
    drainage_data: dict,
    rainfall_intensity: float,
) -> list[dict]:
    """Evaluate drainage segment utilisation against a given rainfall intensity.

    For each segment the *required capacity* is estimated from the rainfall
    intensity and the segment's catchment contribution (approximated from its
    length and a default catchment width).

    Parameters
    ----------
    drainage_data : dict
        GeoJSON FeatureCollection of drainage segments.  Each feature's
        ``properties`` should include ``segment_id``, ``capacity_m3s``,
        ``width_m``, ``depth_m``, ``length_m``, ``condition``, and
        optionally ``ward_id``.
    rainfall_intensity : float
        Rainfall intensity in mm/h.

    Returns
    -------
    list[dict]
        Per-segment analysis with keys: ``segment_id``, ``ward_id``,
        ``capacity_m3s``, ``required_flow_m3s``, ``utilization_pct``,
        ``is_over_capacity``, ``surplus_deficit_m3s``, ``condition``,
        ``effective_capacity_m3s``.
    """
    features = drainage_data.get("features", [])
    if not features:
        return []

    # Condition degradation factors.
    condition_factors: dict[str, float] = {
        "good": 1.0,
        "fair": 0.80,
        "poor": 0.55,
        "blocked": 0.15,
    }

    results: list[dict] = []
    for feat in features:
        props = feat.get("properties", {})
        segment_id = props.get("segment_id", "unknown")
        ward_id = props.get("ward_id", "")
        capacity = float(props.get("capacity_m3s", 0.0))
        width = float(props.get("width_m", 1.0))
        length = float(props.get("length_m", 100.0))
        condition = str(props.get("condition", "good")).lower()

        # Effective capacity after condition degradation.
        cond_factor = condition_factors.get(condition, 0.7)
        effective_capacity = capacity * cond_factor

        # Estimate required flow: assume each segment drains a rectangular
        # catchment of length x default_width (50 m).  Convert rainfall
        # intensity from mm/h to m3/s.
        # catchment_area_m2 = length * catchment_width
        # required_flow = (rainfall_intensity / 1000 / 3600) * catchment_area_m2
        default_catchment_width_m = 50.0
        catchment_area_m2 = length * default_catchment_width_m
        required_flow = (rainfall_intensity / 1000.0 / 3600.0) * catchment_area_m2

        # Apply a runoff coefficient (~0.75 for urban mixed surfaces).
        runoff_coeff = 0.75
        required_flow *= runoff_coeff

        utilization_pct = (
            (required_flow / effective_capacity * 100.0)
            if effective_capacity > 0
            else float("inf")
        )
        is_over_capacity = required_flow > effective_capacity
        surplus_deficit = effective_capacity - required_flow

        results.append(
            {
                "segment_id": segment_id,
                "ward_id": ward_id,
                "capacity_m3s": round(capacity, 4),
                "effective_capacity_m3s": round(effective_capacity, 4),
                "condition": condition,
                "condition_factor": cond_factor,
                "required_flow_m3s": round(required_flow, 6),
                "utilization_pct": round(min(utilization_pct, 999.99), 2),
                "is_over_capacity": is_over_capacity,
                "surplus_deficit_m3s": round(surplus_deficit, 4),
            }
        )

    # Sort by utilization descending so the most stressed segments come first.
    results.sort(key=lambda x: x["utilization_pct"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 7. Hotspot summary statistics
# ---------------------------------------------------------------------------

def get_hotspot_summary(hotspots: dict) -> dict:
    """Compute aggregate summary statistics for flood hotspots.

    Parameters
    ----------
    hotspots : dict
        GeoJSON FeatureCollection of flood hotspots.

    Returns
    -------
    dict with keys:
        ``total_count``, ``by_severity``, ``by_ward``,
        ``avg_flood_probability``, ``max_flood_probability``,
        ``min_flood_probability``,
        ``total_affected_population``,
        ``total_estimated_damage_inr_lakhs``,
        ``avg_elevation_m``, ``avg_slope_deg``,
        ``avg_impervious_surface_pct``,
        ``top_wards`` (top 5 wards by hotspot count).
    """
    features = hotspots.get("features", [])
    total = len(features)

    if total == 0:
        return {
            "total_count": 0,
            "by_severity": {},
            "by_ward": {},
            "avg_flood_probability": 0.0,
            "max_flood_probability": 0.0,
            "min_flood_probability": 0.0,
            "total_affected_population": 0,
            "total_estimated_damage_inr_lakhs": 0.0,
            "avg_elevation_m": 0.0,
            "avg_slope_deg": 0.0,
            "avg_impervious_surface_pct": 0.0,
            "top_wards": [],
        }

    by_severity: dict[str, int] = defaultdict(int)
    by_ward: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "ward_name": ""}
    )
    probabilities: list[float] = []
    populations: list[int] = []
    damages: list[float] = []
    elevations: list[float] = []
    slopes: list[float] = []
    imperv_pcts: list[float] = []

    for feat in features:
        props = feat.get("properties", {})

        sev = str(props.get("severity", "unknown")).lower()
        by_severity[sev] += 1

        wid = str(props.get("ward_id", "unknown"))
        by_ward[wid]["count"] += 1
        by_ward[wid]["ward_name"] = props.get("ward_name", "")

        prob = props.get("flood_probability")
        if prob is not None:
            probabilities.append(float(prob))

        pop = props.get("affected_population")
        if pop is not None:
            populations.append(int(pop))

        dmg = props.get("estimated_damage_inr_lakhs")
        if dmg is not None:
            damages.append(float(dmg))

        elev = props.get("elevation_m")
        if elev is not None:
            elevations.append(float(elev))

        sl = props.get("slope_deg")
        if sl is not None:
            slopes.append(float(sl))

        imp = props.get("impervious_surface_pct")
        if imp is not None:
            imperv_pcts.append(float(imp))

    # Top wards by hotspot count.
    ward_list = [
        {"ward_id": wid, "ward_name": info["ward_name"], "count": info["count"]}
        for wid, info in by_ward.items()
    ]
    ward_list.sort(key=lambda w: w["count"], reverse=True)
    top_wards = ward_list[:5]

    return {
        "total_count": total,
        "by_severity": dict(by_severity),
        "by_ward": {
            wid: {"count": info["count"], "ward_name": info["ward_name"]}
            for wid, info in by_ward.items()
        },
        "avg_flood_probability": round(float(np.mean(probabilities)), 4) if probabilities else 0.0,
        "max_flood_probability": round(float(np.max(probabilities)), 4) if probabilities else 0.0,
        "min_flood_probability": round(float(np.min(probabilities)), 4) if probabilities else 0.0,
        "total_affected_population": sum(populations),
        "total_estimated_damage_inr_lakhs": round(sum(damages), 2),
        "avg_elevation_m": round(float(np.mean(elevations)), 2) if elevations else 0.0,
        "avg_slope_deg": round(float(np.mean(slopes)), 2) if slopes else 0.0,
        "avg_impervious_surface_pct": round(float(np.mean(imperv_pcts)), 2) if imperv_pcts else 0.0,
        "top_wards": top_wards,
    }


# ---------------------------------------------------------------------------
# 8. Hotspot filtering
# ---------------------------------------------------------------------------

def filter_hotspots(
    hotspots: dict,
    ward_id: int | str | None = None,
    min_probability: float | None = None,
    severity: str | None = None,
) -> dict:
    """Filter a hotspot GeoJSON FeatureCollection by one or more criteria.

    All supplied criteria are combined with logical AND.

    Parameters
    ----------
    hotspots : dict
        GeoJSON FeatureCollection of flood hotspots.
    ward_id : int | str | None
        Keep only hotspots whose ``ward_id`` property matches (compared as
        strings).
    min_probability : float | None
        Keep only hotspots with ``flood_probability >= min_probability``.
    severity : str | None
        Keep only hotspots whose ``severity`` matches (case-insensitive).

    Returns
    -------
    dict
        A new GeoJSON FeatureCollection containing only the matching features
        and a ``"filter_applied"`` metadata key.
    """
    features = hotspots.get("features", [])
    filtered: list[dict] = []

    for feat in features:
        props = feat.get("properties", {})

        if ward_id is not None:
            feat_ward = str(props.get("ward_id", ""))
            if feat_ward != str(ward_id):
                continue

        if min_probability is not None:
            feat_prob = props.get("flood_probability")
            if feat_prob is None or float(feat_prob) < min_probability:
                continue

        if severity is not None:
            feat_sev = str(props.get("severity", "")).lower()
            if feat_sev != severity.lower():
                continue

        filtered.append(feat)

    filters_applied: dict[str, Any] = {}
    if ward_id is not None:
        filters_applied["ward_id"] = str(ward_id)
    if min_probability is not None:
        filters_applied["min_probability"] = min_probability
    if severity is not None:
        filters_applied["severity"] = severity

    return {
        "type": "FeatureCollection",
        "features": filtered,
        "filter_applied": filters_applied,
        "total_matched": len(filtered),
        "total_original": len(features),
    }
