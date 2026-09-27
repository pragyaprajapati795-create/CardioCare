"""
CardioCare — Phase 6: Machine Learning Pipeline
=================================================

PURPOSE:
    Train and compare classification models for cardiovascular disease
    prediction using the cleaned 68,616-record dataset.

MODELS EVALUATED:
    1. Logistic Regression (baseline)
    2. Decision Tree
    3. Random Forest
    4. XGBoost (if available)

METRICS:
    Accuracy, Precision, Recall, F1-Score, ROC-AUC, Confusion Matrix

OUTPUT:
    ml/saved_models/cardio_model.joblib      — Final trained model
    ml/saved_models/cardio_scaler.joblib      — Feature scaler
    ml/saved_models/model_metadata.json       — Metrics & metadata
    backend/data/reports/ml_comparison.png     — Model comparison chart

DISCLAIMER:
    This model provides ML-based risk prediction for educational and
    software demonstration purposes. It is NOT a medical diagnostic system.

RUN:
    python scripts/02_train_model.py
"""

import sys
import io
import json
import time
import warnings
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve
)
import joblib

# Try XGBoost — optional
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).resolve().parent.parent
CLEAN_DATA     = PROJECT_ROOT / "backend" / "data" / "processed" / "cardio_clean.csv"
MODELS_DIR     = PROJECT_ROOT / "ml" / "saved_models"
REPORTS_DIR    = PROJECT_ROOT / "backend" / "data" / "reports"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def header(title: str):
    bar = "=" * 72
    print(f"\n{bar}\n  {title}\n{bar}\n")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — LOAD CLEANED DATA
# ─────────────────────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    header("STEP 1 — LOADING CLEANED DATASET")
    if not CLEAN_DATA.exists():
        print(f"  [ERROR] {CLEAN_DATA} not found.")
        print("  Run Phase 2 preprocessing first.")
        sys.exit(1)

    df = pd.read_csv(CLEAN_DATA)
    print(f"  Records : {len(df):,}")
    print(f"  Columns : {list(df.columns)}")
    print(f"  Target   : cardio (0={df['cardio'].value_counts()[0]:,} | 1={df['cardio'].value_counts()[1]:,})")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — FEATURE SELECTION & PREPARATION
# ─────────────────────────────────────────────────────────────────────────────

def prepare_features(df: pd.DataFrame):
    """
    Select features for ML training.

    FEATURES USED:
        age_years, gender, height, weight, bmi,
        systolic_bp, diastolic_bp, cholesterol, glucose,
        smoking, alcohol, physical_activity

    FEATURES EXCLUDED:
        - patient_id   : identifier, not a predictor
        - age (days)   : we use age_years instead (interpretable)
        - bp_category  : derived from BP values, would cause data leakage
        - cardio       : target variable

    WHY StandardScaler?
        Logistic Regression and some distance-based models are sensitive
        to feature scale. height (55-250 cm) and cholesterol (1-3) are on
        vastly different scales. StandardScaler normalizes each feature
        to mean=0, std=1.
    """
    header("STEP 2 — FEATURE SELECTION & PREPARATION")

    feature_cols = [
        "age_years", "gender", "height", "weight", "bmi",
        "systolic_bp", "diastolic_bp", "cholesterol", "glucose",
        "smoking", "alcohol", "physical_activity"
    ]
    target_col = "cardio"

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    print(f"  Features ({len(feature_cols)}): {feature_cols}")
    print(f"  Target: {target_col}")
    print(f"  X shape: {X.shape}")
    print(f"  y distribution: 0={int((y==0).sum()):,}  1={int((y==1).sum()):,}")

    # ── Train/Test Split ──────────────────────────────────────────────────
    # stratify=y ensures both train & test maintain the 50/50 class ratio
    # random_state=42 for reproducibility
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n  Train set: {len(X_train):,} ({len(X_train)/len(X)*100:.1f}%)")
    print(f"  Test set : {len(X_test):,} ({len(X_test)/len(X)*100:.1f}%)")
    print(f"  Train class dist: 0={int((y_train==0).sum()):,}  1={int((y_train==1).sum()):,}")
    print(f"  Test  class dist: 0={int((y_test==0).sum()):,}  1={int((y_test==1).sum()):,}")

    # ── Feature Scaling ───────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)   # Use .transform (NOT fit_transform) to avoid data leakage

    print("\n  StandardScaler fitted on TRAINING data only (no data leakage).")

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_cols


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — TRAIN & EVALUATE MODELS
# ─────────────────────────────────────────────────────────────────────────────

