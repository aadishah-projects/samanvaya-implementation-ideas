"""Mock Bank Server - simulates a settlement ledger for demo purposes."""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI(title="Mock Bank - Samanvaya Demo Ledger")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMANVAYA_WEBHOOK_URL = os.getenv("SAMANVAYA_WEBHOOK_URL", "http://localhost:8000/webhook/gateway")
BANK_DB_PATH = os.getenv("MOCK_BANK_DB", os.path.join(os.path.dirname(__file__), "mock_bank.db"))

# In-memory payout records for the active demo session.
pending_payouts: dict[str, dict] = {}


@app.on_event("startup")
def startup():
    init_bank_db()


def init_bank_db():
    with sqlite3.connect(BANK_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bank_batch_ledger (
                id TEXT PRIMARY KEY,
                ledger_key TEXT UNIQUE NOT NULL,
                batch_id TEXT,
                batch_code TEXT,
                status TEXT NOT NULL,
                total_amount REAL NOT NULL,
                transaction_count INTEGER NOT NULL,
                reference_number TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                payouts_json TEXT NOT NULL
            )
            """
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def batch_key(payout: dict) -> str:
    metadata = payout.get("metadata") or {}
    return metadata.get("batch_id") or payout["ref_id"]


def batch_code(payout: dict) -> str:
    metadata = payout.get("metadata") or {}
    return metadata.get("batch_code") or batch_key(payout)


def payouts_for_batch(key: str) -> list[dict]:
    return [payout for payout in pending_payouts.values() if batch_key(payout) == key]


def summarize_batch(items: list[dict]) -> dict:
    if not items:
        return {}
    statuses = {item["status"] for item in items}
    if statuses == {"SUCCESS"}:
        status = "SUCCESS"
    elif statuses == {"FAILED"}:
        status = "FAILED"
    elif "PENDING" in statuses:
        status = "PENDING"
    else:
        status = "PARTIAL"

    first = items[0]
    key = batch_key(first)
    return {
        "batch_id": (first.get("metadata") or {}).get("batch_id"),
        "batch_code": batch_code(first),
        "ledger_key": key,
        "status": status,
        "total_amount": sum(float(item.get("amount") or 0) for item in items),
        "transaction_count": len(items),
        "payouts": items,
    }


def grouped_batches(only_pending: bool = False) -> list[dict]:
    keys = sorted({batch_key(payout) for payout in pending_payouts.values()})
    groups = []
    for key in keys:
        summary = summarize_batch(payouts_for_batch(key))
        if only_pending and summary.get("status") != "PENDING":
            continue
        groups.append(summary)
    return groups


async def send_webhook(ref_id: str, status: str):
    async with httpx.AsyncClient() as client:
        await client.post(SAMANVAYA_WEBHOOK_URL, json={
            "gateway_ref_id": ref_id,
            "status": status,
        }, timeout=5.0)


async def process_payout(ref_id: str, status: str, webhook: bool = True) -> dict:
    payout = pending_payouts.get(ref_id)
    if not payout:
        return {"error": "Payout not found."}
    if payout["status"] != "PENDING":
        return {"error": f"Payout already {payout['status']}."}

    payout["status"] = status
    payout["last_event"] = f"{'Recorded' if status == 'SUCCESS' else 'Rejected'} by Mock Bank ledger"
    payout["processed_at"] = now_iso()

    if webhook:
        try:
            await send_webhook(ref_id, status)
            payout["last_event"] += " and webhook sent"
        except Exception as e:
            payout["webhook_error"] = str(e)

    record_if_batch_complete(batch_key(payout))
    return {"ok": True, "status": status}


def record_if_batch_complete(key: str) -> dict | None:
    items = payouts_for_batch(key)
    if not items or any(item["status"] == "PENDING" for item in items):
        return None

    summary = summarize_batch(items)
    reference_number = f"MBK-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    processed_at = now_iso()
    payouts_json = json.dumps(items)

    with sqlite3.connect(BANK_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO bank_batch_ledger (
                id, ledger_key, batch_id, batch_code, status, total_amount,
                transaction_count, reference_number, processed_at, payouts_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ledger_key) DO UPDATE SET
                status=excluded.status,
                total_amount=excluded.total_amount,
                transaction_count=excluded.transaction_count,
                reference_number=excluded.reference_number,
                processed_at=excluded.processed_at,
                payouts_json=excluded.payouts_json
            """,
            (
                str(uuid.uuid4()),
                key,
                summary.get("batch_id"),
                summary.get("batch_code"),
                summary["status"],
                summary["total_amount"],
                summary["transaction_count"],
                reference_number,
                processed_at,
                payouts_json,
            ),
        )

    return get_ledger_record(key)


