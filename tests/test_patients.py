"""
Phase 3 — Patient Management API Tests
========================================
Uses an ISOLATED test collection (patients_test) so real 68,616 production
records are NEVER modified, deleted, or corrupted during testing.

Run:
  $env:PYTHONPATH="backend"
  .venv/Scripts/python.exe -m pytest tests/test_patients.py -v
"""

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

# ── Setup test app with patched DB collection ────────────────────────────────
from app.main import app
from app.database.mongodb import connect_to_mongodb, get_db

connect_to_mongodb()

client = TestClient(app)

# Grab the real DB and point a separate TEST collection
_real_db = get_db()
TEST_COLLECTION = "patients_test"


def _col():
    return _real_db[TEST_COLLECTION]


# ── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_PATIENT = {
    "age_years": 45.0,
    "gender": 2,
    "height": 175,
    "weight": 80.0,
    "systolic_bp": 130,
    "diastolic_bp": 85,
    "cholesterol": 2,
    "glucose": 1,
    "smoking": 0,
    "alcohol": 0,
    "physical_activity": 1,
    "cardio": 0,
}


@pytest.fixture(autouse=True)
def clean_test_collection():
    """
    Before each test: drop the test collection.
    After each test: drop again to ensure clean state.
    NOTE: This ONLY touches 'patients_test', NEVER 'patients'.
    """
    _col().drop()
    yield
    _col().drop()


# We monkey-patch the patients router to use patients_test during these tests
@pytest.fixture(autouse=True)
def patch_collection(monkeypatch):
    """Redirect all DB calls in patients router to the isolated test collection."""
    import app.routes.patients as pr

    original_get_db = pr.get_db

    class _FakeDB:
        @property
        def patients(self):
            return _real_db[TEST_COLLECTION]

    def _patched_get_db():
        return _FakeDB()

    monkeypatch.setattr(pr, "get_db", _patched_get_db)
    yield
    monkeypatch.setattr(pr, "get_db", original_get_db)


def _create_via_api(payload=None):
    """Helper: create patient via API and return response."""
    return client.post("/api/v1/patients/", json=payload or SAMPLE_PATIENT)


# ── 1. LIST patients ──────────────────────────────────────────────────────────

def test_list_patients_empty():
    r = client.get("/api/v1/patients/")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_patients_returns_items():
    # Pre-insert 3 docs directly
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": f"PTEST00{i}", "bmi": 26.1, "bp_category": "Stage1_HTN"}
        for i in range(3)
    ])
    r = client.get("/api/v1/patients/")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 3
    assert len(r.json()["data"]["items"]) == 3


# ── 2. PAGINATION ─────────────────────────────────────────────────────────────

def test_pagination_page_and_limit():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": f"PTEST{i:03d}", "bmi": 26.1, "bp_category": "Stage1_HTN"}
        for i in range(25)
    ])
    r = client.get("/api/v1/patients/?page=2&limit=10")
    data = r.json()["data"]
    assert r.status_code == 200
    assert data["page"] == 2
    assert data["limit"] == 10
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["total_pages"] == 3


def test_pagination_last_page_partial():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": f"PTEST{i:03d}", "bmi": 26.1, "bp_category": "Normal"}
        for i in range(25)
    ])
    r = client.get("/api/v1/patients/?page=3&limit=10")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 5


# ── 3. MAX LIMIT enforcement ──────────────────────────────────────────────────

def test_limit_above_100_rejected():
    r = client.get("/api/v1/patients/?limit=101")
    assert r.status_code == 422   # FastAPI Query validation


def test_limit_100_accepted():
    r = client.get("/api/v1/patients/?limit=100")
    assert r.status_code == 200


# ── 4. SEARCH ─────────────────────────────────────────────────────────────────

def test_search_by_patient_id():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": "PTEST001", "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "PTEST002", "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "XOTHER01", "bmi": 26.1, "bp_category": "Normal"},
    ])
    r = client.get("/api/v1/patients/?search=PTEST")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 2
    for item in data["items"]:
        assert item["patient_id"].startswith("PTEST")


def test_search_no_match_returns_empty():
    r = client.get("/api/v1/patients/?search=DOESNOTEXIST99999")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 0


# ── 5. FILTERS ────────────────────────────────────────────────────────────────

def test_filter_by_gender():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": "F001", "gender": 1, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "M001", "gender": 2, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "M002", "gender": 2, "bmi": 26.1, "bp_category": "Normal"},
    ])
    r = client.get("/api/v1/patients/?gender=2")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 2


def test_filter_by_cardio():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": "D001", "cardio": 1, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "D002", "cardio": 1, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "H001", "cardio": 0, "bmi": 26.1, "bp_category": "Normal"},
    ])
    r = client.get("/api/v1/patients/?cardio=1")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 2


def test_filter_by_age_range():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": "Y001", "age_years": 25.0, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "M001", "age_years": 45.0, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "O001", "age_years": 65.0, "bmi": 26.1, "bp_category": "Normal"},
    ])
    r = client.get("/api/v1/patients/?min_age=35&max_age=55")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["patient_id"] == "M001"


def test_invalid_filter_value_rejected():
    r = client.get("/api/v1/patients/?gender=9")
    assert r.status_code == 422


# ── 6. SORTING ────────────────────────────────────────────────────────────────

def test_sort_by_age_desc():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": "A1", "age_years": 30.0, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "A2", "age_years": 50.0, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "A3", "age_years": 40.0, "bmi": 26.1, "bp_category": "Normal"},
    ])
    r = client.get("/api/v1/patients/?sort_by=age_years&sort_order=desc")
    assert r.status_code == 200
    ages = [item["age_years"] for item in r.json()["data"]["items"]]
    assert ages == sorted(ages, reverse=True)


