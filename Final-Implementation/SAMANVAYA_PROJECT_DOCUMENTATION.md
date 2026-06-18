# Samanvaya Project Documentation

## 1. One-Line Pitch

Samanvaya is a payment execution module for OpenIMIS that replaces the SOSYS handoff, so OpenIMIS can approve claims, create payment batches, disburse funds, track transaction status, reconcile legacy SOSYS data, and report financial health from one system.

## 2. Problem Statement

In the current workflow, OpenIMIS manages enrollment, claims, and approvals, but the financial payment loop is handed off to SOSYS or another external payment process. After that handoff, OpenIMIS cannot reliably answer:

- Was the hospital paid?
- Did the payment fail or remain pending?
- Was a claim paid twice?
- Did SOSYS contain payments that OpenIMIS does not know about?
- Is the financial ledger complete enough for audit and reporting?

Samanvaya closes this blind spot by moving payment execution, transaction logging, status tracking, reconciliation, and reporting inside the OpenIMIS ecosystem.

## 3. Goal From The Research Notes

The corrected goal is not "make OpenIMIS and SOSYS talk better forever." The goal is:

OpenIMIS absorbs the payment responsibilities currently handled outside it. SOSYS becomes unnecessary after migration, and reconciliation exists as the temporary bridge that protects the cutover.

That means the project is built around two connected ideas:

- Core product: an OpenIMIS payment execution engine.
- Migration safety net: a reconciliation engine comparing Samanvaya/OpenIMIS payments with legacy SOSYS exports.

## 4. What Is Implemented

The `Final-Implementation/` folder contains three working layers.

### A. Standalone Hackathon Demo

This is the fast, reliable demo stack:

- FastAPI backend in `backend/`
- React + Vite frontend in `frontend/`
- Interactive mock bank in `mock-bank/`
- SQLite database for local development
- One-click Windows scripts: `start.bat` and `stop.bat`

It supports:

- Approved claim queue
- Manual payment batch creation
- Automatic amount-limited batch creation
- Batch execution through a mock bank gateway
- Webhook status updates
- Transaction ledger with raw request and response logs
- Ledger CSV export for audit and finance handoff
- Ledger clear/reset control for repeated hackathon demos
- Failed payment retry
- Manual verification of processing transactions
- Financial dashboard with KPIs and charts
- SOSYS CSV upload
- Generated SOSYS CSV download
- Generated reconciliation demo with intentional anomalies
- Larger mock data generation for stress testing

### B. Native OpenIMIS Module

The production direction is represented by:

- `openimis-be-samanvaya/`
- `openimis-fe-samanvaya/`
- `openimis.json`
- `docker-compose.yml`
- `openimis_test/` Django harness

This layer follows the OpenIMIS module pattern:

- Django models
- GraphQL queries and mutations
- Celery task structure
- Gateway adapter pattern
- Signal handler for claim approval
- React module registration
- OpenIMIS menu/routes
- Payment status widget concept for claim detail pages

### C. Django Test Harness

The harness simulates enough of OpenIMIS to validate the Samanvaya module without running the full OpenIMIS stack.

It includes:

- Mock `claim.Claim` model
- Django settings
- GraphQL schema wiring
- Admin and GraphiQL access

## 5. Core Architecture

Samanvaya is structured around five core capabilities.

### 5.1 Bulk Disbursement Engine

The engine turns approved claims into payment batches and individual payment transactions.

Current standalone implementation:

- `backend/services/disbursement.py`
- `POST /api/batches`
- `POST /api/batches/auto`
- `POST /api/batches/{batch_id}/execute`

The new automatic batch creation endpoint accepts an amount limit and creates as many batches as needed without crossing that limit when possible. If a single claim is larger than the limit, it is isolated into its own batch and reported back to the UI.

### 5.2 Transaction Ledger

Each payment attempt is stored as a `PaymentTransaction`.

It records:

- Claim ID
- Batch ID
- Amount
- Status
- Gateway name
- Gateway reference
- Idempotency key
- Retry count
- Raw request JSON
- Raw response JSON
- Webhook received timestamp

This is the financial source of truth.

### 5.3 Gateway Adapter

The gateway adapter lets the system swap payment rails without rewriting business logic.

Current adapters:

- Mock Bank adapter
- eSewa placeholder/stub
- Base gateway interface

Production direction:

- eSewa
- ConnectIPS
- RTGS
- Other national payment rails

### 5.4 Reconciliation Engine

The reconciliation engine compares legacy SOSYS rows against the Samanvaya ledger.

It detects:

- Matched payments
- Ghost payments: SOSYS paid something OpenIMIS/Samanvaya does not know
- Amount mismatches
- Duplicate SOSYS rows
- Samanvaya success payments missing in SOSYS
- SOSYS paid claims that exist but have no Samanvaya transaction
- Status mismatches

Current files:

- `backend/services/reconciliation.py`
- `backend/services/sosys_mock.py`
- `backend/routers/reconciliation.py`

