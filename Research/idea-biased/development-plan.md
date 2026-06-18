# Samanvaya — Detailed Development Plan

A phased, task-by-task development plan for building **Samanvaya** as a standalone payment execution module — a FastAPI backend, React frontend, and Mock Bank server — designed to replace SOSYS and give OpenIMIS full end-to-end financial visibility.

---

## Phase 1: Project Setup & Foundation

**Goal:** Get the development environment running, define all data models, seed realistic demo data, and verify the skeleton end-to-end.

### Task 1.1 — Initialize Backend Project

- Create `backend/` directory with the following structure:
  ```
  backend/
  ├── main.py
  ├── database.py
  ├── models.py
  ├── schemas.py
  ├── seed.py
  ├── routers/
  │   ├── __init__.py
  │   ├── claims.py
  │   ├── batches.py
  │   ├── transactions.py
  │   ├── reconciliation.py
  │   ├── dashboard.py
  │   └── webhooks.py
  ├── services/
  │   ├── __init__.py
  │   ├── disbursement.py
  │   ├── reconciliation.py
  │   ├── poller.py
  │   └── gateway/
  │       ├── __init__.py
  │       ├── base.py
  │       ├── mock_bank.py
  │       └── esewa.py
  └── requirements.txt
  ```
- Create `requirements.txt` with: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `httpx`, `apscheduler`, `python-multipart`
- Set up Python virtual environment and install dependencies
- **Verification:** Run `uvicorn main:app --reload --port 8000` and confirm `http://localhost:8000/docs` loads Swagger UI

### Task 1.2 — Configure Database & ORM

- In `database.py`:
  - Set up SQLAlchemy engine pointing to SQLite (`sqlite:///./samanvaya.db`)
  - Create `SessionLocal` and `get_db` dependency
  - Define `Base = declarative_base()`
- In `main.py`:
  - Register CORS middleware (`allow_origins=["*"]`)
  - Add startup event to create all tables (`Base.metadata.create_all`)
  - Register all routers with `/api` prefix
- **Verification:** Start the server and confirm `samanvaya.db` file is created

### Task 1.3 — Define All Database Models (`models.py`)

Create the following SQLAlchemy models mirroring OpenIMIS naming conventions:

| Model | Table Name | Key Columns |
|---|---|---|
| `Claim` | `claims` | `id` (UUID PK), `claim_code` (unique), `health_facility`, `insuree_name`, `claimed_amount`, `approved_amount`, `status` (APPROVED/QUEUED/PROCESSED), `approved_date` |
| `PaymentBatch` | `payment_batches` | `id` (UUID PK), `created_at`, `total_amount`, `claim_count`, `status` (QUEUED/EXECUTING/DONE/PARTIAL/FAILED) |
| `PaymentTransaction` | `payment_transactions` | `id` (UUID PK), `batch_id` (FK), `claim_id` (FK), `amount`, `status` (PENDING/PROCESSING/SUCCESS/FAILED/PARTIAL), `idempotency_key` (UUID unique), `gateway_name`, `gateway_ref_id` (unique nullable), `raw_request_log` (JSON), `raw_response_log` (JSON), `webhook_received_at`, `retry_count`, `next_retry_at`, `created_at`, `updated_at` |
| `GatewayConfig` | `gateway_configs` | `id`, `name` (mock_bank/esewa/connectips), `is_active` (bool), `config` (JSON) |
| `SOSYSLegacyLog` | `sosys_legacy_logs` | `id`, `claim_code`, `health_facility`, `amount`, `payment_date`, `sosys_status`, `match_status` (MATCHED/UNMATCHED/FLAGGED), `notes` |

- Define Python enums for `ClaimStatus` and `TransactionStatus`
- **Verification:** Restart server, confirm all tables appear in SQLite via DB browser or raw query

### Task 1.4 — Define Pydantic Schemas (`schemas.py`)

Create request/response schemas for every API endpoint:
- `ClaimResponse`, `ClaimListResponse`
- `BatchCreateRequest` (list of claim IDs), `BatchResponse`
- `TransactionResponse`, `TransactionDetailResponse` (includes raw logs)
- `DashboardSummaryResponse` (total_disbursed, success_rate, pending_count, failed_count)
- `DashboardVolumeResponse` (daily totals for chart)
- `ReconciliationUploadResponse`, `ReconciliationResultResponse`
- `WebhookPayload` (gateway_ref_id, status)
- **Verification:** Schemas import cleanly with no errors

