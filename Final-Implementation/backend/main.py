"""Samanvaya — Standalone Payment Execution Engine for OpenIMIS."""
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from database import engine, Base, SessionLocal, sync_demo_schema
from models import Claim, ClaimStatus, PaymentBatch, PaymentTransaction, SOSYSLegacyLog
from routers import claims, batches, transactions, webhooks, dashboard, reconciliation, demo
from services.poller import start_poller, stop_poller

MOCK_BANK_URL = os.getenv("MOCK_BANK_URL", "http://localhost:8001")
DEMO_RESET_ON_STARTUP = os.getenv("SAMANVAYA_DEMO_RESET_ON_STARTUP", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    sync_demo_schema()
    if DEMO_RESET_ON_STARTUP:
        reset_demo_runtime_state()
        reset_mock_bank_runtime_state()
    start_poller()
    yield
    # Shutdown
    stop_poller()


def reset_demo_runtime_state() -> None:
    """Clear runtime ledgers so every backend restart starts from a clean demo slate."""
    db = SessionLocal()
    try:
        db.query(PaymentTransaction).delete(synchronize_session=False)
        db.query(PaymentBatch).delete(synchronize_session=False)
        db.query(SOSYSLegacyLog).delete(synchronize_session=False)
        (
            db.query(Claim)
            .filter(Claim.status != ClaimStatus.APPROVED.value)
            .update({Claim.status: ClaimStatus.APPROVED.value}, synchronize_session=False)
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_mock_bank_runtime_state() -> None:
    """Best-effort reset of the external demo gateway ledger."""
    try:
        httpx.post(f"{MOCK_BANK_URL}/reset", timeout=2.0)
    except Exception:
        pass


app = FastAPI(
    title="Samanvaya — Payment Execution Engine",
    description=(
        "Standalone payment execution module that replaces SOSYS. "
        "Takes approved health insurance claims, disburses payments through "
        "configurable gateways, tracks every transaction with financial-grade reliability."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(claims.router)
app.include_router(batches.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
app.include_router(reconciliation.router)
app.include_router(demo.router)


@app.get("/")
def root():
    return {
        "name": "Samanvaya",
        "version": "1.0.0",
        "description": "Payment Execution Engine for OpenIMIS",
        "docs": "/docs",
    }
