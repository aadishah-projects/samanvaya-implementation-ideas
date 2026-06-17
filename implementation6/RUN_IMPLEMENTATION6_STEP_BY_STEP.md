# Run Implementation 6 Step By Step

This guide teaches you how to run the current Samanvaya implementation.

Run these commands from the main project root:

```powershell
cd C:\Users\Acer\Downloads\samanvaya
```

## 1. What You Need

Required:

- Python 3.12 or similar.
- PostgreSQL running locally.
- The Python dependencies in `app/requirements.txt`.

Recommended for this project:

- Docker PostgreSQL container named `samanvaya-db`.
- Database name: `samanvaya`.
- User: `postgres`.
- Password: `secret`.
- Host port: `5433`.

The project config defaults to:

```text
DB_NAME=samanvaya
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=localhost
DB_PORT=5433
```

These defaults are defined in:

```text
app/config.py
```

## 2. Install Python Dependencies

```powershell
python -m pip install -r app\requirements.txt
```

If dependencies are already installed, this command is still safe.

## 3. Start PostgreSQL

If your Docker Postgres container already exists and is running, skip this step.

To check:

```powershell
docker ps
```

If you need to create the database container:

```powershell
docker run --name samanvaya-db -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=samanvaya -p 5433:5432 -d postgres:15
```

If the container already exists but is stopped:

```powershell
docker start samanvaya-db
```

## 4. Set Database Port For This Terminal

```powershell
$env:DB_PORT = "5433"
```

This tells the Python app to use the Docker-mapped Postgres port.

## 5. Create Or Upgrade Database Tables

```powershell
python app\setup_db.py
```

Expected output:

```text
Staging tables created.
```

This creates:

- `staging_openimis_claims`
- `staging_sosys_payments`
- `reconciled_view`
- `pipeline_runs`

It also adds missing columns if an older version of the tables already exists.

## 6. Quick Demo Mode: Seed Realistic Data

This is the best mode for judging because it creates predictable anomalies.

```powershell
python app\seed_realistic_data.py
```

Expected output:

```text
Seeded 50 claims and 38 payments into staging tables.
Anomalies introduced:
  - 12 MISSING_PAYMENT (no matching payment)
  - 9 AMOUNT_MISMATCH (amount_paid != amount_claimed)
  - 5 STATUS_PENDING
```

## 7. Run SQL Reconciliation

```powershell
python app\reconcile_sql.py
```

Expected output:

```text
Running SQL-based Reconciliation Engine...
SQL Reconciliation complete! 50 claims processed and stored in database.
```

## 8. Start The Dashboard

Use port `8002` if port `8000` is already busy.

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Open:

```text
http://127.0.0.1:8002
```

You should see:

- Total claims.
- Reconciled count.
- Open issue count.
- Reconciliation quality score.
- Unreconciled NPR amount.
- Risk hospitals.
- District hotspots.
- Recent pipeline runs.
- A searchable/filterable claim table.

## 9. Full Mock Pipeline Mode

This mode tests the extractor pipeline.

Terminal 1:

```powershell
cd C:\Users\Acer\Downloads\samanvaya
$env:DB_PORT = "5433"
python app\mock_fhir.py
```

This starts a mock OpenIMIS/SOSYS server at:

```text
http://127.0.0.1:8001
```

Terminal 2:

```powershell
cd C:\Users\Acer\Downloads\samanvaya
$env:DB_PORT = "5433"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Open:

```text
http://127.0.0.1:8002
```

Click:

```text
Run Pipeline Now
```

What happens:

```text
extract_openimis.py pulls claims from mock GraphQL.
extract_sosys.py pulls payments from mock FHIR REST.
reconcile_sql.py writes results into reconciled_view.
main.py refreshes the dashboard.
```

The mock pipeline now also includes controlled anomalies, so the button is useful for demos.

## 10. Manual Pipeline Commands

If you want to run the pipeline manually instead of clicking the button:

Terminal 1:

```powershell
python app\mock_fhir.py
```

Terminal 2:

```powershell
python app\extract_openimis.py
python app\extract_sosys.py
python app\reconcile_sql.py
```

Then start the dashboard:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

## 11. Live API Mode

To switch from mock APIs to live API configuration:

```powershell
$env:USE_LIVE_API = "True"
$env:OPENIMIS_JWT_TOKEN = "paste-your-token-here"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

In live mode:

```text
OPENIMIS_URL=http://demo.openimis.org/api/graphql
SOSYS_API_URL=https://sandbox.mojaloop.io/centralledger/v1/transfers
```

For the hackathon, mock mode is safer because network access can fail.

## 12. Useful API Checks

Check dashboard API:

```powershell
curl.exe http://127.0.0.1:8002/api/reconcile
```

Check recent pipeline runs:

```powershell
curl.exe http://127.0.0.1:8002/api/pipeline-runs
```

Download CSV in browser:

```text
http://127.0.0.1:8002/api/export-csv
```

## 13. Troubleshooting

### Problem: Postgres authentication fails

Most likely cause:

```text
You are connecting to local Windows Postgres on 5432 instead of Docker Postgres on 5433.
```

Fix:

```powershell
$env:DB_PORT = "5433"
```

Then rerun:

```powershell
python app\setup_db.py
```

### Problem: Dashboard opens but data does not load

Run:

```powershell
python app\setup_db.py
python app\seed_realistic_data.py
python app\reconcile_sql.py
```

Then refresh the dashboard.

### Problem: Run Pipeline Now fails

Most likely cause:

```text
The mock API server is not running on port 8001.
```

Fix:

```powershell
python app\mock_fhir.py
```

Then click `Run Pipeline Now` again.

### Problem: Port 8000 is busy

Use port 8002:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

### Problem: You want to reset demo data

Run:

```powershell
python app\setup_db.py
python app\seed_realistic_data.py
python app\reconcile_sql.py
```

This rebuilds the deterministic hackathon dataset.
