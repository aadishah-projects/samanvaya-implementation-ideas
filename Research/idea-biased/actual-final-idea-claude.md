# Samanvaya — Revised & Clarified 🎯

## The Real Goal (Corrected Understanding)

```
❌ Wrong understanding:
   OpenIMIS + SOSYS working together, just better reconciled

✅ Correct understanding:
   A standalone module that replicates what OpenIMIS's payment layer SHOULD do
   Built independently (no live OpenIMIS instance needed)
   Designed to slot into OpenIMIS later — but runs perfectly on its own for the demo
```

---

## Why Standalone (Not Plugged Into OpenIMIS)

Running a full OpenIMIS instance locally requires:
- Docker with 8–12 GB RAM
- Complex multi-container setup (PostgreSQL, Django, React, Celery, Redis)
- Long build times and frequent environment issues

**The Samanvaya approach:** Build the payment module as a self-contained app that mirrors OpenIMIS's data models and API conventions exactly. It is OpenIMIS-compatible by design — just not dependent on a live instance to run.

---

## What SOSYS Actually Does (That Samanvaya Replaces)

| SOSYS Function | What it means |
|---|---|
| **Bulk Payment Processing** | Takes approved claim bundles → disburses money to hospitals/providers |
| **Payment Execution** | Connects to banks / payment rails to actually move funds |
| **Transaction Logging** | Records every payment attempt, success, failure |
| **Payment Status Tracking** | Knows which payments went through and which didn't |
| **Financial Reporting** | Generates payout summaries, statements |

OpenIMIS **stops at claim approval**. It hands a bundle to SOSYS and hopes for the best. **Samanvaya closes that gap — and does it without needing OpenIMIS running.**

---

## The New Picture

```
BEFORE (Current State):
┌──────────────────┐         ┌────────────────┐         ┌──────────────┐
│    OpenIMIS      │──────►  │     SOSYS      │──────►  │   Hospital   │
│                  │         │                │         │   / Provider │
│ Enrollment       │  claim  │ Bulk Payment   │  money  │              │
│ Claims           │ bundles │ Execution      │         │              │
│ Approvals        │         │ Tx Logging     │         │              │
│ Bundling         │         │ Reporting      │         │              │
└──────────────────┘         └────────────────┘         └──────────────┘
         OpenIMIS is BLIND after this handoff ↑


AFTER (With Samanvaya — Standalone Build):
┌──────────────────────────────────────────────────────┐
│              SAMANVAYA (Standalone Module)             │
│                                                      │
│  Simulated Claims Layer  ──►  Payment Engine         │──────► Hospital
│  (seeded demo data)           • Bulk Disbursement         / Provider
│                               • Transaction Ledger        (Mock Bank)
│                               • Status Tracking
│                               • Financial Dashboard
│                               • Reconciliation Console
└──────────────────────────────────────────────────────┘
         Full end-to-end flow, no OpenIMIS install needed ↑
```

---

## What Samanvaya Actually Builds (Standalone Version)

```
Samanvaya = Self-Contained Payment Engine
           (OpenIMIS-compatible, runs independently)

1. Simulated Claims Layer
   └─ Seeded database of realistic approved claim bundles
   └─ API endpoints that mimic OpenIMIS's claim approval output
   └─ "Approve Claim" button in UI triggers the Samanvaya queue

2. Payment Gateway Adapter
   └─ Connects to Mock Bank (your own local FastAPI server)
   └─ Designed to swap in eSewa, ConnectIPS, RTGS with no logic changes

3. Bulk Disbursement Engine
   └─ Takes approved claim bundles → executes mock payments
   └─ Handles batching, retries, failures

4. Transaction Ledger
   └─ Every payment attempt logged
   └─ Success / partial / failed / pending states tracked

5. Reconciliation Engine (Migration Demo Tool)
   └─ Upload a mock "SOSYS CSV" → instantly see mismatches flagged

6. Financial Dashboard
   └─ Real-time fund flow, payment health, anomaly alerts
```

---

## Where Reconciliation Fits

```
Migration Demo (Within Samanvaya):
                     ┌─────────────────────┐
Samanvaya Ledger ──► │   Reconciliation    │ ← upload mock SOSYS CSV
Mock SOSYS CSV ────► │   Engine            │   flags double payments,
                     │                     │   missing claims, mismatches
                     └─────────────────────┘
                              │
                              ▼
                     Anomalies shown in dashboard
                     → "This is what transition from SOSYS looks like"
```

---

## The One-Line Pitch

> **"Samanvaya is a standalone payment execution module built to replace SOSYS — it takes approved health insurance claims, disburses payments through configurable gateways, tracks every transaction with financial-grade reliability, and gives OpenIMIS full end-to-end visibility for the first time."**

---

## Why This Is a Strong Hackathon Project

| Dimension | Strength |
|---|---|
| **Buildable** | Runs on any laptop — no heavy OpenIMIS install required |
| **Problem clarity** | OpenIMIS has a real, documented external dependency on SOSYS |
| **Track alignment** | Directly addresses SSF financial loop independence |
| **Scope for demo** | Claim → approval → payment → status in one clean flow |
| **Future value** | Drop it into any OpenIMIS instance when ready — compatible by design |
| **Name fit** | Samanvaya (coordination) = the financial nervous system OpenIMIS was missing |
