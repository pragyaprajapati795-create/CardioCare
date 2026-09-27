# MongoDB Query Lab — Documentation

## Purpose
The Query Lab demonstrates real, live MongoDB operations against the `cardiocare_db.patients`
collection. It is designed for:
- ADBMS academic submission
- Placement interview demonstrations
- Teaching MongoDB aggregation concepts visually

---

## Security Architecture
**Arbitrary code execution is impossible.**

The frontend sends only a `query_id` string:
```json
{ "query_id": "cholesterol_vs_disease" }
```
The backend resolves the corresponding pre-approved Python lambda from `QUERY_REGISTRY`.
Raw MongoDB code, JavaScript, or dynamic queries from the client are **never executed**.

---

## Query Registry (15 Approved Queries)

| # | ID | Name | Operation | Key Operators |
|---|----|------|-----------|---------------|
| 1 | `total_patients` | Total Patients | countDocuments | — |
| 2 | `cardio_cases` | CVD Disease Cases | countDocuments | — |
| 3 | `non_cardio_cases` | Non-Disease Cases | countDocuments | — |
| 4 | `average_age` | Average Age | aggregate | `$group`, `$avg` |
| 5 | `gender_distribution` | Gender Distribution | aggregate | `$group`, `$sum`, `$sort` |
| 6 | `gender_vs_disease` | Gender vs Disease | aggregate | `$group`, `$cond`, `$eq` |
| 7 | `cholesterol_distribution` | Cholesterol Distribution | aggregate | `$group`, `$switch` |
| 8 | `cholesterol_vs_disease` | Cholesterol vs Disease | aggregate | `$group`, `$cond`, `$eq` |
| 9 | `glucose_distribution` | Glucose Distribution | aggregate | `$group`, `$switch` |
| 10 | `smoking_vs_disease` | Smoking vs Disease | aggregate | `$group`, `$cond` |
| 11 | `alcohol_vs_disease` | Alcohol vs Disease | aggregate | `$group`, `$cond` |
| 12 | `physical_activity_vs_disease` | Physical Activity vs Disease | aggregate | `$group`, `$cond` |
| 13 | `age_group_analysis` | Age Group Analysis | aggregate | `$bucket` |
| 14 | `bmi_analysis` | BMI Category Analysis | aggregate | `$addFields`, `$switch`, `$group` |
| 15 | `blood_pressure_analysis` | Blood Pressure Analysis | aggregate | `$group`, `$sort` |

---

## MongoDB Operators Explained

| Operator | Purpose |
|----------|---------|
| `$group` | Groups documents by a field — like GROUP BY in SQL |
| `$sum` | Counts documents or sums a numeric field within a group |
| `$avg` | Computes arithmetic mean within a group |
| `$cond` | IF-THEN-ELSE conditional — routes count to different accumulators |
| `$eq` | Equality check used inside `$cond` |
| `$sort` | Sorts results ascending or descending |
| `$bucket` | Automatically places documents into predefined numeric ranges |
| `$switch` | Multi-case conditional (CASE statement equivalent) |
| `$addFields` | Adds computed fields without modifying stored documents |
| `$project` | Shapes the output — includes, excludes, or renames fields |

---

## Example Aggregation Pipeline

```javascript
// Cholesterol vs Cardiovascular Disease
db.patients.aggregate([
  {
    $group: {
      _id: "$cholesterol",
      total: { $sum: 1 },
      diseaseCases: {
        $sum: { $cond: [{ $eq: ["$cardio", 1] }, 1, 0] }
      },
      nonDiseaseCases: {
        $sum: { $cond: [{ $eq: ["$cardio", 0] }, 1, 0] }
      }
    }
  },
  { $sort: { _id: 1 } }
])
```

---

## API Endpoints

### Query Lab
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/query-lab/queries` | List all approved queries |
| POST | `/api/v1/query-lab/run` | Execute a query by ID |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/overview` | KPIs: total, disease %, averages |
| GET | `/api/v1/analytics/age` | Age group breakdown |
| GET | `/api/v1/analytics/gender` | Gender distribution |
| GET | `/api/v1/analytics/cholesterol` | Cholesterol levels |
| GET | `/api/v1/analytics/glucose` | Glucose levels |
| GET | `/api/v1/analytics/lifestyle` | Smoking, alcohol, physical activity |
| GET | `/api/v1/analytics/bmi` | BMI category analysis |
| GET | `/api/v1/analytics/blood-pressure` | Blood pressure categories |

---

## Running Tests
```bash
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests/test_query_lab.py tests/test_database.py -v
```
Expected: **31 passed, 0 failed**
