# Samanvaya — Technical Architecture

This document covers the full technical architecture of Samanvaya as a **standalone module** — a FastAPI backend, React frontend, and a Mock Bank server — designed to run on any laptop without a live OpenIMIS instance.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SAMANVAYA SYSTEM                         │
│                                                                 │
│  ┌──────────────┐      ┌───────────────────┐                   │
│  │  React UI    │◄────►│  FastAPI Backend  │                   │
│  │  Port: 3000  │      │  Port: 8000       │                   │
│  └──────────────┘      └────────┬──────────┘                   │
│                                 │                               │
│                    ┌────────────┼─────────────┐                 │
│                    │            │             │                 │
│              ┌─────▼──┐  ┌─────▼──┐   ┌─────▼──┐             │
│              │SQLite  │  │APSched │   │Gateway │             │
│              │(or PG) │  │Poller  │   │Adapter │             │
│              └────────┘  └────────┘   └────┬───┘             │
│                                            │                   │
└────────────────────────────────────────────┼───────────────────┘
                                             │ HTTP
                                   ┌─────────▼──────────┐
                                   │   Mock Bank Server  │
                                   │   Port: 8001        │
                                   │   (+ Browser UI)    │
                                   └────────────────────┘
```

---

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | FastAPI (Python) | Fast to write, async-native, auto-generates API docs |
| **Database** | SQLite (dev) / PostgreSQL (prod) | SQLite = zero config for the hackathon |
| **ORM** | SQLAlchemy + Alembic | Standard, works with both SQLite and PG |
| **Background Tasks** | APScheduler (lightweight) | For the polling safety net — no Redis/Celery overhead |
| **Frontend** | React + Vite + Tailwind CSS | Instant hot reload, utility-first styling |
| **Charts** | Recharts | Dead simple React chart library |
| **HTTP Client** | Axios (frontend) + httpx (backend) | Async-friendly, clean API |
| **Mock Bank** | FastAPI (separate process) | Isolated, easy to demo interactively |

---

## 3. Data Flow

### Happy Path: Claim → Payment → Success

```
1. CLAIM APPROVED
   Seed data / UI click "Approve Claim"
   → Claim.status = APPROVED
   → Claim added to ClaimsQueue

2. BATCH CREATION
   User selects claims in UI → clicks "Create Batch"
   POST /api/batches
   → PaymentBatch created (status: QUEUED)
   → PaymentTransactions created for each claim (status: PENDING)

3. BATCH EXECUTION
   User clicks "Execute Batch"
   POST /api/batches/{id}/execute
   → Each transaction: PENDING → PROCESSING
   → BulkDisbursementService calls GatewayAdapter.initiate_payout()
   → Gateway (MockBank) receives payout request
   → Transaction status stays PROCESSING (awaiting webhook)

4. BANK APPROVAL (Demo: click "Approve" in Mock Bank UI)
   Mock Bank fires: POST http://localhost:8000/webhook/gateway
   payload: { gateway_ref_id: "...", status: "SUCCESS" }

5. WEBHOOK RECEIVED
   Samanvaya webhook handler:
   → Looks up transaction by gateway_ref_id
   → Row lock (select_for_update)
   → Transaction: PROCESSING → SUCCESS
   → webhook_received_at = now()

6. UI UPDATE
   Frontend polling detects status change
   → Transaction row turns green
   → Dashboard totals update
   → Progress bar reaches "Confirmed"
```

### Failure Path

```
Bank fires: POST /webhook/gateway { status: "FAILED" }
→ Transaction: PROCESSING → FAILED
→ retry_count++, next_retry_at = now() + 5 min
→ UI shows red badge + "Retry" button
→ User clicks Retry → new idempotency_key generated → re-initiates payout
```

### Safety Net Path (Polling)

```
APScheduler fires every 5 minutes:
→ Queries all PROCESSING transactions older than 10 minutes
→ Calls gateway.verify_status(gateway_ref_id) for each
→ Updates status based on bank's current answer
→ Handles the case where the webhook was lost/dropped
```

---

## 4. API Endpoints

### Claims
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/claims` | List all approved claims (seeded demo data) |
| `POST` | `/api/claims/{id}/approve` | Manually approve a claim (simulates OpenIMIS handoff) |

