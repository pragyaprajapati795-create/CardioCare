# CardioCare — Model Card

> **DISCLAIMER:** This model is an educational/software demonstration and is NOT a medical diagnostic system. It must not be used to make clinical decisions.

---

## 1. Model Purpose

Predict whether a patient is likely to have cardiovascular disease (CVD) based on demographic, physiological, and lifestyle features. The output is a binary classification (0 = no CVD, 1 = CVD predicted) with a probability score.

**Intended use:** Academic submission, project demonstration, software engineering portfolio.

**Out of scope:** Clinical diagnosis, medical screening, treatment recommendations.

---

## 2. Dataset

| Property | Value |
|---|---|
| Source | `backend/data/processed/cardio_clean.csv` |
| Original records | 70,000 |
| After cleaning | 68,616 |
| MongoDB documents | 68,616 |
| Class balance | 50.5% No CVD / 49.5% CVD (near-balanced) |

---

## 3. Features (12 input features)

| Feature | Type | Description |
|---|---|---|
| `age_years` | Continuous | Age in years |
| `gender` | Binary (1/2) | 1=Female, 2=Male |
| `height` | Integer (cm) | Height |
| `weight` | Continuous (kg) | Weight |
| `bmi` | Continuous | Computed from weight/height |
| `systolic_bp` | Integer (mmHg) | Systolic blood pressure |
| `diastolic_bp` | Integer (mmHg) | Diastolic blood pressure |
| `cholesterol` | Ordinal (1–3) | 1=Normal, 2=Above Normal, 3=Well Above Normal |
| `glucose` | Ordinal (1–3) | 1=Normal, 2=Above Normal, 3=Well Above Normal |
| `smoking` | Binary (0/1) | Smoking status |
| `alcohol` | Binary (0/1) | Alcohol intake |
| `physical_activity` | Binary (0/1) | Physical activity status |

**Excluded:**
- `patient_id` — identifier, not a predictor
- `cardio` — target variable (excluded to prevent leakage)
- `bp_category` — derived from `systolic_bp`/`diastolic_bp` (excluded to prevent leakage)
- `age` (raw days) — replaced by `age_years` for interpretability

---

## 4. Target

| Column | Values | Meaning |
|---|---|---|
| `cardio` | 0 | No cardiovascular disease |
| `cardio` | 1 | Cardiovascular disease present |

---

## 5. Training Procedure

| Step | Detail |
|---|---|
| Train/test split | 80% train, 20% test, stratified by target |
| Random seed | `42` (fixed for reproducibility) |
| Train samples | 54,892 |
| Test samples | 13,724 |
| Preprocessing | `StandardScaler` — fit **only** on training data |
| Leakage prevention | Scaler applied via `.transform()` on test set (never `fit_transform`) |

### Models compared

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0.7319 | 0.7605 | 0.6690 | 0.7118 | 0.7958 |
| Decision Tree | 0.7309 | 0.7442 | 0.6950 | 0.7188 | 0.7848 |
| Random Forest | 0.7354 | 0.7576 | 0.6840 | 0.7189 | 0.8013 |
| **XGBoost** | **0.7405** | **0.7646** | **0.6869** | **0.7237** | **0.8057** |

---

## 6. Evaluation Procedure

- All metrics computed on the **held-out test set** (13,724 records, never seen during training)
- 5-fold stratified cross-validation performed on training set to estimate generalisation
- Model selection criterion: **ROC-AUC** (primary), **F1-Score** (secondary)
- No hyperparameter tuning on the test set

---

## 7. Selected Model — XGBoost

**Selection reason:** Highest ROC-AUC (0.8057) with cross-validated F1 of 0.7166 ± 0.0019, indicating strong discriminative power with low variance.

### Evaluation Metrics

| Metric | Value |
|---|---|
| Accuracy | 0.7405 |
| Precision | 0.7646 |
| Recall | 0.6869 |
| F1-Score | 0.7237 |
| ROC-AUC | 0.8057 |
| CV F1 (5-fold) | 0.7166 ± 0.0019 |

### Confusion Matrix (test set)

|  | Predicted No CVD | Predicted CVD |
|---|---|---|
| **Actual No CVD** | 5,497 (TN) | 1,436 (FP) |
| **Actual CVD** | 2,126 (FN) | 4,665 (TP) |

### Top Feature Importances (XGBoost gain)

| Rank | Feature | Importance |
|---|---|---|
| 1 | systolic_bp | 0.598 |
| 2 | cholesterol | 0.140 |
| 3 | age_years | 0.062 |
| 4 | physical_activity | 0.033 |
| 5 | glucose | 0.026 |

---

## 8. Limitations

- **Educational only** — not validated for clinical use
- Training data is from a public dataset of unknown collection methodology
- Binary target may oversimplify CVD risk which exists on a spectrum
- ~26% false negative rate means some CVD cases are missed
- Model performance may not generalise to other populations or demographics
- Feature encodings (cholesterol 1–3, glucose 1–3) are ordinal approximations

---

## 9. Explainability Method

### Global Explainability
- **Feature importance** from XGBoost built-in gain scores (all 12 features)
- **Global SHAP values** computed via `TreeExplainer` on a random sample of 2,000 training records

### Per-prediction Explainability
- **SHAP TreeExplainer** applied to each individual prediction
- Returns per-feature contribution with direction (`toward_positive_class` / `toward_negative_class`)
- Top 5 positive and top 5 negative contributors reported

> ⚠ Feature contributions represent model behaviour, **not medical causation**. A high SHAP value for `systolic_bp` means the model weights this feature heavily — it does not mean high blood pressure *caused* the predicted outcome.

---

## 10. Medical Disclaimer

> **This model is an educational/software demonstration and is NOT a medical diagnostic system.**
> 
> - It must not be used to diagnose, treat, or make clinical decisions for any individual.
> - Results should never be communicated to patients as medical advice.
> - Any cardiovascular risk assessment must be performed by a qualified healthcare professional.
> - The CardioCare project was built for academic/portfolio demonstration purposes only.
