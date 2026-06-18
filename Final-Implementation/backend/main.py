"""Samanvaya — Standalone Payment Execution Engine for OpenIMIS."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base, sync_demo_schema
from routers import claims, batches, transactions, webhooks, dashboard, reconciliation, demo
from services.poller import start_poller, stop_poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    sync_demo_schema()
    start_poller()
    yield
    # Shutdown
    stop_poller()


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
