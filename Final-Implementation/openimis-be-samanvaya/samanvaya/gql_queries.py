"""
GraphQL Queries — Fetch ledger, dashboard stats, reconciliation results.
"""
import graphene
from graphene_django import DjangoObjectType
from django.db.models import Sum, Count, Q

from .models import PaymentBatch, PaymentTransaction, GatewayConfig, SOSYSLegacyLog


class PaymentBatchGQLType(DjangoObjectType):
    class Meta:
        model = PaymentBatch
        fields = "__all__"


class PaymentTransactionGQLType(DjangoObjectType):
    health_facility = graphene.String()
    claim_code = graphene.String()

    class Meta:
        model = PaymentTransaction
        fields = "__all__"

    def resolve_health_facility(self, info):
        if self.claim and hasattr(self.claim, 'health_facility'):
            return str(self.claim.health_facility) if self.claim.health_facility else None
        return None

    def resolve_claim_code(self, info):
        if self.claim and hasattr(self.claim, 'code'):
            return self.claim.code
        return None


class GatewayConfigGQLType(DjangoObjectType):
    class Meta:
        model = GatewayConfig
        fields = ("id", "name", "api_endpoint", "is_active")


class SOSYSLegacyLogGQLType(DjangoObjectType):
    class Meta:
        model = SOSYSLegacyLog
        fields = "__all__"


class DashboardSummaryGQLType(graphene.ObjectType):
    total_disbursed = graphene.Float()
    success_rate = graphene.Float()
    pending_count = graphene.Int()
    failed_count = graphene.Int()
    success_count = graphene.Int()
    total_transactions = graphene.Int()


class DailyVolumeGQLType(graphene.ObjectType):
    date = graphene.String()
    total_amount = graphene.Float()
    count = graphene.Int()


class Query(graphene.ObjectType):
    samanvaya_batches = graphene.List(PaymentBatchGQLType)
    samanvaya_batch = graphene.Field(PaymentBatchGQLType, id=graphene.UUID(required=True))
    samanvaya_transactions = graphene.List(
        PaymentTransactionGQLType,
        status=graphene.String(),
        health_facility=graphene.String(),
    )
    samanvaya_transaction_detail = graphene.Field(
        PaymentTransactionGQLType, id=graphene.UUID(required=True)
    )
    samanvaya_dashboard_summary = graphene.Field(DashboardSummaryGQLType)
    samanvaya_dashboard_volume = graphene.List(DailyVolumeGQLType)
    samanvaya_reconciliation_results = graphene.List(
        SOSYSLegacyLogGQLType, match_status=graphene.String()
    )
    samanvaya_reconciliation_summary = graphene.Field(graphene.JSONString)
    samanvaya_anomaly_count = graphene.Int()
    samanvaya_gateway_configs = graphene.List(GatewayConfigGQLType)

    def resolve_samanvaya_batches(self, info):
        return PaymentBatch.objects.all()

    def resolve_samanvaya_batch(self, info, id):
        return PaymentBatch.objects.get(id=id)

    def resolve_samanvaya_transactions(self, info, status=None, health_facility=None):
        qs = PaymentTransaction.objects.all()
        if status:
            qs = qs.filter(status=status.upper())
        return qs

    def resolve_samanvaya_transaction_detail(self, info, id):
        return PaymentTransaction.objects.get(id=id)

    def resolve_samanvaya_dashboard_summary(self, info):
        txs = PaymentTransaction.objects.all()
        total = txs.count()
        success = txs.filter(status="SUCCESS").count()
        pending = txs.filter(status__in=["QUEUED", "PROCESSING"]).count()
        failed = txs.filter(status="FAILED").count()
        disbursed = txs.filter(status="SUCCESS").aggregate(
            total=Sum("amount")
        )["total"] or 0
        rate = round((success / total) * 100, 1) if total > 0 else 0.0

        return DashboardSummaryGQLType(
            total_disbursed=float(disbursed),
            success_rate=rate,
            pending_count=pending,
            failed_count=failed,
            success_count=success,
            total_transactions=total,
        )

    def resolve_samanvaya_dashboard_volume(self, info):
        from django.db.models.functions import TruncDate
        txs = (
            PaymentTransaction.objects.filter(status="SUCCESS")
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(total_amount=Sum("amount"), count=Count("id"))
            .order_by("-date")[:7]
        )
        return [
            DailyVolumeGQLType(
                date=str(v["date"]),
                total_amount=float(v["total_amount"]),
                count=v["count"],
            )
            for v in txs
        ]

    def resolve_samanvaya_reconciliation_results(self, info, match_status=None):
        qs = SOSYSLegacyLog.objects.all()
        if match_status:
            qs = qs.filter(match_status=match_status.upper())
        return qs

    def resolve_samanvaya_reconciliation_summary(self, info):
        return {
            "matched": SOSYSLegacyLog.objects.filter(match_status="MATCHED").count(),
            "unmatched": SOSYSLegacyLog.objects.filter(match_status="UNMATCHED").count(),
            "flagged": SOSYSLegacyLog.objects.filter(match_status="FLAGGED").count(),
            "total": SOSYSLegacyLog.objects.count(),
        }

    def resolve_samanvaya_anomaly_count(self, info):
        return SOSYSLegacyLog.objects.filter(
            match_status__in=["FLAGGED", "UNMATCHED"], resolved=False
        ).count()

    def resolve_samanvaya_gateway_configs(self, info):
        return GatewayConfig.objects.all()
