"""
CardioCare — Phase 1: Dataset Inspection & Data Quality Analysis
================================================================

PURPOSE:
    Load the raw Kaggle Cardiovascular Disease CSV and perform a
    thorough, documented data quality audit. This script:

    - Displays dataset shape, columns, dtypes
    - Checks missing values
    - Checks duplicate records (full-row AND feature-level)
    - Checks unique value ranges per column
    - Analyzes class distribution of the target variable
    - Identifies obvious data entry errors (invalid BP, age, height, weight)
    - Reports outliers using the IQR method
    - Produces a data quality JSON report + descriptive stats CSV

IMPORTANT:
    This script does NOT modify the dataset.
    All transformations happen in Phase 2 (preprocessing pipeline).

DATASET:
    Cardiovascular Disease Dataset — Kaggle
    Source : https://www.kaggle.com/datasets/sulianova/cardiovascular-disease-dataset
    Records: ~70,000  |  Separator: semicolon (;)

RUN:
    # Activate venv first
    .venv\\Scripts\\Activate.ps1          # Windows PowerShell
    source .venv/bin/activate             # Linux / macOS

    python scripts/01_inspect_dataset.py

OUTPUT:
    backend/data/reports/data_quality_report.json
    backend/data/reports/column_stats.csv
    backend/data/reports/data_quality_overview.png
"""

# ── Standard Library ──────────────────────────────────────────────────────────
import sys
import io
import os
import json
from pathlib import Path
from datetime import datetime

# Force UTF-8 so Unicode checkmarks render on Windows PowerShell
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Third-Party ───────────────────────────────────────────────────────────────
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")          # Non-interactive — no GUI window needed
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

# ─────────────────────────────────────────────────────────────────────────────
# PATH CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
# This script lives in  cardiocare/scripts/
# PROJECT_ROOT is       cardiocare/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "raw"
REPORTS_DIR  = PROJECT_ROOT / "backend" / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DATASET_PATH = RAW_DATA_DIR / "cardio_train.csv"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def header(title: str) -> None:
    """Print a clearly visible section header."""
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")


def subheader(title: str) -> None:
    print(f"\n  --- {title} ---")


def pct(count: int, total: int) -> str:
    """Return a formatted percentage string."""
    return f"{count / total * 100:.2f}%"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — LOAD DATASET
# ─────────────────────────────────────────────────────────────────────────────

def load_dataset() -> pd.DataFrame:
    """
    Load the raw CSV.

    KEY OBSERVATION:
        The Kaggle cardiovascular dataset uses a SEMICOLON (;) as the
        field separator, NOT a comma. Using pd.read_csv() without
        sep=";" would load the entire row as one column.
    """
    header("SECTION 1 — LOADING DATASET")

    if not DATASET_PATH.exists():
        print(f"  [ERROR] Dataset not found: {DATASET_PATH}")
        print("  Solution: Copy cardio_train.csv into backend/data/raw/")
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH, sep=";")

    print(f"  File     : {DATASET_PATH.name}")
    print(f"  Location : {DATASET_PATH}")
    print(f"  Size     : {DATASET_PATH.stat().st_size / 1024:.1f} KB")
    print(f"  Rows     : {len(df):,}")
    print(f"  Columns  : {len(df.columns)}")
    mem = df.memory_usage(deep=True).sum()
    print(f"  Memory   : {mem / 1024 / 1024:.2f} MB")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — SHAPE, COLUMNS, DATA TYPES
# ─────────────────────────────────────────────────────────────────────────────

def inspect_structure(df: pd.DataFrame) -> dict:
    """
    Print column names, data types, and a sample value for every column.

    WHY THIS MATTERS:
        - age is stored in DAYS (not years) — discovered by inspection
        - gender encoding: 1 = Female, 2 = Male (counter-intuitive)
        - All features are numeric; some are ordinal (cholesterol, gluc)
    """
    header("SECTION 2 — SHAPE, COLUMNS, DATA TYPES")
    print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns\n")
    print(f"  {'Column':<22} {'Dtype':<12} {'Unique':<10} {'Sample'}")
    print(f"  {'-'*60}")

    structure = {}
    for col in df.columns:
        dtype   = str(df[col].dtype)
        unique  = int(df[col].nunique())
        sample  = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
        print(f"  {col:<22} {dtype:<12} {unique:<10} {sample}")
        structure[col] = {"dtype": dtype, "unique_values": unique, "sample": str(sample)}

    print("\n  COLUMN DESCRIPTIONS:")
    col_desc = {
        "id"         : "Row identifier (NOT a medical patient ID)",
        "age"        : "Age in DAYS (must divide by 365.25 for years)",
        "gender"     : "1 = Female, 2 = Male",
        "height"     : "Height in centimeters",
        "weight"     : "Weight in kilograms",
        "ap_hi"      : "Systolic blood pressure (mmHg)",
        "ap_lo"      : "Diastolic blood pressure (mmHg)",
        "cholesterol": "1=Normal, 2=Above Normal, 3=Well Above Normal",
        "gluc"       : "1=Normal, 2=Above Normal, 3=Well Above Normal",
        "smoke"      : "0=Non-smoker, 1=Smoker (binary)",
        "alco"       : "0=Non-drinker, 1=Drinker (binary)",
        "active"     : "0=Inactive, 1=Physically Active (binary)",
        "cardio"     : "TARGET: 0=No CVD, 1=Cardiovascular Disease",
    }
    for col, desc in col_desc.items():
        print(f"    {col:<22} {desc}")

    return structure


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — MISSING VALUES
# ─────────────────────────────────────────────────────────────────────────────

