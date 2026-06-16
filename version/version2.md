# Samanvaya Implementation Guide: Complete Beginner Walkthrough

## Phase 0: Understand the Domain (Day 1)

**What is OpenIMIS?**
Open-source Insurance Management Information System used to manage health insurance — beneficiary enrollment, claims, providers, policies. Built on Django (backend) + PostgreSQL. Hospitals submit claims into it.

**What is SOSYS?**
Nepal's Social Security Management Information System — tracks the government payment/disbursement side. This is where money actually moves.

**The core problem you're solving:** A claim gets approved in OpenIMIS but the payment record in SOSYS doesn't match (wrong amount, missing, duplicated, or delayed). Nobody reconciles these two systems automatically today.

Before writing code, get read access to:
- A demo/sandbox OpenIMIS instance (https://github.com/openimis/openimis-be_py — you can self-host)
- Sample SOSYS data structure (if you don't have real access, you'll need to **mock this** — see Phase 1)

## Phase 1: Data Access Strategy (Day 1–2)

**Reality check for a hackathon:** You almost certainly won't get live API access to government SOSYS in time. Plan for this explicitly:

| Option | Effort | Realism |
|---|---|---|
| Self-host OpenIMIS demo + mock SOSYS as a second Postgres DB/CSV | Medium | High — do this |
| Use OpenIMIS public demo API + synthetic SOSYS data | Low | High — fallback |
| Real API access to both | High | Low — don't bet on this |

**Decision: build OpenIMIS-side from real/demo data, mock SOSYS as a structured CSV/DB that mirrors what a payment ledger would look like** (claim_id, amount_paid, payment_date, status, district). State this explicitly in your pitch — judges respect honest scoping more than fake claims of "full integration."

## Phase 2: Set Up OpenIMIS Locally (Day 2–3)

```bash
git clone https://github.com/openimis/openimis-be_py.git
cd openimis-be_py
docker-compose up -d
```

This gives you Postgres + Django backend + GraphQL API at `localhost:8000/api/graphql`.

Seed it with demo data (OpenIMIS ships demo fixtures) so you have realistic claims: hospital names, claim amounts, dates, statuses.

**Beginner tip:** If Docker setup eats your timeline, skip self-hosting entirely. Export/copy the demo data schema and just build a Postgres table with the same fields. The reconciliation logic doesn't care where the data physically lives — it cares about the *shape* of the data.

## Phase 3: Define Your Data Schema (Day 3)

You need two tables that represent the two systems:

```sql
-- OpenIMIS side (claims)
CREATE TABLE openimis_claims (
    claim_id TEXT PRIMARY KEY,
    hospital_name TEXT,
    district TEXT,
    amount_claimed NUMERIC,
    claim_date DATE,
    status TEXT -- approved, pending, rejected
);

-- SOSYS side (payments) -- mocked
CREATE TABLE sosys_payments (
    payment_id TEXT PRIMARY KEY,
    claim_id TEXT, -- should match openimis_claims.claim_id
    amount_paid NUMERIC,
    payment_date DATE,
    status TEXT -- paid, partial, failed, missing
);
```

Generate ~200–500 synthetic rows with Python/Faker, deliberately injecting mismatches (10–15% of rows): missing payments, partial amounts, duplicates, wrong amounts. This becomes your demo dataset.

## Phase 4: Build the Reconciliation Engine (Day 4–5)

This is the core logic — a Python script/service that joins the two tables and classifies each claim.

```python
import pandas as pd

def reconcile(claims_df, payments_df):
    merged = claims_df.merge(payments_df, on='claim_id', how='left', indicator=True)
    
    def classify(row):
        if row['_merge'] == 'left_only':
            return 'MISSING_PAYMENT'  # red
        if row['amount_claimed'] != row['amount_paid']:
            return 'AMOUNT_MISMATCH'  # red/yellow
        if row['status'] != 'paid':
            return 'STATUS_PENDING'  # yellow
        return 'RECONCILED'  # green
    
    merged['reconciliation_status'] = merged.apply(classify, axis=1)
    return merged
```

Wrap this in a FastAPI service so your frontend can call it:

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/reconcile")
def get_reconciliation():
    # load from DB, run reconcile(), return JSON
    ...
```

## Phase 5: AI Explanation Layer (Day 5–6)

For each flagged claim, call Claude to generate a plain-language explanation using the hospital's historical pattern.

```python
import anthropic

client = anthropic.Anthropic()

def explain_anomaly(claim, hospital_history):
    prompt = f"""
    Claim: {claim['hospital_name']} claimed NPR {claim['amount_claimed']} on {claim['claim_date']}.
    Status: {claim['reconciliation_status']}.
    This hospital's average claim over the last 6 months: NPR {hospital_history['avg']}.
    
    In 2 sentences, explain in simple English why this looks anomalous (or not), 
    referencing the historical pattern. Be specific with numbers.
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

**Beginner pitfall:** Don't call this live per-request in your demo — pre-generate explanations for your demo dataset and cache them. Live LLM calls during a live judge demo risk latency/failure. Have a fallback static response ready.

## Phase 6: Predictive Module (Day 6 — Optional/Simplified)

Don't build real ML under time pressure. A defensible "predictive" heuristic:

```python
def predict_risk(claim, hospital_stats):
    risk_score = 0
    if claim['amount_claimed'] > hospital_stats['avg'] * 3:
        risk_score += 40
    if claim['district'] in high_failure_districts:
        risk_score += 30
    if claim['claim_date'].weekday() >= 5:  # weekend submission
        risk_score += 15
    return min(risk_score, 100)
```

Call this "rule-based risk scoring," not "machine learning," in your pitch unless you actually train a model. Judges penalize overclaiming AI sophistication more than they reward it.

## Phase 7: Frontend Dashboard (Day 6–7)

Build in React (or even just HTML/JS if time-constrained):
- Traffic light table (red/yellow/green rows, sortable/filterable by district)
- Click a row → see Claude's explanation + risk score
- District heat map (use a simple Nepal districts GeoJSON + color intensity)
- Role toggle (cashier/officer/ministry view) — just filter the same data differently per role, don't build separate backends

## Phase 8: One-Click Resolution (Day 7)

A button that takes the flagged claim's data and generates a pre-filled template:

```python
def generate_dispute_letter(claim, explanation):
    return f"""
    To: SOSYS Reconciliation Unit
    Re: Claim {claim['claim_id']} - {claim['hospital_name']}
    
    Discrepancy detected: {claim['reconciliation_status']}
    Claimed: NPR {claim['amount_claimed']} | Paid: NPR {claim.get('amount_paid', 'N/A')}
    
    Analysis: {explanation}
    
    Requesting reconciliation review.
    """
```

Render as downloadable PDF or just a copyable text block — don't over-engineer this.

## Phase 9: Audit Trail (Day 7)

Simple append-only log table:

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    action TEXT,
    actor TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

Every reconciliation run and every "resolve" click writes a row. Show this table in the demo as proof of governance thinking.

## Phase 10: Rehearse the Demo (Day 8)

Script the exact click path: dashboard → flagged claim → AI explanation → risk score → resolution letter → audit log entry. Time it under 3 minutes. Have the pitch reframe ("financial integrity layer," not "we reconcile two databases") memorized, not read.

**Critical beginner mistake to avoid:** Building features in isolation without a working end-to-end path. After each phase, make sure claims flow dashboard → AI explanation → resolution, even if ugly, before polishing any single piece.