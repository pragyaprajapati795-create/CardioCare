from fastapi.testclient import TestClient
from app.main import app
from pymongo import MongoClient
from app.config import get_settings
from app.database.mongodb import connect_to_mongodb

connect_to_mongodb()
client = TestClient(app)
settings = get_settings()

def test_database_health():
    """Test the database health endpoint"""
    response = client.get("/api/v1/database/health")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["database"] == "cardiocare_db"
    assert data["collection"] == "patients"
    assert data["patient_count"] == 68616

def test_database_pipeline():
    """Test the pipeline sync status"""
    response = client.get("/api/v1/database/pipeline")
    assert response.status_code == 200
    data = response.json()
    assert data["sync_status"] == "SYNCED"
    assert data["raw_records"] == 70000
    assert data["clean_records"] == 68616
    assert data["mongodb_records"] == 68616
    assert data["records_difference"] == 0

def test_database_stats():
    """Test the detailed stats endpoint"""
    response = client.get("/api/v1/database/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["database_connection_status"] == "Connected"
    assert "patients" in [c["name"] for c in data["collections"]]
    assert "indexes" in data

def test_mongodb_connection_direct():
    """Directly test the mongodb connection via pymongo"""
    mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)
    assert mongo_client.admin.command('ping')['ok'] == 1.0
    count = mongo_client[settings.MONGO_DB_NAME].patients.count_documents({})
    assert count == 68616
