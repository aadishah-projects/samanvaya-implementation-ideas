# Samanvaya Improvement Notes

This document captures recommended improvements after the Phase 2 implementation. The current build is functional for the demo flow, but the items below would make it safer, easier to maintain, and closer to production quality.

## Current Status

Phase 2 now supports strict amount-limited batching, batch details, startup demo cleanup, automatic SOSYS audit reflection, Mock Bank batch approval, Mock Bank ledger history, and reconciliation between the SOSYS audit ledger and the Mock Bank ledger.

The system is suitable for a controlled demo. The next improvements should focus on making demo-only behavior explicit, hardening data integrity, and improving test coverage.

## Priority Improvements

### 1. Separate Demo Reset From Production Startup

The backend currently clears payment transactions, batches, SOSYS audit rows, and resets claim statuses on startup. This is useful for demos, but dangerous for any persistent environment.

Recommended change:

- Add an environment variable such as `SAMANVAYA_DEMO_RESET_ON_STARTUP=true`.
- Run startup cleanup only when that flag is enabled.
- Default the flag to `false` for safer behavior.
- Keep `/api/demo/reset` as the explicit reset endpoint for demo sessions.

### 2. Add Real Database Migrations

The project currently uses `Base.metadata.create_all()` and a small SQLite schema sync helper. That works for local demos, but it becomes fragile as tables evolve.

Recommended change:

- Introduce Alembic migrations for backend schema changes.
- Add migrations for SOSYS ledger fields and future Mock Bank ledger tables.
- Keep `sync_demo_schema()` only as a fallback for demo databases, or remove it after migrations are stable.

### 3. Move Mock Bank Ledger Into a Clear Data Contract

The Mock Bank ledger is SQLite-backed and works for demo reconciliation. It should have a documented schema/API contract so reconciliation does not depend on loose JSON assumptions.

Recommended change:

- Define Pydantic response models for Mock Bank ledger endpoints.
- Add a versioned endpoint such as `/api/v1/ledger/payments`.
- Document required fields: `gateway_ref_id`, `batch_code`, `claim_code`, `amount`, `status`, `processed_at`, and `bank_reference_number`.

### 4. Improve Reconciliation Matching Rules

The reconciliation engine now compares SOSYS audit rows against Mock Bank ledger rows. It should be made more explicit and testable.

Recommended change:

- Prefer matching by `gateway_ref_id`.
- Fall back to `batch_code + claim_code`.
- Fall back to claim-only matching only when the claim has a single payment candidate.
- Flag ambiguous matches instead of silently matching the first row.
- Store the matched bank reference number in the SOSYS audit row or a separate reconciliation result table.

### 5. Add Automated Tests

The Phase 2 smoke checks passed, but the project should keep these behaviors protected with repeatable tests.

Recommended tests:

- Batch amount limit never exceeds the requested limit.
- A single claim above the limit is skipped and remains approved.
- Batch details endpoint returns claim and transaction metadata.
- Startup reset runs only when demo reset mode is enabled.
- SOSYS reflection is idempotent.
- Mock Bank batch approval writes one ledger row per completed batch.
- Reconciliation detects ghost payments, missing payments, amount mismatches, duplicates, and status mismatches.

### 6. Add Authentication and Role Controls

The demo app currently exposes sensitive actions directly, including batch execution, bank approval, ledger reset, and anomaly resolution.

Recommended change:

- Add authentication before any real deployment.
- Restrict high-impact actions by role.
- Suggested roles: `claims_reviewer`, `payment_operator`, `finance_auditor`, `admin`.
- Add an audit trail for who executed or approved a batch.

### 7. Strengthen Idempotency and Concurrency

Payment systems need strong protection against duplicate execution.

Recommended change:

- Add database-level uniqueness around claim payment completion where appropriate.
- Prevent executing the same batch twice after it enters a terminal state.
- Add transaction boundaries around batch execution.
- Consider row locking or optimistic version fields for concurrent batch approvals.

### 8. Improve Error Visibility

Gateway and reconciliation failures should be easier to understand in the UI.

Recommended change:

- Surface webhook errors in the transaction details drawer.
- Add a "last reconciliation run" timestamp.
- Add a visible bank-ledger connectivity status in the reconciliation page.
- Show skipped over-limit claims after automatic batch creation.

### 9. Add Export and Reporting

Auditors will likely need downloadable evidence.

Recommended change:

- Export batch details as CSV.
- Export SOSYS audit ledger.
- Export reconciliation anomalies.
- Include bank reference numbers and timestamps in exports.

### 10. Prepare For Real Bank Integration

The Mock Bank is useful for demonstration, but production bank integration will need stronger controls.

Recommended change:

- Add signed webhook verification.
- Store raw request and response payloads securely.
- Encrypt or mask sensitive account fields.
- Add retry backoff and dead-letter handling.
- Add gateway-specific reconciliation import or API polling.

## Suggested Next Phase

The best next phase is a stabilization phase:

1. Add the demo reset environment flag.
2. Add tests for batch limits, SOSYS reflection, Mock Bank ledger, and reconciliation.
3. Introduce Alembic migrations.
4. Tighten reconciliation matching and ambiguity handling.
5. Add UI visibility for skipped claims and bank connectivity.

These changes would keep the current demo experience intact while making the system much safer to evolve.
