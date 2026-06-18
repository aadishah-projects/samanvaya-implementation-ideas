To win this hackathon, your module cannot just be an "external app that talks to OpenIMIS via API." It must be a **native, first-class citizen** inside the OpenIMIS ecosystem. 

OpenIMIS uses a specific architectural pattern: **Django (Backend) + React (Frontend) + GraphQL (API Layer)**. 

Here is the deep-dive technical structure for building **Samanvaya** as a native OpenIMIS module.

---

### 1. Backend Structure (Django / Python)

In OpenIMIS, every feature is a Django app. Samanvaya will be structured to leverage OpenIMIS's core models (like `Claim`, `HealthFacility`) while adding its own financial models.

#### Directory Tree
```text
openimis-be-samanvaya/
├── samanvaya/
│   ├── __init__.py
│   ├── apps.py                 # Registers the app, sets up Signals (The "Hook")
│   ├── models.py               # PaymentBatch, PaymentTransaction, GatewayConfig
│   ├── schema.py               # Root GraphQL schema aggregator
│   ├── gql_queries.py          # GraphQL Queries (Fetch ledger, dashboard stats)
│   ├── gql_mutations.py        # GraphQL Mutations (Trigger payment, retry, reconcile)
│   ├── services.py             # Core Business Logic (BulkDisbursementService)
│   ├── tasks.py                # Celery async tasks (Gateway API calls, retries)
│   ├── adapters.py             # Strategy pattern for eSewa, ConnectIPS, MockBank
│   ├── permissions.py          # Custom rights (e.g., 150001: Can execute payment)
│   ├── signal_handlers.py      # Listens to Claim approval events
│   ├── migrations/             # Database migrations
│   └── tests/                  # Unit tests
├── setup.py                    # Package definition
└── README.md
```

#### Crucial Backend Components Explained:

**A. The "Hook" (`signal_handlers.py` & `apps.py`)**
How does Samanvaya know a claim is approved? You don't poll the database. You use Django Signals.
```python
# signal_handlers.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from claim.models import Claim # OpenIMIS core model

@receiver(post_save, sender=Claim)
def trigger_samanvaya_payment(sender, instance, **kwargs):
    # Check if claim status just changed to APPROVED and is part of a bundle
    if instance.status == 'APPROVED' and instance.claim_bundle:
        # Trigger Celery task to add to PaymentBatch asynchronously
        from .tasks import queue_claim_for_payment
        queue_claim_for_payment.delay(instance.id)
```

**B. GraphQL Layer (`gql_mutations.py`)**
OpenIMIS relies heavily on GraphQL. Your frontend will not use REST; it will use GraphQL mutations to trigger actions.
```python
# gql_mutations.py
import graphene
from graphene_django import DjangoObjectType
from .models import PaymentBatch
from .services import PaymentExecutionService

class ExecutePaymentMutation(graphene.Mutation):
    class Arguments:
        batch_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, batch_id):
        # Check permissions (OpenIMIS specific context)
        if not info.context.user.has_perm('samanvaya.execute_payment'):
            raise PermissionDenied("Unauthorized")
            
        service = PaymentExecutionService(info.context.user)
        result = service.execute_batch(batch_id)
        return ExecutePaymentMutation(success=result, message="Batch queued")
```

---

### 2. Frontend Structure (React)

The OpenIMIS frontend is a React application built with Material-UI, Redux, and Apollo Client (for GraphQL). Your module must follow its specific routing and menu registration patterns.

#### Directory Tree
```text
openimis-fe-samanvaya/
├── src/
│   ├── index.js                # Module entry point, registers routes & menu
│   ├── components/
│   │   ├── SamanvayaDashboard.js   # Financial overview (Charts, KPIs)
│   │   ├── PaymentLedger.js        # Data grid of all transactions
│   │   ├── ReconciliationConsole.js# SOSYS migration matching UI
│   │   └── GatewayConfigForm.js    # UI to add bank API keys
│   ├── helpers/
│   │   ├── graphql/
│   │   │   ├── queries.js      # Apollo GraphQL query definitions
│   │   │   └── mutations.js    # Apollo GraphQL mutation definitions
│   ├── constants.js            # Menu keys, permission codes
│   └── translations/
│       ├── en.json             # English translations
│       └── ne.json             # Nepali translations (Huge bonus points!)
├── package.json
└── webpack.config.js
```

