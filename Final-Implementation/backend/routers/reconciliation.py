from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import SOSYSLegacyLog
from schemas import ReconciliationResultResponse, ReconciliationSummaryResponse
from services import reconciliation as recon_service
from services.sosys_mock import (
    parse_sosys_csv,
    replace_sosys_logs,
)

router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliation"])


@router.post("/upload")
def upload_sosys_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Parse uploaded SOSYS legacy CSV into SOSYSLegacyLogs."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    content = file.file.read().decode("utf-8")
    rows = parse_sosys_csv(content)
    count = replace_sosys_logs(db, rows)

    # Auto-run reconciliation
    summary = recon_service.reconcile(db)

    return {"uploaded": count, "reconciliation": summary}


@router.post("/run", response_model=ReconciliationSummaryResponse)
def run_reconciliation(db: Session = Depends(get_db)):
    """Re-run comparison between the SOSYS audit ledger and Mock Bank ledger."""
    return ReconciliationSummaryResponse(**recon_service.reconcile(db))


@router.get("/sosys-ledger", response_model=list[ReconciliationResultResponse])
def get_sosys_ledger(db: Session = Depends(get_db)):
    return (
        db.query(SOSYSLegacyLog)
        .order_by(SOSYSLegacyLog.payment_date.desc(), SOSYSLegacyLog.claim_code.asc())
        .all()
    )


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