### Task 1.5 — Seed Realistic Demo Data (`seed.py`)

- Create `seed.py` that populates the database with ~20 realistic claims:
  - Hospitals: "Bir Hospital", "Civil Hospital", "Patan Hospital", "Nepal Medical College", "Grande International Hospital"
  - Claim amounts in NPR (range: NPR 5,000 – NPR 150,000)
  - Insuree names: realistic Nepali names
  - Claim codes: `CLM-2024-001` through `CLM-2024-020`
  - Mix of statuses: ~15 APPROVED (ready to pay), ~5 already PROCESSED
- Seed one `GatewayConfig` row: `name="mock_bank"`, `is_active=True`
- **Verification:** Run `python seed.py`, then hit `GET /api/claims` in Swagger and confirm data returns

### Task 1.6 — Implement Claims Router (`routers/claims.py`)

| Endpoint | Method | Logic |
|---|---|---|
| `/api/claims` | GET | Return all claims (filterable by status query param) |
| `/api/claims/{id}/approve` | POST | Set `Claim.status = APPROVED`, set `approved_date = now()` |

- **Verification:** Use Swagger UI to list claims and approve one

---

## Phase 2: Core Payment Engine & Ledger

**Goal:** Build the bulk disbursement engine, transaction ledger, and gateway adapter — the financial heart of Samanvaya.

### Task 2.1 — Build the Gateway Adapter Interface (`services/gateway/base.py`)

- Define `PayoutResponse` dataclass: `success`, `gateway_ref`, `status`, `raw_response`, `request_payload`, `error_msg`
- Define abstract `BasePaymentGateway` with methods:
  - `initiate_payout(ref_id, amount, recipient) -> PayoutResponse`
  - `verify_status(gateway_ref) -> PayoutResponse`
- **Verification:** File imports without errors

### Task 2.2 — Implement MockBank Gateway Adapter (`services/gateway/mock_bank.py`)

- `MockBankGateway(BasePaymentGateway)`:
  - `BASE_URL = "http://localhost:8001"`
  - `initiate_payout`: POST to `{BASE_URL}/payout` with `{ref_id, amount, recipient}`, return `PayoutResponse` with status `INITIATED`
  - `verify_status`: GET `{BASE_URL}/status/{gateway_ref}`, return current status
- Handle connection errors gracefully (return `FAILED` with error message if bank is unreachable)
- **Verification:** Unit test or manual call against a running Mock Bank (built in Phase 3)

### Task 2.3 — Implement eSewa Gateway Stub (`services/gateway/esewa.py`)

- `ESewaGateway(BasePaymentGateway)`:
  - Both methods raise `NotImplementedError` with descriptive message
  - Add comments explaining what a real eSewa integration would do (HMAC signing, FTPL format, etc.)
- **Verification:** Importing works; calling methods raises the expected error

### Task 2.4 — Build the Bulk Disbursement Service (`services/disbursement.py`)

- `BulkDisbursementService.__init__(db, gateway: BasePaymentGateway)`
- `execute_batch(batch_id)`:
  1. Fetch the `PaymentBatch` by ID
  2. Fetch all `PaymentTransaction` rows for that batch
  3. Set batch status to `EXECUTING`
  4. For each PENDING transaction:
     - Set status to `PROCESSING`
     - Call `gateway.initiate_payout(ref_id=str(tx.idempotency_key), amount=tx.amount, recipient=tx.claim.health_facility)`
     - Store `raw_request_log`, `raw_response_log`, `gateway_ref_id`
     - If response status is `SUCCESS` → mark `SUCCESS`
     - If response status is `FAILED` → mark `FAILED`
     - Otherwise → leave as `PROCESSING` (awaiting webhook)
  5. After all transactions processed, update batch status:
     - All SUCCESS → `DONE`
     - Some SUCCESS, some FAILED → `PARTIAL`
     - All FAILED → `FAILED`
     - Any PROCESSING → `PARTIAL` (awaiting webhooks)
- `retry_transaction(transaction_id)`:
  1. Verify transaction status is `FAILED`
  2. Generate new `idempotency_key`
  3. Reset status to `PENDING`, increment `retry_count`
  4. Call `gateway.initiate_payout` again
- **Verification:** Create a batch via API, execute it, confirm transactions move to PROCESSING

### Task 2.5 — Build Batches Router (`routers/batches.py`)

