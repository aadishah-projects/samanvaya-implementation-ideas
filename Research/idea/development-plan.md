# Samanvaya — Development Plan: Standalone Build & OpenIMIS Integration

A phased, task-by-task plan to build Samanvaya as a **standalone payment engine** first (for reliable hackathon demo), then **integrate it as a native OpenIMIS module** — Django backend, React frontend, GraphQL API, Celery async workers.

---

## Architecture Overview

```
PHASE A (Standalone — Hackathon Demo):
  FastAPI Backend + React Frontend + Mock Bank Server
  → Runs on any laptop, no OpenIMIS dependency

PHASE B (OpenIMIS Integration — Production Path):
  Django Module (openimis-be-samanvaya) + React Module (openimis-fe-samanvaya)
  → Native OpenIMIS citizen: Django Signals, GraphQL, Celery, Material-UI
```

### Existing Code Baseline

The current `implementation6` provides a working reconciliation dashboard (FastAPI + PostgreSQL + inline HTML). Key assets to carry forward:
- Reconciliation SQL logic (`RECONCILE_SQL` in `main.py`)
- Data extraction modules (`extract_openimis.py`, `extract_sosys.py`)
- Mock FHIR/GraphQL servers (`mock_fhir.py`, `mock_openimis_graphql.py`)
- PostgreSQL schema for `staging_openimis_claims` and `staging_sosys_payments`
- Stats computation and risk-level classification logic

---

## PHASE A: Standalone Build (Hackathon-Ready)

---

### Phase A1 — Project Setup & Foundation

**Goal:** Clean project structure, database models, seeded demo data, Swagger API docs.

#### Task A1.1 — Initialize Project Structure

```
samanvaya-standalone/
├── backend/
│   ├── main.py                  # FastAPI entry, CORS, router registration
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # All DB models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── seed.py                  # Realistic Nepali demo data
│   ├── routers/
│   │   ├── claims.py            # GET claims, POST approve
│   │   ├── batches.py           # POST create batch, POST execute
│   │   ├── transactions.py      # GET ledger, GET detail, POST retry
│   │   ├── reconciliation.py    # POST upload CSV, GET anomalies
│   │   ├── dashboard.py         # GET summary stats, volume
│   │   └── webhooks.py          # POST /webhook/gateway
│   ├── services/
│   │   ├── disbursement.py      # Bulk payment engine + state machine
│   │   ├── reconciliation.py    # SOSYS CSV matching algorithm
│   │   ├── poller.py            # APScheduler polling safety net
│   │   └── gateway/
│   │       ├── base.py          # Abstract gateway interface
│   │       ├── mock_bank.py     # MockBank adapter
│   │       └── esewa.py         # eSewa stub (production swap-in)
│   └── requirements.txt
├── mock-bank/
│   ├── main.py                  # Payout queue, approve/reject
│   ├── ui/index.html            # Control panel HTML+JS
│   └── requirements.txt
├── frontend/                    # React (Phase A6)
└── start.bat / stop.bat         # One-click launch scripts
```

- **Backend stack:** FastAPI, SQLAlchemy, SQLite (dev) / PostgreSQL (prod), APScheduler, httpx
- **Verification:** `uvicorn main:app --reload --port 8000` → Swagger at `localhost:8000/docs`

#### Task A1.2 — Define Database Models (`models.py`)

| Model | Table | Key Fields |
|---|---|---|
| `Claim` | `claims` | `id` (UUID PK), `claim_code` (unique, e.g. `CLM-2024-001`), `health_facility`, `insuree_name`, `claimed_amount` (NPR), `approved_amount` (NPR), `status` (APPROVED/QUEUED/PROCESSED), `approved_date` |
| `PaymentBatch` | `payment_batches` | `id` (UUID PK), `created_at`, `total_amount`, `claim_count`, `status` (QUEUED/EXECUTING/DONE/PARTIAL/FAILED) |
| `PaymentTransaction` | `payment_transactions` | `id` (UUID PK), `batch_id` (FK), `claim_id` (FK), `amount`, `status` (PENDING/PROCESSING/SUCCESS/FAILED/PARTIAL), `idempotency_key` (UUID unique), `gateway_name`, `gateway_ref_id` (unique nullable), `raw_request_log` (JSON), `raw_response_log` (JSON), `webhook_received_at`, `retry_count`, `next_retry_at`, `created_at`, `updated_at` |
| `GatewayConfig` | `gateway_configs` | `id`, `name`, `is_active`, `config` (JSON) |
| `SOSYSLegacyLog` | `sosys_legacy_logs` | `id`, `claim_code`, `health_facility`, `amount`, `payment_date`, `sosys_status`, `match_status` (MATCHED/UNMATCHED/FLAGGED), `notes` |