def get_ledger_record(key: str) -> dict | None:
    with sqlite3.connect(BANK_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM bank_batch_ledger WHERE ledger_key = ?", (key,)).fetchone()
    return row_to_ledger(row) if row else None


def row_to_ledger(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["payouts"] = json.loads(data.pop("payouts_json") or "[]")
    return data


@app.post("/payout")
async def receive_payout(payload: dict):
    """Receive an OpenIMIS payment instruction and record settlement immediately."""
    ref_id = payload["ref_id"]
    existing = pending_payouts.get(ref_id)
    if existing:
        return {
            "gateway_ref_id": ref_id,
            "status": existing["status"],
            "idempotent_replay": True,
        }

    pending_payouts[ref_id] = {
        "status": "SUCCESS",
        "ref_id": ref_id,
        "amount": payload.get("amount", 0),
        "recipient": payload.get("recipient", "Unknown"),
        "metadata": payload.get("metadata") or {},
        "last_event": "Recorded payment instruction from OpenIMIS",
        "created_at": now_iso(),
        "processed_at": now_iso(),
    }
    record_if_batch_complete(batch_key(pending_payouts[ref_id]))
    return {"gateway_ref_id": ref_id, "status": "SUCCESS"}


@app.post("/ghost-payment")
async def create_ghost_payment(payload: dict):
    """Create a bank-ledger-only row that has no OpenIMIS transaction."""
    ref_id = f"GHOST-{uuid.uuid4().hex[:10].upper()}"
    batch_id = f"GHOST-BATCH-{uuid.uuid4().hex[:8].upper()}"
    amount = float(payload.get("amount") or 1000)
    pending_payouts[ref_id] = {
        "status": "SUCCESS",
        "ref_id": ref_id,
        "amount": amount,
        "recipient": payload.get("health_facility", "Unknown"),
        "metadata": {
            "batch_id": batch_id,
            "batch_code": payload.get("batch_code") or batch_id,
            "claim_id": None,
            "claim_code": f"BANK-GHOST-{uuid.uuid4().hex[:6].upper()}",
            "health_facility": payload.get("health_facility", "Unknown"),
            "simulation": "GHOST_PAYMENT",
        },
        "last_event": "Injected bank-ledger-only ghost payment",
        "created_at": now_iso(),
        "processed_at": now_iso(),
    }
    record = record_if_batch_complete(batch_id)
    return {"ok": True, "gateway_ref_id": ref_id, "record": record}


@app.post("/reset")
async def reset_bank():
    """Clear the active queue and persisted bank ledger for a clean demo run."""
    pending_payouts.clear()
    with sqlite3.connect(BANK_DB_PATH) as conn:
        conn.execute("DELETE FROM bank_batch_ledger")
    return {"ok": True, "cleared": True}


@app.get("/status/{ref_id}")
async def get_status(ref_id: str):
    """Check the status of a payout."""
    payout = pending_payouts.get(ref_id)
    if not payout:
        return {"status": "NOT_FOUND", "ref_id": ref_id}
    return {"status": payout["status"], "ref_id": ref_id, "amount": payout["amount"]}


@app.get("/pending")
async def get_pending():
    """List all pending payouts."""
    return [v for v in pending_payouts.values() if v["status"] == "PENDING"]


@app.get("/batches")
async def get_batches():
    """List active Mock Bank payout batches."""
    return grouped_batches()


@app.get("/pending-batches")
async def get_pending_batches():
    """List batches that still require approval or rejection."""
    return grouped_batches(only_pending=True)


@app.get("/all")
async def get_all():
    """List all payouts (any status)."""
    return list(pending_payouts.values())


@app.get("/ledger")
async def get_bank_ledger():
    """Return persisted processed batch history."""
    with sqlite3.connect(BANK_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bank_batch_ledger ORDER BY processed_at DESC").fetchall()
    return [row_to_ledger(row) for row in rows]


@app.get("/ledger/payments")
async def get_bank_payment_ledger():
    """Return processed bank records flattened to one row per payout."""
    records = await get_bank_ledger()
    rows = []
    for record in records:
        for payout in record["payouts"]:
            metadata = payout.get("metadata") or {}
            rows.append({
                "batch_id": record["batch_id"],
                "batch_code": record["batch_code"],
                "bank_batch_status": record["status"],
                "bank_reference_number": record["reference_number"],
                "processed_at": record["processed_at"],
                "gateway_ref_id": payout.get("ref_id"),
                "claim_id": metadata.get("claim_id"),
                "claim_code": metadata.get("claim_code") or payout.get("ref_id"),
                "health_facility": metadata.get("health_facility") or payout.get("recipient"),
                "amount": float(payout.get("amount") or 0),
                "status": payout.get("status"),
            })
    return rows


@app.post("/approve/{ref_id}")
async def approve_payout(ref_id: str):
    """Manually approve one payout and fire a webhook to Samanvaya."""
    return await process_payout(ref_id, "SUCCESS")


@app.post("/settle-silent/{ref_id}")
async def settle_silent(ref_id: str):
    """Mark one payout successful without sending a webhook."""
    return await process_payout(ref_id, "SUCCESS", webhook=False)


@app.post("/reject/{ref_id}")
async def reject_payout(ref_id: str):
    """Manually reject one payout and fire a webhook to Samanvaya."""
    return await process_payout(ref_id, "FAILED")


@app.post("/batches/{batch_id}/approve")
async def approve_batch(batch_id: str):
    """Approve every pending payout in a batch."""
    items = [item for item in payouts_for_batch(batch_id) if item["status"] == "PENDING"]
    if not items:
        return {"error": "No pending payouts found for this batch."}
    for item in items:
        await process_payout(item["ref_id"], "SUCCESS")
    return {"ok": True, "status": "SUCCESS", "batch": record_if_batch_complete(batch_id)}


@app.post("/batches/{batch_id}/reject")
async def reject_batch(batch_id: str):
    """Reject every pending payout in a batch."""
    items = [item for item in payouts_for_batch(batch_id) if item["status"] == "PENDING"]
    if not items:
        return {"error": "No pending payouts found for this batch."}
    for item in items:
        await process_payout(item["ref_id"], "FAILED")
    return {"ok": True, "status": "FAILED", "batch": record_if_batch_complete(batch_id)}


@app.get("/ui", response_class=HTMLResponse)
async def control_panel():
    """Serve the Mock Bank control panel."""
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()
