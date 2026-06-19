"""Bulk Disbursement Service: the financial heart of Samanvaya."""
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    BatchStatus,
    Claim,
    ClaimStatus,
    PaymentBatch,
    PaymentTransaction,
    TransactionStatus,
)
from services.gateway.base import BasePaymentGateway
from services.status import apply_gateway_status, update_batch_status


class BulkDisbursementService:
    def __init__(self, db: Session, gateway: BasePaymentGateway):
        self.db = db
        self.gateway = gateway

    def create_batch(self, claim_ids: list[str]) -> PaymentBatch:
        """Create a PaymentBatch from a list of approved claim IDs."""
        claims = (
            self.db.query(Claim)
            .filter(Claim.id.in_(claim_ids), Claim.status == ClaimStatus.APPROVED.value)
            .all()
        )
        if not claims:
            raise ValueError("No approved claims found for the given IDs.")

        hospitals = {claim.health_facility for claim in claims}
        if len(hospitals) != 1:
            raise ValueError("A payment batch can contain claims from one hospital only.")

        hospital = claims[0].health_facility
        batch = PaymentBatch(
            batch_code=self._next_batch_code(hospital),
            health_facility=hospital,
            total_amount=sum(c.approved_amount for c in claims),
            claim_count=len(claims),
            status=BatchStatus.QUEUED.value,
        )
        self.db.add(batch)
        self.db.flush()

        for claim in claims:
            self.db.add(
                PaymentTransaction(
                    batch_id=batch.id,
                    claim_id=claim.id,
                    amount=claim.approved_amount,
                    claimed_amount=claim.claimed_amount,
                    approved_amount=claim.approved_amount,
                    paid_amount=0.0,
                    status=TransactionStatus.PENDING.value,
                    gateway_name="mock_bank",
                    clinical_screening_reasons=clinical_screening_reasons(claim),
                )
            )
            claim.status = ClaimStatus.QUEUED.value

        self.db.commit()
        self.db.refresh(batch)
        return batch

    def create_batches_by_amount_limit(self, amount_limit: float) -> tuple[list[PaymentBatch], list[str]]:
        """Create amount-limited batches, grouped by individual hospital."""
        if amount_limit <= 0:
            raise ValueError("Amount limit must be greater than zero.")

        claims = (
            self.db.query(Claim)
            .filter(Claim.status == ClaimStatus.APPROVED.value)
            .order_by(Claim.health_facility.asc(), Claim.approved_date.asc(), Claim.claim_code.asc())
            .all()
        )
        if not claims:
            raise ValueError("No approved claims are available for automatic batching.")

        created_batches: list[PaymentBatch] = []
        over_limit_claims: list[str] = []

        claims_by_hospital: dict[str, list[Claim]] = {}
        for claim in claims:
            claims_by_hospital.setdefault(claim.health_facility, []).append(claim)

        for hospital in sorted(claims_by_hospital):
            current_group: list[Claim] = []
            current_total = 0.0

            def flush_group():
                nonlocal current_group, current_total
                if not current_group:
                    return
                batch = self.create_batch([claim.id for claim in current_group])
                created_batches.append(batch)
                current_group = []
                current_total = 0.0

            for claim in claims_by_hospital[hospital]:
                amount = float(claim.approved_amount)
                if amount > amount_limit:
                    flush_group()
                    over_limit_claims.append(claim.claim_code)
                    continue

                if current_group and current_total + amount > amount_limit:
                    flush_group()

                current_group.append(claim)
                current_total += amount

            flush_group()

        return created_batches, over_limit_claims

    def pay_batch(self, batch_id: str, pay_less: bool = False) -> PaymentBatch:
        """Record OpenIMIS-approved payments in the internal and bank ledgers."""
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found.")

        transactions = (
            self.db.query(PaymentTransaction)
            .filter_by(batch_id=batch_id, status=TransactionStatus.PENDING.value)
            .all()
        )
        if not transactions:
            raise ValueError("No pending transactions in this batch.")

        batch.status = BatchStatus.EXECUTING.value
        self.db.commit()

        for tx in transactions:
            tx.status = TransactionStatus.PROCESSING.value
            self.db.commit()

            approved_amount = float(tx.approved_amount or tx.amount or 0)
            claimed_amount = (
                float(tx.claimed_amount)
                if tx.claimed_amount is not None
                else float(tx.claim.claimed_amount if tx.claim else approved_amount)
            )
            paid_amount = paid_amount_for_instruction(approved_amount, pay_less)
            response = self.gateway.initiate_payout(
                ref_id=str(tx.id),
                amount=paid_amount,
                recipient=tx.claim.health_facility if tx.claim else "Unknown",
                metadata={
                    "batch_id": batch.id,
                    "batch_code": batch.batch_code,
                    "claim_id": tx.claim_id,
                    "claim_code": tx.claim.claim_code if tx.claim else None,
                    "health_facility": tx.claim.health_facility if tx.claim else None,
                    "openimis_transaction_id": tx.id,
                    "claimed_amount": claimed_amount,
                    "approved_amount": approved_amount,
                    "simulation": "PAY_LESS" if pay_less else "PAY",
                },
            )

            tx.raw_request_log = response.request_payload
            tx.gateway_ref_id = response.gateway_ref if response.gateway_ref else None
            tx.paid_amount = paid_amount if response.status == "SUCCESS" else 0.0
            tx.financial_screening_completed = False
            apply_gateway_status(self.db, tx, response.status, response.raw_response)

        return self.db.query(PaymentBatch).filter_by(id=batch_id).first()

    def execute_batch(self, batch_id: str) -> PaymentBatch:
        """Backward-compatible alias for the renamed Pay operation."""
        return self.pay_batch(batch_id)

    def inject_ghost_payment(self, batch_id: str) -> dict:
        """Insert a bank-ledger-only payment for reconciliation testing."""
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found.")

        return self.gateway.create_ghost_payment({
            "batch_id": batch.id,
            "batch_code": batch.batch_code,
            "health_facility": batch.health_facility or "Unknown",
            "amount": round(max(float(batch.total_amount or 0) * 0.07, 1000.0), 2),
        })

    def run_financial_screening(
        self,
        batch_id: str,
        reason: str | None = None,
        notes: str | None = None,
    ) -> PaymentBatch:
        """Record financial reasons for Approved vs Paid differences."""
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found.")

        transactions = self.db.query(PaymentTransaction).filter_by(batch_id=batch_id).all()
        if not transactions:
            raise ValueError("No transactions found for this batch.")

        difference_txs = [
            tx for tx in transactions
            if abs(float(tx.approved_amount or tx.amount or 0) - float(tx.paid_amount or 0)) > 0.01
        ]
        if difference_txs and not (reason or "").strip():
            raise ValueError("Financial screening reason is required when Approved and Paid amounts differ.")

        screened_at = datetime.now(timezone.utc).isoformat()
        for tx in transactions:
            approved_amount = float(tx.approved_amount or tx.amount or 0)
            paid_amount = float(tx.paid_amount or 0)
            has_difference = abs(approved_amount - paid_amount) > 0.01
            tx.financial_screening_completed = True
            tx.financial_screening_reason = (reason or "").strip() if has_difference else "No financial difference"
            tx.financial_screening_notes = (notes or "").strip() if has_difference else None
            tx.raw_response_log = {
                **(tx.raw_response_log or {}),
                "financial_screening": {
                    "completed_at": screened_at,
                    "reason": tx.financial_screening_reason,
                    "notes": tx.financial_screening_notes,
                    "approved_amount": approved_amount,
                    "paid_amount": paid_amount,
                },
            }

        self.db.commit()
        self.db.refresh(batch)
        return batch

    def retry_transaction(self, transaction_id: str) -> PaymentTransaction:
        """Retry a FAILED transaction with a new idempotency key."""
        tx = self.db.query(PaymentTransaction).filter_by(id=transaction_id).first()
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found.")
        if tx.status != TransactionStatus.FAILED.value:
            raise ValueError("Only FAILED transactions can be retried.")

        tx.idempotency_key = str(uuid.uuid4())
        tx.status = TransactionStatus.PENDING.value
        tx.retry_count += 1
        tx.gateway_ref_id = None
        tx.raw_request_log = None
        tx.raw_response_log = None
        tx.webhook_received_at = None
        self.db.commit()

        tx.status = TransactionStatus.PROCESSING.value
        self.db.commit()

        response = self.gateway.initiate_payout(
            ref_id=str(tx.idempotency_key),
            amount=tx.amount,
            recipient=tx.claim.health_facility if tx.claim else "Unknown",
            metadata={
                "batch_id": tx.batch_id,
                "batch_code": tx.batch.batch_code if tx.batch else None,
                "claim_id": tx.claim_id,
                "claim_code": tx.claim.claim_code if tx.claim else None,
                "health_facility": tx.claim.health_facility if tx.claim else None,
            },
        )

        tx.raw_request_log = response.request_payload
        tx.gateway_ref_id = response.gateway_ref if response.gateway_ref else None
        apply_gateway_status(self.db, tx, response.status, response.raw_response)
        return tx

    def _update_batch_status(self, batch_id: str):
        """Recompute batch status from its transactions."""
        update_batch_status(self.db, batch_id)

    def _next_batch_code(self, hospital: str) -> str:
        hospital_code = _hospital_code(hospital)
        existing_count = (
            self.db.query(PaymentBatch)
            .filter(PaymentBatch.batch_code.like(f"BATCH-{hospital_code}-%"))
            .count()
        )
        return f"BATCH-{hospital_code}-{existing_count + 1:04d}"


def _hospital_code(name: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", name or "")
    if not tokens:
        return "HF"
    code = "".join(token[0].upper() for token in tokens[:4])
    return code[:8] or "HF"


def paid_amount_for_instruction(approved_amount: float, pay_less: bool) -> float:
    if not pay_less:
        return round(float(approved_amount), 2)
    return round(max(float(approved_amount) * 0.9, 0.0), 2)


def clinical_screening_reasons(claim: Claim) -> list[str]:
    claimed = float(claim.claimed_amount or 0)
    approved = float(claim.approved_amount or 0)
    if approved >= claimed:
        return []

    reasons: list[str] = []
    difference = claimed - approved
    if claimed >= 100000 or difference >= 5000:
        reasons.append("Exceeded policy limit")
    if claim.diagnosis and "diabetes" in claim.diagnosis.lower():
        reasons.append("Non-covered drug")
    if claim.is_reclaim or difference >= 3000:
        reasons.append("Documentation missing")
    if not reasons:
        reasons.append("Clinical tariff adjustment")
    return reasons
