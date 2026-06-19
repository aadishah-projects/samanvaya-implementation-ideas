from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import MatchStatus, PaymentTransaction, SOSYSLegacyLog
from schemas import ReconciliationResultResponse, ReconciliationSummaryResponse
from services import reconciliation as recon_service
from services.sosys_mock import (
    parse_sosys_csv,
    replace_sosys_logs,
)

router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliation"])


@router.post("/upload")
def upload_sosys_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Deprecated: SOSYS no longer accepts independent ledger data."""
    raise HTTPException(status_code=410, detail="SOSYS is now a read-only mirror of the OpenIMIS ledger.")


@router.post("/run", response_model=ReconciliationSummaryResponse)
def run_reconciliation(db: Session = Depends(get_db)):
    """Re-run comparison between the OpenIMIS ledger and Bank ledger."""
    return ReconciliationSummaryResponse(**recon_service.reconcile(db))


@router.get("/sosys-ledger", response_model=list[ReconciliationResultResponse])
def get_sosys_ledger(db: Session = Depends(get_db)):
    return [
        openimis_mirror_row(tx)
        for tx in db.query(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).all()
    ]


@router.get("/results", response_model=list[ReconciliationResultResponse])
def get_results(db: Session = Depends(get_db)):
    return db.query(SOSYSLegacyLog).order_by(SOSYSLegacyLog.claim_code).all()


@router.get("/summary", response_model=ReconciliationSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    return ReconciliationSummaryResponse(**recon_service.build_summary(db))


@router.post("/{log_id}/resolve")
def resolve_anomaly(log_id: str, db: Session = Depends(get_db)):
    log = db.query(SOSYSLegacyLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    log.resolved = True
    db.commit()
    return {"ok": True, "id": log_id}


def openimis_mirror_row(tx: PaymentTransaction) -> ReconciliationResultResponse:
    claim = tx.claim
    batch = tx.batch
    claimed = float(tx.claimed_amount if tx.claimed_amount is not None else (claim.claimed_amount if claim else tx.amount))
    approved = float(tx.approved_amount if tx.approved_amount is not None else tx.amount)
    paid = float(tx.paid_amount or 0)
    return ReconciliationResultResponse(
        id=tx.id,
        claim_code=claim.claim_code if claim else tx.claim_id,
        health_facility=claim.health_facility if claim else (batch.health_facility if batch else "Unknown"),
        amount=approved,
        claimed_amount=claimed,
        approved_amount=approved,
        paid_amount=paid,
        batch_code=batch.batch_code if batch else None,
        gateway_ref_id=tx.gateway_ref_id,
        payment_date=tx.updated_at.strftime("%Y-%m-%d") if tx.updated_at else None,
        sosys_status="OPENIMIS_MIRROR",
        source="OPENIMIS_LEDGER",
        match_status=MatchStatus.MATCHED.value,
        issue_type=None,
        notes="Read-only SOSYS mirror row sourced from the OpenIMIS ledger.",
        clinical_difference=max(claimed - approved, 0.0),
        financial_difference=approved - paid,
        total_difference=claimed - paid,
        clinical_reasons=tx.clinical_screening_reasons or [],
        financial_reason=tx.financial_screening_reason,
        financial_notes=tx.financial_screening_notes,
        financial_screening_completed=bool(tx.financial_screening_completed),
        resolved=False,
    )
