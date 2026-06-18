"""Seed the database with realistic Nepali demo data."""
import argparse
import random
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

MOCK_HOSPITALS = [
    "Bir Hospital",
    "Civil Hospital",
    "Patan Hospital",
    "Dhulikhel Hospital",
    "Bharatpur Hospital",
    "Koshi Hospital",
    "Lumbini Provincial Hospital",
    "Karnali Academy of Health Sciences",
    "Seti Provincial Hospital",
    "Mechi Provincial Hospital",
    "Nepal Medical College",
    "Grande International Hospital",
]

MOCK_INSUREE_NAMES = [
    "Aarav Adhikari", "Asmita Rai", "Bikash Shrestha", "Bina Thapa",
    "Chandra Gurung", "Deepa Lama", "Esha Karki", "Ganesh Basnet",
    "Hema Khadka", "Ishwor Poudel", "Januka Tamang", "Kamal Magar",
    "Lalita Chaudhary", "Manoj Bhandari", "Nirmala Joshi", "Om Prakash Yadav",
    "Prabina KC", "Ramesh Mahato", "Sabita Tharu", "Tek Bahadur Ale",
]

CLAIM_TYPE_PROFILES = [
    ("OPD", 1200, 8500),
    ("Diagnostics", 3500, 18500),
    ("Emergency", 9500, 42000),
    ("Maternity", 18000, 65000),
    ("Surgery", 45000, 160000),
    ("Dialysis", 12000, 36000),
    ("ICU", 80000, 240000),
    ("Referral", 25000, 90000),
]


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


def seed_mock_data(claim_count: int = 60, reset: bool = True):
    """Generate a larger deterministic dataset for stress-testing batches and reconciliation."""
    claim_count = max(5, min(int(claim_count), 250))
    rng = random.Random(20260618 + claim_count)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if reset:
        _clear_demo_data(db)

    existing_count = db.query(Claim).count()
    processed_claims = []
    base_date = datetime(2026, 1, 10, tzinfo=timezone.utc)

    for i in range(claim_count):
        sequence = existing_count + i + 1
        claim_type, min_amount, max_amount = CLAIM_TYPE_PROFILES[i % len(CLAIM_TYPE_PROFILES)]
        approved = float(rng.randrange(min_amount, max_amount, 500))
        claimed = approved + float(rng.randrange(0, 12000, 500))
        status = ClaimStatus.PROCESSED.value if i % 4 == 0 else ClaimStatus.APPROVED.value
        hospital = MOCK_HOSPITALS[(i + rng.randrange(len(MOCK_HOSPITALS))) % len(MOCK_HOSPITALS)]
        insuree = MOCK_INSUREE_NAMES[(i + rng.randrange(len(MOCK_INSUREE_NAMES))) % len(MOCK_INSUREE_NAMES)]

        claim = Claim(
            claim_code=f"CLM-MOCK-{sequence:04d}",
            health_facility=hospital,
            insuree_name=f"{insuree} ({claim_type})",
            claimed_amount=claimed,
            approved_amount=approved,
            status=status,
            approved_date=base_date + timedelta(hours=i * 6),
        )
        db.add(claim)
        if status == ClaimStatus.PROCESSED.value:
            processed_claims.append(claim)

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
                idempotency_key=f"MOCK-HIST-{claim.claim_code}",
                gateway_name="mock_bank",
                gateway_ref_id=f"MOCK-HIST-{claim.claim_code}",
                raw_request_log={
                    "source": "mock_seed",
                    "claim_code": claim.claim_code,
                    "recipient": claim.health_facility,
                    "amount": claim.approved_amount,
                },
                raw_response_log={
                    "source": "mock_seed",
                    "status": "SUCCESS",
                    "note": "Historical processed claim generated for reconciliation testing.",
                },
                webhook_received_at=claim.approved_date,
                created_at=claim.approved_date,
                updated_at=claim.approved_date,
            ))

    db.commit()

    total_claims = db.query(Claim).count()
    approved_count = db.query(Claim).filter_by(status=ClaimStatus.APPROVED.value).count()
    processed_count = db.query(Claim).filter_by(status=ClaimStatus.PROCESSED.value).count()
    tx_count = db.query(PaymentTransaction).count()
    total_approved_amount = sum(c.approved_amount for c in db.query(Claim).all())
    db.close()

    return {
        "seeded": True,
        "claims": total_claims,
        "approved": approved_count,
        "processed": processed_count,
        "transactions": tx_count,
        "total_approved_amount": total_approved_amount,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Samanvaya demo data.")
    parser.add_argument("--reset", action="store_true", help="Clear existing demo data before seeding.")
    args = parser.parse_args()
    seed(reset=args.reset)
