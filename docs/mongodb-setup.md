# MongoDB Setup & Dataset Verification

## Requirements
- MongoDB Community Server running locally on `localhost:27017`
- Python 3.11+
- `pymongo` driver installed in the backend environment.

## Environment Variables
The application uses the following configuration logic:
- `MONGODB_URI`: `mongodb://localhost:27017`
- `MONGODB_DATABASE`: `cardiocare_db`
- `COLLECTION`: `patients`

## Dataset Information (Measured Actuals)
- **Raw dataset path**: `backend/data/raw/cardio_train.csv`
- **Raw dataset count**: 70,000 records
- **Cleaned dataset path**: `backend/data/processed/cardio_clean.csv`
- **Cleaned dataset count**: 68,616 records
- **MongoDB document count**: 68,616 records
- **Sync Status**: SYNCED

## Import Command
To import the cleaned dataset into MongoDB, use the optimized bulk-insertion script:
```bash
python scripts/03_import_to_mongodb.py
```
This script handles duplicate protection by dropping partial imports or safely inserting using the `patient_id` generated during the process. 

## Indexes Created
The following indexes are built in the `patients` collection to optimize API lookups and dashboard aggregation:
1. `patient_id` (Unique: True) - Fast O(1) patient lookups.
2. `cardio` (Unique: False) - Disease aggregation grouping.
3. `age_years` (Unique: False) - Age cohort analytics.
4. `cholesterol` (Unique: False) - Cholesterol distribution filtering.
5. `systolic_bp` (Unique: False) - BP risk analysis.
6. `gender` (Unique: False) - Gender-wise analytics grouping.

## Verification
You can verify the active MongoDB connection and sync status by querying the health endpoints:
```bash
curl http://localhost:8000/api/v1/database/health
curl http://localhost:8000/api/v1/database/pipeline
```

## Troubleshooting
If MongoDB connection fails, check:
1. Windows Services -> Ensure "MongoDB" is running.
2. Firewalls are not blocking port 27017.
3. Run `mongosh` in terminal to manually test access.
