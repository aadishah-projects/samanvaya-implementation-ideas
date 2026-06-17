from datetime import datetime, timezone
from io import StringIO
import csv

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
from sqlalchemy import create_engine, text
from config import DB_CONFIG, USE_LIVE_API

app = FastAPI()

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
engine = create_engine(DATABASE_URL)

last_synced: datetime | None = None


def get_db_url():
    return DATABASE_URL


def run_reconciliation():
    df = pd.read_sql("SELECT * FROM reconciled_view ORDER BY claim_code", engine)
    return df.fillna("N/A").to_dict(orient="records")


@app.get("/api/last-synced")
def get_last_synced():
    return {"last_synced": last_synced.isoformat() if last_synced else None}


@app.post("/api/run-pipeline")
def run_pipeline():
    global last_synced
    try:
        from extract_openimis import extract_and_load as extract_openimis
        from extract_sosys import extract_and_load as extract_sosys
        from reconcile_sql import run_sql_reconciliation

        extract_openimis()
        extract_sosys()
        run_sql_reconciliation()
        last_synced = datetime.now(timezone.utc)
        return {"status": "ok", "message": "Pipeline completed successfully", "last_synced": last_synced.isoformat()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/export-csv")
def export_csv():
    df = pd.read_sql("SELECT * FROM reconciled_view ORDER BY claim_code", engine)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["claim_code", "hospital_name", "amount_claimed", "amount_paid", "reconciliation_status"])
    for _, row in df.iterrows():
        writer.writerow([row["claim_code"], row["hospital_name"], row["amount_claimed"], row["amount_paid"], row["reconciliation_status"]])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reconciled_claims.csv"},
    )


@app.get("/api/reconcile")
def get_reconciliation():
    data = run_reconciliation()
    total_unreconciled = sum(
        1 for r in data
        if r["reconciliation_status"] in ("MISSING_PAYMENT", "AMOUNT_MISMATCH", "STATUS_PENDING")
    )
    unreconciled_amount = sum(
        float(r["amount_claimed"]) for r in data
        if r["reconciliation_status"] in ("MISSING_PAYMENT", "AMOUNT_MISMATCH", "STATUS_PENDING")
        and r["amount_claimed"] != "N/A"
    )
    return {
        "data": data,
        "stats": {
            "total_unreconciled": total_unreconciled,
            "unreconciled_amount_npr": round(unreconciled_amount, 2),
        }
    }


live_badge = "LIVE" if USE_LIVE_API else "MOCK"

