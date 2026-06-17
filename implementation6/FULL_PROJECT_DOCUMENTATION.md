# Samanvaya Full Project Documentation

## 1. Project Summary

Samanvaya is a financial reconciliation prototype for Nepal's health insurance ecosystem.

The core problem is simple but important:

```text
OpenIMIS says a hospital claim was approved.
SOSYS or a payment system says money was paid.
Samanvaya checks whether those two truths match.
```

If they do not match, the system flags the issue for action.

This is useful because real public payment systems can have:

- Approved claims with no payment.
- Payments that are lower than approved claim amounts.
- Payments stuck in pending state.
- Duplicate payouts for the same claim.
- Weak visibility for hospitals, district officers, and national administrators.

The strongest framing for the project is:

```text
Samanvaya is a financial integrity layer for Nepal's health insurance payment flow.
```

## 2. What You Have Achieved So Far

You started with a very small reconciliation idea and turned it into a realistic ETL-backed prototype.

Current achievements:

- Built a basic reconciliation engine from claims and payments.
- Moved from CSV files to a PostgreSQL database.
- Created staging tables for raw OpenIMIS and SOSYS data.
- Built an OpenIMIS-style GraphQL extractor.
- Built a SOSYS/Mojaloop-style REST/FHIR extractor.
- Added a SQL-based reconciliation engine.
- Added realistic Nepali hospital and district data.
- Added deliberate anomaly generation for hackathon demos.
- Built a FastAPI dashboard.
- Added a one-click pipeline trigger.
- Added CSV export for audit/evidence use.
- Added live/mock configuration switching.
- Added run history, issue reasons, risk levels, district hotspots, and risk hospitals.

That means the project is no longer a toy data-matching script. It now has the shape of a real operational reconciliation system.

## 3. Evolution Of The Project

### Version 1: CSV Reconciliation

Location:

```text
basic_implementation/
```

What it did:

- Used `claims.csv`.
- Used `payments.csv`.
- Merged both files using Pandas.
- Classified each row as matched, missing, mismatch, or pending.

Why it mattered:

This proved the core idea. Without this, the later API and database work would not matter.

### Version 2: Export And Dashboard

Location:

```text
basic_implementation/
```

What improved:

- Reconciliation output could be exported.
- A small FastAPI dashboard showed results in the browser.
- Traffic-light logic became visible to users.

Why it mattered:

This made the project understandable to non-technical judges.

### Version 3: PostgreSQL Foundation

Location:

```text
implementation2/
```

What improved:

- CSV files were replaced by PostgreSQL tables.
- Data became persistent.
- Fake but realistic data could be seeded.
- The project became closer to how government or insurance systems actually store records.

Why it mattered:

This moved the project from "script" to "system."

### Version 4: Real OpenIMIS Direction

Location:

```text
implementation3/
```

What happened:

- You explored running the real `openimis-be_py` backend.
- You learned OpenIMIS is a large Django and GraphQL system.
- You documented Docker and environment issues.

Why it mattered:

Even though the full local OpenIMIS stack was heavy, you learned the real integration direction.

### Version 5: FHIR And Interoperability Direction

Location:

```text
implementation4/
```

What improved:

- You explored FHIR-style REST data.
- You created a mock FHIR server.
- You aligned the project with healthcare interoperability ideas.

Why it mattered:

FHIR-style APIs are easier to demo and explain than a heavy full OpenIMIS Docker stack.

### Version 6: Enterprise ETL Foundation

Locations:

```text
implementation5/
implementation6/
app/
```

What improved:

- Central config file with live/mock switching.
- OpenIMIS extractor.
- SOSYS/Mojaloop extractor.
- PostgreSQL staging tables.
- SQL reconciliation engine.
- FastAPI operational dashboard.
- CSV export.
- Pipeline trigger.
- Realistic Nepal-specific seed data.
- Mock and live API modes.

Why it mattered:

This is the current hackathon-ready implementation.

## 4. Current Architecture

```text
                OpenIMIS
          GraphQL claims source
                    |
                    v
          extract_openimis.py
                    |
                    v
      staging_openimis_claims table


              SOSYS / Mojaloop
          REST or FHIR payment source
                    |
                    v
            extract_sosys.py
                    |
                    v
      staging_sosys_payments table


      staging_openimis_claims + staging_sosys_payments
                    |
                    v
             reconcile_sql.py
                    |
                    v
             reconciled_view
                    |
                    v
                main.py
          FastAPI dashboard + APIs
```

## 5. Current Database Tables

### `staging_openimis_claims`

Stores claims extracted from OpenIMIS.

Important fields:

