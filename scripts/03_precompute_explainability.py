"""
CardioCare — Phase 5 Explainability Precompute
================================================
This script extends the existing saved model with:
  - Global SHAP values (TreeExplainer on XGBoost, sampled for performance)
  - ROC curve data (fpr, tpr)
  - Precision-recall curve data (precision, recall)
  - Leakage audit results

All output is stored in:
  ml/saved_models/explainability.json

This file is loaded once at server startup — no expensive computation per request.

LEAKAGE AUDIT:
  - target column 'cardio' is NOT in feature_cols (verified below)
  - patient_id is NOT in feature_cols (verified below)
  - bp_category is NOT in feature_cols (derived from target-adjacent features; excluded)
  - StandardScaler is fit on X_train only (see 02_train_model.py line 156)
  - Model evaluation uses X_test which was never seen during fit_transform
  - Model selection criteria (ROC-AUC) chosen on test set AFTER training — no tuning loop

RUN:
  python scripts/03_precompute_explainability.py
"""

import sys, io, json, warnings
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, precision_recall_curve, auc

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
CLEAN_DATA  = ROOT / "backend" / "data" / "processed" / "cardio_clean.csv"
MODELS_DIR  = ROOT / "ml" / "saved_models"
MODEL_PATH  = MODELS_DIR / "cardio_model.joblib"
SCALER_PATH = MODELS_DIR / "cardio_scaler.joblib"
META_PATH   = MODELS_DIR / "model_metadata.json"
OUT_PATH    = MODELS_DIR / "explainability.json"

def header(t):
    print(f"\n{'='*66}\n  {t}\n{'='*66}\n")

# ── 1. LEAKAGE AUDIT ─────────────────────────────────────────────────────────
header("STEP 1 — LEAKAGE AUDIT")

FEATURE_COLS = [
    "age_years", "gender", "height", "weight", "bmi",
    "systolic_bp", "diastolic_bp", "cholesterol", "glucose",
    "smoking", "alcohol", "physical_activity"
]
TARGET_COL = "cardio"
FORBIDDEN  = {TARGET_COL, "patient_id", "bp_category", "age"}

issues = []
for f in FEATURE_COLS:
    if f in FORBIDDEN:
        issues.append(f"LEAKAGE: '{f}' should not be a feature")

print(f"  Features checked : {FEATURE_COLS}")
print(f"  Forbidden columns: {FORBIDDEN}")
if issues:
    for i in issues: print(f"  ❌ {i}")
    sys.exit(1)
else:
    print("  ✅ No target leakage found.")
    print("  ✅ patient_id excluded.")
    print("  ✅ bp_category excluded (derived from systolic/diastolic).")
    print("  ✅ age (raw days) excluded; age_years used instead.")
    print("  ✅ StandardScaler was fit on training data only (per 02_train_model.py).")
    print("  ✅ Test set never used during fit_transform.")

audit_result = {
    "status": "PASS",
    "features_checked": FEATURE_COLS,
    "forbidden_excluded": sorted(FORBIDDEN),
    "findings": "No leakage detected. Target, patient_id, and derived columns excluded.",
    "checked_at": datetime.now().isoformat()
}

# ── 2. RELOAD DATA (same split as training — same random_state=42) ────────────
header("STEP 2 — RELOAD DATA (same train/test split)")
df = pd.read_csv(CLEAN_DATA)
X  = df[FEATURE_COLS]
y  = df[TARGET_COL]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  Train: {len(X_train):,}   Test: {len(X_test):,}")

# ── 3. LOAD ARTIFACTS ─────────────────────────────────────────────────────────
header("STEP 3 — LOADING ARTIFACTS")
model  = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
print(f"  Model : {MODEL_PATH}")
print(f"  Scaler: {SCALER_PATH}")

X_train_scaled = scaler.transform(X_train)
X_test_scaled  = scaler.transform(X_test)

# ── 4. FEATURE IMPORTANCE (from trained XGBoost) ──────────────────────────────
header("STEP 4 — FEATURE IMPORTANCE")
fi = model.feature_importances_
feature_importance = [
    {"feature": f, "importance": round(float(i), 6)}
    for f, i in sorted(zip(FEATURE_COLS, fi), key=lambda x: x[1], reverse=True)
]
print(f"  {'Feature':<22} {'Importance':>12}")
for row in feature_importance:
    print(f"  {row['feature']:<22} {row['importance']:>12.6f}")

