"""Internal SOSYS audit ledger reflection."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import BatchStatus, MatchStatus, PaymentBatch, SOSYSLegacyLog, TransactionStatus


def reflect_completed_batch(db: Session, batch: PaymentBatch | None) -> int:
    """Mirror a completed payment batch into the SOSYS audit ledger once."""
    if not batch or batch.status != BatchStatus.DONE.value:
        return 0

    created = 0
    payment_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for tx in batch.transactions:
        if tx.status != TransactionStatus.SUCCESS.value:
            continue

        existing = (
            db.query(SOSYSLegacyLog)
            .filter(SOSYSLegacyLog.gateway_ref_id == tx.gateway_ref_id)
            .first()
        )
        if existing:
            continue

        claim = tx.claim
        db.add(SOSYSLegacyLog(
            claim_code=claim.claim_code if claim else tx.claim_id,
            health_facility=claim.health_facility if claim else batch.health_facility or "Unknown",
            amount=float(tx.amount),
            batch_id=batch.id,
            batch_code=batch.batch_code,
            gateway_ref_id=tx.gateway_ref_id,
            payment_date=payment_date,
            sosys_status="AUTO_REFLECTED",
            source="SAMANVAYA_AUTO",
            match_status=MatchStatus.UNMATCHED.value,
            notes="Auto-reflected after Mock Bank approved the completed batch.",
        ))
        created += 1

    if created:
        db.commit()
    return created
