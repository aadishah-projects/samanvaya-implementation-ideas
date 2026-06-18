"""
Celery async tasks — Gateway API calls, retries, polling safety net.
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.db import transaction as db_transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def queue_claim_for_payment(self, claim_id):
    """
    Create PaymentTransaction for an approved claim.
    Triggered by Django Signal when claim is approved in OpenIMIS.
    """
    try:
        from .models import PaymentBatch, PaymentTransaction
        try:
            from claim.models import Claim
        except ImportError:
            from openimis_test.claim.models import Claim

        claim = Claim.objects.get(id=claim_id)

        # Get or create an active (QUEUED) batch
        batch = PaymentBatch.objects.filter(status="QUEUED").first()
        if not batch:
            batch = PaymentBatch.objects.create(
                total_amount=0, claim_count=0, status="QUEUED"
            )

        # Check if transaction already exists for this claim
        existing = PaymentTransaction.objects.filter(claim=claim).first()
        if existing:
            logger.info(f"Transaction already exists for claim {claim_id}")
            return

        tx = PaymentTransaction.objects.create(
            batch=batch,
            claim=claim,
            amount=claim.claimed or 0,
            status="QUEUED",
            gateway_name="mock_bank",
        )

        # Update batch totals
        batch.total_amount = sum(
            t.amount for t in PaymentBatch.objects.get(id=batch.id).transactions.all()
        )
        batch.claim_count = batch.transactions.count()
        batch.save()

        logger.info(f"Queued claim {claim_id} in batch {batch.id}")

    except Exception as e:
        logger.error(f"Failed to queue claim {claim_id}: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_payment_transaction(self, transaction_id):
    """Send payout to gateway with retry logic."""
    try:
        from .models import PaymentTransaction
        from .adapters import get_active_gateway

        with db_transaction.atomic():
            tx = PaymentTransaction.objects.select_for_update().get(id=transaction_id)
            if tx.status not in ("QUEUED", "PROCESSING"):
                return

            tx.status = "PROCESSING"
            tx.save()

            gateway = get_active_gateway()
            facility_name = "Unknown"
            if hasattr(tx.claim, 'health_facility') and tx.claim.health_facility:
                facility_name = str(tx.claim.health_facility)

            response = gateway.initiate_payout(
                ref_id=str(tx.idempotency_key),
                amount=float(tx.amount),
                recipient=facility_name,
            )

            tx.raw_request_log = response.request_payload
            tx.raw_response_log = response.raw_response
            tx.gateway_ref_id = response.gateway_ref or None

            if response.status == "SUCCESS":
                tx.status = "SUCCESS"
            elif response.status == "FAILED":
                tx.status = "FAILED"
                tx.failure_reason = response.error_msg or ""
            tx.save()

    except Exception as e:
        logger.error(f"Payment execution failed for {transaction_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def process_gateway_webhook(payload):
    """Handle async webhook from payment gateway."""
    from .models import PaymentBatch, PaymentTransaction

    gateway_ref_id = payload.get("gateway_ref_id")
    status = payload.get("status")

    with db_transaction.atomic():
        tx = PaymentTransaction.objects.select_for_update().filter(
            gateway_ref_id=gateway_ref_id
        ).first()

        if not tx or tx.status in ("SUCCESS", "FAILED", "REVERSED"):
            return  # Idempotency: skip if already terminal

        if status == "SUCCESS":
            tx.status = "SUCCESS"
        elif status == "FAILED":
            tx.status = "FAILED"
        tx.webhook_received_at = timezone.now()
        tx.raw_response_log = payload
        tx.save()

    # Update batch status
    batch = PaymentBatch.objects.get(id=tx.batch_id)
    statuses = set(batch.transactions.values_list("status", flat=True))
    if statuses == {"SUCCESS"}:
        batch.status = "DONE"
    elif "FAILED" in statuses and "SUCCESS" in statuses:
        batch.status = "PARTIAL"
    elif statuses == {"FAILED"}:
        batch.status = "FAILED"
    else:
        batch.status = "EXECUTING"
    batch.save()


@shared_task
def poll_pending_transactions():
    """
    Safety net: check stale PROCESSING transactions.
    Run every 5 min via Celery Beat.
    """
    from .models import PaymentTransaction
    from .adapters import get_active_gateway

    cutoff = timezone.now() - timedelta(minutes=10)
    stale = PaymentTransaction.objects.filter(
        status="PROCESSING",
        gateway_ref_id__isnull=False,
        created_at__lt=cutoff,
    )

    gateway = get_active_gateway()
    for tx in stale:
        try:
            result = gateway.verify_status(tx.gateway_ref_id)
            with db_transaction.atomic():
                tx = PaymentTransaction.objects.select_for_update().get(id=tx.id)
                if result.status == "SUCCESS":
                    tx.status = "SUCCESS"
                    tx.webhook_received_at = timezone.now()
                elif result.status == "FAILED":
                    tx.status = "FAILED"
                tx.raw_response_log = result.raw_response
                tx.save()
        except Exception as e:
            logger.error(f"Poll failed for tx {tx.id}: {e}")
