from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests
from sqlalchemy import create_engine

app = FastAPI()

DATABASE_URL = "postgresql://postgres:secret@localhost:5433/samanvaya"
engine = create_engine(DATABASE_URL)

def fetch_openimis_claims():
    print("Fetching FHIR data from OpenIMIS...")
    try:
        response = requests.get("http://localhost:8001/fhir/Claim")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Failed to connect to FHIR server: {e}")
        return pd.DataFrame()

    claims_list = []
    for entry in data.get("entry", []):
        resource = entry["resource"]
        claims_list.append({
            "claim_id": resource["id"],
            "hospital_name": resource.get("provider", {}).get("display", "Unknown"),
            "amount_claimed": float(resource.get("total", {}).get("value", 0)),
            "claim_date": resource["created"],
            "status": "approved"
        })

    return pd.DataFrame(claims_list)

def fetch_sosys_payments():
    return pd.read_sql("SELECT * FROM sosys_payments", engine)

def run_reconciliation():
    claims = fetch_openimis_claims()
    if claims.empty:
        return []

    payments = fetch_sosys_payments()

    merged = claims.merge(payments, on="claim_id", how="left", indicator=True)

    def classify(row):
        if row["_merge"] == "left_only":
            return "MISSING_PAYMENT"
        if row["amount_claimed"] != row["amount_paid"]:
            return "AMOUNT_MISMATCH"
        if row["status_y"] != "paid":
            return "STATUS_PENDING"
        return "RECONCILED"

    merged["reconciliation_status"] = merged.apply(classify, axis=1)
    merged = merged.fillna("N/A")

    final_df = merged[[
        "claim_id", "hospital_name", "amount_claimed",
        "amount_paid", "reconciliation_status"
    ]]

    return final_df.to_dict(orient="records")

@app.get("/api/reconcile")
def get_reconciliation():
    return {"data": run_reconciliation()}

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <head>
            <title>Samanvaya: OpenIMIS (FHIR) + SOSYS</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                .badge { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; margin-right: 10px;}
                .badge-fhir { background: #e74c3c; }
                .badge-sosys { background: #f39c12; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden;}
                th, td { border: 1px solid #eee; padding: 15px; text-align: left; }
                th { background-color: #34495e; color: white; text-transform: uppercase; font-size: 14px;}
                button { padding: 12px 24px; font-size: 16px; cursor: pointer; background-color: #27ae60; color: white; border: none; border-radius: 5px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);}
                button:hover { background-color: #2ecc71; }
                .stats { margin-top: 20px; font-size: 16px; font-weight: 600; color: #555; }
            </style>
        </head>
        <body>
            <h1>Samanvaya Reconciliation Engine</h1>
            <p>
                <span class="badge badge-fhir">LIVE: OpenIMIS (FHIR API)</span>
                <span class="badge badge-sosys">MOCKED: SOSYS (PostgreSQL)</span>
            </p>

            <button onclick="loadData()">Run Reconciliation</button>
            <div id="stats" class="stats"></div>

            <table>
                <thead>
                    <tr>
                        <th>Claim ID</th>
                        <th>Hospital</th>
                        <th>Claimed (NPR)</th>
                        <th>Paid (SOSYS)</th>
                        <th>Reconciliation Status</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="5" style="text-align:center;">Click the button to query the FHIR API...</td></tr>
                </tbody>
            </table>

            <script>
                async function loadData() {
                    document.getElementById('stats').innerHTML = "Fetching FHIR Bundle from OpenIMIS...";
                    const response = await fetch('/api/reconcile');
                    const result = await response.json();
                    const tbody = document.getElementById('data-body');
                    tbody.innerHTML = '';

                    let counts = {RECONCILED: 0, MISSING_PAYMENT: 0, AMOUNT_MISMATCH: 0, STATUS_PENDING: 0};

                    result.data.forEach(row => {
                        counts[row.reconciliation_status]++;

                        let color = 'white';
                        if (row.reconciliation_status === 'RECONCILED') color = '#d4edda';
                        else if (row.reconciliation_status === 'STATUS_PENDING') color = '#fff3cd';
                        else color = '#f8d7da';

                        tbody.innerHTML += `
                            <tr style="background-color: ${color};">
                                <td><strong>${row.claim_id}</strong></td>
                                <td>${row.hospital_name}</td>
                                <td>${row.amount_claimed}</td>
                                <td>${row.amount_paid}</td>
                                <td><strong>${row.reconciliation_status}</strong></td>
                            </tr>
                        `;
                    });

                    document.getElementById('stats').innerHTML = `
                        Total FHIR Claims: ${result.data.length} |
                        Reconciled: ${counts.RECONCILED} |
                        Missing: ${counts.MISSING_PAYMENT} |
                        Mismatch: ${counts.AMOUNT_MISMATCH} |
                        Pending: ${counts.STATUS_PENDING}
                    `;
                }
            </script>
        </body>
    </html>
    """
