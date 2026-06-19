import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Claim,
    ClaimStatus,
    PaymentBatch,
    PaymentTransaction,
    SOSYSLegacyLog,
)
from schemas import TransactionResponse, TransactionDetailResponse
from services.disbursement import BulkDisbursementService
from services.gateway.mock_bank import MockBankGateway
from services.status import apply_gateway_status

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    status: str | None = None,
    health_facility: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(PaymentTransaction)
    if status:
        query = query.filter(PaymentTransaction.status == status.upper())
    txs = query.order_by(PaymentTransaction.created_at.desc()).all()

    results = []
    for tx in txs:
        claim = db.query(Claim).filter_by(id=tx.claim_id).first()
        if health_facility and claim and health_facility.lower() not in claim.health_facility.lower():
            continue
        results.append(TransactionResponse(
            id=tx.id,
            batch_id=tx.batch_id,
            claim_id=tx.claim_id,
            amount=tx.amount,
            claimed_amount=tx.claimed_amount,
            approved_amount=tx.approved_amount or tx.amount,
            paid_amount=tx.paid_amount,
            status=tx.status,
            idempotency_key=tx.idempotency_key,
            gateway_name=tx.gateway_name,
            gateway_ref_id=tx.gateway_ref_id,
            retry_count=tx.retry_count,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
            health_facility=claim.health_facility if claim else None,
            claim_code=claim.claim_code if claim else None,
            insuree_name=claim.insuree_name if claim else None,
            clinical_screening_reasons=tx.clinical_screening_reasons or [],
            financial_screening_reason=tx.financial_screening_reason,
            financial_screening_notes=tx.financial_screening_notes,
            financial_screening_completed=bool(tx.financial_screening_completed),
        ))
    return results


