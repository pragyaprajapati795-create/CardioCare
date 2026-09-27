"""
Phase 5 — Explainability & Model Insights Tests
=================================================
Tests:
  1.  feature importance endpoint
  2.  feature importance values are real (not zero/fabricated)
  3.  feature names match model features
  4.  explainability service loads
  5.  prediction includes explanation
  6.  top positive contributors structure
  7.  top negative contributors structure
  8.  confusion matrix endpoint
  9.  ROC curve endpoint
  10. Precision-recall endpoint
  11. Leakage audit: target NOT in features
  12. Leakage audit: patient_id NOT in features
  13. Global explainability endpoint

Uses isolated predictions_test collection — production records untouched.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.mongodb import connect_to_mongodb, get_db
from app.services.explainability_service import explainability_service

connect_to_mongodb()
client = TestClient(app)

_real_db = get_db()
TEST_PRED_COL    = "predictions_test"
TEST_PATIENT_COL = "patients_test"


@pytest.fixture(autouse=True)
def clean_test_collections():
    _real_db[TEST_PRED_COL].drop()
    _real_db[TEST_PATIENT_COL].drop()
    yield
    _real_db[TEST_PRED_COL].drop()
    _real_db[TEST_PATIENT_COL].drop()


@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    import app.routes.prediction as pr

    original = pr.get_db

    class _FakeDB:
        @property
        def predictions(self):
            return _real_db[TEST_PRED_COL]
        @property
        def patients(self):
            return _real_db[TEST_PATIENT_COL]

    monkeypatch.setattr(pr, "get_db", lambda: _FakeDB())
    yield
    monkeypatch.setattr(pr, "get_db", original)


VALID_PAYLOAD = {
    "age_years":        55,
    "gender":           2,
    "height":           170,
    "weight":           80,
    "systolic_bp":      145,
    "diastolic_bp":     90,
    "cholesterol":      2,
    "glucose":          1,
    "smoking":          0,
    "alcohol":          0,
    "physical_activity": 1,
}

EXPECTED_FEATURES = [
    "age_years", "gender", "height", "weight", "bmi",
    "systolic_bp", "diastolic_bp", "cholesterol", "glucose",
    "smoking", "alcohol", "physical_activity",
]


# ── 1. Feature importance endpoint ───────────────────────────────────────────

def test_feature_importance_endpoint():
    r = client.get("/api/v1/model/feature-importance")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "features" in body["data"]


# ── 2. Feature importance values are real numbers > 0 ────────────────────────

def test_feature_importance_values_nonzero():
    r = client.get("/api/v1/model/feature-importance")
    features = r.json()["data"]["features"]
    assert len(features) == 12
    importances = [f["importance"] for f in features]
    # Sum of XGBoost importances is approximately 1.0
    assert abs(sum(importances) - 1.0) < 0.01
    # All are positive
    assert all(v > 0 for v in importances)


# ── 3. Feature names match model features ────────────────────────────────────

def test_feature_names_match_model():
    r = client.get("/api/v1/model/feature-importance")
    returned_features = {f["feature"] for f in r.json()["data"]["features"]}
    assert returned_features == set(EXPECTED_FEATURES)


# ── 4. Explainability service loads ──────────────────────────────────────────

def test_explainability_service_loads():
    assert explainability_service.is_ready()
    fi = explainability_service.get_feature_importance()
    assert len(fi) == 12


# ── 5. Prediction includes explanation ───────────────────────────────────────

def test_prediction_includes_explanation():
    r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
    assert r.status_code == 200
    data = r.json()["data"]
    assert "explanation" in data
    expl = data["explanation"]
    assert expl["available"] is True
    assert len(expl["explanation"]) == 12  # all features


# ── 6. Top positive contributors structure ───────────────────────────────────

def test_top_positive_contributors_structure():
    r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
    expl = r.json()["data"]["explanation"]
    pos = expl["top_positive_contributors"]
    assert isinstance(pos, list)
    assert len(pos) <= 5
    for item in pos:
        assert "feature"      in item
        assert "value"        in item
        assert "contribution" in item
        assert "direction"    in item
        assert item["direction"] == "toward_positive_class"
        assert item["contribution"] > 0


# ── 7. Top negative contributors structure ───────────────────────────────────

def test_top_negative_contributors_structure():
    r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
    expl = r.json()["data"]["explanation"]
    neg = expl["top_negative_contributors"]
    assert isinstance(neg, list)
    for item in neg:
        assert item["direction"] == "toward_negative_class"
        assert item["contribution"] < 0


# ── 8. Confusion matrix endpoint ─────────────────────────────────────────────

def test_confusion_matrix_endpoint():
    r = client.get("/api/v1/model/confusion-matrix")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "true_negative"  in data
    assert "false_positive" in data
    assert "false_negative" in data
    assert "true_positive"  in data
    # Values must be positive integers from the actual evaluation
    total = data["true_negative"] + data["false_positive"] + data["false_negative"] + data["true_positive"]
    assert total == 13724  # 20% of 68,616


# ── 9. ROC curve endpoint ─────────────────────────────────────────────────────

def test_roc_curve_endpoint():
    r = client.get("/api/v1/model/roc-curve")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "fpr" in data
    assert "tpr" in data
    assert "auc" in data
    assert len(data["fpr"]) == len(data["tpr"])
    assert len(data["fpr"]) > 10
    assert 0.7 < data["auc"] < 1.0  # our model got 0.8057


# ── 10. Precision-recall endpoint ────────────────────────────────────────────

def test_precision_recall_endpoint():
    r = client.get("/api/v1/model/precision-recall")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "precision" in data
    assert "recall"    in data
    assert "auc"       in data
    assert len(data["precision"]) == len(data["recall"])
    assert len(data["precision"]) > 10


# ── 11. Leakage audit: target NOT in features ─────────────────────────────────

def test_leakage_target_not_in_features():
    fi = explainability_service.get_feature_importance()
    feature_names = {row["feature"] for row in fi}
    assert "cardio" not in feature_names, "TARGET LEAKAGE: 'cardio' is in feature list!"


# ── 12. Leakage audit: patient_id NOT in features ────────────────────────────

def test_leakage_patient_id_not_in_features():
    fi = explainability_service.get_feature_importance()
    feature_names = {row["feature"] for row in fi}
    assert "patient_id" not in feature_names, "IDENTIFIER LEAKAGE: 'patient_id' is in feature list!"
    assert "bp_category" not in feature_names, "DERIVED LEAKAGE: 'bp_category' is in feature list!"


# ── 13. Global explainability endpoint ───────────────────────────────────────

def test_global_explainability_endpoint():
    r = client.get("/api/v1/model/explainability")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "model_name"         in data
    assert "feature_importance" in data
    assert "global_shap"        in data
    assert data["shap_available"] is True
    assert len(data["global_shap"]) == 12


# ── 14. Production patient count sanity check ────────────────────────────────

def test_production_patients_collection_untouched():
    real_count = _real_db.patients.count_documents({})
    assert real_count == 68616, (
        f"Production patients collection was MODIFIED! Expected 68616, got {real_count}"
    )