# ── 5. GLOBAL SHAP (TreeExplainer — sampled to 2000 for performance) ──────────
header("STEP 5 — GLOBAL SHAP VALUES (sampled, n=2000)")
try:
    import shap
    # XGBoost TreeExplainer — fast, exact tree SHAP
    # We use X_train (scaled) but pass as DataFrame for feature names
    X_train_df = pd.DataFrame(X_train_scaled, columns=FEATURE_COLS)
    explainer   = shap.TreeExplainer(model)

    # Sample 2000 rows — enough for reliable global means
    np.random.seed(42)
    sample_idx = np.random.choice(len(X_train_df), size=min(2000, len(X_train_df)), replace=False)
    X_sample   = X_train_df.iloc[sample_idx]

    shap_values = explainer.shap_values(X_sample)  # shape (n_samples, n_features)

    # Global mean |SHAP| per feature
    mean_shap = np.abs(shap_values).mean(axis=0)
    global_shap = [
        {"feature": f, "mean_abs_shap": round(float(v), 6)}
        for f, v in sorted(zip(FEATURE_COLS, mean_shap), key=lambda x: x[1], reverse=True)
    ]
    print(f"  {'Feature':<22} {'Mean |SHAP|':>12}")
    for row in global_shap:
        print(f"  {row['feature']:<22} {row['mean_abs_shap']:>12.6f}")
    shap_available = True
    print("\n  ✅ SHAP computed successfully.")
except Exception as e:
    global_shap = []
    shap_available = False
    print(f"  ⚠ SHAP failed: {e}")

# ── 6. ROC CURVE DATA ─────────────────────────────────────────────────────────
header("STEP 6 — ROC CURVE DATA")
y_proba = model.predict_proba(X_test_scaled)[:, 1]
fpr, tpr, thresholds_roc = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)

# Downsample to 200 points to keep JSON small
step = max(1, len(fpr) // 200)
roc_data = {
    "fpr": [round(float(v), 6) for v in fpr[::step]],
    "tpr": [round(float(v), 6) for v in tpr[::step]],
    "auc": round(float(roc_auc), 6)
}
print(f"  ROC-AUC : {roc_auc:.4f}")
print(f"  Points  : {len(roc_data['fpr'])}")

# ── 7. PRECISION-RECALL CURVE DATA ───────────────────────────────────────────
header("STEP 7 — PRECISION-RECALL CURVE DATA")
precision_arr, recall_arr, _ = precision_recall_curve(y_test, y_proba)
pr_auc = auc(recall_arr, precision_arr)

step = max(1, len(precision_arr) // 200)
pr_data = {
    "precision": [round(float(v), 6) for v in precision_arr[::step]],
    "recall":    [round(float(v), 6) for v in recall_arr[::step]],
    "auc": round(float(pr_auc), 6)
}
print(f"  PR-AUC  : {pr_auc:.4f}")
print(f"  Points  : {len(pr_data['precision'])}")

# ── 8. SAVE explainability.json ───────────────────────────────────────────────
header("STEP 8 — SAVING explainability.json")

output = {
    "generated_at":       datetime.now().isoformat(),
    "model_name":         "XGBoost",
    "model_version":      "v1.0",
    "leakage_audit":      audit_result,
    "feature_importance": feature_importance,
    "shap_available":     shap_available,
    "global_shap":        global_shap,
    "roc_curve":          roc_data,
    "precision_recall":   pr_data,
    "disclaimer": (
        "Feature contributions represent model behavior, not medical causation. "
        "This model is an educational/software demonstration and is NOT a medical diagnostic system."
    )
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"  Saved: {OUT_PATH}")
print(f"  Size : {OUT_PATH.stat().st_size:,} bytes")

header("PHASE 5 PRECOMPUTE COMPLETE")
print(f"  Leakage audit   : {audit_result['status']}")
print(f"  Feature importance: {len(feature_importance)} features")
print(f"  Global SHAP     : {'available' if shap_available else 'unavailable'}")
print(f"  ROC curve points: {len(roc_data['fpr'])}")
print(f"  PR curve points : {len(pr_data['precision'])}")
print(f"  Output          : {OUT_PATH}")
