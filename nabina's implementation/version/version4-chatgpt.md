This is actually a pretty good implementation guide, but if you're a beginner, a lot of the terms can sound intimidating. Let me explain it as if we're building **Samanvaya from scratch**.

---

# 1. First, What Problem Are We Solving?

Imagine this situation:

### Hospital submits a claim

Bir Hospital says:

> "We treated patients under health insurance. Please pay us NPR 50,000."

This claim goes into **OpenIMIS**.

---

### Government pays hospital

Later, the government payment system (**SOSYS**) records:

| Claim ID | Amount Paid |
| -------- | ----------- |
| C001     | NPR 40,000  |

Uh oh.

Hospital asked for **50,000**
Government paid **40,000**

Somebody should investigate.

But imagine there are:

* 100 hospitals
* 1000 claims per month
* Thousands of payments

Doing this manually is painful.

---

## What Samanvaya Does

Samanvaya automatically compares:

### OpenIMIS

| Claim ID | Amount Claimed |
| -------- | -------------- |
| C001     | 50,000         |

with

### SOSYS

| Claim ID | Amount Paid |
| -------- | ----------- |
| C001     | 40,000      |

and says:

🔴 Amount Mismatch

---

# 2. Understanding OpenIMIS

Think of OpenIMIS as:

> "The insurance side"

It stores:

* Patient records
* Hospitals
* Insurance enrollment
* Claims

Example:

| Claim ID | Hospital | Amount |
| -------- | -------- | ------ |
| C001     | Bir      | 50,000 |

---

# 3. Understanding SOSYS

Think of SOSYS as:

> "The payment side"

It stores:

* Payment records
* Money transfers
* Payment status

Example:

| Payment ID | Claim ID | Amount Paid |
| ---------- | -------- | ----------- |
| P001       | C001     | 40,000      |

---

# 4. Why Reconciliation Is Needed

The word:

## Reconciliation

simply means:

> Compare two records and check if they agree.

Like comparing:

### Bank Statement

vs

### Your Cashbook

---

Example:

OpenIMIS says:

Claim = 50,000

SOSYS says:

Payment = 50,000

✅ Reconciled

---

OpenIMIS says:

Claim = 50,000

SOSYS says:

Payment = 40,000

❌ Mismatch

---

# 5. Phase 1 — Why We Mock SOSYS

You probably won't get access to the real government database.

So you create fake data.

This is called:

## Mocking

Example:

```csv
payment_id,claim_id,amount_paid
P001,C001,50000
P002,C002,45000
```

This behaves like a real SOSYS system.

---

# 6. Phase 2 — Why Docker?

They suggest:

```bash
docker-compose up -d
```

### What Docker Does

Instead of installing:

* PostgreSQL
* Django
* OpenIMIS

manually,

Docker downloads everything and runs it.

Think of Docker as:

> A ready-made computer inside your computer.

---

# 7. Understanding the Database Tables

You create two tables.

---

## Table 1: Claims

```sql
openimis_claims
```

Contains:

| claim_id | amount_claimed |
| -------- | -------------- |
| C001     | 50000          |

---

## Table 2: Payments

```sql
sosys_payments
```

Contains:

| claim_id | amount_paid |
| -------- | ----------- |
| C001     | 40000       |

---

# 8. What Is Synthetic Data?

Synthetic means:

> Fake but realistic.

Instead of entering 500 rows manually:

Python creates them.

Example:

```python
from faker import Faker
```

Generates:

| Hospital              |
| --------------------- |
| Bir Hospital          |
| Patan Hospital        |
| Nepal Medical College |

Automatically.

---

# 9. Core of the Project: Reconciliation Engine

This is the most important part.

---

## Step 1

Load claims

```python
claims_df
```

---

## Step 2

Load payments

```python
payments_df
```

---

## Step 3

Merge them

```python
merged = claims_df.merge(
    payments_df,
    on='claim_id'
)
```

Imagine:

### Claims

| claim_id | amount |
| -------- | ------ |
| C001     | 50000  |

### Payments

| claim_id | paid  |
| -------- | ----- |
| C001     | 40000 |

After merge:

| claim_id | amount | paid  |
| -------- | ------ | ----- |
| C001     | 50000  | 40000 |

Now comparison is easy.

