"""
Webhook views — Receives payment status callbacks from Mock Bank (or real bank).
This is a standard Django URL route, NOT a GraphQL mutation (webhooks come from outside).
"""
import json
import hmac
import hashlib
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import PaymentBatch, PaymentTransaction
from .tasks import process_gateway_webhook

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def gateway_webhook(request):
    """
    POST /webhook/gateway/ — Receives payment status callback.
    In production: verify HMAC-SHA256 signature before processing.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    gateway_ref_id = payload.get("gateway_ref_id")
    status = payload.get("status")

    if not gateway_ref_id or not status:
        return JsonResponse({"error": "Missing gateway_ref_id or status"}, status=400)

    # Process asynchronously via Celery (or synchronously for demo)
    try:
        process_gateway_webhook.delay(payload)
    except Exception:
        # Fallback to synchronous if Celery is not running
        with db_transaction.atomic():
            tx = PaymentTransaction.objects.select_for_update().filter(
                gateway_ref_id=gateway_ref_id
            ).first()

            if not tx or tx.status in ("SUCCESS", "FAILED", "REVERSED"):
                return JsonResponse({"ok": True, "note": "already_processed"})

            if status == "SUCCESS":
                tx.status = "SUCCESS"
            elif status == "FAILED":
                tx.status = "FAILED"
            tx.webhook_received_at = timezone.now()
            tx.raw_response_log = payload
            tx.save()

        # Update batch status
        try:
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
        except Exception:
            pass

    return JsonResponse({"ok": True})
