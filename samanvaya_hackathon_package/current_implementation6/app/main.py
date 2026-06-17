from datetime import datetime, timezone
from io import StringIO
import csv

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
from sqlalchemy import create_engine, text

try:
    from .config import DB_CONFIG, USE_LIVE_API
except ImportError:
    from config import DB_CONFIG, USE_LIVE_API


app = FastAPI(title="Samanvaya Reconciliation Dashboard")

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
engine = create_engine(DATABASE_URL)
last_synced: datetime | None = None

ISSUE_STATUSES = {
    "MISSING_PAYMENT",
    "AMOUNT_MISMATCH",
    "STATUS_PENDING",
    "DUPLICATE_PAYMENT",
}


def get_db_url():
    return DATABASE_URL


def dataframe_records(df: pd.DataFrame) -> list[dict]:
    df = df.where(pd.notna(df), None)
    for column in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df[column] = df[column].astype(str)
    return df.to_dict(orient="records")


def ensure_pipeline_runs_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id SERIAL PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                status TEXT NOT NULL,
                source_mode TEXT NOT NULL,
                claims_extracted INT DEFAULT 0,
                payments_extracted INT DEFAULT 0,
                reconciled_count INT DEFAULT 0,
                unreconciled_count INT DEFAULT 0,
                unreconciled_amount_npr NUMERIC DEFAULT 0,
                message TEXT
            );
        """))


def run_reconciliation():
    query = """
        SELECT
            claim_code,
            hospital_name,
            COALESCE(district, 'Unknown') AS district,
            amount_claimed,
            amount_paid,
            COALESCE(amount_variance, amount_claimed - amount_paid) AS amount_variance,
            COALESCE(payment_status, 'unknown') AS payment_status,
            COALESCE(payment_count, 0) AS payment_count,
            reconciliation_status,
            COALESCE(reconciliation_reason, 'No reason recorded.') AS reconciliation_reason,
            COALESCE(risk_level, 'LOW') AS risk_level,
            updated_at
        FROM reconciled_view
        ORDER BY
            CASE COALESCE(risk_level, 'LOW')
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                ELSE 3
            END,
            claim_code;
    """
    df = pd.read_sql(query, engine)
    return dataframe_records(df)


def money(value) -> float:
    if value in (None, "N/A", ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_stats(data: list[dict]) -> dict:
    status_counts: dict[str, int] = {}
    hospital_issue_counts: dict[str, int] = {}
    district_issue_counts: dict[str, int] = {}

    for row in data:
        status = row.get("reconciliation_status") or "UNKNOWN"
        status_counts[status] = status_counts.get(status, 0) + 1

        if status in ISSUE_STATUSES:
            hospital = row.get("hospital_name") or "Unknown"
            district = row.get("district") or "Unknown"
            hospital_issue_counts[hospital] = hospital_issue_counts.get(hospital, 0) + 1
            district_issue_counts[district] = district_issue_counts.get(district, 0) + 1

    total_claims = len(data)
    reconciled = status_counts.get("RECONCILED", 0)
    issue_rows = [row for row in data if row.get("reconciliation_status") in ISSUE_STATUSES]
    total_unreconciled = len(issue_rows)
    unreconciled_amount = sum(money(row.get("amount_claimed")) for row in issue_rows)
    total_variance = sum(abs(money(row.get("amount_variance"))) for row in issue_rows)
    quality_score = round((reconciled / total_claims) * 100, 1) if total_claims else 0

    top_hospitals = [
        {"name": name, "issues": count}
        for name, count in sorted(hospital_issue_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    district_hotspots = [
        {"name": name, "issues": count}
        for name, count in sorted(district_issue_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return {
        "total_claims": total_claims,
        "total_reconciled": reconciled,
        "total_unreconciled": total_unreconciled,
        "unreconciled_amount_npr": round(unreconciled_amount, 2),
        "total_variance_npr": round(total_variance, 2),
        "quality_score": quality_score,
        "status_counts": status_counts,
        "top_risk_hospitals": top_hospitals,
        "district_hotspots": district_hotspots,
    }


def table_count(table_name: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()


def create_pipeline_run() -> int | None:
    try:
        ensure_pipeline_runs_table()
        with engine.begin() as conn:
            return conn.execute(
                text("""
                    INSERT INTO pipeline_runs (status, source_mode, message)
                    VALUES (:status, :source_mode, :message)
                    RETURNING id;
                """),
                {
                    "status": "RUNNING",
                    "source_mode": "LIVE_API" if USE_LIVE_API else "MOCK_API",
                    "message": "Pipeline started.",
                },
            ).scalar_one()
    except Exception:
        return None


def finish_pipeline_run(run_id: int | None, status: str, message: str, stats: dict | None = None):
    if run_id is None:
        return

    try:
        stats = stats or {}
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE pipeline_runs
                    SET
                        finished_at = CURRENT_TIMESTAMP,
                        status = :status,
                        claims_extracted = :claims_extracted,
                        payments_extracted = :payments_extracted,
                        reconciled_count = :reconciled_count,
                        unreconciled_count = :unreconciled_count,
                        unreconciled_amount_npr = :unreconciled_amount_npr,
                        message = :message
                    WHERE id = :run_id;
                """),
                {
                    "run_id": run_id,
                    "status": status,
                    "claims_extracted": stats.get("claims_extracted", 0),
                    "payments_extracted": stats.get("payments_extracted", 0),
                    "reconciled_count": stats.get("total_reconciled", 0),
                    "unreconciled_count": stats.get("total_unreconciled", 0),
                    "unreconciled_amount_npr": stats.get("unreconciled_amount_npr", 0),
                    "message": message,
                },
            )
    except Exception:
        pass