HTML_TEMPLATE = f"""
<html>
    <head>
        <title>Samanvaya: OpenIMIS + SOSYS Reconciliation Dashboard</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 30px; background: #f0f2f5; color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; color: white; }}
            .badge-live {{ background: #27ae60; }}
            .badge-mock {{ background: #e67e22; }}
            .badge-fhir {{ background: #e74c3c; }}
            .badge-sosys {{ background: #f39c12; }}
            .badge-etl {{ background: #8e44ad; }}
            .toolbar {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin: 20px 0; }}
            .toolbar button, .toolbar a {{ padding: 10px 20px; font-size: 14px; cursor: pointer; border: none; border-radius: 6px; font-weight: 600; text-decoration: none; display: inline-block; }}
            .btn-primary {{ background: #27ae60; color: white; }}
            .btn-primary:hover {{ background: #2ecc71; }}
            .btn-secondary {{ background: #2980b9; color: white; }}
            .btn-secondary:hover {{ background: #3498db; }}
            .btn-danger {{ background: #e74c3c; color: white; }}
            .btn-danger:hover {{ background: #ec7063; }}
            .btn-warning {{ background: #f39c12; color: white; }}
            .btn-warning:hover {{ background: #f1c40f; }}
            .stats-bar {{ display: flex; gap: 15px; flex-wrap: wrap; margin: 15px 0; }}
            .stat-card {{ background: white; border-radius: 8px; padding: 15px 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); flex: 1; min-width: 140px; text-align: center; }}
            .stat-card .number {{ font-size: 28px; font-weight: 700; display: block; }}
            .stat-card .label {{ font-size: 12px; text-transform: uppercase; color: #666; margin-top: 4px; }}
            .stat-green .number {{ color: #27ae60; }}
            .stat-yellow .number {{ color: #f39c12; }}
            .stat-red .number {{ color: #e74c3c; }}
            .stat-blue .number {{ color: #2980b9; }}
            .stat-highlight {{ background: #eafaf1; border-left: 4px solid #27ae60; }}
            .stat-highlight .number {{ color: #1a7a3a; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 10px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; }}
            th, td {{ border: 1px solid #eee; padding: 12px 15px; text-align: left; font-size: 13px; }}
            th {{ background-color: #34495e; color: white; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
            .synced-info {{ font-size: 13px; color: #666; margin: 10px 0; }}
            .status-badge {{ display: inline-block; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
            .status-reconciled {{ background: #d4edda; color: #155724; }}
            .status-missing {{ background: #f8d7da; color: #721c24; }}
            .status-mismatch {{ background: #f8d7da; color: #721c24; }}
            .status-pending {{ background: #fff3cd; color: #856404; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                Samanvaya Reconciliation Dashboard
                <span class="badge badge-{'live' if USE_LIVE_API else 'mock'}">{live_badge} API</span>
            </h1>
            <p>
                <span class="badge badge-fhir">OpenIMIS (GraphQL)</span>
                <span class="badge badge-sosys">SOSYS / Mojaloop (REST)</span>
                <span class="badge badge-etl">SQL reconciled_view</span>
                <span id="mode-badge" style="margin-left:10px;"></span>
            </p>

            <div class="toolbar">
                <button class="btn-primary" onclick="runPipeline()">Run Pipeline Now</button>
                <button class="btn-secondary" onclick="loadData()">Refresh Dashboard</button>
                <a class="btn-warning" href="/api/export-csv">Export CSV</a>
            </div>

            <div id="pipeline-status" class="synced-info"></div>
            <div id="last-synced" class="synced-info">Last synced: Never</div>

            <div class="stats-bar" id="stats-bar">
                <div class="stat-card stat-green">
                    <span class="number" id="count-reconciled">0</span>
                    <span class="label">Reconciled</span>
                </div>
                <div class="stat-card stat-red">
                    <span class="number" id="count-missing">0</span>
                    <span class="label">Missing Payment</span>
                </div>
                <div class="stat-card stat-red">
                    <span class="number" id="count-mismatch">0</span>
                    <span class="label">Amount Mismatch</span>
                </div>
                <div class="stat-card stat-yellow">
                    <span class="number" id="count-pending">0</span>
                    <span class="label">Pending</span>
                </div>
                <div class="stat-card stat-highlight">
                    <span class="number" id="npr-unreconciled">NPR 0</span>
                    <span class="label">Unreconciled Total</span>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Claim Code</th>
                        <th>Hospital</th>
                        <th>Claimed (NPR)</th>
                        <th>Paid (NPR)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="5" style="text-align:center; padding:30px;">Click <strong>Refresh Dashboard</strong> to load data...</td></tr>
                </tbody>
            </table>
        </div>

        <script>
            async function runPipeline() {{
                document.getElementById('pipeline-status').innerHTML = 'Running ETL pipeline (extract OpenIMIS -> extract SOSYS -> reconcile)...';
                document.getElementById('pipeline-status').style.color = '#2980b9';
                try {{
                    const resp = await fetch('/api/run-pipeline', {{ method: 'POST' }});
                    const result = await resp.json();
                    if (result.status === 'ok') {{
                        document.getElementById('pipeline-status').innerHTML = 'Pipeline completed successfully!';
                        document.getElementById('pipeline-status').style.color = '#27ae60';
                        document.getElementById('last-synced').innerHTML = 'Last synced: ' + new Date(result.last_synced).toLocaleString();
                        loadData();
                    }} else {{
                        document.getElementById('pipeline-status').innerHTML = 'Pipeline error: ' + result.message;
                        document.getElementById('pipeline-status').style.color = '#e74c3c';
                    }}
                }} catch(e) {{
                    document.getElementById('pipeline-status').innerHTML = 'Failed to run pipeline: ' + e.message;
                    document.getElementById('pipeline-status').style.color = '#e74c3c';
                }}
            }}

            async function loadData() {{
                document.getElementById('pipeline-status').innerHTML = 'Loading reconciled view from database...';
                const response = await fetch('/api/reconcile');
                const result = await response.json();
                const tbody = document.getElementById('data-body');
                tbody.innerHTML = '';

                let counts = {{RECONCILED: 0, MISSING_PAYMENT: 0, AMOUNT_MISMATCH: 0, STATUS_PENDING: 0}};

                result.data.forEach(row => {{
                    counts[row.reconciliation_status]++;

                    let cls = 'status-reconciled';
                    if (row.reconciliation_status === 'STATUS_PENDING') cls = 'status-pending';
                    else if (row.reconciliation_status === 'AMOUNT_MISMATCH') cls = 'status-mismatch';
                    else if (row.reconciliation_status === 'MISSING_PAYMENT') cls = 'status-missing';

                    tbody.innerHTML += `
                        <tr>
                            <td><strong>${{row.claim_code}}</strong></td>
                            <td>${{row.hospital_name}}</td>
                            <td>${{row.amount_claimed}}</td>
                            <td>${{row.amount_paid}}</td>
                            <td><span class="status-badge ${{cls}}">${{row.reconciliation_status}}</span></td>
                        </tr>
                    `;
                }});

                document.getElementById('count-reconciled').textContent = counts.RECONCILED;
                document.getElementById('count-missing').textContent = counts.MISSING_PAYMENT;
                document.getElementById('count-mismatch').textContent = counts.AMOUNT_MISMATCH;
                document.getElementById('count-pending').textContent = counts.STATUS_PENDING;

                if (result.stats) {{
                    const amt = result.stats.unreconciled_amount_npr;
                    document.getElementById('npr-unreconciled').textContent = 'NPR ' + amt.toLocaleString('en-IN');
                }}

                document.getElementById('pipeline-status').innerHTML = 'Loaded ' + result.data.length + ' claims.';
                document.getElementById('pipeline-status').style.color = '#666';

                const syncResp = await fetch('/api/last-synced');
                const syncResult = await syncResp.json();
                if (syncResult.last_synced) {{
                    document.getElementById('last-synced').innerHTML = 'Last synced: ' + new Date(syncResult.last_synced).toLocaleString();
                }}
            }}

            loadData();
        </script>
    </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTML_TEMPLATE
