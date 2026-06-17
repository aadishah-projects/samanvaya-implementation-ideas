import psycopg2
import requests
from config import SOSYS_API_URL, SOSYS_HEADERS, USE_LIVE_API, DB_CONFIG

def extract_and_load():
    print(f"Extracting payments from SOSYS/Mojaloop API ({SOSYS_API_URL})...")
    try:
        if USE_LIVE_API:
            response = requests.get(SOSYS_API_URL, headers=SOSYS_HEADERS)
        else:
            response = requests.get(SOSYS_API_URL)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Failed to connect to SOSYS: {e}")
        return

    if USE_LIVE_API:
        transfers = data if isinstance(data, list) else []
        print(f"Fetched {len(transfers)} Mojaloop transfers.")
        entries = []
        for t in transfers:
            entries.append({
                "id": t.get("transferId", "unknown"),
                "claim_code": t.get("ilpPacket", "UNKNOWN"),
                "amount": t.get("amount", {}).get("amount", 0) if isinstance(t.get("amount"), dict) else 0,
                "created": t.get("createdDate", ""),
                "status": t.get("status", "unknown"),
            })
    else:
        payments = data.get('entry', [])
        print(f"Fetched {len(payments)} payments.")
        entries = []
        for entry in payments:
            res = entry['resource']
            entries.append({
                "id": res['id'],
                "claim_code": res['id'],
                "amount": float(res['total']['value']),
                "created": res['created'],
                "status": 'paid',
            })

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE staging_sosys_payments;")

    for e in entries:
        cur.execute("""
            INSERT INTO staging_sosys_payments (transaction_id, claim_code, amount_paid, payment_date, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            e["id"],
            e["claim_code"],
            e["amount"],
            e["created"],
            e["status"],
        ))

    conn.commit()
    cur.close()
    conn.close()
    print("SOSYS data successfully loaded into staging table!")

if __name__ == "__main__":
    extract_and_load()
