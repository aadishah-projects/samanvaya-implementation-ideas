"""Django Admin registration for Samanvaya models."""
from django.contrib import admin
from .models import PaymentBatch, PaymentTransaction, GatewayConfig, SOSYSLegacyLog


@admin.register(PaymentBatch)
class PaymentBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "total_amount", "claim_count", "created_at")
    list_filter = ("status",)
    readonly_fields = ("id", "created_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "claim", "amount", "status", "gateway_name", "retry_count", "created_at")
    list_filter = ("status", "gateway_name")
    readonly_fields = ("id", "idempotency_key", "created_at", "updated_at")


@admin.register(GatewayConfig)
class GatewayConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "api_endpoint")


@admin.register(SOSYSLegacyLog)
class SOSYSLegacyLogAdmin(admin.ModelAdmin):
    list_display = ("claim_code", "health_facility", "amount", "match_status", "resolved")
    list_filter = ("match_status", "resolved")
