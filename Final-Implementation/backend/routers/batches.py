from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import PaymentBatch, PaymentTransaction, Claim
from schemas import (
    BatchAutoCreateRequest,
    BatchAutoCreateResponse,
    BatchCreateRequest,
    BatchDetailResponse,
    BatchDetailTransactionResponse,
    BatchResponse,
    FinancialScreeningRequest,
    TransactionResponse,
)
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


@router.post("/auto", response_model=BatchAutoCreateResponse)
def create_batches_automatically(req: BatchAutoCreateRequest, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        batches, over_limit_claims = service.create_batches_by_amount_limit(req.amount_limit)
        batch_responses = [BatchResponse.model_validate(batch) for batch in batches]
        return BatchAutoCreateResponse(
            created_count=len(batches),
            total_claims=sum(batch.claim_count for batch in batches),
            total_amount=sum(batch.total_amount for batch in batches),
            amount_limit=req.amount_limit,
            over_limit_claims=over_limit_claims,
            batches=batch_responses,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[BatchResponse])
def list_batches(db: Session = Depends(get_db)):
    return db.query(PaymentBatch).order_by(PaymentBatch.created_at.desc()).all()


@router.get("/{batch_id}", response_model=BatchDetailResponse)
def get_batch_details(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(PaymentBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    txs = (
        db.query(PaymentTransaction)
        .filter_by(batch_id=batch_id)
        .order_by(PaymentTransaction.created_at)
        .all()
    )
    return BatchDetailResponse(
        id=batch.id,
        batch_code=batch.batch_code,
        health_facility=batch.health_facility,
        created_at=batch.created_at,
        total_amount=batch.total_amount,
        claim_count=batch.claim_count,
        status=batch.status,
        transactions=[
            BatchDetailTransactionResponse(
                id=tx.id,
                claim_id=tx.claim_id,
                claim_code=tx.claim.claim_code if tx.claim else None,
                insuree_name=tx.claim.insuree_name if tx.claim else None,
                health_facility=tx.claim.health_facility if tx.claim else None,
                amount=tx.amount,
                claimed_amount=tx.claimed_amount,
                approved_amount=tx.approved_amount or tx.amount,
                paid_amount=tx.paid_amount,
                status=tx.status,
                gateway_ref_id=tx.gateway_ref_id,
                clinical_screening_reasons=tx.clinical_screening_reasons or [],
                financial_screening_reason=tx.financial_screening_reason,
                financial_screening_notes=tx.financial_screening_notes,
                financial_screening_completed=bool(tx.financial_screening_completed),
                retry_count=tx.retry_count,
                created_at=tx.created_at,
                updated_at=tx.updated_at,
            )
            for tx in txs
        ],
    )


@router.post("/{batch_id}/execute", response_model=BatchResponse)
def execute_batch(batch_id: str, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        batch = service.pay_batch(batch_id)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/pay", response_model=BatchResponse)
def pay_batch(batch_id: str, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        batch = service.pay_batch(batch_id)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/pay-less", response_model=BatchResponse)
def pay_less(batch_id: str, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        batch = service.pay_batch(batch_id, pay_less=True)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/ghost-payment")
def ghost_payment(batch_id: str, db: Session = Depends(get_db)):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        result = service.inject_ghost_payment(batch_id)
        if result.get("ok") is False:
            raise HTTPException(status_code=502, detail=result.get("error") or "Mock Bank ghost injection failed.")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/financial-screening", response_model=BatchResponse)
def run_financial_screening(
    batch_id: str,
    req: FinancialScreeningRequest,
    db: Session = Depends(get_db),
):
    gateway = MockBankGateway()
    service = BulkDisbursementService(db, gateway)
    try:
        return service.run_financial_screening(batch_id, req.reason, req.notes)
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