def train_and_evaluate(X_train, X_test, y_train, y_test):
    """
    Train 4 classifiers, evaluate each on the test set, and
    perform 5-fold stratified cross-validation.

    MODEL SELECTION STRATEGY:
        We do NOT pick the model with highest accuracy alone.
        For a medical-context model:
        - F1-score balances precision and recall
        - ROC-AUC measures discriminative ability across thresholds
        - We examine the confusion matrix for false negatives
          (a false negative = missed CVD case = more dangerous than false positive)
    """
    header("STEP 3 — TRAINING & EVALUATING MODELS")

    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, random_state=42, solver="lbfgs"
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=10, random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=15, random_state=42, n_jobs=-1
        ),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            random_state=42, eval_metric="logloss", verbosity=0
        )
        print("  XGBoost is available and will be evaluated.\n")
    else:
        print("  XGBoost not installed — skipping. (pip install xgboost)\n")

    results = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in models.items():
        print(f"  Training: {name}...")
        start = time.time()

        # ── Train ─────────────────────────────────────────────────────────
        model.fit(X_train, y_train)
        train_time = time.time() - start

        # ── Predict ───────────────────────────────────────────────────────
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        # ── Metrics ───────────────────────────────────────────────────────
        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec  = recall_score(y_test, y_pred)
        f1   = f1_score(y_test, y_pred)
        auc  = roc_auc_score(y_test, y_proba)
        cm   = confusion_matrix(y_test, y_pred)

        # ── Cross-Validation ──────────────────────────────────────────────
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1")

        results[name] = {
            "model"         : model,
            "accuracy"      : round(acc, 4),
            "precision"     : round(prec, 4),
            "recall"        : round(rec, 4),
            "f1_score"      : round(f1, 4),
            "roc_auc"       : round(auc, 4),
            "confusion_matrix": cm.tolist(),
            "cv_f1_mean"    : round(cv_scores.mean(), 4),
            "cv_f1_std"     : round(cv_scores.std(), 4),
            "train_time_sec": round(train_time, 3),
            "y_proba"       : y_proba,
        }

        # ── Print ─────────────────────────────────────────────────────────
        print(f"    Accuracy  : {acc:.4f}")
        print(f"    Precision : {prec:.4f}")
        print(f"    Recall    : {rec:.4f}")
        print(f"    F1-Score  : {f1:.4f}")
        print(f"    ROC-AUC   : {auc:.4f}")
        print(f"    CV F1     : {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        print(f"    Train time: {train_time:.3f}s")
        print(f"    Confusion Matrix:")
        print(f"      TN={cm[0][0]:,}  FP={cm[0][1]:,}")
        print(f"      FN={cm[1][0]:,}  TP={cm[1][1]:,}")
        print()

    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — MODEL COMPARISON & SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def select_best_model(results: dict):
    """
    Compare all models and select the best one.

    SELECTION CRITERIA (in order of importance):
        1. ROC-AUC — overall discriminative power
        2. F1-Score — balance of precision and recall
        3. CV F1 Mean — generalization performance
        4. Recall — minimize false negatives (missed CVD cases)

    We do NOT choose purely by accuracy because:
        - Accuracy alone can be misleading even with balanced data
        - A model with slightly lower accuracy but much better recall
          is preferable in a health-risk context
    """
    header("STEP 4 — MODEL COMPARISON & SELECTION")

    # ── Comparison Table ──────────────────────────────────────────────────
    print(f"  {'Model':<25} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7} {'AUC':>7} {'CV-F1':>10}")
    print(f"  {'-'*75}")
    for name, r in results.items():
        print(f"  {name:<25} {r['accuracy']:>7.4f} {r['precision']:>7.4f} "
              f"{r['recall']:>7.4f} {r['f1_score']:>7.4f} {r['roc_auc']:>7.4f} "
              f"{r['cv_f1_mean']:>6.4f}+/-{r['cv_f1_std']:.4f}")

    # ── Select by ROC-AUC (primary) then F1 (secondary) ──────────────────
    best_name = max(results, key=lambda k: (results[k]["roc_auc"], results[k]["f1_score"]))
    best = results[best_name]

    print(f"\n  SELECTED MODEL: {best_name}")
    print(f"  REASON: Highest ROC-AUC ({best['roc_auc']:.4f}) with strong "
          f"F1-Score ({best['f1_score']:.4f})")
    print(f"  Cross-validated F1: {best['cv_f1_mean']:.4f} (+/- {best['cv_f1_std']:.4f})")

    return best_name, best


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — FEATURE IMPORTANCE
# ─────────────────────────────────────────────────────────────────────────────

def analyze_feature_importance(model, feature_cols: list, model_name: str):
    """
    Display feature importance for tree-based models.
    For logistic regression, we use coefficient magnitudes.
    """
    header("STEP 5 — FEATURE IMPORTANCE")

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        method = "Feature Importance (Gini / Information Gain)"
    elif hasattr(model, "coef_"):
        importances = np.abs(model.coef_[0])
        method = "Coefficient Magnitude (absolute)"
    else:
        print("  Model does not expose feature importances.")
        return None

    print(f"  Model: {model_name}")
    print(f"  Method: {method}\n")

    feat_imp = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
    print(f"  {'Feature':<25} {'Importance':>12}")
    print(f"  {'-'*40}")
    for feat, imp in feat_imp:
        bar = "#" * int(imp * 80)
        print(f"  {feat:<25} {imp:>12.4f}  {bar}")

    return feat_imp


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — SAVE MODEL & ARTIFACTS
# ─────────────────────────────────────────────────────────────────────────────

def save_artifacts(model, scaler, feature_cols, model_name, results, feat_imp):
    header("STEP 6 — SAVING MODEL & ARTIFACTS")

    # ── Save model ────────────────────────────────────────────────────────
    model_path = MODELS_DIR / "cardio_model.joblib"
    joblib.dump(model, model_path)
    print(f"  Model saved : {model_path}")

    # ── Save scaler ───────────────────────────────────────────────────────
    scaler_path = MODELS_DIR / "cardio_scaler.joblib"
    joblib.dump(scaler, scaler_path)
    print(f"  Scaler saved: {scaler_path}")

    # ── Build metadata ────────────────────────────────────────────────────
    best_r = results[model_name]
    metadata = {
        "model_name"        : model_name,
        "model_version"     : "v1.0",
        "trained_at"        : datetime.now().isoformat(),
        "dataset"           : str(CLEAN_DATA),
        "features"          : feature_cols,
        "test_split"        : 0.2,
        "random_state"      : 42,
        "metrics"           : {
            "accuracy"      : best_r["accuracy"],
            "precision"     : best_r["precision"],
            "recall"        : best_r["recall"],
            "f1_score"      : best_r["f1_score"],
            "roc_auc"       : best_r["roc_auc"],
            "cv_f1_mean"    : best_r["cv_f1_mean"],
            "cv_f1_std"     : best_r["cv_f1_std"],
            "confusion_matrix": best_r["confusion_matrix"],
        },
        "all_model_results" : {
            name: {k: v for k, v in r.items() if k not in ("model", "y_proba")}
            for name, r in results.items()
        },
        "feature_importance": [
            {"feature": f, "importance": round(float(i), 6)}
            for f, i in (feat_imp or [])
        ],
        "disclaimer": (
            "This model provides ML-based risk prediction for educational "
            "and software demonstration purposes. It is NOT a medical "
            "diagnostic system."
        ),
    }

    meta_path = MODELS_DIR / "model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"  Metadata saved: {meta_path}")

    return metadata


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — GENERATE COMPARISON CHART
# ─────────────────────────────────────────────────────────────────────────────

def generate_comparison_chart(results: dict, best_name: str, y_test):
    header("STEP 7 — GENERATING COMPARISON CHART")

    fig = plt.figure(figsize=(20, 12))
    fig.suptitle(
        "CardioCare — ML Model Comparison Dashboard\n"
        "Cardiovascular Disease Classification",
        fontsize=14, fontweight="bold", y=0.98
    )
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    model_names = list(results.keys())
    colors = ["#4C72B0", "#55A868", "#C44E52", "#DD8452"]

    # ── Panel 1: Accuracy Comparison ──────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    accs = [results[m]["accuracy"] for m in model_names]
    bars = ax1.bar(model_names, accs, color=colors[:len(model_names)], edgecolor="white")
    ax1.set_title("Accuracy", fontweight="bold")
    ax1.set_ylim(0.5, 1.0)
    ax1.set_ylabel("Score")
    for bar, val in zip(bars, accs):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                 f"{val:.4f}", ha="center", fontsize=8, fontweight="bold")
    ax1.tick_params(axis="x", rotation=15)

    # ── Panel 2: F1-Score Comparison ──────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    f1s = [results[m]["f1_score"] for m in model_names]
    bars = ax2.bar(model_names, f1s, color=colors[:len(model_names)], edgecolor="white")
    ax2.set_title("F1-Score", fontweight="bold")
    ax2.set_ylim(0.5, 1.0)
    for bar, val in zip(bars, f1s):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                 f"{val:.4f}", ha="center", fontsize=8, fontweight="bold")
    ax2.tick_params(axis="x", rotation=15)

    # ── Panel 3: ROC-AUC Comparison ───────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    aucs = [results[m]["roc_auc"] for m in model_names]
    bars = ax3.bar(model_names, aucs, color=colors[:len(model_names)], edgecolor="white")
    ax3.set_title("ROC-AUC", fontweight="bold")
    ax3.set_ylim(0.5, 1.0)
    for bar, val in zip(bars, aucs):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                 f"{val:.4f}", ha="center", fontsize=8, fontweight="bold")
    ax3.tick_params(axis="x", rotation=15)

    # ── Panel 4: ROC Curves ───────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    for i, name in enumerate(model_names):
        fpr, tpr, _ = roc_curve(y_test, results[name]["y_proba"])
        ax4.plot(fpr, tpr, color=colors[i], linewidth=2,
                 label=f"{name} (AUC={results[name]['roc_auc']:.3f})")
    ax4.plot([0,1], [0,1], "k--", linewidth=1, alpha=0.5)
    ax4.set_title("ROC Curves", fontweight="bold")
    ax4.set_xlabel("False Positive Rate")
    ax4.set_ylabel("True Positive Rate")
    ax4.legend(fontsize=7, loc="lower right")

    # ── Panel 5: Confusion Matrix (best model) ───────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    cm = np.array(results[best_name]["confusion_matrix"])
    im = ax5.imshow(cm, cmap="Blues", interpolation="nearest")
    ax5.set_title(f"Confusion Matrix — {best_name}", fontweight="bold")
    ax5.set_xticks([0,1]); ax5.set_yticks([0,1])
    ax5.set_xticklabels(["No CVD", "CVD"]); ax5.set_yticklabels(["No CVD", "CVD"])
    ax5.set_xlabel("Predicted"); ax5.set_ylabel("Actual")
    for i in range(2):
        for j in range(2):
            ax5.text(j, i, f"{cm[i][j]:,}", ha="center", va="center",
                     fontsize=14, fontweight="bold",
                     color="white" if cm[i][j] > cm.max()/2 else "black")

    # ── Panel 6: All Metrics Comparison ───────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2])
    metrics_list = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    x_pos = np.arange(len(metrics_list))
    width = 0.8 / len(model_names)
    for i, name in enumerate(model_names):
        vals = [results[name][m] for m in metrics_list]
        ax6.bar(x_pos + i * width, vals, width, label=name,
                color=colors[i], edgecolor="white")
    ax6.set_title("All Metrics Comparison", fontweight="bold")
    ax6.set_xticks(x_pos + width * (len(model_names)-1) / 2)
    ax6.set_xticklabels(["Acc", "Prec", "Rec", "F1", "AUC"])
    ax6.set_ylim(0.5, 1.0)
    ax6.legend(fontsize=7)

    chart_path = REPORTS_DIR / "ml_comparison.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Chart saved: {chart_path}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — VERIFY SAVED MODEL (SMOKE TEST)