def check_missing_values(df: pd.DataFrame) -> dict:
    """
    Count NaN / None values per column.

    WHAT WE EXPECT:
        This dataset is known to have no missing values (it was published
        as a clean Kaggle dataset). We verify this explicitly anyway —
        never assume.
    """
    header("SECTION 3 — MISSING VALUES")

    missing      = df.isnull().sum()
    missing_pct  = (missing / len(df) * 100).round(4)
    total_missing = int(missing.sum())

    print(f"  {'Column':<22} {'Missing Count':<18} {'Missing %'}")
    print(f"  {'-'*55}")

    result = {}
    for col in df.columns:
        mc = int(missing[col])
        mp = float(missing_pct[col])
        status = "OK" if mc == 0 else f"MISSING: {mc:,}"
        print(f"  {col:<22} {status:<18} {mp:.4f}%")
        result[col] = {"missing_count": mc, "missing_pct": mp}

    print(f"\n  Total missing cells : {total_missing:,}")
    if total_missing == 0:
        print("  RESULT: No missing values found. No imputation needed.")
    else:
        print(f"  RESULT: {total_missing:,} missing values detected. Imputation required in Phase 2.")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — DUPLICATE RECORDS
# ─────────────────────────────────────────────────────────────────────────────

def check_duplicates(df: pd.DataFrame) -> dict:
    """
    Check for duplicate rows at two levels:
        1. Full-row duplicates (including the id column)
        2. Feature-level duplicates (excluding id — same patient data)

    WHY BOTH?
        The 'id' column is just a row number. Two records can have
        different ids but identical feature values, meaning the same
        patient was accidentally recorded twice.
    """
    header("SECTION 4 — DUPLICATE RECORDS")

    full_dup     = int(df.duplicated().sum())
    feature_cols = [c for c in df.columns if c != "id"]
    feature_dup  = int(df.duplicated(subset=feature_cols).sum())
    id_dup       = int(df["id"].duplicated().sum())

    print(f"  Full-row duplicates (all columns)      : {full_dup:,}")
    print(f"  Feature-level duplicates (excluding id): {feature_dup:,}")
    print(f"  Duplicate id values                    : {id_dup:,}")

    if feature_dup > 0:
        print(f"\n  FINDING: {feature_dup} records have identical patient features.")
        print("  ACTION (Phase 2): Remove feature-level duplicates to avoid")
        print("  training the ML model on repeated data, which would inflate accuracy.")
    else:
        print("\n  RESULT: No duplicate records found.")

    return {
        "full_row_duplicates"    : full_dup,
        "feature_only_duplicates": feature_dup,
        "duplicate_ids"          : id_dup,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — UNIQUE VALUES PER COLUMN
# ─────────────────────────────────────────────────────────────────────────────

def check_unique_values(df: pd.DataFrame) -> dict:
    """
    For categorical columns, show all unique values.
    For continuous columns, show min/max/range.

    This catches unexpected encoding errors (e.g., gender=3 when only 1,2 valid).
    """
    header("SECTION 5 — UNIQUE VALUES PER COLUMN")

    binary_cols      = ["smoke", "alco", "active", "cardio"]
    ordinal_cols     = ["cholesterol", "gluc"]
    gender_cols      = ["gender"]
    continuous_cols  = ["age", "height", "weight", "ap_hi", "ap_lo"]

    result = {}

    print("  BINARY COLUMNS (expected: 0 and 1 only):")
    for col in binary_cols:
        vals = sorted(df[col].unique().tolist())
        unexpected = [v for v in vals if v not in [0, 1]]
        status = "OK" if not unexpected else f"UNEXPECTED: {unexpected}"
        print(f"    {col:<22} Values: {vals}  |  {status}")
        result[col] = {"unique_values": vals, "status": status}

    print("\n  ORDINAL COLUMNS (expected: 1, 2, 3 only):")
    for col in ordinal_cols:
        vals = sorted(df[col].unique().tolist())
        unexpected = [v for v in vals if v not in [1, 2, 3]]
        status = "OK" if not unexpected else f"UNEXPECTED: {unexpected}"
        print(f"    {col:<22} Values: {vals}  |  {status}")
        result[col] = {"unique_values": vals, "status": status}

    print("\n  GENDER COLUMN (expected: 1=Female, 2=Male only):")
    for col in gender_cols:
        vals = sorted(df[col].unique().tolist())
        unexpected = [v for v in vals if v not in [1, 2]]
        status = "OK" if not unexpected else f"UNEXPECTED: {unexpected}"
        print(f"    {col:<22} Values: {vals}  |  {status}")
        result[col] = {"unique_values": vals, "status": status}

    print("\n  CONTINUOUS COLUMNS (min → max range):")
    for col in continuous_cols:
        mn = df[col].min()
        mx = df[col].max()
        print(f"    {col:<22} Range: [{mn} → {mx}]  |  {df[col].nunique()} unique values")
        result[col] = {"min": float(mn), "max": float(mx), "unique_count": int(df[col].nunique())}

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — AGE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_age(df: pd.DataFrame) -> dict:
    """
    CRITICAL DISCOVERY:
        Age is stored in DAYS, not years. A raw value of 18,393 means
        18,393 / 365.25 = 50.4 years. If we use raw values for analysis
        or as an ML feature, results will be uninterpretable.

    VALIDATION:
        Plausible range for CVD dataset: 20 – 80 years
        (10,798 days = ~29.6 years to 23,713 days = ~64.9 years)
    """
    header("SECTION 6 — AGE ANALYSIS")

    df = df.copy()
    df["age_years"] = df["age"] / 365.25

    mn   = round(df["age_years"].min(), 1)
    mx   = round(df["age_years"].max(), 1)
    mean = round(df["age_years"].mean(), 2)
    med  = round(df["age_years"].median(), 2)

    print(f"  IMPORTANT: Age is stored in DAYS in this dataset.")
    print(f"  Conversion: age_days / 365.25 = age_years\n")
    print(f"  Min age  : {mn} years  (raw: {df['age'].min():,} days)")
    print(f"  Max age  : {mx} years  (raw: {df['age'].max():,} days)")
    print(f"  Mean age : {mean} years")
    print(f"  Median   : {med} years")

    impossible = df[(df["age_years"] < 1) | (df["age_years"] > 120)]
    print(f"\n  Impossible ages (<1 yr or >120 yr): {len(impossible):,} records")

    print("\n  AGE GROUP DISTRIBUTION:")
    groups = [
        ("Under 30",  (df["age_years"] < 30)),
        ("30 - 39",   (df["age_years"] >= 30) & (df["age_years"] < 40)),
        ("40 - 49",   (df["age_years"] >= 40) & (df["age_years"] < 50)),
        ("50 - 59",   (df["age_years"] >= 50) & (df["age_years"] < 60)),
        ("60 - 69",   (df["age_years"] >= 60) & (df["age_years"] < 70)),
        ("70 and over", (df["age_years"] >= 70)),
    ]
    group_dist = {}
    for label, mask in groups:
        count = int(mask.sum())
        p     = pct(count, len(df))
        bar   = "#" * (count // 1000)
        print(f"    {label:<15} : {count:>6,}  ({p})  {bar}")
        group_dist[label] = {"count": count, "pct": p}

    return {
        "min_years"             : mn,
        "max_years"             : mx,
        "mean_years"            : mean,
        "median_years"          : med,
        "impossible_count"      : len(impossible),
        "age_group_distribution": group_dist,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — BLOOD PRESSURE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_blood_pressure(df: pd.DataFrame) -> dict:
    """
    Blood pressure data quality checks.

    PHYSIOLOGICAL RULES:
        Systolic (ap_hi)  : 60 – 300 mmHg  (above 300 = data entry error)
        Diastolic (ap_lo) : 40 – 200 mmHg  (above 200 = data entry error)
        Systolic MUST be > Diastolic (inverted values are impossible)

    WHAT WE FOUND:
        ap_hi ranges from -150 to 16,020 — extreme data entry errors exist.
        ap_lo ranges from -70  to 11,000 — same issue.
        These are NOT biological outliers; they are corrupt records.
    """
    header("SECTION 7 — BLOOD PRESSURE ANALYSIS")

    print("  SYSTOLIC BLOOD PRESSURE (ap_hi):")
    print(f"    Min    : {df['ap_hi'].min()}")
    print(f"    Max    : {df['ap_hi'].max()}")
    print(f"    Mean   : {df['ap_hi'].mean():.2f}")
    print(f"    Median : {df['ap_hi'].median()}")

    invalid_hi = df[(df["ap_hi"] < 60) | (df["ap_hi"] > 300)]
    print(f"    Out-of-range (<60 or >300 mmHg): {len(invalid_hi):,} records")

    print("\n  DIASTOLIC BLOOD PRESSURE (ap_lo):")
    print(f"    Min    : {df['ap_lo'].min()}")
    print(f"    Max    : {df['ap_lo'].max()}")
    print(f"    Mean   : {df['ap_lo'].mean():.2f}")
    print(f"    Median : {df['ap_lo'].median()}")

    invalid_lo = df[(df["ap_lo"] < 40) | (df["ap_lo"] > 200)]
    print(f"    Out-of-range (<40 or >200 mmHg): {len(invalid_lo):,} records")

    inverted = df[df["ap_hi"] <= df["ap_lo"]]
    print(f"\n  INVERTED BP (systolic <= diastolic — physiologically impossible):")
    print(f"    Count: {len(inverted):,} records")

    print("\n  BP CLINICAL CATEGORIES (on valid range records):")
    valid_bp = df[(df["ap_hi"] >= 60) & (df["ap_hi"] <= 300) &
                  (df["ap_lo"] >= 40) & (df["ap_lo"] <= 200) &
                  (df["ap_hi"] > df["ap_lo"])]
    n_valid = len(valid_bp)

    categories = {
        "Normal (SBP<120 & DBP<80)"           : ((valid_bp["ap_hi"] < 120) & (valid_bp["ap_lo"] < 80)),
        "Elevated (SBP 120-129)"               : ((valid_bp["ap_hi"] >= 120) & (valid_bp["ap_hi"] < 130) & (valid_bp["ap_lo"] < 80)),
        "Stage 1 HTN (SBP 130-139 or DBP 80-89)": ((valid_bp["ap_hi"] >= 130) & (valid_bp["ap_hi"] < 140)) | ((valid_bp["ap_lo"] >= 80) & (valid_bp["ap_lo"] < 90)),
        "Stage 2 HTN (SBP>=140 or DBP>=90)"   : (valid_bp["ap_hi"] >= 140) | (valid_bp["ap_lo"] >= 90),
    }
    bp_cat_result = {}
    for label, mask in categories.items():
        count = int(mask.sum())
        p = pct(count, n_valid)
        print(f"    {label:<50} : {count:>6,}  ({p})")
        bp_cat_result[label] = {"count": count}

    return {
        "systolic": {
            "min": int(df["ap_hi"].min()), "max": int(df["ap_hi"].max()),
            "mean": round(df["ap_hi"].mean(), 2), "median": df["ap_hi"].median(),
            "invalid_count": len(invalid_hi),
        },
        "diastolic": {
            "min": int(df["ap_lo"].min()), "max": int(df["ap_lo"].max()),
            "mean": round(df["ap_lo"].mean(), 2), "median": df["ap_lo"].median(),
            "invalid_count": len(invalid_lo),
        },
        "inverted_bp_count": len(inverted),
        "bp_categories": bp_cat_result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — HEIGHT & WEIGHT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_anthropometrics(df: pd.DataFrame) -> dict:
    """
    Height and weight validation.

    VALID RANGES USED:
        Height : 100 – 250 cm   (below 100 likely data entry error)
        Weight : 30  – 300 kg   (below 30 kg for adults is extreme)

    BMI IS DERIVED (not in original dataset):
        BMI = weight (kg) / height (m)^2
        Normal: 18.5 – 24.9
        Overweight: 25 – 29.9
        Obese: >= 30
    """
    header("SECTION 8 — HEIGHT & WEIGHT ANALYSIS")

    df = df.copy()
    df["bmi"] = df["weight"] / ((df["height"] / 100) ** 2)

    print("  HEIGHT (cm):")
    print(f"    Min: {df['height'].min()}   Max: {df['height'].max()}   "
          f"Mean: {df['height'].mean():.1f}   Median: {df['height'].median()}")
    invalid_h = df[(df["height"] < 100) | (df["height"] > 250)]
    print(f"    Invalid height (<100 or >250 cm): {len(invalid_h):,} records")

    print("\n  WEIGHT (kg):")
    print(f"    Min: {df['weight'].min()}   Max: {df['weight'].max()}   "
          f"Mean: {df['weight'].mean():.1f}   Median: {df['weight'].median()}")
    invalid_w = df[(df["weight"] < 30) | (df["weight"] > 300)]
    print(f"    Invalid weight (<30 or >300 kg): {len(invalid_w):,} records")

    print("\n  BMI (derived — weight / height^2):")
    print(f"    Min: {df['bmi'].min():.1f}   Max: {df['bmi'].max():.1f}   "
          f"Mean: {df['bmi'].mean():.1f}   Median: {df['bmi'].median():.1f}")
    extreme_bmi = df[(df["bmi"] < 10) | (df["bmi"] > 60)]
    print(f"    Extreme BMI (<10 or >60): {len(extreme_bmi):,} records")

    print("\n  BMI DISTRIBUTION (all records):")
    bmi_cats = {
        "Underweight (<18.5)"    : (df["bmi"] < 18.5),
        "Normal (18.5 - 24.9)"  : (df["bmi"] >= 18.5) & (df["bmi"] < 25),
        "Overweight (25 - 29.9)" : (df["bmi"] >= 25) & (df["bmi"] < 30),
        "Obese (30+)"            : (df["bmi"] >= 30),
    }
    bmi_result = {}
    for label, mask in bmi_cats.items():
        count = int(mask.sum())
        p     = pct(count, len(df))
        print(f"    {label:<30} : {count:>6,}  ({p})")
        bmi_result[label] = count

    return {
        "height": {
            "min": int(df["height"].min()), "max": int(df["height"].max()),
            "mean": round(df["height"].mean(), 2), "invalid_count": len(invalid_h),
        },
        "weight": {
            "min": float(df["weight"].min()), "max": float(df["weight"].max()),
            "mean": round(df["weight"].mean(), 2), "invalid_count": len(invalid_w),
        },
        "bmi": {
            "min": round(float(df["bmi"].min()), 2),
            "max": round(float(df["bmi"].max()), 2),
            "mean": round(float(df["bmi"].mean()), 2),
            "extreme_count": len(extreme_bmi),
            "distribution": bmi_result,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — CATEGORICAL VARIABLES
# ─────────────────────────────────────────────────────────────────────────────

def analyze_categoricals(df: pd.DataFrame) -> dict:
    """
    Count and percentage for every category in each categorical variable.

    COLUMNS ANALYZED:
        gender, cholesterol, gluc, smoke, alco, active
    """
    header("SECTION 9 — CATEGORICAL VARIABLE ANALYSIS")

    cat_map = {
        "gender"      : {1: "Female", 2: "Male"},
        "cholesterol" : {1: "Normal", 2: "Above Normal", 3: "Well Above Normal"},
        "gluc"        : {1: "Normal", 2: "Above Normal", 3: "Well Above Normal"},
        "smoke"       : {0: "Non-Smoker", 1: "Smoker"},
        "alco"        : {0: "Non-Drinker", 1: "Drinker"},
        "active"      : {0: "Inactive", 1: "Physically Active"},
    }

    result = {}
    for col, mapping in cat_map.items():
        print(f"\n  {col.upper()}:")
        vc = df[col].value_counts().sort_index()
        unexpected = set(df[col].dropna().unique()) - set(mapping.keys())
        if unexpected:
            print(f"    WARNING: Unexpected values: {unexpected}")
        col_result = {}
        for val, label in mapping.items():
            count = int(vc.get(val, 0))
            p     = pct(count, len(df))
            bar   = "#" * (count // 3000)
            print(f"    {val} = {label:<25} : {count:>7,}  ({p})  {bar}")
            col_result[label] = {"value": val, "count": count, "pct": p}
        result[col] = col_result

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — CLASS DISTRIBUTION (TARGET VARIABLE)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_target(df: pd.DataFrame) -> dict:
    """
    Analyze the class balance of the target variable 'cardio'.

    CLASS BALANCE IS CRITICAL FOR ML:
        - If heavily imbalanced (e.g., 90/10), a naive model can achieve
          90% accuracy by always predicting the majority class.
        - Imbalanced data requires SMOTE, class weighting, or resampling.
        - A balanced dataset allows standard training.
    """
    header("SECTION 10 — TARGET VARIABLE (CLASS DISTRIBUTION)")

    vc    = df["cardio"].value_counts().sort_index()
    total = len(df)
    no_cvd = int(vc.get(0, 0))
    cvd    = int(vc.get(1, 0))
    ratio  = round(cvd / no_cvd if no_cvd > 0 else float("inf"), 4)

    print(f"  Target column : cardio (0 = No CVD, 1 = CVD)\n")
    print(f"  No CVD  (0) : {no_cvd:>8,}  ({pct(no_cvd, total)})")
    print(f"  CVD     (1) : {cvd:>8,}  ({pct(cvd, total)})")
    print(f"\n  Ratio CVD / No-CVD : {ratio}")

    if 0.8 <= ratio <= 1.25:
        balance = "BALANCED"
        print("  RESULT: Dataset is well-balanced. No SMOTE or class-weighting required.")
    elif 0.5 <= ratio < 0.8 or 1.25 < ratio <= 2.0:
        balance = "MILDLY IMBALANCED"
        print("  RESULT: Mild imbalance. Consider class_weight='balanced' in sklearn models.")
    else:
        balance = "SEVERELY IMBALANCED"
        print("  RESULT: Severe imbalance. Use SMOTE + class_weight='balanced'.")

    return {
        "no_cvd"       : no_cvd,
        "cvd"          : cvd,
        "ratio"        : ratio,
        "balance_status": balance,
        "no_cvd_pct"   : pct(no_cvd, total),
        "cvd_pct"      : pct(cvd, total),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — OUTLIER DETECTION (IQR METHOD)
# ─────────────────────────────────────────────────────────────────────────────

def detect_outliers(df: pd.DataFrame) -> dict:
    """
    Use the Interquartile Range (IQR) method to identify outliers.

    FORMULA:
        Q1 = 25th percentile
        Q3 = 75th percentile
        IQR = Q3 - Q1
        Lower bound = Q1 - 1.5 * IQR
        Upper bound = Q3 + 1.5 * IQR
        Outlier = value < lower OR value > upper

    WHY IQR OVER Z-SCORE?
        Z-score assumes a normal distribution. Medical data (BP, BMI,
        weight) is often right-skewed. IQR is distribution-agnostic
        and more robust against extreme outliers.

    NOTE: Not all IQR "outliers" are errors. Some are legitimate extreme
    values. We inspect them; Phase 2 decides what to do.
    """
    header("SECTION 11 — OUTLIER DETECTION (IQR METHOD)")

    numeric_cols = ["age", "height", "weight", "ap_hi", "ap_lo"]
    result       = {}

    print(f"  {'Column':<12} {'Q1':>8} {'Q3':>8} {'IQR':>8} "
          f"{'Lower':>10} {'Upper':>10} {'Outliers':>10} {'%':>8}")
    print(f"  {'-'*76}")

    for col in numeric_cols:
        Q1      = df[col].quantile(0.25)
        Q3      = df[col].quantile(0.75)
        iqr     = Q3 - Q1
        lower   = Q1 - 1.5 * iqr
        upper   = Q3 + 1.5 * iqr
        outlier = df[(df[col] < lower) | (df[col] > upper)]
        n_out   = len(outlier)
        p       = n_out / len(df) * 100

        print(f"  {col:<12} {Q1:>8.1f} {Q3:>8.1f} {iqr:>8.1f} "
              f"{lower:>10.1f} {upper:>10.1f} {n_out:>10,} {p:>7.2f}%")

        result[col] = {
            "Q1": Q1, "Q3": Q3, "IQR": iqr,
            "lower_bound": round(lower, 2), "upper_bound": round(upper, 2),
            "outlier_count": n_out, "outlier_pct": round(p, 4),
        }

    print("\n  INTERPRETATION:")
    print("    age    : 4 outliers  — very young patients; likely valid edge cases")
    print("    height : ~519 outliers — mostly biological variation; some errors")
    print("    weight : ~1,819 outliers — right-skewed distribution; clip in Phase 2")
    print("    ap_hi  : ~1,435 outliers — includes corrupt entries (ap_hi=16020)")
    print("    ap_lo  : ~4,632 outliers — includes corrupt entries (ap_lo=11000)")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — DESCRIPTIVE STATISTICS
# ─────────────────────────────────────────────────────────────────────────────

def descriptive_statistics(df: pd.DataFrame) -> None:
    """
    Generate full descriptive statistics for all numeric columns.
    Also computes skewness and kurtosis to understand distribution shape.

    SKEWNESS:
        0 = symmetric, >0 = right-skewed, <0 = left-skewed
        High skewness (>1 or <-1) suggests outliers or non-normal dist.

    KURTOSIS:
        High kurtosis = heavy tails = more outliers relative to normal dist.
    """
    header("SECTION 12 — DESCRIPTIVE STATISTICS")

    numeric = df.select_dtypes(include=[np.number]).copy()
    numeric["age_years"] = numeric["age"] / 365.25
    numeric["bmi"]       = df["weight"] / ((df["height"] / 100) ** 2)

    stats             = numeric.describe().T
    stats["skewness"] = numeric.skew()
    stats["kurtosis"] = numeric.kurt()

    # Drop id — not analytically meaningful
    stats = stats.drop(index=["id"], errors="ignore")

    with pd.option_context("display.float_format", "{:.3f}".format,
                           "display.max_columns", 12, "display.width", 120):
        print(stats.to_string())

    stats_path = REPORTS_DIR / "column_stats.csv"
    stats.to_csv(stats_path)
    print(f"\n  Saved descriptive statistics to: {stats_path}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 13 — DATA QUALITY SUMMARY & PREPROCESSING PLAN
# ─────────────────────────────────────────────────────────────────────────────

def summarize_issues(report: dict) -> None:
    """
    Consolidate all detected issues and produce a clear action plan
    for Phase 2 (Preprocessing).
    """
    header("SECTION 13 — DATA QUALITY ISSUES SUMMARY & PHASE 2 ACTION PLAN")

    issues = []
    bp = report["blood_pressure"]

    if bp["systolic"]["invalid_count"] > 0:
        issues.append(f"Remove {bp['systolic']['invalid_count']:,} records with invalid systolic BP (<60 or >300 mmHg)")
    if bp["diastolic"]["invalid_count"] > 0:
        issues.append(f"Remove {bp['diastolic']['invalid_count']:,} records with invalid diastolic BP (<40 or >200 mmHg)")
    if bp["inverted_bp_count"] > 0:
        issues.append(f"Remove {bp['inverted_bp_count']:,} records with inverted BP (systolic <= diastolic)")

    anthro = report["anthropometrics"]
    if anthro["height"]["invalid_count"] > 0:
        issues.append(f"Remove {anthro['height']['invalid_count']:,} records with invalid height (<100 or >250 cm)")
    if anthro["weight"]["invalid_count"] > 0:
        issues.append(f"Remove {anthro['weight']['invalid_count']:,} records with invalid weight (<30 or >300 kg)")

    dups = report["duplicates"]
    if dups["feature_only_duplicates"] > 0:
        issues.append(f"Remove {dups['feature_only_duplicates']:,} feature-level duplicate records")

    age = report["age"]
    if age["impossible_count"] > 0:
        issues.append(f"Remove {age['impossible_count']:,} records with impossible age")

    print(f"  ISSUES FOUND: {len(issues)}\n")
    for i, issue in enumerate(issues, 1):
        print(f"  [{i}] {issue}")

    total_raw     = report["total_records"]
    approx_removed = (
        bp["systolic"]["invalid_count"] +
        bp["diastolic"]["invalid_count"] +
        bp["inverted_bp_count"] +
        anthro["height"]["invalid_count"] +
        anthro["weight"]["invalid_count"] +
        dups["feature_only_duplicates"] +
        age["impossible_count"]
    )
    print(f"\n  ESTIMATED IMPACT:")
    print(f"    Total raw records     : {total_raw:>7,}")
    print(f"    Records to remove     : ~{approx_removed:>6,}")
    print(f"    Expected clean records: ~{total_raw - approx_removed:>6,}")

    print("\n  PHASE 2 PREPROCESSING STEPS:")
    steps = [
        "1.  Remove records with invalid BP (outside physiological range)",
        "2.  Remove records where systolic BP <= diastolic BP",
        "3.  Remove records with invalid height or weight",
        "4.  Remove feature-level duplicate records",
        "5.  Convert age: days -> years  (age / 365.25)",
        "6.  Engineer BMI: weight / (height/100)^2",
        "7.  Engineer BP Category: Normal / Elevated / Stage1 HTN / Stage2 HTN",
        "8.  Apply IQR-based clipping for remaining BP outliers (not deletion)",
        "9.  Verify class balance after cleaning",
        "10. Save cleaned dataset: backend/data/processed/cardio_clean.csv",
        "11. Save preprocessing report: backend/data/reports/preprocessing_report.json",
    ]
    for step in steps:
        print(f"    {step}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — VISUALISATIONS (9-Panel Dashboard)
# ─────────────────────────────────────────────────────────────────────────────

def generate_visualizations(df: pd.DataFrame) -> None:
    """
    Generate a 9-panel data quality overview chart.
    Each panel answers a specific analytical question.

    PANELS:
        1. Age Distribution        — What is the age profile of the dataset?
        2. Class Balance           — Is the dataset balanced? Can we train directly?
        3. Systolic BP Distribution— Where are the extreme BP values?
        4. Height Distribution     — Are there anthropometric anomalies?
        5. Weight Distribution     — What is the weight distribution shape?
        6. Cholesterol Levels      — How many patients have elevated cholesterol?
        7. Gender Split            — Male/Female ratio in the dataset
        8. Lifestyle Flags         — Prevalence of smoking/drinking/inactivity
        9. BMI Distribution        — What is the BMI profile (derived feature)?
    """
    header("SECTION 14 — GENERATING VISUALIZATIONS")

    df = df.copy()
    df["age_years"] = df["age"] / 365.25
    df["bmi"]       = df["weight"] / ((df["height"] / 100) ** 2)

    # ── Style ──────────────────────────────────────────────────────────────
    sns.set_theme(style="darkgrid", palette="muted", font_scale=1.0)
    BLUE   = "#4C72B0"
    RED    = "#C44E52"
    GREEN  = "#55A868"
    ORANGE = "#DD8452"
    PURPLE = "#8172B2"
    BROWN  = "#937860"
    PINK   = "#DA8BC3"
    CYAN   = "#64B5CD"
    GOLD   = "#CCB974"

    fig = plt.figure(figsize=(20, 16))
    fig.suptitle(
        "CardioCare — Dataset Quality & Distribution Overview\n"
        "Kaggle Cardiovascular Disease Dataset  |  70,000 Records",
        fontsize=15, fontweight="bold", y=0.98
    )
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ── Panel 1: Age Distribution ──────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(df["age_years"], bins=40, color=BLUE, edgecolor="white", linewidth=0.5)
    ax1.set_title("Age Distribution (years)", fontweight="bold")
    ax1.set_xlabel("Age (years)")
    ax1.set_ylabel("Count")
    ax1.axvline(df["age_years"].mean(), color="red", linestyle="--",
                linewidth=1.5, label=f"Mean: {df['age_years'].mean():.1f}")
    ax1.legend(fontsize=8)

    # ── Panel 2: Class Balance ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    vc = df["cardio"].value_counts().sort_index()
    bars = ax2.bar(["No CVD (0)", "CVD (1)"], vc.values, color=[GREEN, RED],
                   edgecolor="white", linewidth=0.5)
    ax2.set_title("Target Variable — Class Balance", fontweight="bold")
    ax2.set_ylabel("Count")
    for bar, val in zip(bars, vc.values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 200,
                 f"{val:,}\n({val/len(df)*100:.1f}%)", ha="center",
                 fontsize=9, fontweight="bold")

    # ── Panel 3: Systolic BP (valid range only) ────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    valid_hi = df[(df["ap_hi"] >= 60) & (df["ap_hi"] <= 300)]["ap_hi"]
    ax3.hist(valid_hi, bins=50, color=ORANGE, edgecolor="white", linewidth=0.5)
    ax3.set_title("Systolic BP — Valid Range (60-300)", fontweight="bold")
    ax3.set_xlabel("Systolic BP (mmHg)")
    ax3.set_ylabel("Count")
    ax3.axvline(120, color="green", linestyle="--", linewidth=1, label="120 (Normal)")
    ax3.axvline(140, color="red", linestyle="--", linewidth=1, label="140 (Stage 2)")
    ax3.legend(fontsize=7)

    # ── Panel 4: Height ────────────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.hist(df["height"], bins=50, color=PURPLE, edgecolor="white", linewidth=0.5)
    ax4.set_title("Height Distribution (cm)", fontweight="bold")
    ax4.set_xlabel("Height (cm)")
    ax4.set_ylabel("Count")

    # ── Panel 5: Weight ────────────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    valid_w = df[(df["weight"] >= 30) & (df["weight"] <= 200)]["weight"]
    ax5.hist(valid_w, bins=50, color=BROWN, edgecolor="white", linewidth=0.5)
    ax5.set_title("Weight Distribution (valid range)", fontweight="bold")
    ax5.set_xlabel("Weight (kg)")
    ax5.set_ylabel("Count")

    # ── Panel 6: Cholesterol ───────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2])
    chol_map = {1: "Normal", 2: "Above\nNormal", 3: "Well Above\nNormal"}
    chol_vc  = df["cholesterol"].value_counts().sort_index()
    ax6.bar([chol_map[k] for k in chol_vc.index], chol_vc.values,
            color=[GREEN, GOLD, RED], edgecolor="white", linewidth=0.5)
    ax6.set_title("Cholesterol Level Distribution", fontweight="bold")
    ax6.set_ylabel("Count")
    for i, v in enumerate(chol_vc.values):
        ax6.text(i, v + 200, f"{v:,}", ha="center", fontsize=8)

    # ── Panel 7: Gender ────────────────────────────────────────────────────
    ax7 = fig.add_subplot(gs[2, 0])
    gender_vc = df["gender"].value_counts().sort_index()
    ax7.bar(["Female (1)", "Male (2)"], gender_vc.values,
            color=[PINK, BLUE], edgecolor="white", linewidth=0.5)
    ax7.set_title("Gender Distribution", fontweight="bold")
    ax7.set_ylabel("Count")
    for i, v in enumerate(gender_vc.values):
        ax7.text(i, v + 200, f"{v:,}\n({v/len(df)*100:.1f}%)", ha="center", fontsize=8)

    # ── Panel 8: Lifestyle Flags ───────────────────────────────────────────
    ax8 = fig.add_subplot(gs[2, 1])
    lifestyle = {
        "Smoker"   : int(df["smoke"].sum()),
        "Drinker"  : int(df["alco"].sum()),
        "Active"   : int(df["active"].sum()),
        "Inactive" : int((df["active"] == 0).sum()),
    }
    colors = [RED, ORANGE, GREEN, PURPLE]
    ax8.bar(lifestyle.keys(), lifestyle.values(), color=colors,
            edgecolor="white", linewidth=0.5)
    ax8.set_title("Lifestyle Flags", fontweight="bold")
    ax8.set_ylabel("Count")
    for i, v in enumerate(lifestyle.values()):
        ax8.text(i, v + 200, f"{v:,}", ha="center", fontsize=8)

    # ── Panel 9: BMI ───────────────────────────────────────────────────────
    ax9 = fig.add_subplot(gs[2, 2])
    valid_bmi = df[(df["bmi"] >= 10) & (df["bmi"] <= 60)]["bmi"]
    ax9.hist(valid_bmi, bins=60, color=CYAN, edgecolor="white", linewidth=0.5)
    ax9.axvline(18.5, color="blue", linestyle="--", linewidth=1, label="Underweight")
    ax9.axvline(25,   color="green", linestyle="--", linewidth=1, label="Overweight")
    ax9.axvline(30,   color="red", linestyle="--", linewidth=1, label="Obese")
    ax9.set_title("BMI Distribution (derived feature)", fontweight="bold")
    ax9.set_xlabel("BMI")
    ax9.set_ylabel("Count")
    ax9.legend(fontsize=7)

    # ── Save ───────────────────────────────────────────────────────────────
    plot_path = REPORTS_DIR / "data_quality_overview.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved visualization: {plot_path}")


# ─────────────────────────────────────────────────────────────────────────────
# SAVE REPORT
# ─────────────────────────────────────────────────────────────────────────────

def save_report(report: dict) -> None:
    """Persist the full data quality report as JSON."""
    path = REPORTS_DIR / "data_quality_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Saved data quality report: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# PLACEMENT INTERVIEW QUESTIONS (printed at end of script)
# ─────────────────────────────────────────────────────────────────────────────

def print_interview_questions() -> None:
    header("PHASE 1 — PLACEMENT INTERVIEW QUESTIONS")

    qnas = [
        (
            "Q1. Why did you perform data quality analysis before loading data into MongoDB?",
            """Loading dirty data into a production database creates cascading problems:
       - Invalid records corrupt analytics queries (e.g., average BP becomes meaningless)
       - ML models trained on dirty data learn incorrect patterns
       - Removing records from MongoDB later is much harder than cleaning a CSV
       This is called 'fail early' — catch problems at the data ingestion boundary.
       In production, this step is formalized as a 'data contract'."""
        ),
        (
            "Q2. The age column has values like 18,393. How did you detect this is in days?",
            """By computing min_age_years = 10798 / 365.25 = 29.6 years and
       max_age_years = 23713 / 365.25 = 64.9 years. These are realistic for
       a cardiovascular disease dataset (CVD is rare in young adults). A value
       of 18,393 in years would be biologically impossible, immediately revealing
       that the unit is days."""
        ),
        (
            "Q3. What is the difference between full-row duplicates and feature-level duplicates?",
            """Full-row duplicates: Every column (including 'id') is identical.
       Feature-level duplicates: The feature columns are identical but 'id' differs.
       The 'id' is just a row number assigned at data collection — two different
       row numbers can represent the same patient recorded twice. We found 24
       feature-level duplicates. Removing them prevents the ML model from seeing
       the same patient twice (which would artificially inflate training accuracy)."""
        ),
        (
            "Q4. Why is IQR preferred over Z-score for outlier detection in medical data?",
            """Z-score assumes a normal (Gaussian) distribution. Medical variables like
       blood pressure, BMI, and weight are typically right-skewed. IQR is a
       non-parametric, distribution-agnostic method — it only uses the 25th and
       75th percentiles, making it robust to extreme outliers that already exist
       in the data. For this dataset, ap_hi has extreme outliers (16,020 mmHg)
       that would distort the Z-score mean and standard deviation, making Z-score
       useless for detecting the moderate outliers we actually care about."""
        ),
        (
            "Q5. The dataset is nearly 50/50 balanced. What advantage does this give us?",
            """With a 50/50 balance (35,021 No-CVD vs 34,979 CVD):
       - Standard accuracy is a meaningful metric (not misleading)
       - We don't need SMOTE or class_weight='balanced'
       - The model cannot 'cheat' by predicting only one class
       - Cross-validation fold distributions are reliable
       In contrast, with a 95/5 imbalance, a model predicting 'No CVD' always
       would score 95% accuracy while being clinically useless."""
        ),
    ]

    for q, a in qnas:
        print(f"\n  {q}")
        print(f"  A: {a}\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n+------------------------------------------------------------------+")
    print("|  CardioCare  |  Phase 1: Dataset Inspection                       |")
    print("|  Project     : Cardiovascular Risk Analytics Platform             |")
    print("|  Dataset     : Kaggle Cardiovascular Disease (70K records)        |")
    print("+------------------------------------------------------------------+")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print(f"  Dataset  : {DATASET_PATH}\n")

    # ── Load ──────────────────────────────────────────────────────────────
    df = load_dataset()

    # ── Run all inspections ───────────────────────────────────────────────
    structure   = inspect_structure(df)
    missing     = check_missing_values(df)
    duplicates  = check_duplicates(df)
    unique_vals = check_unique_values(df)
    age_info    = analyze_age(df)
    bp_info     = analyze_blood_pressure(df)
    anthro_info = analyze_anthropometrics(df)
    cat_info    = analyze_categoricals(df)
    target_info = analyze_target(df)
    outlier_info= detect_outliers(df)
    descriptive_statistics(df)

    # ── Build report dict ─────────────────────────────────────────────────
    report = {
        "generated_at"    : datetime.now().isoformat(),
        "dataset_file"    : str(DATASET_PATH),
        "total_records"   : len(df),
        "total_columns"   : len(df.columns),
        "structure"       : structure,
        "missing_values"  : missing,
        "duplicates"      : duplicates,
        "unique_values"   : unique_vals,
        "age"             : age_info,
        "blood_pressure"  : bp_info,
        "anthropometrics" : anthro_info,
        "categoricals"    : cat_info,
        "target"          : target_info,
        "outliers_iqr"    : outlier_info,
    }

    # ── Summarize & plan ──────────────────────────────────────────────────
    summarize_issues(report)

    # ── Save outputs ──────────────────────────────────────────────────────
    generate_visualizations(df)
    save_report(report)

    # ── Interview questions ───────────────────────────────────────────────
    print_interview_questions()

    # ── Final summary ─────────────────────────────────────────────────────
    header("PHASE 1 COMPLETE")
    print("  Generated files:")
    print(f"    {REPORTS_DIR / 'data_quality_report.json'}")
    print(f"    {REPORTS_DIR / 'column_stats.csv'}")
    print(f"    {REPORTS_DIR / 'data_quality_overview.png'}")
    print("\n  Next Step: Confirm and proceed to PHASE 2 — Data Preprocessing Pipeline")
    print("  (Clean the dataset and prepare it for MongoDB ingestion and ML training)\n")


if __name__ == "__main__":
    main()
