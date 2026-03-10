"""
Infrastructure gap detection for UFIE backend.

Provides pure functions to detect infrastructure deficiencies across wards,
generate prioritized improvement recommendations, and summarise gap statistics.
"""

import numpy as np
from collections import defaultdict


def detect_infrastructure_gaps(
    wards_geojson: dict,
    hotspots_geojson: dict,
    drainage_geojson: dict,
    pumps_geojson: dict,
) -> list[dict]:
    """
    Detect infrastructure gaps across the city.

    Gap categories:
      - Undersized drains: segments where current_load > capacity or
        condition is 'Poor' / 'Critical'.
      - Insufficient pump stations: wards with high flood risk but few or
        no operational pumps.
      - Low emergency coverage: wards with high population but few shelters.
      - Drainage gaps: wards with high impervious surface but low drainage
        density.

    Args:
        wards_geojson: GeoJSON FeatureCollection of ward polygons with
            properties including ward_id, ward_name, flood_risk_score,
            impervious_surface_pct, area_km2, population, shelter_count.
        hotspots_geojson: GeoJSON FeatureCollection of flood hotspot points.
        drainage_geojson: GeoJSON FeatureCollection of drainage line segments
            with properties including ward_id, capacity_m3s,
            current_load_m3s, condition, length_km.
        pumps_geojson: GeoJSON FeatureCollection of pump station points with
            properties including ward_id, status, capacity_m3s.

    Returns:
        List of gap dicts, each containing ward_id, ward_name, gap_type,
        description, severity, recommended_action, and
        estimated_cost_inr_crores.
    """
    gaps: list[dict] = []

    # ---- Build lookup maps ----
    ward_props: dict[str, dict] = {}
    for feature in wards_geojson.get("features", []):
        props = feature.get("properties", {})
        wid = str(props.get("ward_id", ""))
        ward_props[wid] = props

    drainage_by_ward: dict[str, list[dict]] = defaultdict(list)
    for feature in drainage_geojson.get("features", []):
        props = feature.get("properties", {})
        wid = str(props.get("ward_id", ""))
        drainage_by_ward[wid].append(props)

    pumps_by_ward: dict[str, list[dict]] = defaultdict(list)
    for feature in pumps_geojson.get("features", []):
        props = feature.get("properties", {})
        wid = str(props.get("ward_id", ""))
        pumps_by_ward[wid].append(props)

    hotspots_by_ward: dict[str, list[dict]] = defaultdict(list)
    for feature in hotspots_geojson.get("features", []):
        props = feature.get("properties", {})
        wid = str(props.get("ward_id", ""))
        hotspots_by_ward[wid].append(props)

    # ---- 1. Undersized drains ----
    for wid, drains in drainage_by_ward.items():
        wp = ward_props.get(wid, {})
        ward_name = str(wp.get("ward_name", wid))

        for drain in drains:
            capacity = float(drain.get("capacity_m3s", 0))
            current_load = float(drain.get("current_load_m3s", 0))
            condition = str(drain.get("condition", "Unknown"))
            segment_id = drain.get("segment_id", "unknown")

            is_overloaded = capacity > 0 and current_load > capacity
            is_degraded = condition in ("Poor", "Critical")

            if is_overloaded or is_degraded:
                if is_overloaded and is_degraded:
                    severity = "Critical"
                    desc = (
                        f"Drainage segment {segment_id} is overloaded "
                        f"({current_load:.1f}/{capacity:.1f} m3/s) and in "
                        f"{condition} condition."
                    )
                    cost = 8.0
                elif is_overloaded:
                    severity = "High"
                    desc = (
                        f"Drainage segment {segment_id} is overloaded "
                        f"({current_load:.1f}/{capacity:.1f} m3/s)."
                    )
                    cost = 5.0
                else:
                    severity = "High" if condition == "Critical" else "Moderate"
                    desc = (
                        f"Drainage segment {segment_id} is in {condition} "
                        f"condition and requires rehabilitation."
                    )
                    cost = 4.0 if condition == "Critical" else 2.5

                gaps.append(
                    {
                        "ward_id": wid,
                        "ward_name": ward_name,
                        "gap_type": "Undersized Drain",
                        "description": desc,
                        "severity": severity,
                        "recommended_action": (
                            "Upgrade drain capacity and rehabilitate infrastructure"
                            if is_overloaded
                            else "Rehabilitate drainage segment"
                        ),
                        "estimated_cost_inr_crores": cost,
                    }
                )

    # ---- 2. Insufficient pump stations ----
    for wid, wp in ward_props.items():
        flood_risk_score = float(wp.get("flood_risk_score", 0))
        ward_name = str(wp.get("ward_name", wid))

        if flood_risk_score < 0.4:
            continue  # only flag wards with moderate-to-high risk

        ward_pumps = pumps_by_ward.get(wid, [])
        operational_pumps = [
            p for p in ward_pumps if str(p.get("status", "")).lower() == "operational"
        ]
        total_pump_capacity = sum(
            float(p.get("capacity_m3s", 0)) for p in operational_pumps
        )

        # A ward is under-served if it has high risk but fewer than 2
        # operational pumps or low total pump capacity relative to risk.
        needed_capacity = flood_risk_score * 10.0  # heuristic threshold
        if len(operational_pumps) < 2 or total_pump_capacity < needed_capacity:
            if len(operational_pumps) == 0:
                severity = "Critical"
                cost = 12.0
            elif flood_risk_score >= 0.7:
                severity = "High"
                cost = 8.0
            else:
                severity = "Moderate"
                cost = 5.0

            gaps.append(
                {
                    "ward_id": wid,
                    "ward_name": ward_name,
                    "gap_type": "Insufficient Pump Stations",
                    "description": (
                        f"Ward has flood risk score {flood_risk_score:.2f} but only "
                        f"{len(operational_pumps)} operational pump(s) with total "
                        f"capacity {total_pump_capacity:.1f} m3/s "
                        f"(needed ~{needed_capacity:.1f} m3/s)."
                    ),
                    "severity": severity,
                    "recommended_action": (
                        "Install additional pump stations and ensure existing "
                        "pumps are maintained"
                    ),
                    "estimated_cost_inr_crores": cost,
                }
            )

    # ---- 3. Low emergency coverage ----
    for wid, wp in ward_props.items():
        population = int(wp.get("population", 0))
        shelter_count = int(wp.get("shelter_count", 0))
        ward_name = str(wp.get("ward_name", wid))

        if population == 0:
            continue

        # Threshold: at least 1 shelter per 25 000 people
        shelters_needed = max(1, population // 25_000)
        if shelter_count < shelters_needed:
            deficit = shelters_needed - shelter_count
            if shelter_count == 0:
                severity = "Critical"
                cost = 6.0 * deficit
            elif deficit >= 3:
                severity = "High"
                cost = 5.0 * deficit
            else:
                severity = "Moderate"
                cost = 4.0 * deficit

            gaps.append(
                {
                    "ward_id": wid,
                    "ward_name": ward_name,
                    "gap_type": "Low Emergency Coverage",
                    "description": (
                        f"Ward population {population:,} has {shelter_count} "
                        f"shelter(s) but needs at least {shelters_needed}. "
                        f"Deficit: {deficit}."
                    ),
                    "severity": severity,
                    "recommended_action": (
                        f"Establish {deficit} additional emergency shelter(s) "
                        f"with adequate supplies"
                    ),
                    "estimated_cost_inr_crores": round(cost, 2),
                }
            )

    # ---- 4. Drainage gaps (high impervious, low drainage density) ----
    for wid, wp in ward_props.items():
        impervious_pct = float(wp.get("impervious_surface_pct", 0))
        area_km2 = float(wp.get("area_km2", 1.0))
        ward_name = str(wp.get("ward_name", wid))

        if impervious_pct < 50:
            continue  # only flag highly impervious wards

        ward_drains = drainage_by_ward.get(wid, [])
        total_drain_length_km = sum(
            float(d.get("length_km", 0)) for d in ward_drains
        )
        drainage_density = total_drain_length_km / area_km2 if area_km2 > 0 else 0.0

        # Threshold: at least 2 km of drainage per km^2 for highly impervious wards
        if drainage_density < 2.0:
            shortfall_km = (2.0 - drainage_density) * area_km2
            if drainage_density < 0.5:
                severity = "Critical"
                cost_per_km = 3.0
            elif drainage_density < 1.0:
                severity = "High"
                cost_per_km = 2.5
            else:
                severity = "Moderate"
                cost_per_km = 2.0

            cost = round(shortfall_km * cost_per_km, 2)

            gaps.append(
                {
                    "ward_id": wid,
                    "ward_name": ward_name,
                    "gap_type": "Drainage Gap",
                    "description": (
                        f"Ward has {impervious_pct:.0f}% impervious surface but "
                        f"drainage density is only {drainage_density:.2f} km/km2 "
                        f"(target: 2.0 km/km2). Shortfall: {shortfall_km:.1f} km."
                    ),
                    "severity": severity,
                    "recommended_action": (
                        f"Construct {shortfall_km:.1f} km of additional drainage "
                        f"infrastructure and consider permeable surface retrofits"
                    ),
                    "estimated_cost_inr_crores": cost,
                }
            )

    return gaps


def generate_improvement_recommendations(gaps: list[dict]) -> list[dict]:
    """
    Group gaps by ward and generate prioritised improvement recommendations.

    Priority is determined by number and severity of gaps within each ward.

    Args:
        gaps: List of gap dicts as returned by detect_infrastructure_gaps.

    Returns:
        List of recommendation dicts sorted by priority (1 = highest), each
        containing ward_id, ward_name, priority, recommendations,
        total_estimated_cost_inr_crores, and expected_risk_reduction_pct.
    """
    severity_weight = {"Critical": 3, "High": 2, "Moderate": 1}

    # Group by ward
    wards: dict[str, dict] = {}
    for gap in gaps:
        wid = gap["ward_id"]
        if wid not in wards:
            wards[wid] = {
                "ward_id": wid,
                "ward_name": gap["ward_name"],
                "gaps": [],
                "total_cost": 0.0,
                "severity_score": 0,
            }
        wards[wid]["gaps"].append(gap)
        wards[wid]["total_cost"] += gap.get("estimated_cost_inr_crores", 0)
        wards[wid]["severity_score"] += severity_weight.get(gap.get("severity", "Moderate"), 1)

    # Sort wards by severity_score descending, then by total_cost descending
    sorted_wards = sorted(
        wards.values(),
        key=lambda w: (w["severity_score"], w["total_cost"]),
        reverse=True,
    )

    recommendations: list[dict] = []
    for priority, ward_data in enumerate(sorted_wards, start=1):
        # Build unique recommendation strings from gap actions
        rec_strings: list[str] = []
        for gap in ward_data["gaps"]:
            action = gap.get("recommended_action", "")
            if action and action not in rec_strings:
                rec_strings.append(action)

        # Estimate risk reduction heuristic based on severity score
        max_possible_score = len(ward_data["gaps"]) * 3
        risk_reduction_pct = round(
            np.clip(
                (ward_data["severity_score"] / max_possible_score) * 40 + 10,
                10,
                50,
            ),
            1,
        )

        recommendations.append(
            {
                "ward_id": ward_data["ward_id"],
                "ward_name": ward_data["ward_name"],
                "priority": priority,
                "recommendations": rec_strings,
                "total_estimated_cost_inr_crores": round(ward_data["total_cost"], 2),
                "expected_risk_reduction_pct": float(risk_reduction_pct),
            }
        )

    return recommendations


def get_gap_summary(gaps: list[dict]) -> dict:
    """
    Produce summary statistics for the detected infrastructure gaps.

    Args:
        gaps: List of gap dicts as returned by detect_infrastructure_gaps.

    Returns:
        Dict with total_gaps, by_type (counts per gap_type),
        by_severity (counts per severity level), total_estimated_cost
        (sum in INR crores), and top_priority_wards (up to 5 wards with
        the most / most severe gaps).
    """
    by_type: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    total_cost = 0.0
    ward_severity: dict[str, dict] = {}

    severity_weight = {"Critical": 3, "High": 2, "Moderate": 1}

    for gap in gaps:
        gap_type = gap.get("gap_type", "Unknown")
        severity = gap.get("severity", "Moderate")
        cost = gap.get("estimated_cost_inr_crores", 0)

        by_type[gap_type] += 1
        by_severity[severity] += 1
        total_cost += cost

        wid = gap.get("ward_id", "")
        wname = gap.get("ward_name", wid)
        if wid not in ward_severity:
            ward_severity[wid] = {
                "ward_id": wid,
                "ward_name": wname,
                "gap_count": 0,
                "score": 0,
            }
        ward_severity[wid]["gap_count"] += 1
        ward_severity[wid]["score"] += severity_weight.get(severity, 1)

    # Top priority wards: sorted by score desc, then gap_count desc
    sorted_wards = sorted(
        ward_severity.values(),
        key=lambda w: (w["score"], w["gap_count"]),
        reverse=True,
    )
    top_priority_wards = [
        {"ward_id": w["ward_id"], "ward_name": w["ward_name"], "gap_count": w["gap_count"]}
        for w in sorted_wards[:5]
    ]

    return {
        "total_gaps": len(gaps),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "total_estimated_cost": round(total_cost, 2),
        "top_priority_wards": top_priority_wards,
    }
