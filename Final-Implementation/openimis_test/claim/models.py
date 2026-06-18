"""
Mock OpenIMIS Claim model — simulates the core claim.Claim model.
This allows Samanvaya to run in a test harness without the full OpenIMIS stack.
"""
import uuid
from django.db import models


class HealthFacility(models.Model):
    """Mock OpenIMIS HealthFacility."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    district = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        app_label = "claim"

    def __str__(self):
        return self.name


class Claim(models.Model):
    """
    Mock OpenIMIS Claim model.
    In real OpenIMIS: claim.models.Claim with status codes 1-16.
    Status 4 = CHECKED/APPROVED (the hook point for Samanvaya).
    """

    STATUS_REJECTED = 1
    STATUS_ENTERED = 2
    STATUS_CHECKED = 4    # APPROVED — this is the Samanvaya hook
    STATUS_PROCESSED = 8
    STATUS_VALUATED = 16

    STATUS_CHOICES = [
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ENTERED, "Entered"),
        (STATUS_CHECKED, "Checked/Approved"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_VALUATED, "Valuated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50, unique=True)  # e.g. "CLM-2024-001"
    health_facility = models.ForeignKey(
        HealthFacility, on_delete=models.CASCADE, null=True, blank=True
    )
    insuree_name = models.CharField(max_length=200, blank=True, default="")
    claimed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_ENTERED)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "claim"

    def __str__(self):
        return f"{self.code} — {self.get_status_display()}"
