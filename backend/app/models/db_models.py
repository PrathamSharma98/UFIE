"""SQLAlchemy ORM models for UFIE (future PostGIS integration).

These models define the relational schema.  During the prototype phase the
application falls back to the InMemoryDataStore (see database.py) so these
tables are not strictly required at runtime.
"""

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


# ---------------------------------------------------------------------------
# Ward
# ---------------------------------------------------------------------------

class Ward(Base):
    """Administrative ward boundary with aggregate GIS attributes."""

    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ward_id = Column(String(32), unique=True, nullable=False, index=True)
    ward_name = Column(String(128), nullable=False)
    zone = Column(String(64), nullable=True)
    population = Column(Integer, nullable=True)
    area_km2 = Column(Float, nullable=True)

    # GIS-derived aggregate stats
    avg_elevation_m = Column(Float, nullable=True)
    avg_slope_deg = Column(Float, nullable=True)
    impervious_pct = Column(Float, nullable=True)
    drainage_density_km_per_km2 = Column(Float, nullable=True)
    green_cover_pct = Column(Float, nullable=True)

    # Geometry stored as WKT for portability; switch to
    # geoalchemy2.Geometry("MULTIPOLYGON", srid=4326) with PostGIS
    geom_wkt = Column(Text, nullable=True)

    # Relationships
    hotspots = relationship("FloodHotspot", back_populates="ward")
    drainage_segments = relationship("DrainageSegment", back_populates="ward")
    pump_stations = relationship("PumpStation", back_populates="ward")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Flood Hotspot
# ---------------------------------------------------------------------------

class FloodHotspot(Base):
    """Point location with high flood susceptibility."""

    __tablename__ = "flood_hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hotspot_id = Column(String(32), unique=True, nullable=False, index=True)
    ward_id = Column(String(32), ForeignKey("wards.ward_id"), nullable=False)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)
    slope_deg = Column(Float, nullable=True)
    flow_accumulation = Column(Float, nullable=True)
    drainage_proximity_m = Column(Float, nullable=True)
    impervious_surface_pct = Column(Float, nullable=True)
    soil_permeability = Column(Float, nullable=True)

    flood_probability = Column(Float, nullable=True)
    severity = Column(String(16), nullable=True)
    affected_population = Column(Integer, nullable=True)
    estimated_damage_inr_lakhs = Column(Float, nullable=True)
    runoff_coefficient = Column(Float, nullable=True)

    # Geometry: POINT
    geom_wkt = Column(Text, nullable=True)

    ward = relationship("Ward", back_populates="hotspots")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Drainage Segment
# ---------------------------------------------------------------------------

class DrainageSegment(Base):
    """A drain / nala segment with capacity metadata."""

    __tablename__ = "drainage_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(String(32), unique=True, nullable=False, index=True)
    ward_id = Column(String(32), ForeignKey("wards.ward_id"), nullable=True)

    drain_type = Column(String(32), nullable=True)  # open | closed | nala
    width_m = Column(Float, nullable=True)
    depth_m = Column(Float, nullable=True)
    length_m = Column(Float, nullable=True)
    capacity_m3s = Column(Float, nullable=True)
    condition = Column(String(32), nullable=True)  # good | fair | poor | blocked
    is_undersized = Column(Boolean, default=False)

    # Geometry: LINESTRING
    geom_wkt = Column(Text, nullable=True)

    ward = relationship("Ward", back_populates="drainage_segments")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Pump Station
# ---------------------------------------------------------------------------

class PumpStation(Base):
    """Flood-water pump station."""

    __tablename__ = "pump_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(32), unique=True, nullable=False, index=True)
    station_name = Column(String(128), nullable=True)
    ward_id = Column(String(32), ForeignKey("wards.ward_id"), nullable=True)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    capacity_lps = Column(Float, nullable=True)  # litres per second
    status = Column(String(32), nullable=True)  # operational | non-operational | under-maintenance
    num_pumps = Column(Integer, nullable=True)

    # Geometry: POINT
    geom_wkt = Column(Text, nullable=True)

    ward = relationship("Ward", back_populates="pump_stations")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Rainfall Record
# ---------------------------------------------------------------------------

class RainfallRecord(Base):
    """Historical or real-time rainfall observation."""

    __tablename__ = "rainfall_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_name = Column(String(128), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    timestamp = Column(DateTime, nullable=False, index=True)
    rainfall_mm = Column(Float, nullable=False)
    intensity_mmh = Column(Float, nullable=True)
    cumulative_mm = Column(Float, nullable=True)
    duration_hours = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
