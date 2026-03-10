"""UFIE Configuration Module."""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Urban Flood Intelligence Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://ufie_user:ufie_pass@localhost:5432/ufie_db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # AI API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # GIS Settings
    CITY_CENTER_LAT: float = float(os.getenv("CITY_CENTER_LAT", "28.6139"))
    CITY_CENTER_LNG: float = float(os.getenv("CITY_CENTER_LNG", "77.2090"))
    CITY_NAME: str = os.getenv("CITY_NAME", "Delhi")
    GRID_RESOLUTION: float = 0.001  # ~111m grid cells

    # Data paths
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    SAMPLE_DATA_DIR: str = os.path.join(DATA_DIR, "sample")

    class Config:
        env_file = ".env"


settings = Settings()
