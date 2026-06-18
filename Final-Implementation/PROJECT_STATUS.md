# Samanvaya — Project Status Report

> **Last updated:** Current session
> **Location:** `Final-Implementation/`

---

## 1. Your Goal (from `Research/idea/`)

> *"Samanvaya is a payment execution module that plugs into OpenIMIS, replacing SOSYS entirely — so OpenIMIS can enroll, process claims, disburse payments, and report financials without depending on any external payment system."*

### SOSYS Functions to Replace

| SOSYS Function | Your Requirement |
|---|---|
| Bulk Payment Processing | Takes approved claim bundles → disburses money |
| Payment Execution | Connects to banks/payment rails |
| Transaction Logging | Records every attempt, success, failure |
| Payment Status Tracking | Knows which payments went through |
| Financial Reporting | Generates payout summaries |

### Your 6 Phases (from `main-idea.md`)

1. Foundation & OpenIMIS Module Setup
2. Core Payment Engine & Ledger
3. Payment Gateway Adapter (Mock Bank)
4. Reconciliation Engine (SOSYS Migration Bridge)
5. UI/UX & Financial Dashboard
6. Hackathon Demo & Polish

---

## 2. What Has Been Built

The project has **3 complete systems** inside `Final-Implementation/`:

### System A — Standalone Demo (FastAPI + React + Mock Bank)

**Purpose:** Runs on any laptop without OpenIMIS. This is the hackathon demo.

| Component | Files | Status | Port |
|---|---|---|---|
| Backend (FastAPI) | `backend/` — 14 files | Running, tested | 8000 |
| Mock Bank (FastAPI) | `mock-bank/` — 3 files | Running, tested | 8001 |
| Frontend (React+Vite+Tailwind) | `frontend/` — 8 files | Built, running | 5173 |

**What it does:**
- 20 seeded claims (Nepali hospitals: Bir Hospital, Civil Hospital, etc.)
- Select claims → Create batch → Execute → Mock Bank receives payouts
- Approve/Reject in Mock Bank UI → webhook fires → dashboard updates live
- Transaction Ledger with status badges, raw JSON logs, retry button
- Transaction Ledger export to CSV for finance/audit evidence
- Transaction Ledger clear button for repeatable hackathon demos
- Reconciliation Console: upload SOSYS CSV → auto-matching → anomaly flagging
- Financial Dashboard: KPI cards, pie chart, bar chart, anomaly alerts

### System B — Native OpenIMIS Module (Django + GraphQL + Celery)

**Purpose:** Installable module that plugs into any OpenIMIS instance.

| Component | Files | Status |
|---|---|---|
| Backend (`openimis-be-samanvaya`) | 14 files | Built, tested via harness |
| Frontend (`openimis-fe-samanvaya`) | 10 files | Built (not yet deployed) |
| Docker Compose | `docker-compose.yml` | Written (not yet run) |
| Module Registry | `openimis.json` | Samanvaya listed first |

**Backend files:**
```
openimis-be-samanvaya/samanvaya/
├── models.py          — PaymentBatch, PaymentTransaction, GatewayConfig, SOSYSLegacyLog
├── apps.py            — Registers signals on ready()
├── signal_handlers.py — Django post_save hook on claim.Claim (the SOSYS replacement hook)
├── services.py        — BulkDisbursementService (create batch, execute, retry)
├── adapters.py        — Strategy Pattern: MockBankGateway, ESewaGateway, factory
├── tasks.py           — Celery tasks: queue_claim, execute_payment, process_webhook, poll_pending
├── gql_queries.py     — 10 GraphQL queries (batches, transactions, dashboard, reconciliation)
├── gql_mutations.py   — 5 GraphQL mutations (create batch, execute, retry, upload CSV, resolve)
├── schema.py          — Root schema aggregator
├── reconciliation.py  — Matching algorithm (matched/unmatched/flagged)
├── views.py           — Webhook endpoint (CSRF-exempt, row-locked)
├── urls.py            — /webhook/gateway/
├── permissions.py     — Numeric rights (150001-150006)
├── admin.py           — Django admin registration
└── migrations/        — Auto-generated
```

