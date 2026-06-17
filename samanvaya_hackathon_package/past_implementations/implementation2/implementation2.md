This is a massive milestone! You are now transitioning from a "toy prototype" to a **production-grade architecture**. 

Before we start, **a quick note on your mentor's Mojaloop suggestion:** Mojaloop is an incredible enterprise payment switch, but setting up the actual Mojaloop infrastructure (Kafka, Docker Swarm, multiple microservices) will eat your entire hackathon timeline. Your guide explicitly advises **mocking SOSYS** for this exact reason. We will architect our system so it *could* plug into Mojaloop in the future, but for now, we will mock the payment ledger in a real database to keep your momentum going. Judges respect pragmatic scoping!

We are now executing **Phases 1 through 4** of your guide. We are replacing your CSV files with a real **PostgreSQL Database** to simulate OpenIMIS and SOSYS.

Here is your step-by-step guide to Version 4.

---

### 🗄️ Step 1: Spin up a Real Database
Instead of the massive OpenIMIS Docker stack (which can take hours to debug), we will run a single, clean PostgreSQL database that holds both the OpenIMIS and SOSYS tables.

Open your terminal and run this Docker command to start a Postgres database:
```bash
docker run --name samanvaya-db -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=samanvaya -p 5432:5432 -d postgres:15
```
*(This creates a database named `samanvaya` running on port 5432).*

---

### 📦 Step 2: Install Database & Data Generation Libraries
We need libraries to talk to Postgres and generate realistic fake data. Update your terminal:

```bash
pip install psycopg2-binary sqlalchemy faker
```

---

### 🌱 Step 3: Seed the "Real" Data (Phase 3)
We need to create the tables and generate ~300 realistic claims, deliberately injecting 10-15% errors (missing payments, wrong amounts) just like your guide suggests.

Create a new file called **`seed_data.py`** and paste this exact code:

```python
import psycopg2
import psycopg2.extras
from faker import Faker
import random

# 1. Connect to our Postgres DB
conn = psycopg2.connect(dbname="samanvaya", user="postgres", password="secret", host="localhost")
cur = conn.cursor()

# 2. Create the OpenIMIS and SOSYS tables
cur.execute("""
CREATE TABLE IF NOT EXISTS openimis_claims (
    claim_id TEXT PRIMARY KEY,
    hospital_name TEXT,
    district TEXT,
    amount_claimed NUMERIC,
    claim_date DATE,
    status TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sosys_payments (
    payment_id TEXT PRIMARY KEY,
    claim_id TEXT,
    amount_paid NUMERIC,
    payment_date DATE,
    status TEXT
);
""")
conn.commit()

# 3. Generate Synthetic Data
fake = Faker()
Faker.seed(42)
random.seed(42)

hospitals = ["Bir Hospital", "Patan Hospital", "Teaching Hospital", "Norvic Hospital", "TU Teaching Hospital"]
districts = ["Kathmandu", "Lalitpur", "Bhaktapur", "Kavrepalanchok", "Chitwan"]

# Generate 300 Claims (OpenIMIS side)
claims_data = []
for i in range(1, 301):
    claims_data.append((
        f"C{i:04d}",
        random.choice(hospitals),
        random.choice(districts),
        random.randint(10000, 150000),
        fake.date_between(start_date='-6M', end_date='today'),
        'approved'
    ))

# Insert claims into DB
psycopg2.extras.execute_values(
    cur, "INSERT INTO openimis_claims (claim_id, hospital_name, district, amount_claimed, claim_date, status) VALUES %s", claims_data
)
conn.commit()

# Generate Payments (SOSYS side) with deliberate errors
payments_data = []
payment_id = 1
for claim in claims_data:
    claim_id, hospital, district, amount, c_date, status = claim
    
    # 10% chance of MISSING payment (Red)
    if random.random() < 0.10:
        continue
        
    paid_amount = amount
    pay_status = 'paid'
    
    # 5% chance of AMOUNT MISMATCH (Red/Yellow)
    if random.random() < 0.05:
        paid_amount = int(amount * random.uniform(0.7, 0.95))
        pay_status = 'partial'
        
    # 5% chance of STATUS PENDING (Yellow)
    elif random.random() < 0.05:
        pay_status = 'pending'

    payments_data.append((
        f"P{payment_id:04d}",
        claim_id,
        paid_amount,
        fake.date_between(start_date=c_date, end_date='today'),
        pay_status
    ))
    payment_id += 1

# Insert payments into DB
psycopg2.extras.execute_values(
    cur, "INSERT INTO sosys_payments (payment_id, claim_id, amount_paid, payment_date, status) VALUES %s", payments_data
)
conn.commit()
cur.close()
conn.close()

print("✅ Database seeded with 300 OpenIMIS claims and ~250 SOSYS payments (with deliberate errors)!")
```

Run it once to populate your database:
```bash
python seed_data.py
```

---

### ⚙️ Step 4: Upgrade FastAPI to use the Database (Phase 4)
Now we update your `main.py` to stop reading CSVs and start querying the real PostgreSQL database using Pandas' `read_sql` function.

Open **`main.py`** and replace the entire contents with this:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
from sqlalchemy import create_engine

app = FastAPI()

# Connect FastAPI to our Postgres Database
DATABASE_URL = "postgresql://postgres:secret@localhost:5432/samanvaya"
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
```

---

### 🚀 Step 5: Run Your Real-World App!
Start your FastAPI server just like before:

```bash
uvicorn main:app --reload
```

Open your browser to **http://127.0.0.1:8000**.

Click **"Run Reconciliation Engine"**. 
You will now see a beautiful dashboard populated with **300 real database records**, complete with a summary counter at the top showing exactly how many claims are missing, mismatched, or pending!

### 🎯 What you just achieved:
1. You moved off CSVs into a **Relational Database (PostgreSQL)**.
2. You simulated **OpenIMIS** and **SOSYS** with realistic, messy data.
3. Your FastAPI backend is now executing SQL queries and running Pandas dataframes in memory.
4. You added the `district` column, perfectly setting yourself up for **Phase 7 (The Nepal District Heat Map)**.

Let me know when the dashboard is loading the 300 rows successfully. Once it is, we will immediately move to **Phase 5: Adding the AI Explanation Layer!**