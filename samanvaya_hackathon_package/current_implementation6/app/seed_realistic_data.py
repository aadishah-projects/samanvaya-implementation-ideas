import psycopg2
import random
import uuid
from datetime import date, timedelta

try:
    from .config import DB_CONFIG
except ImportError:
    from config import DB_CONFIG

random.seed(42)

HOSPITALS = [
    "Bir Hospital", "Patan Hospital", "TUTH",
    "Grande International Hospital", "Norvic International",
    "Om Hospital", "Nepal Medical College", "Dhulikhel Hospital",
    "Medicare Hospital", "B&B Hospital", "Alka Hospital",
    "HAMS Hospital", "Vayodha Hospital", "Neuro Hospital",
    "Kathmandu Medical College", "Chitwan Medical College",
    "Biratnagar Eye Hospital", "Pokhara Academy of Health Sciences",
    "Manipal Teaching Hospital", "Scheer Memorial Hospital",
]

DISTRICTS = [
    "Kathmandu", "Lalitpur", "Bhaktapur", "Kaski", "Chitwan",
    "Morang", "Sunsari", "Banke", "Kailali", "Rupandehi",
    "Dhanusa", "Jhapa", "Nawalparasi", "Surkhet", "Dolakha",
]


def generate_claims(n=50):
    claims = []
    for i in range(1, n + 1):
        base_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 180))
        claims.append({
            "uuid": str(uuid.uuid4()),
            "code": f"CLM{i:05d}",
            "date_claimed": base_date,
            "amount_claimed": round(random.uniform(2000, 150000), 2),
            "hospital_name": random.choice(HOSPITALS),
            "district": random.choice(DISTRICTS),
            "status_code": 4,
        })
    return claims


def generate_payments(claims):
    payments = []
    for index, claim in enumerate(claims, start=1):
        if index <= 12:
            continue
        amount_paid = claim["amount_claimed"]
        status = "paid"
        if 13 <= index <= 21:
            amount_paid = round(claim["amount_claimed"] * random.uniform(0.3, 0.9), 2)
            status = "paid"
        elif 22 <= index <= 26:
            amount_paid = claim["amount_claimed"]
            status = "pending"
        payments.append({
            "transaction_id": str(uuid.uuid4())[:12],
            "claim_code": claim["code"],
            "amount_paid": amount_paid,
            "payment_date": claim["date_claimed"] + timedelta(days=random.randint(1, 30)),
            "status": status,
        })
    return payments


def seed():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("ALTER TABLE staging_openimis_claims ADD COLUMN IF NOT EXISTS district TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS district TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS amount_variance NUMERIC;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS payment_status TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS payment_count INT DEFAULT 0;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS reconciliation_reason TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS risk_level TEXT;")
    cur.execute("TRUNCATE TABLE staging_openimis_claims CASCADE;")
    cur.execute("TRUNCATE TABLE staging_sosys_payments CASCADE;")
    cur.execute("TRUNCATE TABLE reconciled_view;")

    claims = generate_claims(50)
    payments = generate_payments(claims)

    for c in claims:
        cur.execute("""
            INSERT INTO staging_openimis_claims (uuid, code, date_claimed, amount_claimed, hospital_name, district, status_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            c["uuid"],
            c["code"],
            c["date_claimed"],
            c["amount_claimed"],
            c["hospital_name"],
            c["district"],
            c["status_code"],
        ))

    for p in payments:
        cur.execute("""
            INSERT INTO staging_sosys_payments (transaction_id, claim_code, amount_paid, payment_date, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (p["transaction_id"], p["claim_code"], p["amount_paid"], p["payment_date"], p["status"]))

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM staging_openimis_claims")
    claim_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM staging_sosys_payments")
    pay_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    print(f"Seeded {claim_count} claims and {pay_count} payments into staging tables.")
    print("Anomalies introduced:")
    total = len(claims)
    missing = total - len(payments)
    claim_lookup = {c["code"]: c["amount_claimed"] for c in claims}
    mismatches = sum(
        1 for p in payments
        if p["status"] == "paid" and p["amount_paid"] != claim_lookup.get(p["claim_code"])
    )
    pending = sum(1 for p in payments if p["status"] == "pending")
    print(f"  - {missing} MISSING_PAYMENT (no matching payment)")
    print(f"  - {mismatches} AMOUNT_MISMATCH (amount_paid != amount_claimed)")
    print(f"  - {pending} STATUS_PENDING")


if __name__ == "__main__":
    seed()