- `uuid`
- `code`
- `date_claimed`
- `amount_claimed`
- `hospital_name`
- `district`
- `status_code`
- `extracted_at`

### `staging_sosys_payments`

Stores payment records extracted from SOSYS or Mojaloop-style APIs.

Important fields:

- `transaction_id`
- `claim_code`
- `amount_paid`
- `payment_date`
- `status`
- `extracted_at`

### `reconciled_view`

Stores final reconciliation results.

Important fields:

- `claim_code`
- `hospital_name`
- `district`
- `amount_claimed`
- `amount_paid`
- `amount_variance`
- `payment_status`
- `payment_count`
- `reconciliation_status`
- `reconciliation_reason`
- `risk_level`
- `updated_at`

### `pipeline_runs`

Stores pipeline run history.

Important fields:

- `started_at`
- `finished_at`
- `status`
- `source_mode`
- `claims_extracted`
- `payments_extracted`
- `reconciled_count`
- `unreconciled_count`
- `unreconciled_amount_npr`
- `message`

## 6. Reconciliation Statuses

### `RECONCILED`

The claim and payment match.

Meaning:

```text
OpenIMIS approved claim amount = SOSYS paid amount
Payment status = paid
```

### `MISSING_PAYMENT`

OpenIMIS has an approved claim, but no payment record exists.

Meaning:

```text
Claim exists.
Payment does not exist.
```

### `AMOUNT_MISMATCH`

A payment exists, but the amount paid is different from the amount claimed.

Meaning:

```text
Claimed NPR 75,000
Paid NPR 70,000
Difference NPR 5,000
```

### `STATUS_PENDING`

Payment exists, and the amount may match, but it is not marked paid.

Meaning:

```text
Payment exists.
Status is pending.
```

### `DUPLICATE_PAYMENT`

Multiple payment rows exist for one claim.

Meaning:

```text
One OpenIMIS claim has more than one SOSYS payment record.
```

This status is now supported by the SQL engine even if the default seed data does not yet generate duplicates.

## 7. Current Demo Result

Using the deterministic seeded dataset:

```text
Total claims: 50
Reconciled: 24
Missing payment: 12
Amount mismatch: 9
Status pending: 5
Open issues: 26
```

The dashboard also calculates:

- Reconciliation quality score.
- Total unreconciled claim value in NPR.
- Total payment variance in NPR.
- Top risk hospitals.
- District hotspots.
- Recent pipeline runs.

## 8. Why Implementation 6 Is More Real World

Implementation 6 is stronger because it separates concerns:

```text
Extraction is separate from storage.
Storage is separate from reconciliation.
Reconciliation is separate from presentation.
Configuration is separate from code.
```

This is how real data systems are usually structured.

Important real-world patterns now present:

- ETL pipeline.
- Staging tables.
- SQL transformation.
- Environment-based configuration.
- Mock/live mode switching.
- Operational dashboard.
- Audit-style CSV export.
- Run history.
- Risk scoring.
- Human-readable issue reasons.

## 9. What Is Still Mocked

The project is honest but not fully production-connected yet.

Still mocked or partially mocked:

- SOSYS real API access.
- Mojaloop real payment ledger access.
- OpenIMIS live credentials and production server.
- User authentication.
- Role-based permissions.
- Case management workflow.
- SMS integration.
- Deployment.

That is normal for a hackathon. The important part is that the architecture now has places where those real integrations can plug in.

## 10. Best Hackathon Pitch

Do not pitch it as:

```text
We matched claims and payments.
```

Pitch it as:

```text
Samanvaya is a financial integrity layer for Nepal's health insurance payment ecosystem. It automatically reconciles approved OpenIMIS claims against SOSYS/Mojaloop-style payment records, detects missing or mismatched payments, explains the reason, and gives officials a dashboard for action.
```

## 11. Best Demo Flow

1. Show the architecture.
2. Open the dashboard.
3. Show total claims and issue counts.
4. Filter to `MISSING_PAYMENT`.
5. Click/export the CSV evidence report.
6. Explain one case:

```text
This claim was approved in OpenIMIS.
No matching payment was found in SOSYS.
Samanvaya flags it as high risk and explains why.
```

7. Explain the real-world upgrade path:

```text
Today we run with mock/live toggles. In production, the same extractors connect to real OpenIMIS and SOSYS APIs.
```

## 12. Package Contents

The handoff package separates the past journey from the current implementation.

Past work:

```text
samanvaya_hackathon_package/past_implementations/
```

Current implementation 6:

```text
samanvaya_hackathon_package/current_implementation6/
```

Documentation:

```text
samanvaya_hackathon_package/docs/
```
