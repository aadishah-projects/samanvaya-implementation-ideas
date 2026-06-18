Integrating a payment gateway into a core health information system like OpenIMIS is not just about making an HTTP POST request. It is about building a **financial-grade state machine** that guarantees every single cent is accounted for, even when networks fail or banks go down.

Here is the deep-dive technical approach for the **Samanvaya Payment Gateway Integration**, designed to impress technical judges and ensure a flawless hackathon demo.

---

### 1. Architectural Pattern: The Adapter & Strategy Pattern

OpenIMIS must never have hardcoded logic for eSewa, ConnectIPS, or RTGS. We use the **Strategy Pattern** to abstract the gateway. This allows you to swap the "Mock Bank" during the demo with the "Real eSewa API" in production without changing a single line of core business logic.

```python
# samanvaya/gateways/base.py
from abc import ABC, abstractmethod
from decimal import Decimal

class PayoutResponse:
    def __init__(self, success: bool, gateway_ref: str, status: str, raw_response: dict, error_msg: str = None):
        self.success = success
        self.gateway_ref = gateway_ref
        self.status = status # 'INITIATED', 'SUCCESS', 'FAILED', 'PENDING'
        self.raw_response = raw_response
        self.error_msg = error_msg

class BasePaymentGateway(ABC):
    @abstractmethod
    def initiate_bulk_payout(self, batch_id: str, transactions: list, idempotency_key: str) -> PayoutResponse:
        pass

    @abstractmethod
    def verify_transaction_status(self, gateway_ref: str) -> PayoutResponse:
        pass
        
    @abstractmethod
    def process_webhook(self, headers: dict, payload: dict) -> PayoutResponse:
        pass
```

```python
# samanvaya/gateways/esewa.py & mock.py
class ESewaGateway(BasePaymentGateway):
    def initiate_bulk_payout(self, batch_id, transactions, idempotency_key):
        # 1. Format payload to eSewa's specific FTPL/API standard
        # 2. Sign the request using Merchant Secret Key
        # 3. Make HTTP POST
        # 4. Parse response and return PayoutResponse
        pass

class MockBankGateway(BasePaymentGateway):
    """Used for Hackathon Demo & Unit Testing"""
    def initiate_bulk_payout(self, batch_id, transactions, idempotency_key):
        import time, random
        time.sleep(1.5) # Simulate network latency
        
        # Simulate real-world bank behavior: 80% success, 10% fail, 10% pending
        roll = random.random()
        if roll < 0.8:
            return PayoutResponse(True, f"MOCK-{batch_id[:8]}", "SUCCESS", {"code": "00"})
        elif roll < 0.9:
            return PayoutResponse(False, "", "FAILED", {"code": "99"}, "Insufficient funds in provider account")
        else:
            return PayoutResponse(False, f"MOCK-PENDING-{batch_id[:8]}", "PENDING", {"code": "02"})
```

---

### 2. The 3 Pillars of Gateway Interaction

A robust payment integration relies on three distinct communication flows. You must build all three.

#### Pillar A: Outbound Payout (Synchronous Initiation)
When OpenIMIS approves a claim bundle, Samanvaya triggers the gateway. 
* **Crucial Rule:** The gateway will almost *never* return "SUCCESS" immediately. It will return "ACCEPTED" or "PENDING". 
* **Action:** Your system must immediately update the `PaymentTransaction` status to `INITIATED` (not `SUCCESS`) and save the `gateway_ref_id`.

#### Pillar B: Inbound Webhooks (Asynchronous Notification)
When the bank finishes processing, it sends a POST request to your webhook endpoint.
* **Security:** You **must** verify the webhook signature (e.g., HMAC-SHA256) using the gateway's secret key. If the signature fails, reject the webhook. This prevents malicious actors from spoofing "Payment Successful" messages.
* **Action:** Parse the payload, find the transaction by `gateway_ref_id`, and update the status to `SUCCESS` or `FAILED`.

