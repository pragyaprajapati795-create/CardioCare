"""
CardioCare - Step 1: Dataset Inspection & Data Quality Analysis
================================================================
Dataset  : Cardiovascular Disease Dataset (Kaggle)
Author   : CardioCare Project
Purpose  : Load the raw dataset, perform comprehensive data quality
           analysis, and generate a structured report. This script
           does NOT modify the dataset – it only reads and reports.

Run:
    python scripts/inspect_dataset.py

Output:
    backend/data/reports/data_quality_report.txt
    backend/data/reports/column_stats.csv
"""

import os
import sys
import json
import textwrap
from pathlib import Path
from datetime import datetime

import sys
import io
# Force UTF-8 output on Windows to handle Unicode characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend (no GUI needed)
import matplotlib.pyplot as plt
import seaborn as sns

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent          # cardiocare/
DATA_RAW     = PROJECT_ROOT / "backend" / "data" / "raw"
REPORTS_DIR  = PROJECT_ROOT / "backend" / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH     = DATA_RAW / "cardio_train.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────
def section(title: str) -> str:
    """Return a formatted section header string."""
    bar = "=" * 70
    return f"\n{bar}\n  {title}\n{bar}\n"


def log(msg: str, indent: int = 0) -> None:
    prefix = "  " * indent
    print(f"{prefix}{msg}")


