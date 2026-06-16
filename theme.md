Your idea is already aligned very well with **Track 1 (Dual-System Reconciliation Engine)**. The key to scoring highly in a hackathon is showing that you're solving a **real operational problem**, not just matching two spreadsheets.

# The Real Problem Behind Track 1

Think of the payment lifecycle:

```text
Patient Receives Treatment
          ↓
Hospital submits claim
          ↓
OpenIMIS processes claim
          ↓
Claim Approved
          ↓
SOSYS payment generated
          ↓
Bank transfer executed
          ↓
Hospital receives money
```

In reality, things break:

```text
Claim approved = Rs. 50,000
Payment sent = Rs. 40,000
```

or

```text
Claim approved
No payment record found
```

or

```text
One claim
Paid twice accidentally
```

or

```text
Same hospital written differently
```

OpenIMIS:

```
Patan Hospital Pvt Ltd
```

SOSYS:

```
PATAN HOSPITAL PVT. LTD.
```

Humans must manually reconcile thousands of records.

That's what Samanvaya automates.

---

# Architecture of Samanvaya

```text
                OpenIMIS
            (Claims Bundle)
                     |
                     |
                     v
           Data Extraction Layer
                     |
                     |
                     v
          Reconciliation Engine
                     |
      -----------------------------
      |            |             |
      v            v             v
 Fuzzy Match   Rule Engine   Anomaly Detector
      |            |             |
      --------------------------------
                     |
                     v
           Classification Engine
                     |
                     v
             Traffic Dashboard
                     |
                     v
               SMS Alerts
```

---

# Module 1: Data Extraction

Input 1:

OpenIMIS Claim Bundle

```json
{
  "claim_id":"CLM001",
  "provider":"Patan Hospital",
  "amount":50000,
  "date":"2026-05-01"
}
```

Input 2:

SOSYS Payment Log

```json
{
  "payment_ref":"PAY998",
  "provider":"PATAN HOSPITAL",
  "amount":50000,
  "date":"2026-05-02"
}
```

These could come from:

* CSV
* Excel
* API
* Database

For the hackathon:

```text
CSV Upload
```

is enough.

---

# Module 2: Fuzzy Matching Engine

This is where your project becomes interesting.

Simple matching:

```python
claim.provider == payment.provider
```

fails.

Instead:

```python
RapidFuzz
```

Example:

```text
Patan Hospital
PATAN HOSPITAL
```

Similarity:

```text
98%
```

Matched.

---

Another example:

```text
Bir Hospital
BIR HOSPITAL
```

Match.

---

Useful fields:

```text
Provider Name
Amount
Claim Date
District
Reference Number
```

Combined score:

```text
Name Similarity = 40%
Amount Match = 40%
Date Match = 20%
```

Final score:

```text
92%
```

Matched.

---

# Module 3: Reconciliation Rules

After matching:

## Green

Claim:

```text
50,000
```

Payment:

```text
50,000
```

Status:

```text
FULLY MATCHED
```

Green.

---

## Yellow

Claim:

```text
50,000
```

Payment:

```text
30,000
```

Status:

```text
PARTIAL PAYMENT
```

Yellow.

---

## Red

Claim:

```text
50,000
```

Payment:

```text
0
```

Status:

```text
PAYMENT MISSING
```

Red.

---

## Red

Claim:

```text
50,000
```

Payments:

```text
50,000
50,000
```

Status:

```text
DUPLICATE PAYMENT
```

Red.

---

# Module 4: Anomaly Detection

This is your "AI" component.

You don't need deep learning.

Simple rule-based anomaly detection is enough.

---

### Ghost Claim Detection

Claim exists:

```text
Claim ID = C100
Amount = 50,000
```

No payment after:

```text
30 days
```

Flag:

```text
Ghost Claim
```

---

### Duplicate Payout

```text
Claim C100
```

Matched to:

```text
PAY100
PAY101
```

Both:

```text
50,000
```

Flag.

---

### Suspicious Amount

Hospital usually receives:

```text
20k-60k
```

Suddenly:

```text
500k
```

Flag.

---

### Batch Failure Detection

Suppose:

```text
100 payments sent
80 failed
```

This may indicate:

```text
Bank outage
```

Flag entire batch.

---

# Module 5: Traffic Light Dashboard

This is probably what judges will remember most.

## Executive Summary

```text
Total Claims: 5,000

🟢 Fully Matched : 4,500
🟡 Partial : 300
🔴 Failed : 200
```

---

### Pie Chart

```text
Matched 90%
Partial 6%
Failed 4%
```

---

### Trend Graph

```text
Failures per month
```

Shows operational health.

---

### Top Risk Providers

```text
Provider A
12 failed claims

Provider B
8 duplicates
```

---

# Module 6: SMS Notification System

Very relevant for Nepal.

Example:

```text
Samanvaya Alert:

Claim CLM001 approved.
Payment NPR 50,000 successfully reconciled.

Status: GREEN
```

---

Partial:

```text
Samanvaya Alert:

Claim CLM002

Expected: NPR 50,000
Received: NPR 30,000

Status: PARTIAL PAYMENT
```

---

Failed:

```text
Samanvaya Alert:

Claim CLM003

No payment found.
Please contact district office.
```

---

# Suggested Tech Stack

Since you're a Computer Engineering student and likely have limited hackathon time:

### Backend

```text
Python
FastAPI
Pandas
RapidFuzz
```

### Database

```text
PostgreSQL
```

or

```text
SQLite
```

for demo

### Dashboard

```text
Streamlit
```

Fastest option.

or

```text
React + FastAPI
```

More impressive but more work.

### SMS

Nepali SMS Gateway API
or mocked SMS service

```

---

# What Will Impress Judges Most

Don't present Samanvaya as:

> "A claim matching system."

Present it as:

> "A Financial Integrity Layer for Nepal's Health Insurance Ecosystem."

Your three strongest points are:

1. **Automated reconciliation** between OpenIMIS and SOSYS.
2. **Anomaly detection** for ghost claims and duplicate payouts.
3. **Traffic-light operational dashboard + SMS alerts** for real-time visibility.

That framing makes it sound like a national-scale solution rather than a simple data-matching tool.
```