### 5.5 Financial Dashboard

The dashboard gives finance officers a live view of payment health.

It shows:

- Total disbursed
- Success rate
- Pending count
- Failed count
- Daily volume
- Payment status breakdown
- Reconciliation anomaly count

## 6. Data Model

### Claim

Represents an approved or processed health insurance claim.

Important fields:

- `claim_code`
- `health_facility`
- `insuree_name`
- `claimed_amount`
- `approved_amount`
- `status`
- `approved_date`

Statuses:

- `APPROVED`
- `QUEUED`
- `PROCESSED`

### PaymentBatch

Groups payment transactions.

Important fields:

- `total_amount`
- `claim_count`
- `status`
- `created_at`

Statuses:

- `QUEUED`
- `EXECUTING`
- `DONE`
- `PARTIAL`
- `FAILED`

### PaymentTransaction

The audit ledger for a single payment.

Statuses:

- `PENDING`
- `PROCESSING`
- `SUCCESS`
- `FAILED`
- `PARTIAL`

### GatewayConfig

Stores gateway configuration.

Current demo gateway:

- `mock_bank`

### SOSYSLegacyLog

Stores imported or generated SOSYS rows and reconciliation results.

Match statuses:

- `MATCHED`
- `UNMATCHED`
- `FLAGGED`

## 7. API Reference

### Claims

- `GET /api/claims`
- `GET /api/claims?status=APPROVED`
- `POST /api/claims/{claim_id}/approve`

### Batches

- `POST /api/batches`
- `POST /api/batches/auto`
- `GET /api/batches`
- `POST /api/batches/{batch_id}/execute`
- `GET /api/batches/{batch_id}/transactions`

Example automatic batch request:

```json
{
  "amount_limit": 100000
}
```

### Transactions

- `GET /api/transactions`
- `GET /api/transactions?status=FAILED`
- `GET /api/transactions?health_facility=Bir`
- `GET /api/transactions/export-csv`
- `DELETE /api/transactions/ledger`
- `GET /api/transactions/{tx_id}`
- `POST /api/transactions/{tx_id}/retry`
- `POST /api/transactions/{tx_id}/verify`

`GET /api/transactions/export-csv` downloads the current ledger as a CSV with transaction ID, batch ID, claim code, facility, amount, status, gateway reference, retry count, and timestamps.

`DELETE /api/transactions/ledger` clears transactions, batches, and stale reconciliation rows, then resets affected claims back to `APPROVED` so the same demo dataset can be reused.

### Dashboard

- `GET /api/dashboard/summary`
- `GET /api/dashboard/volume`
- `GET /api/dashboard/anomaly-count`

### Reconciliation

- `POST /api/reconciliation/upload`
- `GET /api/reconciliation/generate-csv?scenario=mixed`
- `GET /api/reconciliation/generate-csv?scenario=clean`
- `POST /api/reconciliation/generate-demo?scenario=mixed`
- `GET /api/reconciliation/results`
- `GET /api/reconciliation/summary`
- `POST /api/reconciliation/{log_id}/resolve`

Generated CSV fields:

```csv
claim_code,health_facility,amount,payment_date,status
```

### Demo

- `POST /api/demo/reset`
- `POST /api/demo/mock-data`

Example mock-data request:

```json
{
  "claim_count": 60,
  "reset": true
}
```

### Webhook

- `POST /webhook/gateway`

Example webhook payload:

```json
{
  "gateway_ref_id": "MOCK-123",
  "status": "SUCCESS",
  "message": "Paid"
}
```

## 8. Frontend Pages

### Dashboard

Use this page to show the system state at a glance.

Key controls:

- Open Mock Bank
- Reset Demo

### Claims Queue

Use this page to test payment creation.

Key controls:

- Generate Mock Data
- Set amount limit
- Auto Create Batches
- Select claims manually
- Create Batch
- Execute queued batches

### Transaction Ledger

Use this page to inspect individual payments.

Key controls:

- Export ledger CSV
- Clear ledger
- Filter by status
- Search hospital
- Open transaction detail
- Retry failed transaction
- Verify processing transaction

### Reconciliation Console

Use this page to test the migration bridge.

Key controls:

- Upload SOSYS CSV
- Generate SOSYS CSV
- Run Generated Reconciliation
- Filter All / Matched / Unmatched / Flagged
- Resolve anomalies

## 9. How To Run

From `Final-Implementation/`:

```powershell
.\start.bat
```

Expected services:

- Frontend: `http://localhost:5173` or `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- Mock Bank UI: `http://localhost:8001/ui`

To stop:

```powershell
.\stop.bat
```

## 10. Demo Script

### Payment Execution Demo

1. Open the Samanvaya dashboard.
2. Click Reset Demo if needed.
3. Go to Claims Queue.
4. Generate 60 mock claims.
5. Set amount limit to `100000`.
6. Click Auto Create Batches.
7. Execute one queued batch.
8. Open Mock Bank.
9. Approve one payment and reject another.
10. Return to Samanvaya and show the dashboard and ledger updating.
11. Retry a failed transaction from the ledger.
12. Export the ledger CSV as finance evidence.
13. Clear the ledger if you need to repeat the same demo cleanly.