| Endpoint | Method | Logic |
|---|---|---|
| `POST /api/batches` | POST | Accept list of claim IDs → create `PaymentBatch` + `PaymentTransaction` rows (status PENDING), set claims to QUEUED |
| `GET /api/batches` | GET | List all batches with summary info |
| `POST /api/batches/{id}/execute` | POST | Instantiate `BulkDisbursementService` with active gateway → call `execute_batch` |
| `GET /api/batches/{id}/transactions` | GET | List all transactions for a batch |

- **Verification:** Full Swagger flow — create batch, list batches, execute, check transactions

### Task 2.6 — Build Transactions Router (`routers/transactions.py`)

| Endpoint | Method | Logic |
|---|---|---|
| `GET /api/transactions` | GET | Full ledger with optional filters: `status`, `health_facility`, `date_from`, `date_to` |
| `GET /api/transactions/{id}` | GET | Transaction detail including `raw_request_log` and `raw_response_log` |
| `POST /api/transactions/{id}/retry` | POST | Call `disbursement.retry_transaction()` |

- **Verification:** Execute a batch, then query ledger and detail endpoints in Swagger

### Task 2.7 — Build Webhook Receiver (`routers/webhooks.py`)

- `POST /webhook/gateway`:
  1. Extract `gateway_ref_id` and `status` from payload
  2. Query `PaymentTransaction` by `gateway_ref_id` with `with_for_update()` (row lock)
  3. If transaction not found or already in terminal state → return `{"ok": True, "note": "already_processed"}`
  4. Update status to `SUCCESS` or `FAILED` based on payload
  5. Set `webhook_received_at = datetime.utcnow()`
  6. Store `raw_response_log = payload`
  7. Check if all transactions in the batch are now terminal → update batch status
  8. Commit and return `{"ok": True}`
- **Verification:** Manually POST a webhook payload via Swagger and confirm transaction status updates

### Task 2.8 — Build the Polling Safety Net (`services/poller.py`)

- Use `APScheduler` with `AsyncIOScheduler`
- Scheduled job every 5 minutes:
  1. Query all `PaymentTransaction` where `status == PROCESSING` and `created_at < now() - 10 minutes`
  2. For each, call `gateway.verify_status(gateway_ref_id)`
  3. Update transaction status accordingly
- Register scheduler in `main.py` startup/shutdown events
- **Verification:** Leave a transaction in PROCESSING state, wait for poll cycle, confirm it updates

---

## Phase 3: Mock Bank Server

**Goal:** Build the interactive mock bank that makes the demo compelling — a separate FastAPI server with a simple UI for approving/rejecting payouts.

### Task 3.1 — Initialize Mock Bank Server

- Create `mock-bank/` directory:
  ```
  mock-bank/
  ├── main.py
  ├── ui/
  │   └── index.html
  └── requirements.txt
  ```
- `requirements.txt`: `fastapi`, `uvicorn`, `httpx`
- **Verification:** Start on port 8001, confirm it responds

### Task 3.2 — Build Mock Bank API (`mock-bank/main.py`)

| Endpoint | Method | Logic |
|---|---|---|
| `POST /payout` | POST | Receive `{ref_id, amount, recipient}` → store in in-memory `pending_payouts` dict with status `PENDING` → return `{gateway_ref_id: ref_id, status: "INITIATED"}` |
| `GET /status/{ref_id}` | GET | Return current status of payout from in-memory dict |
| `GET /pending` | GET | Return all payouts with status `PENDING` |
| `POST /approve/{ref_id}` | POST | Set status to `SUCCESS` → fire webhook `POST http://localhost:8000/webhook/gateway` with `{gateway_ref_id, status: "SUCCESS"}` |
| `POST /reject/{ref_id}` | POST | Set status to `FAILED` → fire webhook with `{status: "FAILED"}` |

- Serve static HTML UI at `/ui`
- Add CORS middleware for browser access
- **Verification:** POST a payout, check `/pending`, approve it, confirm webhook fires to Samanvaya

### Task 3.3 — Build Mock Bank Control Panel UI (`mock-bank/ui/index.html`)

- Single-page HTML + vanilla JS:
  - Heading: "Mock Bank Control Panel"
  - Auto-refreshing list of pending payouts (poll `/pending` every 3 seconds)
  - Each payout shows: recipient name, amount (NPR), ref_id
  - "Approve" button → calls `POST /approve/{ref_id}`
  - "Reject" button → calls `POST /reject/{ref_id}`
  - List refreshes automatically after action