- Enums: `ClaimStatus` (APPROVED, QUEUED, PROCESSED), `TransactionStatus` (PENDING, PROCESSING, SUCCESS, FAILED, PARTIAL)
- **Verification:** Server starts, all tables created in SQLite

#### Task A1.3 — Seed Demo Data (`seed.py`)

- ~20 realistic claims with Nepali context:
  - Hospitals: Bir Hospital, Civil Hospital, Patan Hospital, Nepal Medical College, Grande International Hospital
  - Amounts: NPR 5,000 – NPR 150,000
  - Claim codes: `CLM-2024-001` through `CLM-2024-020`
  - Mix: ~15 APPROVED (ready to pay), ~5 already PROCESSED
- 1 GatewayConfig: `mock_bank`, `is_active=True`
- **Port existing reconciliation data:** Migrate `staging_openimis_claims` data into `claims` table format for continuity
- **Verification:** `python seed.py` → `GET /api/claims` returns seeded data

#### Task A1.4 — Implement Claims Router

| Endpoint | Method | Logic |
|---|---|---|
| `/api/claims` | GET | List all claims (filterable by `status`) |
| `/api/claims/{id}/approve` | POST | Set status = APPROVED, set `approved_date` |

---

### Phase A2 — Core Payment Engine & Ledger

**Goal:** Build the financial heart — bulk disbursement, transaction state machine, gateway adapter, webhook receiver.

#### Task A2.1 — Gateway Adapter Interface (`services/gateway/base.py`)

- `PayoutResponse` dataclass: `success`, `gateway_ref`, `status`, `raw_response`, `request_payload`, `error_msg`
- Abstract `BasePaymentGateway`:
  - `initiate_payout(ref_id, amount, recipient) → PayoutResponse`
  - `verify_status(gateway_ref) → PayoutResponse`

#### Task A2.2 — MockBank Adapter (`services/gateway/mock_bank.py`)

- `MockBankGateway(BasePaymentGateway)`:
  - `BASE_URL = "http://localhost:8001"`
  - `initiate_payout`: POST `/payout` → returns `INITIATED`
  - `verify_status`: GET `/status/{ref}` → returns current status
  - Graceful error handling if bank is unreachable

#### Task A2.3 — eSewa Gateway Stub (`services/gateway/esewa.py`)

- `ESewaGateway(BasePaymentGateway)`:
  - Both methods raise `NotImplementedError`
  - Documented comments for production: HMAC signing, FTPL payload format, merchant keys

#### Task A2.4 — Bulk Disbursement Service (`services/disbursement.py`)

- `BulkDisbursementService.__init__(db, gateway)`
- `execute_batch(batch_id)`:
  1. Fetch batch + transactions
  2. Set batch → `EXECUTING`
  3. For each PENDING transaction:
     - Set → `PROCESSING`
     - Call `gateway.initiate_payout(idempotency_key, amount, hospital)`
     - Store `raw_request_log`, `raw_response_log`, `gateway_ref_id`
     - Map response to status (SUCCESS / FAILED / stay PROCESSING)
  4. Compute final batch status: DONE / PARTIAL / FAILED
- `retry_transaction(transaction_id)`:
  1. Verify status = FAILED
  2. Generate new `idempotency_key`
  3. Re-initiate payout
- **Edge cases:** Partial batch success, idempotency on retries, graceful gateway timeout

#### Task A2.5 — Batches Router

| Endpoint | Method | Logic |
|---|---|---|
| `POST /api/batches` | POST | Accept claim IDs → create `PaymentBatch` + `PaymentTransaction` rows (PENDING), set claims → QUEUED |
| `GET /api/batches` | GET | List all batches |
| `POST /api/batches/{id}/execute` | POST | Instantiate disbursement service → `execute_batch` |
| `GET /api/batches/{id}/transactions` | GET | List transactions for a batch |

#### Task A2.6 — Transactions Router

| Endpoint | Method | Logic |
|---|---|---|
| `GET /api/transactions` | GET | Full ledger (filters: status, facility, date range) |
| `GET /api/transactions/{id}` | GET | Detail with raw logs |
| `POST /api/transactions/{id}/retry` | POST | Call `retry_transaction` |

#### Task A2.7 — Webhook Receiver (`routers/webhooks.py`)

