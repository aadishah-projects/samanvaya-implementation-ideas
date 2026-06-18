# Samanvaya — Standalone Module Structure

Since we are not running a live OpenIMIS instance, Samanvaya is built as a **self-contained FastAPI + React application** that mirrors OpenIMIS's data conventions exactly. It is OpenIMIS-compatible by design — meaning you can plug it in later — but it runs independently on any laptop.

---

## 1. Overall Project Structure

```text
samanvaya/
├── backend/                   # FastAPI app (Python)
│   ├── main.py                # App entry point, router registration
│   ├── database.py            # SQLAlchemy engine + session setup
│   ├── models.py              # All DB models (Claim, Batch, Transaction, etc.)
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── routers/
│   │   ├── claims.py          # GET claims, POST approve (simulates OpenIMIS)
│   │   ├── batches.py         # POST create batch, POST execute batch
│   │   ├── transactions.py    # GET ledger, GET transaction detail
│   │   ├── reconciliation.py  # POST upload SOSYS CSV, GET anomalies
│   │   ├── dashboard.py       # GET summary stats for dashboard
│   │   └── webhooks.py        # POST /webhook/gateway — receives bank callbacks
│   ├── services/
│   │   ├── disbursement.py    # Core bulk payment logic + state machine
│   │   ├── reconciliation.py  # SOSYS CSV matching algorithm
│   │   └── gateway/
│   │       ├── base.py        # Abstract gateway interface
│   │       ├── mock_bank.py   # MockBank adapter (calls localhost:8001)
│   │       └── esewa.py       # eSewa stub (swap in for production)
│   ├── seed.py                # Seeds DB with Nepali demo data
│   └── requirements.txt
│
├── mock-bank/                 # Separate FastAPI server — simulates a bank
│   ├── main.py                # Payout queue, approve/reject endpoints
│   ├── ui/                    # Simple HTML+JS UI for demo control
│   └── requirements.txt
│
└── frontend/                  # React app
    ├── src/
    │   ├── App.jsx
    │   ├── pages/
    │   │   ├── Dashboard.jsx          # KPI cards + charts
    │   │   ├── ClaimsQueue.jsx        # Approved claims, batch creation
    │   │   ├── TransactionLedger.jsx  # Full payment history
    │   │   └── Reconciliation.jsx     # SOSYS upload + anomaly view
    │   ├── components/
    │   │   ├── StatusBadge.jsx        # Color-coded status pill
    │   │   ├── PaymentProgressBar.jsx # Claim → Queued → Sent → Success
    │   │   └── AnomalyAlert.jsx       # Pulsing red alert widget
    │   └── api/
    │       └── client.js              # Axios calls to backend
    └── package.json
```

---

## 2. Backend Deep Dive

### A. Models (`models.py`)

These mirror OpenIMIS's naming conventions so the module is recognizable to OpenIMIS developers.

```python
# models.py
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid, enum

class ClaimStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    QUEUED = "QUEUED"
    PROCESSED = "PROCESSED"

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

class Claim(Base):
    __tablename__ = "claims"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    claim_code = Column(String, unique=True)          # e.g. "CLM-2024-001"
    health_facility = Column(String)                  # "Bir Hospital"
    insuree_name = Column(String)
    claimed_amount = Column(Float)                    # in NPR
    approved_amount = Column(Float)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.APPROVED)
    approved_date = Column(DateTime)

class PaymentBatch(Base):
    __tablename__ = "payment_batches"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime)
    total_amount = Column(Float)
    claim_count = Column(Integer)
    status = Column(String)                           # QUEUED, EXECUTING, DONE, PARTIAL

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID, ForeignKey("payment_batches.id"))
    claim_id = Column(UUID, ForeignKey("claims.id"))
    amount = Column(Float)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    idempotency_key = Column(UUID, unique=True, default=uuid.uuid4)
    gateway_name = Column(String)                     # "mock_bank", "esewa"
    gateway_ref_id = Column(String, unique=True, nullable=True)
    raw_request_log = Column(JSON, nullable=True)
    raw_response_log = Column(JSON, nullable=True)
    webhook_received_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

---

### B. The Disbursement Service (`services/disbursement.py`)

This is the core of Samanvaya — the payment state machine.

```python
# services/disbursement.py
from ..models import PaymentBatch, PaymentTransaction, TransactionStatus
from .gateway.base import BasePaymentGateway

