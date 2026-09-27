# Machine Learning Pipeline

## Overview
The Machine Learning Pipeline for CardioCare is designed to predict the risk of cardiovascular disease based on patient features. It is built for educational and software demonstration purposes, and is NOT a medical diagnostic system.

## Dataset
- **Source**: Cleaned dataset (`backend/data/processed/cardio_clean.csv`)
- **Rows**: 68,616
- **Target**: `cardio` (binary: 0 = No CVD, 1 = CVD)
- **Features Used**: `age_years`, `gender`, `height`, `weight`, `bmi`, `systolic_bp`, `diastolic_bp`, `cholesterol`, `glucose`, `smoking`, `alcohol`, `physical_activity`

## Data Preparation & Leakage Prevention
- **Split**: 80% Training, 20% Testing
- **Stratification**: The target class distribution was maintained in both splits.
- **Random Seed**: `42`
- **Scaling**: A `StandardScaler` was fit ONLY on the training data to prevent data leakage, then applied to transform both train and test sets.

## Models Evaluated
1. **Logistic Regression** (Baseline)
2. **Decision Tree**
3. **Random Forest**
4. **XGBoost**

## Selection Criteria
Models were evaluated using Accuracy, Precision, Recall, F1-Score, and ROC-AUC.
- **Primary Metric**: ROC-AUC (overall discriminative ability)
- **Secondary Metric**: F1-Score (balance of precision and recall)

The final selected model is **XGBoost** due to its superior ROC-AUC and F1-Score compared to the baseline and other tree ensembles.

## Artifacts
The pipeline saves the following artifacts for the prediction service:
- `cardio_model.joblib`: The trained XGBoost model.
- `cardio_scaler.joblib`: The fitted StandardScaler.
- `model_metadata.json`: Contains model name, version, training details, feature list, and evaluation metrics.

## API Integration
The FastAPI backend serves the prediction service via:
- `POST /api/v1/predict`
- `GET /api/v1/predictions`
- `GET /api/v1/model/info`
- `GET /api/v1/model/metrics`

Predictions are saved into the MongoDB `cardiocare_db.predictions` collection.

## Disclaimer
This model provides ML-based risk prediction for educational and software demonstration purposes. It is NOT a medical diagnostic system.
