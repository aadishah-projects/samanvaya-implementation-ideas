# Samanvaya: Payment Execution Module for OpenIMIS
## Project Documentation & Implementation Guide

### 1. Executive Summary
Samanvaya is a state-of-the-art payment execution and reconciliation engine designed as a standalone module for OpenIMIS. It bridges the gap between claim approval and final bank settlement, providing a financial-grade audit trail, automated disbursement, and a robust reconciliation safety net.

### 2. The Architectural Paradigm Shift
Unlike legacy implementations where the Bank or SOSYS acted as the "authority" for payment success, Samanvaya introduces a **Source of Truth (SoT) Shift**:

*   **OpenIMIS as SoT**: OpenIMIS (via Samanvaya) is now the absolute source of truth for approvals and payment instructions.
*   **Bank as Ledger**: The Bank (Mock Bank) is repurposed strictly as a **settlement ledger**. It no longer "approves" payments; it simply records the settlement based on Samanvaya's instructions.
*   **Reconciliation as Verification**: Reconciliation is redefined as the process of comparing the **OpenIMIS Internal Ledger** against the **Bank Settlement Ledger** to verify actual movement of funds.

---

### 3. Technology Stack & Rationale

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend API** | **FastAPI (Python)** | High performance, asynchronous support for long-running payment polls, and automatic OpenAPI documentation. |
| **Frontend UI** | **React + Vite** | Component-based architecture for complex financial dashboards; Vite provides a near-instant developer experience. |
| **Database** | **SQLAlchemy + SQLite** | Portable, file-based database for zero-config hackathon demos; easily swappable to PostgreSQL for production. |
| **Styling** | **Vanilla CSS + Tailwind** | Fine-grained control over the "OpenIMIS Blue" aesthetic while maintaining rapid layout speed. |
| **Mock Bank** | **FastAPI + SQLite** | Separated service to demonstrate true cross-system interoperability and asynchronous webhook patterns. |
| **Scheduling** | **APScheduler** | Handles polling safety nets for transactions that might miss their webhook updates. |

---

### 4. Codebase Architecture

The project is organized into three primary independent modules within the `Final-Implementation` folder:

#### A. Samanvaya Backend (`/backend`)
*   **`models.py`**: Definition of the Financial Ledger. Includes three-tier amount tracking (`claimed_amount`, `approved_amount`, `paid_amount`) and screening reasons.
*   **`services/disbursement.py`**: The core logic for batching and payment instructions.
*   **`services/reconciliation.py`**: The "Financial Integrity Engine" that compares internal vs external ledgers and flags anomalies.
*   **`routers/`**: Cleanly separated API endpoints for Claims, Batches, Transactions, and Reconciliation.

#### B. Samanvaya Frontend (`/frontend`)
*   **`pages/Batches.jsx`**: Renamed action flow from "Execute" to "Pay". Features specialized drawers for **Financial Screening**.
*   **`pages/TransactionLedger.jsx`**: Acts as the "Permanent Record". Shows the full history and provides **Clinical Review** drawers for medical deductions.
*   **`pages/SosysMigration.jsx`**: Repurposed as a **Read-Only Ledger Mirror**, representing the legacy system's view of OpenIMIS data.
*   **`pages/Reconciliation.jsx`**: The command center for identifying and resolving financial anomalies.

#### C. Mock Bank Simulator (`/mock-bank`)
*   **`main.py`**: Simulates a banking settlement system. Records payments immediately upon instruction and provides endpoints to **inject anomalies** (Partial Payments, Ghost Payments) for testing.

---

### 5. API Data Exchange & Interoperability

Samanvaya operates through a secure, asynchronous data exchange pattern.

#### 5.1 Payment Instruction (Samanvaya -> Bank)
**Endpoint**: `POST /payout`
**Payload**:
```json
{
  "ref_id": "TXN-UUID",
  "amount": 10500.25,
  "recipient": "Seti Provincial Hospital",
  "metadata": {
    "claim_id": "CLM-001",
    "batch_code": "BATCH-2024-001",
    "simulation": "PAY_LESS"
  }
}
```

#### 5.2 Status Update (Bank -> Samanvaya Webhook)
**Endpoint**: `POST /webhook/gateway`
**Payload**:
```json
{
  "gateway_ref_id": "TXN-UUID",
  "status": "SUCCESS",
  "message": "Settled in Bank Ledger"
}
```

#### 5.3 Internal Data Alignment
Samanvaya ensures that every external API call is wrapped in a local database transaction, ensuring the **Internal Ledger** always reflects the most recent state known from the Bank.

---

### 6. Three-Tier Difference Tracking Logic

Samanvaya distinguishes between different types of financial "missing funds" using the following logic:

1.  **Clinical Difference** (`Claimed - Approved`):
    *   **Reason**: Medical screening rules (e.g., non-covered drugs, limit exceeded).
    *   **Action**: Viewable via "Review" button in the Ledger.
2.  **Financial Difference** (`Approved - Paid`):
    *   **Reason**: Banking artifacts (e.g., processing fees, partial liquidity in bank).
    *   **Action**: Recorded during the mandatory **Financial Screening** step on the Batch page.
3.  **Reconciliation Flag** (`Claimed - Paid`):
    *   **Reason**: The aggregate of all deductions.
    *   **Action**: High-visibility flag in the Reconciliation Console that pulls data from both Clinical and Financial screening history.

---

### 7. Implementation Detail: Simulation Buttons
For the purpose of the demo and verification, specialized simulation tools were added to the Batch Detail page:
*   **Pay Less**: Forcibly instructs the bank to record a settlement amount **90% lower** than the approved amount, triggering a "Financial Screening Required" flag.
*   **Ghost Payment**: Injects a row into the Bank Ledger with a random Claim Code that does **not exist** in OpenIMIS, triggering a "Ghost Payment" flag on the Reconciliation page.

---

### 8. Installation & Execution
1.  Navigate to `Final-Implementation/`.
2.  Run `start.bat` to launch all three services.
3.  Access the Frontend at `http://localhost:5173`.
4.  Access the API documentation at `http://localhost:8000/docs`.
