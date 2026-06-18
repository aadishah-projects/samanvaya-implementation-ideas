"""
Reconciliation matching algorithm — SOSYS legacy vs Samanvaya ledger.
"""
import logging
from .models import PaymentTransaction, SOSYSLegacyLog

logger = logging.getLogger(__name__)


def run_reconciliation() -> dict:
    """
    Match SOSYSLegacyLogs against PaymentTransactions.
    Returns summary counts.
    """
    sosys_logs = SOSYSLegacyLog.objects.all()
    if not sosys_logs.exists():
        return {"matched": 0, "unmatched": 0, "flagged": 0, "total": 0}

    # Build lookup: claim_code -> list of successful transaction amounts
    successful_txs = PaymentTransaction.objects.filter(status="SUCCESS")
    claim_tx_map = {}
    for tx in successful_txs:
        code = None
        if tx.claim and hasattr(tx.claim, 'code'):
            code = tx.claim.code
        if code:
            claim_tx_map.setdefault(code, []).append(float(tx.amount))

    # Check for duplicates in SOSYS logs
    sosys_code_counts = {}
    for log in sosys_logs:
        sosys_code_counts[log.claim_code] = sosys_code_counts.get(log.claim_code, 0) + 1

    matched = 0
    unmatched = 0
    flagged = 0

    for log in sosys_logs:
        txs = claim_tx_map.get(log.claim_code, [])

        # Duplicate in SOSYS
        if sosys_code_counts.get(log.claim_code, 0) > 1:
            log.match_status = "FLAGGED"
            log.notes = (
                f"Duplicate payment: claim {log.claim_code} appears "
                f"{sosys_code_counts[log.claim_code]} times in SOSYS."
            )
            flagged += 1
            log.save()
            continue

        if not txs:
            log.match_status = "UNMATCHED"
            log.notes = "No matching payment found in Samanvaya ledger."
            unmatched += 1
            log.save()
            continue

        samanvaya_amount = txs[0]
        if abs(float(log.amount) - samanvaya_amount) > 0.01:
            log.match_status = "FLAGGED"
            log.notes = (
                f"Amount mismatch: SOSYS={float(log.amount)}, "
                f"Samanvaya={samanvaya_amount}, "
                f"difference={abs(float(log.amount) - samanvaya_amount):.2f} NPR."
            )
            flagged += 1
        else:
            log.match_status = "MATCHED"
            log.notes = "Amounts match. Payment verified."
            matched += 1
        log.save()

    return {
        "matched": matched,
        "unmatched": unmatched,
        "flagged": flagged,
        "total": sosys_logs.count(),
    }
