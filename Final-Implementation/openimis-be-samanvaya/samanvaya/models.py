import uuid
from django.db import models
from django.conf import settings


class PaymentBatch(models.Model):
    """Groups approved claims together for bulk payment disbursement."""

    STATUS_CHOICES = [
        ("QUEUED", "Queued"),
        ("EXECUTING", "Executing"),
        ("DONE", "Done"),
        ("PARTIAL", "Partial"),
        ("FAILED", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    claim_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="QUEUED")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="samanvaya_batches"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Batch"
        verbose_name_plural = "Payment Batches"

    def __str__(self):
        return f"Batch {str(self.id)[:8]} — {self.status} ({self.claim_count} claims)"


class PaymentTransaction(models.Model):
    """
    The single source of truth for every payment attempt.
    Every cent is tracked with full audit trail.
    """

    STATUS_CHOICES = [
        ("QUEUED", "Queued"),
        ("PROCESSING", "Processing"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REVERSED", "Reversed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        PaymentBatch, on_delete=models.CASCADE, related_name="transactions"
    )
    # FK to OpenIMIS core Claim model
    claim = models.ForeignKey(
        "claim.Claim", on_delete=models.CASCADE, related_name="samanvaya_transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # State machine
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="QUEUED"
    )

    # Gateway specifics
    gateway_name = models.CharField(max_length=50, default="mock_bank")
    gateway_ref_id = models.CharField(
        max_length=200, unique=True, null=True, blank=True
    )
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)

    # Financial-grade audit fields
    raw_request_log = models.JSONField(null=True, blank=True)
    raw_response_log = models.JSONField(null=True, blank=True)
    webhook_received_at = models.DateTimeField(null=True, blank=True)

    # Retry logic
    retry_count = models.IntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"

    def __str__(self):
        return f"TX {str(self.id)[:8]} — {self.status} — NPR {self.amount}"


class GatewayConfig(models.Model):
    """Stores payment gateway credentials (encrypted at rest in production)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)  # mock_bank, esewa, connectips
    api_endpoint = models.URLField(blank=True, default="")
    api_key = models.TextField(blank=True, default="")
    secret_key = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Gateway Configuration"
        verbose_name_plural = "Gateway Configurations"

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"


class SOSYSLegacyLog(models.Model):
    """
    Temporary table for SOSYS migration reconciliation.
    Used during transition from SOSYS to Samanvaya.
    """

    MATCH_CHOICES = [
        ("MATCHED", "Matched"),
        ("UNMATCHED", "Unmatched"),
        ("FLAGGED", "Flagged"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_code = models.CharField(max_length=50)
    health_facility = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.CharField(max_length=50, blank=True, default="")
    sosys_status = models.CharField(max_length=50, blank=True, default="")
    match_status = models.CharField(
        max_length=20, choices=MATCH_CHOICES, default="UNMATCHED"
    )
    notes = models.TextField(blank=True, default="")
    resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "SOSYS Legacy Log"
        verbose_name_plural = "SOSYS Legacy Logs"

    def __str__(self):
        return f"{self.claim_code} — {self.match_status}"
