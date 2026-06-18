from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import PaymentTransaction
from schemas import WebhookPayload
from services.status import TERMINAL_STATUSES, apply_gateway_status

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


@router.post("/gateway")
def receive_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    """Receive payment status callback from Mock Bank (or real bank)."""
    tx = (
        db.query(PaymentTransaction)
        .filter_by(gateway_ref_id=payload.gateway_ref_id)
        .with_for_update()
        .first()
    )

    if not tx:
        return {"ok": True, "note": "transaction_not_found"}

    # Idempotency: skip if already in terminal state
    if tx.status in TERMINAL_STATUSES:
        return {"ok": True, "note": "already_processed"}

    if payload.status not in {"SUCCESS", "FAILED"}:
        return {"ok": True, "note": "unknown_status"}

    apply_gateway_status(db, tx, payload.status, {
        "source": "webhook",
        "gateway_ref_id": payload.gateway_ref_id,
        "status": payload.status,
        "message": payload.message,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }, webhook_received=True)

    return {"ok": True}