- Clean, minimal styling (border cards, clear buttons, green for approve, red for reject)
- **Verification:** Open `http://localhost:8001/ui` in browser, see pending payouts, click approve/reject

---

## Phase 4: Reconciliation Engine

**Goal:** Demonstrate the SOSYS-to-Samanvaya migration story with CSV upload and anomaly detection.

### Task 4.1 — Generate Mock SOSYS Legacy CSV

- Create `sosys_legacy.csv` with ~20 records:
  - Columns: `claim_code`, `health_facility`, `amount`, `payment_date`, `status`
  - Include intentional mismatches:
    - 2-3 records with claim codes that don't exist in Samanvaya (unmatched)
    - 2 records with amounts that differ from Samanvaya's records (amount mismatch)
    - 1 duplicate payment (same claim code, paid twice)
    - 1 missing claim (exists in Samanvaya but not in SOSYS)
  - Use same hospital names and NPR amounts as seed data

### Task 4.2 — Build Reconciliation Router (`routers/reconciliation.py`)

| Endpoint | Method | Logic |
|---|---|---|
| `POST /api/reconciliation/upload` | POST | Accept CSV file upload → parse rows → insert into `SOSYSLegacyLogs` table |
| `GET /api/reconciliation/results` | GET | Return all rows with `match_status` populated |
| `POST /api/reconciliation/{id}/resolve` | POST | Mark a flagged anomaly as manually resolved |

### Task 4.3 — Build Reconciliation Matching Algorithm (`services/reconciliation.py`)

- `reconcile(db)` function:
  1. Load all `SOSYSLegacyLogs`
  2. Load all `PaymentTransaction` records
  3. Match on `claim_code`:
     - Exact match on claim_code + amount → `MATCHED`
     - claim_code exists in both but amounts differ → `FLAGGED` (amount mismatch)
     - claim_code only in SOSYS → `UNMATCHED` (no Samanvaya record)
     - claim_code only in Samanvaya → `UNMATCHED` (missing from SOSYS)
  4. Detect duplicates: same claim_code appears more than once in SOSYS logs → `FLAGGED`
  5. Write `match_status` and `notes` back to `SOSYSLegacyLogs`
  6. Return summary counts: matched, unmatched, flagged
- **Verification:** Upload the mock CSV via Swagger, call results endpoint, confirm anomalies appear correctly

---

## Phase 5: Dashboard API

**Goal:** Build the summary endpoints that power the financial dashboard.

### Task 5.1 — Build Dashboard Router (`routers/dashboard.py`)

| Endpoint | Method | Logic |
|---|---|---|
| `GET /api/dashboard/summary` | GET | Calculate: total disbursed (sum of SUCCESS amounts), success rate %, pending count, failed count |
| `GET /api/dashboard/volume` | GET | Group transactions by date, return daily totals for last 7 days (for bar chart) |
| `GET /api/dashboard/anomaly-count` | GET | Count of FLAGGED items from `SOSYSLegacyLogs` |

- **Verification:** Execute some batches, then query summary — numbers should match

---

## Phase 6: Frontend — React Application

**Goal:** Build a polished, clear UI that judges can understand in 5 seconds.

### Task 6.1 — Initialize Frontend Project

- Run `npm create vite@latest frontend -- --template react`
- Install dependencies: `tailwindcss`, `recharts`, `axios`, `react-router-dom`
- Configure Tailwind CSS
- Set up `src/api/client.js` with Axios base URL `http://localhost:8000`
- Set up React Router with routes: `/` (Dashboard), `/claims` (Claims Queue), `/ledger` (Transaction Ledger), `/reconciliation` (Reconciliation Console)
- **Verification:** `npm run dev` loads a blank page at `http://localhost:3000`

### Task 6.2 — Build Shared Components

- `StatusBadge.jsx` — Color-coded pill: green (SUCCESS), red (FAILED), yellow (PENDING/PROCESSING), gray (PARTIAL)
- `PaymentProgressBar.jsx` — 4-step visual: "Claim Approved" → "Queued in Samanvaya" → "Sent to Bank" → "Confirmed"
- `AnomalyAlert.jsx` — Pulsing red banner showing "N SOSYS Anomalies Detected"
- `Navbar.jsx` — Navigation links to all 4 pages
- `Layout.jsx` — Common layout wrapper with navbar

### Task 6.3 — Build Dashboard Page (`pages/Dashboard.jsx`)

