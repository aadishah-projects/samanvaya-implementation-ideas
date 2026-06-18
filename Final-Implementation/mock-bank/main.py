"""Mock Bank Server — simulates a payment gateway for demo purposes."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI(title="Mock Bank — Samanvaya Demo Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMANVAYA_WEBHOOK_URL = os.getenv("SAMANVAYA_WEBHOOK_URL", "http://localhost:8000/webhook/gateway")

# In-memory payout queue
pending_payouts: dict[str, dict] = {}


@app.post("/payout")
async def receive_payout(payload: dict):
    """Receive a payout request from Samanvaya."""
    ref_id = payload["ref_id"]
    existing = pending_payouts.get(ref_id)
    if existing:
        return {
            "gateway_ref_id": ref_id,
            "status": "INITIATED" if existing["status"] == "PENDING" else existing["status"],
            "idempotent_replay": True,
        }

    pending_payouts[ref_id] = {
        "status": "PENDING",
        "ref_id": ref_id,
        "amount": payload.get("amount", 0),
        "recipient": payload.get("recipient", "Unknown"),
        "last_event": "Received payout request from Samanvaya",
    }
    return {"gateway_ref_id": ref_id, "status": "INITIATED"}


@app.post("/reset")
async def reset_bank():
    """Clear the in-memory payout queue for a clean demo run."""
    pending_payouts.clear()
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


@app.get("/all")
async def get_all():
    """List all payouts (any status)."""
    return list(pending_payouts.values())


@app.post("/approve/{ref_id}")
async def approve_payout(ref_id: str):
    """Manually approve a payout — fires webhook to Samanvaya."""
    payout = pending_payouts.get(ref_id)
    if not payout:
        return {"error": "Payout not found."}
    if payout["status"] != "PENDING":
        return {"error": f"Payout already {payout['status']}."}

    payout["status"] = "SUCCESS"
    payout["last_event"] = "Approved and webhook sent"

    # Fire webhook
    try:
        async with httpx.AsyncClient() as client:
            await client.post(SAMANVAYA_WEBHOOK_URL, json={
                "gateway_ref_id": ref_id,
                "status": "SUCCESS",
            }, timeout=5.0)
    except Exception as e:
        payout["webhook_error"] = str(e)

    return {"ok": True, "status": "SUCCESS"}


@app.post("/settle-silent/{ref_id}")
async def settle_silent(ref_id: str):
    """Mark a payout successful without sending a webhook."""
    payout = pending_payouts.get(ref_id)
    if not payout:
        return {"error": "Payout not found."}
    if payout["status"] != "PENDING":
        return {"error": f"Payout already {payout['status']}."}

    payout["status"] = "SUCCESS"
    payout["last_event"] = "Bank settled successfully; webhook intentionally dropped"
    return {"ok": True, "status": "SUCCESS", "webhook_sent": False}


@app.post("/reject/{ref_id}")
async def reject_payout(ref_id: str):
    """Manually reject a payout — fires webhook to Samanvaya."""
    payout = pending_payouts.get(ref_id)
    if not payout:
        return {"error": "Payout not found."}
    if payout["status"] != "PENDING":
        return {"error": f"Payout already {payout['status']}."}

    payout["status"] = "FAILED"
    payout["last_event"] = "Rejected and webhook sent"

    try:
        async with httpx.AsyncClient() as client:
            await client.post(SAMANVAYA_WEBHOOK_URL, json={
                "gateway_ref_id": ref_id,
                "status": "FAILED",
            }, timeout=5.0)
    except Exception as e:
        payout["webhook_error"] = str(e)

    return {"ok": True, "status": "FAILED"}


@app.get("/ui", response_class=HTMLResponse)
async def control_panel():
    """Serve the Mock Bank control panel."""
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()
