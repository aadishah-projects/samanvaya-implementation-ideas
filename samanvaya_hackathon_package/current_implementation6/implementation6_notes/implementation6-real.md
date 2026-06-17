# Implementation 6 — Real-Data Pipeline: What Was Built

Based on the battle plan in `implementation6.md`, the following was implemented in `app/`:

---

## Files Created

### `app/config.py`
Central configuration with `USE_LIVE_API` toggle (default: `False`):

| Setting | `USE_LIVE_API=False` (mock) | `USE_LIVE_API=True` (live) |
|---|---|---|
| `OPENIMIS_URL` | `http://localhost:8001/api/graphql` | `http://demo.openimis.org/api/graphql` |
| `JWT_TOKEN` | `mock_openimis_jwt_secret_12345` | From env `OPENIMIS_JWT_TOKEN` |
| `SOSYS_API_URL` | `http://localhost:8001/fhir/Claim` | `https://sandbox.mojaloop.io/centralledger/v1/transfers` |
| `SOSYS_HEADERS` | Basic JSON | `FSPIOP-Source: testfsp1` |

All DB credentials are configurable via env vars (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).

### `app/mock_openimis_graphql.py`
Schema-accurate OpenIMIS GraphQL mock using **Strawberry GraphQL** + FastAPI:
- Mirrors the exact OpenIMIS GraphQL schema (`ClaimConnection` → `ClaimEdge` → `ClaimNode`)
- 20 real Nepali hospital names (Bir Hospital, Patan Hospital, TUTH, Grande International, etc.)
- Generates 100 realistic claims on each query
- Includes `tokenAuth` mutation (returns mock JWT)
- Runs on `http://localhost:8000/api/graphql`

### `app/seed_realistic_data.py`
Seeds staging tables with realistic data:
- 50 claims with real Nepali hospital names across 15 districts
- NPR amounts ranging 2,000–150,000
- Date range: Jan–June 2025
- Deliberate anomalies:
  - ~20% MISSING_PAYMENT (no matching payment)
  - ~16% AMOUNT_MISMATCH (amount_paid != amount_claimed)
  - ~10% STATUS_PENDING

### `app/requirements.txt`
Added `strawberry-graphql>=0.200.0` dependency.

---

## Files Modified

| File | Change |
|---|---|
| `app/extract_openimis.py` | Imports `OPENIMIS_URL`, `JWT_TOKEN`, `DB_CONFIG` from `config.py` |
| `app/extract_sosys.py` | Imports `SOSYS_API_URL`, `SOSYS_HEADERS`, `USE_LIVE_API`, `DB_CONFIG`; handles Mojaloop vs FHIR response format |
| `app/setup_db.py` | Imports `DB_CONFIG` from `config.py` |
| `app/reconcile_sql.py` | Imports `DB_CONFIG` from `config.py` |
| `app/main.py` | Full dashboard overhaul with all features below |

---

## Dashboard Improvements

| Feature | Endpoint | Description |
|---|---|---|
| **Run Pipeline Now** | `POST /api/run-pipeline` | Triggers full ETL (extract OpenIMIS → extract SOSYS → reconcile) |
| **Last Synced** | `GET /api/last-synced` | Tracks when pipeline last ran |
| **Anomaly Stat Cards** | `GET /api/reconcile` | Counts for RECONCILED, MISSING_PAYMENT, AMOUNT_MISMATCH, STATUS_PENDING |
| **NPR Unreconciled Total** | `GET /api/reconcile (stats)` | Sum of all unreconciled claim amounts |
| **Export CSV** | `GET /api/export-csv` | Downloads `reconciled_claims.csv` |
| **Live/Mock Badge** | Dashboard header | Shows "LIVE API" or "MOCK API" based on config |

---

## Run Order

```powershell
# 1. Create DB tables
python app/setup_db.py

# 2. Start mock FHIR server (in a separate terminal)
python app/mock_fhir.py

# 3. Seed realistic data (optional — or use the pipeline)
python app/seed_realistic_data.py

# 4. Start main dashboard
uvicorn app.main:app --reload
```

Then open `http://localhost:8000` and click **Run Pipeline Now**.

---

## Toggling Live APIs

```powershell
# Windows PowerShell
$env:USE_LIVE_API="True"
uvicorn app.main:app --reload
```

---

## Pipeline Run Log (2025-06-17)

### Prerequisites
- Docker PostgreSQL `samanvaya-db` running on port 5433
- Mock FHIR server started on port 8001 (`python app/mock_fhir.py`)

### Step 1 — Create Tables
```
> python app/setup_db.py
Staging tables created.
```

### Step 2 — Seed Realistic Data
```
> python app/seed_realistic_data.py
Seeded 50 claims and 38 payments into staging tables.
Anomalies introduced:
  - 12 MISSING_PAYMENT (no matching payment)
  - 9 AMOUNT_MISMATCH (amount_paid != amount_claimed)
  - 5 STATUS_PENDING
```

### Step 3 — Run ETL Pipeline
```
> python run_pipeline.py (extract_openimis → extract_sosys → reconcile_sql)

Extracting claims from OpenIMIS GraphQL API (http://localhost:8001/api/graphql)...
Fetched 50 claims. Loading to Postgres...
OpenIMIS data successfully loaded into staging table!

Extracting payments from SOSYS/Mojaloop API (http://localhost:8001/fhir/Claim)...
Fetched 50 payments.
SOSYS data successfully loaded into staging table!

Running SQL-based Reconciliation Engine...
SQL Reconciliation complete! 50 claims processed and stored in database.
Pipeline complete!
```

### Step 4 — Verify Reconciled View

| Status | Count |
|---|---|
| RECONCILED | 24 |
| MISSING_PAYMENT | 12 |
| AMOUNT_MISMATCH | 9 |
| STATUS_PENDING | 5 |
| **Unreconciled NPR** | **1,935,742.97** |

### Step 5 — Start Dashboard
```
> uvicorn app.main:app --reload
```
Opened at `http://localhost:8000`. The **Run Pipeline Now** button triggers the full ETL cycle. The **Export CSV** button downloads the reconciled view. Anomaly counts and NPR unreconciled total render live from `/api/reconcile`.
