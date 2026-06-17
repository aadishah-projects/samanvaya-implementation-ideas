import psycopg2
import requests

SOSYS_API_URL = "http://localhost:8001/fhir/Claim"

def extract_and_load():
    print("Extracting payments from SOSYS/Mojaloop REST API...")
    try:
        response = requests.get(SOSYS_API_URL)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Failed to connect to SOSYS: {e}")
        return

    payments = data.get('entry', [])
    print(f"Fetched {len(payments)} payments. Loading to Postgres...")

    conn = psycopg2.connect(
        dbname="samanvaya",
        user="postgres",
        password="secret",
        host="localhost",
        port=5433
    )
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE staging_sosys_payments;")

    for entry in payments:
        res = entry['resource']
        cur.execute("""
            INSERT INTO staging_sosys_payments (transaction_id, claim_code, amount_paid, payment_date, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            res['id'],
            res['id'],
            float(res['total']['value']),
            res['created'],
            'paid'
        ))

    conn.commit()
    cur.close()
    conn.close()
    print("SOSYS data successfully loaded into staging table!")

if __name__ == "__main__":
    extract_and_load()
