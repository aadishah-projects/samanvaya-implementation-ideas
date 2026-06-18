Here is a deep dive into the **Technical Architecture** for **Samanvaya**. Since OpenIMIS is built on a specific tech stack (Django for backend, React for frontend, PostgreSQL for DB), this architecture is designed to integrate seamlessly as a native OpenIMIS module while leveraging modern asynchronous patterns for payment processing.

---

### 1. High-Level System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        OpenIMIS Ecosystem                               │
│  ┌──────────────────────┐       ┌───────────────────────────────────┐   │
│  │   Core OpenIMIS      │       │      SAMANVAYA MODULE (Native)    │   │
│  │  (Enrollment, Claims,│ Hook  │                                   │   │
│  │   Approvals)         ├──────►│  1. Bulk Disbursement Engine      │   │
│  └──────────────────────┘       │  2. Transaction Ledger            │   │
│                                 │  3. Reconciliation Engine         │   │
│                                 └──────────────┬────────────────────┘   │
└────────────────────────────────────────────────┼────────────────────────┘
                                                 │
                      ┌──────────────────────────┼──────────────────────────┐
                      │                          │                          │
                      ▼                          ▼                          ▼
         ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
         │  Payment Gateways  │      │  Async Task Queue  │      │  Legacy SOSYS DB   │
         │ (eSewa, ConnectIPS,│◄────►│  (Celery + Redis)  │      │  (CSV/DB Import)   │
         │  RTGS, Mock Bank)  │ API  │                    │      │                    │
         └────────────────────┘      └────────────────────┘      └────────────────────┘
```

---

### 2. Backend Architecture (Python / Django)

OpenIMIS modules are essentially Django apps. Samanvaya will be structured as a suite of Django apps to maintain separation of concerns.

#### Module Breakdown:
1. **`samanvaya_core`**: The heart of the system. Handles the Transaction Ledger, state machines, and batch generation.
2. **`samanvaya_gateway`**: The Adapter layer. Contains the Strategy Pattern implementation to talk to different payment rails.
3. **`samanvaya_recon`**: The migration bridge. Handles CSV parsing, matching algorithms, and anomaly flagging.
4. **`samanvaya_workers`**: Celery tasks for asynchronous payment execution, webhook processing, and retry mechanisms.

#### Asynchronous Processing (Crucial for Payments):
You cannot process bulk payments synchronously in a web request. 
* **Tech Stack**: **Celery** (Task Queue) + **Redis** (Message Broker).
* **Flow**: When a claim bundle is approved, a `PaymentBatch` is created. A Celery task is triggered to split the batch into individual `PaymentTransaction` records and queue them for execution.

---

### 3. Database Schema Design (PostgreSQL)

Here are the core models required to make the system robust and auditable.

```python
# 1. The Batch (Groups approved claims together)
class PaymentBatch(models.Model):
    batch_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    claim_bundle_ref = models.ForeignKey(ClaimBundle, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('PARTIAL', 'Partial')])
    created_at = models.DateTimeField(auto_now_add=True)

