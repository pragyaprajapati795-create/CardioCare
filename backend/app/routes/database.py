import os
import pandas as pd
from fastapi import APIRouter
from app.database.mongodb import get_db

router = APIRouter(prefix="/database", tags=["Database"])

@router.get("/health")
def get_db_health():
    try:
        db = get_db()
        count = db.patients.count_documents({})
        return {
            "connected": True,
            "database": db.name,
            "collection": "patients",
            "patient_count": count
        }
    except Exception as e:
        return {
            "connected": False,
            "database": "cardiocare_db",
            "collection": "patients",
            "patient_count": 0,
            "error": str(e)
        }

@router.get("/pipeline")
def get_db_pipeline():
    try:
        db = get_db()
        mongodb_records = db.patients.count_documents({})
        
        # Calculate from files
        raw_path = "backend/data/raw/cardio_train.csv"
        clean_path = "backend/data/processed/cardio_clean.csv"
        
        raw_records = 0
        if os.path.exists(raw_path):
            raw_records = sum(1 for line in open(raw_path)) - 1
            
        clean_records = 0
        if os.path.exists(clean_path):
            clean_records = sum(1 for line in open(clean_path)) - 1
            
        diff = clean_records - mongodb_records
        sync_status = "SYNCED" if diff == 0 else "OUT_OF_SYNC"
        
        return {
            "raw_records": raw_records,
            "clean_records": clean_records,
            "mongodb_records": mongodb_records,
            "records_difference": abs(diff),
            "sync_status": sync_status
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/stats")
def get_db_stats():
    db = get_db()
    collections = db.list_collection_names()
    
    stats = {
        "database_name": db.name,
        "collections": [],
        "total_documents": 0
    }
    
    for coll_name in collections:
        count = db[coll_name].estimated_document_count()
        stats["total_documents"] += count
        
        # Determine purpose based on our schema
        purpose = "Unknown"
        if coll_name == "patients":
            purpose = "Core cardiovascular dataset"
        elif coll_name == "users":
            purpose = "Authentication & Authz"
        elif coll_name == "predictions":
            purpose = "ML historical results"
        elif coll_name == "audit_logs":
            purpose = "Security & tracking"
            
        stats["collections"].append({
            "name": coll_name,
            "document_count": count,
            "purpose": purpose
        })
        
    stats["database_connection_status"] = "Connected"
    
    # Also attach indexes to stats response for completeness
    stats["indexes"] = get_db_indexes()
        
    return stats

@router.get("/indexes")
def get_db_indexes():
    db = get_db()
    try:
        # Get indexes for patients collection which we heavily indexed
        idx_info = db.patients.index_information()
        
        formatted_indexes = []
        for name, info in idx_info.items():
            if name == "_id_":
                continue
                
            field_name = info['key'][0][0]
            unique = info.get('unique', False)
            
            purpose = "Filter optimization"
            if field_name == "patient_id":
                purpose = "Fast O(1) patient lookup"
            elif field_name == "cardio":
                purpose = "Disease aggregation grouping"
            elif field_name == "age_years":
                purpose = "Age cohort analytics"
                
            formatted_indexes.append({
                "name": name,
                "collection": "patients",
                "field": field_name,
                "unique": unique,
                "purpose": purpose
            })
            
        return formatted_indexes
    except Exception as e:
        return []
