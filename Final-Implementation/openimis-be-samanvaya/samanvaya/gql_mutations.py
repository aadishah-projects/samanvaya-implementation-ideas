"""
GraphQL Mutations — Execute batch, retry, upload CSV, resolve anomaly.
"""
import csv
import io
import uuid
import graphene
from django.core.exceptions import PermissionDenied

from .models import PaymentBatch, PaymentTransaction, SOSYSLegacyLog
from .services import BulkDisbursementService
from .permissions import check_permission


class CreatePaymentBatchMutation(graphene.Mutation):
    class Arguments:
        claim_ids = graphene.List(graphene.UUID, required=True)

    success = graphene.Boolean()
    message = graphene.String()
    batch_id = graphene.UUID()

    def mutate(self, info, claim_ids):
        user = info.context.user
        if not check_permission(user, 150002):
            raise PermissionDenied("No permission to create payment batch.")

        try:
            service = BulkDisbursementService(user=user)
            batch = service.create_batch(claim_ids)
            return CreatePaymentBatchMutation(
                success=True, message=f"Batch created with {batch.claim_count} claims.",
                batch_id=batch.id,
            )
        except ValueError as e:
            return CreatePaymentBatchMutation(success=False, message=str(e))


class ExecutePaymentBatchMutation(graphene.Mutation):
    class Arguments:
        batch_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, batch_id):
        user = info.context.user
        if not check_permission(user, 150002):
            raise PermissionDenied("No permission to execute payment batch.")

        try:
            service = BulkDisbursementService(user=user)
            batch = service.execute_batch(str(batch_id))
            return ExecutePaymentBatchMutation(
                success=True,
                message=f"Batch {str(batch_id)[:8]} executed. Status: {batch.status}",
            )
        except ValueError as e:
            return ExecutePaymentBatchMutation(success=False, message=str(e))


class RetryFailedTransactionMutation(graphene.Mutation):
    class Arguments:
        transaction_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, transaction_id):
        user = info.context.user
        if not check_permission(user, 150003):
            raise PermissionDenied("No permission to retry transactions.")

        try:
            service = BulkDisbursementService(user=user)
            tx = service.retry_transaction(str(transaction_id))
            return RetryFailedTransactionMutation(
                success=True,
                message=f"Transaction retried. New status: {tx.status}",
            )
        except ValueError as e:
            return RetryFailedTransactionMutation(success=False, message=str(e))


class UploadSOSYSCSVMutation(graphene.Mutation):
    class Arguments:
        csv_content = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    uploaded_count = graphene.Int()
    matched = graphene.Int()
    unmatched = graphene.Int()
    flagged = graphene.Int()

    def mutate(self, info, csv_content):
        user = info.context.user
        if not check_permission(user, 150004):
            raise PermissionDenied("No permission to upload SOSYS CSV.")

        # Clear previous logs
        SOSYSLegacyLog.objects.all().delete()

        reader = csv.DictReader(io.StringIO(csv_content))
        count = 0
        for row in reader:
            SOSYSLegacyLog.objects.create(
                claim_code=row.get("claim_code", "").strip(),
                health_facility=row.get("health_facility", "").strip(),
                amount=float(row.get("amount", 0)),
                payment_date=row.get("payment_date", ""),
                sosys_status=row.get("status", ""),
            )
            count += 1

        # Run reconciliation
        from .reconciliation import run_reconciliation
        summary = run_reconciliation()

        return UploadSOSYSCSVMutation(
            success=True,
            message=f"Uploaded {count} rows. Reconciliation complete.",
            uploaded_count=count,
            matched=summary["matched"],
            unmatched=summary["unmatched"],
            flagged=summary["flagged"],
        )


class ResolveReconciliationAnomalyMutation(graphene.Mutation):
    class Arguments:
        log_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, log_id):
        user = info.context.user
        if not check_permission(user, 150005):
            raise PermissionDenied("No permission to resolve anomalies.")

        try:
            log = SOSYSLegacyLog.objects.get(id=log_id)
            log.resolved = True
            log.save()
            return ResolveReconciliationAnomalyMutation(
                success=True, message=f"Anomaly {str(log_id)[:8]} resolved."
            )
        except SOSYSLegacyLog.DoesNotExist:
            return ResolveReconciliationAnomalyMutation(
                success=False, message="Log entry not found."
            )


class Mutation(graphene.ObjectType):
    create_payment_batch = CreatePaymentBatchMutation.Field()
    execute_payment_batch = ExecutePaymentBatchMutation.Field()
    retry_failed_transaction = RetryFailedTransactionMutation.Field()
    upload_sosys_csv = UploadSOSYSCSVMutation.Field()
    resolve_reconciliation_anomaly = ResolveReconciliationAnomalyMutation.Field()
