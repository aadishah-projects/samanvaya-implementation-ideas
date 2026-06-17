import psycopg2

conn = psycopg2.connect(
    dbname="samanvaya",
    user="postgres",
    password="secret",
    host="localhost",
    port=5433
)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS staging_openimis_claims (
    uuid TEXT PRIMARY KEY,
    code TEXT,
    date_claimed DATE,
    amount_claimed NUMERIC,
    hospital_name TEXT,
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
    amount_claimed NUMERIC,
    amount_paid NUMERIC,
    reconciliation_status TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()
cur.close()
conn.close()
print("Staging tables created.")