- **KPI Cards** (top row):
  - Total Disbursed Today (NPR)
  - Success Rate (%)
  - Pending Count
  - Failed Count
- **Charts**:
  - Pie chart: Success / Failed / Pending breakdown (Recharts `PieChart`)
  - Bar chart: Daily payment volume, last 7 days (Recharts `BarChart`)
- **Alert Banner**: Show `AnomalyAlert` if anomaly count > 0
- Poll `/api/dashboard/summary` and `/api/dashboard/volume` every 5 seconds
- **Verification:** Dashboard loads, cards show correct numbers, charts render

### Task 6.4 — Build Claims Queue Page (`pages/ClaimsQueue.jsx`)

- Table of all APPROVED claims: claim_code, health_facility, insuree_name, approved_amount, approved_date
- Checkbox column for row selection
- "Create Batch" button:
  1. Collect selected claim IDs
  2. `POST /api/batches` with claim IDs
  3. Navigate to batch detail or show success toast
- "Approve" button per row (for demo: manually approve a claim)
- Show list of existing batches below the table with status badges
- "Execute Batch" button per batch → `POST /api/batches/{id}/execute`
- After execution, start polling batch transactions to show live status updates
- **Verification:** Select claims → create batch → execute → watch statuses change

### Task 6.5 — Build Transaction Ledger Page (`pages/TransactionLedger.jsx`)

- Searchable, filterable data table:
  - Columns: Claim ID, Hospital, Amount (NPR), Status (badge), Gateway Ref, Timestamp
  - Filters: status dropdown, date range picker, hospital text search
- Click a row → expandable drawer/panel showing:
  - `raw_request_log` (formatted JSON)
  - `raw_response_log` (formatted JSON)
  - `idempotency_key`, `retry_count`, `webhook_received_at`
- "Retry" button on FAILED transactions → `POST /api/transactions/{id}/retry`
- **Verification:** After executing batches, ledger shows all transactions with correct statuses

### Task 6.6 — Build Reconciliation Console Page (`pages/Reconciliation.jsx`)

- "Upload SOSYS CSV" button with drag-and-drop file input
  - `POST /api/reconciliation/upload` (multipart form data)
- Results table with tabs or filter buttons: All / Matched / Unmatched / Flagged
  - Columns: claim_code, health_facility, amount, sosys_status, match_status, notes
  - Color-coded rows: green (MATCHED), orange (UNMATCHED), red (FLAGGED)
- "Resolve" button per flagged row → `POST /api/reconciliation/{id}/resolve`
- Summary bar at top: "15 Matched | 3 Unmatched | 2 Flagged"
- **Verification:** Upload mock CSV, see anomalies appear, resolve one

---

## Phase 7: Integration Testing & End-to-End Flow

**Goal:** Wire everything together and verify the complete happy path, failure path, and safety net path.

### Task 7.1 — Test Happy Path End-to-End

1. Start all 3 servers (backend:8000, mock-bank:8001, frontend:3000)
2. Run `seed.py` to populate demo data
3. Open frontend → go to Claims Queue
4. Select 3 claims → Create Batch → Execute Batch
5. Observe transactions move to PROCESSING
6. Open Mock Bank UI (`localhost:8001/ui`)
7. Click "Approve" on one payout → verify Samanvaya shows SUCCESS in real-time
8. Click "Reject" on another → verify Samanvaya shows FAILED
9. Check Dashboard → KPI cards and charts update correctly
10. Check Ledger → raw logs visible, status badges correct

### Task 7.2 — Test Failure & Retry Path

1. Reject a transaction via Mock Bank
2. In Ledger, click "Retry" on the failed transaction
3. Verify new idempotency key generated, transaction re-enters PROCESSING
4. Approve the retried transaction in Mock Bank
5. Verify it reaches SUCCESS

### Task 7.3 — Test Reconciliation Flow

1. Go to Reconciliation Console
2. Upload `sosys_legacy.csv`
3. Verify matched, unmatched, and flagged items appear correctly
4. Resolve a flagged anomaly
5. Verify dashboard anomaly count decreases

### Task 7.4 — Test Polling Safety Net

1. Execute a batch but don't approve/reject in Mock Bank
2. Wait for the polling interval (or temporarily reduce to 1 minute for testing)
3. Verify poller picks up stale PROCESSING transactions and updates them

---

## Phase 8: Demo Polish & Pitch Preparation