# ─────────────────────────────────────────────────────────────────────────────

def verify_model(feature_cols):
    header("STEP 8 — VERIFYING SAVED MODEL (SMOKE TEST)")

    model  = joblib.load(MODELS_DIR / "cardio_model.joblib")
    scaler = joblib.load(MODELS_DIR / "cardio_scaler.joblib")

    # Sample input: 55-year-old male, 170cm, 80kg, BP 145/95, chol=2
    sample = {
        "age_years"         : 55,
        "gender"            : 2,
        "height"            : 170,
        "weight"            : 80,
        "bmi"               : 80 / (1.70 ** 2),
        "systolic_bp"       : 145,
        "diastolic_bp"      : 95,
        "cholesterol"       : 2,
        "glucose"           : 1,
        "smoking"           : 0,
        "alcohol"           : 0,
        "physical_activity" : 1,
    }

    X = np.array([[sample[f] for f in feature_cols]])
    X_scaled = scaler.transform(X)

    prediction  = model.predict(X_scaled)[0]
    probability = model.predict_proba(X_scaled)[0]

    print(f"  Sample input: {sample}")
    print(f"\n  Prediction : {prediction}  ({'CVD Risk' if prediction == 1 else 'No CVD Risk'})")
    print(f"  Probability: No-CVD={probability[0]:.4f}  CVD={probability[1]:.4f}")
    print(f"\n  Model loaded and working correctly.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n+------------------------------------------------------------------+")
    print("|  CardioCare  |  Phase 6: Machine Learning Pipeline               |")
    print("+------------------------------------------------------------------+")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print(f"  XGBoost  : {'Available' if HAS_XGBOOST else 'Not installed'}\n")

    df = load_data()
    X_train, X_test, y_train, y_test, scaler, feature_cols = prepare_features(df)
    results = train_and_evaluate(X_train, X_test, y_train, y_test)
    best_name, best_result = select_best_model(results)
    feat_imp = analyze_feature_importance(best_result["model"], feature_cols, best_name)
    metadata = save_artifacts(
        best_result["model"], scaler, feature_cols, best_name, results, feat_imp
    )
    generate_comparison_chart(results, best_name, y_test)
    verify_model(feature_cols)

    header("PHASE 6 COMPLETE")
    print(f"  Selected Model  : {best_name}")
    print(f"  Model Version   : v1.0")
    print(f"  Accuracy        : {best_result['accuracy']:.4f}")
    print(f"  F1-Score        : {best_result['f1_score']:.4f}")
    print(f"  ROC-AUC         : {best_result['roc_auc']:.4f}")
    print(f"\n  Files saved:")
    print(f"    ml/saved_models/cardio_model.joblib")
    print(f"    ml/saved_models/cardio_scaler.joblib")
    print(f"    ml/saved_models/model_metadata.json")
    print(f"    backend/data/reports/ml_comparison.png")
    print(f"\n  NEXT: Install MongoDB + Node.js, then build FastAPI + React\n")


if __name__ == "__main__":
    main()
