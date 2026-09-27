import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import joblib

logger = logging.getLogger(__name__)

# Paths
MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "saved_models"
MODEL_PATH = MODELS_DIR / "cardio_model.joblib"
SCALER_PATH = MODELS_DIR / "cardio_scaler.joblib"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

class PredictionService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.metadata = None
        self.feature_cols = []
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            if not MODEL_PATH.exists() or not SCALER_PATH.exists() or not METADATA_PATH.exists():
                logger.warning("ML artifacts not found. Model must be trained first.")
                return

            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
                
            self.feature_cols = self.metadata.get("features", [
                "age_years", "gender", "height", "weight", "bmi",
                "systolic_bp", "diastolic_bp", "cholesterol", "glucose",
                "smoking", "alcohol", "physical_activity"
            ])
            logger.info("ML Prediction artifacts loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load ML artifacts: {str(e)}")

    def is_ready(self) -> bool:
        return self.model is not None and self.scaler is not None

    def get_model_info(self) -> Dict[str, Any]:
        if not self.is_ready():
            return {"status": "not_ready", "message": "Model not loaded"}
            
        return {
            "model_name": self.metadata.get("model_name"),
            "model_version": self.metadata.get("model_version"),
            "features": self.feature_cols,
            "trained_at": self.metadata.get("trained_at"),
            "training_samples": int(68616 * 0.8), # based on train_test_split logic
            "test_samples": int(68616 * 0.2)
        }
        
    def get_model_metrics(self) -> Dict[str, Any]:
        if not self.is_ready():
            return {"status": "not_ready", "message": "Model not loaded"}
        return self.metadata.get("metrics", {})

    def predict(self, features_dict: Dict[str, Any]) -> Tuple[int, float]:
        """
        Takes a dictionary of features, scales them, and returns (prediction, probability of class 1)
        """
        if not self.is_ready():
            raise RuntimeError("Prediction model is not initialized.")

        # Ensure order matches training
        input_array = []
        for col in self.feature_cols:
            if col not in features_dict:
                raise ValueError(f"Missing required feature: {col}")
            input_array.append(features_dict[col])
            
        X = np.array([input_array])
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Predict
        pred = int(self.model.predict(X_scaled)[0])
        
        # Probabilities
        if hasattr(self.model, "predict_proba"):
            proba = float(self.model.predict_proba(X_scaled)[0][1])
        else:
            proba = 1.0 if pred == 1 else 0.0
            
        return pred, proba

# Singleton instance
prediction_service = PredictionService()
