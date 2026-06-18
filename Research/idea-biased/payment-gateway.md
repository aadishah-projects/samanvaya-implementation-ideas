# Samanvaya — Payment Gateway Integration

Integrating a payment gateway is not just about making an HTTP POST request. Even in a standalone demo, we build this like a **financial-grade state machine** — because the judges will ask hard questions, and the architecture needs to hold up.

---

## 1. Architectural Pattern: The Adapter (Strategy Pattern)

Samanvaya never hardcodes logic for any specific bank. We use the **Strategy Pattern** to abstract the gateway. This means:
- The hackathon runs against **MockBank**
- Production swaps in **eSewa**, **ConnectIPS**, or **RTGS** without touching any business logic

```python
# backend/services/gateway/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PayoutResponse:
    success: bool
    gateway_ref: str
    status: str          # 'INITIATED', 'SUCCESS', 'FAILED', 'PENDING'
    raw_response: dict
    request_payload: dict
    error_msg: str = None

class BasePaymentGateway(ABC):
    @abstractmethod
    def initiate_payout(self, ref_id: str, amount: float, recipient: str) -> PayoutResponse:
        pass

    @abstractmethod
    def verify_status(self, gateway_ref: str) -> PayoutResponse:
        pass
```

```python
# backend/services/gateway/mock_bank.py
import httpx, uuid

class MockBankGateway(BasePaymentGateway):
    BASE_URL = "http://localhost:8001"

    def initiate_payout(self, ref_id, amount, recipient):
        payload = {
            "ref_id": ref_id,
            "amount": amount,
            "recipient": recipient
        }
        resp = httpx.post(f"{self.BASE_URL}/payout", json=payload, timeout=5.0)
        data = resp.json()

        return PayoutResponse(
            success=True,
            gateway_ref=data["gateway_ref_id"],
            status="INITIATED",
            raw_response=data,
            request_payload=payload
        )

    def verify_status(self, gateway_ref):
        resp = httpx.get(f"{self.BASE_URL}/status/{gateway_ref}")
        data = resp.json()
        return PayoutResponse(
            success=data["status"] == "SUCCESS",
            gateway_ref=gateway_ref,
            status=data["status"],
            raw_response=data,
            request_payload={}
        )
```

```python
# backend/services/gateway/esewa.py (stub — swap in for production)
class ESewaGateway(BasePaymentGateway):
    def initiate_payout(self, ref_id, amount, recipient):
        # Format payload to eSewa FTPL/API standard
        # Sign request with Merchant Secret Key
        # POST to eSewa endpoint
        # Parse and return PayoutResponse
        pass
```

---

## 2. The 3 Pillars of Gateway Interaction

Every production payment integration has three communication flows. Samanvaya implements all three — even against the Mock Bank — because this is what separates a real financial system from a toy.

### Pillar A: Outbound Payout (Synchronous Initiation)

When a batch is executed, Samanvaya sends a payout request to the gateway.

**Crucial rule:** Banks almost never return `SUCCESS` immediately. They return `INITIATED` or `PENDING`. Your system must:
1. Mark the transaction as `PROCESSING`
2. Store the `gateway_ref_id`
3. Wait for a webhook (or poll) — never assume success from the initiation response

### Pillar B: Inbound Webhook (Asynchronous Notification)

When the bank finishes processing, it POSTs back to your webhook endpoint.

**For the demo:** Mock Bank fires this webhook when you click "Approve" in its UI — giving you a real-time status flip on the Samanvaya dashboard.

**In production:** Verify the webhook signature (HMAC-SHA256) using the gateway's secret key before trusting any payload. If the signature fails, reject it — this prevents attackers from spoofing "Payment Successful" messages.

### Pillar C: Active Polling (The Safety Net)

Webhooks fail. Networks drop. Don't rely on them alone.

Run a background task (APScheduler for FastAPI, or Celery if you want it heavier) that:
- Queries all `PaymentTransaction` records where `status == 'PROCESSING'` and `created_at < 10 minutes ago`
- Calls `gateway.verify_status(gateway_ref)` for each
- Updates the transaction status accordingly

