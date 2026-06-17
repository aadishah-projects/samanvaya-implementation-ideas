from __future__ import annotations

import pathlib

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .services import (
    fetch_dashboard,
    get_claim_detail,
    get_hospital_detail,
    ingest_openimis,
    ingest_sosys,
    list_claims,
    list_hospitals,
    parse_openimis_bundle,
    parse_sosys_payload,
    reset_and_seed_demo_data,
    run_reconciliation,
    send_sms_mock,
)

app = FastAPI(title="Samanvaya API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    dashboard = fetch_dashboard()
    if dashboard["metrics"]["totalClaims"] == 0:
        reset_and_seed_demo_data(500)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "samanvaya"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return fetch_dashboard()


@app.get("/api/claims")
def claims(status: str | None = None, search: str | None = None) -> dict:
    items = list_claims(status=status, search=search)
    return {"items": items, "total": len(items)}


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: str) -> dict:
    detail = get_claim_detail(claim_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Claim not found")
    return detail


@app.post("/api/upload/openimis")
async def upload_openimis(file: UploadFile = File(...)) -> dict:
    raw = (await file.read()).decode("utf-8")
    try:
        claims, count = parse_openimis_bundle(raw, file.filename or "openimis.json")
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Invalid OpenIMIS JSON: {error}") from error
    result = ingest_openimis(claims, file.filename or "openimis.json")
    reconcile = run_reconciliation()
    return {"source": "openimis", "filename": file.filename, "records": count, "stored": result["records"], "reconciliation": reconcile}


@app.post("/api/upload/sosys")
async def upload_sosys(file: UploadFile = File(...)) -> dict:
    raw = (await file.read()).decode("utf-8")
    try:
        payments, count = parse_sosys_payload(raw)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Invalid SOSYS payload: {error}") from error
    result = ingest_sosys(payments, file.filename or "sosys.csv")
    reconcile = run_reconciliation()
    return {"source": "sosys", "filename": file.filename, "records": count, "stored": result["records"], "reconciliation": reconcile}


@app.post("/api/reconcile/run")
def reconcile_run() -> dict:
    return run_reconciliation()


@app.post("/api/synthetic/generate")
def synthetic_generate(count: int = 500) -> dict:
    summary = reset_and_seed_demo_data(count)
    return {"status": "generated", "summary": summary}


@app.get("/api/hospitals")
def hospitals_endpoint() -> dict:
    items = list_hospitals()
    return {"items": items, "total": len(items)}


@app.get("/api/hospitals/{hospital_name}")
def hospital_detail_endpoint(hospital_name: str) -> dict:
    detail = get_hospital_detail(hospital_name)
    if not detail:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return detail


@app.post("/api/claims/{claim_id}/sms")
def sms(claim_id: str) -> dict:
    try:
        return send_sms_mock(claim_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
