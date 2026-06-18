In the context of OpenIMIS deployments in Nepal (specifically for the **Health Insurance Board / Swasthya Bima Board**), **SOSYS** (or similar proprietary local middleware) acts as the **Payment Gateway Aggregator / Middleware**. It sits between OpenIMIS and the actual payment rails (banks, eSewa, Khalti, ConnectIPS, etc.) to handle premium collections and claim payouts.

Because SOSYS is a **proprietary, locally developed, or vendor-specific middleware**, there are **no official public internet resources or open-source documentation specifically for "SOSYS"**. 

However, to achieve your goal—**building a standalone NCHL-IPS system to completely replace SOSYS**—you do not need SOSYS documentation. You need to understand **how OpenIMIS expects to receive payment data** so you can replicate the "SOSYS handshake" with your own custom NCHL-IPS middleware.

Here are the exact resources and a step-by-step guide to bypassing SOSYS and integrating your standalone NCHL-IPS system directly into OpenIMIS.

---

### 🌐 1. Core OpenIMIS Payment Architecture Resources (To Replace SOSYS)

To replace SOSYS, your standalone system must speak the exact same "language" to OpenIMIS that SOSYS currently uses. You need to study the core OpenIMIS Payment and Contribution modules.

*   **OpenIMIS Backend Payment Module (Source Code & Logic):**
    *   **URL:** [https://github.com/openimis/openimis-be-payment_py](https://github.com/openimis/openimis-be-payment_py)
    *   **Use:** This is the exact code SOSYS interacts with. Study the `models.py` (to understand the database schema for payments) and `services.py` (to understand how a payment is validated and matched to an insuree's premium).
*   **OpenIMIS Backend Contribution Module:**
    *   **URL:** [https://github.com/openimis/openimis-be-contribution_py](https://github.com/openimis/openimis-be-contribution_py)
    *   **Use:** In OpenIMIS, a "Payment" is just money received. A "Contribution" is that money linked to a specific Insuree/Policy. Your NCHL-IPS system must ultimately create a Contribution.
*   **OpenIMIS API & GraphQL Documentation:**
    *   **URL:** [https://docs.openimis.org/en/latest/cookbook/rest_api.html](https://docs.openimis.org/en/latest/cookbook/rest_api.html)
    *   **URL:** [https://docs.openimis.org/en/latest/cookbook/graphql.html](https://docs.openimis.org/en/latest/cookbook/graphql.html)
    *   **Use:** OpenIMIS uses REST for external integrations and GraphQL for internal/frontend communication. Your standalone NCHL-IPS middleware will use the **REST API** to push payment confirmations into OpenIMIS.

---

### 🛠️ 2. Step-by-Step Guide: Building the Standalone NCHL-IPS Middleware to Replace SOSYS

To remove SOSYS from the equation, you must build a standalone microservice (using Python/FastAPI, Node.js, or Java) that acts as the new bridge. 

#### Step 1: Reverse-Engineer the "SOSYS Handshake"
Before writing code, you need to know what SOSYS currently sends to OpenIMIS. 
1.  Check the OpenIMIS database (`tblPayment` and `tblContribution` tables) to see the data SOSYS leaves behind.
2.  Look at the OpenIMIS backend logs or network traffic to see the exact JSON payload SOSYS sends when a payment is successful. 
3.  *Typical SOSYS payload to OpenIMIS includes:* `insuree_chf_id` (Health ID), `policy_id`, `amount`, `receipt_number`, `payment_date`, and `payment_origin`.

#### Step 2: Develop the Standalone Middleware (The "New SOSYS")
Build a standalone API service. This service will have two sides:
*   **Side A (Faces NCHL-IPS):** Implements the NPI OAuth2 authentication, generates the SHA256withRSA digital signatures, and calls the `postnchlipsbatch` endpoint (as detailed in the previous NCHL-IPS guide).
*   **Side B (Faces OpenIMIS):** Exposes an API that OpenIMIS can call to initiate a batch, and exposes a Webhook to receive NCHL-IPS settlement statuses.

#### Step 3: Implement the OpenIMIS Integration Endpoints
Once NCHL-IPS confirms a deferred payment is settled (Status: `ACSC`), your standalone middleware must push this data into OpenIMIS. You will use the OpenIMIS REST API to do this:

1.  **Create the Payment Record:**
    *   **Endpoint:** `POST /api/payment/payments/`
    *   **Action:** Your middleware sends the batch details (Total amount, date, reference number) to OpenIMIS to create a "Payment" object.
2.  **Match Payment to Contributions (Crucial Step):**
    *   **Endpoint:** `POST /api/payment/match/` (or via GraphQL mutation `matchPayment`).
    *   **Action:** This tells OpenIMIS, "Take the money from this Payment and apply it to these specific Insurees' policies." You will map the NCHL-IPS `CreditorAccount` (the citizen's bank account) to the OpenIMIS `insuree_chf_id`.
3.  **Generate the Receipt:**
    *   Once matched, OpenIMIS automatically generates the official Health Insurance receipt. Your middleware can then fetch this receipt via the OpenIMIS API and send it to the user (via SMS/Email).

#### Step 4: Handle the "Deferred" Nature in OpenIMIS
Because NCHL-IPS is non-real-time, you cannot mark the policy as "Active" immediately.
1.  When OpenIMIS requests a payment via your middleware, your middleware returns a `PENDING` status to OpenIMIS.
2.  OpenIMIS should keep the policy in a "Grace Period" or "Pending Payment" state.
3.  Your middleware sets up a **cron job / polling mechanism** (or listens to the NPI Webhook) to check the NCHL-IPS batch status.
4.  Once NCHL-IPS returns `ACSC` (Accepted Settlement), your middleware triggers the OpenIMIS `match` API to activate the policy.

---

### 💡 3. Specific Resources for the Nepal Health Insurance Context

Since this is for the Nepal Health Insurance Board (HIB), you should leverage local context and existing community forks:

*   **OpenIMIS Nepal / HIB Implementations:**
    *   Search GitHub for `openimis nepal` or `openimis health insurance board`. Often, local implementers push their custom payment gateway modules to public repos. You might find an existing "ConnectIPS" or "Bank" module that you can fork and adapt for NCHL-IPS.
*   **Nepal Health Insurance Board (NHIB) Official Portal:**
    *   **URL:** [https://hib.gov.np](https://hib.gov.np)
    *   **Use:** While they don't have API docs, reviewing their public premium collection guidelines will help you ensure your standalone system complies with their specific business rules (e.g., family size premiums, government subsidies for certain demographics).
*   **NCHL ConnectIPS / NPI Developer Support:**
    *   Since you are bypassing SOSYS, you are now directly integrating with NCHL. You **must** contact NCHL directly ([https://nchl.com.np](https://nchl.com.np)) to get your specific **Client ID, Private Key (.pfx), and API credentials** for the NPI gateway. They will provide the specific UAT (Testing) environment details which are not public.

### Summary of the Strategy
Do not look for "SOSYS" documentation. Instead, look at the **`openimis-be-payment_py`** repository. Understand how OpenIMIS ingests money. Then, build a standalone Python/Node.js microservice that talks to **NCHL NPI** on one side, and calls the **OpenIMIS Payment REST API** on the other side. This completely decouples you from SOSYS.