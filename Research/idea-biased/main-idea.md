# Samanvaya — Hackathon To-Do List 🗂️

Here is a comprehensive, phased to-do list to build **Samanvaya** as a **standalone module** and win the hackathon. No live OpenIMIS instance needed — just a clean FastAPI backend, React frontend, and a mock bank server.

---

### Phase 1: Project Setup & Foundation 🏗️
*Goal: Get the dev environment up, define the data models, and wire up the skeleton.*

- [ ] **Initialize the Project:**
  - Backend: `fastapi` + `sqlalchemy` + `alembic` (or plain Django if you prefer)
  - Frontend: `create-react-app` or Vite + React + Tailwind CSS
  - Mock Bank: Separate FastAPI server on a different port (e.g., `localhost:8001`)
- [ ] **Design the Database Schema:** Create tables for:
  - `Claims` — seeded with realistic approved claim bundles (mimics OpenIMIS output)
  - `Payment_Batches` — groups of claims queued for disbursement
  - `Payment_Transactions` — individual payment records with status: `Pending`, `Processing`, `Success`, `Failed`, `Partial`
  - `Gateway_Configs` — which gateway to use (MockBank, eSewa stub, etc.)
  - `SOSYS_Legacy_Logs` — temporary table for reconciliation uploads
- [ ] **Seed Demo Data:** Populate `Claims` with realistic Nepali context data:
  - Hospitals: "Bir Hospital", "Civil Hospital", "Patan Hospital"
  - Claim amounts in NPR (e.g., NPR 12,500 for a surgery claim)
  - Mix of statuses: some ready to pay, some already processed

---

### Phase 2: Core Payment Engine & Ledger ⚙️
*Goal: Build the internal logic that handles the money movement and tracks every single cent.*

- [ ] **Build the Bulk Disbursement Engine:**
  - Endpoint: `POST /api/batches/{batch_id}/execute`
  - Logic: Takes a batch of approved claims → splits into individual payment tasks → calls the gateway adapter
  - Implement basic batching (e.g., process 50 at a time) and retry logic for failures
- [ ] **Implement the Transaction Ledger:**
  - Log every payment attempt with timestamps and state transitions
  - Strict state machine: `Pending → Processing → Success / Failed / Partial`
  - Store `raw_request_log` and `raw_response_log` (JSON) for every gateway call
- [ ] **Handle Edge Cases:**
  - Partial batch success (e.g., 8 of 10 succeed, 2 fail due to bad bank details)
  - Duplicate webhook calls (use `idempotency_key` to prevent double-logging)

---

### Phase 3: Mock Bank Server (Your "Payment Rail") 🏦
*Goal: Build the interactive mock bank that makes the demo compelling.*

- [ ] **Create the Mock Bank FastAPI Server** (runs on `localhost:8001`):
  - `POST /mock-bank/payout` — receives payout from Samanvaya, puts it in "Pending" queue
  - `GET /mock-bank/status/{ref_id}` — returns current status
  - `POST /mock-bank/webhook/approve/{ref_id}` — manually trigger a success callback
  - `POST /mock-bank/webhook/fail/{ref_id}` — manually trigger a failure callback
- [ ] **Build a Simple Mock Bank UI:**
  - Show all pending payouts in a list
  - "Approve" / "Reject" buttons for each
  - When approved → fires a webhook to Samanvaya → Samanvaya dashboard updates live
  - **This is your demo money moment** — judges will love the interactive flow
- [ ] **Build the Gateway Adapter in Samanvaya:**
  - Abstract base class so you can swap MockBank → eSewa in production
  - Samanvaya never hardcodes bank logic — all goes through the adapter interface

---

### Phase 4: Reconciliation Engine (Track 1 Bridge) 🌉
*Goal: Show the SOSYS → Samanvaya migration story.*

- [ ] **Create Mock SOSYS Data:**
  - Generate a `sosys_legacy.csv` with ~20 records
  - Include intentional mismatches: double payments, missing claims, amount discrepancies
- [ ] **Build the CSV Upload + Ingestion Endpoint:**
  - `POST /api/reconciliation/upload` — parses the SOSYS CSV into `SOSYS_Legacy_Logs`
- [ ] **Build the Matching Algorithm:**
  - Compare `SOSYS_Legacy_Logs` against `Payment_Transactions` using Claim IDs and amounts
  - Output: `Matched`, `Unmatched (only in SOSYS)`, `Unmatched (only in Samanvaya)`, `Amount Mismatch`
- [ ] **Anomaly Flagging:**
  - Flag anything that looks like a double payment or a missed claim
  - Surface these as a count on the main dashboard: *"3 SOSYS Anomalies Detected"*

---

### Phase 5: UI / Financial Dashboard 📊
*Goal: Make it look polished and easy to understand for judges.*

- [ ] **Simulated Claims Queue UI:**
  - Table of approved claims ready to be batched
  - "Create Batch" button → groups selected claims into a `Payment_Batch`
  - "Execute Batch" button → triggers the payment engine
- [ ] **Transaction Ledger UI:**
  - Clean, searchable, filterable data table
  - Columns: Claim ID, Hospital, Amount (NPR), Status, Gateway Ref, Timestamp
  - Color-coded status badges (green = Success, red = Failed, yellow = Pending)
- [ ] **Financial Dashboard:**
  - Summary cards: *Total Disbursed Today, Success Rate %, Pending Count, Failed Count*
  - Simple chart: Pie chart for Success/Fail ratio, Bar chart for daily volume
  - Red pulsing alert if SOSYS anomalies are detected
- [ ] **Reconciliation Console:**
  - Upload SOSYS CSV button
  - Table showing Matched / Unmatched / Flagged rows side by side
  - "Resolve / Override" button per anomaly

---

### Phase 6: Demo Polish & Pitch Prep 🏆
*Goal: Flawless demo, tight pitch, nothing left to chance.*

- [ ] **Rehearse the End-to-End Flow:**
  1. Open Samanvaya → show approved claims in the queue
  2. Select claims → create a batch → click "Execute Payment"
  3. Show transactions moving to `Processing` → open Mock Bank UI on screen
  4. Say: *"This is the bank's internal processing. Let's simulate approval."*
  5. Click "Approve" on Mock Bank → webhook fires → Samanvaya dashboard flips to `Success`
  6. Show Financial Dashboard updating in real-time
  7. *Bonus:* Upload SOSYS CSV → show reconciliation flagging a double payment instantly
- [ ] **Finalize the Pitch:** Lead with the one-liner:
  > *"Samanvaya is a payment execution module that replaces SOSYS — so OpenIMIS can finally see its entire financial loop, end to end."*
- [ ] **Record a Backup Video:** 3-minute screencast of the perfect flow. Hackathon demos fail — this is your insurance.

---

**💡 Scope Management Tip:**
If time is tight, **drop Phase 4 (Reconciliation)** and focus 100% on making Phases 2, 3, and 5 look incredibly smooth. You can describe the reconciliation engine in your pitch as the "migration strategy" without showing a live demo of it. The core payment flow is what wins.