- `POST /webhook/gateway`:
  1. Extract `gateway_ref_id`, `status`
  2. Row lock: `with_for_update()` on matching transaction
  3. Idempotency: skip if already in terminal state
  4. Update status + `webhook_received_at` + `raw_response_log`
  5. Check batch completion → update batch status
  6. Return `{"ok": true}`

#### Task A2.8 — Polling Safety Net (`services/poller.py`)

- APScheduler `AsyncIOScheduler`, every 5 minutes:
  1. Query `PROCESSING` transactions older than 10 minutes
  2. Call `gateway.verify_status(gateway_ref_id)` for each
  3. Update status accordingly
- Register in `main.py` startup/shutdown

#### Task A2.9 — Dashboard Router

| Endpoint | Method | Logic |
|---|---|---|
| `GET /api/dashboard/summary` | GET | Total disbursed, success rate %, pending count, failed count |
| `GET /api/dashboard/volume` | GET | Daily payment volume (last 7 days) for bar chart |
| `GET /api/dashboard/anomaly-count` | GET | Count of FLAGGED SOSYS legacy items |

---

### Phase A3 — Mock Bank Server

**Goal:** Interactive bank simulator with approve/reject UI — the demo's "wow" moment.

#### Task A3.1 — Mock Bank API (`mock-bank/main.py`, port 8001)

| Endpoint | Method | Logic |
|---|---|---|
| `POST /payout` | POST | Store payout in-memory, status = PENDING, return `{gateway_ref_id, status: "INITIATED"}` |
| `GET /status/{ref_id}` | GET | Return current payout status |
| `GET /pending` | GET | All PENDING payouts |
| `POST /approve/{ref_id}` | POST | Set SUCCESS → fire webhook to `localhost:8000/webhook/gateway` |
| `POST /reject/{ref_id}` | POST | Set FAILED → fire webhook with FAILED status |

#### Task A3.2 — Mock Bank Control Panel UI (`mock-bank/ui/index.html`)

- Auto-refreshing list of pending payouts (poll `/pending` every 3s)
- Each payout: recipient, amount (NPR), ref_id
- "Approve" (green) / "Reject" (red) buttons
- Clean minimal HTML + vanilla JS

---

### Phase A4 — Reconciliation Engine

**Goal:** SOSYS → Samanvaya migration bridge with anomaly detection.

#### Task A4.1 — Generate Mock SOSYS CSV

- ~20 records with intentional mismatches:
  - 2-3 non-existent claim codes (unmatched)
  - 2 amount discrepancies
  - 1 duplicate payment
  - 1 missing claim (in Samanvaya but not SOSYS)
- **Carry forward:** Adapt existing `RECONCILE_SQL` logic from implementation6 for the matching algorithm

#### Task A4.2 — Reconciliation Router

| Endpoint | Method | Logic |
|---|---|---|
| `POST /api/reconciliation/upload` | POST | Parse CSV → insert into `SOSYSLegacyLogs` |
| `GET /api/reconciliation/results` | GET | Return all rows with `match_status` |
| `POST /api/reconciliation/{id}/resolve` | POST | Mark anomaly as resolved |

#### Task A4.3 — Matching Algorithm (`services/reconciliation.py`)

- Match on `claim_code` + `amount`:
  - Exact match → MATCHED
  - Same code, different amount → FLAGGED (amount mismatch)
  - Only in SOSYS → UNMATCHED (ghost payment)
  - Only in Samanvaya → UNMATCHED (orphan)
- Duplicate detection: same claim_code appearing >1 time → FLAGGED
- Write results back + return summary counts

---

### Phase A5 — (Reserved for Frontend — see Phase A6)

---

### Phase A6 — Frontend: React Application

**Goal:** Polished, clear UI that judges understand in 5 seconds.

#### Task A6.1 — Initialize Frontend

- `npm create vite@latest frontend -- --template react`
- Install: `tailwindcss`, `recharts`, `axios`, `react-router-dom`
- Routes: `/` (Dashboard), `/claims` (Claims Queue), `/ledger` (Transaction Ledger), `/reconciliation` (Reconciliation Console)
- `src/api/client.js` — Axios base URL `http://localhost:8000`

#### Task A6.2 — Shared Components

- `StatusBadge.jsx` — Green (SUCCESS), Red (FAILED), Yellow (PENDING/PROCESSING), Gray (PARTIAL)
- `PaymentProgressBar.jsx` — 4 steps: Claim Approved → Queued → Sent to Bank → Confirmed
- `AnomalyAlert.jsx` — Pulsing red banner: "N SOSYS Anomalies Detected"
- `Navbar.jsx` + `Layout.jsx` — Navigation + common wrapper