# 2. The Ledger (The single source of truth for every cent)
class PaymentTransaction(models.Model):
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    batch = models.ForeignKey(PaymentBatch, related_name='transactions')
    provider_hospital = models.ForeignKey(HealthFacility, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # State Machine
    status = models.CharField(choices=[
        ('QUEUED', 'Queued'), 
        ('INITIATED', 'Initiated at Gateway'), 
        ('SUCCESS', 'Success'), 
        ('FAILED', 'Failed'), 
        ('REVERSED', 'Reversed')
    ], default='QUEUED')
    
    gateway_ref_id = models.CharField(max_length=100, blank=True) # ID from eSewa/Bank
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# 3. Gateway Configuration (Securely stored credentials)
class GatewayConfig(models.Model):
    gateway_name = models.CharField(max_length=50) # 'esewa', 'connectips', 'mock'
    api_endpoint = models.URLField()
    # Credentials should be encrypted at rest using Django's EncryptedTextField
    api_key = EncryptedTextField() 
    secret_key = EncryptedTextField()
    is_active = models.BooleanField(default=True)
```

---

### 4. Payment Gateway Adapter (Strategy Pattern)

To ensure OpenIMIS isn't locked into one bank, we use the **Strategy Pattern**. This makes the hackathon demo incredibly flexible (you can switch to a "Mock Bank" for the live demo to guarantee success).

```python
# samanvaya_gateway/adapters.py

class BasePaymentAdapter(ABC):
    @abstractmethod
    def initiate_payment(self, transaction: PaymentTransaction) -> dict:
        pass

    @abstractmethod
    def verify_status(self, gateway_ref_id: str) -> str:
        pass

class ESewaAdapter(BasePaymentAdapter):
    def initiate_payment(self, transaction):
        # Real eSewa API call logic
        pass

class MockBankAdapter(BasePaymentAdapter):
    def initiate_payment(self, transaction):
        # Hackathon Demo Logic: 
        # Simulates network delay, randomly returns Success/Fail/Pending
        import random
        time.sleep(2) 
        outcome = random.choice(['SUCCESS', 'FAILED', 'PENDING'])
        return {'status': outcome, 'ref_id': f"MOCK-{uuid.uuid4().hex[:8]}"}

# Factory to get the right adapter
def get_adapter(gateway_name):
    adapters = {'esewa': ESewaAdapter, 'mock': MockBankAdapter}
    return adapters[gateway_name]()
```

---

### 5. Reconciliation Engine (Track 1 Migration Bridge)

This is your "safety net" feature. It proves to the judges that you understand the real-world problem of migrating from a legacy system (SOSYS).

**Workflow:**
1. **Ingestion**: Admin uploads a `SOSYS_Legacy_Payouts.csv`.
2. **Parsing**: Pandas (or Django ORM) reads the CSV into a temporary `LegacySOSYSRecord` table.
3. **Matching Algorithm**: 
   * *Primary Match*: `Claim_ID` + `Exact_Amount`
   * *Fuzzy Match*: `Provider_Name` + `Date_Range` + `Amount_Tolerance_±1%`
4. **Anomaly Flagging**: 
   * *Ghost Payment*: SOSYS says paid, OpenIMIS has no record.
   * *Double Payment*: SOSYS says paid, OpenIMIS says paid, but amounts differ.
   * *Orphan*: OpenIMIS says paid, SOSYS has no record.
5. **Resolution UI**: A dashboard where finance officers can manually override or mark anomalies as "Resolved".

---

### 6. Frontend Architecture (React)

OpenIMIS uses React. Samanvaya's frontend will be a set of React components injected into the OpenIMIS navigation menu.

**Key Views to Build for the Demo:**
1. **The "Command Center" Dashboard**:
   * Big, bold numbers: *Total Disbursed Today (NPR)*, *Success Rate %*, *Pending Batches*.
   * A live-updating line chart showing payment volume over the last 24 hours.
2. **The Ledger (Data Grid)**:
   * A highly filterable table (using Material-UI DataGrid).
   * Columns: `Date`, `Hospital`, `Amount`, `Status` (with color-coded chips: Green=Success, Red=Failed, Yellow=Processing).
   * Action: "Retry Failed Payment" button.
3. **Reconciliation Console**:
   * Split screen: Left side shows SOSYS legacy data, Right side shows OpenIMIS data.
   * Highlighted rows showing mismatches in red.

---

### 7. Security & Compliance (Crucial for Fintech/Healthtech)

Even in a hackathon, mentioning these will score you massive bonus points with technical judges:

* **Data Encryption**: Bank account numbers and IFSC codes in the database must be encrypted at rest (using `django-fernet` or AWS KMS).
* **Audit Trails**: Every status change in the `PaymentTransaction` model should log *who* changed it and *when* (using `django-simple-history`).
* **Idempotency**: The Gateway Adapter must use idempotency keys. If a network call times out, retrying the exact same request won't result in a double payment.
* **Webhook Security**: When the bank sends a callback (e.g., "Payment Successful"), the endpoint must verify the webhook signature to prevent spoofed payment confirmations.

---

### 💡 Hackathon Execution Strategy

If you are short on time, **build in this exact order**:
1. **Mock Bank + Ledger**: Get the database and the Mock Adapter working. Show a payment going from `QUEUED` to `SUCCESS`.
2. **Dashboard**: Build the React UI to show the ledger updating in real-time.
3. **Bulk Engine**: Add the Celery task to process 50 claims at once.
4. **Reconciliation**: *Only build the UI and a simple matching script.* Don't waste time on complex fuzzy matching algorithms unless you have extra hours. The *concept* and the *UI* are enough to sell the vision.