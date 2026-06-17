Awesome job getting Version 1 running! You now have the core logic working. 

Let's move to **Version 2** and **Version 3**. I have broken them down into exact, copy-pasteable steps.

---

### 🚀 VERSION 2: Export Results to CSV

Right now, your script just prints to the screen. Let's make it save the results so an accountant or auditor could actually use the file.

**Step 1: Update `reconcile.py`**
Open your `reconcile.py` file. Delete the `print(...)` block at the very bottom and replace it with this:

```python
# Save the results to a new CSV file
merged.to_csv("reconciled_output.csv", index=False)
print("✅ Reconciliation complete! Check reconciled_output.csv")
```

**Step 2: Run it**
```bash
python reconcile.py
```

**Step 3: Verify**
Look in your `samanvaya/` folder. You will now see a new file called `reconciled_output.csv`. Open it in Excel or a text editor. You should see your 4 claims with the new `reconciliation_status` column.

*You just built an automated reporting tool.*

---

### 🌐 VERSION 3: FastAPI Backend + Web Dashboard

Now we are going to turn this into a real web application. We will build a backend (FastAPI) and a frontend (HTML/JS) in a single file to keep it simple and fast.

**Step 1: Install Web Libraries**
Update your `requirements.txt` to include FastAPI and Uvicorn (the server that runs FastAPI).

```text
pandas
fastapi
uvicorn
```

Install them:
```bash
pip install fastapi uvicorn
```

**Step 2: Create the Backend (`main.py`)**
Create a new file in your folder called `main.py` and paste this exact code:

```python
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
```

**Step 3: Run the Web Server**
Instead of running `python main.py`, we use `uvicorn` to start the server. Run this in your terminal:

```bash
uvicorn main:app --reload
```

**Step 4: Open Your Browser**
Open your web browser and go to:
👉 **http://127.0.0.1:8000**

You will see a clean web page. Click the **"Run Reconciliation"** button. 
The table will populate with your data, and the rows will be color-coded (Green, Yellow, Red) based on the reconciliation status!

---

### 🎯 What to do next
Once you get the web dashboard working in your browser, you have officially built **Version 3**. 

Let me know when it's running (or if you hit any errors), and we will move to **Version 4: Adding the AI Explanation Button!**