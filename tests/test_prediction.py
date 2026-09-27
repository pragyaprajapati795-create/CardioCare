import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json

from app.main import app
from app.database.mongodb import connect_to_mongodb, get_db
from app.services.prediction_service import prediction_service

connect_to_mongodb()
client = TestClient(app)

_real_db = get_db()
TEST_COLLECTION_PRED = "predictions_test"
TEST_COLLECTION_PATIENT = "patients_test"

def _pred_col():
    return _real_db[TEST_COLLECTION_PRED]
    
def _pat_col():
    return _real_db[TEST_COLLECTION_PATIENT]

@pytest.fixture(autouse=True)
def clean_test_collections():
    _pred_col().drop()
    _pat_col().drop()
    yield
    _pred_col().drop()
    _pat_col().drop()

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    import app.routes.prediction as pr

    original_get_db = pr.get_db

    class _FakeDB:
        @property
        def predictions(self):
            return _real_db[TEST_COLLECTION_PRED]
            
        @property
        def patients(self):
            return _real_db[TEST_COLLECTION_PATIENT]

    def _patched_get_db():
        return _FakeDB()

    monkeypatch.setattr(pr, "get_db", _patched_get_db)
    yield
    monkeypatch.setattr(pr, "get_db", original_get_db)


def test_model_artifacts_exist():
    # 1. model artifact exists
    # 2. preprocessing artifact exists
    from app.services.prediction_service import MODEL_PATH, SCALER_PATH, METADATA_PATH
    assert MODEL_PATH.exists()
    assert SCALER_PATH.exists()
    assert METADATA_PATH.exists()

def test_model_loads():
    # 3. model loads
    assert prediction_service.is_ready()
    assert prediction_service.model is not None
    assert prediction_service.scaler is not None

def test_valid_prediction_works():
    # 4. valid prediction works
    # 6. prediction probability is valid
    # 7. prediction response structure
    payload = {
        "age_years": 55,
        "gender": 2,
        "height": 170,
        "weight": 80,
        "systolic_bp": 145,
        "diastolic_bp": 95,
        "cholesterol": 2,
        "glucose": 1,
        "smoking": 0,
        "alcohol": 0,
        "physical_activity": 1
    }
    
    r = client.post("/api/v1/predict", json=payload)
    assert r.status_code == 200
    
    data = r.json()["data"]
    assert "prediction" in data
    assert "probability" in data
    assert "model_version" in data
    assert "prediction_id" in data
    assert "disclaimer" in data
    assert 0.0 <= data["probability"] <= 1.0

def test_prediction_saved_to_isolated_test_collection():
    # 8. prediction saved to isolated test collection
    payload = {
        "age_years": 55,
        "gender": 2,
        "height": 170,
        "weight": 80,
        "systolic_bp": 145,
        "diastolic_bp": 95,
        "cholesterol": 2,
        "glucose": 1,
        "smoking": 0,
        "alcohol": 0,
        "physical_activity": 1
    }
    r = client.post("/api/v1/predict", json=payload)
    assert r.status_code == 200
    
    # Check it was saved
    saved = list(_pred_col().find())
    assert len(saved) == 1
    
def test_invalid_input_rejected():
    # 5. invalid input rejected
    payload = {
        "age_years": 150, # invalid age
        "gender": 2,
        "height": 170,
        "weight": 80,
        "systolic_bp": 145,
        "diastolic_bp": 95,
        "cholesterol": 2,
        "glucose": 1,
        "smoking": 0,
        "alcohol": 0,
        "physical_activity": 1
    }
    r = client.post("/api/v1/predict", json=payload)
    assert r.status_code == 422
    
def test_nonexistent_patient_handling():
    # 9. nonexistent patient handling
    payload = {
        "patient_id": "DOES_NOT_EXIST",
        "age_years": 55,
        "gender": 2,
        "height": 170,
        "weight": 80,
        "systolic_bp": 145,
        "diastolic_bp": 95,
        "cholesterol": 2,
        "glucose": 1,
        "smoking": 0,
        "alcohol": 0,
        "physical_activity": 1
    }
    r = client.post("/api/v1/predict", json=payload)
    assert r.status_code == 404
    
def test_model_info_endpoint():
    # 10. model info endpoint
    r = client.get("/api/v1/model/info")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "model_name" in data
    assert "features" in data
    
def test_model_metrics_endpoint():
    # 11. model metrics endpoint
    r = client.get("/api/v1/model/metrics")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "accuracy" in data
    assert "f1_score" in data
    
def test_prediction_history_pagination():
    # 12. prediction history pagination
    # insert some dummy data
    import uuid
    from datetime import datetime
    dummy = []
    for i in range(25):
        dummy.append({
            "prediction_id": f"PR{str(uuid.uuid4().int)[:8]}",
            "patient_id": "PTEST",
            "prediction": 1,
            "probability": 0.8,
            "model_version": "v1.0",
            "timestamp": datetime.now().isoformat(),
            "input_summary": {}
        })
    _pred_col().insert_many(dummy)
    
    r = client.get("/api/v1/predictions?page=2&limit=10")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 2
