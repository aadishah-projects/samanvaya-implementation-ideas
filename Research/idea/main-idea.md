Here is a comprehensive, phased to-do list to build **Samanvaya** and win the hackathon. It is structured to take you from initial setup to a flawless end-to-end demo, keeping the "Correct Understanding" (OpenIMIS becoming fully self-sufficient) at the core.

### Phase 1: Foundation & OpenIMIS Module Setup 🏗️
*Goal: Get the basic OpenIMIS environment running and create the skeleton for the Samanvaya module.*

- [ ] **Set up OpenIMIS Dev Environment:** Spin up a local instance of OpenIMIS (Docker is usually best).
- [ ] **Design Database Schema:** Create tables for the new module:
  - `Payment_Batches` (links to approved claim bundles)
  - `Payment_Transactions` (individual payment records with status: Pending, Processing, Success, Failed, Partial)
  - `Gateway_Configs` (credentials/settings for eSewa, ConnectIPS, etc.)
- [ ] **Create Module Skeleton:** Generate the backend (Python/Django) and frontend (React) boilerplate for the Samanvaya module within the OpenIMIS architecture.
- [ ] **Define the "Handoff" Hook:** Write the logic that intercepts an "Approved Claim Bundle" in OpenIMIS and automatically pushes it into the Samanvaya queue.

### Phase 2: Core Payment Engine & Ledger (The "Meat") ⚙️
*Goal: Build the internal logic that handles the money movement and tracks every single cent.*

- [ ] **Build the Bulk Disbursement Engine:** 
  - Write the logic to take a batch of approved claims and split them into individual payment tasks.
  - Implement batching (e.g., processing 100 payments at a time) and basic retry logic for transient failures.
- [ ] **Implement the Transaction Ledger:**
  - Create the backend services to log every payment attempt.
  - Ensure state transitions are strictly logged (e.g., *Pending → Processing → Success*).
- [ ] **Handle Edge Cases:** Write logic to handle partial successes (e.g., a batch of 10 claims where 8 succeed and 2 fail due to invalid bank details).

### Phase 3: Payment Gateway Adapter (Connecting to Rails) 🏦
*Goal: Connect the engine to actual (or mock) payment rails. **Hackathon Tip:** Do not get stuck on real banking compliance. Use mock APIs or sandboxes.*

- [ ] **Select/Build Mock Gateway:** For the hackathon, build a "Mock Bank API" (a simple FastAPI/Node server) that simulates eSewa/ConnectIPS. It should randomly return Success, Fail, or Pending to test your system.
- [ ] **Build the Gateway Adapter Interface:** Create an abstract class in OpenIMIS so you can easily swap between "Mock Bank", "eSewa", and "ConnectIPS" in the future.
- [ ] **Implement Outbound API Calls:** Write the code that formats the OpenIMIS payment data into the required JSON/Payload format for the gateway and sends it.
- [ ] **Implement Webhooks/Callbacks:** Build the endpoint that receives the "Payment Successful/Failed" callback from the gateway and updates the Transaction Ledger accordingly.

### Phase 4: Reconciliation Engine (Track 1 Migration Bridge) 🌉
*Goal: Build the safety net for the transition from SOSYS to OpenIMIS.*

- [ ] **Create SOSYS Mock Data:** Generate a CSV/JSON file representing "Legacy SOSYS Logs" (include some intentional mismatches, double payments, and missing claims for the demo).
- [ ] **Build the Ingestion Parser:** Create a tool to upload and parse the SOSYS legacy file into a temporary database table.
- [ ] **Develop the Matching Algorithm:** Write the logic to compare the `SOSYS_Legacy` table against the `Samanvaya_Ledger` table using Claim IDs and Amounts.
- [ ] **Implement Anomaly Flagging:** Create the logic to flag discrepancies (e.g., "SOSYS says paid, OpenIMIS says failed" or "Amount mismatch").

### Phase 5: UI/UX & Financial Dashboard (The "Wow" Factor) 📊
*Goal: Make it look professional and easy to understand for the judges.*

- [ ] **Build the Transaction Ledger UI:** A clean, searchable, and filterable data table showing all payment attempts, their statuses, and timestamps.
- [ ] **Build the Financial Dashboard:** 
  - Add summary cards: *Total Disbursed Today, Success Rate %, Failed Payments.*
  - Add a simple chart (Pie chart for Success/Fail, Bar chart for daily volume).
- [ ] **Build the Reconciliation UI:** A specific view for the migration phase showing "Matched", "Unmatched", and "Flagged Anomalies" with a button to "Resolve/Override".

### Phase 6: Hackathon Demo & Polish 🏆
*Goal: Ensure the pitch and demo are flawless.*

- [ ] **Seed Demo Data:** Populate the database with realistic Nepali context data (e.g., "Bir Hospital", "Civil Hospital", realistic claim amounts in NPR).
- [ ] **Rehearse the End-to-End Flow:** 
  1. Show a claim being approved in standard OpenIMIS.
  2. Show it automatically appearing in the Samanvaya queue.
  3. Click "Execute Payment" and watch the status change from Pending to Success in real-time.
  4. Show the Financial Dashboard updating.
  5. *Bonus:* Upload the SOSYS legacy file and show the Reconciliation engine instantly catching a "double payment" anomaly.
- [ ] **Finalize the Pitch Deck:** Focus heavily on the **One-Line Pitch**: *"Samanvaya is a payment execution module that plugs into OpenIMIS, replacing SOSYS entirely..."*
- [ ] **Record a Backup Video:** Hackathon demos often fail due to live internet/API issues. Record a 3-minute screencast of the perfect flow just in case.

***

**💡 Pro-Tip for the Hackathon:** 
Judges love **scope management**. If you run out of time, **drop the Reconciliation Engine (Phase 4)** and focus 100% on making the **Core Payment Engine + Gateway + Dashboard (Phases 2, 3, 5)** look incredibly smooth. You can always *talk* about the Reconciliation Engine in your pitch as the "Track 1 migration strategy" without having to code the whole thing if time is tight!