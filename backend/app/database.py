"""Database connection and in-memory data store for UFIE.

* SQLAlchemy engine / session factory -- used when a real PostgreSQL
  (PostGIS) database is available.
* InMemoryDataStore -- loads GeoJSON sample files from disk so the
  prototype can run without any database at all.
"""

import json
import os
import logging
from typing import Generator, Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models.db_models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLAlchemy engine & session
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal = None


def _get_engine():
    """Lazily create the SQLAlchemy engine (avoids crash if DB is unavailable)."""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                echo=settings.DEBUG,
                future=True,
            )
        except Exception as exc:
            logger.warning("Could not create database engine: %s", exc)
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        eng = _get_engine()
        if eng is not None:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    factory = _get_session_factory()
    if factory is None:
        raise RuntimeError("Database is not configured")
    db = factory()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# In-memory data store (prototype fallback)
# ---------------------------------------------------------------------------

class InMemoryDataStore:
    """Loads GeoJSON / JSON sample data into memory for quick access.

    Expected directory layout under ``data/sample/``::

        wards.geojson
        flood_hotspots.geojson
        drainage.geojson
        pump_stations.geojson
        rainfall.json
        dem.json
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir or settings.SAMPLE_DATA_DIR
        self._wards: dict[str, Any] = {}
        self._hotspots: dict[str, Any] = {}
        self._drainage: dict[str, Any] = {}
        self._pumps: dict[str, Any] = {}
        self._rainfall: dict[str, Any] = {}
        self._dem: dict[str, Any] = {}
        self._loaded: bool = False

    # -- file helpers -------------------------------------------------------

    def _read_json(self, filename: str) -> dict[str, Any]:
        """Read a JSON / GeoJSON file and return parsed dict."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.isfile(filepath):
            logger.warning("Sample data file not found: %s", filepath)
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", filepath, exc)
            return {}

    # -- public API ---------------------------------------------------------

    def load_data(self) -> None:
        """Load all sample data files into memory."""
        if self._loaded:
            return

        logger.info("Loading sample data from %s ...", self.data_dir)
        self._wards = self._read_json("ward_boundaries.geojson")
        self._hotspots = self._read_json("flood_hotspots.geojson")
        self._drainage = self._read_json("drainage_network.geojson")
        self._pumps = self._read_json("pump_stations.geojson")
        self._rainfall = self._read_json("rainfall_history.json")
        self._dem = self._read_json("dem_grid.json")
        self._loaded = True
        logger.info("Sample data loaded successfully.")

    def get_wards(self) -> dict[str, Any]:
        """Return wards GeoJSON feature collection."""
        if not self._loaded:
            self.load_data()
        return self._wards

    def get_hotspots(self) -> dict[str, Any]:
        """Return flood-hotspot GeoJSON feature collection."""
        if not self._loaded:
            self.load_data()
        return self._hotspots

    def get_drainage(self) -> dict[str, Any]:
        """Return drainage GeoJSON feature collection."""
        if not self._loaded:
            self.load_data()
        return self._drainage

    def get_pumps(self) -> dict[str, Any]:
        """Return pump-station GeoJSON feature collection."""
        if not self._loaded:
            self.load_data()
        return self._pumps

    def get_rainfall(self) -> dict[str, Any]:
        """Return historical rainfall records."""
        if not self._loaded:
            self.load_data()
        return self._rainfall

    def get_dem(self) -> dict[str, Any]:
        """Return DEM (Digital Elevation Model) data."""
        if not self._loaded:
            self.load_data()
        return self._dem


# ---------------------------------------------------------------------------
# Global singleton -- import ``data_store`` anywhere in the app
# ---------------------------------------------------------------------------

data_store = InMemoryDataStore()
