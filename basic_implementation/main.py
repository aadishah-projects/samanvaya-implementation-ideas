import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
from sqlalchemy import create_engine

app = FastAPI()

# Connect FastAPI to our Postgres Database
DB_NAME = os.getenv("DB_NAME", "samanvaya")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secret")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
engine = create_engine(DATABASE_URL)

def run_reconciliation():
    # 1. Load Data DIRECTLY from Postgres
    claims = pd.read_sql("SELECT * FROM openimis_claims", engine)
    payments = pd.read_sql("SELECT * FROM sosys_payments", engine)

    # 2. Merge Data (The Reconciliation Engine)
    merged = claims.merge(payments, on="claim_id", how="left", indicator=True)

    # 3. Classify
    def classify(row):
        if row["_merge"] == "left_only":
            return "MISSING_PAYMENT"
        if row["amount_claimed"] != row["amount_paid"]:
            return "AMOUNT_MISMATCH"
        if row["status_y"] != "paid":
            return "STATUS_PENDING"
        return "RECONCILED"

    merged["reconciliation_status"] = merged.apply(classify, axis=1)
    
    # 4. Clean data for JSON
    merged = merged.fillna("N/A")
    
    # 5. Select columns (Added 'district' for your future heat map!)
    final_df = merged[[
        "claim_id", 
        "hospital_name", 
        "district", 
        "amount_claimed", 
        "amount_paid", 
        "reconciliation_status"
    ]]
    
    return final_df.to_dict(orient="records")

# --- API ENDPOINT ---
@app.get("/api/reconcile")
def get_reconciliation():
    return {"data": run_reconciliation()}

# --- WEB DASHBOARD (HTML) ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <head>
            <title>Samanvaya Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #007BFF; color: white; }
                button { padding: 12px 24px; font-size: 16px; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px; font-weight: bold;}
                button:hover { background-color: #218838; }
                .stats { margin-top: 20px; font-size: 18px; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🇳🇵 Samanvaya: OpenIMIS ↔ SOSYS Reconciliation</h1>
            <button onclick="loadData()">Run Reconciliation Engine</button>
            <div id="stats" class="stats"></div>
            
            <table>
                <thead>
                    <tr>
                        <th>Claim ID</th>
                        <th>District</th>
                        <th>Hospital</th>
                        <th>Claimed (NPR)</th>
                        <th>Paid (NPR)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="6" style="text-align:center;">Click the button to query the database...</td></tr>
                </tbody>
            </table>

            <script>
                async function loadData() {
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
                                <td>${row.claim_id}</td>
                                <td>${row.district}</td>
                                <td>${row.hospital_name}</td>
                                <td>${row.amount_claimed}</td>
                                <td>${row.amount_paid}</td>
                                <td><strong>${row.reconciliation_status}</strong></td>
                            </tr>
                        `;
                    });
                    
                    document.getElementById('stats').innerHTML = `
                        🟢 Reconciled: ${counts.RECONCILED} | 
                        🔴 Missing: ${counts.MISSING_PAYMENT} | 
                        🔴 Mismatch: ${counts.AMOUNT_MISMATCH} | 
                        🟡 Pending: ${counts.STATUS_PENDING}
                    `;
                }
            </script>
        </body>
    </html>
    """