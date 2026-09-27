from datetime import datetime
from typing import Optional, Any, Dict
import uuid

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.database.mongodb import get_db
from app.services.prediction_service import prediction_service
from app.services.explainability_service import explainability_service

router = APIRouter(tags=["Prediction"])

def _success(data):
    return {"success": True, "data": data}

class PredictionRequest(BaseModel):
    patient_id: Optional[str] = Field(None, description="If provided, saves prediction to history under this ID")
    # Features required for prediction
    age_years: float = Field(..., ge=1, le=120)
    gender: int = Field(..., ge=1, le=2)
    height: int = Field(..., ge=50, le=250)
    weight: float = Field(..., ge=10, le=300)
    systolic_bp: int = Field(..., ge=60, le=300)
    diastolic_bp: int = Field(..., ge=40, le=200)
    cholesterol: int = Field(..., ge=1, le=3)
    glucose: int = Field(..., ge=1, le=3)
    smoking: int = Field(..., ge=0, le=1)
    alcohol: int = Field(..., ge=0, le=1)
    physical_activity: int = Field(..., ge=0, le=1)

    # Note: BMI is required by the model. We can accept it or compute it.
    # The model expects exactly 12 features. We compute BMI from weight/height if not passed directly.
    # We will compute it in the route.

@router.post("/predict", summary="Predict cardiovascular disease risk")
def predict_risk(request: PredictionRequest):
    if not prediction_service.is_ready():
        raise HTTPException(status_code=503, detail="Prediction service is not available")
        
    if request.systolic_bp <= request.diastolic_bp:
        raise HTTPException(status_code=422, detail="systolic_bp must be greater than diastolic_bp")
        
    db = get_db()
    
    # If patient_id is provided, verify it exists
    if request.patient_id:
        existing = db.patients.find_one({"patient_id": request.patient_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Patient not found")

    features_dict = request.model_dump()
    # Compute BMI for prediction
    features_dict["bmi"] = round(features_dict["weight"] / ((features_dict["height"] / 100) ** 2), 2)
    
    try:
        pred, proba = prediction_service.predict(features_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    model_version = prediction_service.metadata.get("model_version", "v1.0")
    
    # Per-prediction SHAP explanation (fast — XGBoost TreeExplainer)
    explanation = explainability_service.explain_prediction(features_dict, top_n=5)

    # Save to MongoDB
    pred_record = {
        "prediction_id": f"PR{str(uuid.uuid4().int)[:8].upper()}",
        "patient_id": request.patient_id,
        "prediction": pred,
        "probability": proba,
        "model_version": model_version,
        "timestamp": datetime.now().isoformat(),
        "input_summary": {
            "age_years": request.age_years,
            "systolic_bp": request.systolic_bp,
            "diastolic_bp": request.diastolic_bp,
            "cholesterol": request.cholesterol
        }
    }
    
    db.predictions.insert_one(pred_record)
    pred_record.pop("_id", None)
    
    return _success({
        "prediction":    pred,
        "probability":   proba,
        "model_version": model_version,
        "prediction_id": pred_record["prediction_id"],
        "explanation":   explanation,
        "disclaimer":    "Predicted cardiovascular disease class. This is an educational demonstration, not a medical diagnosis."
    })


@router.get("/predictions", summary="Get prediction history")
def list_predictions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    patient_id: Optional[str] = None
):
    db = get_db()
    skip = (page - 1) * limit
    
    filter_query = {}
    if patient_id:
        filter_query["patient_id"] = patient_id
        
    total = db.predictions.count_documents(filter_query)
    items = list(
        db.predictions.find(filter_query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    
    return _success({
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": max(1, (total + limit - 1) // limit)
    })


@router.get("/model/info", summary="Get model metadata and feature list")
def get_model_info():
    info = prediction_service.get_model_info()
    if info.get("status") == "not_ready":
        raise HTTPException(status_code=503, detail="Prediction service is not available")
    return _success(info)


@router.get("/model/metrics", summary="Get model evaluation metrics")
def get_model_metrics():
    metrics = prediction_service.get_model_metrics()
    if metrics.get("status") == "not_ready":
        raise HTTPException(status_code=503, detail="Prediction service is not available")
    return _success(metrics)
