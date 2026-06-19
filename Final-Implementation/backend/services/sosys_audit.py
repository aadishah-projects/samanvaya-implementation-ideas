"""Internal SOSYS audit ledger reflection."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import BatchStatus, MatchStatus, PaymentBatch, SOSYSLegacyLog, TransactionStatus


def reflect_completed_batch(db: Session, batch: PaymentBatch | None) -> int:
    """Deprecated: SOSYS is now a read-only API mirror of the OpenIMIS ledger."""
    return 0