**Frontend files:**
```
openimis-fe-samanvaya/src/
├── index.js           — getRoutes(), getMenu(), getExtensions() (OpenIMIS registration)
├── constants.js       — Permission codes + route paths
├── helpers/graphql/queries.js — All Apollo queries + mutations
├── components/
│   ├── SamanvayaDashboard.js    — Material-UI + Recharts KPIs
│   ├── ClaimsQueue.js           — Batch creation + execution
│   ├── PaymentLedger.js         — Filterable table + detail dialog + retry
│   ├── ReconciliationConsole.js — CSV upload + tabs + resolve
│   └── PaymentStatusWidget.js   — Injected into ClaimDetail (the "Blind Spot Fix")
└── translations/
    ├── en.json         — English
    └── ne.json         — Nepali (नेपाली)
```

### System C — Test Harness (Django project to validate System B)

**Purpose:** Simulates OpenIMIS enough to test the Samanvaya module without the full Docker stack.

| Component | Files | Status |
|---|---|---|
| Django settings | `openimis_test/settings.py` | Working |
| Mock claim.Claim model | `openimis_test/claim/models.py` | Working |
| Root GraphQL schema | `openimis_test/schema.py` | Working |
| URL config | `openimis_test/urls.py` | Working |

---

## 3. Alignment with Your Goal — Phase by Phase

### Phase 1: Foundation & OpenIMIS Module Setup

| Your Requirement | Status | Details |
|---|---|---|
| Set up OpenIMIS dev environment | Partial | Docker stack NOT running (needs 8-12GB RAM). Test harness built instead. |
| Design DB schema (Payment_Batches, Payment_Transactions, Gateway_Configs) | Done | All 4 models in both SQLAlchemy (standalone) and Django ORM (OpenIMIS module) |
| Create module skeleton (Django + React) | Done | `openimis-be-samanvaya/` + `openimis-fe-samanvaya/` fully structured |
| Define the "Handoff" Hook | Done | `signal_handlers.py` — `post_save` on `claim.Claim`, tested and verified firing |

### Phase 2: Core Payment Engine & Ledger

| Your Requirement | Status | Details |
|---|---|---|
| Build Bulk Disbursement Engine | Done | `services.py` — create_batch, execute_batch, retry_transaction, all tested |
| Implement Transaction Ledger | Done | Full state machine (QUEUED→PROCESSING→SUCCESS/FAILED), raw JSON logs |
| Handle edge cases (partial success) | Done | Batch status computation (DONE/PARTIAL/FAILED), tested live |

### Phase 3: Payment Gateway Adapter

| Your Requirement | Status | Details |
|---|---|---|
| Build Mock Gateway | Done | `mock-bank/` — separate FastAPI server with approve/reject UI |
| Build Gateway Adapter Interface | Done | Strategy Pattern: `BasePaymentGateway` → `MockBankGateway`, `ESewaGateway` |
| Implement outbound API calls | Done | `adapters.py` — initiate_payout with idempotency keys |
| Implement webhooks/callbacks | Done | `views.py` + `urls.py` — CSRF-exempt, row-locked, tested end-to-end |

### Phase 4: Reconciliation Engine

| Your Requirement | Status | Details |
|---|---|---|
| Create SOSYS mock data | Done | `sosys_legacy.csv` — 20 records with intentional mismatches |
| Build ingestion parser | Done | CSV upload via GraphQL mutation, auto-parses |
| Develop matching algorithm | Done | `reconciliation.py` — matched/unmatched/flagged, duplicate detection |
| Implement anomaly flagging | Done | Tested: duplicate detection, amount mismatch, ghost payments |

### Phase 5: UI/UX & Financial Dashboard

| Your Requirement | Status | Details |
|---|---|---|
| Transaction Ledger UI | Done | Standalone (Tailwind) + OpenIMIS module (Material-UI) |
| Financial Dashboard (KPIs + charts) | Done | Pie + bar charts, anomaly alerts, auto-refresh |
| Reconciliation UI | Done | Upload CSV, tabbed results, resolve buttons |
| Ledger maintenance controls | Done | CSV export + clear ledger/reset affected claims for repeatable demos |

### Phase 6: Hackathon Demo & Polish

| Your Requirement | Status | Details |
|---|---|---|
| Seed demo data (Nepali context) | Done | 20 claims, NPR amounts, 5 hospitals |
| Rehearse end-to-end flow | Partial | Tested programmatically, NOT rehearsed live |
| Finalize pitch deck | Not started | No pitch materials created |
| Record backup video | Not started | No video recorded |

