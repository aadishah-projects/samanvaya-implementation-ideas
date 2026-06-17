# Implementation 6 File And Component Roles

This document explains what each file and component does in the current implementation.

## 1. High-Level Components

Implementation 6 has six main layers:

```text
Configuration
Mock/live data sources
Extraction layer
PostgreSQL staging layer
SQL reconciliation engine
FastAPI dashboard and APIs
```

## 2. `app/config.py`

Role:

```text
Central configuration for database and API endpoints.
```

What it controls:

- Whether the system uses mock APIs or live APIs.
- PostgreSQL database credentials.
- OpenIMIS GraphQL URL.
- OpenIMIS JWT token.
- SOSYS/Mojaloop API URL.
- SOSYS/Mojaloop headers.

Important setting:

```python
USE_LIVE_API = os.getenv("USE_LIVE_API", "False").lower() == "true"
```

When `USE_LIVE_API=False`:

```text
OpenIMIS URL: http://localhost:8001/api/graphql
SOSYS URL: http://localhost:8001/fhir/Claim
```

When `USE_LIVE_API=True`:

```text
OpenIMIS URL: http://demo.openimis.org/api/graphql
SOSYS URL: https://sandbox.mojaloop.io/centralledger/v1/transfers
```

Why it matters:

This is a real-world pattern. Production systems should not hard-code environment-specific values across many files.

## 3. `app/setup_db.py`

Role:

```text
Creates and upgrades the PostgreSQL schema.
```

Tables created:

- `staging_openimis_claims`
- `staging_sosys_payments`
- `reconciled_view`
- `pipeline_runs`

Why it matters:

This file gives the application a stable database foundation. It also uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` so older versions of the database can be upgraded without dropping everything.

Run it with:

```powershell
python app\setup_db.py
```

## 4. `app/seed_realistic_data.py`

Role:

```text
Seeds deterministic Nepali healthcare demo data.
```

It creates:

- 50 claims.
- 38 payment records.
- 12 missing payment cases.
- 9 amount mismatch cases.
- 5 pending payment cases.
- 24 reconciled cases.

It uses:

- Nepali hospital names.
- Nepali district names.
- NPR amounts.
- Claim dates in 2025.

Why it matters:

This makes the demo strong and predictable. You can rerun it before a presentation and get the same story every time.

Run it with:

```powershell
python app\seed_realistic_data.py
```

## 5. `app/mock_fhir.py`

Role:

```text
Runs a lightweight mock server for OpenIMIS and SOSYS.
```

Endpoints:

```text
GET  /fhir/Claim
POST /api/graphql
```

How it is used:

- `extract_openimis.py` calls `/api/graphql`.
- `extract_sosys.py` calls `/fhir/Claim`.

Why it matters:

Hackathon WiFi and live systems can fail. This mock server lets the entire pipeline run offline.

Run it with:

```powershell
python app\mock_fhir.py
```

It listens on:

```text
http://127.0.0.1:8001
```

## 6. `app/mock_openimis_graphql.py`

Role:

```text
Alternative schema-accurate OpenIMIS GraphQL mock.
```

It uses:

- FastAPI.
- Strawberry GraphQL.
- OpenIMIS-style connection structure: `ClaimConnection -> ClaimEdge -> ClaimNode`.

Why it matters:

This file is useful if you want to demonstrate a more realistic GraphQL-only OpenIMIS mock.

Note:

The default implementation currently uses `mock_fhir.py` because it serves both mock GraphQL and mock FHIR/REST from one server.

## 7. `app/extract_openimis.py`

Role:

```text
Extracts approved claims from OpenIMIS GraphQL and loads them into PostgreSQL.
```

Input:

```text
OpenIMIS GraphQL API
```

Output:

```text
staging_openimis_claims
```

Query shape:

```text
claims(status: 4, first: 100)
```

Fields extracted:

- `uuid`
- `code`
- `dateClaimed`
- `claimed`
- `status`
- `healthFacility.name`

Why it matters:

This is the bridge from OpenIMIS into Samanvaya.

Run it with:

```powershell
python app\extract_openimis.py
```

## 8. `app/extract_sosys.py`

Role:

```text
Extracts payment records from SOSYS/Mojaloop-style APIs and loads them into PostgreSQL.
```

Input in mock mode:

```text
http://localhost:8001/fhir/Claim
```

Input in live mode:

```text
https://sandbox.mojaloop.io/centralledger/v1/transfers
```

Output:

```text
staging_sosys_payments
```

Fields loaded:

- `transaction_id`
- `claim_code`
- `amount_paid`
- `payment_date`
- `status`

Why it matters:

This is the bridge from the payment system into Samanvaya.

Run it with:

```powershell
python app\extract_sosys.py
```

## 9. `app/reconcile_sql.py`

Role:

```text
Runs the SQL reconciliation engine.
```

Input tables:

- `staging_openimis_claims`
- `staging_sosys_payments`

Output table:

- `reconciled_view`

Main logic:

```text
Group payments by claim.
Join claims to payments.
Calculate amount variance.
Classify reconciliation status.
Generate human-readable reason.
Assign risk level.
```

Statuses produced:

- `RECONCILED`
- `MISSING_PAYMENT`
- `AMOUNT_MISMATCH`
- `STATUS_PENDING`
- `DUPLICATE_PAYMENT`

Why it matters:

This is the heart of the project. It moves the critical matching logic into PostgreSQL, which is much more realistic than doing everything in browser code or a small script.

Run it with:

```powershell
python app\reconcile_sql.py
```

## 10. `app/main.py`

Role:

```text
FastAPI web app, dashboard, and API layer.
```

Main endpoints:

```text
GET  /
GET  /api/reconcile
POST /api/run-pipeline
GET  /api/last-synced
GET  /api/pipeline-runs
GET  /api/export-csv
```

What the dashboard shows:

- Total claims.
- Reconciled claims.
- Open issues.
- Reconciliation quality score.
- Unreconciled NPR amount.
- Total variance.
- Missing payment count.
- Amount mismatch count.
- Pending count.
- Duplicate count.
- Risk hospitals.
- District hotspots.
- Recent pipeline runs.
- Detailed claim table.

Why it matters:

This is what judges and users see. It turns the backend reconciliation engine into a usable operational tool.

Run it with:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

## 11. `app/requirements.txt`

Role:

```text
Lists Python dependencies.
```

Important libraries:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `pandas`
- `psycopg2-binary`
- `gql`
- `requests`
- `faker`
- `strawberry-graphql`

Install with:

```powershell
python -m pip install -r app\requirements.txt
```

## 12. Database Component Roles

### `staging_openimis_claims`

Raw claim data from OpenIMIS.

This table should stay close to source data.

### `staging_sosys_payments`

Raw payment data from SOSYS/Mojaloop.

This table should stay close to source data.

### `reconciled_view`

Final result table used by the dashboard.

This is where claim and payment records are joined and classified.

### `pipeline_runs`

Operational audit table.

It records when the ETL pipeline ran and what happened.

## 13. Typical Data Flow

Quick seeded demo:

```text
setup_db.py
  -> seed_realistic_data.py
  -> reconcile_sql.py
  -> main.py dashboard
```

Full mock pipeline:

```text
mock_fhir.py
  -> extract_openimis.py
  -> extract_sosys.py
  -> reconcile_sql.py
  -> main.py dashboard
```

## 14. What To Explain To Judges

Use this explanation:

```text
We separated the system into extraction, staging, SQL reconciliation, and dashboard layers. This means the app can run with mock data during a hackathon, but the same structure can connect to live OpenIMIS and SOSYS/Mojaloop APIs in production.
```
