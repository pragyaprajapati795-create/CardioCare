"""
CardioCare — Analytics Routes (Phase 2)
========================================
All aggregations run inside MongoDB. No full-table scans into Python memory.
"""

from fastapi import APIRouter, HTTPException
from app.database.mongodb import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ─── helper ───────────────────────────────────────────────────────────────────
def _db():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    return db


# ── 1 ─────────────────────────────────────────────────────────────────────────
@router.get("/overview")
def get_analytics_overview():
    db = _db()

    total = db.patients.count_documents({})
    disease = db.patients.count_documents({"cardio": 1})
    non_disease = total - disease
    pct = round((disease / total * 100) if total > 0 else 0, 1)

    agg = list(db.patients.aggregate([{
        "$group": {
            "_id": None,
            "avgAge":    {"$avg": "$age_years"},
            "avgSys":    {"$avg": "$systolic_bp"},
            "avgDia":    {"$avg": "$diastolic_bp"},
            "avgBmi":    {"$avg": "$bmi"},
        }
    }]))

    s = agg[0] if agg else {}

    return {
        "totalPatients":       total,
        "diseaseCases":        disease,
        "nonDiseaseCases":     non_disease,
        "diseasePercentage":   pct,
        "averageAge":          round(s.get("avgAge", 0), 1),
        "averageSystolicBP":   round(s.get("avgSys", 0), 1),
        "averageDiastolicBP":  round(s.get("avgDia", 0), 1),
        "averageBMI":          round(s.get("avgBmi", 0), 1),
    }


# ── 2 ─────────────────────────────────────────────────────────────────────────
@router.get("/age")
def get_age_distribution():
    db = _db()
    raw = list(db.patients.aggregate([
        {"$bucket": {
            "groupBy":    "$age_years",
            "boundaries": [18, 31, 41, 51, 61, 71, 120],
            "default":    "Other",
            "output": {
                "total":   {"$sum": 1},
                "disease": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
            },
        }}
    ]))
    labels = {18: "18–30", 31: "31–40", 41: "41–50", 51: "51–60", 61: "61–70", 71: "70+"}
    return [
        {"name": labels.get(r["_id"], str(r["_id"])),
         "total": r["total"], "disease": r["disease"]}
        for r in raw
    ]


# ── 3 ─────────────────────────────────────────────────────────────────────────
@router.get("/gender")
def get_gender_distribution():
    db = _db()
    raw = list(db.patients.aggregate([
        {"$group": {
            "_id":            "$gender",
            "total":          {"$sum": 1},
            "diseaseCases":   {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
            "nonDiseaseCases":{"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]))
    label = {1: "Female", 2: "Male"}
    return [
        {"name": label.get(r["_id"], f"Gender {r['_id']}"),
         "total": r["total"],
         "diseaseCases": r["diseaseCases"],
         "nonDiseaseCases": r["nonDiseaseCases"]}
        for r in raw
    ]


# ── 4 ─────────────────────────────────────────────────────────────────────────
@router.get("/cholesterol")
def get_cholesterol_distribution():
    db = _db()
    raw = list(db.patients.aggregate([
        {"$group": {
            "_id":            "$cholesterol",
            "total":          {"$sum": 1},
            "diseaseCases":   {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]))
    label = {1: "Normal", 2: "Above Normal", 3: "Well Above Normal"}
    return [
        {"name": label.get(r["_id"], str(r["_id"])),
         "total": r["total"], "diseaseCases": r["diseaseCases"]}
        for r in raw
    ]


# ── 5 ─────────────────────────────────────────────────────────────────────────
@router.get("/glucose")
def get_glucose_distribution():
    db = _db()
    raw = list(db.patients.aggregate([
        {"$group": {
            "_id":          "$glucose",
            "total":        {"$sum": 1},
            "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]))
    label = {1: "Normal", 2: "Above Normal", 3: "Well Above Normal"}
    return [
        {"name": label.get(r["_id"], str(r["_id"])),
         "total": r["total"], "diseaseCases": r["diseaseCases"]}
        for r in raw
    ]


# ── 6 ─────────────────────────────────────────────────────────────────────────
@router.get("/lifestyle")
def get_lifestyle_analytics():
    db = _db()

    def _binary_breakdown(field, labels):
        raw = list(db.patients.aggregate([
            {"$group": {
                "_id":            f"${field}",
                "total":          {"$sum": 1},
                "diseaseCases":   {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases":{"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]))
        return [
            {"name": labels.get(r["_id"], str(r["_id"])),
             "total": r["total"],
             "diseaseCases": r["diseaseCases"],
             "nonDiseaseCases": r["nonDiseaseCases"]}
            for r in raw
        ]

    return {
        "smoking":          _binary_breakdown("smoking",          {0: "Non-Smoker",  1: "Smoker"}),
        "alcohol":          _binary_breakdown("alcohol",          {0: "No Alcohol",  1: "Drinks Alcohol"}),
        "physicalActivity": _binary_breakdown("physical_activity",{0: "Inactive",    1: "Active"}),
    }


# ── 7 ─────────────────────────────────────────────────────────────────────────
@router.get("/bmi")
def get_bmi_distribution():
    db = _db()
    raw = list(db.patients.aggregate([
        {"$addFields": {"bmiCat": {"$switch": {"branches": [
            {"case": {"$lt": ["$bmi", 18.5]}, "then": "Underweight"},
            {"case": {"$lt": ["$bmi", 25.0]}, "then": "Normal"},
            {"case": {"$lt": ["$bmi", 30.0]}, "then": "Overweight"},
        ], "default": "Obese"}}}},
        {"$group": {
            "_id":          "$bmiCat",
            "total":        {"$sum": 1},
            "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
        }},
        {"$sort": {"total": -1}},
    ]))
    return [{"name": r["_id"], "total": r["total"], "diseaseCases": r["diseaseCases"]} for r in raw]


# ── 8 ─────────────────────────────────────────────────────────────────────────
@router.get("/blood-pressure")
def get_blood_pressure_distribution():
    db = _db()
    raw = list(db.patients.aggregate([
        {"$group": {
            "_id":            "$bp_category",
            "total":          {"$sum": 1},
            "diseaseCases":   {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
            "nonDiseaseCases":{"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
        }},
        {"$sort": {"total": -1}},
    ]))
    return [
        {"name": r["_id"] or "Unknown",
         "total": r["total"],
         "diseaseCases": r["diseaseCases"],
         "nonDiseaseCases": r["nonDiseaseCases"]}
        for r in raw
    ]
