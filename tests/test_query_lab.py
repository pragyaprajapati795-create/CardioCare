"""
Phase 2 — Query Lab & Analytics Tests
======================================
Requires: MongoDB running with 68,616 patient records imported (Phase 1).
Run:  $env:PYTHONPATH="backend"; .venv/Scripts/python.exe -m pytest tests/test_query_lab.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.mongodb import connect_to_mongodb, get_db

# Ensure MongoDB is connected before any test
connect_to_mongodb()
client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _run(query_id: str):
    return client.post("/api/v1/query-lab/run", json={"query_id": query_id})


def _live_count():
    """Fetch actual patient count from MongoDB — never hard-coded."""
    return get_db().patients.count_documents({})


# ── Registry tests ─────────────────────────────────────────────────────────────
def test_query_registry_returns_list():
    r = client.get("/api/v1/query-lab/queries")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 15, f"Expected ≥15 queries, got {len(data)}"


def test_query_registry_has_required_fields():
    r = client.get("/api/v1/query-lab/queries")
    for q in r.json():
        assert "id"          in q
        assert "name"        in q
        assert "description" in q
        assert "operators"   in q


def test_invalid_query_id_rejected():
    r = _run("ARBITRARY_MONGO_CODE; db.dropDatabase()")
    assert r.status_code == 400
    assert r.json()["detail"]["success"] is False


# ── Query execution tests ──────────────────────────────────────────────────────
def test_total_patients_query():
    r = _run("total_patients")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    expected = _live_count()
    assert data["result"][0]["total_patients"] == expected


def test_cardio_cases_query():
    r = _run("cardio_cases")
    assert r.status_code == 200
    expected = get_db().patients.count_documents({"cardio": 1})
    assert r.json()["result"][0]["cardio_cases"] == expected


def test_non_cardio_cases_query():
    r = _run("non_cardio_cases")
    assert r.status_code == 200
    expected = get_db().patients.count_documents({"cardio": 0})
    assert r.json()["result"][0]["non_cardio_cases"] == expected


def test_cardio_plus_non_cardio_equals_total():
    """Integrity: disease + non-disease must equal total."""
    total   = _run("total_patients").json()["result"][0]["total_patients"]
    disease = _run("cardio_cases").json()["result"][0]["cardio_cases"]
    healthy = _run("non_cardio_cases").json()["result"][0]["non_cardio_cases"]
    assert disease + healthy == total


def test_average_age_query():
    r = _run("average_age")
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result) == 1
    avg = result[0].get("averageAge", 0)
    assert 18 < avg < 80, f"Average age {avg} is out of plausible range"


def test_gender_distribution_query():
    r = _run("gender_distribution")
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result) >= 1
    for row in result:
        assert "gender" in row
        assert "total"  in row


def test_cholesterol_distribution_query():
    r = _run("cholesterol_distribution")
    assert r.status_code == 200
    result = r.json()["result"]
    # dataset has 3 cholesterol levels
    assert len(result) == 3


def test_age_group_analysis_query():
    r = _run("age_group_analysis")
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result) >= 3
    for row in result:
        assert "ageGroup" in row
        assert "total"    in row
        assert "disease"  in row


def test_bmi_analysis_query():
    r = _run("bmi_analysis")
    assert r.status_code == 200
    result = r.json()["result"]
    categories = {row["category"] for row in result}
    assert categories & {"Normal", "Overweight", "Obese"}


def test_blood_pressure_analysis_query():
    r = _run("blood_pressure_analysis")
    assert r.status_code == 200
    assert r.json()["result_count"] >= 1


def test_smoking_vs_disease_query():
    r = _run("smoking_vs_disease")
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result) == 2  # smoker / non-smoker


def test_alcohol_vs_disease_query():
    r = _run("alcohol_vs_disease")
    assert r.status_code == 200
    assert len(r.json()["result"]) == 2


def test_physical_activity_vs_disease_query():
    r = _run("physical_activity_vs_disease")
    assert r.status_code == 200
    assert len(r.json()["result"]) == 2


# ── Execution metadata ─────────────────────────────────────────────────────────
def test_execution_time_is_measured():
    r = _run("total_patients")
    ms = r.json()["execution_time_ms"]
    assert ms >= 0, "execution_time_ms must be non-negative"
    assert ms < 5000, "Query took >5 s — something is wrong"


def test_json_serialization():
    """All query results must be JSON-serialisable (no ObjectId / datetime leaking)."""
    import json
    for qid in [
        "total_patients", "gender_distribution", "age_group_analysis",
        "bmi_analysis", "blood_pressure_analysis",
    ]:
        r = _run(qid)
        assert r.status_code == 200
        # If JSON serialization failed, the response would already be 500
        json.dumps(r.json())   # must not raise


# ── Analytics endpoint tests ────────────────────────────────────────────────────
def test_analytics_overview():
    r = client.get("/api/v1/analytics/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["totalPatients"] == _live_count()
    assert "averageBMI" in data


def test_analytics_gender():
    r = client.get("/api/v1/analytics/gender")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_analytics_cholesterol():
    r = client.get("/api/v1/analytics/cholesterol")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_analytics_glucose():
    r = client.get("/api/v1/analytics/glucose")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_analytics_lifestyle():
    r = client.get("/api/v1/analytics/lifestyle")
    assert r.status_code == 200
    data = r.json()
    assert "smoking"          in data
    assert "alcohol"          in data
    assert "physicalActivity" in data


def test_analytics_age():
    r = client.get("/api/v1/analytics/age")
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_analytics_bmi():
    r = client.get("/api/v1/analytics/bmi")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_analytics_blood_pressure():
    r = client.get("/api/v1/analytics/blood-pressure")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── Data integrity ─────────────────────────────────────────────────────────────
def test_mongodb_count_matches_csv():
    """Phase 2 integrity gate: MongoDB documents must equal cleaned CSV rows."""
    import os
    csv_path = "backend/data/processed/cardio_clean.csv"
    if not os.path.exists(csv_path):
        pytest.skip("Cleaned CSV not found — skip integrity check")
    csv_count = sum(1 for _ in open(csv_path)) - 1   # subtract header
    mongo_count = _live_count()
    assert mongo_count == csv_count, (
        f"MISMATCH — CSV: {csv_count}, MongoDB: {mongo_count}"
    )
