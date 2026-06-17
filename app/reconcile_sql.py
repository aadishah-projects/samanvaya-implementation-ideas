import psycopg2
from config import DB_CONFIG

def run_sql_reconciliation():
    print("Running SQL-based Reconciliation Engine...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE reconciled_view;")

    sql_query = """
    INSERT INTO reconciled_view (claim_code, hospital_name, amount_claimed, amount_paid, reconciliation_status)
    SELECT
        o.code AS claim_code,
        o.hospital_name,
        o.amount_claimed,
        COALESCE(s.amount_paid, 0) AS amount_paid,
        CASE
            WHEN s.transaction_id IS NULL THEN 'MISSING_PAYMENT'
            WHEN o.amount_claimed != s.amount_paid THEN 'AMOUNT_MISMATCH'
            WHEN s.status != 'paid' THEN 'STATUS_PENDING'
            ELSE 'RECONCILED'
        END AS reconciliation_status
    FROM staging_openimis_claims o
    LEFT JOIN staging_sosys_payments s
        ON o.code = s.claim_code;
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
