from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Claim, ClaimStatus
from schemas import ClaimResponse

router = APIRouter(prefix="/api/claims", tags=["Claims"])


@router.get("", response_model=list[ClaimResponse])
def list_claims(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Claim)
    if status:
        query = query.filter(Claim.status == status.upper())
    return query.order_by(Claim.approved_date.desc()).all()


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