#### Task A6.3 — Dashboard Page

- KPI Cards: Total Disbursed Today (NPR), Success Rate %, Pending Count, Failed Count
- Pie chart: Success / Failed / Pending (Recharts)
- Bar chart: Daily volume, last 7 days
- Alert banner: AnomalyAlert if count > 0
- Poll `/api/dashboard/summary` + `/api/dashboard/volume` every 5s

#### Task A6.4 — Claims Queue Page

- Table: claim_code, hospital, insuree, amount, date (APPROVED claims)
- Checkbox selection → "Create Batch" button
- "Execute Batch" button per batch
- Live status polling after execution

#### Task A6.5 — Transaction Ledger Page

- Searchable/filterable table: Claim ID, Hospital, Amount, Status (badge), Gateway Ref, Timestamp
- Row click → drawer with `raw_request_log` + `raw_response_log` (formatted JSON)
- "Retry" button on FAILED transactions

#### Task A6.6 — Reconciliation Console Page

- Upload CSV button (drag-and-drop)
- Results table with tabs: All / Matched / Unmatched / Flagged
- Color-coded rows, "Resolve" button per flagged row
- Summary bar: "15 Matched | 3 Unmatched | 2 Flagged"

---

### Phase A7 — Integration Testing

**Goal:** Verify all three paths work end-to-end.

#### Task A7.1 — Happy Path

1. Start all 3 servers
2. Select claims → create batch → execute
3. Approve in Mock Bank → dashboard flips to SUCCESS in real-time
4. Reject another → shows FAILED immediately

#### Task A7.2 — Failure & Retry Path

1. Reject a transaction
2. Click "Retry" in Ledger
3. Approve the retried transaction → SUCCESS

#### Task A7.3 — Reconciliation Path

1. Upload SOSYS CSV → anomalies detected
2. Resolve a flagged item
3. Dashboard anomaly count decreases

#### Task A7.4 — Polling Safety Net

1. Execute batch, don't touch Mock Bank
2. Wait for poll cycle
3. Verify stale transactions update automatically

---

## PHASE B: OpenIMIS Integration (Production Path)

---

### Phase B1 — OpenIMIS Environment Setup

**Goal:** Get a local OpenIMIS instance running with the module registration system ready.

#### Task B1.1 — Set Up OpenIMIS Backend

- Clone `openimis-be_py` repository
- Configure `docker-compose.yml` with PostgreSQL, Django, Celery, Redis
- Verify: `docker-compose up` → OpenIMIS backend responds at `localhost:8000`
- Confirm existing modules from `openimis.json` load correctly:
  - Key dependencies: `core`, `claim`, `claim_batch`, `payment`, `payment_cycle`, `insuree`, `medical`

#### Task B1.2 — Set Up OpenIMIS Frontend

- Clone `openimis-fe_js` repository
- Verify: `npm start` → React app loads at `localhost:3000`
- Understand the module registration pattern: `getRoutes()`, `getMenu()`, `getDefaultMenu()`

#### Task B1.3 — Understand the Claim Approval Pipeline

- Study `claim` module: how claims are submitted, reviewed, and approved
- Study `claim_batch` module: how approved claims are grouped for payment
- Identify the exact signal/hook point: when `Claim.status` transitions to `APPROVED`
- Study `payment` module: existing payment models and how they relate to our needs

---

### Phase B2 — Create the Samanvaya Django Module (`openimis-be-samanvaya`)

**Goal:** A native OpenIMIS backend module — Django app with models, GraphQL, Celery tasks, and Django Signals.

#### Task B2.1 — Module Skeleton

```
openimis-be-samanvaya/
├── samanvaya/
│   ├── __init__.py
│   ├── apps.py                 # App registration, signal connection
│   ├── models.py               # PaymentBatch, PaymentTransaction, GatewayConfig, SOSYSLegacyLog
│   ├── schema.py               # Root GraphQL schema aggregator
│   ├── gql_queries.py          # GraphQL queries (ledger, dashboard, reconciliation)
│   ├── gql_mutations.py        # GraphQL mutations (execute batch, retry, upload CSV, resolve)
│   ├── services.py             # BulkDisbursementService (ported from standalone)
│   ├── tasks.py                # Celery async tasks (gateway calls, polling, retries)
│   ├── adapters.py             # Strategy pattern: BasePaymentGateway, MockBank, ESewa
│   ├── signal_handlers.py      # Listen to Claim approval events
│   ├── permissions.py          # Custom rights (150001: Can execute payment, etc.)
│   ├── migrations/
│   └── tests/
├── setup.py
└── README.md
```