```python
# backend/services/poller.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", minutes=5)
async def poll_pending_transactions():
    with get_db() as db:
        stale = db.query(PaymentTransaction).filter(
            PaymentTransaction.status == "PROCESSING",
            PaymentTransaction.created_at < datetime.utcnow() - timedelta(minutes=10)
        ).all()

        gateway = MockBankGateway()
        for tx in stale:
            result = gateway.verify_status(tx.gateway_ref_id)
            tx.status = result.status
            db.commit()
```

---

## 3. Financial-Grade Reliability

These are the concepts that will impress technical judges when you explain them.

### A. Idempotency (Preventing Double Payments)

If a network call times out and retries, you could accidentally pay a hospital twice.

**Solution:** Generate a unique `idempotency_key` (UUID) for every `PaymentTransaction`. Pass it in every request to the gateway. If the gateway receives the same key twice, it returns the original result without processing a new payment.

```python
# Generated once at transaction creation, never changes
idempotency_key = uuid.uuid4()

# Passed to the gateway on every attempt (including retries)
payload["idempotency_key"] = str(tx.idempotency_key)
```

### B. Concurrency & Race Conditions

What if a webhook callback and the polling task both try to update the same transaction at the same millisecond?

**Solution:** Database row locking.

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

with db.begin():
    tx = db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.gateway_ref_id == ref_id)
        .with_for_update()  # Locks the row until this transaction commits
    ).scalar_one_or_none()

    if tx and tx.status == "PROCESSING":
        tx.status = "SUCCESS"
        # Only one process can be here at a time
```

### C. Immutable Raw Logs (The Audit Trail)

In fintech, if it is not logged, it did not happen.

Every `PaymentTransaction` stores:
- `raw_request_log` (JSON) — exact payload sent to the gateway
- `raw_response_log` (JSON) — exact response received

When a hospital disputes a payment, you can show the literal HTTP exchange — not just "our system says it was sent."

---

## 4. The Mock Bank Demo Strategy

This is your biggest demo advantage. Build the Mock Bank to be **interactive**, not just random.

**How it works during the pitch:**

1. You execute a batch in Samanvaya → transactions move to `Processing`
2. You open the Mock Bank UI (a second browser tab) on screen
3. You say: *"Notice the payment is pending. In the real world, this is the bank's internal processing. Let's simulate the bank approving it."*
4. You click **"Approve"** on the Mock Bank UI
5. Mock Bank fires a webhook to Samanvaya
6. Samanvaya dashboard flips to **"SUCCESS"** in real-time
7. The Financial Dashboard total updates

Then for the failure demo:
- Click **"Reject"** on a second transaction
- Samanvaya marks it `Failed`, shows it in red on the ledger
- Retry button attempts the payout again (with a new idempotency key)

*This interactive flow proves you understand async banking better than 99% of hackathon teams.*

---

## 5. Mock Bank UI (Minimal HTML)

Keep it dead simple — this is a control panel, not a product.

```html
<!-- mock-bank/ui/index.html -->
<!DOCTYPE html>
<html>
<body>
  <h2>🏦 Mock Bank Control Panel</h2>
  <div id="queue"></div>
  <script>
    async function loadQueue() {
      const res = await fetch('/pending');
      const items = await res.json();
      document.getElementById('queue').innerHTML = items.map(item => `
        <div style="border:1px solid #ccc; padding:10px; margin:8px;">
          <b>${item.recipient}</b> — NPR ${item.amount}<br/>
          Ref: ${item.ref_id}<br/>
          <button onclick="approve('${item.ref_id}')">✅ Approve</button>
          <button onclick="reject('${item.ref_id}')">❌ Reject</button>
        </div>
      `).join('');
    }

    async function approve(ref_id) {
      await fetch(`/approve/${ref_id}`, { method: 'POST' });
      loadQueue();
    }

    async function reject(ref_id) {
      await fetch(`/reject/${ref_id}`, { method: 'POST' });
      loadQueue();
    }

    loadQueue();
    setInterval(loadQueue, 3000); // Auto-refresh
  </script>
</body>
</html>
```

---

## 6. Pitch Summary for This Section

> *"Most integrations just make an API call and hope for the best. Samanvaya treats the payment gateway as an unreliable external actor. We implemented the Strategy Pattern to abstract the rails, Idempotency Keys to prevent double-payouts, row-level locking to handle webhook race conditions, and an Active Polling mechanism as a safety net for dropped webhooks. Every raw HTTP payload is logged for absolute auditability. We didn't build a payment button — we built a financial-grade ledger."*
