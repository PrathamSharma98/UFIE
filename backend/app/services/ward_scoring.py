"""Ward-level Pre-Monsoon Readiness Score calculator.

Production module that computes a composite readiness score (0-100) for each
administrative ward based on five weighted components:

    1. Drainage Capacity Index            (0-25)
    2. Emergency Infrastructure Coverage  (0-20)
    3. Flood Hotspot Density (inverse)    (0-25)
    4. Rainfall Vulnerability             (0-15)
    5. Pump Station Availability          (0-15)

All functions are **pure** -- they accept raw GeoJSON / dict data and return
results without side-effects.  No imports from ``app``.

Dependencies:
    numpy
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum component weights (must sum to 100).
_MAX_DRAINAGE: float = 25.0
_MAX_EMERGENCY: float = 20.0
_MAX_HOTSPOT: float = 25.0
_MAX_RAINFALL: float = 15.0
_MAX_PUMP: float = 15.0

# Readiness category thresholds.
_CATEGORY_THRESHOLDS: list[tuple[float, str]] = [
    (30.0, "Critical Risk"),
    (60.0, "Moderate Risk"),
    (80.0, "Prepared"),
    (100.0, "Resilient"),
]

# Drainage condition degradation factors -- mirrors gis_analysis.py.
_CONDITION_FACTORS: dict[str, float] = {
    "good": 1.0,
    "fair": 0.80,
    "poor": 0.55,
    "critical": 0.30,
    "blocked": 0.15,
}

# Reference benchmarks used for normalisation.
_REF_DRAINAGE_CAPACITY_M3S: float = 50.0   # ideal capacity per ward
_REF_SHELTER_PER_100K: float = 5.0         # ideal shelters per 100k people
_REF_HOTSPOT_DENSITY: float = 30.0         # hotspots/km2 ceiling
_REF_ELEVATION_LOW: float = 195.0          # lowest expected elevation (m)
_REF_ELEVATION_HIGH: float = 260.0         # highest expected elevation (m)
_REF_PUMPS_PER_WARD: float = 6.0           # ideal operational pumps per ward


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify(score: float) -> str:
    """Map a readiness score (0-100) to its category label."""
    for threshold, label in _CATEGORY_THRESHOLDS:
        if score <= threshold:
            return label
    return _CATEGORY_THRESHOLDS[-1][1]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* between *lo* and *hi*."""
    return float(np.clip(value, lo, hi))


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns *default* when the denominator is zero."""
    if denominator == 0.0:
        return default
    return numerator / denominator


def _group_features_by_ward(geojson: dict, ward_key: str = "ward_id") -> dict[Any, list[dict]]:
    """Group GeoJSON features by their ward identifier property.

    Returns a ``defaultdict(list)`` mapping ward_id -> list of feature
    ``properties`` dicts.
    """
    grouped: dict[Any, list[dict]] = defaultdict(list)
    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        wid = props.get(ward_key)
        if wid is not None:
            grouped[str(wid)].append(props)
    return grouped


# ---------------------------------------------------------------------------
# Component scorers (each returns a float in [0, max_weight])
# ---------------------------------------------------------------------------

def _score_drainage_capacity(
    ward_props: dict,
    drain_segments: list[dict],
) -> float:
    """Drainage Capacity Index (0-25).

    Factors considered:
    * Total drainage capacity (m3/s) relative to a reference benchmark.
    * Average condition factor across all segments in the ward.
    * Average utilisation -- lower utilisation is better (more headroom).
    """
    # Ward-level capacity from ward properties (fallback).
    ward_capacity = float(ward_props.get("drainage_capacity_m3s", 0.0))

    if drain_segments:
        # Aggregate from individual segments.
        capacities = np.array(
            [float(s.get("capacity_m3s", 0.0)) for s in drain_segments]
        )
        conditions = np.array(
            [
                _CONDITION_FACTORS.get(
                    str(s.get("condition", "good")).lower(), 0.7
                )
                for s in drain_segments
            ]
        )
        utilisations = np.array(
            [float(s.get("utilization_pct", 50.0)) for s in drain_segments]
        )

        total_capacity = float(np.sum(capacities))
        avg_condition = float(np.mean(conditions))
        avg_utilisation_frac = float(np.mean(utilisations)) / 100.0
    else:
        total_capacity = ward_capacity
        avg_condition = 0.5
        avg_utilisation_frac = 0.7  # pessimistic default

    # Sub-scores, each in [0, 1].
    capacity_ratio = _clamp(total_capacity / _REF_DRAINAGE_CAPACITY_M3S)
    condition_score = _clamp(avg_condition)
    utilisation_headroom = _clamp(1.0 - avg_utilisation_frac)

    # Weighted combination within this component.
    raw = 0.45 * capacity_ratio + 0.30 * condition_score + 0.25 * utilisation_headroom

    return round(raw * _MAX_DRAINAGE, 2)


def _score_emergency_infrastructure(
    ward_props: dict,
) -> float:
    """Emergency Infrastructure Coverage (0-20).

    Based on emergency shelter count relative to the ward population.
    """
    shelters = int(ward_props.get("emergency_shelters", 0))
    population = max(int(ward_props.get("population", 1)), 1)

    shelters_per_100k = shelters / (population / 100_000)
    coverage_ratio = _clamp(shelters_per_100k / _REF_SHELTER_PER_100K)

    # Bonus for having at least one shelter.
    has_any = 1.0 if shelters > 0 else 0.0

    raw = 0.75 * coverage_ratio + 0.25 * has_any

    return round(raw * _MAX_EMERGENCY, 2)


def _score_hotspot_density(
    ward_props: dict,
    hotspot_list: list[dict],
) -> float:
    """Flood Hotspot Density score (0-25).  Inverse -- fewer hotspots is better.

    Also factors in the average severity of existing hotspots.
    """
    area_km2 = max(float(ward_props.get("area_km2", 1.0)), 0.01)
    count = len(hotspot_list)
    density = count / area_km2

    # Inverse density score: 0 hotspots/km2 -> 1.0, >= REF ceiling -> 0.0.
    density_score = _clamp(1.0 - density / _REF_HOTSPOT_DENSITY)

    # Severity penalty: higher proportion of critical/high hotspots lowers score.
    if count > 0:
        severity_weights = {"critical": 1.0, "high": 0.7, "moderate": 0.3, "low": 0.0}
        severities = np.array(
            [
                severity_weights.get(str(h.get("severity", "low")).lower(), 0.3)
                for h in hotspot_list
            ]
        )
        avg_severity = float(np.mean(severities))
    else:
        avg_severity = 0.0

    severity_bonus = _clamp(1.0 - avg_severity)

    raw = 0.65 * density_score + 0.35 * severity_bonus

    return round(raw * _MAX_HOTSPOT, 2)


def _score_rainfall_vulnerability(
    ward_props: dict,
) -> float:
    """Rainfall Vulnerability score (0-15).

    Lower vulnerability yields a *higher* readiness score.

    Factors:
    * Elevation -- higher is better (less ponding).
    * Impervious surface % -- lower is better.
    * Soil permeability -- higher is better.
    """
    elevation = float(ward_props.get("avg_elevation_m", 215.0))
    impervious_pct = float(ward_props.get("impervious_surface_pct", 60.0))
    soil_perm = float(ward_props.get("soil_permeability", 0.4))

    elev_norm = _clamp(
        (elevation - _REF_ELEVATION_LOW) / (_REF_ELEVATION_HIGH - _REF_ELEVATION_LOW)
    )
    imperv_score = _clamp(1.0 - impervious_pct / 100.0)
    perm_score = _clamp(soil_perm)

    # Green cover provides additional mitigation.
    green_pct = float(ward_props.get("green_cover_pct", 10.0))
    green_score = _clamp(green_pct / 40.0)  # 40% green cover = full benefit

    raw = (
        0.30 * elev_norm
        + 0.30 * imperv_score
        + 0.25 * perm_score
        + 0.15 * green_score
    )

    return round(raw * _MAX_RAINFALL, 2)


def _score_pump_availability(
    ward_props: dict,
    pump_list: list[dict],
) -> float:
    """Pump Station Availability score (0-15).

    Considers:
    * Number of operational pumps.
    * Proportion with power backup.
    * Total pumping capacity (m3/h).
    """
    if not pump_list:
        # Fall back to ward-level count (no detail available).
        count = int(ward_props.get("pump_stations", 0))
        if count == 0:
            return 0.0
        # Assume a pessimistic 60% operational without detailed data.
        operational_ratio = 0.6
        backup_ratio = 0.4
        count_score = _clamp(count / _REF_PUMPS_PER_WARD)
        raw = 0.50 * count_score + 0.30 * operational_ratio + 0.20 * backup_ratio
        return round(raw * _MAX_PUMP, 2)

    total = len(pump_list)
    operational = [
        p for p in pump_list
        if str(p.get("status", "")).lower() == "operational"
    ]
    num_operational = len(operational)

    operational_ratio = _clamp(_safe_div(num_operational, total))

    # Power backup ratio among operational pumps.
    if num_operational > 0:
        backup_count = sum(1 for p in operational if p.get("power_backup", False))
        backup_ratio = _clamp(backup_count / num_operational)
    else:
        backup_ratio = 0.0

    # Count-based adequacy.
    count_score = _clamp(num_operational / _REF_PUMPS_PER_WARD)

    # Capacity adequacy (optional -- not all datasets have this).
    capacities = [float(p.get("capacity_m3h", 0.0)) for p in operational]
    total_capacity = sum(capacities) if capacities else 0.0
    # Reference: 4000 m3/h total ideal per ward.
    capacity_score = _clamp(total_capacity / 4000.0)

    raw = (
        0.30 * count_score
        + 0.30 * operational_ratio
        + 0.20 * backup_ratio
        + 0.20 * capacity_score
    )

    return round(raw * _MAX_PUMP, 2)


# ---------------------------------------------------------------------------
# 1. calculate_ward_scores
# ---------------------------------------------------------------------------

def calculate_ward_scores(
    wards_geojson: dict,
    hotspots_geojson: dict,
    drainage_geojson: dict,
    pumps_geojson: dict,
) -> list[dict]:
    """Calculate Pre-Monsoon Readiness Scores for every ward.

    Parameters
    ----------
    wards_geojson : dict
        GeoJSON FeatureCollection of ward boundaries.  Each feature's
        ``properties`` must include at minimum ``ward_id``, ``ward_name``,
        ``population``, ``area_km2``.
    hotspots_geojson : dict
        GeoJSON FeatureCollection of flood hotspots (``ward_id`` in props).
    drainage_geojson : dict
        GeoJSON FeatureCollection of drainage segments (``ward_id`` in props).
    pumps_geojson : dict
        GeoJSON FeatureCollection of pump stations (``ward_id`` in props).

    Returns
    -------
    list[dict]
        One dict per ward sorted by ``readiness_score`` **ascending** (worst
        first).  Each dict contains:

        * ``ward_id``, ``ward_name``, ``population``, ``area_km2``
        * ``drainage_capacity_index``          (0-25)
        * ``emergency_infrastructure_coverage`` (0-20)
        * ``flood_hotspot_density``            (0-25)
        * ``rainfall_vulnerability``           (0-15)
        * ``pump_station_availability``        (0-15)
        * ``readiness_score``                  (0-100)
        * ``category`` -- one of ``"Critical Risk"``, ``"Moderate Risk"``,
          ``"Prepared"``, ``"Resilient"``
        * ``hotspot_count``, ``drain_segment_count``, ``pump_count``
    """
    ward_features = wards_geojson.get("features", [])
    if not ward_features:
        logger.warning("calculate_ward_scores: empty wards FeatureCollection")
        return []

    # Pre-group ancillary features by ward_id for O(1) lookups.
    hotspots_by_ward = _group_features_by_ward(hotspots_geojson)
    drainage_by_ward = _group_features_by_ward(drainage_geojson)
    pumps_by_ward = _group_features_by_ward(pumps_geojson)

    results: list[dict] = []

    for feat in ward_features:
        props = feat.get("properties", {})
        wid = str(props.get("ward_id", ""))
        ward_name = str(props.get("ward_name", "Unknown"))
        population = int(props.get("population", 0))
        area_km2 = float(props.get("area_km2", 1.0))

        ward_hotspots = hotspots_by_ward.get(wid, [])
        ward_drains = drainage_by_ward.get(wid, [])
        ward_pumps = pumps_by_ward.get(wid, [])

        # -- Compute the five component scores --------------------------------
        drainage_idx = _score_drainage_capacity(props, ward_drains)
        emergency_cov = _score_emergency_infrastructure(props)
        hotspot_dens = _score_hotspot_density(props, ward_hotspots)
        rainfall_vuln = _score_rainfall_vulnerability(props)
        pump_avail = _score_pump_availability(props, ward_pumps)

        readiness = round(
            drainage_idx + emergency_cov + hotspot_dens + rainfall_vuln + pump_avail,
            2,
        )
        # Clamp to [0, 100] in case of floating-point drift.
        readiness = float(np.clip(readiness, 0.0, 100.0))

        category = _classify(readiness)

        results.append(
            {
                "ward_id": wid,
                "ward_name": ward_name,
                "population": population,
                "area_km2": round(area_km2, 2),
                "drainage_capacity_index": drainage_idx,
                "emergency_infrastructure_coverage": emergency_cov,
                "flood_hotspot_density": hotspot_dens,
                "rainfall_vulnerability": rainfall_vuln,
                "pump_station_availability": pump_avail,
                "readiness_score": readiness,
                "category": category,
                "hotspot_count": len(ward_hotspots),
                "drain_segment_count": len(ward_drains),
                "pump_count": len(ward_pumps),
            }
        )

    # Sort ascending by readiness_score (worst-prepared wards first).
    results.sort(key=lambda w: w["readiness_score"])

    logger.info(
        "calculate_ward_scores: scored %d wards  (min=%.1f, max=%.1f)",
        len(results),
        results[0]["readiness_score"] if results else 0.0,
        results[-1]["readiness_score"] if results else 0.0,
    )

    return results


# ---------------------------------------------------------------------------
# 2. get_ward_rankings
# ---------------------------------------------------------------------------

def get_ward_rankings(ward_scores: list[dict]) -> list[dict]:
    """Return a ranked leaderboard from pre-computed ward scores.

    Parameters
    ----------
    ward_scores : list[dict]
        Output of :func:`calculate_ward_scores` (already sorted ascending).

    Returns
    -------
    list[dict]
        Each element contains ``rank``, ``ward_id``, ``ward_name``,
        ``readiness_score``, ``category``.  Rank 1 = lowest score (most at
        risk).
    """
    if not ward_scores:
        return []

    # Ensure ascending order for ranking (rank 1 = worst).
    sorted_scores = sorted(ward_scores, key=lambda w: w["readiness_score"])

    rankings: list[dict] = []
    for idx, ws in enumerate(sorted_scores, start=1):
        rankings.append(
            {
                "rank": idx,
                "ward_id": ws["ward_id"],
                "ward_name": ws["ward_name"],
                "readiness_score": ws["readiness_score"],
                "category": ws["category"],
            }
        )

    return rankings


# ---------------------------------------------------------------------------
# 3. get_risk_alerts
# ---------------------------------------------------------------------------

# Alert definitions: (check_fn, alert_type, severity, message_template)
# check_fn receives the ward score dict and returns True if the alert fires.

_ALERT_RULES: list[tuple[str, str, str, str]] = [
    # (field_to_check, alert_type, severity, message_template)
    # These are processed by _evaluate_alert_rules below.
]


def get_risk_alerts(ward_scores: list[dict]) -> list[dict]:
    """Generate risk alerts for wards that fall below safety thresholds.

    Alerts are issued when:

    * The ward category is ``"Critical Risk"`` (readiness_score <= 30).
    * ``drainage_capacity_index`` is below 8 out of 25.
    * ``pump_station_availability`` is 0 (no operational pumps).
    * ``emergency_infrastructure_coverage`` is 0 (no shelters).
    * ``flood_hotspot_density`` component is below 6 out of 25.
    * ``rainfall_vulnerability`` component is below 4 out of 15.

    Parameters
    ----------
    ward_scores : list[dict]
        Output of :func:`calculate_ward_scores`.

    Returns
    -------
    list[dict]
        Each alert contains ``ward_id``, ``ward_name``, ``alert_type``,
        ``message``, ``severity``.
    """
    if not ward_scores:
        return []

    alerts: list[dict] = []

    for ws in ward_scores:
        wid = ws["ward_id"]
        wname = ws["ward_name"]

        # --- Critical Risk category alert ---
        if ws.get("category") == "Critical Risk":
            alerts.append(
                {
                    "ward_id": wid,
                    "ward_name": wname,
                    "alert_type": "critical_risk_ward",
                    "message": (
                        f"Ward '{wname}' has a readiness score of "
                        f"{ws['readiness_score']:.1f}/100 and is classified as "
                        f"Critical Risk. Immediate pre-monsoon intervention required."
                    ),
                    "severity": "critical",
                }
            )

        # --- Drainage capacity dangerously low ---
        if ws.get("drainage_capacity_index", _MAX_DRAINAGE) < 8.0:
            alerts.append(
                {
                    "ward_id": wid,
                    "ward_name": wname,
                    "alert_type": "low_drainage_capacity",
                    "message": (
                        f"Ward '{wname}' drainage capacity index is only "
                        f"{ws['drainage_capacity_index']:.1f}/{_MAX_DRAINAGE:.0f}. "
                        f"Drain desilting and capacity augmentation recommended."
                    ),
                    "severity": "high",
                }
            )

        # --- No operational pump stations ---
        if ws.get("pump_station_availability", _MAX_PUMP) == 0.0:
            alerts.append(
                {
                    "ward_id": wid,
                    "ward_name": wname,
                    "alert_type": "no_pump_stations",
                    "message": (
                        f"Ward '{wname}' has no operational pump stations. "
                        f"Deploy mobile pumps before monsoon onset."
                    ),
                    "severity": "critical",
                }
            )

        # --- No emergency shelters ---
        if ws.get("emergency_infrastructure_coverage", _MAX_EMERGENCY) == 0.0:
            alerts.append(
                {
                    "ward_id": wid,
                    "ward_name": wname,
                    "alert_type": "no_emergency_shelters",
                    "message": (
                        f"Ward '{wname}' has zero emergency infrastructure "
                        f"coverage. Designate shelters and stockpile relief "
                        f"supplies immediately."
                    ),
                    "severity": "critical",
                }
            )

        # --- High hotspot density ---
        if ws.get("flood_hotspot_density", _MAX_HOTSPOT) < 6.0:
            alerts.append(
                {
                    "ward_id": wid,
                    "ward_name": wname,
                    "alert_type": "high_hotspot_density",
                    "message": (
                        f"Ward '{wname}' has a high flood hotspot density "
                        f"(score {ws['flood_hotspot_density']:.1f}/{_MAX_HOTSPOT:.0f}). "
                        f"Prioritise micro-level flood mitigation works."
                    ),
                    "severity": "high",
                }
            )

        # --- Severe rainfall vulnerability ---
        if ws.get("rainfall_vulnerability", _MAX_RAINFALL) < 4.0:
            alerts.append(
                {
                    "ward_id": wid,
                    "ward_name": wname,
                    "alert_type": "high_rainfall_vulnerability",
                    "message": (
                        f"Ward '{wname}' is highly vulnerable to rainfall "
                        f"(score {ws['rainfall_vulnerability']:.1f}/{_MAX_RAINFALL:.0f}). "
                        f"Increase permeable surfaces and green cover."
                    ),
                    "severity": "high",
                }
            )

    # Sort alerts: critical first, then high.
    severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

    logger.info("get_risk_alerts: generated %d alerts across all wards", len(alerts))

    return alerts


# ---------------------------------------------------------------------------
# 4. get_category_distribution
# ---------------------------------------------------------------------------

def get_category_distribution(ward_scores: list[dict]) -> dict:
    """Compute the distribution of wards across readiness categories.

    Parameters
    ----------
    ward_scores : list[dict]
        Output of :func:`calculate_ward_scores`.

    Returns
    -------
    dict
        Top-level keys:

        * ``total_wards`` -- total number of wards.
        * ``categories`` -- dict keyed by category name, each containing
          ``count`` and ``percentage`` (rounded to one decimal).
        * ``avg_readiness_score`` -- mean score across all wards.
        * ``median_readiness_score`` -- median score.
        * ``std_readiness_score`` -- standard deviation of scores.
    """
    if not ward_scores:
        return {
            "total_wards": 0,
            "categories": {},
            "avg_readiness_score": 0.0,
            "median_readiness_score": 0.0,
            "std_readiness_score": 0.0,
        }

    total = len(ward_scores)
    scores = np.array([ws["readiness_score"] for ws in ward_scores])

    # Initialise all categories with zero counts.
    cat_counts: dict[str, int] = {label: 0 for _, label in _CATEGORY_THRESHOLDS}
    for ws in ward_scores:
        cat = ws.get("category", _classify(ws["readiness_score"]))
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    categories: dict[str, dict[str, Any]] = {}
    for label in cat_counts:
        count = cat_counts[label]
        categories[label] = {
            "count": count,
            "percentage": round(count / total * 100.0, 1),
        }

    return {
        "total_wards": total,
        "categories": categories,
        "avg_readiness_score": round(float(np.mean(scores)), 2),
        "median_readiness_score": round(float(np.median(scores)), 2),
        "std_readiness_score": round(float(np.std(scores)), 2),
    }
