"""
CardioCare — Patient Management API (Phase 3)
=============================================
Production-quality CRUD with:
  - server-side pagination (max 100 per page)
  - server-side search by patient_id
  - allowlisted filters (no injection possible)
  - allowlisted sort fields
  - full Pydantic validation with realistic ranges
  - consistent {success, data/error} envelope
  - no full-collection Python scans
"""

import uuid
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.database.mongodb import get_db

router = APIRouter(prefix="/patients", tags=["Patients"])

# ── Allowlists (prevent injection / arbitrary field access) ──────────────────

SORTABLE_FIELDS = {
    "patient_id", "age_years", "bmi",
    "systolic_bp", "diastolic_bp", "cholesterol", "glucose",
}

FILTERABLE_INT_FIELDS = {
    "gender":            (1, 2),
    "cardio":            (0, 1),
    "cholesterol":       (1, 3),
    "glucose":           (1, 3),
    "smoking":           (0, 1),
    "alcohol":           (0, 1),
    "physical_activity": (0, 1),
}


# ── Pydantic models ──────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    """Input model for creating a new patient. All ranges derived from the actual dataset."""

    age_years: float = Field(..., ge=1, le=120, description="Age in years (1–120)")
    gender: int = Field(..., ge=1, le=2, description="1=Female, 2=Male")
    height: int = Field(..., ge=50, le=250, description="Height in cm (50–250)")
    weight: float = Field(..., ge=10, le=300, description="Weight in kg (10–300)")
    systolic_bp: int = Field(..., ge=60, le=300, description="Systolic BP in mmHg")
    diastolic_bp: int = Field(..., ge=40, le=200, description="Diastolic BP in mmHg")
    cholesterol: int = Field(..., ge=1, le=3, description="1=Normal, 2=Above Normal, 3=Well Above Normal")
    glucose: int = Field(..., ge=1, le=3, description="1=Normal, 2=Above Normal, 3=Well Above Normal")
    smoking: int = Field(..., ge=0, le=1, description="0=No, 1=Yes")
    alcohol: int = Field(..., ge=0, le=1, description="0=No, 1=Yes")
    physical_activity: int = Field(..., ge=0, le=1, description="0=Inactive, 1=Active")
    cardio: int = Field(0, ge=0, le=1, description="0=No disease, 1=Disease (default 0)")

    @model_validator(mode="after")
    def systolic_above_diastolic(self) -> "PatientCreate":
        if self.systolic_bp <= self.diastolic_bp:
            raise ValueError("systolic_bp must be greater than diastolic_bp")
        return self


class PatientUpdate(BaseModel):
    """Partial update — all fields optional, same validation ranges."""

    age_years: Optional[float] = Field(None, ge=1, le=120)
    gender: Optional[int] = Field(None, ge=1, le=2)
    height: Optional[int] = Field(None, ge=50, le=250)
    weight: Optional[float] = Field(None, ge=10, le=300)
    systolic_bp: Optional[int] = Field(None, ge=60, le=300)
    diastolic_bp: Optional[int] = Field(None, ge=40, le=200)
    cholesterol: Optional[int] = Field(None, ge=1, le=3)
    glucose: Optional[int] = Field(None, ge=1, le=3)
    smoking: Optional[int] = Field(None, ge=0, le=1)
    alcohol: Optional[int] = Field(None, ge=0, le=1)
    physical_activity: Optional[int] = Field(None, ge=0, le=1)
    cardio: Optional[int] = Field(None, ge=0, le=1)


# ── helpers ──────────────────────────────────────────────────────────────────

def _bp_category(systolic: int, diastolic: int) -> str:
    if systolic < 120 and diastolic < 80:
        return "Normal"
    if systolic < 130 and diastolic < 80:
        return "Elevated"
    if systolic < 140 or diastolic < 90:
        return "Stage1_HTN"
    if systolic >= 180 or diastolic >= 120:
        return "Crisis"
    return "Stage2_HTN"


def _bmi(weight: float, height: int) -> float:
    if height <= 0:
        return 0.0
    return round(weight / ((height / 100) ** 2), 2)


def _success(data):
    return {"success": True, "data": data}


