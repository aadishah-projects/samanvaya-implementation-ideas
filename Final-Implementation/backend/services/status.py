"""Shared payment status helpers for ledger, claims, and batches."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    BatchStatus,
    ClaimStatus,
    PaymentBatch,
    PaymentTransaction,
    TransactionStatus,
)


TERMINAL_STATUSES = {
    TransactionStatus.SUCCESS.value,
    TransactionStatus.FAILED.value,
}


def apply_gateway_status(
    db: Session,
    tx: PaymentTransaction,
    gateway_status: str,
    response_log: dict | None = None,
    webhook_received: bool = False,
) -> PaymentTransaction:
    """Apply a gateway status to a transaction and sync related records."""
    normalized = (gateway_status or "").upper()

    if normalized == "SUCCESS":
        tx.status = TransactionStatus.SUCCESS.value
    elif normalized == "FAILED":
        tx.status = TransactionStatus.FAILED.value
    elif normalized in {"INITIATED", "PENDING", "PROCESSING"}:
        tx.status = TransactionStatus.PROCESSING.value

    if response_log is not None:
        tx.raw_response_log = response_log
    if webhook_received:
        tx.webhook_received_at = datetime.now(timezone.utc)

    _sync_claim_status(tx)
    db.commit()
    update_batch_status(db, tx.batch_id)
    db.refresh(tx)
    return tx


def update_batch_status(db: Session, batch_id: str) -> PaymentBatch | None:
    """Recompute a batch status from all child transactions."""
    batch = db.query(PaymentBatch).filter_by(id=batch_id).first()
    if not batch:
        return None

    txs = db.query(PaymentTransaction).filter_by(batch_id=batch_id).all()
    statuses = {tx.status for tx in txs}

    if not statuses:
        batch.status = BatchStatus.QUEUED.value
    elif statuses == {TransactionStatus.SUCCESS.value}:
        batch.status = BatchStatus.DONE.value
    elif statuses == {TransactionStatus.FAILED.value}:
        batch.status = BatchStatus.FAILED.value
    elif statuses.issubset({TransactionStatus.PENDING.value}):
        batch.status = BatchStatus.QUEUED.value
    elif statuses & {TransactionStatus.PROCESSING.value, TransactionStatus.PENDING.value}:
        batch.status = BatchStatus.EXECUTING.value
    elif TransactionStatus.FAILED.value in statuses and TransactionStatus.SUCCESS.value in statuses:
        batch.status = BatchStatus.PARTIAL.value
    else:
        batch.status = BatchStatus.PARTIAL.value

    db.commit()
    db.refresh(batch)
    return batch


def _sync_claim_status(tx: PaymentTransaction) -> None:
    """Keep the simulated OpenIMIS claim layer aligned with payment outcome."""
    if not tx.claim:
        return

    if tx.status == TransactionStatus.SUCCESS.value:
        tx.claim.status = ClaimStatus.PROCESSED.value
    elif tx.status in {
        TransactionStatus.PENDING.value,
        TransactionStatus.PROCESSING.value,
        TransactionStatus.FAILED.value,
    }:
        tx.claim.status = ClaimStatus.QUEUED.value