@app.get("/api/last-synced")
def get_last_synced():
    return {"last_synced": last_synced.isoformat() if last_synced else None}


@app.post("/api/run-pipeline")
def run_pipeline():
    global last_synced
    run_id = create_pipeline_run()

    try:
        try:
            from .extract_openimis import extract_and_load as extract_openimis
            from .extract_sosys import extract_and_load as extract_sosys
            from .reconcile_sql import run_sql_reconciliation
        except ImportError:
            from extract_openimis import extract_and_load as extract_openimis
            from extract_sosys import extract_and_load as extract_sosys
            from reconcile_sql import run_sql_reconciliation

        extract_openimis()
        extract_sosys()
        run_sql_reconciliation()

        data = run_reconciliation()
        stats = build_stats(data)
        stats["claims_extracted"] = table_count("staging_openimis_claims")
        stats["payments_extracted"] = table_count("staging_sosys_payments")

        last_synced = datetime.now(timezone.utc)
        finish_pipeline_run(run_id, "SUCCESS", "Pipeline completed successfully.", stats)
        return {
            "status": "ok",
            "message": "Pipeline completed successfully",
            "last_synced": last_synced.isoformat(),
            "stats": stats,
        }
    except Exception as e:
        finish_pipeline_run(run_id, "FAILED", str(e), {})
        return {"status": "error", "message": str(e)}


@app.get("/api/pipeline-runs")
def get_pipeline_runs():
    try:
        ensure_pipeline_runs_table()
        df = pd.read_sql(
            """
            SELECT
                id,
                started_at,
                finished_at,
                status,
                source_mode,
                claims_extracted,
                payments_extracted,
                reconciled_count,
                unreconciled_count,
                unreconciled_amount_npr,
                message
            FROM pipeline_runs
            ORDER BY id DESC
            LIMIT 5;
            """,
            engine,
        )
        return {"data": dataframe_records(df)}
    except Exception as e:
        return {"data": [], "error": str(e)}


