"""
CardioCare — Query Lab Backend (Phase 2)
========================================
Secure, whitelist-only MongoDB query registry.
Arbitrary MongoDB code from the frontend is NEVER executed.
Only approved query IDs from QUERY_REGISTRY are permitted.
"""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.mongodb import get_db

router = APIRouter(prefix="/query-lab", tags=["Query Lab"])


class QueryRequest(BaseModel):
    query_id: str


# ─────────────────────────────────────────────────────────────────────────────
# QUERY REGISTRY  — every entry is a pre-approved, server-side MongoDB operation
# Frontend sends ONLY a query_id string; the server resolves the operation.
# ─────────────────────────────────────────────────────────────────────────────
QUERY_REGISTRY = {

    # ── 1 ──────────────────────────────────────────────────────────────────
    "total_patients": {
        "name": "Total Patients",
        "description": "Counts all patient documents in the collection.",
        "operation": "countDocuments",
        "operators": [],
        "explanation": (
            "Uses MongoDB countDocuments({}) to return the total number of "
            "patient records in the collection. This is a fast O(log n) operation "
            "that uses the collection's metadata."
        ),
        "code": "db.patients.countDocuments({})",
        "execute": lambda db: [{"total_patients": db.patients.count_documents({})}],
    },

    # ── 2 ──────────────────────────────────────────────────────────────────
    "cardio_cases": {
        "name": "Cardiovascular Disease Cases",
        "description": "Counts patients diagnosed with cardiovascular disease (cardio = 1).",
        "operation": "countDocuments",
        "operators": [],
        "explanation": (
            "Applies a filter {cardio: 1} to countDocuments. "
            "The 'cardio' index (created in Phase 1) makes this lookup very fast."
        ),
        "code": 'db.patients.countDocuments({ "cardio": 1 })',
        "execute": lambda db: [{"cardio_cases": db.patients.count_documents({"cardio": 1})}],
    },

    # ── 3 ──────────────────────────────────────────────────────────────────
    "non_cardio_cases": {
        "name": "Non-Cardiovascular Disease Cases",
        "description": "Counts patients with no cardiovascular disease (cardio = 0).",
        "operation": "countDocuments",
        "operators": [],
        "explanation": (
            "Applies filter {cardio: 0}. Together with Query 2, these two values "
            "should sum to the total patient count, verifying dataset integrity."
        ),
        "code": 'db.patients.countDocuments({ "cardio": 0 })',
        "execute": lambda db: [{"non_cardio_cases": db.patients.count_documents({"cardio": 0})}],
    },

    # ── 4 ──────────────────────────────────────────────────────────────────
    "average_age": {
        "name": "Average Age of Patients",
        "description": "Calculates the mean age across all patients using $group and $avg.",
        "operation": "aggregate",
        "operators": ["$group", "$avg", "$round"],
        "explanation": (
            "$group with _id: null collapses all documents into a single group. "
            "$avg then computes the arithmetic mean of age_years across that group. "
            "$round limits the result to 2 decimal places."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: { _id: null, averageAge: { $avg: '$age_years' } } },\n"
            "  { $project: { averageAge: { $round: ['$averageAge', 2] }, _id: 0 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {"_id": None, "averageAge": {"$avg": "$age_years"}}},
            {"$project": {"averageAge": {"$round": ["$averageAge", 2]}, "_id": 0}},
        ])),
    },

    # ── 5 ──────────────────────────────────────────────────────────────────
    "gender_distribution": {
        "name": "Gender Distribution",
        "description": "Groups all patients by gender and counts each group.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$sort", "$project"],
        "explanation": (
            "$group groups documents by the 'gender' field. "
            "$sum: 1 increments a counter for each document in the group. "
            "$sort arranges results in ascending order. "
            "In this dataset: 1 = Female, 2 = Male."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: { _id: '$gender', total: { $sum: 1 } } },\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {"_id": "$gender", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$project": {
                "gender": {"$cond": [{"$eq": ["$_id", 1]}, "Female", "Male"]},
                "total": 1, "_id": 0
            }},
        ])),
    },

    # ── 6 ──────────────────────────────────────────────────────────────────
    "gender_vs_disease": {
        "name": "Gender vs Cardiovascular Disease",
        "description": "For each gender, counts total patients, disease cases, and non-disease cases.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$cond", "$eq", "$sort", "$project"],
        "explanation": (
            "$cond acts as an IF-THEN-ELSE inside the aggregation pipeline. "
            "When cardio equals 1, it adds 1 to diseaseCases; otherwise to nonDiseaseCases. "
            "This lets us split each gender's count into two disease-status buckets in a single pass."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: {\n"
            "      _id: '$gender',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } },\n"
            "      nonDiseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 0] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {
                "_id": "$gender",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "gender": {"$cond": [{"$eq": ["$_id", 1]}, "Female", "Male"]},
                "total": 1, "diseaseCases": 1, "nonDiseaseCases": 1, "_id": 0
            }},
        ])),
    },

    # ── 7 ──────────────────────────────────────────────────────────────────
    "cholesterol_distribution": {
        "name": "Cholesterol Distribution",
        "description": "Groups patients by cholesterol level (1=Normal, 2=Above Normal, 3=Well Above Normal).",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$sort", "$project"],
        "explanation": (
            "Cholesterol is encoded as: 1=Normal, 2=Above Normal, 3=Well Above Normal. "
            "$group with _id: '$cholesterol' creates one bucket per level. "
            "The $project stage maps numeric codes to readable labels."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: { _id: '$cholesterol', total: { $sum: 1 } } },\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {"_id": "$cholesterol", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$project": {
                "level": {"$switch": {"branches": [
                    {"case": {"$eq": ["$_id", 1]}, "then": "Normal"},
                    {"case": {"$eq": ["$_id", 2]}, "then": "Above Normal"},
                    {"case": {"$eq": ["$_id", 3]}, "then": "Well Above Normal"},
                ], "default": "Unknown"}},
                "total": 1, "_id": 0
            }},
        ])),
    },

    # ── 8 ──────────────────────────────────────────────────────────────────
    "cholesterol_vs_disease": {
        "name": "Cholesterol vs Cardiovascular Disease",
        "description": "Groups patients by cholesterol level and splits counts by disease status.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$cond", "$eq", "$switch", "$sort"],
        "explanation": (
            "Combines grouping and conditional counting in a single pipeline. "
            "$cond checks the value of 'cardio' for each document and routes the count "
            "to either 'diseaseCases' or 'nonDiseaseCases'. "
            "This demonstrates MongoDB's ability to perform multi-dimensional aggregation."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: {\n"
            "      _id: '$cholesterol',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } },\n"
            "      nonDiseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 0] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {
                "_id": "$cholesterol",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "level": {"$switch": {"branches": [
                    {"case": {"$eq": ["$_id", 1]}, "then": "Normal"},
                    {"case": {"$eq": ["$_id", 2]}, "then": "Above Normal"},
                    {"case": {"$eq": ["$_id", 3]}, "then": "Well Above Normal"},
                ], "default": "Unknown"}},
                "total": 1, "diseaseCases": 1, "nonDiseaseCases": 1, "_id": 0
            }},
        ])),
    },

    # ── 9 ──────────────────────────────────────────────────────────────────
    "glucose_distribution": {
        "name": "Glucose Distribution",
        "description": "Groups patients by glucose level (1=Normal, 2=Above Normal, 3=Well Above Normal).",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$sort", "$switch", "$project"],
        "explanation": (
            "Glucose is encoded like cholesterol: 1=Normal, 2=Above Normal, 3=Well Above Normal. "
            "$group buckets each document by glucose value, $sum counts them, "
            "and $project maps numeric codes to human-readable labels."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: { _id: '$glucose', total: { $sum: 1 } } },\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {"_id": "$glucose", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$project": {
                "level": {"$switch": {"branches": [
                    {"case": {"$eq": ["$_id", 1]}, "then": "Normal"},
                    {"case": {"$eq": ["$_id", 2]}, "then": "Above Normal"},
                    {"case": {"$eq": ["$_id", 3]}, "then": "Well Above Normal"},
                ], "default": "Unknown"}},
                "total": 1, "_id": 0
            }},
        ])),
    },

    # ── 10 ─────────────────────────────────────────────────────────────────
    "smoking_vs_disease": {
        "name": "Smoking vs Cardiovascular Disease",
        "description": "Compares disease rates between smokers and non-smokers.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$cond", "$eq", "$project"],
        "explanation": (
            "Groups by the 'smoking' binary field (0=No, 1=Yes). "
            "Within each group, $cond conditionally counts disease and non-disease cases. "
            "Useful for studying the correlation between lifestyle and cardiovascular risk."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: {\n"
            "      _id: '$smoking',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {
                "_id": "$smoking",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "status": {"$cond": [{"$eq": ["$_id", 1]}, "Smoker", "Non-Smoker"]},
                "total": 1, "diseaseCases": 1, "nonDiseaseCases": 1, "_id": 0
            }},
        ])),
    },

    # ── 11 ─────────────────────────────────────────────────────────────────
    "alcohol_vs_disease": {
        "name": "Alcohol Consumption vs Cardiovascular Disease",
        "description": "Compares disease rates between alcohol consumers and non-consumers.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$cond", "$eq", "$project"],
        "explanation": (
            "Identical structure to the smoking query but grouped by 'alcohol' (0=No, 1=Yes). "
            "Demonstrates reuse of the same aggregation pattern for different lifestyle fields."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: {\n"
            "      _id: '$alcohol',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {
                "_id": "$alcohol",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "status": {"$cond": [{"$eq": ["$_id", 1]}, "Drinks Alcohol", "No Alcohol"]},
                "total": 1, "diseaseCases": 1, "nonDiseaseCases": 1, "_id": 0
            }},
        ])),
    },

    # ── 12 ─────────────────────────────────────────────────────────────────
    "physical_activity_vs_disease": {
        "name": "Physical Activity vs Cardiovascular Disease",
        "description": "Compares disease rates between physically active and inactive patients.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$cond", "$eq", "$project"],
        "explanation": (
            "Groups by 'physical_activity' (0=Inactive, 1=Active). "
            "Physical activity is a key protective factor against cardiovascular disease. "
            "This query lets the data confirm or challenge that hypothesis."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: {\n"
            "      _id: '$physical_activity',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { _id: 1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {
                "_id": "$physical_activity",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "status": {"$cond": [{"$eq": ["$_id", 1]}, "Physically Active", "Inactive"]},
                "total": 1, "diseaseCases": 1, "nonDiseaseCases": 1, "_id": 0
            }},
        ])),
    },

    # ── 13 ─────────────────────────────────────────────────────────────────
    "age_group_analysis": {
        "name": "Age Group Analysis",
        "description": "Divides patients into age brackets and counts total and disease cases per bracket.",
        "operation": "aggregate",
        "operators": ["$bucket", "$sum", "$cond", "$eq"],
        "explanation": (
            "$bucket is a powerful MongoDB operator that automatically places each document "
            "into predefined numeric ranges (boundaries). "
            "Here we split age_years into 6 brackets: 18-30, 31-40, 41-50, 51-60, 61-70, 70+. "
            "Within each bucket, $cond counts disease vs non-disease cases. "
            "This is more efficient than loading all records into Python and grouping manually."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $bucket: {\n"
            "      groupBy: '$age_years',\n"
            "      boundaries: [18, 31, 41, 51, 61, 71, 120],\n"
            "      default: 'Other',\n"
            "      output: {\n"
            "        total: { $sum: 1 },\n"
            "        disease: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } }\n"
            "      }\n"
            "  }}\n"
            "])"
        ),
        "execute": lambda db: _age_group_execute(db),
    },

    # ── 14 ─────────────────────────────────────────────────────────────────
    "bmi_analysis": {
        "name": "BMI Category Analysis",
        "description": "Categorises patients by WHO BMI classification and counts disease cases per category.",
        "operation": "aggregate",
        "operators": ["$addFields", "$switch", "$group", "$sum", "$cond", "$eq", "$sort"],
        "explanation": (
            "$addFields creates a new computed field 'bmi_category' on each document without modifying the stored data. "
            "$switch evaluates multiple conditions (like a CASE statement in SQL): "
            "Underweight <18.5, Normal 18.5-24.9, Overweight 25-29.9, Obese 30+. "
            "The subsequent $group then aggregates on this computed field — "
            "demonstrating MongoDB's ability to group on derived/computed attributes."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $addFields: { bmi_category: { $switch: { branches: [\n"
            "      { case: { $lt: ['$bmi', 18.5] }, then: 'Underweight' },\n"
            "      { case: { $lt: ['$bmi', 25.0] }, then: 'Normal' },\n"
            "      { case: { $lt: ['$bmi', 30.0] }, then: 'Overweight' }\n"
            "    ], default: 'Obese' } } } },\n"
            "  { $group: { _id: '$bmi_category',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { total: -1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$addFields": {"bmi_category": {"$switch": {"branches": [
                {"case": {"$lt": ["$bmi", 18.5]}, "then": "Underweight"},
                {"case": {"$lt": ["$bmi", 25.0]}, "then": "Normal"},
                {"case": {"$lt": ["$bmi", 30.0]}, "then": "Overweight"},
            ], "default": "Obese"}}}},
            {"$group": {
                "_id": "$bmi_category",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
            }},
            {"$sort": {"total": -1}},
            {"$project": {"category": "$_id", "total": 1, "diseaseCases": 1, "_id": 0}},
        ])),
    },

    # ── 15 ─────────────────────────────────────────────────────────────────
    "blood_pressure_analysis": {
        "name": "Blood Pressure Category Analysis",
        "description": "Groups patients by the existing bp_category field and counts disease cases.",
        "operation": "aggregate",
        "operators": ["$group", "$sum", "$cond", "$eq", "$sort"],
        "explanation": (
            "The dataset already contains a validated 'bp_category' field computed during the "
            "Phase 2 data cleaning step (e.g., Normal, Elevated, Stage1_HTN, Stage2_HTN, Crisis). "
            "$group aggregates on this categorical string field directly. "
            "This shows that MongoDB can group by both numeric and string fields equally well."
        ),
        "code": (
            "db.patients.aggregate([\n"
            "  { $group: {\n"
            "      _id: '$bp_category',\n"
            "      total: { $sum: 1 },\n"
            "      diseaseCases: { $sum: { $cond: [{ $eq: ['$cardio', 1] }, 1, 0] } }\n"
            "  }},\n"
            "  { $sort: { total: -1 } }\n"
            "])"
        ),
        "execute": lambda db: list(db.patients.aggregate([
            {"$group": {
                "_id": "$bp_category",
                "total": {"$sum": 1},
                "diseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
                "nonDiseaseCases": {"$sum": {"$cond": [{"$eq": ["$cardio", 0]}, 1, 0]}},
            }},
            {"$sort": {"total": -1}},
            {"$project": {"category": "$_id", "total": 1, "diseaseCases": 1, "nonDiseaseCases": 1, "_id": 0}},
        ])),
    },
}


# ── helper: age group (needs label mapping) ────────────────────────────────
def _age_group_execute(db):
    raw = list(db.patients.aggregate([
        {"$bucket": {
            "groupBy": "$age_years",
            "boundaries": [18, 31, 41, 51, 61, 71, 120],
            "default": "Other",
            "output": {
                "total": {"$sum": 1},
                "disease": {"$sum": {"$cond": [{"$eq": ["$cardio", 1]}, 1, 0]}},
            },
        }}
    ]))
    labels = {18: "18–30", 31: "31–40", 41: "41–50", 51: "51–60", 61: "61–70", 71: "70+"}
    out = []
    for row in raw:
        key = row["_id"]
        out.append({
            "ageGroup": labels.get(key, str(key)),
            "total": row["total"],
            "disease": row["disease"],
            "nonDisease": row["total"] - row["disease"],
        })
    return out


# ── serialize: convert any non-JSON-safe MongoDB types ────────────────────
def _serialize(obj):
    """Recursively make MongoDB result JSON-safe."""
    from bson import ObjectId
    import datetime
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/queries")
def get_available_queries():
    """Return the list of all approved query IDs with name and description."""
    return [
        {
            "id": qid,
            "name": q["name"],
            "description": q["description"],
            "operation": q["operation"],
            "operators": q["operators"],
        }
        for qid, q in QUERY_REGISTRY.items()
    ]


@router.post("/run")
def run_query(request: QueryRequest):
    """
    Execute a whitelisted MongoDB query by ID.
    Frontend sends only { query_id: "..." } — no raw MongoDB code is accepted.
    """
    if request.query_id not in QUERY_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "query_id": request.query_id,
                "error": f"Unknown query_id '{request.query_id}'. Use GET /queries for valid IDs.",
            },
        )

    db = get_db()
    q = QUERY_REGISTRY[request.query_id]

    start = time.perf_counter()
    try:
        raw_result = q["execute"](db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "query_id": request.query_id,
                "error": "Query execution failed. Database may be unavailable.",
            },
        )
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    result = _serialize(raw_result)

    return {
        "success": True,
        "query_id": request.query_id,
        "query_name": q["name"],
        "collection": "patients",
        "operation": q["operation"],
        "operators": q["operators"],
        "description": q["description"],
        "explanation": q.get("explanation", ""),
        "code": q["code"],
        "execution_time_ms": elapsed_ms,
        "result_count": len(result),
        "result": result,
    }
