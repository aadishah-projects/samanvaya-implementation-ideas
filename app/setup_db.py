import psycopg2

try:
    from .config import DB_CONFIG
except ImportError:
    from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS staging_openimis_claims (
    uuid TEXT PRIMARY KEY,
    code TEXT,
    date_claimed DATE,
    amount_claimed NUMERIC,
    hospital_name TEXT,
    district TEXT,
    status_code INT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staging_sosys_payments (
    transaction_id TEXT PRIMARY KEY,
    claim_code TEXT,
    amount_paid NUMERIC,
    payment_date DATE,
    status TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reconciled_view (
    claim_code TEXT PRIMARY KEY,
    hospital_name TEXT,
    district TEXT,
    amount_claimed NUMERIC,
    amount_paid NUMERIC,
    amount_variance NUMERIC,
    payment_status TEXT,
    payment_count INT DEFAULT 0,
    reconciliation_status TEXT,
    reconciliation_reason TEXT,
    risk_level TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    claims_extracted INT DEFAULT 0,
    payments_extracted INT DEFAULT 0,
    reconciled_count INT DEFAULT 0,
    unreconciled_count INT DEFAULT 0,
    unreconciled_amount_npr NUMERIC DEFAULT 0,
    message TEXT
);
""")

cur.execute("ALTER TABLE staging_openimis_claims ADD COLUMN IF NOT EXISTS district TEXT;")
cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS district TEXT;")
cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS amount_variance NUMERIC;")
cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS payment_status TEXT;")
cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS payment_count INT DEFAULT 0;")
cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS reconciliation_reason TEXT;")
cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS risk_level TEXT;")
conn.commit()
cur.close()
conn.close()
print("Staging tables created.")