def _not_found(patient_id: str):
    raise HTTPException(
        status_code=404,
        detail={"success": False, "error": {
            "code": "PATIENT_NOT_FOUND",
            "message": f"Patient '{patient_id}' was not found.",
        }},
    )


def _conflict(patient_id: str):
    raise HTTPException(
        status_code=409,
        detail={"success": False, "error": {
            "code": "PATIENT_ALREADY_EXISTS",
            "message": f"A patient with ID '{patient_id}' already exists.",
        }},
    )


# ── PATIENT LIST  GET /api/v1/patients ───────────────────────────────────────

@router.get(
    "/",
    summary="List patients with pagination, search, filters and sorting",
    response_description="Paginated patient list",
)
def list_patients(
    page:              int  = Query(1,    ge=1,    description="Page number (starts at 1)"),
    limit:             int  = Query(20,   ge=1, le=100, description="Records per page (max 100)"),
    search:            Optional[str]  = Query(None, description="Search by patient_id prefix"),
    # int filters
    gender:            Optional[int]  = Query(None, ge=1, le=2),
    cardio:            Optional[int]  = Query(None, ge=0, le=1),
    cholesterol:       Optional[int]  = Query(None, ge=1, le=3),
    glucose:           Optional[int]  = Query(None, ge=1, le=3),
    smoking:           Optional[int]  = Query(None, ge=0, le=1),
    alcohol:           Optional[int]  = Query(None, ge=0, le=1),
    physical_activity: Optional[int]  = Query(None, ge=0, le=1),
    # range filters
    min_age:           Optional[float] = Query(None, ge=1),
    max_age:           Optional[float] = Query(None, le=120),
    min_bmi:           Optional[float] = Query(None, ge=5),
    max_bmi:           Optional[float] = Query(None, le=80),
    min_systolic:      Optional[int]   = Query(None, ge=60),
    max_systolic:      Optional[int]   = Query(None, le=300),
    min_diastolic:     Optional[int]   = Query(None, ge=40),
    max_diastolic:     Optional[int]   = Query(None, le=200),
    # sorting
    sort_by:           Optional[str]   = Query(None, description=f"Sort field. Allowed: {SORTABLE_FIELDS}"),
    sort_order:        Optional[str]   = Query("asc", pattern="^(asc|desc)$"),
):
    db = get_db()

    # ── Build MongoDB filter ─────────────────────────────────────────────────
    mongo_filter = {}

    # search: prefix match on patient_id (uses the patient_id index)
    if search:
        mongo_filter["patient_id"] = {"$regex": f"^{search}", "$options": "i"}

    # int equality filters (allowlisted — no user-supplied field name reaches MongoDB)
    for field, value in [
        ("gender", gender), ("cardio", cardio), ("cholesterol", cholesterol),
        ("glucose", glucose), ("smoking", smoking), ("alcohol", alcohol),
        ("physical_activity", physical_activity),
    ]:
        if value is not None:
            lo, hi = FILTERABLE_INT_FIELDS[field]
            if not (lo <= value <= hi):
                raise HTTPException(
                    status_code=422,
                    detail={"success": False, "error": {
                        "code": "INVALID_FILTER",
                        "message": f"'{field}' must be between {lo} and {hi}.",
                    }},
                )
            mongo_filter[field] = value

    # range filters
    def _range(field, lo, hi):
        clause = {}
        if lo is not None: clause["$gte"] = lo
        if hi is not None: clause["$lte"] = hi
        if clause:         mongo_filter[field] = clause

    _range("age_years",    min_age,       max_age)
    _range("bmi",          min_bmi,       max_bmi)
    _range("systolic_bp",  min_systolic,  max_systolic)
    _range("diastolic_bp", min_diastolic, max_diastolic)

    # ── Validate sort field ──────────────────────────────────────────────────
    sort_dir = 1 if sort_order == "asc" else -1
    sort_spec = [("patient_id", 1)]   # default deterministic sort
    if sort_by:
        if sort_by not in SORTABLE_FIELDS:
            raise HTTPException(
                status_code=422,
                detail={"success": False, "error": {
                    "code": "INVALID_SORT_FIELD",
                    "message": f"Cannot sort by '{sort_by}'. Allowed: {sorted(SORTABLE_FIELDS)}",
                }},
            )
        sort_spec = [(sort_by, sort_dir)]

    # ── MongoDB: count + paginate ────────────────────────────────────────────
    total = db.patients.count_documents(mongo_filter)
    skip  = (page - 1) * limit
    items = list(
        db.patients
        .find(mongo_filter, {"_id": 0})
        .sort(sort_spec)
        .skip(skip)
        .limit(limit)
    )

    return _success({
        "items":       items,
        "page":        page,
        "limit":       limit,
        "total":       total,
        "total_pages": max(1, (total + limit - 1) // limit),
    })


# ── PATIENT DETAIL  GET /api/v1/patients/{patient_id} ────────────────────────

@router.get(
    "/{patient_id}",
    summary="Get complete details of a single patient",
)
def get_patient(patient_id: str):
    db      = get_db()
    patient = db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
    if not patient:
        _not_found(patient_id)
    return _success(patient)


# ── CREATE PATIENT  POST /api/v1/patients ─────────────────────────────────────

@router.post(
    "/",
    status_code=201,
    summary="Create a new patient record",
)
def create_patient(body: PatientCreate):
    db = get_db()

    # Generate unique patient_id
    new_id = f"P{str(uuid.uuid4().int)[:8].upper()}"
    # Guarantee uniqueness (extremely unlikely collision but be safe)
    while db.patients.find_one({"patient_id": new_id}):
        new_id = f"P{str(uuid.uuid4().int)[:8].upper()}"

    doc = body.model_dump()
    doc["patient_id"]  = new_id
    doc["bmi"]         = _bmi(doc["weight"], doc["height"])
    doc["bp_category"] = _bp_category(doc["systolic_bp"], doc["diastolic_bp"])

    db.patients.insert_one(doc)
    doc.pop("_id", None)

    return _success({
        "message": "Patient created successfully",
        "patient": doc,
    })


# ── UPDATE PATIENT  PUT /api/v1/patients/{patient_id} ────────────────────────

@router.put(
    "/{patient_id}",
    summary="Update an existing patient record (partial update)",
)
def update_patient(patient_id: str, body: PatientUpdate):
    db = get_db()

    existing = db.patients.find_one({"patient_id": patient_id})
    if not existing:
        _not_found(patient_id)

    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(
            status_code=422,
            detail={"success": False, "error": {
                "code": "EMPTY_UPDATE",
                "message": "At least one field must be provided for update.",
            }},
        )

    # Validate BP ordering after partial update
    sys_bp = updates.get("systolic_bp",  existing.get("systolic_bp",  0))
    dia_bp = updates.get("diastolic_bp", existing.get("diastolic_bp", 0))
    if sys_bp <= dia_bp:
        raise HTTPException(
            status_code=422,
            detail={"success": False, "error": {
                "code": "INVALID_BP",
                "message": "systolic_bp must be greater than diastolic_bp.",
            }},
        )

    # Recompute derived fields if weight/height/bp changed
    if "weight" in updates or "height" in updates:
        w = updates.get("weight", existing.get("weight", 0))
        h = updates.get("height", existing.get("height", 0))
        updates["bmi"] = _bmi(w, h)

    if "systolic_bp" in updates or "diastolic_bp" in updates:
        updates["bp_category"] = _bp_category(sys_bp, dia_bp)

    db.patients.update_one({"patient_id": patient_id}, {"$set": updates})

    updated = db.patients.find_one({"patient_id": patient_id}, {"_id": 0})
    return _success({
        "message": "Patient updated successfully",
        "patient": updated,
    })


# ── DELETE PATIENT  DELETE /api/v1/patients/{patient_id} ─────────────────────

@router.delete(
    "/{patient_id}",
    summary="Delete a patient record",
)
def delete_patient(patient_id: str):
    db     = get_db()
    result = db.patients.delete_one({"patient_id": patient_id})
    if result.deleted_count == 0:
        _not_found(patient_id)
    return _success({"message": f"Patient '{patient_id}' deleted successfully."})
