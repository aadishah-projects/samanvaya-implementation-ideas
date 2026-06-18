import io
import csv
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models import SOSYSLegacyLog
from schemas import ReconciliationResultResponse, ReconciliationSummaryResponse
from services import reconciliation as recon_service

router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliation"])


@router.post("/upload")
def upload_sosys_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Parse uploaded SOSYS legacy CSV into SOSYSLegacyLogs."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    # Clear previous logs
    db.query(SOSYSLegacyLog).delete()
    db.commit()

    count = 0
    for row in reader:
        log = SOSYSLegacyLog(
            claim_code=row.get("claim_code", "").strip(),
            health_facility=row.get("health_facility", "").strip(),
            amount=float(row.get("amount", 0)),
            payment_date=row.get("payment_date", ""),
            sosys_status=row.get("status", ""),
        )
        db.add(log)
        count += 1

    db.commit()

    # Auto-run reconciliation
    summary = recon_service.reconcile(db)

    return {"uploaded": count, "reconciliation": summary}


@router.get("/results", response_model=list[ReconciliationResultResponse])
def get_results(db: Session = Depends(get_db)):
    return db.query(SOSYSLegacyLog).order_by(SOSYSLegacyLog.claim_code).all()


@router.get("/summary", response_model=ReconciliationSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    matched = db.query(SOSYSLegacyLog).filter_by(match_status="MATCHED").count()
    unmatched = db.query(SOSYSLegacyLog).filter_by(match_status="UNMATCHED").count()
    flagged = db.query(SOSYSLegacyLog).filter_by(match_status="FLAGGED").count()
    total = db.query(SOSYSLegacyLog).count()
    return ReconciliationSummaryResponse(
        matched=matched, unmatched=unmatched, flagged=flagged, total=total
    )


@router.post("/{log_id}/resolve")
def resolve_anomaly(log_id: str, db: Session = Depends(get_db)):
    log = db.query(SOSYSLegacyLog).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    log.resolved = True
    db.commit()
    return {"ok": True, "id": log_id}
