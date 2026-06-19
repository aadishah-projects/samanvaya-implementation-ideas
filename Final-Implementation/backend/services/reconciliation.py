"""Reconciliation matching algorithm: OpenIMIS ledger vs Bank ledger."""
import os

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import MatchStatus, PaymentTransaction, SOSYSLegacyLog

MOCK_BANK_URL = os.getenv("MOCK_BANK_URL", "http://localhost:8001")

ISSUE_MATCHED = "MATCHED"
ISSUE_GHOST_PAYMENT = "GHOST_PAYMENT"
ISSUE_MISSING_PAYMENT = "MISSING_PAYMENT"
ISSUE_STATUS_MISMATCH = "STATUS_MISMATCH"
ISSUE_FINANCIAL_SCREENING_REQUIRED = "FINANCIAL_SCREENING_REQUIRED"
ISSUE_CLAIMED_PAID_MISMATCH = "CLAIMED_PAID_MISMATCH"
ISSUE_AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
ISSUE_DUPLICATE = "DUPLICATE"


def reconcile(db: Session) -> dict:
    """Compare the OpenIMIS internal ledger against the bank settlement ledger."""
    db.query(SOSYSLegacyLog).delete(synchronize_session=False)
    db.commit()

    txs = db.query(PaymentTransaction).all()
    bank_rows = fetch_bank_payment_ledger()
    bank_by_ref, bank_by_composite = index_bank_rows(bank_rows)
    matched_bank_keys: set[str] = set()

    for tx in txs:
        claim = tx.claim
        batch = tx.batch
        bank_row = find_bank_row(tx, bank_by_ref, bank_by_composite)
        if bank_row:
            matched_bank_keys.add(bank_key(bank_row))

        claimed = float(tx.claimed_amount if tx.claimed_amount is not None else (claim.claimed_amount if claim else tx.amount))
        approved = float(tx.approved_amount if tx.approved_amount is not None else tx.amount)
        paid = float(bank_row.get("amount") or 0) if bank_row else 0.0
        clinical_difference = max(claimed - approved, 0.0)
        financial_difference = approved - paid
        total_difference = claimed - paid
        clinical_reasons = tx.clinical_screening_reasons or []
        financial_screened = bool(tx.financial_screening_completed)

        match_status = MatchStatus.MATCHED.value
        issue_type = ISSUE_MATCHED
        notes = "OpenIMIS ledger and Bank ledger match."

        if not bank_row:
            match_status = MatchStatus.UNMATCHED.value
            issue_type = ISSUE_MISSING_PAYMENT
            notes = "Missing payment: OpenIMIS ledger has this transaction, but the Bank ledger does not."
        elif bank_row.get("status") != "SUCCESS":
            match_status = MatchStatus.FLAGGED.value
            issue_type = ISSUE_STATUS_MISMATCH
            notes = f"Bank status is {bank_row.get('status')}, expected SUCCESS."
        elif not financial_screened:
            match_status = MatchStatus.FLAGGED.value
            issue_type = ISSUE_FINANCIAL_SCREENING_REQUIRED
            notes = "Financial screening must be run before this transaction can be considered fully reconciled."
            if abs(financial_difference) > 0.01:
                notes = (
                    f"Financial screening required: approved NPR {approved:.2f}, "
                    f"paid NPR {paid:.2f}."
                )
        elif abs(total_difference) > 0.01:
            match_status = MatchStatus.FLAGGED.value
            issue_type = ISSUE_CLAIMED_PAID_MISMATCH
            notes = reconciliation_note(
                total_difference,
                clinical_difference,
                financial_difference,
                clinical_reasons,
                tx.financial_screening_reason,
            )

        db.add(SOSYSLegacyLog(
            id=tx.id,
            claim_code=claim.claim_code if claim else tx.claim_id,
            health_facility=claim.health_facility if claim else (batch.health_facility if batch else "Unknown"),
            amount=claimed,
            claimed_amount=claimed,
            approved_amount=approved,
            paid_amount=paid,
            batch_id=tx.batch_id,
            batch_code=batch.batch_code if batch else None,
            gateway_ref_id=tx.gateway_ref_id,
            payment_date=(bank_row.get("processed_at") or "")[:10] if bank_row else None,
            sosys_status="OPENIMIS_MIRROR",
            source="OPENIMIS_LEDGER",
            match_status=match_status,
            issue_type=issue_type,
            notes=notes,
            clinical_difference=clinical_difference,
            financial_difference=financial_difference,
            total_difference=total_difference,
            clinical_reasons=clinical_reasons,
            financial_reason=tx.financial_screening_reason,
            financial_notes=tx.financial_screening_notes,
            financial_screening_completed=financial_screened,
        ))

    for row in bank_rows:
        if bank_key(row) in matched_bank_keys:
            continue
        if row.get("status") != "SUCCESS":
            continue

        paid = float(row.get("amount") or 0)
        db.add(SOSYSLegacyLog(
            id=f"BANK-{row.get('gateway_ref_id') or row.get('claim_code')}",
            claim_code=row.get("claim_code") or row.get("gateway_ref_id") or "UNKNOWN",
            health_facility=row.get("health_facility") or "Unknown",
            amount=0.0,
            claimed_amount=0.0,
            approved_amount=0.0,
            paid_amount=paid,
            batch_id=row.get("batch_id"),
            batch_code=row.get("batch_code"),
            gateway_ref_id=row.get("gateway_ref_id"),
            payment_date=(row.get("processed_at") or "")[:10],
            sosys_status="BANK_ONLY",
            source="BANK_LEDGER_ONLY",
            match_status=MatchStatus.UNMATCHED.value,
            issue_type=ISSUE_GHOST_PAYMENT,
            notes="Ghost payment: Bank ledger has this payment, but the OpenIMIS ledger does not.",
            clinical_difference=0.0,
            financial_difference=-paid,
            total_difference=-paid,
            clinical_reasons=[],
            financial_screening_completed=False,
        ))

    db.commit()
    return build_summary(db)