def test_invalid_sort_field_rejected():
    r = client.get("/api/v1/patients/?sort_by=__proto__")
    assert r.status_code == 422


# ── 7. PATIENT DETAIL ─────────────────────────────────────────────────────────

def test_get_patient_detail():
    _col().insert_one({**SAMPLE_PATIENT, "patient_id": "PTEST001", "bmi": 26.1, "bp_category": "Normal"})
    r = client.get("/api/v1/patients/PTEST001")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["patient_id"] == "PTEST001"
    assert "_id" not in data


def test_get_patient_not_found():
    r = client.get("/api/v1/patients/DOESNOTEXIST")
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "PATIENT_NOT_FOUND"


# ── 8. CREATE PATIENT ─────────────────────────────────────────────────────────

def test_create_patient_success():
    r = _create_via_api()
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    p = body["data"]["patient"]
    assert p["patient_id"].startswith("P")
    assert "bmi" in p
    assert "bp_category" in p


def test_create_patient_computes_bmi():
    r = _create_via_api({**SAMPLE_PATIENT, "weight": 80.0, "height": 180})
    assert r.status_code == 201
    p = r.json()["data"]["patient"]
    expected_bmi = round(80.0 / (1.80 ** 2), 2)
    assert abs(p["bmi"] - expected_bmi) < 0.01


def test_create_patient_computes_bp_category():
    r = _create_via_api({**SAMPLE_PATIENT, "systolic_bp": 115, "diastolic_bp": 75})
    assert r.status_code == 201
    assert r.json()["data"]["patient"]["bp_category"] == "Normal"


def test_create_patient_invalid_age():
    r = _create_via_api({**SAMPLE_PATIENT, "age_years": 200})
    assert r.status_code == 422


def test_create_patient_systolic_must_exceed_diastolic():
    r = _create_via_api({**SAMPLE_PATIENT, "systolic_bp": 80, "diastolic_bp": 90})
    assert r.status_code == 422


def test_create_patient_invalid_gender():
    r = _create_via_api({**SAMPLE_PATIENT, "gender": 5})
    assert r.status_code == 422


def test_create_patient_invalid_cholesterol():
    r = _create_via_api({**SAMPLE_PATIENT, "cholesterol": 0})
    assert r.status_code == 422


# ── 9. UPDATE PATIENT ─────────────────────────────────────────────────────────

def test_update_patient_success():
    _col().insert_one({**SAMPLE_PATIENT, "patient_id": "UPTEST", "bmi": 26.1, "bp_category": "Normal"})
    r = client.put("/api/v1/patients/UPTEST", json={"smoking": 1})
    assert r.status_code == 200
    assert r.json()["data"]["patient"]["smoking"] == 1


def test_update_patient_recomputes_bmi():
    _col().insert_one({**SAMPLE_PATIENT, "patient_id": "BMITEST", "bmi": 26.1, "bp_category": "Normal"})
    r = client.put("/api/v1/patients/BMITEST", json={"weight": 100.0, "height": 175})
    assert r.status_code == 200
    new_bmi = r.json()["data"]["patient"]["bmi"]
    expected = round(100.0 / (1.75 ** 2), 2)
    assert abs(new_bmi - expected) < 0.01


def test_update_patient_not_found():
    r = client.put("/api/v1/patients/GHOST", json={"smoking": 1})
    assert r.status_code == 404


def test_update_patient_empty_body_rejected():
    _col().insert_one({**SAMPLE_PATIENT, "patient_id": "EMPTYTEST", "bmi": 26.1, "bp_category": "Normal"})
    r = client.put("/api/v1/patients/EMPTYTEST", json={})
    assert r.status_code == 422


def test_update_patient_invalid_bp_rejected():
    _col().insert_one({**SAMPLE_PATIENT, "patient_id": "BPTEST", "bmi": 26.1, "bp_category": "Normal"})
    r = client.put("/api/v1/patients/BPTEST", json={"systolic_bp": 70, "diastolic_bp": 90})
    assert r.status_code == 422


# ── 10. DELETE PATIENT ────────────────────────────────────────────────────────

def test_delete_patient_success():
    _col().insert_one({**SAMPLE_PATIENT, "patient_id": "DELTEST", "bmi": 26.1, "bp_category": "Normal"})
    r = client.delete("/api/v1/patients/DELTEST")
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert _col().find_one({"patient_id": "DELTEST"}) is None


def test_delete_patient_not_found():
    r = client.delete("/api/v1/patients/GHOST99")
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "PATIENT_NOT_FOUND"


# ── 11. COMBINED FILTERS ──────────────────────────────────────────────────────

def test_combined_filters():
    _col().insert_many([
        {**SAMPLE_PATIENT, "patient_id": "C1", "gender": 1, "cardio": 1, "age_years": 45.0, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "C2", "gender": 1, "cardio": 0, "age_years": 45.0, "bmi": 26.1, "bp_category": "Normal"},
        {**SAMPLE_PATIENT, "patient_id": "C3", "gender": 2, "cardio": 1, "age_years": 45.0, "bmi": 26.1, "bp_category": "Normal"},
    ])
    r = client.get("/api/v1/patients/?gender=1&cardio=1")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1
    assert r.json()["data"]["items"][0]["patient_id"] == "C1"


# ── 12. PRODUCTION DATA INTEGRITY ────────────────────────────────────────────

def test_production_patients_collection_untouched():
    """
    CRITICAL: Verify the real 68,616-record production collection
    was NOT modified during ANY Phase 3 test.
    """
    real_count = _real_db.patients.count_documents({})
    assert real_count == 68616, (
        f"Production patients collection was CORRUPTED during tests! "
        f"Expected 68616, got {real_count}"
    )