# ── 1. Load Dataset ───────────────────────────────────────────────────────────
def load_dataset(path: Path) -> pd.DataFrame:
    log(section("1. LOADING DATASET"))
    if not path.exists():
        sys.exit(f"[ERROR] Dataset not found at: {path}\n"
                 "  → Copy cardio_train.csv into backend/data/raw/")

    df = pd.read_csv(path, sep=";")
    log(f"✔  File loaded       : {path.name}")
    log(f"✔  Rows              : {len(df):,}")
    log(f"✔  Columns           : {len(df.columns)}")
    log(f"✔  Columns list      : {list(df.columns)}")
    log(f"✔  Memory usage      : {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    return df


# ── 2. Basic Structure ────────────────────────────────────────────────────────
def inspect_structure(df: pd.DataFrame) -> dict:
    log(section("2. DATA STRUCTURE & DTYPES"))
    info = {}
    for col in df.columns:
        dtype      = str(df[col].dtype)
        n_unique   = df[col].nunique()
        sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
        log(f"  {col:<22} dtype={dtype:<10} unique={n_unique:<8} sample={sample_val}")
        info[col] = {"dtype": dtype, "unique_values": n_unique, "sample": str(sample_val)}
    return info


# ── 3. Missing Values ─────────────────────────────────────────────────────────
def check_missing(df: pd.DataFrame) -> dict:
    log(section("3. MISSING VALUES"))
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(4)
    result = {}
    for col in df.columns:
        status = "✔  OK" if missing[col] == 0 else f"⚠  {missing[col]:,} missing"
        log(f"  {col:<22} {status}  ({missing_pct[col]:.2f}%)")
        result[col] = {"missing_count": int(missing[col]), "missing_pct": float(missing_pct[col])}

    total_missing = missing.sum()
    log(f"\n  Total missing cells : {total_missing:,}")
    return result


# ── 4. Duplicate Records ──────────────────────────────────────────────────────
def check_duplicates(df: pd.DataFrame) -> dict:
    log(section("4. DUPLICATE RECORDS"))

    # Full-row duplicates (excluding the id column)
    feature_cols = [c for c in df.columns if c != "id"]
    dup_full = df.duplicated().sum()
    dup_features = df.duplicated(subset=feature_cols).sum()

    log(f"  Full-row duplicates             : {dup_full:,}")
    log(f"  Feature-only duplicates (no id) : {dup_features:,}")
    log(f"  Duplicate IDs                   : {df['id'].duplicated().sum():,}")

    return {
        "full_row_duplicates": int(dup_full),
        "feature_only_duplicates": int(dup_features),
        "duplicate_ids": int(df["id"].duplicated().sum()),
    }


# ── 5. Age Analysis ───────────────────────────────────────────────────────────
def analyze_age(df: pd.DataFrame) -> dict:
    log(section("5. AGE ANALYSIS"))
    log("  ⚠  Age is stored in DAYS in this dataset (not years).")

    df["age_years"] = (df["age"] / 365.25).round(1)

    age_min  = df["age_years"].min()
    age_max  = df["age_years"].max()
    age_mean = df["age_years"].mean()
    age_med  = df["age_years"].median()

    log(f"  Min age  : {age_min:.1f} years  (raw days: {df['age'].min():,})")
    log(f"  Max age  : {age_max:.1f} years  (raw days: {df['age'].max():,})")
    log(f"  Mean age : {age_mean:.1f} years")
    log(f"  Median   : {age_med:.1f} years")

    impossible = df[(df["age_years"] < 1) | (df["age_years"] > 120)]
    log(f"\n  Impossible ages (<1 or >120 years) : {len(impossible):,}")

    age_groups = {
        "Under 30"    : int(((df["age_years"] < 30)).sum()),
        "30–39"       : int(((df["age_years"] >= 30) & (df["age_years"] < 40)).sum()),
        "40–49"       : int(((df["age_years"] >= 40) & (df["age_years"] < 50)).sum()),
        "50–59"       : int(((df["age_years"] >= 50) & (df["age_years"] < 60)).sum()),
        "60–69"       : int(((df["age_years"] >= 60) & (df["age_years"] < 70)).sum()),
        "70 and over" : int(((df["age_years"] >= 70)).sum()),
    }
    log("\n  Age group distribution:")
    for grp, count in age_groups.items():
        pct = count / len(df) * 100
        log(f"    {grp:<15} : {count:>6,}  ({pct:.1f}%)", indent=1)

    return {
        "min_years": age_min, "max_years": age_max,
        "mean_years": round(age_mean, 2), "median_years": age_med,
        "impossible_count": len(impossible),
        "age_group_distribution": age_groups,
    }


# ── 6. Blood Pressure Analysis ────────────────────────────────────────────────
def analyze_blood_pressure(df: pd.DataFrame) -> dict:
    log(section("6. BLOOD PRESSURE ANALYSIS"))

    # Physiologically plausible ranges:
    #   Systolic  : 60 – 300 mmHg
    #   Diastolic : 40 – 200 mmHg
    #   Systolic must be > Diastolic

    invalid_systolic   = df[(df["ap_hi"] < 60) | (df["ap_hi"] > 300)]
    invalid_diastolic  = df[(df["ap_lo"] < 40) | (df["ap_lo"] > 200)]
    inverted_bp        = df[df["ap_hi"] <= df["ap_lo"]]   # systolic ≤ diastolic is impossible

    log(f"  Systolic  (ap_hi) stats:")
    log(f"    Min={df['ap_hi'].min()}, Max={df['ap_hi'].max()}, "
        f"Mean={df['ap_hi'].mean():.1f}, Median={df['ap_hi'].median()}")
    log(f"    Out-of-range (<60 or >300)   : {len(invalid_systolic):,} records")

    log(f"\n  Diastolic (ap_lo) stats:")
    log(f"    Min={df['ap_lo'].min()}, Max={df['ap_lo'].max()}, "
        f"Mean={df['ap_lo'].mean():.1f}, Median={df['ap_lo'].median()}")
    log(f"    Out-of-range (<40 or >200)   : {len(invalid_diastolic):,} records")

    log(f"\n  Inverted BP (systolic ≤ diastolic) : {len(inverted_bp):,} records")

    return {
        "systolic"  : {
            "min": int(df["ap_hi"].min()), "max": int(df["ap_hi"].max()),
            "mean": round(df["ap_hi"].mean(), 2), "median": df["ap_hi"].median(),
            "invalid_count": len(invalid_systolic)
        },
        "diastolic" : {
            "min": int(df["ap_lo"].min()), "max": int(df["ap_lo"].max()),
            "mean": round(df["ap_lo"].mean(), 2), "median": df["ap_lo"].median(),
            "invalid_count": len(invalid_diastolic)
        },
        "inverted_bp_count": len(inverted_bp),
    }


# ── 7. Height & Weight Analysis ───────────────────────────────────────────────
def analyze_anthropometrics(df: pd.DataFrame) -> dict:
    log(section("7. HEIGHT & WEIGHT ANALYSIS"))

    # Plausible ranges: height 100–250 cm, weight 30–300 kg
    invalid_height = df[(df["height"] < 100) | (df["height"] > 250)]
    invalid_weight = df[(df["weight"] < 30)  | (df["weight"] > 300)]

    log(f"  Height (cm): Min={df['height'].min()}, Max={df['height'].max()}, "
        f"Mean={df['height'].mean():.1f}, Median={df['height'].median()}")
    log(f"    Out-of-range (<100 or >250 cm) : {len(invalid_height):,} records")

    log(f"\n  Weight (kg): Min={df['weight'].min()}, Max={df['weight'].max()}, "
        f"Mean={df['weight'].mean():.1f}, Median={df['weight'].median()}")
    log(f"    Out-of-range (<30 or >300 kg)  : {len(invalid_weight):,} records")

    # BMI
    df["bmi"] = (df["weight"] / ((df["height"] / 100) ** 2)).round(2)
    invalid_bmi = df[(df["bmi"] < 10) | (df["bmi"] > 60)]
    log(f"\n  BMI (derived): Min={df['bmi'].min():.1f}, Max={df['bmi'].max():.1f}, "
        f"Mean={df['bmi'].mean():.1f}")
    log(f"    Physiologically extreme BMI (<10 or >60) : {len(invalid_bmi):,} records")

    return {
        "height": {
            "min": int(df["height"].min()), "max": int(df["height"].max()),
            "mean": round(df["height"].mean(), 2), "invalid_count": len(invalid_height)
        },
        "weight": {
            "min": float(df["weight"].min()), "max": float(df["weight"].max()),
            "mean": round(df["weight"].mean(), 2), "invalid_count": len(invalid_weight)
        },
        "bmi": {
            "min": round(float(df["bmi"].min()), 2),
            "max": round(float(df["bmi"].max()), 2),
            "mean": round(float(df["bmi"].mean()), 2),
            "extreme_count": len(invalid_bmi)
        },
    }


# ── 8. Categorical Variables ──────────────────────────────────────────────────
def analyze_categoricals(df: pd.DataFrame) -> dict:
    log(section("8. CATEGORICAL VARIABLE ANALYSIS"))

    cat_map = {
        "gender"      : {1: "Female", 2: "Male"},
        "cholesterol" : {1: "Normal", 2: "Above normal", 3: "Well above normal"},
        "gluc"        : {1: "Normal", 2: "Above normal", 3: "Well above normal"},
        "smoke"       : {0: "Non-smoker", 1: "Smoker"},
        "alco"        : {0: "Non-drinker", 1: "Drinker"},
        "active"      : {0: "Inactive", 1: "Active"},
        "cardio"      : {0: "No CVD", 1: "CVD"},
    }

    result = {}
    for col, mapping in cat_map.items():
        if col not in df.columns:
            log(f"  ⚠  Column '{col}' not found – skipping")
            continue
        vc = df[col].value_counts().sort_index()
        log(f"\n  {col}:")
        invalid_vals = set(df[col].dropna().unique()) - set(mapping.keys())
        if invalid_vals:
            log(f"    ⚠  Unexpected values found: {invalid_vals}")
        col_result = {}
        for val, label in mapping.items():
            count = int(vc.get(val, 0))
            pct   = count / len(df) * 100
            log(f"    {val} ({label:<20}) : {count:>7,}  ({pct:.1f}%)")
            col_result[label] = {"value": val, "count": count, "pct": round(pct, 2)}
        result[col] = col_result
    return result


# ── 9. Class Balance (Target Variable) ───────────────────────────────────────
def analyze_target(df: pd.DataFrame) -> dict:
    log(section("9. TARGET VARIABLE – CLASS BALANCE"))
    vc = df["cardio"].value_counts()
    total = len(df)
    no_cvd = int(vc.get(0, 0))
    cvd    = int(vc.get(1, 0))
    ratio  = cvd / no_cvd if no_cvd > 0 else float("inf")

    log(f"  No CVD  (0) : {no_cvd:>7,}  ({no_cvd/total*100:.2f}%)")
    log(f"  CVD     (1) : {cvd:>7,}  ({cvd/total*100:.2f}%)")
    log(f"  Ratio (CVD:No-CVD) : {ratio:.4f}")

    if 0.8 <= ratio <= 1.25:
        balance = "BALANCED"
        log("  ✔  Dataset is reasonably balanced – standard training is fine.")
    else:
        balance = "IMBALANCED"
        log("  ⚠  Class imbalance detected – consider SMOTE or class weighting in ML step.")

    return {"no_cvd": no_cvd, "cvd": cvd, "ratio": round(ratio, 4), "balance": balance}


# ── 10. Outlier Summary (IQR method) ─────────────────────────────────────────
def detect_outliers(df: pd.DataFrame) -> dict:
    log(section("10. OUTLIER DETECTION (IQR Method)"))
    numeric_cols = ["age", "height", "weight", "ap_hi", "ap_lo"]
    result = {}
    for col in numeric_cols:
        Q1  = df[col].quantile(0.25)
        Q3  = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = df[(df[col] < lower) | (df[col] > upper)]
        pct = len(outliers) / len(df) * 100
        log(f"  {col:<10} IQR=[{Q1:.1f}, {Q3:.1f}]  bounds=[{lower:.1f}, {upper:.1f}]  "
            f"outliers={len(outliers):,} ({pct:.2f}%)")
        result[col] = {
            "Q1": Q1, "Q3": Q3, "IQR": IQR,
            "lower_bound": round(lower, 2), "upper_bound": round(upper, 2),
            "outlier_count": len(outliers), "outlier_pct": round(pct, 4),
        }
    return result


# ── 11. Descriptive Statistics ────────────────────────────────────────────────
def descriptive_stats(df: pd.DataFrame) -> None:
    log(section("11. DESCRIPTIVE STATISTICS (Numeric Columns)"))
    numeric = df.select_dtypes(include=[np.number])
    stats = numeric.describe().T
    stats["skewness"] = numeric.skew()
    stats["kurtosis"] = numeric.kurt()
    log(stats.to_string())

    # Save to CSV
    stats_path = REPORTS_DIR / "column_stats.csv"
    stats.to_csv(stats_path)
    log(f"\n  ✔  Saved to {stats_path}")


# ── 12. Visualisations ────────────────────────────────────────────────────────
def generate_plots(df: pd.DataFrame) -> None:
    log(section("12. GENERATING VISUALISATION PLOTS"))

    df = df.copy()
    df["age_years"] = df["age"] / 365.25
    df["bmi"]       = df["weight"] / ((df["height"] / 100) ** 2)

    sns.set_theme(style="darkgrid", palette="muted")
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle("CardioCare – Data Quality & Distribution Overview", fontsize=16, fontweight="bold")

    # 1. Age distribution
    axes[0, 0].hist(df["age_years"], bins=40, color="#4C72B0", edgecolor="white")
    axes[0, 0].set_title("Age Distribution (years)")
    axes[0, 0].set_xlabel("Age (years)")

    # 2. Target class balance
    target_counts = df["cardio"].value_counts()
    axes[0, 1].bar(["No CVD (0)", "CVD (1)"], target_counts.values,
                   color=["#55A868", "#C44E52"], edgecolor="white")
    axes[0, 1].set_title("Target Variable – Class Balance")
    for i, v in enumerate(target_counts.values):
        axes[0, 1].text(i, v + 100, f"{v:,}", ha="center", fontweight="bold")

    # 3. Systolic BP distribution
    bp_valid = df[(df["ap_hi"] >= 60) & (df["ap_hi"] <= 300)]
    axes[0, 2].hist(bp_valid["ap_hi"], bins=50, color="#DD8452", edgecolor="white")
    axes[0, 2].set_title("Systolic BP Distribution (valid range)")
    axes[0, 2].set_xlabel("Systolic BP (mmHg)")

    # 4. Height distribution
    axes[1, 0].hist(df["height"], bins=40, color="#8172B2", edgecolor="white")
    axes[1, 0].set_title("Height Distribution (cm)")
    axes[1, 0].set_xlabel("Height (cm)")

    # 5. Weight distribution
    axes[1, 1].hist(df["weight"], bins=40, color="#937860", edgecolor="white")
    axes[1, 1].set_title("Weight Distribution (kg)")
    axes[1, 1].set_xlabel("Weight (kg)")

    # 6. Cholesterol levels
    chol_map  = {1: "Normal", 2: "Above\nNormal", 3: "Well Above\nNormal"}
    chol_vc   = df["cholesterol"].value_counts().sort_index()
    axes[1, 2].bar([chol_map[k] for k in chol_vc.index], chol_vc.values,
                   color=["#55A868", "#CCB974", "#C44E52"], edgecolor="white")
    axes[1, 2].set_title("Cholesterol Level Distribution")

    # 7. Gender distribution
    gender_map = {1: "Female", 2: "Male"}
    gender_vc  = df["gender"].value_counts().sort_index()
    axes[2, 0].bar([gender_map.get(k, k) for k in gender_vc.index], gender_vc.values,
                   color=["#DA8BC3", "#4C72B0"], edgecolor="white")
    axes[2, 0].set_title("Gender Distribution")

    # 8. Lifestyle flags
    lifestyle = {
        "Smoker"  : df["smoke"].sum(),
        "Drinker" : df["alco"].sum(),
        "Active"  : df["active"].sum(),
    }
    axes[2, 1].bar(lifestyle.keys(), lifestyle.values(),
                   color=["#C44E52", "#DD8452", "#55A868"], edgecolor="white")
    axes[2, 1].set_title("Lifestyle Flags (count of 1s)")

    # 9. BMI distribution (filtered)
    bmi_valid = df[(df["bmi"] >= 10) & (df["bmi"] <= 60)]
    axes[2, 2].hist(bmi_valid["bmi"], bins=50, color="#64B5CD", edgecolor="white")
    axes[2, 2].set_title("BMI Distribution (valid range)")
    axes[2, 2].set_xlabel("BMI")

    plt.tight_layout()
    plot_path = REPORTS_DIR / "data_quality_overview.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    log(f"  ✔  Plot saved to {plot_path}")


# ── 13. Summary Report ────────────────────────────────────────────────────────
def save_report(report: dict) -> None:
    report_path = REPORTS_DIR / "data_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    log(f"\n  ✔  JSON report saved to {report_path}")


def print_action_plan(report: dict) -> None:
    log(section("13. PREPROCESSING ACTION PLAN"))
    issues = []

    bp = report["blood_pressure"]
    if bp["systolic"]["invalid_count"] > 0:
        issues.append(f"Remove {bp['systolic']['invalid_count']:,} records with invalid systolic BP")
    if bp["diastolic"]["invalid_count"] > 0:
        issues.append(f"Remove {bp['diastolic']['invalid_count']:,} records with invalid diastolic BP")
    if bp["inverted_bp_count"] > 0:
        issues.append(f"Remove {bp['inverted_bp_count']:,} records with inverted BP (systolic ≤ diastolic)")

    anthro = report["anthropometrics"]
    if anthro["height"]["invalid_count"] > 0:
        issues.append(f"Remove {anthro['height']['invalid_count']:,} records with invalid height")
    if anthro["weight"]["invalid_count"] > 0:
        issues.append(f"Remove {anthro['weight']['invalid_count']:,} records with invalid weight")

    dup = report["duplicates"]
    if dup["feature_only_duplicates"] > 0:
        issues.append(f"Remove {dup['feature_only_duplicates']:,} feature-level duplicate rows")

    age = report["age"]
    if age["impossible_count"] > 0:
        issues.append(f"Remove {age['impossible_count']:,} records with impossible age (<1 or >120 years)")

    if not issues:
        log("  ✔  No critical issues found. Dataset appears reasonably clean.")
    else:
        log(f"  Found {len(issues)} preprocessing action(s):\n")
        for i, issue in enumerate(issues, 1):
            log(f"  {i}. {issue}")

    log("\n  Additional steps for Step 2 (Preprocessing):")
    log("  • Convert age from days → years")
    log("  • Derive BMI column (weight / height²)")
    log("  • One-hot or ordinal encode categoricals where needed")
    log("  • Apply IQR-based outlier clipping (NOT deletion) for BP/height/weight")
    log("  • Feature scaling (StandardScaler) for ML step")
    log("  • Persist cleaned dataset to backend/data/processed/cardio_clean.csv")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "+" + "-" * 68 + "+")
    print("|  CardioCare - Dataset Inspection & Data Quality Analysis        |")
    print("|  Step 1 of the CardioCare Project                               |")
    print("+" + "-" * 68 + "+")
    print(f"  Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Dataset   : {CSV_PATH}\n")

    df = load_dataset(CSV_PATH)

    report = {
        "generated_at"    : datetime.now().isoformat(),
        "dataset_file"    : str(CSV_PATH),
        "total_records"   : len(df),
        "total_columns"   : len(df.columns),
        "structure"       : inspect_structure(df),
        "missing_values"  : check_missing(df),
        "duplicates"      : check_duplicates(df),
        "age"             : analyze_age(df),
        "blood_pressure"  : analyze_blood_pressure(df),
        "anthropometrics" : analyze_anthropometrics(df),
        "categoricals"    : analyze_categoricals(df),
        "target_balance"  : analyze_target(df),
        "outliers_iqr"    : detect_outliers(df),
    }

    descriptive_stats(df)
    generate_plots(df)
    save_report(report)
    print_action_plan(report)

    log(section("✅ STEP 1 COMPLETE"))
    log(f"Reports saved to : {REPORTS_DIR}")
    log("Files generated  :")
    log("  • data_quality_report.json  – full structured report")
    log("  • column_stats.csv          – descriptive statistics per column")
    log("  • data_quality_overview.png – 9-panel visualisation")
    log("\nNext: Confirm and proceed to STEP 2 – Data Preprocessing Pipeline")


if __name__ == "__main__":
    main()
