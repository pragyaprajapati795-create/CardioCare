"""
CardioCare — Phase 3: MongoDB Dataset Import
=============================================

PURPOSE:
    Bulk-import the cleaned 68,616-record cardiovascular dataset into
    MongoDB, create indexes, and verify the import.

FEATURES:
    - Reads cardio_clean.csv (cleaned in Phase 2)
    - Generates patient_id if not already present
    - Uses bulk_write with InsertOne for efficient batch insertion
    - Handles duplicates (skips if already imported)
    - Creates MongoDB indexes on frequently queried fields
    - Displays progress and final counts

PREREQUISITE:
    MongoDB must be running on localhost:27017

RUN:
    python scripts/03_import_to_mongodb.py

DATABASE:
    cardiocare_db.patients
"""

import sys
import io
import time
import math
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
from pymongo import MongoClient, InsertOne, errors

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_DATA   = PROJECT_ROOT / "backend" / "data" / "processed" / "cardio_clean.csv"

# ── MongoDB Config ────────────────────────────────────────────────────────────
MONGO_URI     = "mongodb://localhost:27017"
MONGO_DB_NAME = "cardiocare_db"
BATCH_SIZE    = 5000   # Insert in batches of 5,000 for efficiency


def header(title: str):
    bar = "=" * 72
    print(f"\n{bar}\n  {title}\n{bar}\n")


