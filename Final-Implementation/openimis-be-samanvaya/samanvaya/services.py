"""
Core Business Logic — Bulk Disbursement Service.
Ported from standalone FastAPI version to Django ORM.
"""
import uuid
import logging
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import PaymentBatch, PaymentTransaction
from .adapters import get_active_gateway

logger = logging.getLogger(__name__)


class BulkDisbursementService:
    def __init__(self, user=None):
        self.user = user
        self.gateway = get_active_gateway()

    def create_batch(self, claim_ids: list) -> PaymentBatch:
        """Create a PaymentBatch from approved OpenIMIS claim IDs."""
        try:
            from claim.models import Claim  # OpenIMIS core model
        except ImportError:
            from openimis_test.claim.models import Claim  # Test harness fallback

        claims = Claim.objects.filter(id__in=claim_ids, status=4)  # status 4 = APPROVED
        if not claims.exists():
            raise ValueError("No approved claims found for the given IDs.")

        total = sum(c.claimed or Decimal(0) for c in claims)
        # Only set created_by if user is authenticated
        user_kwarg = {}
        if self.user and hasattr(self.user, 'is_authenticated') and self.user.is_authenticated:
            user_kwarg["created_by"] = self.user
        batch = PaymentBatch.objects.create(
            total_amount=total,
            claim_count=claims.count(),
            status="QUEUED",
            **user_kwarg,
        )

        for claim in claims:
            PaymentTransaction.objects.create(
                batch=batch,
                claim=claim,
                amount=claim.claimed or Decimal(0),
                status="QUEUED",
                gateway_name="mock_bank",
            )

        return batch

    def execute_batch(self, batch_id: str) -> PaymentBatch:
        """Execute all QUEUED transactions through the gateway."""
        batch = PaymentBatch.objects.get(id=batch_id)
        txs = PaymentTransaction.objects.filter(batch=batch, status="QUEUED")

        if not txs.exists():
            raise ValueError("No queued transactions in this batch.")

        batch.status = "EXECUTING"
        batch.save()

        for tx in txs:
            with db_transaction.atomic():
                tx = PaymentTransaction.objects.select_for_update().get(id=tx.id)
                tx.status = "PROCESSING"
                tx.save()

                # Get health facility name from the claim
                facility_name = "Unknown"
                if hasattr(tx.claim, 'health_facility') and tx.claim.health_facility:
                    facility_name = str(tx.claim.health_facility)

                response = self.gateway.initiate_payout(
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
                # else stays PROCESSING — awaiting webhook

                tx.save()

        self._update_batch_status(batch_id)
        return PaymentBatch.objects.get(id=batch_id)

    def retry_transaction(self, transaction_id: str) -> PaymentTransaction:
        """Retry a FAILED transaction with new idempotency key."""
        with db_transaction.atomic():
            tx = PaymentTransaction.objects.select_for_update().get(id=transaction_id)
            if tx.status != "FAILED":
                raise ValueError("Only FAILED transactions can be retried.")

            tx.idempotency_key = uuid.uuid4()
            tx.status = "QUEUED"
            tx.retry_count += 1
            tx.gateway_ref_id = None
            tx.raw_request_log = None
            tx.raw_response_log = None
            tx.webhook_received_at = None
            tx.failure_reason = ""
            tx.save()

        return self.execute_single(tx.id)

    def execute_single(self, transaction_id: str) -> PaymentTransaction:
        """Execute a single transaction."""
        with db_transaction.atomic():
            tx = PaymentTransaction.objects.select_for_update().get(id=transaction_id)
            tx.status = "PROCESSING"
            tx.save()

            facility_name = "Unknown"
            if hasattr(tx.claim, 'health_facility') and tx.claim.health_facility:
                facility_name = str(tx.claim.health_facility)

            response = self.gateway.initiate_payout(
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

        self._update_batch_status(tx.batch_id)
        return PaymentTransaction.objects.get(id=transaction_id)

    def _update_batch_status(self, batch_id: str):
        """Recompute batch status from its transactions."""
        batch = PaymentBatch.objects.get(id=batch_id)
        statuses = set(
            PaymentTransaction.objects.filter(batch=batch)
            .values_list("status", flat=True)
        )

        if statuses == {"SUCCESS"}:
            batch.status = "DONE"
        elif "FAILED" in statuses and "SUCCESS" in statuses:
            batch.status = "PARTIAL"
        elif statuses == {"FAILED"}:
            batch.status = "FAILED"
        elif "PROCESSING" in statuses:
            batch.status = "EXECUTING"
        else:
            batch.status = "PARTIAL"
        batch.save()