**Goal:** Flawless demo, tight pitch, nothing left to chance.

### Task 8.1 — UI Polish

- Ensure consistent styling across all pages
- Add loading spinners for API calls
- Add empty-state messages ("No claims selected", "No transactions yet")
- Add toast notifications for batch creation, execution, retry actions
- Ensure responsive layout works on standard laptop resolution

### Task 8.2 — Create One-Click Startup Scripts

Two batch files have been created in the project root:

- `start.bat` — Launches all 3 servers in separate command windows:
  - Backend: runs `seed.py` then starts `uvicorn` on port 8000
  - Mock Bank: starts `uvicorn` on port 8001
  - Frontend: runs `npm run dev` (Vite on port 3000)
- `stop.bat` — Kills all running server processes

After running `start.bat`, the following are available:
- `http://localhost:3000` — Samanvaya UI
- `http://localhost:8001/ui` — Mock Bank control panel
- `http://localhost:8000/docs` — FastAPI auto-generated API docs (Swagger)

- **Verification:** Double-click `start.bat`, confirm all 3 windows open and servers respond

### Task 8.3 — Rehearse the 3-Minute Demo Script

Practice the following flow until automatic:

| Time | Action | Talking Point |
|---|---|---|
| 0:00 | Open Dashboard | "This is the financial nerve center OpenIMIS never had." |
| 0:20 | Go to Claims Queue, select 3 claims, create batch, execute | "These are approved claims. Right now they'd go to SOSYS. With Samanvaya, they don't." |
| 0:50 | Watch PROCESSING, switch to Mock Bank UI | "The batch is with the bank. Samanvaya tracks every rupee." |
| 1:10 | Click Approve in Mock Bank, switch back — SUCCESS | "Webhook came back. Dashboard updates in real time." |
| 1:30 | Click Reject on second transaction — FAILED | "Failed payments flagged immediately. No manual reconciliation." |
| 1:45 | Go to Ledger, click a row, show raw logs | "Full audit trail. Every byte logged." |
| 2:15 | Upload SOSYS CSV in Reconciliation | "Migration bridge. Catches double payments automatically." |
| 2:45 | Closing | "Samanvaya closes the loop OpenIMIS was missing." |

### Task 8.4 — Prepare Technical Q&A Answers

Memorize responses to these expected judge questions:

1. **"What if the bank's webhook never arrives?"** → Active polling every 5 min, checks PROCESSING transactions older than 10 min
2. **"What prevents double payments?"** → UUID idempotency key + DB row locking with `select_for_update`
3. **"Why not plug into OpenIMIS directly?"** → Compatible by design; claims layer is a stand-in for OpenIMIS GraphQL; integration = replace seed data with live subscription
4. **"How would eSewa/ConnectIPS work?"** → Strategy Pattern; 3-method interface (`initiate_payout`, `verify_status`, `process_webhook`); swap adapter, keep all logic

### Task 8.5 — Record Backup Demo Video

- 3-minute screencast of the perfect flow (screen + audio narration)
- This is insurance against live demo failures

---

## Scope Management — Priority Cuts

If time runs short, cut in this order (least critical first):

| Priority | Cut This | Keep At All Costs |
|---|---|---|
| 1st to drop | Reconciliation Engine full logic | Core payment flow (Claim → Batch → Execute → Success) |
| 2nd to drop | Retry UI button | Mock Bank interactive webhook demo |
| 3rd to drop | Active polling background task | Financial Dashboard (KPI cards + 1 chart) |
| 4th to drop | eSewa gateway stub | Transaction Ledger with status badges |
| 5th to drop | Dashboard charts | The one-line pitch, practiced and tight |

> You can *talk* about cut features confidently as "built and tested" — judges won't ask to see the code.

---

## Key Technical Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI | Async-native, auto-docs, fast to build |
| Database (hackathon) | SQLite | Zero config, works on any laptop |
| Database (production) | PostgreSQL | Swap via SQLAlchemy connection string |
| Frontend | React + Vite + Tailwind | Instant hot reload, clean utility styling |
| Charts | Recharts | Simple React-native charting |
| Background polling | APScheduler | Lightweight, no Redis/Celery overhead |
| Gateway pattern | Strategy/Adapter | Swap MockBank → eSewa with zero logic changes |
| State management | Local React state + polling | No Redux complexity needed for this scope |
| Live updates | 3-second polling | Simpler and more reliable than WebSockets for demo |
