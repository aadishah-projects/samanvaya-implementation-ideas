# Real-World Upgrade Roadmap

This document explains what can be upgraded next to make Samanvaya more efficient, more realistic, and more impressive for a hackathon.

## 1. Current Strengths

Implementation 6 already has a strong foundation:

- ETL pipeline.
- PostgreSQL staging tables.
- SQL reconciliation.
- Mock/live API switching.
- Realistic Nepali data.
- Dashboard.
- CSV export.
- Run history.
- Risk levels.
- Issue explanations.

This is enough for a strong hackathon demo.

The next step is not to rewrite everything. The best next step is to add small features that make it feel more like a real government or insurance operations tool.

## 2. Highest-Impact Hackathon Upgrades

### Upgrade 1: Case Management

Add a table like:

```text
reconciliation_cases
```

Fields:

- `case_id`
- `claim_code`
- `assigned_to`
- `case_status`
- `notes`
- `created_at`
- `resolved_at`

Why it helps:

Right now, Samanvaya detects problems. Case management would show how people fix those problems.

Demo line:

```text
We do not only detect missing payments. We turn them into trackable cases for finance officers.
```

### Upgrade 2: One-Click Escalation Letter

For each issue, generate a simple escalation message:

```text
Subject: Missing payment for claim CLM00001

OpenIMIS approved this claim, but no matching SOSYS payment was found.
Hospital: Bir Hospital
Claimed amount: NPR 50,000
Risk: HIGH
```

Why it helps:

Judges like systems that close the loop from detection to action.

### Upgrade 3: SMS Alert Mock

Add an endpoint:

```text
POST /api/send-alert/{claim_code}
```

It can return a mocked SMS message:

```text
Samanvaya Alert: Claim CLM00001 has no matching payment. Risk: HIGH.
```

Why it helps:

SMS is very relevant for Nepal and for hospitals outside major cities.

### Upgrade 4: Role-Based Views

Create three dashboard views:

```text
Hospital view
District officer view
Ministry view
```

Each role sees different information:

- Hospital: only its own claims.
- District officer: district-level issues.
- Ministry: national summary.

Why it helps:

This shows product thinking, not just technical matching.

### Upgrade 5: AI Explanation Layer

Add an explanation button for each issue.

Example output:

```text
This claim is high risk because OpenIMIS has an approved claim, but no payment record was found in SOSYS. The full claimed amount is currently unreconciled.
```

This can start rule-based. It does not need a real LLM for the hackathon.

Why it helps:

It makes the system easier for non-technical users.

## 3. Efficiency Upgrades

### Add Indexes

Add indexes on join/filter fields:

```sql
CREATE INDEX IF NOT EXISTS idx_openimis_claim_code
ON staging_openimis_claims(code);

CREATE INDEX IF NOT EXISTS idx_sosys_claim_code
ON staging_sosys_payments(claim_code);

CREATE INDEX IF NOT EXISTS idx_reconciled_status
ON reconciled_view(reconciliation_status);
```

Why it helps:

If the dataset grows from 50 claims to millions of claims, indexes become essential.

### Use Upserts Instead Of Truncate

Current implementation truncates staging tables before loading.

That is fine for a demo.

Production should use upserts:

```sql
INSERT ... ON CONFLICT ... DO UPDATE
```

Why it helps:

It supports incremental sync instead of full reloads.

### Add Batch IDs

Add a `batch_id` to staging tables.

Why it helps:

You can trace exactly which pipeline run loaded which records.

### Add Data Quality Checks

Examples:

- Claim code missing.
- Negative payment amount.
- Payment date before claim date.
- Duplicate claim code.
- Unknown hospital.

Why it helps:

Real-world data is messy. Data quality checks make the system trustworthy.

## 4. Real API Integration Upgrades

### OpenIMIS Live Integration

Current direction:

```text
OpenIMIS GraphQL -> extract_openimis.py -> staging_openimis_claims
```

Next improvements:

- Store JWT securely in environment variables.
- Add token refresh.
- Add pagination for more than 100 claims.
- Add error logging.
- Save raw API responses for audit.

### SOSYS/Mojaloop Integration

Current direction:

```text
SOSYS/Mojaloop REST -> extract_sosys.py -> staging_sosys_payments
```

Next improvements:

- Use real payment reference mapping.
- Map Mojaloop transfer IDs to OpenIMIS claim codes.
- Handle failed, pending, and settled transfer states.
- Add webhook-style payment updates.

## 5. Dashboard Upgrades

### Add Charts

Useful charts:

- Status distribution bar chart.
- Unreconciled NPR by district.
- Top hospitals by issue count.
- Monthly trend of mismatches.

### Add Claim Detail Drawer

Click a claim and show:

- OpenIMIS source data.
- SOSYS source data.
- Variance.
- Reason.
- Suggested action.

### Add Filters

Useful filters:

- Date range.
- District.
- Hospital.
- Risk level.
- Status.

Some search and status filtering already exists. Date and district filters would be natural next upgrades.

## 6. Security And Governance Upgrades

### Add Authentication

Use simple login roles:

- Admin.
- Finance officer.
- District officer.
- Hospital viewer.

### Add Audit Log

Track:

- Who viewed a case.
- Who exported CSV.
- Who changed case status.
- Who sent an alert.

Why it matters:

Financial systems need accountability.

### Protect Secrets

Do not hard-code:

- Database password.
- OpenIMIS JWT.
- API credentials.

Use environment variables or a secret manager.

## 7. Testing Upgrades

Add tests for:

- Missing payment classification.
- Amount mismatch classification.
- Pending status classification.
- Duplicate payment classification.
- CSV export.
- API response shape.

Example:

```text
tests/test_reconciliation_rules.py
```

Why it helps:

Judges may not ask for tests, but tests make the project safer to modify during a hackathon.

## 8. Deployment Upgrades

### Docker Compose

Create a `docker-compose.yml` with:

- FastAPI app.
- PostgreSQL.
- Mock API server.

Why it helps:

One command can run the whole demo.

### Environment Files

Create:

```text
.env.example
```

Include:

```text
DB_NAME=samanvaya
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=localhost
DB_PORT=5433
USE_LIVE_API=False
```

## 9. Best Next Three Features

If time is short, build only these:

1. Case management table and "Create Case" button.
2. SMS alert mock endpoint.
3. Claim detail view with recommended action.

These three make the project feel like a working product, not just an analytics dashboard.

## 10. Production Vision

The final production version could look like this:

```text
OpenIMIS GraphQL
      |
Scheduled ETL / webhook listener
      |
PostgreSQL staging tables
      |
SQL reconciliation engine
      |
Case management and audit trail
      |
Role-based dashboard
      |
SMS/email alerts
      |
Ministry reporting exports
```

## 11. Final Hackathon Advice

Do not add too many half-working features.

For the hackathon, prioritize:

- A reliable demo.
- Clear problem framing.
- Realistic data.
- Explainable statuses.
- A visible path to production.

That is exactly what Implementation 6 is now set up to do.
