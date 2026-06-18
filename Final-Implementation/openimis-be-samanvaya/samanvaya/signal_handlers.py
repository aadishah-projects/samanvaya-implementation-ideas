"""
Django Signal Handlers — The core integration point.
When OpenIMIS approves a claim, Samanvaya automatically picks it up.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="claim.Claim")
def trigger_samanvaya_queue(sender, instance, **kwargs):
    """
    When a claim is approved in OpenIMIS, auto-queue it for payment.
    This is the hook that replaces SOSYS.
    """
    # Check if claim status just changed to APPROVED (status code 4 in OpenIMIS)
    # OpenIMIS claim statuses: 1=REJECTED, 2=ENTERED, 4=CHECKED, 8=PROCESSED, 16=VALUATED
    # The exact approved status depends on the OpenIMIS configuration
    if hasattr(instance, 'status') and instance.status == 4:  # CHECKED/APPROVED
        try:
            from .tasks import queue_claim_for_payment
            queue_claim_for_payment.delay(instance.id)
            logger.info(
                f"Samanvaya: Claim {instance.id} approved — queued for payment"
            )
        except Exception as e:
            logger.error(f"Samanvaya: Failed to queue claim {instance.id}: {e}")
