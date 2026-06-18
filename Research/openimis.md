Integrating the **NCHL-IPS (non-real-time deferred payment system)** into **OpenIMIS** (the Open Health Insurance Management Information System) is a highly specific and advanced integration. OpenIMIS is a modular, open-source platform primarily used for managing social health insurance, including premium collection (payments) and healthcare provider reimbursements (claims).

Because NCHL-IPS is a deferred (batch) system, integrating it into OpenIMIS requires handling asynchronous payment states (e.g., marking a premium as "Pending" until NCHL-IPS confirms settlement).

Here are all the essential internet resources for OpenIMIS, followed by a strategic guide on how to architect this specific integration.

---

### 🌐 1. Core OpenIMIS Internet Resources

To build any integration, you must understand the OpenIMIS architecture (Django/Python backend, React/Redux frontend) and its modular design.

*   **Official OpenIMIS Website:**
    *   **URL:** [https://openimis.org](https://openimis.org)
    *   **Use:** High-level overview, community news, and implementation case studies.
*   **Official OpenIMIS Documentation Portal:**
    *   **URL:** [https://docs.openimis.org](https://docs.openimis.org)
    *   **Use:** The master documentation hub. It covers system architecture, deployment (Docker/Kubernetes), and module-by-module functional guides.
*   **OpenIMIS GitHub Organization (Source Code):**
    *   **URL:** [https://github.com/openimis](https://github.com/openimis)
    *   **Key Repositories:**
        *   **`openimis-be_py`**: The backend (Django REST Framework). *You will write your NCHL-IPS integration logic here.*
        *   **`openimis-fe_js`**: The frontend (React). *You may need to add UI buttons here to trigger NCHL-IPS batch payments.*
        *   **`openimis-libs_py`**: Core libraries and shared utilities.
*   **OpenIMIS REST API Documentation:**
    *   **URL:** [https://docs.openimis.org/en/latest/cookbook/rest_api.html](https://docs.openimis.org/en/latest/cookbook/rest_api.html) (or via the Swagger endpoint at `/api/` in a running instance).
    *   **Use:** Understanding how OpenIMIS exposes its data (Insurees, Policies, Claims, Payments) via REST endpoints.

---

### 💰 2. OpenIMIS Payment & Financial Module Resources

To integrate NCHL-IPS, you must understand how OpenIMIS handles money. OpenIMIS generally deals with two types of financial flows:
1.  **Premium Collection (Inflow):** Citizens paying health insurance premiums.
2.  **Claim Payouts (Outflow):** The insurance fund paying hospitals/clinics for treated patients.

*   **Payment/Contribution Module (Backend):**
    *   **Repo:** Look inside `openimis-be_py` for the `payment` or `contribution` module.
    *   **Resource:** [OpenIMIS Payment Module Docs](https://docs.openimis.org/en/latest/modules/payment.html)
    *   **Use:** This module handles the receipt of funds. You will need to hook into this module to trigger the NCHL-IPS API when a batch of premium payments is initiated.
*   **Claim Module (Backend):**
    *   **Repo:** Look inside `openimis-be_py` for the `claim` module.
    *   **Use:** If you are using NCHL-IPS to *pay* hospitals, you will hook into the claim approval process to generate the NCHL-IPS batch file.
*   **OpenIMIS Data Model (ER Diagrams):**
    *   **URL:** [https://docs.openimis.org/en/latest/architecture/data_model.html](https://docs.openimis.org/en/latest/architecture/data_model.html)
    *   **Use:** Understanding the database schema (e.g., how `tblPayment`, `tblPolicy`, and `tblClaim` relate to each other).

---

### 🛠️ 3. Step-by-Step Integration Strategy (OpenIMIS + NCHL-IPS)

Since OpenIMIS does not have a native "NCHL-IPS" plugin, you must build a **Custom Integration Module**. Here is the exact architectural flow you need to implement:

#### Phase 1: Backend Integration (Python/Django)
1.  **Create a Custom Django App:** Inside the `openimis-be_py` directory, create a new module (e.g., `openimis-be-nchlips`).
2.  **Implement the NPI Client:** Write a Python service within this module that handles the NCHL-IPS authentication (OAuth2 token generation) and the SHA256withRSA digital signature generation (using the `cryptography` or `PyOpenSSL` Python libraries).
3.  **Map OpenIMIS Data to ISO 20022:**
    *   Map OpenIMIS `Payment` or `Claim` data to the NCHL-IPS JSON schema.
    *   *Example:* Map OpenIMIS `PaymentId` to NCHL `InstructionId`, and the total sum to `BatchAmount`.
4.  **Handle the "Deferred" Nature (Crucial):**
    *   Because NCHL-IPS is non-real-time, when OpenIMIS sends the batch to NPI, the money isn't settled instantly.
    *   You must create a custom status in OpenIMIS (e.g., `NCHL_PENDING`).
    *   The OpenIMIS payment/claim record should remain in this pending state until NCHL-IPS confirms settlement.

#### Phase 2: Webhook / Polling for Status Updates
Since NCHL-IPS credits are deferred (settled in cycles like 12:30 PM, 4:00 PM), OpenIMIS needs to know when the money actually arrives.
*   **Option A (Webhook - Recommended):** Create a new REST API endpoint in your custom OpenIMIS module (e.g., `/api/nchlips/webhook/`). Configure NCHL/NPI to send a POST request to this URL when a batch status changes to `ACSC` (Success) or `RJCT` (Rejected).
*   **Option B (Polling):** Use a background task (like Celery, which OpenIMIS uses) to periodically call the NCHL-IPS Transaction Reporting API to check the status of pending batches.
*   **Update OpenIMIS:** Once the webhook/polling receives `ACSC`, write a Django script to update the OpenIMIS `Payment` or `Claim` status to `Matched` or `Paid`, and generate the official OpenIMIS receipt.

#### Phase 3: Frontend Adjustments (React)
1.  Navigate to the `openimis-fe_js` repository.
2.  Locate the Payment or Claim UI components.
3.  Add a "Process via NCHL-IPS" button.
4.  When clicked, this button should call your custom backend endpoint, which then formats the selected OpenIMIS records into a batch and sends them to the NPI gateway.

---

### 🤝 4. Community and Support Resources

If you get stuck on OpenIMIS-specific architecture (like how to properly override a Django view or how to register a custom React component), use these channels:

*   **OpenIMIS Community Forum:**
    *   **URL:** [https://community.openimis.org](https://community.openimis.org)
    *   **Use:** The best place to ask architectural questions to core developers.
*   **OpenIMIS Jira (Issue Tracker):**
    *   **URL:** [https://openimis.atlassian.net](https://openimis.atlassian.net)
    *   **Use:** To report bugs or request features in the core OpenIMIS modules.
*   **OpenIMIS Slack/Discord:**
    *   Check the official website for current invite links to their developer chat channels, which are highly active for backend Python/Django questions.

### 💡 Pro-Tip for the Nepali Context
If you are implementing this for a specific Nepali entity (like the Health Insurance Board), ensure you check if they are using the standard global OpenIMIS release or a **localized fork**. Many countries maintain their own GitHub forks of OpenIMIS with local tax, language, and payment integrations already partially built. Search GitHub for `"openimis nepal"` or `"openimis health insurance board"` to see if a localized codebase already exists that you can build upon.