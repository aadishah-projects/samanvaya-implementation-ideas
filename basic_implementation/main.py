from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd

app = FastAPI()

def run_reconciliation():
    # 1. Load Data
    claims = pd.read_csv("claims.csv")
    payments = pd.read_csv("payments.csv")

    # 2. Merge Data
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
    
    # 4. Clean data for JSON (replace NaN with "N/A" so it doesn't break the web app)
    merged = merged.fillna("N/A")
    
    # 5. Select only the columns we want to show
    final_df = merged[[
        "claim_id", 
        "hospital_name", 
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
                body { font-family: Arial, sans-serif; margin: 40px; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #f2f2f2; }
                button { padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #007BFF; color: white; border: none; border-radius: 5px;}
                button:hover { background-color: #0056b3; }
            </style>
        </head>
        <body>
            <h1>🇳🇵 Samanvaya Reconciliation Dashboard</h1>
            <button onclick="loadData()">Run Reconciliation</button>
            
            <table>
                <thead>
                    <tr>
                        <th>Claim ID</th>
                        <th>Hospital</th>
                        <th>Amount Claimed</th>
                        <th>Amount Paid</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="5" style="text-align:center;">Click the button to load data...</td></tr>
                </tbody>
            </table>

            <script>
                async function loadData() {
                    const response = await fetch('/api/reconcile');
                    const result = await response.json();
                    const tbody = document.getElementById('data-body');
                    tbody.innerHTML = '';
                    
                    result.data.forEach(row => {
                        // Traffic Light Colors
                        let color = 'white';
                        if (row.reconciliation_status === 'RECONCILED') color = '#d4edda'; // Green
                        else if (row.reconciliation_status === 'STATUS_PENDING') color = '#fff3cd'; // Yellow
                        else color = '#f8d7da'; // Red
                        
                        tbody.innerHTML += `
                            <tr style="background-color: ${color};">
                                <td>${row.claim_id}</td>
                                <td>${row.hospital_name}</td>
                                <td>NPR ${row.amount_claimed}</td>
                                <td>NPR ${row.amount_paid}</td>
                                <td><strong>${row.reconciliation_status}</strong></td>
                            </tr>
                        `;
                    });
                }
            </script>
        </body>
    </html>
    """