"""Mock SOSYS export helpers for reconciliation demos."""
import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Claim, ClaimStatus, PaymentTransaction, SOSYSLegacyLog, TransactionStatus


CSV_FIELDS = ["claim_code", "health_facility", "amount", "payment_date", "status"]


def rows_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
    return output.getvalue()


def parse_sosys_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    return [
        {
            "claim_code": row.get("claim_code", "").strip(),
            "health_facility": row.get("health_facility", "").strip(),
            "amount": float(row.get("amount", 0) or 0),
            "payment_date": row.get("payment_date", "").strip(),
            "status": row.get("status", "").strip() or row.get("sosys_status", "").strip(),
        }
        for row in reader
    ]


def replace_sosys_logs(db: Session, rows: list[dict]) -> int:
    db.query(SOSYSLegacyLog).delete()
    db.commit()

    for row in rows:
        db.add(SOSYSLegacyLog(
            claim_code=row["claim_code"],
            health_facility=row["health_facility"],
            amount=float(row["amount"]),
            payment_date=row.get("payment_date", ""),
            sosys_status=row.get("status", ""),
        ))

    db.commit()
    return len(rows)


def build_mock_sosys_rows(db: Session, scenario: str = "mixed") -> list[dict]:
    """Build a deterministic SOSYS-style export from the current Samanvaya ledger."""
    scenario = (scenario or "mixed").lower()
    successful_txs = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.status == TransactionStatus.SUCCESS.value)
        .order_by(PaymentTransaction.created_at.asc())
        .all()
    )

    rows: list[dict] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if scenario == "clean":
        for tx in successful_txs:
            rows.append(_row_from_tx(tx))
        return rows

    # 1-2 clean matches prove the happy path.
    for tx in successful_txs[:2]:
        rows.append(_row_from_tx(tx))

    # Amount mismatch: same claim code, different amount.
    if len(successful_txs) >= 3:
        tx = successful_txs[2]
        rows.append(_row_from_tx(tx, amount=float(tx.amount) + 750.0))

    # Duplicate payment: same claim appears twice in legacy SOSYS.
    if len(successful_txs) >= 4:
        tx = successful_txs[3]
        rows.append(_row_from_tx(tx))
        rows.append(_row_from_tx(tx, payment_date=today))

    # Missing-in-SOSYS is created by omitting the 5th success transaction.
    if len(successful_txs) > 5:
        for tx in successful_txs[5:]:
            rows.append(_row_from_tx(tx))

    # SOSYS says paid, but Samanvaya has no claim at all.
    rows.append({
        "claim_code": "CLM-SOSYS-GHOST-001",
        "health_facility": "Legacy District Hospital",
        "amount": 18250.0,
        "payment_date": today,
        "status": "PAID",
    })

    # SOSYS says paid for a real approved claim that was never sent to payment.
    approved_claim = (
        db.query(Claim)
        .filter(Claim.status == ClaimStatus.APPROVED.value)
        .order_by(Claim.approved_date.asc(), Claim.claim_code.asc())
        .first()
    )
    if approved_claim:
        rows.append({
            "claim_code": approved_claim.claim_code,
            "health_facility": approved_claim.health_facility,
            "amount": approved_claim.approved_amount,
            "payment_date": today,
            "status": "PAID",
        })

    return rows


def _row_from_tx(
    tx: PaymentTransaction,
    amount: float | None = None,
    payment_date: str | None = None,
) -> dict:
    claim = tx.claim
    tx_date = tx.created_at.strftime("%Y-%m-%d") if tx.created_at else ""
    return {
        "claim_code": claim.claim_code if claim else tx.claim_id,
        "health_facility": claim.health_facility if claim else "Unknown",
        "amount": float(tx.amount if amount is None else amount),
        "payment_date": payment_date or tx_date,
        "status": "PAID",
    }