@router.get("/export-csv")
def export_ledger_csv(db: Session = Depends(get_db)):
    """Download the transaction ledger as a finance/audit CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "transaction_id",
        "batch_id",
        "claim_code",
        "health_facility",
        "claimed_amount",
        "approved_amount",
        "paid_amount",
        "status",
        "gateway_name",
        "gateway_ref_id",
        "retry_count",
        "created_at",
        "updated_at",
        "webhook_received_at",
    ], lineterminator="\n")
    writer.writeheader()

    txs = (
        db.query(PaymentTransaction)
        .order_by(PaymentTransaction.created_at.desc())
        .all()
    )
    for tx in txs:
        claim = db.query(Claim).filter_by(id=tx.claim_id).first()
        writer.writerow({
            "transaction_id": tx.id,
            "batch_id": tx.batch_id,
            "claim_code": claim.claim_code if claim else "",
            "health_facility": claim.health_facility if claim else "",
            "claimed_amount": tx.claimed_amount if tx.claimed_amount is not None else "",
            "approved_amount": tx.approved_amount if tx.approved_amount is not None else tx.amount,
            "paid_amount": tx.paid_amount if tx.paid_amount is not None else "",
            "status": tx.status,
            "gateway_name": tx.gateway_name,
            "gateway_ref_id": tx.gateway_ref_id or "",
            "retry_count": tx.retry_count,
            "created_at": tx.created_at.isoformat() if tx.created_at else "",
            "updated_at": tx.updated_at.isoformat() if tx.updated_at else "",
            "webhook_received_at": tx.webhook_received_at.isoformat() if tx.webhook_received_at else "",
        })

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="samanvaya_ledger_export.csv"'
        },
    )


@router.delete("/ledger")
def clear_ledger(db: Session = Depends(get_db)):
    """Clear payment ledger data and make affected claims demo-ready again."""
    affected_claim_ids = [
        row[0]
        for row in db.query(PaymentTransaction.claim_id).distinct().all()
        if row[0]
    ]
    transaction_count = db.query(PaymentTransaction).count()
    batch_count = db.query(PaymentBatch).count()
    reconciliation_count = db.query(SOSYSLegacyLog).count()

    if affected_claim_ids:
        (
            db.query(Claim)
            .filter(Claim.id.in_(affected_claim_ids))
            .update({Claim.status: ClaimStatus.APPROVED.value}, synchronize_session=False)
        )

    db.query(PaymentTransaction).delete(synchronize_session=False)
    db.query(PaymentBatch).delete(synchronize_session=False)
    db.query(SOSYSLegacyLog).delete(synchronize_session=False)
    db.commit()

    return {
        "ok": True,
        "deleted_transactions": transaction_count,
        "deleted_batches": batch_count,
        "deleted_reconciliation_rows": reconciliation_count,
        "reset_claims": len(affected_claim_ids),
    }


@router.get("/{tx_id}", response_model=TransactionDetailResponse)
def get_transaction(tx_id: str, db: Session = Depends(get_db)):
    tx = db.query(PaymentTransaction).filter_by(id=tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    claim = db.query(Claim).filter_by(id=tx.claim_id).first()
    return TransactionDetailResponse(
        id=tx.id,
        batch_id=tx.batch_id,
        claim_id=tx.claim_id,
        amount=tx.amount,
        claimed_amount=tx.claimed_amount,
        approved_amount=tx.approved_amount or tx.amount,
        paid_amount=tx.paid_amount,
        status=tx.status,
        idempotency_key=tx.idempotency_key,
        gateway_name=tx.gateway_name,
        gateway_ref_id=tx.gateway_ref_id,
        retry_count=tx.retry_count,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
        health_facility=claim.health_facility if claim else None,
        claim_code=claim.claim_code if claim else None,
        insuree_name=claim.insuree_name if claim else None,
        clinical_screening_reasons=tx.clinical_screening_reasons or [],
        financial_screening_reason=tx.financial_screening_reason,
        financial_screening_notes=tx.financial_screening_notes,
        financial_screening_completed=bool(tx.financial_screening_completed),
        raw_request_log=tx.raw_request_log,
        raw_response_log=tx.raw_response_log,
        webhook_received_at=tx.webhook_received_at,
    )


@router.post("/{tx_id}/verify", response_model=TransactionResponse)
def verify_transaction(tx_id: str, db: Session = Depends(get_db)):
    tx = db.query(PaymentTransaction).filter_by(id=tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if not tx.gateway_ref_id:
        raise HTTPException(status_code=400, detail="Transaction has no gateway reference yet.")

    gateway = MockBankGateway()
    result = gateway.verify_status(tx.gateway_ref_id)
    if result.status in {"SUCCESS", "FAILED", "PENDING", "PROCESSING"}:
        tx = apply_gateway_status(db, tx, result.status, {
            "source": "manual_verify",
            **result.raw_response,
        })
    else:
        tx.raw_response_log = {
            "source": "manual_verify",
            **result.raw_response,
        }
        db.commit()
        db.refresh(tx)

    claim = db.query(Claim).filter_by(id=tx.claim_id).first()
    return TransactionResponse(
        id=tx.id,
        batch_id=tx.batch_id,
        claim_id=tx.claim_id,
        amount=tx.amount,
        claimed_amount=tx.claimed_amount,
        approved_amount=tx.approved_amount or tx.amount,
        paid_amount=tx.paid_amount,
        status=tx.status,
        idempotency_key=tx.idempotency_key,
        gateway_name=tx.gateway_name,
        gateway_ref_id=tx.gateway_ref_id,
        retry_count=tx.retry_count,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
        health_facility=claim.health_facility if claim else None,
        claim_code=claim.claim_code if claim else None,
        insuree_name=claim.insuree_name if claim else None,
        clinical_screening_reasons=tx.clinical_screening_reasons or [],
        financial_screening_reason=tx.financial_screening_reason,
        financial_screening_notes=tx.financial_screening_notes,
        financial_screening_completed=bool(tx.financial_screening_completed),
    )


@router.post("/{tx_id}/retry", response_model=TransactionResponse)
def retry_transaction(tx_id: str, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        tx = service.retry_transaction(tx_id)
        claim = db.query(Claim).filter_by(id=tx.claim_id).first()
        return TransactionResponse(
            id=tx.id,
            batch_id=tx.batch_id,
            claim_id=tx.claim_id,
            amount=tx.amount,
            claimed_amount=tx.claimed_amount,
            approved_amount=tx.approved_amount or tx.amount,
            paid_amount=tx.paid_amount,
            status=tx.status,
            idempotency_key=tx.idempotency_key,
            gateway_name=tx.gateway_name,
            gateway_ref_id=tx.gateway_ref_id,
            retry_count=tx.retry_count,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
            health_facility=claim.health_facility if claim else None,
            claim_code=claim.claim_code if claim else None,
            insuree_name=claim.insuree_name if claim else None,
            clinical_screening_reasons=tx.clinical_screening_reasons or [],
            financial_screening_reason=tx.financial_screening_reason,
            financial_screening_notes=tx.financial_screening_notes,
            financial_screening_completed=bool(tx.financial_screening_completed),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
