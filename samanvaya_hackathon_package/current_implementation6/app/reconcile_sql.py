import psycopg2

try:
    from .config import DB_CONFIG
except ImportError:
    from config import DB_CONFIG

def run_sql_reconciliation():
    print("Running SQL-based Reconciliation Engine...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS district TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS amount_variance NUMERIC;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS payment_status TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS payment_count INT DEFAULT 0;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS reconciliation_reason TEXT;")
    cur.execute("ALTER TABLE reconciled_view ADD COLUMN IF NOT EXISTS risk_level TEXT;")

    sql_query = """
    WITH payment_rollup AS (
        SELECT
            claim_code,
            COUNT(*) AS payment_count,
            SUM(amount_paid) AS amount_paid,
            CASE
                WHEN BOOL_OR(status != 'paid') THEN 'pending'
                ELSE 'paid'
            END AS payment_status
        FROM staging_sosys_payments
        GROUP BY claim_code
    )
    INSERT INTO reconciled_view (
        claim_code,
        hospital_name,
        district,
        amount_claimed,
        amount_paid,
        amount_variance,
        payment_status,
        payment_count,
        reconciliation_status,
        reconciliation_reason,
        risk_level,
        updated_at
    )
    SELECT
        o.code AS claim_code,
        o.hospital_name,
        COALESCE(o.district, 'Unknown') AS district,
        o.amount_claimed,
        COALESCE(s.amount_paid, 0) AS amount_paid,
        o.amount_claimed - COALESCE(s.amount_paid, 0) AS amount_variance,
        COALESCE(s.payment_status, 'missing') AS payment_status,
        COALESCE(s.payment_count, 0) AS payment_count,
        CASE
            WHEN s.claim_code IS NULL THEN 'MISSING_PAYMENT'
            WHEN s.payment_count > 1 THEN 'DUPLICATE_PAYMENT'
            WHEN s.payment_status != 'paid' THEN 'STATUS_PENDING'
            WHEN o.amount_claimed != s.amount_paid THEN 'AMOUNT_MISMATCH'
            ELSE 'RECONCILED'
        END AS reconciliation_status,
        CASE
            WHEN s.claim_code IS NULL THEN 'No SOSYS/Mojaloop payment was found for this approved OpenIMIS claim.'
            WHEN s.payment_count > 1 THEN 'Multiple payment records exist for one claim; possible duplicate payout.'
            WHEN s.payment_status != 'paid' THEN 'Payment exists but is not marked paid in SOSYS/Mojaloop.'
            WHEN o.amount_claimed != s.amount_paid THEN 'Claimed and paid amounts differ by NPR ' || ABS(o.amount_claimed - s.amount_paid)::TEXT || '.'
            ELSE 'Claim amount and payment amount match, and payment is marked paid.'
        END AS reconciliation_reason,
        CASE
            WHEN s.claim_code IS NULL THEN 'HIGH'
            WHEN s.payment_count > 1 THEN 'HIGH'
            WHEN o.amount_claimed != s.amount_paid AND ABS(o.amount_claimed - s.amount_paid) >= 10000 THEN 'HIGH'
            WHEN o.amount_claimed != s.amount_paid THEN 'MEDIUM'
            WHEN s.payment_status != 'paid' THEN 'MEDIUM'
            ELSE 'LOW'
        END AS risk_level,
        CURRENT_TIMESTAMP AS updated_at
    FROM staging_openimis_claims o
    LEFT JOIN payment_rollup s
        ON o.code = s.claim_code
    ON CONFLICT (claim_code) DO UPDATE SET
        hospital_name = EXCLUDED.hospital_name,
        district = EXCLUDED.district,
        amount_claimed = EXCLUDED.amount_claimed,
        amount_paid = EXCLUDED.amount_paid,
        amount_variance = EXCLUDED.amount_variance,
        payment_status = EXCLUDED.payment_status,
        payment_count = EXCLUDED.payment_count,
        reconciliation_status = EXCLUDED.reconciliation_status,
        reconciliation_reason = EXCLUDED.reconciliation_reason,
        risk_level = EXCLUDED.risk_level,
        updated_at = CURRENT_TIMESTAMP;
    """

    cur.execute(sql_query)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM reconciled_view;")
    count = cur.fetchone()[0]

    cur.close()
    conn.close()
    print(f"SQL Reconciliation complete! {count} claims processed and stored in database.")

if __name__ == "__main__":
    run_sql_reconciliation()