def fetch_bank_payment_ledger() -> list[dict]:
    try:
        resp = httpx.get(f"{MOCK_BANK_URL}/ledger/payments", timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def index_bank_rows(bank_rows: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_ref = {
        row["gateway_ref_id"]: row
        for row in bank_rows
        if row.get("gateway_ref_id")
    }
    by_composite = {
        composite_key(row.get("batch_code"), row.get("claim_code")): row
        for row in bank_rows
        if row.get("batch_code") and row.get("claim_code")
    }
    return by_ref, by_composite


def find_bank_row(
    tx: PaymentTransaction,
    by_gateway_ref: dict[str, dict],
    by_composite: dict[str, dict],
) -> dict | None:
    if tx.gateway_ref_id and tx.gateway_ref_id in by_gateway_ref:
        return by_gateway_ref[tx.gateway_ref_id]
    if tx.batch and tx.claim:
        return by_composite.get(composite_key(tx.batch.batch_code, tx.claim.claim_code))
    return None


def bank_key(row: dict) -> str:
    if row.get("gateway_ref_id"):
        return f"ref:{row['gateway_ref_id']}"
    if row.get("batch_code"):
        return composite_key(row.get("batch_code"), row.get("claim_code"))
    return f"claim:{row.get('claim_code')}"


def composite_key(batch_code: str | None, claim_code: str | None) -> str:
    return f"batch:{batch_code or ''}:claim:{claim_code or ''}"


def reconciliation_note(
    total_difference: float,
    clinical_difference: float,
    financial_difference: float,
    clinical_reasons: list[str],
    financial_reason: str | None,
) -> str:
    parts = [
        f"Claimed vs Paid flag: total deduction NPR {total_difference:.2f}.",
        f"Clinical difference NPR {clinical_difference:.2f}.",
        f"Financial difference NPR {financial_difference:.2f}.",
    ]
    if clinical_reasons:
        parts.append("Clinical reasons: " + ", ".join(clinical_reasons) + ".")
    if financial_reason:
        parts.append(f"Financial reason: {financial_reason}.")
    return " ".join(parts)


def build_summary(db: Session) -> dict:
    """Return status totals plus actionable reconciliation insight counts."""
    missing_filter = or_(
        SOSYSLegacyLog.issue_type == ISSUE_MISSING_PAYMENT,
        SOSYSLegacyLog.issue_type == "MISSING_IN_SOSYS",
    )
    return {
        "matched": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.MATCHED.value).count(),
        "unmatched": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.UNMATCHED.value).count(),
        "flagged": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.FLAGGED.value).count(),
        "total": db.query(SOSYSLegacyLog).count(),
        "ghost_payments": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_GHOST_PAYMENT).count(),
        "missing_in_sosys": db.query(SOSYSLegacyLog).filter(missing_filter).count(),
        "missing_payments": db.query(SOSYSLegacyLog).filter(missing_filter).count(),
        "amount_mismatches": db.query(SOSYSLegacyLog).filter(
            SOSYSLegacyLog.issue_type.in_([
                ISSUE_CLAIMED_PAID_MISMATCH,
                ISSUE_FINANCIAL_SCREENING_REQUIRED,
                ISSUE_AMOUNT_MISMATCH,
            ])
        ).count(),
        "duplicates": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_DUPLICATE).count(),
        "status_mismatches": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_STATUS_MISMATCH).count(),
    }