#### Crucial Frontend Components Explained:

**A. Menu & Routing Registration (`index.js`)**
You must inject Samanvaya into the OpenIMIS side navigation.
```javascript
// src/index.js
import { defineMessages } from 'react-intl';
import SamanvayaDashboard from './components/SamanvayaDashboard';
import PaymentLedger from './components/PaymentLedger';

const ROUTES = {
    SAMANVAYA_DASHBOARD: 'samanvaya/dashboard',
    SAMANVAYA_LEDGER: 'samanvaya/ledger',
};

// This function is called by OpenIMIS core to build the menu
export function getRoutes() {
    return [
        { path: ROUTES.SAMANVAYA_DASHBOARD, component: SamanvayaDashboard },
        { path: ROUTES.SAMANVAYA_LEDGER, component: PaymentLedger },
    ];
}

export function getMenu(cfg) {
    return {
        key: 'samanvaya', // Unique key
        label: 'Samanvaya Payments',
        // Permission check: Only show if user has the right
        filter: (rights) => rights.includes(150001), 
        subMenu: [
            { key: 'dashboard', label: 'Financial Dashboard', path: ROUTES.SAMANVAYA_DASHBOARD },
            { key: 'ledger', label: 'Transaction Ledger', path: ROUTES.SAMANVAYA_LEDGER },
        ]
    };
}
```

---

### 3. The "Secret Sauce": Deep Integration Points

To make the judges say *"Wow, this is truly native,"* you need to nail these three integration points:

#### 1. The "Blind Spot" Fix (Visualizing the Handoff)
In standard OpenIMIS, when a claim is approved, the UI just says "Approved." 
**Your Hackathon Move:** Add a custom UI widget directly inside the standard OpenIMIS `ClaimDetail` page. 
*   Use OpenIMIS's extension points to inject a `<SamanvayaPaymentStatus />` React component into the Claim view.
*   This component queries your GraphQL API to show a live progress bar: *Claim Approved → Queued in Samanvaya → Sent to eSewa → Success*. This visually proves OpenIMIS is no longer "blind."

#### 2. Idempotency & Concurrency in the Ledger
Payment gateways will send webhooks. Sometimes they send them twice. 
*   In your `PaymentTransaction` model, ensure `gateway_ref_id` has a `unique=True` constraint.
*   In your webhook receiver mutation, use Django's `select_for_update()` or `get_or_create()` to ensure a successful callback doesn't accidentally mark a payment as successful twice, causing a double-payout in the ledger.

#### 3. Reconciliation as a "Shadow" Mode
For the Track 1 migration bridge, don't just make it a separate page. 
*   Create a GraphQL query `getReconciliationAnomalies`.
*   On the main Samanvaya Dashboard, if there are unmatched SOSYS legacy records, show a pulsing red alert: *"Migration Alert: 14 Unmatched SOSYS Records Detected."* This shows the judges you are thinking about the *transition*, not just the end-state.

---

### 💡 Hackathon Survival Guide for OpenIMIS

OpenIMIS can be a heavy, complex beast to spin up locally. Here is how you don't waste 12 hours on environment setup:

1. **Don't build from scratch:** Use the official `openimis-be-dist` and `openimis-fe-dist` Docker repositories. 
2. **Mount your module as a volume:** In the `docker-compose.yml`, map your local `samanvaya` folder directly into the container's `/app/openimis/` directory. This gives you hot-reloading.
3. **The GraphQL Trap:** OpenIMIS uses Graphene. If you make a mistake in your `schema.py` (like a circular import), the *entire* backend will crash with a 500 error and no clear logs. **Test your GraphQL schema locally with a simple Python script before running the Docker container.**
4. **Frontend Build Times:** React builds in OpenIMIS can take 3-5 minutes. During the hackathon, run the frontend in `npm start` (development mode) for fast hot-reloading, and only run `npm run build` right before your final demo.
5. **Mock the Bank, Don't Fake the UI:** The judges will care more about a beautiful, responsive React dashboard interacting with a "Mock Bank" than a ugly dashboard interacting with a real bank API. Spend 70% of your UI time on the **Ledger Data Grid** and the **Dashboard Charts**.

By structuring Samanvaya exactly like this, you aren't just building a payment app; you are building the *missing financial nervous system* of OpenIMIS.