---

# 10. Understanding the Classification Logic

This function:

```python
def classify(row):
```

acts like a judge.

---

### Case 1

No payment found

```python
left_only
```

Result:

```python
MISSING_PAYMENT
```

🔴 Red

---

### Case 2

Amounts different

```python
amount_claimed != amount_paid
```

Result:

```python
AMOUNT_MISMATCH
```

🔴 Red

---

### Case 3

Status still pending

```python
status != "paid"
```

Result:

```python
STATUS_PENDING
```

🟡 Yellow

---

### Case 4

Everything matches

Result:

```python
RECONCILED
```

🟢 Green

---

# 11. Why FastAPI?

Your frontend cannot directly access Python functions.

So you create:

```python
@app.get("/reconcile")
```

Think of it like:

Restaurant waiter.

Frontend says:

> Give me reconciliation results.

FastAPI runs:

```python
reconcile()
```

and sends JSON back.

---

# 12. What Is JSON?

Example:

```json
{
  "claim_id": "C001",
  "status": "AMOUNT_MISMATCH"
}
```

Frontend reads this and displays it.

---

# 13. AI Explanation Layer

This is where judges will get impressed.

Instead of:

```text
AMOUNT_MISMATCH
```

the system says:

> Bir Hospital submitted a claim of NPR 50,000 but only NPR 40,000 was recorded in SOSYS. The difference of NPR 10,000 exceeds the hospital's normal variance pattern.

Much easier to understand.

---

# 14. Why Cache AI Responses?

Bad idea:

Judge clicks button →

Claude API slow →

Internet issue →

Demo dies

💀

Better:

Generate explanations beforehand.

Store them in database.

Show instantly.

---

# 15. Risk Scoring

This is NOT machine learning.

It is:

## Rule-Based Scoring

Example:

Claim amount = 300,000

Hospital average = 50,000

Since:

```python
300000 > 3 * 50000
```

Add:

```python
+40 points
```

---

Another rule:

High-risk district

```python
+30 points
```

Total:

```python
70/100
```

Risk score.

---

# 16. Frontend Dashboard

This is what judges see.

---

## Green

Everything okay.

```text
Claim C001
Status: Reconciled
```

🟢

---

## Yellow

Needs attention.

```text
Claim C002
Status: Pending
```

🟡

---

## Red

Problem.

```text
Claim C003
Status: Missing Payment
```

🔴

---

# 17. District Heatmap

Imagine Nepal map.

Districts become:

🟢 Mostly reconciled

🟡 Some issues

🔴 Many problems

A ministry officer can instantly see:

> "Why is Kailali district showing so many red claims?"

---

# 18. One-Click Resolution

Instead of writing:

> Dear SOSYS Team...

manually every time,

button generates:

```text
To: SOSYS Reconciliation Unit

Claim ID: C001

Claimed: NPR 50,000
Paid: NPR 40,000

Difference detected.
```

Automatically.

---

# 19. Audit Log

Very important for government systems.

Whenever someone:

* Runs reconciliation
* Opens claim
* Resolves issue

record it.

Example:

| Time  | User    | Action        |
| ----- | ------- | ------------- |
| 10:01 | Officer | Reconcile     |
| 10:03 | Officer | Resolve Claim |

This creates accountability.

---

# 20. What Judges Actually Care About

Many beginners think:

> More AI = better score

Not necessarily.

For your Samanvaya project, judges will likely care more about:

### 1. Clear Problem

"Health claims and payments don't match."

---

### 2. Working Solution

"System automatically finds discrepancies."

---

### 3. Practical Impact

"Reduces payment delays and financial leakages."

---

### 4. Governance

"Every action is logged."

---

### 5. Honest AI Usage

"AI explains anomalies."

Not:

> "We built revolutionary AGI-powered blockchain quantum ML."

---

# The Simplest Mental Model

Think of Samanvaya as:

```text
OpenIMIS Claims
        +
SOSYS Payments
        ↓
Compare Records
        ↓
Find Problems
        ↓
Explain Problems
        ↓
Show Dashboard
        ↓
Generate Resolution
        ↓
Store Audit Trail
```

That flow is the entire project. Everything else (FastAPI, React, AI, Docker, PostgreSQL) is just technology used to make those steps happen.
