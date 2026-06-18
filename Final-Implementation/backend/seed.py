"""Seed the database with realistic Nepali demo data."""
import argparse
from datetime import datetime, timezone, timedelta
from database import engine, SessionLocal, Base
from models import (
    BatchStatus,
    Claim,
    ClaimStatus,
    GatewayConfig,
    PaymentBatch,
    PaymentTransaction,
    SOSYSLegacyLog,
    TransactionStatus,
)

HOSPITALS = [
    "Bir Hospital",
    "Civil Hospital",
    "Patan Hospital",
    "Nepal Medical College",
    "Grande International Hospital",
]

INSUREE_NAMES = [
    "Ram Bahadur Thapa", "Sita Kumari Shrestha", "Hari Prasad Pokharel",
    "Gita Devi Maharjan", "Krishna Bahadur Gurung", "Anita Tamang",
    "Bijay Rai", "Kamala Basnet", "Deepak Adhikari", "Sunita Lama",
    "Prakash Karki", "Mina Poudel", "Suresh Magar", "Radha Khadka",
    "Narayan Joshi", "Laxmi Bhandari", "Gopal Tharu", "Sarita Chaudhary",
    "Madhav Subedi", "Rekha KC",
]

CLAIMS_DATA = [
    ("CLM-2024-001", 0, 0, 45000, 42000),
    ("CLM-2024-002", 1, 1, 12500, 12500),
    ("CLM-2024-003", 2, 2, 78000, 75000),
    ("CLM-2024-004", 3, 3, 8500, 8500),
    ("CLM-2024-005", 4, 4, 125000, 120000),
    ("CLM-2024-006", 0, 5, 33000, 33000),
    ("CLM-2024-007", 1, 6, 5600, 5600),
    ("CLM-2024-008", 2, 7, 92000, 88000),
    ("CLM-2024-009", 3, 8, 15000, 15000),
    ("CLM-2024-010", 4, 9, 67000, 65000),
    ("CLM-2024-011", 0, 10, 22000, 22000),
    ("CLM-2024-012", 1, 11, 48000, 45000),
    ("CLM-2024-013", 2, 12, 9800, 9800),
    ("CLM-2024-014", 3, 13, 150000, 145000),
    ("CLM-2024-015", 4, 14, 37000, 37000),
    ("CLM-2024-016", 0, 15, 28500, 28500),
    ("CLM-2024-017", 1, 16, 71000, 68000),
    ("CLM-2024-018", 2, 17, 11000, 11000),
    ("CLM-2024-019", 3, 18, 84000, 80000),
    ("CLM-2024-020", 4, 19, 19500, 19500),
]

# First 5 are PROCESSED (already paid), rest are APPROVED (ready to pay)
PROCESSED_INDICES = {0, 3, 6, 12, 17}


def _clear_demo_data(db):
    db.query(SOSYSLegacyLog).delete()
    db.query(PaymentTransaction).delete()
    db.query(PaymentBatch).delete()
    db.query(GatewayConfig).delete()
    db.query(Claim).delete()
    db.commit()


def seed(reset: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if reset:
        _clear_demo_data(db)

    existing = db.query(Claim).first()
    if existing:
        claim_count = db.query(Claim).count()
        print("Database already seeded. Skipping.")
        db.close()
        return {"seeded": False, "claims": claim_count}

    base_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
    processed_claims = []

    for i, (code, hosp_idx, name_idx, claimed, approved) in enumerate(CLAIMS_DATA):
        status = ClaimStatus.PROCESSED.value if i in PROCESSED_INDICES else ClaimStatus.APPROVED.value
        claim = Claim(
            claim_code=code,
            health_facility=HOSPITALS[hosp_idx],
            insuree_name=INSUREE_NAMES[name_idx],
            claimed_amount=float(claimed),
            approved_amount=float(approved),
            status=status,
            approved_date=base_date + timedelta(days=i),
        )
        db.add(claim)
        if status == ClaimStatus.PROCESSED.value:
            processed_claims.append(claim)

    # Seed gateway config
    gc = GatewayConfig(
        name="mock_bank",
        is_active=True,
        config={"base_url": "http://localhost:8001"},
    )
    db.add(gc)
    db.flush()

    if processed_claims:
        historical_batch = PaymentBatch(
            total_amount=sum(c.approved_amount for c in processed_claims),
            claim_count=len(processed_claims),
            status=BatchStatus.DONE.value,
            created_at=base_date - timedelta(days=1),
        )
        db.add(historical_batch)
        db.flush()

        for claim in processed_claims:
            db.add(PaymentTransaction(
                batch_id=historical_batch.id,
                claim_id=claim.id,
                amount=claim.approved_amount,
                status=TransactionStatus.SUCCESS.value,
                idempotency_key=f"HIST-{claim.claim_code}",
                gateway_name="mock_bank",
                gateway_ref_id=f"HIST-{claim.claim_code}",
                raw_request_log={
                    "source": "seed",
                    "claim_code": claim.claim_code,
                    "recipient": claim.health_facility,
                    "amount": claim.approved_amount,
                },
                raw_response_log={
                    "source": "seed",
                    "status": "SUCCESS",
                    "note": "Historical processed claim seeded for demo continuity.",
                },
                webhook_received_at=claim.approved_date,
                created_at=claim.approved_date,
                updated_at=claim.approved_date,
            ))

    db.commit()
    claim_count = db.query(Claim).count()
    tx_count = db.query(PaymentTransaction).count()
    db.close()
    print(f"Seeded {claim_count} claims, {tx_count} historical transactions, and 1 gateway config.")
    return {"seeded": True, "claims": claim_count, "transactions": tx_count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Samanvaya demo data.")
    parser.add_argument("--reset", action="store_true", help="Clear existing demo data before seeding.")
    args = parser.parse_args()
    seed(reset=args.reset)