#### Pillar C: Active Polling (The Safety Net)
Webhooks fail. Networks drop. You cannot rely solely on webhooks.
* **Action:** Create a Celery Beat task that runs every 5 minutes. It queries all `PaymentTransaction` records where `status == 'INITIATED'` and `created_at < 10 minutes ago`. It actively calls the gateway's `verify_transaction_status` API to check if the money actually moved.

---

### 3. Financial-Grade Reliability (The "Judge Winners")

If you explain these concepts in your pitch, the technical judges will instantly recognize you as senior engineers.

#### A. Idempotency (Preventing Double Payments)
If a network call times out, Celery might retry the task. If you just send the request again, the bank might process it twice, paying the hospital double.
* **Solution:** Generate a unique `idempotency_key` (e.g., a UUID) for every `PaymentTransaction`. Pass this key in the HTTP Header (`Idempotency-Key: <uuid>`) to the gateway. If the gateway receives the same key twice, it returns the original result without processing a new payment.

#### B. Concurrency & Race Conditions
What if a Webhook and an Active Polling task try to update the same transaction at the exact same millisecond?
* **Solution:** Use Database Row Locking. In Django:
  ```python
  from django.db import transaction
  
  with transaction.atomic():
      # select_for_update() locks the row until the transaction commits
      tx = PaymentTransaction.objects.select_for_update().get(gateway_ref_id=ref_id)
      if tx.status == 'INITIATED': # Only update if it hasn't been updated by the other process
          tx.status = 'SUCCESS'
          tx.save()
  ```

#### C. Immutable Raw Logs (The Audit Trail)
In fintech, if it isn't logged, it didn't happen. 
* **Solution:** Add `raw_request_payload` (JSONField) and `raw_response_payload` (JSONField) to your `PaymentTransaction` model. Every time you talk to the gateway, dump the exact HTTP request and response into these fields. When a hospital complains about missing funds, you can show the judge/exact JSON sent to the bank.

---

### 4. Hackathon Execution Strategy: The "Mock Bank" UI

Since you won't get real eSewa/ConnectIPS merchant credentials in time for the hackathon, **build a Mock Bank Server**. This is your secret weapon for the demo.

Build a tiny, separate FastAPI or Node.js server (e.g., running on `localhost:8001`) that acts as the Bank.

**Make the Mock Bank Interactive for the Demo:**
Instead of just returning random successes/failures, give the Mock Bank a simple UI.
1. When Samanvaya sends a payout request, the Mock Bank puts it in a "Pending" queue.
2. During your live pitch, you open the Mock Bank UI on the screen.
3. You say to the judges: *"Notice how the payment is pending. In the real world, this is the bank's internal processing. Let's simulate a manual bank approval."*
4. You click **"Approve"** on the Mock Bank UI.
5. The Mock Bank instantly fires a Webhook to your OpenIMIS Samanvaya module.
6. The Samanvaya Dashboard updates in real-time to show **"SUCCESS"**.

*This interactive demo proves you understand asynchronous banking flows better than 99% of hackathon teams.*

---

### 5. Database Schema Additions for Gateway

Update your `PaymentTransaction` model to support these gateway features:

```python
class PaymentTransaction(models.Model):
    # ... existing fields ...
    
    # Gateway Specifics
    gateway_name = models.CharField(max_length=50) # 'esewa', 'mock', 'connectips'
    gateway_ref_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Financial Grade Audit Fields
    raw_request_log = models.JSONField(null=True, blank=True)
    raw_response_log = models.JSONField(null=True, blank=True)
    webhook_received_at = models.DateTimeField(null=True, blank=True)
    
    # Retry Logic
    retry_count = models.IntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
```

---

### 💡 Summary of the Integration Pitch

When presenting this part of Samanvaya, use this narrative:

> *"Most integrations just make an API call and hope for the best. Samanvaya treats the payment gateway as an unreliable external actor. We implemented the **Strategy Pattern** to abstract the rails, **Idempotency Keys** to prevent double-payouts, **Row-level locking** to handle webhook race conditions, and an **Active Polling mechanism** as a safety net for dropped webhooks. Furthermore, we log every raw HTTP payload for absolute auditability. We didn't just build a payment button; we built a financial-grade ledger."*