from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import SOSYSLegacyLog
from schemas import ReconciliationResultResponse, ReconciliationSummaryResponse
from services import reconciliation as recon_service
from services.sosys_mock import (
    build_mock_sosys_rows,
    parse_sosys_csv,
    replace_sosys_logs,
    rows_to_csv,
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


@router.get("/generate-csv")
def generate_sosys_csv(scenario: str = "mixed", db: Session = Depends(get_db)):
    """Download a generated SOSYS-style CSV from the current Samanvaya ledger."""
    rows = build_mock_sosys_rows(db, scenario=scenario)
    csv_text = rows_to_csv(rows)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="sosys_{scenario}_export.csv"'
        },
    )


@router.post("/generate-demo")
def generate_and_run_demo(scenario: str = "mixed", db: Session = Depends(get_db)):
    """Generate mock SOSYS rows, load them, and run reconciliation immediately."""
    rows = build_mock_sosys_rows(db, scenario=scenario)
    count = replace_sosys_logs(db, rows)
    summary = recon_service.reconcile(db)
    return {
        "generated": count,
        "scenario": scenario,
        "reconciliation": summary,
        "csv_preview": rows_to_csv(rows).splitlines()[:8],
    }


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
