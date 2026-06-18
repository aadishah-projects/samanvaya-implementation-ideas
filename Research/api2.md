Integrating the **NCHL-IPS (Interbank Payment System)** for non-real-time (deferred credit) transactions via the National Payment Interface (NPI) involves a specific workflow where debits are processed instantly, but credits are settled in batches.

Below is a comprehensive list of available resources and a step-by-step technical implementation guide.

### 🌐 Available Internet Resources

Here are the primary official and technical resources for integrating NCHL-IPS:

1.  **Official NPI API Specifications (Core Documentation):**
    *   **URL:** [https://doc.connectips.com/docs/NPI/NPI_Specification/api_specifications](https://doc.connectips.com/docs/NPI/NPI_Specification/api_specifications)
    *   **Details:** Contains Section 5.4.2, which details the `postnchlipsbatch` endpoint, request/response schemas, and digital signature generation [[5]].
2.  **Non-Real Time Remittance API Documentation:**
    *   **URL:** [https://doc.connectips.com/docs/Remit/non_real_time](https://doc.connectips.com/docs/Remit/non_real_time)
    *   **Details:** Specific guide for remittance companies using the `REMI` category purpose, including mandatory compliance fields [[38]].
3.  **NCHL-IPS Official Product Page:**
    *   **URL:** [https://nchl.com.np/interbank-payment-system-nchl-ips/](https://nchl.com.np/interbank-payment-system-nchl-ips/)
    *   **Details:** Overview of the system and the list of allowed transaction purposes (e.g., `CUST` for Customer Transfer, `SALA` for Salary, `TREA` for Treasury) [[3]].
4.  **NCHL-IPS Operating Rule Book (PDF):**
    *   **URL:** [https://nchl.com.np/wp-content/uploads/2023/02/nchl-ips-o-1884711099.pdf](https://nchl.com.np/wp-content/uploads/2023/02/nchl-ips-o-1884711099.pdf)
    *   **Details:** Critical for understanding business rules, transaction limits, settlement timings, and compliance requirements [[7]].
5.  **National Payments Interface (NPI) Overview:**
    *   **URL:** [https://nchl.com.np/national-payments-interface-npi/](https://nchl.com.np/national-payments-interface-npi/)
    *   **Details:** Explains how NPI acts as a single gateway to connect to both real-time (connectIPS) and deferred (NCHL-IPS) systems [[12]].

---

### 🛠️ Step-by-Step Implementation Guide

#### Step 1: Understand the Core Mechanism
The integration relies on the `postnchlipsbatch` endpoint [[5]].
*   **Instant Debit:** The system immediately debits the debtor's account (or the debtor bank's Nostro account) upon receiving the request.
*   **Deferred Credit:** Once the debit is successful, the credit transactions are queued and routed to the NCHL-IPS system for processing during specific settlement cycles.

#### Step 2: Authentication
Like all NPI integrations, you must use **OAuth 2.0** to obtain an Access Token.
*   Send a login request with your client credentials to receive an access token.
*   Include this token in the header of your API requests: `Authorization: Bearer [your_access_token]`.

#### Step 3: Construct the JSON Payload
The request body must follow the ISO 20022 structure and is divided into two main objects:

1.  **Batch Details (`nchlIpsBatchDetail`):**
    *   `batchId`: A unique string for reconciliation (max 20 chars).
    *   `batchAmount`: The total sum of all transactions in the batch.
    *   `categoryPurpose`: Must be a valid code like `CUST` (Customer Transfer) or `SALA` (Salary) [[3]].
    *   **Debtor Info:** `debtorAgent`, `debtorBranch`, `debtorAccount`, `debtorName`.

2.  **Transaction Details (`nchlIpsTransactionDetailList`):**
    *   An array containing individual transfer instructions.
    *   **Mandatory fields:** `instructionId` (unique ID), `endToEndId`, `amount`, `creditorAgent` (bank code), `creditorBranch`, `creditorAccount`, and `creditorName`.

*Note: For remittance, additional fields like `remitterName`, `countryOfOrigin`, and `remitCompanyName` are required [[38]].*

#### Step 4: Generate the Digital Signature (Token)
Every request must be cryptographically signed to ensure data integrity.
1.  **Create Token String:** Concatenate the following financial fields with commas:
    *   *Batch Part:* `<BatchId>,<DebtorAgent>,<DebtorBranch>,<DebtorAccount>,<BatchAmount>,<BatchCurrency>,<CategoryPurpose>`
    *   *Transaction Part (for each item):* `<InstructionId>,<CreditorAgent>,<CreditorBranch>,<CreditorAccount>,<TransactionAmount>`
    *   *User Part:* `<userId>`
2.  **Sign:** Generate a SHA256withRSA signature of this string using your private key (`.pfx` file).
3.  **Attach:** Base64 encode the signature and place it in the `token` field of your JSON payload.

#### Step 5: API Execution & Process Flow
Send a `POST` request to `/api/postnchlipsbatch` (or `/api/remit/postnchlipsbatch` for remittance) [[38]].
*   **Validation:** NPI performs technical checks.
*   **Debit:** The system instantly attempts to debit the debtor bank [[5]].
*   **Response:** If the debit is successful (status `000`), the API returns a `200 OK` response. The transaction is then queued for the NCHL-IPS batch process.

#### Step 6: Handle Statuses & Settlement
Because credits are deferred, the status lifecycle is distinct:
*   **`ENTR` (Entered):** The transaction has been received and debit was successful; it is pending posting to NCHL-IPS.
*   **Intermediate Statuses:** `GEN` (Generated), `SENT`, `ACTC` (Accepted Technical), `ACSP` (Accepted Settlement).
*   **Final Statuses:**
    *   **`ACSC` (Accepted Settlement):** The credit was successful and settled.
    *   **`RJCT` (Rejected):** The credit failed (e.g., invalid account) and funds may be reversed.

**Settlement Timing:**
Beneficiary accounts are credited only after the bank Nostro settlement is completed at Nepal Rastra Bank [[5]]. These settlements typically occur in cycles (e.g., 12:30 PM, 1:30 PM, 2:30 PM, and 4:00 PM) [[5]].

#### Step 7: Business Rules & Constraints
*   **Off-Us Only:** `postnchlipsbatch` is strictly for interbank (Off-Us) transactions.
*   **Batch Limit:** A single batch can contain up to **10,000 transactions** [[5]].
*   **Validation:** It is highly recommended to perform account validation (using the Account Enquiry API) before posting the batch to reduce rejection rates.
*   **Reporting:** Use the Transaction Reporting API to fetch the final status (`ACSC` or `RJCT`) of deferred transactions after the settlement cycle.