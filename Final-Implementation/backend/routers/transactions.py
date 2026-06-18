from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import PaymentTransaction, Claim
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
            status=tx.status,
            idempotency_key=tx.idempotency_key,
            gateway_name=tx.gateway_name,
            gateway_ref_id=tx.gateway_ref_id,
            retry_count=tx.retry_count,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
            health_facility=claim.health_facility if claim else None,
            claim_code=claim.claim_code if claim else None,
        ))
    return results


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
        status=tx.status,
        idempotency_key=tx.idempotency_key,
        gateway_name=tx.gateway_name,
        gateway_ref_id=tx.gateway_ref_id,
        retry_count=tx.retry_count,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
        health_facility=claim.health_facility if claim else None,
        claim_code=claim.claim_code if claim else None,
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
        status=tx.status,
        idempotency_key=tx.idempotency_key,
        gateway_name=tx.gateway_name,
        gateway_ref_id=tx.gateway_ref_id,
        retry_count=tx.retry_count,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
        health_facility=claim.health_facility if claim else None,
        claim_code=claim.claim_code if claim else None,
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
            status=tx.status,
            idempotency_key=tx.idempotency_key,
            gateway_name=tx.gateway_name,
            gateway_ref_id=tx.gateway_ref_id,
            retry_count=tx.retry_count,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
            health_facility=claim.health_facility if claim else None,
            claim_code=claim.claim_code if claim else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