- Register in `openimis.json`:
  ```json
  { "name": "samanvaya", "pip": "./openimis-be-samanvaya" }
  ```

#### Task B2.2 — Django Models (Port from Standalone)

Port all models from Phase A1.2 to Django ORM. Key adaptations:

| Standalone (SQLAlchemy) | OpenIMIS (Django ORM) |
|---|---|
| `Column(UUID, primary_key=True)` | `models.UUIDField(primary_key=True, default=uuid.uuid4)` |
| `Column(JSON)` | `models.JSONField()` |
| `Column(Enum(...))` | `models.CharField(choices=...)` |
| `ForeignKey` (string) | `models.ForeignKey("claim.Claim", on_delete=models.CASCADE)` |
| SQLite | PostgreSQL (already OpenIMIS's default) |

- Add Django-specific fields:
  - `created_by = models.ForeignKey("core.User", on_delete=models.SET_NULL)` — audit trail
  - Use `django-simple-history` for `PaymentTransaction` — every status change logs who/when

#### Task B2.3 — Django Signal Handler (The "Hook")

```python
# signal_handlers.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from claim.models import Claim

@receiver(post_save, sender=Claim)
def trigger_samanvaya_queue(sender, instance, **kwargs):
    """When a claim is approved in OpenIMIS, auto-queue it for payment."""
    if instance.status == Claim.STATUS_APPROVED:
        from .tasks import queue_claim_for_payment
        queue_claim_for_payment.delay(instance.id)
```

- This is the core integration point: OpenIMIS approves a claim → Samanvaya automatically picks it up
- **Verification:** Approve a claim in OpenIMIS UI → see it appear in Samanvaya's payment queue

#### Task B2.4 — Celery Tasks (Async Payment Processing)

```python
# tasks.py
from celery import shared_task

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def queue_claim_for_payment(self, claim_id):
    """Create PaymentTransaction for an approved claim."""
    # 1. Get or create active PaymentBatch
    # 2. Create PaymentTransaction(status=QUEUED)
    # 3. Trigger batch execution if threshold reached

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_payment_transaction(self, transaction_id):
    """Send payout to gateway with retry logic."""
    # 1. Lock transaction row (select_for_update)
    # 2. Get active gateway adapter
    # 3. Call initiate_payout with idempotency_key
    # 4. Handle response: SUCCESS/FAILED/PENDING

@shared_task
def process_gateway_webhook(payload):
    """Handle async webhook from payment gateway."""
    # 1. Verify webhook signature (HMAC-SHA256)
    # 2. Lock transaction row
    # 3. Update status, log response

@shared_task
def poll_pending_transactions():
    """Safety net: check stale PROCESSING transactions."""
    # Run every 5 min via Celery Beat
    # Call gateway.verify_status for each
```

- Register Celery Beat schedule in `apps.py`:
  ```python
  app.conf.beat_schedule = {
      'poll-pending': {
          'task': 'samanvaya.tasks.poll_pending_transactions',
          'schedule': 300.0,  # every 5 minutes
      },
  }
  ```

#### Task B2.5 — Gateway Adapter Layer (Port from Standalone)

- Port `BasePaymentGateway`, `MockBankGateway`, `ESewaGateway` from Phase A2
- Adapt to use Django's `httpx` or `requests`
- Store gateway configs in `GatewayConfig` model with encrypted fields (`django-fernet` or `EncryptedTextField`)

#### Task B2.6 — GraphQL Queries

```python
# gql_queries.py
class Query(graphene.ObjectType):
    samanvaya_claims = graphene.List(ClaimGQLType, status=graphene.String())
    samanvaya_batches = graphene.List(PaymentBatchGQLType)
    samanvaya_transactions = graphene.List(
        PaymentTransactionGQLType,
        status=graphene.String(),
        health_facility=graphene.String(),
        date_from=graphene.Date(),
        date_to=graphene.Date()
    )
    samanvaya_transaction_detail = graphene.Field(
        PaymentTransactionDetailGQLType, id=graphene.UUID(required=True)
    )
    samanvaya_dashboard_summary = graphene.Field(DashboardSummaryGQLType)
    samanvaya_dashboard_volume = graphene.List(DailyVolumeGQLType)
    samanvaya_reconciliation_results = graphene.List(ReconciliationResultGQLType)
```

#### Task B2.7 — GraphQL Mutations

```python
# gql_mutations.py
class CreatePaymentBatch(graphene.Mutation):
    """Select approved claims → create batch"""

class ExecutePaymentBatch(graphene.Mutation):
    """Trigger bulk disbursement for a batch"""

class RetryFailedTransaction(graphene.Mutation):
    """Re-initiate a failed payment with new idempotency key"""

class UploadSOSYSCSV(graphene.Mutation):
    """Parse legacy CSV → run reconciliation matching"""

class ResolveReconciliationAnomaly(graphene.Mutation):
    """Mark a flagged anomaly as manually resolved"""

class ReceiveGatewayWebhook(graphene.Mutation):
    """Process webhook callback from payment gateway"""
```

- All mutations check permissions: `info.context.user.has_perm('samanvaya.execute_payment')`

#### Task B2.8 — Webhook URL Endpoint

- Add a Django URL route for the gateway webhook (webhooks come from outside, not through GraphQL):
  ```python
  # urls.py
  urlpatterns = [
      path('webhook/gateway/', views.gateway_webhook, name='gateway-webhook'),
  ]
  ```
- Verify HMAC signature before processing
- Use `select_for_update()` for row locking

#### Task B2.9 — Permissions

| Permission Code | Description |
|---|---|
| 150001 | Can view Samanvaya dashboard |
| 150002 | Can execute payment batch |
| 150003 | Can retry failed transaction |
| 150004 | Can upload SOSYS CSV |
| 150005 | Can resolve reconciliation anomaly |
| 150006 | Can configure payment gateway |

---

### Phase B3 — Create the Samanvaya React Module (`openimis-fe-samanvaya`)

**Goal:** Native OpenIMIS frontend module — Material-UI components, Apollo GraphQL, registered in OpenIMIS navigation.

#### Task B3.1 — Module Skeleton

```
openimis-fe-samanvaya/
├── src/
│   ├── index.js                # Module entry: getRoutes(), getMenu()
│   ├── components/
│   │   ├── SamanvayaDashboard.js
│   │   ├── ClaimsQueue.js
│   │   ├── PaymentLedger.js
│   │   ├── ReconciliationConsole.js
│   │   ├── PaymentStatusWidget.js    # Injected into ClaimDetail page
│   │   └── GatewayConfigForm.js
│   ├── helpers/
│   │   └── graphql/
│   │       ├── queries.js
│   │       └── mutations.js
│   ├── constants.js            # Menu keys, permission codes
│   └── translations/
│       ├── en.json
│       └── ne.json             # Nepali translations (bonus points)
├── package.json
└── webpack.config.js
```

#### Task B3.2 — Menu & Route Registration (`index.js`)

```javascript
export function getRoutes() {
    return [
        { path: 'samanvaya/dashboard', component: SamanvayaDashboard },
        { path: 'samanvaya/claims', component: ClaimsQueue },
        { path: 'samanvaya/ledger', component: PaymentLedger },
        { path: 'samanvaya/reconciliation', component: ReconciliationConsole },
    ];
}

export function getMenu(cfg) {
    return {
        key: 'samanvaya',
        label: 'Samanvaya Payments',
        filter: (rights) => rights.includes(150001),
        subMenu: [
            { key: 'dashboard', label: 'Financial Dashboard', path: 'samanvaya/dashboard' },
            { key: 'claims', label: 'Claims Queue', path: 'samanvaya/claims' },
            { key: 'ledger', label: 'Transaction Ledger', path: 'samanvaya/ledger' },
            { key: 'reconciliation', label: 'Reconciliation', path: 'samanvaya/reconciliation' },
        ]
    };
}
```

#### Task B3.3 — Port Dashboard (Material-UI + Recharts)

- Use Material-UI `Card`, `Grid`, `Typography` for KPI cards
- Use Recharts for pie + bar charts
- Apollo Client `useQuery` for GraphQL data fetching
- Auto-refresh with `refetchInterval` or `setInterval` + `refetch()`

#### Task B3.4 — Port Claims Queue

- Material-UI `DataGrid` for claims table
- Checkbox selection → `CreatePaymentBatch` mutation
- "Execute Batch" → `ExecutePaymentBatch` mutation
- Status polling with Apollo

#### Task B3.5 — Port Transaction Ledger

- Material-UI `DataGrid` with filters
- Row expansion: `DialogContent` showing raw JSON logs
- "Retry" button → `RetryFailedTransaction` mutation

#### Task B3.6 — Port Reconciliation Console

- File upload component → `UploadSOSYSCSV` mutation
- Tabbed results view (All / Matched / Unmatched / Flagged)
- "Resolve" button → `ResolveReconciliationAnomaly` mutation

#### Task B3.7 — Payment Status Widget (The "Blind Spot" Fix)

- Create `PaymentStatusWidget.jsx` — a small component injected into OpenIMIS's standard `ClaimDetail` page
- Uses OpenIMIS extension points to render a progress bar:
  - Claim Approved → Queued in Samanvaya → Sent to Bank → Confirmed
- Queries `samanvaya_transaction_detail` by claim ID
- **This visually proves OpenIMIS is no longer blind after claim approval**

---

### Phase B4 — Deep Integration & Data Flow

**Goal:** Wire Samanvaya into OpenIMIS's existing data pipeline so it operates as a seamless part of the system.

#### Task B4.1 — Claim → Payment Handoff

- Verify the Django Signal fires when a claim is approved through OpenIMIS's standard workflow
- Auto-create `PaymentTransaction` in QUEUED state
- Auto-assign to active `PaymentBatch` (or create new batch if threshold reached)

#### Task B4.2 — Use OpenIMIS Core Models

- Replace standalone `Claim` model with FK to `claim.Claim` (OpenIMIS core)
- Replace standalone `health_facility` string with FK to `location.HealthFacility`
- Use OpenIMIS's `ClaimBundle` (from `claim_batch` module) for batch grouping
- Link `PaymentBatch.claim_bundle_ref` → `claim_batch.ClaimBatch`

#### Task B4.3 — Reuse OpenIMIS Auth & Permissions

- All Samanvaya pages require OpenIMIS login
- Permission checks use OpenIMIS's `core.User` rights system
- GraphQL context carries the authenticated user automatically

#### Task B4.4 — Shared Database

- Samanvaya tables live in the same PostgreSQL database as OpenIMIS
- Foreign keys reference OpenIMIS core tables directly
- Migrations managed through Django's `makemigrations samanvaya`

---

### Phase B5 — Edge Case Handling (Mentor's Testing Matrix)

**Goal:** Handle the real-world failure scenarios the mentor specified.

#### Task B5.1 — CIPS Fail → Bank Success (Scenario A)

- Gateway returns failure/timeout, but bank actually processed the payment
- **Detection:** Active polling calls `verify_status` → bank says SUCCESS
- **Action:** Update transaction to SUCCESS, log the discrepancy in `raw_response_log`
- **Prevention of double-pay:** Idempotency key ensures retry doesn't create second payment

#### Task B5.2 — CIPS OK → Bank Fail (Scenario B)

- Gateway returns success, but bank ultimately rejects the transfer
- **Detection:** Webhook arrives with FAILED status (or polling detects it)
- **Action:** Override initial PROCESSING → FAILED, increment `retry_count`, flag for review
- **Ledger integrity:** `raw_response_log` captures both the initial OK and the subsequent FAILED

#### Task B5.3 — Duplicate Webhook Handling

- Bank sends the same webhook twice
- **Prevention:** `idempotency_key` + `gateway_ref_id` unique constraint + row locking
- Webhook handler checks `if tx.status in terminal_states → skip`

#### Task B5.4 — Concurrent Update Protection

- Webhook and polling task try to update same transaction simultaneously
- **Solution:** `select_for_update()` row lock in both paths
- Only one process can enter the critical section at a time

---

### Phase B6 — Security & Compliance

**Goal:** Financial-grade security for a production payment system.

#### Task B6.1 — Data Encryption

- Encrypt bank account numbers and sensitive gateway credentials at rest
- Use `django-fernet` or `EncryptedTextField` for `GatewayConfig.api_key` and `secret_key`

#### Task B6.2 — Webhook Signature Verification

- HMAC-SHA256 signature check on every inbound webhook
- Reject payloads with invalid signatures (prevent spoofed "Payment Successful")

#### Task B6.3 — Audit Trail

- `django-simple-history` on `PaymentTransaction` — logs every field change with timestamp + user
- Immutable `raw_request_log` and `raw_response_log` JSON fields

---

### Phase B7 — Testing & Demo Preparation

**Goal:** End-to-end verification in the OpenIMIS environment, demo rehearsal.

#### Task B7.1 — Docker Compose Integration

- Add Samanvaya services to the main `docker-compose.yml`:
  - Mount `openimis-be-samanvaya` as volume in OpenIMIS backend container
  - Mount `openimis-fe-samanvaya` in OpenIMIS frontend container
  - Mock Bank as separate service on port 8001
- Hot-reload enabled for development

#### Task B7.2 — End-to-End Demo Flow (in OpenIMIS)

1. Log into OpenIMIS as admin
2. Navigate to Claims → approve a claim
3. Watch it auto-appear in Samanvaya → Claims Queue
4. Create batch → Execute → transactions move to PROCESSING
5. Open Mock Bank UI → Approve → Samanvaya dashboard flips to SUCCESS
6. Show Financial Dashboard updating in real-time
7. Go to Claim Detail page → see PaymentStatusWidget progress bar
8. Upload SOSYS CSV → reconciliation flags anomalies

#### Task B7.3 — Rehearse 3-Minute Demo

| Time | Action | Talking Point |
|---|---|---|
| 0:00 | Open OpenIMIS Dashboard | "Standard OpenIMIS. Enrollment, claims, approvals." |
| 0:15 | Approve a claim | "Claim approved. Normally handed off to SOSYS. Watch what happens." |
| 0:30 | Switch to Samanvaya → Claims Queue | "It appeared here automatically. Django Signal fired the moment it was approved." |
| 0:45 | Create batch → Execute | "Bulk disbursement engine. Every transaction tracked." |
| 1:00 | Open Mock Bank → Approve | "Bank processing. Let me simulate approval." |
| 1:15 | Dashboard flips SUCCESS | "Webhook received. Row-locked. Idempotency verified. Dashboard live." |
| 1:30 | Reject second transaction | "Failed immediately. No blind spots." |
| 1:45 | Claim Detail → PaymentStatusWidget | "Progress bar inside the claim itself. OpenIMIS is no longer blind." |
| 2:15 | Upload SOSYS CSV | "Migration bridge. Double payments caught instantly." |
| 2:45 | Closing | "Samanvaya closes the loop. Enroll, claim, pay, report — all in OpenIMIS." |

---

## Scope Management — Priority Cuts

If time is tight, cut in this order (least critical first):

| Priority | Cut This | Keep At All Costs |
|---|---|---|
| 1st | Full OpenIMIS integration (Phase B) — demo standalone instead | Core payment flow (Claim → Batch → Execute → Success) |
| 2nd | Reconciliation Engine | Mock Bank interactive webhook demo |
| 3rd | PaymentStatusWidget in ClaimDetail | Financial Dashboard (KPI cards + 1 chart) |
| 4th | Active polling safety net | Transaction Ledger with status badges |
| 5th | Celery Beat scheduling | The one-line pitch, practiced and tight |
| 6th | Nepali translations | GraphQL mutations (use REST fallback for demo) |

> You can describe cut features confidently as "designed and architected" — judges evaluate vision as much as code.

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Hackathon demo** | Standalone FastAPI (Phase A) | Runs on any laptop, no Docker overhead |
| **Production target** | Native OpenIMIS Django module (Phase B) | First-class citizen, uses existing models/auth |
| **API layer** | REST (standalone) → GraphQL (OpenIMIS) | Match each environment's conventions |
| **Async processing** | APScheduler (standalone) → Celery+Redis (OpenIMIS) | Scale appropriately |
| **Database** | SQLite (standalone dev) → PostgreSQL (OpenIMIS shared) | Same data, different deployment |
| **Frontend** | React+Vite+Tailwind (standalone) → Material-UI+Apollo (OpenIMIS) | Match each ecosystem |
| **Gateway pattern** | Strategy/Adapter (both phases) | Swap MockBank → eSewa with zero logic changes |
| **Claim hook** | Seed data (standalone) → Django Signals (OpenIMIS) | Same behavior, different trigger |
| **Idempotency** | UUID keys + row locking (both phases) | Financial-grade double-payment prevention |

---

## Migration Path: Standalone → OpenIMIS

The standalone build is not throwaway work. Every component maps directly:

| Standalone Component | OpenIMIS Equivalent | Migration Effort |
|---|---|---|
| `models.py` (SQLAlchemy) | `models.py` (Django ORM) | Syntax change only, same schema |
| `services/disbursement.py` | `services.py` | Direct port, same logic |
| `services/gateway/*` | `adapters.py` | Direct port |
| `routers/*.py` (REST) | `gql_queries.py` + `gql_mutations.py` (GraphQL) | Rewrite endpoints as GraphQL |
| `seed.py` | Django fixtures + management command | Reformat |
| `services/poller.py` (APScheduler) | `tasks.py` (Celery Beat) | Rewrite scheduler, same query |
| React pages (Tailwind) | React components (Material-UI) | Restyle, same logic |
| `routers/webhooks.py` | `urls.py` + `views.py` | Direct port |

Build Phase A first. Demo it. Then port to Phase B when time allows.
