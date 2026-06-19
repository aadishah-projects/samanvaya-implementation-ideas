"""Reconciliation matching algorithm: SOSYS audit ledger vs Mock Bank ledger."""
import os

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import MatchStatus, SOSYSLegacyLog

MOCK_BANK_URL = os.getenv("MOCK_BANK_URL", "http://localhost:8001")

ISSUE_MATCHED = "MATCHED"
ISSUE_GHOST_PAYMENT = "GHOST_PAYMENT"
ISSUE_MISSING_PAYMENT = "MISSING_PAYMENT"
ISSUE_AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
ISSUE_DUPLICATE = "DUPLICATE"
ISSUE_STATUS_MISMATCH = "STATUS_MISMATCH"


def reconcile(db: Session) -> dict:
    """Compare internal SOSYS audit records against the external Mock Bank ledger."""
    db.query(SOSYSLegacyLog).filter_by(source="BANK_LEDGER_ONLY").delete()
    db.commit()

    sosys_logs = db.query(SOSYSLegacyLog).all()
    bank_rows = fetch_bank_payment_ledger()

    sosys_key_counts: dict[str, int] = {}
    for log in sosys_logs:
        key = sosys_key(log)
        sosys_key_counts[key] = sosys_key_counts.get(key, 0) + 1

    bank_by_gateway_ref = {
        row["gateway_ref_id"]: row
        for row in bank_rows
        if row.get("gateway_ref_id")
    }
    bank_by_composite = {
        composite_key(row.get("batch_code"), row.get("claim_code")): row
        for row in bank_rows
        if row.get("batch_code") and row.get("claim_code")
    }
    bank_by_claim = {
        row["claim_code"]: row
        for row in bank_rows
        if row.get("claim_code")
    }

    matched_bank_keys: set[str] = set()

    for log in sosys_logs:
        key = sosys_key(log)
        if sosys_key_counts.get(key, 0) > 1:
            mark(
                log,
                MatchStatus.FLAGGED.value,
                ISSUE_DUPLICATE,
                f"Duplicate SOSYS audit entry for {log.claim_code}.",
            )
            continue

        bank_row = find_bank_row(log, bank_by_gateway_ref, bank_by_composite, bank_by_claim)
        if not bank_row:
            mark(
                log,
                MatchStatus.UNMATCHED.value,
                ISSUE_MISSING_PAYMENT,
                "Missing payment: SOSYS audit ledger has this payment, but the Mock Bank ledger does not.",
            )
            continue

        matched_bank_keys.add(bank_key(bank_row))
        if bank_row.get("status") != "SUCCESS":
            mark(
                log,
                MatchStatus.FLAGGED.value,
                ISSUE_STATUS_MISMATCH,
                f"Status mismatch: SOSYS expects paid, but bank status is {bank_row.get('status')}.",
            )
            continue

        bank_amount = float(bank_row.get("amount") or 0)
        if abs(float(log.amount or 0) - bank_amount) > 0.01:
            mark(
                log,
                MatchStatus.FLAGGED.value,
                ISSUE_AMOUNT_MISMATCH,
                f"Amount mismatch: SOSYS={log.amount}, bank={bank_amount}, difference={abs(float(log.amount or 0) - bank_amount):.2f} NPR.",
            )
        else:
            mark(log, MatchStatus.MATCHED.value, ISSUE_MATCHED, "SOSYS audit ledger and Mock Bank ledger match.")

    for row in bank_rows:
        if bank_key(row) in matched_bank_keys:
            continue
        if row.get("status") != "SUCCESS":
            continue
        db.add(SOSYSLegacyLog(
            claim_code=row.get("claim_code") or row.get("gateway_ref_id") or "UNKNOWN",
            health_facility=row.get("health_facility") or "Unknown",
            amount=float(row.get("amount") or 0),
            batch_id=row.get("batch_id"),
            batch_code=row.get("batch_code"),
            gateway_ref_id=row.get("gateway_ref_id"),
            payment_date=(row.get("processed_at") or "")[:10],
            sosys_status="BANK_ONLY",
            source="BANK_LEDGER_ONLY",
            match_status=MatchStatus.UNMATCHED.value,
            issue_type=ISSUE_GHOST_PAYMENT,
            notes="Ghost payment: Mock Bank ledger has this payment, but the SOSYS audit ledger does not.",
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


def find_bank_row(
    log: SOSYSLegacyLog,
    by_gateway_ref: dict[str, dict],
    by_composite: dict[str, dict],
    by_claim: dict[str, dict],
) -> dict | None:
    if log.gateway_ref_id and log.gateway_ref_id in by_gateway_ref:
        return by_gateway_ref[log.gateway_ref_id]
    if log.batch_code:
        row = by_composite.get(composite_key(log.batch_code, log.claim_code))
        if row:
            return row
    return by_claim.get(log.claim_code)


def sosys_key(log: SOSYSLegacyLog) -> str:
    if log.gateway_ref_id:
        return f"ref:{log.gateway_ref_id}"
    if log.batch_code:
        return composite_key(log.batch_code, log.claim_code)
    return f"claim:{log.claim_code}"


def bank_key(row: dict) -> str:
    if row.get("gateway_ref_id"):
        return f"ref:{row['gateway_ref_id']}"
    if row.get("batch_code"):
        return composite_key(row.get("batch_code"), row.get("claim_code"))
    return f"claim:{row.get('claim_code')}"


def composite_key(batch_code: str | None, claim_code: str | None) -> str:
    return f"batch:{batch_code or ''}:claim:{claim_code or ''}"


def mark(log: SOSYSLegacyLog, match_status: str, issue_type: str, notes: str) -> None:
    log.match_status = match_status
    log.issue_type = issue_type
    log.notes = notes


def build_summary(db: Session) -> dict:
    """Return status totals plus actionable reconciliation insight counts."""
    missing_filter = or_(
        SOSYSLegacyLog.issue_type == ISSUE_MISSING_PAYMENT,
        SOSYSLegacyLog.issue_type == "MISSING_IN_SOSYS",
    )
    missing_count = db.query(SOSYSLegacyLog).filter(missing_filter).count()
    return {
        "matched": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.MATCHED.value).count(),
        "unmatched": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.UNMATCHED.value).count(),
        "flagged": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.FLAGGED.value).count(),
        "total": db.query(SOSYSLegacyLog).count(),
        "ghost_payments": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_GHOST_PAYMENT).count(),
        "missing_in_sosys": missing_count,
        "missing_payments": missing_count,
        "amount_mismatches": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_AMOUNT_MISMATCH).count(),
        "duplicates": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_DUPLICATE).count(),
        "status_mismatches": db.query(SOSYSLegacyLog).filter_by(issue_type=ISSUE_STATUS_MISMATCH).count(),
    }
