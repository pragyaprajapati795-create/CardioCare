"""
CardioCare — Application Configuration
=======================================
Loads settings from environment variables (.env file).
Uses Pydantic Settings for type-safe config management.
"""

import os
from pathlib import Path
from functools import lru_cache

# Simple config using os.environ (no external dependency needed for startup)
# For production, use pydantic-settings

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings:
    """Application settings loaded from environment variables."""

    # MongoDB
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "cardiocare_db")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production-use-secrets-token-hex-32")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # App
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # ML
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(BASE_DIR.parent / "ml" / "saved_models" / "cardio_model.joblib"))
    SCALER_PATH: str = os.getenv("SCALER_PATH", str(BASE_DIR.parent / "ml" / "saved_models" / "cardio_scaler.joblib"))
    MODEL_VERSION: str = os.getenv("MODEL_VERSION", "v1.0")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
