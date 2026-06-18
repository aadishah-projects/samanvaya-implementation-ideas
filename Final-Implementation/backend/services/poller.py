"""APScheduler polling safety net — catches dropped webhooks."""
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import SessionLocal
from models import PaymentTransaction, TransactionStatus
from services.gateway.mock_bank import MockBankGateway
from services.status import apply_gateway_status

scheduler = AsyncIOScheduler()

gateway = MockBankGateway()


def poll_pending_transactions():
    """Check stale PROCESSING transactions and verify with gateway."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
        stale = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.status == TransactionStatus.PROCESSING.value,
                PaymentTransaction.gateway_ref_id.isnot(None),
            )
            .all()
        )

        for tx in stale:
            if tx.created_at and tx.created_at.replace(tzinfo=timezone.utc) >= cutoff:
                continue  # too recent, skip

            result = gateway.verify_status(tx.gateway_ref_id)
            if result.status in {"SUCCESS", "FAILED", "PENDING", "PROCESSING"}:
                apply_gateway_status(db, tx, result.status, {
                    "source": "poller",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    **result.raw_response,
                })
            else:
                tx.raw_response_log = {
                    "source": "poller",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    **result.raw_response,
                }
                db.commit()

    except Exception:
        pass
    finally:
        db.close()


def start_poller():
    scheduler.add_job(
        poll_pending_transactions,
        "interval",
        minutes=1,
        id="poll_pending",
        replace_existing=True,
    )
    scheduler.start()


def stop_poller():
    scheduler.shutdown(wait=False)
