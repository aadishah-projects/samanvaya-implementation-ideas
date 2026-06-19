"""SOSYS CSV upload helpers."""
import csv
import io

from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import SOSYSLegacyLog


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
    db.query(SOSYSLegacyLog).filter(
        or_(
            SOSYSLegacyLog.source.is_(None),
            SOSYSLegacyLog.source.in_(["UPLOAD", "BANK_LEDGER_ONLY"]),
        )
    ).delete(synchronize_session=False)
    db.commit()

    for row in rows:
        db.add(SOSYSLegacyLog(
            claim_code=row["claim_code"],
            health_facility=row["health_facility"],
            amount=float(row["amount"]),
            payment_date=row.get("payment_date", ""),
            sosys_status=row.get("status", ""),
            source="UPLOAD",
        ))

    db.commit()
    return len(rows)