class BulkDisbursementService:
    def __init__(self, db, gateway: BasePaymentGateway):
        self.db = db
        self.gateway = gateway

    def execute_batch(self, batch_id: str):
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        transactions = self.db.query(PaymentTransaction).filter_by(batch_id=batch_id).all()

        for tx in transactions:
            if tx.status != TransactionStatus.PENDING:
                continue  # Skip already-processed transactions

            tx.status = TransactionStatus.PROCESSING
            self.db.commit()

            response = self.gateway.initiate_payout(
                ref_id=str(tx.idempotency_key),
                amount=tx.amount,
                recipient=tx.claim.health_facility
            )

            tx.raw_request_log = response.request_payload
            tx.raw_response_log = response.raw_response
            tx.gateway_ref_id = response.gateway_ref

            if response.status == "SUCCESS":
                tx.status = TransactionStatus.SUCCESS
            elif response.status == "FAILED":
                tx.status = TransactionStatus.FAILED
            else:
                tx.status = TransactionStatus.PENDING  # Awaiting webhook

            self.db.commit()
```

---

### C. Webhook Receiver (`routers/webhooks.py`)

Handles async callbacks from the Mock Bank (or real bank in production).

```python
# routers/webhooks.py
@router.post("/webhook/gateway")
async def receive_webhook(payload: dict, db: Session = Depends(get_db)):
    ref_id = payload.get("gateway_ref_id")
    status = payload.get("status")  # "SUCCESS" or "FAILED"

    # Idempotency: lock the row before updating
    tx = db.query(PaymentTransaction).filter_by(
        gateway_ref_id=ref_id
    ).with_for_update().first()

    if not tx or tx.status not in ("PENDING", "PROCESSING"):
        return {"ok": True, "note": "already_processed"}

    tx.status = TransactionStatus.SUCCESS if status == "SUCCESS" else TransactionStatus.FAILED
    tx.webhook_received_at = datetime.utcnow()
    tx.raw_response_log = payload
    db.commit()

    return {"ok": True}
```

---

## 3. Frontend Deep Dive

### A. Claims Queue (`pages/ClaimsQueue.jsx`)

Simulates the OpenIMIS "handoff" — this is where claims enter Samanvaya.

```jsx
// Key interaction
const handleExecuteBatch = async (batchId) => {
  setStatus("Executing...");
  await api.post(`/batches/${batchId}/execute`);
  // Poll or use WebSocket to show live status updates
  pollBatchStatus(batchId);
};
```

### B. Payment Progress Bar (`components/PaymentProgressBar.jsx`)

The "blind spot fix" — visually proves Samanvaya has end-to-end visibility.

```jsx
const steps = ["Claim Approved", "Queued in Samanvaya", "Sent to Bank", "Confirmed"];
// Each step lights up as the transaction moves through states
```

### C. Live Status Updates

Use **polling** (simpler, reliable for hackathon) or WebSockets:

```javascript
// Simple polling — refresh transaction status every 3 seconds
const pollBatchStatus = (batchId) => {
  const interval = setInterval(async () => {
    const res = await api.get(`/batches/${batchId}/transactions`);
    setTransactions(res.data);
    if (res.data.every(tx => ["SUCCESS", "FAILED"].includes(tx.status))) {
      clearInterval(interval);
    }
  }, 3000);
};
```

---

## 4. The Mock Bank Server

This is your secret demo weapon. Run it separately on `localhost:8001`.

```python
# mock-bank/main.py (FastAPI)
pending_payouts = {}  # In-memory queue

@app.post("/payout")
async def receive_payout(payload: dict):
    ref_id = payload["ref_id"]
    pending_payouts[ref_id] = {"status": "PENDING", **payload}
    return {"gateway_ref_id": ref_id, "status": "INITIATED"}

@app.post("/approve/{ref_id}")
async def approve_payout(ref_id: str):
    # Fire webhook back to Samanvaya
    import httpx
    pending_payouts[ref_id]["status"] = "SUCCESS"
    await httpx.post("http://localhost:8000/webhook/gateway", json={
        "gateway_ref_id": ref_id,
        "status": "SUCCESS"
    })
    return {"ok": True}

@app.post("/reject/{ref_id}")
async def reject_payout(ref_id: str):
    pending_payouts[ref_id]["status"] = "FAILED"
    await httpx.post("http://localhost:8000/webhook/gateway", json={
        "gateway_ref_id": ref_id,
        "status": "FAILED"
    })
    return {"ok": True}
```

The Mock Bank also serves a minimal HTML page (`/ui`) that lists pending payouts with Approve / Reject buttons — open it on a second browser window during the demo.

---

## 5. Hackathon Survival Tips (Standalone Edition)

| Problem | Solution |
|---|---|
| No real bank API credentials | Use Mock Bank — it's more impressive for the demo anyway |
| Slow frontend builds | Use `vite` instead of CRA — instant hot reload |
| State management complexity | Keep it simple: local React state + polling. No Redux needed. |
| Database setup | Use SQLite for the hackathon — zero config, works anywhere |
| CORS issues between frontend and backend | Add `fastapi.middleware.cors.CORSMiddleware` with `allow_origins=["*"]` |

By building it this way, you get a fully working demo on any laptop in under an hour of setup — and the architecture is clean enough that plugging it into a real OpenIMIS instance later is just a matter of replacing the seeded claims data with live OpenIMIS GraphQL calls.