### Batches
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/batches` | Create a new batch from selected claim IDs |
| `GET` | `/api/batches` | List all batches |
| `POST` | `/api/batches/{id}/execute` | Trigger bulk disbursement for a batch |
| `GET` | `/api/batches/{id}/transactions` | List all transactions in a batch |

### Transactions
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/transactions` | Full ledger (filterable by status, date, facility) |
| `GET` | `/api/transactions/{id}` | Transaction detail + raw logs |
| `POST` | `/api/transactions/{id}/retry` | Retry a failed transaction |

### Webhooks
| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook/gateway` | Receives payment status callbacks from Mock Bank |

### Dashboard
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/dashboard/summary` | Total disbursed, success rate, pending count, failed count |
| `GET` | `/api/dashboard/volume` | Daily payment volume (for bar chart) |

### Reconciliation
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/reconciliation/upload` | Upload SOSYS legacy CSV |
| `GET` | `/api/reconciliation/results` | List matched, unmatched, flagged anomalies |
| `POST` | `/api/reconciliation/{id}/resolve` | Mark an anomaly as manually resolved |

---

## 5. Database Schema (Entity Diagram)

```
Claims
  id (UUID, PK)
  claim_code (unique)
  health_facility
  insuree_name
  claimed_amount (NPR)
  approved_amount (NPR)
  status (APPROVED | QUEUED | PROCESSED)
  approved_date
        │
        │ 1:N
        ▼
PaymentTransactions
  id (UUID, PK)
  batch_id (FK → PaymentBatches)
  claim_id (FK → Claims)
  amount
  status (PENDING | PROCESSING | SUCCESS | FAILED | PARTIAL)
  idempotency_key (UUID, unique)
  gateway_name
  gateway_ref_id (unique, nullable)
  raw_request_log (JSON)
  raw_response_log (JSON)
  webhook_received_at
  retry_count
  next_retry_at
  created_at / updated_at
        │
        │ N:1
        ▼
PaymentBatches
  id (UUID, PK)
  created_at
  total_amount
  claim_count
  status (QUEUED | EXECUTING | DONE | PARTIAL | FAILED)

GatewayConfigs
  id
  name (mock_bank | esewa | connectips)
  is_active (bool)
  config (JSON — base URL, credentials, etc.)

SOSYSLegacyLogs               ← Temporary, reconciliation only
  id
  claim_code
  health_facility
  amount
  payment_date
  sosys_status
  match_status (MATCHED | UNMATCHED | FLAGGED)
  notes
```

---

## 6. Frontend Page Map

```
/ (Dashboard)
├── KPI Cards: Total Disbursed | Success Rate | Pending | Failed
├── Bar Chart: Daily payment volume (last 7 days)
├── Pie Chart: Success / Failed / Pending breakdown
└── Alert Banner: "N SOSYS anomalies detected" (if reconciliation uploaded)

/claims (Claims Queue)
├── Table of approved claims (claim code, hospital, amount, date)
├── Checkbox selection → "Create Batch" button
└── "Approve" button on individual claims (for demo control)

/ledger (Transaction Ledger)
├── Searchable, filterable data table
├── Columns: Claim ID | Hospital | Amount | Status | Gateway Ref | Timestamp
├── Status badges (green/red/yellow)
├── Click row → drawer showing raw_request_log + raw_response_log
└── "Retry" button on failed transactions

/reconciliation (Reconciliation Console)
├── Upload CSV button (SOSYS legacy file)
├── Results table: Matched | Unmatched | Flagged Anomalies
└── "Resolve" button per anomaly row
```

---

## 7. Running Locally

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
python seed.py          # Populates DB with demo data
uvicorn main:app --reload --port 8000

# Terminal 2 — Mock Bank
cd mock-bank
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev             # Vite dev server on port 3000
```

Open:
- `http://localhost:3000` → Samanvaya UI
- `http://localhost:8001/ui` → Mock Bank control panel
- `http://localhost:8000/docs` → FastAPI auto-generated API docs (Swagger)

---

## 8. OpenIMIS Compatibility Notes

Even though this runs standalone, every design decision is made with future OpenIMIS integration in mind:

- **Data models** mirror OpenIMIS's `Claim`, `HealthFacility`, and `ClaimBundle` naming
- **The claims layer** (seeded data + approve endpoint) is a drop-in stand-in for OpenIMIS's GraphQL claim approval output — replace it with a real GraphQL subscription when integrating
- **The gateway adapter** is already abstractly designed — plugging into OpenIMIS's Celery task queue is straightforward
- **The webhook receiver** is stateless and can be exposed through OpenIMIS's Django URL routing without changes

When OpenIMIS integration becomes feasible, the migration path is: replace `Claim` seed data → wire up to OpenIMIS GraphQL → done.
