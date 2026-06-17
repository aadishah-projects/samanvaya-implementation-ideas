This is exactly the right mindset. Moving from a mocked database to the **actual OpenIMIS architecture** is what separates a "school project" from a "production-ready prototype." 

OpenIMIS is a massive, enterprise-grade Django application. It does **not** use simple REST APIs; it uses **GraphQL** for its data layer. 

Here is your step-by-step guide to integrating with the **real OpenIMIS GraphQL API** while keeping our mocked SOSYS database.

---

### 🐳 Step 1: Spin up the REAL OpenIMIS Backend
We are going to run the official OpenIMIS backend via Docker. 

*Note: This will take a few minutes to download the images and build.*

1. Open your terminal and clone the official repository:
   ```bash
   git clone https://github.com/openimis/openimis-be_py.git
   cd openimis-be_py
   ```
2. Start the Docker containers:
   ```bash
   docker-compose up -d
   ```
3. Wait until it finishes. You can check the logs to ensure it's running:
   ```bash
   docker-compose logs -f
   ```
   *(Press `Ctrl+C` to exit the logs once you see it's up).*

**Verify it's running:** Open your browser and go to **http://localhost:8000/api/graphql**. You should see the GraphiQL interface (a dark screen where you can type queries).

---

### 🔐 Step 2: Authenticate with OpenIMIS
OpenIMIS requires a JWT (JSON Web Token) to access its API. The default admin credentials for the local Docker setup are `admin` / `admin`.

We need to write a quick Python script to log in and get our token. 

Create a file called **`get_token.py`** in your `samanvaya/` folder:

```python
import requests

OPENIMIS_URL = "http://localhost:8000/api/graphql"

# 1. The GraphQL Mutation to log in
login_query = """
mutation {
  tokenAuth(username: "admin", password: "admin") {
    token
  }
}
"""

response = requests.post(OPENIMIS_URL, json={'query': login_query})
data = response.json()

if "errors" in data:
    print("❌ Login failed:", data["errors"])
else:
    token = data['data']['tokenAuth']['token']
    print("✅ Success! Your JWT Token is:")
    print(token)
    
    # Save it to a file so main.py can use it
    with open("openimis_token.txt", "w") as f:
        f.write(token)
```

Run it:
```bash
python get_token.py
```
*Copy the token it prints out. It is now saved in `openimis_token.txt`.*

---

### 📡 Step 3: Fetch REAL Claims via GraphQL
OpenIMIS uses a "Relay-style" GraphQL schema. This means data is nested inside `edges` and `node`. 

We need to update your **`main.py`** to stop reading from the fake Postgres `openimis_claims` table, and instead fetch directly from the real OpenIMIS API.

Open **`main.py`** and replace the entire file with this upgraded version:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests
from sqlalchemy import create_engine

app = FastAPI()

# --- CONFIGURATION ---
OPENIMIS_URL = "http://localhost:8000/api/graphql"
DATABASE_URL = "postgresql://postgres:secret@localhost:5432/samanvaya"
engine = create_engine(DATABASE_URL)

# Load the JWT token we generated
with open("openimis_token.txt", "r") as f:
    OPENIMIS_TOKEN = f.read().strip()

# --- 1. FETCH REAL OPENIMIS DATA (GraphQL) ---
def fetch_openimis_claims():
    # The GraphQL query to get approved claims from OpenIMIS
    query = """
    query {
      claims(first: 50, status: 4) {
        edges {
          node {
            uuid
            code
            dateClaimed
            claimed
            healthFacility {
              name
            }
          }
        }
      }
    }
    """
    
    headers = {"Authorization": f"JWT {OPENIMIS_TOKEN}"}
    response = requests.post(OPENIMIS_URL, json={'query': query}, headers=headers)
    data = response.json()
    
    if "errors" in data:
        print("❌ GraphQL Error:", data["errors"])
        return pd.DataFrame()

    # Parse the nested GraphQL "edges" and "node" structure
    claims_list = []
    for edge in data['data']['claims']['edges']:
        node = edge['node']
        claims_list.append({
            "claim_id": node['code'], # Using the human-readable code
            "hospital_name": node['healthFacility']['name'] if node['healthFacility'] else "Unknown",
            "amount_claimed": float(node['claimed']),
            "claim_date": node['dateClaimed'],
            "status": "approved" # We filtered by status: 4 (Processed/Approved)
        })
        
    return pd.DataFrame(claims_list)

# --- 2. FETCH MOCKED SOSYS DATA (Postgres) ---
def fetch_sosys_payments():
    # We still use our mocked SOSYS database for the payment side
    return pd.read_sql("SELECT * FROM sosys_payments", engine)

# --- 3. THE RECONCILIATION ENGINE ---
def run_reconciliation():
    print("🔄 Fetching REAL data from OpenIMIS GraphQL...")
    claims = fetch_openimis_claims()
    
    if claims.empty:
        return []

    print("🔄 Fetching MOCKED data from SOSYS Postgres...")
    payments = fetch_sosys_payments()

    # Merge them
    merged = claims.merge(payments, on="claim_id", how="left", indicator=True)

    # Classify
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
            <title>Samanvaya: OpenIMIS + SOSYS</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                .badge { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; margin-right: 10px;}
                .badge-openimis { background: #e74c3c; }
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
            <h1>🇳🇵 Samanvaya Reconciliation Engine</h1>
            <p>
                <span class="badge badge-openimis">LIVE: OpenIMIS (GraphQL)</span>
                <span class="badge badge-sosys">MOCKED: SOSYS (PostgreSQL)</span>
            </p>
            
            <button onclick="loadData()">Run Reconciliation</button>
            <div id="stats" class="stats"></div>
            
            <table>
                <thead>
                    <tr>
                        <th>Claim Code</th>
                        <th>Hospital (OpenIMIS)</th>
                        <th>Claimed (NPR)</th>
                        <th>Paid (SOSYS)</th>
                        <th>Reconciliation Status</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="5" style="text-align:center;">Click the button to query the live OpenIMIS API...</td></tr>
                </tbody>
            </table>

            <script>
                async function loadData() {
                    document.getElementById('stats').innerHTML = "⏳ Fetching data from OpenIMIS GraphQL API...";
                    const response = await fetch('/api/reconcile');
                    const result = await response.json();
                    const tbody = document.getElementById('data-body');
                    tbody.innerHTML = '';
                    
                    let counts = {RECONCILED: 0, MISSING_PAYMENT: 0, AMOUNT_MISMATCH: 0, STATUS_PENDING: 0};

                    result.data.forEach(row => {
                        counts[row.reconciliation_status]++;
                        
                        let color = 'white';
                        let statusText = row.reconciliation_status;
                        if (row.reconciliation_status === 'RECONCILED') color = '#d4edda'; 
                        else if (row.reconciliation_status === 'STATUS_PENDING') color = '#fff3cd'; 
                        else color = '#f8d7da'; 
                        
                        tbody.innerHTML += `
                            <tr style="background-color: ${color};">
                                <td><strong>${row.claim_id}</strong></td>
                                <td>${row.hospital_name}</td>
                                <td>${row.amount_claimed}</td>
                                <td>${row.amount_paid}</td>
                                <td><strong>${statusText}</strong></td>
                            </tr>
                        `;
                    });
                    
                    document.getElementById('stats').innerHTML = `
                        ✅ Total Fetched: ${result.data.length} | 
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
```

---

### 🧠 Step 4: Understand What Just Happened (The Architecture)

Look at what you just built. This is a **real-world enterprise integration pattern**:

1. **The Source of Truth (OpenIMIS):** Your Python backend is acting as an integration layer. It is hitting a live Django/GraphQL API, authenticating with a JWT token, and parsing a complex, nested JSON response (`edges -> node -> healthFacility -> name`).
2. **The Destination of Truth (SOSYS):** It is simultaneously querying a relational PostgreSQL database for the payment ledger.
3. **The Engine (Pandas):** It is pulling both disparate data formats (GraphQL JSON and SQL Relational) into memory, flattening them into Pandas DataFrames, and executing the reconciliation logic.
4. **The Presentation (FastAPI + HTML):** It is serving this unified, reconciled view to the browser.

### 🚀 Step 5: Run It!

Make sure your OpenIMIS Docker is still running (`docker-compose up -d` inside the `openimis-be_py` folder).

Then, in your `samanvaya/` folder, start your FastAPI app:
```bash
uvicorn main:app --reload
```

Go to **http://127.0.0.1:8000** and click **"Run Reconciliation"**.

You are now looking at **real claims generated by the actual OpenIMIS system**, reconciled against your mocked SOSYS ledger. 

### 🎯 What's Next?
Now that you have successfully integrated with the real OpenIMIS GraphQL API, you have conquered the hardest technical hurdle. 

Tell me when the dashboard successfully loads the real OpenIMIS data. Once it does, we will move to **Phase 5: Adding the AI Explanation Layer** to explain *why* these real claims are mismatched!