What this proves:

- OpenIMIS-style approved claims are converted to payment batches.
- Every payment has a ledger entry.
- The gateway is asynchronous.
- Webhooks update the ledger.
- Failed payments can be retried.
- Finance teams can see status without leaving the system.

### Reconciliation Demo

1. Make sure there are successful transactions in the ledger.
2. Go to Reconciliation Console.
3. Choose `Mixed Anomalies`.
4. Click Generate SOSYS CSV to show export support.
5. Click Run Generated Reconciliation.
6. Show the summary cards.
7. Filter to Flagged.
8. Point out duplicate payments and amount mismatches.
9. Filter to Unmatched.
10. Point out ghost payments and missing legacy rows.
11. Resolve one anomaly and show the count decrease.

What this proves:

- The system can ingest legacy SOSYS-style data.
- It catches migration risk before SOSYS is retired.
- Reconciliation is a temporary safety net, not the final product dependency.

## 11. How Samanvaya Achieves The Hackathon Goal

### It closes the OpenIMIS payment blind spot

OpenIMIS no longer stops at claim approval. Samanvaya adds the missing payment execution, status tracking, and reporting layer.

### It replaces SOSYS functions inside OpenIMIS

SOSYS capability mapped to Samanvaya:

- Bulk payment processing -> Payment batches and transactions
- Payment execution -> Mock Bank gateway and gateway adapter pattern
- Transaction logging -> PaymentTransaction ledger
- Status tracking -> Webhooks, polling/verification, dashboard
- Financial reporting -> KPI dashboard and transaction ledger
- Legacy comparison -> Reconciliation engine

### It is demoable without fragile external dependencies

The standalone FastAPI + React + Mock Bank stack runs locally and lets judges see the full flow without real bank credentials.

### It still has a native OpenIMIS path

The project includes a Django/GraphQL/React module structure that matches OpenIMIS architecture, so the demo is not throwaway work.

### It handles real financial failure modes

Samanvaya uses:

- Idempotency keys
- Gateway reference IDs
- Raw request and response logs
- Retry count
- Webhook update path
- Manual verification path
- Reconciliation anomaly detection

This shows the system is designed for unreliable payment rails, not just the happy path.

### It gives finance officers visibility

The dashboard and ledger make payment status visible in real time, turning a hidden back-office handoff into an auditable workflow.

## 12. Hackathon Pitching Points

- "Samanvaya makes OpenIMIS financially self-sufficient."
- "The old workflow ends at claim approval. Our workflow ends when the hospital is actually paid and the transaction is auditable."
- "We are not permanently integrating SOSYS. We are replacing it, with reconciliation as the migration safety net."
- "The mock bank is not fake UI. It demonstrates the real asynchronous banking pattern: initiate, wait, webhook, verify."
- "Every payment has an idempotency key and raw logs, so retries do not become double payments."
- "The reconciliation engine catches the dangerous migration cases: duplicate payments, ghost payments, amount mismatches, and missing legacy rows."
- "The standalone demo proves the flow today; the OpenIMIS module structure shows the production integration path."
- "This is not a payment button. It is a financial-grade ledger and disbursement workflow for social health insurance."

## 13. Recommended 3-Minute Pitch Flow

0:00 - Problem:

OpenIMIS approves claims, but the payment loop is external. That creates blind spots.

0:30 - Solution:

Samanvaya adds payment execution, transaction ledger, gateway integration, reconciliation, and dashboards.

1:00 - Live payment:

Generate claims, auto-create amount-limited batches, execute a batch, approve/reject in Mock Bank, show ledger updates.

2:00 - Migration safety:

Generate SOSYS CSV, run reconciliation, show anomalies.

2:40 - Close:

Samanvaya lets OpenIMIS enroll, approve, pay, reconcile, and report from one system.

## 14. Current Limitations

- The standalone demo uses SQLite.
- The mock bank is a simulator, not a real eSewa or ConnectIPS integration.
- The ledger clear button is a hackathon/demo maintenance control. In production, ledger deletion should be replaced with archive, retention, and role-based approval rules.
- Webhook HMAC verification is documented as a production requirement but not enforced in the standalone demo.
- Full OpenIMIS Docker deployment still needs heavier environment testing.
- Production encryption and role-based audit history should be completed before real financial use.

## 15. Production Next Steps

- Replace mock bank adapter with eSewa or ConnectIPS sandbox adapter.
- Add HMAC signature verification to webhooks.
- Encrypt gateway credentials.
- Add immutable audit history for transaction status changes.
- Run the native OpenIMIS module in a full OpenIMIS Docker stack.
- Add automated tests for reconciliation edge cases.
- Add role-based approval workflow for high-value batches.
- Add exportable finance reports for SSF operations.
