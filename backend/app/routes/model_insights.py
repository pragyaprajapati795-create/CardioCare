"""
CardioCare — Model Insights API (Phase 5)
==========================================
New endpoints that power the Model Performance dashboard:

  GET /api/v1/model/feature-importance
  GET /api/v1/model/explainability
  GET /api/v1/model/confusion-matrix
  GET /api/v1/model/roc-curve
  GET /api/v1/model/precision-recall

All data is precomputed — no expensive computation per request.
"""

from fastapi import APIRouter, HTTPException
from app.services.explainability_service import explainability_service

router = APIRouter(prefix="/model", tags=["Model Insights"])


def _success(data):
    return {"success": True, "data": data}


def _require_ready():
    if not explainability_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Explainability data not available. Run: python scripts/03_precompute_explainability.py",
        )


@router.get(
    "/feature-importance",
    summary="Get model-level feature importance (XGBoost gain scores)",
)
def get_feature_importance():
    _require_ready()
    data = explainability_service.get_feature_importance()
    return _success({
        "model":    "XGBoost",
        "method":   "built-in feature importance (gain)",
        "features": data,
        "disclaimer": (
            "Feature importance reflects model contribution, not medical causation."
        ),
    })


@router.get(
    "/explainability",
    summary="Full global explainability payload (feature importance + global SHAP)",
)
def get_global_explainability():
    _require_ready()
    return _success(explainability_service.get_global_explainability())


@router.get(
    "/confusion-matrix",
    summary="Confusion matrix from held-out evaluation test set",
)
def get_confusion_matrix():
    _require_ready()
    data = explainability_service.get_confusion_matrix()
    if not data:
        raise HTTPException(status_code=500, detail="Confusion matrix data unavailable")
    return _success(data)


@router.get(
    "/roc-curve",
    summary="ROC curve data from model evaluation (FPR, TPR, AUC)",
)
def get_roc_curve():
    _require_ready()
    data = explainability_service.get_roc_curve()
    if not data:
        raise HTTPException(status_code=500, detail="ROC curve data unavailable")
    return _success(data)


@router.get(
    "/precision-recall",
    summary="Precision-Recall curve data from model evaluation",
)
def get_precision_recall():
    _require_ready()
    data = explainability_service.get_precision_recall()
    if not data:
        raise HTTPException(status_code=500, detail="Precision-recall data unavailable")
    return _success(data)
