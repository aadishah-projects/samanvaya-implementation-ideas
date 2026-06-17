import os
import psycopg2
import psycopg2.extras
from faker import Faker
import random

# 1. Connect to our Postgres DB
DB_NAME = os.getenv("DB_NAME", "samanvaya")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secret")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
except psycopg2.OperationalError as exc:
    raise SystemExit(
        f"Unable to connect to Postgres at {DB_HOST}:{DB_PORT} as {DB_USER}. "
        f"Check that the server is running and the credentials are correct.\n{exc}"
    )

cur = conn.cursor()

# 2. Create the OpenIMIS and SOSYS tables
cur.execute("""
CREATE TABLE IF NOT EXISTS openimis_claims (
    claim_id TEXT PRIMARY KEY,
    hospital_name TEXT,
    district TEXT,
    amount_claimed NUMERIC,
    claim_date DATE,
    status TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sosys_payments (
    payment_id TEXT PRIMARY KEY,
    claim_id TEXT,
    amount_paid NUMERIC,
    payment_date DATE,
    status TEXT
);
""")
conn.commit()

# Clear any previous seeded data so the script is idempotent
cur.execute("TRUNCATE TABLE sosys_payments, openimis_claims;")
conn.commit()

# 3. Generate Synthetic Data
fake = Faker()
Faker.seed(42)
random.seed(42)

hospitals = ["Bir Hospital", "Patan Hospital", "Teaching Hospital", "Norvic Hospital", "TU Teaching Hospital"]
districts = ["Kathmandu", "Lalitpur", "Bhaktapur", "Kavrepalanchok", "Chitwan"]

# Generate 300 Claims (OpenIMIS side)
claims_data = []
for i in range(1, 301):
    claims_data.append((
        f"C{i:04d}",
        random.choice(hospitals),
        random.choice(districts),
        random.randint(10000, 150000),
        fake.date_between(start_date='-6M', end_date='today'),
        'approved'
    ))

# Insert claims into DB
psycopg2.extras.execute_values(
    cur, "INSERT INTO openimis_claims (claim_id, hospital_name, district, amount_claimed, claim_date, status) VALUES %s", claims_data
)
conn.commit()

# Generate Payments (SOSYS side) with deliberate errors
payments_data = []
payment_id = 1
for claim in claims_data:
    claim_id, hospital, district, amount, c_date, status = claim
    
    # 10% chance of MISSING payment (Red)
    if random.random() < 0.10:
        continue
        
    paid_amount = amount
    pay_status = 'paid'
    
    # 5% chance of AMOUNT MISMATCH (Red/Yellow)
    if random.random() < 0.05:
        paid_amount = int(amount * random.uniform(0.7, 0.95))
        pay_status = 'partial'
        
    # 5% chance of STATUS PENDING (Yellow)
    elif random.random() < 0.05:
        pay_status = 'pending'

    payments_data.append((
        f"P{payment_id:04d}",
        claim_id,
        paid_amount,
        fake.date_between(start_date=c_date, end_date='today'),
        pay_status
    ))
    payment_id += 1

# Insert payments into DB
psycopg2.extras.execute_values(
    cur, "INSERT INTO sosys_payments (payment_id, claim_id, amount_paid, payment_date, status) VALUES %s", payments_data
)
conn.commit()
cur.close()
conn.close()

print("✅ Database seeded with 300 OpenIMIS claims and ~250 SOSYS payments (with deliberate errors)!")