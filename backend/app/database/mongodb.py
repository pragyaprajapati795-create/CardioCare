"""
CardioCare — MongoDB Connection Module
========================================
Manages the PyMongo client lifecycle.
Provides get_db() for dependency injection in FastAPI routes.
"""

from pymongo import MongoClient
from pymongo.database import Database
from app.config import get_settings

_client: MongoClient = None
_db: Database = None


def connect_to_mongodb() -> None:
    """Initialize the MongoDB connection. Called on app startup."""
    global _client, _db
    settings = get_settings()
    _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    _db = _client[settings.MONGO_DB_NAME]
    # Verify connection
    _client.admin.command("ping")
    print(f"[MongoDB] Connected to {settings.MONGO_URI}/{settings.MONGO_DB_NAME}")


def close_mongodb() -> None:
    """Close the MongoDB connection. Called on app shutdown."""
    global _client
    if _client:
        _client.close()
        print("[MongoDB] Connection closed.")


def get_db() -> Database:
    """Return the database instance. Use as FastAPI dependency."""
    return _db
