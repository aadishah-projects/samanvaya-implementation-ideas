from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import PaymentBatch, PaymentTransaction, Claim
from schemas import BatchCreateRequest, BatchResponse, TransactionResponse
from services.disbursement import BulkDisbursementService
from services.gateway.mock_bank import MockBankGateway

router = APIRouter(prefix="/api/batches", tags=["Batches"])


@router.post("", response_model=BatchResponse)
def create_batch(req: BatchCreateRequest, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        batch = service.create_batch(req.claim_ids)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[BatchResponse])
def list_batches(db: Session = Depends(get_db)):
    return db.query(PaymentBatch).order_by(PaymentBatch.created_at.desc()).all()


@router.post("/{batch_id}/execute", response_model=BatchResponse)
def execute_batch(batch_id: str, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        batch = service.execute_batch(batch_id)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{batch_id}/transactions", response_model=list[TransactionResponse])
def list_batch_transactions(batch_id: str, db: Session = Depends(get_db)):
    txs = (
        db.query(PaymentTransaction)
        .filter_by(batch_id=batch_id)
        .order_by(PaymentTransaction.created_at)
        .all()
    )
    results = []
    for tx in txs:
        claim = db.query(Claim).filter_by(id=tx.claim_id).first()
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