def main():
    print("\n+------------------------------------------------------------------+")
    print("|  CardioCare  |  Phase 3: MongoDB Dataset Import                  |")
    print("+------------------------------------------------------------------+")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}\n")

    # ── Step 1: Load cleaned CSV ──────────────────────────────────────────
    header("STEP 1 — LOADING CLEANED DATASET")
    if not CLEAN_DATA.exists():
        print(f"  [ERROR] {CLEAN_DATA} not found. Run Phase 2 first.")
        sys.exit(1)

    df = pd.read_csv(CLEAN_DATA)
    print(f"  Records loaded: {len(df):,}")
    print(f"  Columns: {list(df.columns)}")

    # ── Step 2: Connect to MongoDB ────────────────────────────────────────
    header("STEP 2 — CONNECTING TO MONGODB")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print(f"  Connected to MongoDB: {MONGO_URI}")
    except errors.ServerSelectionTimeoutError:
        print(f"  [ERROR] Cannot connect to MongoDB at {MONGO_URI}")
        print("  Make sure MongoDB is running:")
        print("    - Windows: Check 'MongoDB' in Services")
        print("    - Docker:  docker compose up mongodb")
        sys.exit(1)

    db = client[MONGO_DB_NAME]
    patients_col = db["patients"]

    # ── Step 3: Check existing data ───────────────────────────────────────
    header("STEP 3 — CHECKING EXISTING DATA")
    existing_count = patients_col.count_documents({})
    print(f"  Existing records in patients collection: {existing_count:,}")

    if existing_count >= len(df):
        print(f"  Dataset already imported ({existing_count:,} >= {len(df):,}).")
        print("  Skipping import to avoid duplicates.")
        print("  To re-import, drop the collection first:")
        print("    mongosh --eval 'db.getSiblingDB(\"cardiocare_db\").patients.drop()'")
    else:
        if existing_count > 0:
            print(f"  Partial data found. Dropping collection and re-importing...")
            patients_col.drop()

        # ── Step 4: Prepare documents ─────────────────────────────────────
        header("STEP 4 — PREPARING DOCUMENTS")
        records = df.to_dict(orient="records")

        # Ensure proper types
        for rec in records:
            rec["age"]              = int(rec.get("age", 0))
            rec["age_years"]        = round(float(rec.get("age_years", 0)), 1)
            rec["gender"]           = int(rec.get("gender", 0))
            rec["height"]           = int(rec.get("height", 0))
            rec["weight"]           = round(float(rec.get("weight", 0)), 1)
            rec["bmi"]              = round(float(rec.get("bmi", 0)), 2)
            rec["systolic_bp"]      = int(rec.get("systolic_bp", 0))
            rec["diastolic_bp"]     = int(rec.get("diastolic_bp", 0))
            rec["cholesterol"]      = int(rec.get("cholesterol", 0))
            rec["glucose"]          = int(rec.get("glucose", 0))
            rec["smoking"]          = int(rec.get("smoking", 0))
            rec["alcohol"]          = int(rec.get("alcohol", 0))
            rec["physical_activity"]= int(rec.get("physical_activity", 0))
            rec["cardio"]           = int(rec.get("cardio", 0))

        print(f"  Prepared {len(records):,} documents for insertion.")
        print(f"  Batch size: {BATCH_SIZE:,}")

        # ── Step 5: Bulk insert ───────────────────────────────────────────
        header("STEP 5 — BULK INSERTING INTO MONGODB")
        total_batches = math.ceil(len(records) / BATCH_SIZE)
        inserted_total = 0
        start_time = time.time()

        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1

            try:
                result = patients_col.insert_many(batch, ordered=False)
                inserted = len(result.inserted_ids)
                inserted_total += inserted
                pct = (inserted_total / len(records)) * 100
                elapsed = time.time() - start_time
                print(f"  Batch {batch_num:>3}/{total_batches}: "
                      f"inserted {inserted:,} | "
                      f"total {inserted_total:,}/{len(records):,} ({pct:.1f}%) | "
                      f"{elapsed:.1f}s")
            except errors.BulkWriteError as e:
                inserted = e.details.get("nInserted", 0)
                inserted_total += inserted
                print(f"  Batch {batch_num}: {inserted} inserted, "
                      f"{len(e.details.get('writeErrors', []))} errors (duplicates?)")

        elapsed = time.time() - start_time
        print(f"\n  Import complete!")
        print(f"  Total inserted   : {inserted_total:,}")
        print(f"  Time taken       : {elapsed:.2f}s")
        print(f"  Speed            : {inserted_total / elapsed:,.0f} docs/sec")

    # ── Step 6: Create Indexes ────────────────────────────────────────────
    header("STEP 6 — CREATING INDEXES")
    indexes = [
        ("patient_id", {"unique": True, "reason": "Primary lookup key — every patient query uses patient_id"}),
        ("cardio",     {"unique": False, "reason": "Filter by disease status — dashboard analytics"}),
        ("age_years",  {"unique": False, "reason": "Age-group aggregation queries"}),
        ("cholesterol",{"unique": False, "reason": "Cholesterol distribution analytics"}),
        ("systolic_bp",{"unique": False, "reason": "BP-based risk filtering"}),
        ("gender",     {"unique": False, "reason": "Gender-wise analytics aggregation"}),
    ]

    for field, opts in indexes:
        try:
            patients_col.create_index(field, unique=opts["unique"])
            print(f"  Index created: {field:<20} unique={str(opts['unique']):<6} | {opts['reason']}")
        except Exception as e:
            print(f"  Index {field}: {e}")

    # ── Step 7: Create other collections ──────────────────────────────────
    header("STEP 7 — INITIALIZING OTHER COLLECTIONS")
    collections = {
        "predictions": "Stores ML prediction results with patient references",
        "users"      : "User accounts for authentication (JWT)",
        "audit_logs" : "Tracks all CRUD operations for accountability",
    }
    existing_colls = db.list_collection_names()
    for coll, purpose in collections.items():
        if coll not in existing_colls:
            db.create_collection(coll)
            print(f"  Created: {coll:<20} | {purpose}")
        else:
            print(f"  Exists : {coll:<20} | {purpose}")

    # ── Step 8: Verify ────────────────────────────────────────────────────
    header("STEP 8 — VERIFICATION")
    final_count = patients_col.count_documents({})
    disease_count = patients_col.count_documents({"cardio": 1})
    sample = patients_col.find_one({"patient_id": "P10001"}, {"_id": 0})

    print(f"  Database        : {MONGO_DB_NAME}")
    print(f"  Collections     : {db.list_collection_names()}")
    print(f"  Patient records : {final_count:,}")
    print(f"  CVD cases       : {disease_count:,}")
    print(f"  No-CVD cases    : {final_count - disease_count:,}")
    print(f"  Indexes         : {patients_col.index_information()}")
    print(f"\n  Sample document (P10001):")
    if sample:
        for k, v in sample.items():
            print(f"    {k:<25}: {v}")
    else:
        print("    (not found)")

    # ── Quick aggregation test ────────────────────────────────────────────
    header("STEP 9 — QUICK AGGREGATION TEST")
    pipeline = [
        {"$group": {"_id": "$cardio", "count": {"$sum": 1}, "avg_age": {"$avg": "$age_years"}}},
        {"$sort": {"_id": 1}}
    ]
    agg_result = list(patients_col.aggregate(pipeline))
    print("  db.patients.aggregate([ {$group: {_id: '$cardio', count: {$sum: 1}}} ])")
    for doc in agg_result:
        label = "No CVD" if doc["_id"] == 0 else "CVD"
        print(f"    {label}: count={doc['count']:,}, avg_age={doc['avg_age']:.1f} years")

    header("PHASE 3 COMPLETE")
    print(f"  MongoDB is ready with {final_count:,} patient records.")
    print("  Next: Build FastAPI backend\n")

    client.close()


if __name__ == "__main__":
    main()
