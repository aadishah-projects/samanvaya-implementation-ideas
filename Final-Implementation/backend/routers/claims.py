from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Claim, ClaimAuditLog, ClaimStatus
from schemas import (
    ClaimBulkReviewRequest,
    ClaimDetailResponse,
    ClaimResponse,
    ClaimReviewListResponse,
    ClaimReviewRequest,
)

router = APIRouter(prefix="/api/claims", tags=["Claims"])


@router.get("", response_model=list[ClaimResponse])
def list_claims(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Claim)
    if status:
        query = query.filter(Claim.status == status.upper())
    return query.order_by(Claim.approved_date.desc()).all()


@router.get("/review", response_model=list[ClaimReviewListResponse])
def list_claims_for_review(db: Session = Depends(get_db)):
    claims = (
        db.query(Claim)
        .filter(Claim.status.in_([ClaimStatus.APPROVED.value, "PENDING"]))
        .order_by(Claim.approved_date.desc())
        .all()
    )
    return [
        ClaimReviewListResponse(
            id=claim.id,
            claim_code=claim.claim_code,
            health_facility=claim.health_facility,
            insuree_name=claim.insuree_name,
            claimed_amount=claim.claimed_amount,
            submitted_date=claim.claimed_date,
            review_status=claim.review_status,
        )
        for claim in claims
    ]


@router.post("/bulk-review")
def bulk_review_claims(req: ClaimBulkReviewRequest, db: Session = Depends(get_db)):
    status = _normalize_review_status(req.status)
    claims = db.query(Claim).filter(Claim.id.in_(req.claim_ids)).all()
    if len(claims) != len(set(req.claim_ids)):
        raise HTTPException(status_code=404, detail="One or more claims were not found.")

    now = datetime.now(timezone.utc)
    try:
        for claim in claims:
            _apply_review(db, claim, status, req.notes, now)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True, "updated": len(claims), "status": status}


@router.get("/{claim_id}/details", response_model=ClaimDetailResponse)
def get_claim_details(claim_id: str, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


@router.post("/{claim_id}/review", response_model=ClaimDetailResponse)
def review_claim(claim_id: str, req: ClaimReviewRequest, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")

    status = _normalize_review_status(req.status)
    _apply_review(db, claim, status, req.notes, datetime.now(timezone.utc))
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/approve", response_model=ClaimResponse)
def approve_claim(claim_id: str, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter_by(id=claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    claim.status = ClaimStatus.APPROVED.value
    claim.approved_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(claim)
    return claim


def _normalize_review_status(status: str) -> str:
    normalized = (status or "").upper()
    if normalized not in {"APPROVED", "REJECTED", "PENDING"}:
        raise HTTPException(status_code=400, detail="Status must be APPROVED, REJECTED, or PENDING.")
    return normalized


def _apply_review(db: Session, claim: Claim, status: str, notes: str | None, reviewed_at: datetime):
    old_status = claim.status
    claim.review_status = {
        "APPROVED": "Reviewed",
        "REJECTED": "Rejected",
        "PENDING": "Pending",
    }[status]
    claim.review_notes = notes
    claim.reviewed_by = "demo_user"
    claim.reviewed_at = reviewed_at
    claim.status = ClaimStatus.APPROVED.value if status == "APPROVED" else status
    if status == "APPROVED":
        claim.approved_date = reviewed_at

    db.add(ClaimAuditLog(
        claim_id=claim.id,
        action="CLAIM_REVIEW",
        old_status=old_status,
        new_status=claim.status,
        notes=notes,
        actor="demo_user",
    ))