@app.get("/api/export-csv")
def export_csv():
    data = run_reconciliation()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "claim_code",
        "district",
        "hospital_name",
        "amount_claimed",
        "amount_paid",
        "amount_variance",
        "payment_status",
        "payment_count",
        "risk_level",
        "reconciliation_status",
        "reconciliation_reason",
    ])
    for row in data:
        writer.writerow([
            row.get("claim_code"),
            row.get("district"),
            row.get("hospital_name"),
            row.get("amount_claimed"),
            row.get("amount_paid"),
            row.get("amount_variance"),
            row.get("payment_status"),
            row.get("payment_count"),
            row.get("risk_level"),
            row.get("reconciliation_status"),
            row.get("reconciliation_reason"),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reconciled_claims.csv"},
    )


@app.get("/api/reconcile")
def get_reconciliation():
    data = run_reconciliation()
    return {"data": data, "stats": build_stats(data)}


live_badge = "LIVE API" if USE_LIVE_API else "MOCK API"
mode_class = "badge-live" if USE_LIVE_API else "badge-mock"

HTML_TEMPLATE = """
<html>
    <head>
        <title>Samanvaya: OpenIMIS + SOSYS Reconciliation Dashboard</title>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 24px;
                background: #f4f6f8;
                color: #25313d;
            }
            .container { max-width: 1320px; margin: 0 auto; }
            h1 {
                color: #1f2d3a;
                border-bottom: 3px solid #2878b5;
                padding-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
                font-size: 28px;
            }
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 700;
                color: white;
                vertical-align: middle;
            }
            .badge-live { background: #1f8f52; }
            .badge-mock { background: #c76a16; }
            .badge-source { background: #52616f; }
            .badge-risk-high { background: #c0392b; }
            .badge-risk-medium { background: #d68910; }
            .badge-risk-low { background: #1e8449; }
            .toolbar, .filters {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                align-items: center;
                margin: 18px 0;
            }
            .toolbar button, .toolbar a {
                padding: 10px 16px;
                font-size: 14px;
                cursor: pointer;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                text-decoration: none;
                display: inline-block;
            }
            .btn-primary { background: #1f8f52; color: white; }
            .btn-secondary { background: #2878b5; color: white; }
            .btn-warning { background: #d68910; color: white; }
            input, select {
                border: 1px solid #c9d1d9;
                border-radius: 6px;
                padding: 9px 10px;
                font-size: 14px;
                min-height: 38px;
                background: white;
            }
            .status-line { font-size: 13px; color: #52616f; margin: 8px 0; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(5, minmax(150px, 1fr));
                gap: 12px;
                margin: 16px 0;
            }
            .stat-card {
                background: white;
                border-radius: 8px;
                padding: 14px 16px;
                border: 1px solid #e0e5eb;
                box-shadow: 0 1px 2px rgba(20, 30, 40, 0.04);
            }
            .stat-card .number {
                font-size: 25px;
                font-weight: 800;
                display: block;
                color: #1f2d3a;
                line-height: 1.2;
            }
            .stat-card .label {
                font-size: 11px;
                text-transform: uppercase;
                color: #6b7785;
                margin-top: 5px;
                letter-spacing: 0.04em;
            }
            .stat-green .number { color: #1f8f52; }
            .stat-red .number { color: #c0392b; }
            .stat-yellow .number { color: #d68910; }
            .stat-blue .number { color: #2878b5; }
            .operations-grid {
                display: grid;
                grid-template-columns: 1fr 1fr 1.4fr;
                gap: 12px;
                margin: 16px 0;
            }
            .panel {
                background: white;
                border: 1px solid #e0e5eb;
                border-radius: 8px;
                padding: 14px 16px;
            }
            .panel h2 {
                font-size: 15px;
                margin: 0 0 10px;
                color: #1f2d3a;
            }
            .mini-list {
                margin: 0;
                padding: 0;
                list-style: none;
                font-size: 13px;
            }
            .mini-list li {
                display: flex;
                justify-content: space-between;
                gap: 10px;
                padding: 6px 0;
                border-bottom: 1px solid #edf1f5;
            }
            .mini-list li:last-child { border-bottom: none; }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-top: 10px;
                background: white;
                border: 1px solid #e0e5eb;
                border-radius: 8px;
                overflow: hidden;
            }
            th, td {
                border-bottom: 1px solid #edf1f5;
                padding: 10px 12px;
                text-align: left;
                font-size: 13px;
                vertical-align: top;
            }
            th {
                background-color: #263746;
                color: white;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.04em;
            }
            tbody tr:hover { background: #f8fbfd; }
            .reason { color: #52616f; max-width: 360px; }
            .status-badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
                white-space: nowrap;
            }
            .status-reconciled { background: #dff3e8; color: #145a32; }
            .status-missing, .status-mismatch, .status-duplicate { background: #fde3df; color: #922b21; }
            .status-pending { background: #fff1cc; color: #8a5a00; }
            @media (max-width: 900px) {
                body { padding: 14px; }
                .stats-grid, .operations-grid { grid-template-columns: 1fr; }
                table { display: block; overflow-x: auto; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                Samanvaya Reconciliation Dashboard
                <span class="badge __MODE_CLASS__">__LIVE_BADGE__</span>
            </h1>
            <p>
                <span class="badge badge-source">OpenIMIS GraphQL</span>
                <span class="badge badge-source">SOSYS / Mojaloop REST</span>
                <span class="badge badge-source">PostgreSQL SQL engine</span>
            </p>

            <div class="toolbar">
                <button class="btn-primary" onclick="runPipeline()">Run Pipeline Now</button>
                <button class="btn-secondary" onclick="loadData()">Refresh Dashboard</button>
                <a class="btn-warning" href="/api/export-csv">Export Evidence CSV</a>
            </div>

            <div id="pipeline-status" class="status-line"></div>
            <div id="last-synced" class="status-line">Last synced: Never</div>

            <div class="stats-grid">
                <div class="stat-card stat-blue">
                    <span class="number" id="total-claims">0</span>
                    <span class="label">Total Claims</span>
                </div>
                <div class="stat-card stat-green">
                    <span class="number" id="count-reconciled">0</span>
                    <span class="label">Reconciled</span>
                </div>
                <div class="stat-card stat-red">
                    <span class="number" id="count-issues">0</span>
                    <span class="label">Open Issues</span>
                </div>
                <div class="stat-card stat-yellow">
                    <span class="number" id="quality-score">0%</span>
                    <span class="label">Reconciliation Quality</span>
                </div>
                <div class="stat-card stat-red">
                    <span class="number" id="npr-unreconciled">NPR 0</span>
                    <span class="label">Unreconciled NPR</span>
                </div>
            </div>

            <div class="stats-grid">
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
                <div class="stat-card stat-red">
                    <span class="number" id="count-duplicate">0</span>
                    <span class="label">Duplicate Payment</span>
                </div>
                <div class="stat-card stat-blue">
                    <span class="number" id="variance-total">NPR 0</span>
                    <span class="label">Total Variance</span>
                </div>
            </div>

            <div class="operations-grid">
                <div class="panel">
                    <h2>Risk Hospitals</h2>
                    <ul class="mini-list" id="top-hospitals"><li><span>No issues loaded</span><strong>0</strong></li></ul>
                </div>
                <div class="panel">
                    <h2>District Hotspots</h2>
                    <ul class="mini-list" id="district-hotspots"><li><span>No issues loaded</span><strong>0</strong></li></ul>
                </div>
                <div class="panel">
                    <h2>Recent Pipeline Runs</h2>
                    <ul class="mini-list" id="pipeline-runs"><li><span>No runs yet</span><strong>-</strong></li></ul>
                </div>
            </div>

            <div class="filters">
                <select id="status-filter" onchange="renderTable()">
                    <option value="ALL">All statuses</option>
                    <option value="RECONCILED">Reconciled</option>
                    <option value="MISSING_PAYMENT">Missing payment</option>
                    <option value="AMOUNT_MISMATCH">Amount mismatch</option>
                    <option value="STATUS_PENDING">Pending</option>
                    <option value="DUPLICATE_PAYMENT">Duplicate payment</option>
                </select>
                <input id="search-box" oninput="renderTable()" placeholder="Search claim, hospital, or district" />
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Claim</th>
                        <th>District</th>
                        <th>Hospital</th>
                        <th>Claimed</th>
                        <th>Paid</th>
                        <th>Variance</th>
                        <th>Risk</th>
                        <th>Status</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="9" style="text-align:center; padding:30px;">Loading reconciled claims...</td></tr>
                </tbody>
            </table>
        </div>

        <script>
            let currentRows = [];

            function escapeHtml(value) {
                return String(value ?? '')
                    .replaceAll('&', '&amp;')
                    .replaceAll('<', '&lt;')
                    .replaceAll('>', '&gt;')
                    .replaceAll('"', '&quot;')
                    .replaceAll("'", '&#039;');
            }

            function money(value) {
                const number = Number(value || 0);
                return 'NPR ' + number.toLocaleString('en-IN', { maximumFractionDigits: 2 });
            }

            function statusClass(status) {
                if (status === 'RECONCILED') return 'status-reconciled';
                if (status === 'STATUS_PENDING') return 'status-pending';
                if (status === 'DUPLICATE_PAYMENT') return 'status-duplicate';
                if (status === 'AMOUNT_MISMATCH') return 'status-mismatch';
                return 'status-missing';
            }

            function riskClass(risk) {
                if (risk === 'HIGH') return 'badge-risk-high';
                if (risk === 'MEDIUM') return 'badge-risk-medium';
                return 'badge-risk-low';
            }

            function renderMiniList(id, rows, emptyLabel) {
                const element = document.getElementById(id);
                if (!rows || rows.length === 0) {
                    element.innerHTML = `<li><span>${emptyLabel}</span><strong>0</strong></li>`;
                    return;
                }
                element.innerHTML = rows.map(row => `
                    <li><span>${escapeHtml(row.name)}</span><strong>${row.issues}</strong></li>
                `).join('');
            }

            function renderTable() {
                const tbody = document.getElementById('data-body');
                const statusFilter = document.getElementById('status-filter').value;
                const search = document.getElementById('search-box').value.trim().toLowerCase();

                const rows = currentRows.filter(row => {
                    const matchesStatus = statusFilter === 'ALL' || row.reconciliation_status === statusFilter;
                    const haystack = `${row.claim_code} ${row.hospital_name} ${row.district}`.toLowerCase();
                    const matchesSearch = !search || haystack.includes(search);
                    return matchesStatus && matchesSearch;
                });

                if (rows.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px;">No matching claims.</td></tr>';
                    return;
                }

                tbody.innerHTML = rows.map(row => `
                    <tr>
                        <td><strong>${escapeHtml(row.claim_code)}</strong></td>
                        <td>${escapeHtml(row.district)}</td>
                        <td>${escapeHtml(row.hospital_name)}</td>
                        <td>${money(row.amount_claimed)}</td>
                        <td>${money(row.amount_paid)}</td>
                        <td>${money(row.amount_variance)}</td>
                        <td><span class="badge ${riskClass(row.risk_level)}">${escapeHtml(row.risk_level)}</span></td>
                        <td><span class="status-badge ${statusClass(row.reconciliation_status)}">${escapeHtml(row.reconciliation_status)}</span></td>
                        <td class="reason">${escapeHtml(row.reconciliation_reason)}</td>
                    </tr>
                `).join('');
            }

            function applyStats(stats) {
                const counts = stats.status_counts || {};
                document.getElementById('total-claims').textContent = stats.total_claims || 0;
                document.getElementById('count-reconciled').textContent = counts.RECONCILED || 0;
                document.getElementById('count-issues').textContent = stats.total_unreconciled || 0;
                document.getElementById('quality-score').textContent = (stats.quality_score || 0) + '%';
                document.getElementById('npr-unreconciled').textContent = money(stats.unreconciled_amount_npr);
                document.getElementById('count-missing').textContent = counts.MISSING_PAYMENT || 0;
                document.getElementById('count-mismatch').textContent = counts.AMOUNT_MISMATCH || 0;
                document.getElementById('count-pending').textContent = counts.STATUS_PENDING || 0;
                document.getElementById('count-duplicate').textContent = counts.DUPLICATE_PAYMENT || 0;
                document.getElementById('variance-total').textContent = money(stats.total_variance_npr);
                renderMiniList('top-hospitals', stats.top_risk_hospitals, 'No risky hospitals');
                renderMiniList('district-hotspots', stats.district_hotspots, 'No district hotspots');
            }

            async function loadRuns() {
                const response = await fetch('/api/pipeline-runs');
                const result = await response.json();
                const element = document.getElementById('pipeline-runs');
                if (!result.data || result.data.length === 0) {
                    element.innerHTML = '<li><span>No runs yet</span><strong>-</strong></li>';
                    return;
                }

                element.innerHTML = result.data.map(run => {
                    const started = run.started_at ? new Date(run.started_at).toLocaleString() : 'Unknown time';
                    return `
                        <li>
                            <span>${escapeHtml(started)} - ${escapeHtml(run.source_mode)}</span>
                            <strong>${escapeHtml(run.status)}</strong>
                        </li>
                    `;
                }).join('');
            }

            async function runPipeline() {
                document.getElementById('pipeline-status').innerHTML = 'Running ETL pipeline: OpenIMIS extract, SOSYS extract, SQL reconcile...';
                document.getElementById('pipeline-status').style.color = '#2878b5';
                try {
                    const resp = await fetch('/api/run-pipeline', { method: 'POST' });
                    const result = await resp.json();
                    if (result.status === 'ok') {
                        document.getElementById('pipeline-status').innerHTML = 'Pipeline completed successfully.';
                        document.getElementById('pipeline-status').style.color = '#1f8f52';
                        document.getElementById('last-synced').innerHTML = 'Last synced: ' + new Date(result.last_synced).toLocaleString();
                        await loadData();
                    } else {
                        document.getElementById('pipeline-status').innerHTML = 'Pipeline error: ' + escapeHtml(result.message);
                        document.getElementById('pipeline-status').style.color = '#c0392b';
                    }
                    await loadRuns();
                } catch(e) {
                    document.getElementById('pipeline-status').innerHTML = 'Failed to run pipeline: ' + escapeHtml(e.message);
                    document.getElementById('pipeline-status').style.color = '#c0392b';
                }
            }

            async function loadData() {
                document.getElementById('pipeline-status').innerHTML = 'Loading reconciled view from PostgreSQL...';
                try {
                    const response = await fetch('/api/reconcile');
                    const result = await response.json();
                    currentRows = result.data || [];
                    applyStats(result.stats || {});
                    renderTable();
                    document.getElementById('pipeline-status').innerHTML = 'Loaded ' + currentRows.length + ' claims.';
                    document.getElementById('pipeline-status').style.color = '#52616f';

                    const syncResp = await fetch('/api/last-synced');
                    const syncResult = await syncResp.json();
                    if (syncResult.last_synced) {
                        document.getElementById('last-synced').innerHTML = 'Last synced: ' + new Date(syncResult.last_synced).toLocaleString();
                    }
                    await loadRuns();
                } catch(e) {
                    document.getElementById('pipeline-status').innerHTML = 'Could not load dashboard data: ' + escapeHtml(e.message);
                    document.getElementById('pipeline-status').style.color = '#c0392b';
                }
            }

            loadData();
        </script>
    </body>
</html>
"""

HTML_TEMPLATE = (
    HTML_TEMPLATE
    .replace("__LIVE_BADGE__", live_badge)
    .replace("__MODE_CLASS__", mode_class)
)


@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTML_TEMPLATE
