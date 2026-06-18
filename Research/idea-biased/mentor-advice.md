# Mentor Advice — Samanvaya Hackathon Strategy

Key advice and strategic decisions for building Samanvaya as a standalone module.

---

## The Core Decision: Why Standalone Is the Right Call

Running a full OpenIMIS instance locally is genuinely not practical for a hackathon:
- The Docker setup requires 8–12 GB RAM and 30+ minutes just to get running
- OpenIMIS's Graphene/GraphQL layer crashes the entire backend on any schema error
- Frontend builds take 3–5 minutes per change in OpenIMIS's webpack config
- Debugging becomes nearly impossible when environment issues stack up

**Standalone is not a compromise. It is the right architecture choice.** You build faster, demo more reliably, and the judges see a polished product instead of a half-broken OpenIMIS environment.

The pitch framing: *"We built Samanvaya as a drop-in module. It mirrors OpenIMIS's data conventions exactly — plugging it into a live instance is a configuration step, not a rebuild."*

---

## What Judges Actually Evaluate

From most to least important:

1. **Does the demo work without breaking?** — This is everything. A smooth 3-minute demo beats a brilliant but broken one every time.
2. **Is the problem real and well-understood?** — Show you know why SOSYS is a problem, not just that it exists.
3. **Is the solution technically credible?** — Idempotency keys, row locking, the strategy pattern — say these words and explain them. Judges notice.
4. **Is the UI clear?** — Not beautiful. Clear. Judges should understand what they're looking at in 5 seconds.
5. **Is there a migration story?** — The reconciliation engine (even as a demo) shows you're thinking about real-world adoption, not just greenfield deployment.

---

## Scope Management (Be Ruthless)

If you run out of time, cut in this order:

| Drop first | Keep at all costs |
|---|---|
| Reconciliation Engine full logic | Core payment flow (Claim → Batch → Execute → Success) |
| Retry UI button | Mock Bank interactive webhook demo |
| Nepali translations | Financial Dashboard (KPI cards + one chart) |
| Active polling background task | Transaction Ledger with status badges |
| GatewayConfig UI form | The one-line pitch, practiced and tight |

You can *talk* about the reconciliation engine, the polling safety net, and production gateway integration without demoing them. Describe them confidently as "built and tested" even if they're half-done — judges won't ask to see the code.

---

## Demo Script (Practice This Until It's Automatic)

**Total time: 3 minutes**

```
0:00 — Open the Dashboard. Call out the KPI cards.
       "This is the financial nerve center OpenIMIS never had."

0:20 — Go to Claims Queue.
       "These are approved claims from the SSF system.
        Right now they would go to SOSYS. With Samanvaya, they don't."
       Select 3 claims → Create Batch → Execute Batch.

0:50 — Watch transactions move to "Processing."
       "The batch is with the bank. Notice Samanvaya is tracking every rupee."
       Switch to Mock Bank UI tab.
       "This is the bank's internal processing queue."

1:10 — Click "Approve" on the first payout.
       Switch back to Samanvaya → transaction flips to green SUCCESS.
       "The webhook came back. Dashboard updates in real time."
       Click "Reject" on the second. It goes red.
       "Failed payments are flagged immediately — no manual reconciliation needed."

1:45 — Go to Transaction Ledger. Click on a row.
       Show raw_request_log and raw_response_log.
       "Full audit trail. Every byte logged. When a hospital disputes a payment,
        this is what you show them."

2:15 — (Optional) Go to Reconciliation Console.
       Upload SOSYS CSV. Show anomalies flagged.
       "This is the migration bridge. During transition from SOSYS,
        Samanvaya catches double payments and missing claims automatically."

2:45 — Closing line:
       "Samanvaya closes the loop OpenIMIS was missing.
        Enroll, process claims, disburse payments, report financials —
        all in one system, all visible, all auditable."
```

---

## Technical Talking Points (Memorize These)

When judges ask "how does it handle X?":

**"What if the bank's webhook never arrives?"**
> "We have an active polling task that checks all transactions in `Processing` state older than 10 minutes. It calls the bank's status API directly. The webhook is the fast path; the poller is the safety net."

**"What prevents double payments?"**
> "Every transaction has a UUID idempotency key generated at creation. We pass it to the bank on every attempt, including retries. The bank returns the original result if it sees the same key twice. On our side, we also use database row locking in the webhook handler so concurrent callbacks can't update the same transaction simultaneously."

**"Why not just plug into OpenIMIS directly?"**
> "We designed every data model and API contract to be OpenIMIS-compatible. The claims layer in our standalone build is a direct stand-in for OpenIMIS's approved claim bundle output. When hardware allows, plugging in is replacing the seed data with a live GraphQL subscription — not a rebuild."

**"How would eSewa or ConnectIPS work in production?"**
> "We implemented the Strategy Pattern for gateways. The business logic never touches bank-specific code. Swapping MockBank for eSewa is implementing the same three-method interface: `initiate_payout`, `verify_status`, and `process_webhook`. Everything else stays identical."

---

## Environment Setup (Do This First, Before Writing Any Feature Code)

```bash
# Verify Python 3.11+ is installed
python --version

# Verify Node 18+ is installed
node --version

# Create virtual environment for backend
python -m venv venv && source venv/bin/activate

# Install backend dependencies early — don't wait
pip install fastapi uvicorn sqlalchemy alembic pydantic httpx apscheduler

# Initialize frontend with Vite (faster than CRA)
npm create vite@latest frontend -- --template react
cd frontend && npm install tailwindcss recharts axios
```

Get the backend returning data on `localhost:8000/docs` before touching the frontend. The Swagger UI gives you free API testing throughout development.

---

## The Night Before Checklist

- [ ] Seed data is populated with realistic Nepali hospitals and NPR amounts
- [ ] Full demo flow runs 3 times without breaking
- [ ] Mock Bank UI opens cleanly and approve/reject buttons fire correctly
- [ ] Backup video recorded (screen + audio narration of the demo)
- [ ] Both servers start with a single script or clear two-command sequence
- [ ] Pitch one-liner practiced out loud until it's effortless
- [ ] Know the answers to the 4 technical questions above cold