---

## 4. Verified Test Results

| Test | Result |
|---|---|
| Django migrations (claim + samanvaya models) | 4 models created, all applied |
| Seed data (10 claims, 8 approved, 1 gateway config) | Verified |
| Django Signal hook (claim approval → auto-queue) | Fires correctly (Celery connection errors prove it) |
| GraphQL: Dashboard summary query | Returns valid data |
| GraphQL: Create batch mutation (3 claims) | NPR 135,500 batch created |
| GraphQL: Execute batch mutation | 3 transactions → PROCESSING |
| Webhook: SUCCESS callback | Transaction flips to SUCCESS |
| Webhook: FAILED callback | Transaction flips to FAILED |
| GraphQL: Retry failed transaction | retryCount 0→1, new idempotency key, PROCESSING |
| Webhook: Approve retried transaction | SUCCESS, batch → DONE |
| GraphQL: Upload SOSYS CSV (5 rows) | 2 matched, 1 unmatched, 2 flagged |
| GraphQL: Resolve anomaly | Count 3→2 |
| Final dashboard state | NPR 135,500 disbursed, 100% success, batch DONE |
| GraphiQL browser interface | Working at localhost:8080/graphql/ |
| Django admin panel | Working at localhost:8080/admin/ |

---

## 5. What Remains

### Latest Improvement Pass

| Change | Why It Matters |
|---|---|
| Added `GET /api/transactions/export-csv` | Lets finance officers export the audit ledger before cleanup or demo handoff. |
| Added `DELETE /api/transactions/ledger` | Clears transactions, batches, and stale reconciliation rows while resetting affected claims to `APPROVED`. |
| Added Ledger page `Export CSV` and `Clear Ledger` buttons | Solves the growing-ledger issue and makes repeated hackathon rehearsals cleaner. |
| Documented ledger cleanup as demo-only | Keeps the pitch honest: production should use archive/retention controls instead of hard delete. |

### High Priority (Critical for Demo)

| # | Task | Why It Matters | Effort |
|---|---|---|---|
| 1 | **Record 3-minute backup demo video** | Hackathon demos fail; video is insurance | 15 min |
| 2 | **Practice the live demo script** | 3-minute rehearsed flow for judges | 30 min |
| 3 | **Test standalone frontend → backend full flow** | Verify the React UI at :5173 talks to FastAPI at :8000 end-to-end | 10 min |

### Medium Priority (Nice to Have)

| # | Task | Why It Matters | Effort |
|---|---|---|---|
| 4 | **Run full OpenIMIS Docker stack** | Shows real integration, not test harness | 2+ hours (heavy) |
| 5 | **Deploy OpenIMIS frontend module** | Material-UI components inside OpenIMIS | 1 hour |
| 6 | **Add Nepali translations to standalone frontend** | Bonus points with judges | 30 min |
| 7 | **Create pitch deck / slides** | Professional presentation | 1 hour |

### Low Priority (Future/Production)

| # | Task | Why It Matters | Effort |
|---|---|---|---|
| 8 | **eSewa/ConnectIPS real integration** | Production gateway | 1+ week |
| 9 | **HMAC webhook signature verification** | Production security | 2 hours |
| 10 | **Data encryption at rest** | Production compliance | 2 hours |
| 11 | **django-simple-history audit trail** | Production audit | 1 hour |

---

## 6. How to Run Right Now

### Quick Start (Standalone Demo)
```
cd Final-Implementation
start.bat          # Launches all 3 servers
```
- `http://localhost:3000` → Samanvaya React UI (or `:5173` if Vite)
- `http://localhost:8001/ui` → Mock Bank control panel
- `http://localhost:8000/docs` → FastAPI Swagger docs

### Django Test Harness (Phase B verification)
```
cd Final-Implementation
.\venv_b\Scripts\activate
python manage.py runserver 8080
```
- `http://localhost:8080/graphql/` → GraphiQL (test queries/mutations)
- `http://localhost:8080/admin/` → Django admin (admin/admin123)

### Full OpenIMIS Docker (when ready)
```
cd Final-Implementation
docker-compose up
```
