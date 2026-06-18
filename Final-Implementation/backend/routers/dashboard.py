from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import PaymentTransaction, TransactionStatus, SOSYSLegacyLog, MatchStatus
from schemas import DashboardSummaryResponse, DailyVolume

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    txs = db.query(PaymentTransaction).all()
    total = len(txs)
    success = sum(1 for t in txs if t.status == TransactionStatus.SUCCESS.value)
    pending = sum(1 for t in txs if t.status in (
        TransactionStatus.PENDING.value, TransactionStatus.PROCESSING.value
    ))
    failed = sum(1 for t in txs if t.status == TransactionStatus.FAILED.value)
    disbursed = sum(t.amount for t in txs if t.status == TransactionStatus.SUCCESS.value)
    rate = round((success / total) * 100, 1) if total > 0 else 0.0

    return DashboardSummaryResponse(
        total_disbursed=disbursed,
        success_rate=rate,
        pending_count=pending,
        failed_count=failed,
        success_count=success,
        total_transactions=total,
    )


@router.get("/volume", response_model=list[DailyVolume])
def get_volume(db: Session = Depends(get_db)):
    """Daily payment volume for the last 7 days."""
    txs = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.status == TransactionStatus.SUCCESS.value)
        .all()
    )

    daily: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for tx in txs:
        if tx.created_at:
            day = tx.created_at.strftime("%Y-%m-%d")
            daily[day]["total"] += tx.amount
            daily[day]["count"] += 1

    result = []
    for date_str in sorted(daily.keys(), reverse=True)[:7]:
        result.append(DailyVolume(
            date=date_str,
            total_amount=daily[date_str]["total"],
            count=daily[date_str]["count"],
        ))
    return result


@router.get("/anomaly-count")
def get_anomaly_count(db: Session = Depends(get_db)):
    count = (
        db.query(SOSYSLegacyLog)
        .filter(
            SOSYSLegacyLog.match_status.in_([
                MatchStatus.FLAGGED.value,
                MatchStatus.UNMATCHED.value,
            ]),
            SOSYSLegacyLog.resolved == False,
        )
        .count()
    )
    return {"anomaly_count": count}
