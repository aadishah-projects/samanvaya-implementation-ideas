"""Reconciliation matching algorithm: SOSYS legacy vs Samanvaya ledger."""
from sqlalchemy.orm import Session

from models import (
    Claim,
    MatchStatus,
    PaymentTransaction,
    SOSYSLegacyLog,
    TransactionStatus,
)


def reconcile(db: Session) -> dict:
    """Match SOSYS legacy records against the Samanvaya ledger."""
    db.query(SOSYSLegacyLog).filter_by(sosys_status="MISSING_IN_SOSYS").delete()
    db.commit()

    sosys_logs = db.query(SOSYSLegacyLog).all()
    if not sosys_logs:
        return {"matched": 0, "unmatched": 0, "flagged": 0, "total": 0}

    claims = db.query(Claim).all()
    claim_by_code = {claim.claim_code: claim for claim in claims}
    claim_by_id = {claim.id: claim for claim in claims}

    claim_tx_map: dict[str, list[PaymentTransaction]] = {}
    for tx in db.query(PaymentTransaction).all():
        claim = claim_by_id.get(tx.claim_id)
        if claim:
            claim_tx_map.setdefault(claim.claim_code, []).append(tx)

    sosys_code_counts: dict[str, int] = {}
    for log in sosys_logs:
        sosys_code_counts[log.claim_code] = sosys_code_counts.get(log.claim_code, 0) + 1

    for log in sosys_logs:
        txs = claim_tx_map.get(log.claim_code, [])

        if sosys_code_counts.get(log.claim_code, 0) > 1:
            log.match_status = MatchStatus.FLAGGED.value
            log.notes = (
                f"Duplicate payment: claim {log.claim_code} appears "
                f"{sosys_code_counts[log.claim_code]} times in SOSYS."
            )
            continue

        if not txs:
            log.match_status = MatchStatus.UNMATCHED.value
            if log.claim_code in claim_by_code:
                log.notes = "Claim exists, but no payment transaction was found in the Samanvaya ledger."
            else:
                log.notes = "Ghost payment: SOSYS has a payment for a claim code not found in OpenIMIS/Samanvaya."
            continue

        successful_txs = [tx for tx in txs if tx.status == TransactionStatus.SUCCESS.value]
        if len(successful_txs) > 1:
            log.match_status = MatchStatus.FLAGGED.value
            log.notes = (
                f"Possible double payment: Samanvaya has {len(successful_txs)} "
                "successful transactions for this claim."
            )
            continue

        if not successful_txs:
            latest = sorted(txs, key=lambda tx: tx.updated_at or tx.created_at, reverse=True)[0]
            log.match_status = MatchStatus.FLAGGED.value
            log.notes = f"Status mismatch: SOSYS says paid, but Samanvaya status is {latest.status}."
            continue

        samanvaya_amount = successful_txs[0].amount
        if abs(log.amount - samanvaya_amount) > 0.01:
            log.match_status = MatchStatus.FLAGGED.value
            log.notes = (
                f"Amount mismatch: SOSYS={log.amount}, "
                f"Samanvaya={samanvaya_amount}, "
                f"difference={abs(log.amount - samanvaya_amount):.2f} NPR."
            )
        else:
            log.match_status = MatchStatus.MATCHED.value
            log.notes = "Amounts match. Payment verified."

    sosys_codes = {log.claim_code for log in sosys_logs}
    for code, txs in claim_tx_map.items():
        if code in sosys_codes:
            continue

        claim = claim_by_code[code]
        successful_txs = [tx for tx in txs if tx.status == TransactionStatus.SUCCESS.value]
        for tx in successful_txs:
            db.add(SOSYSLegacyLog(
                claim_code=code,
                health_facility=claim.health_facility,
                amount=tx.amount,
                payment_date=tx.created_at.strftime("%Y-%m-%d") if tx.created_at else "",
                sosys_status="MISSING_IN_SOSYS",
                match_status=MatchStatus.UNMATCHED.value,
                notes=(
                    "Orphan payment: Samanvaya shows SUCCESS, but the SOSYS "
                    "legacy file has no matching row."
                ),
            ))

    db.commit()
    return {
        "matched": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.MATCHED.value).count(),
        "unmatched": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.UNMATCHED.value).count(),
        "flagged": db.query(SOSYSLegacyLog).filter_by(match_status=MatchStatus.FLAGGED.value).count(),
        "total": db.query(SOSYSLegacyLog).count(),
    }
