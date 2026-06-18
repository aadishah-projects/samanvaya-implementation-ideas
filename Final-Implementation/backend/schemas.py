from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ── Claims ─────────────────────────────────────────────
class ClaimResponse(BaseModel):
    id: str
    claim_code: str
    health_facility: str
    insuree_name: str
    claimed_amount: float
    approved_amount: float
    status: str
    approved_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Batches ────────────────────────────────────────────
class BatchCreateRequest(BaseModel):
    claim_ids: list[str]


class BatchAutoCreateRequest(BaseModel):
    amount_limit: float = 100000.0


class BatchResponse(BaseModel):
    id: str
    created_at: datetime
    total_amount: float
    claim_count: int
    status: str

    class Config:
        from_attributes = True


class BatchAutoCreateResponse(BaseModel):
    created_count: int
    total_claims: int
    total_amount: float
    amount_limit: float
    over_limit_claims: list[str]
    batches: list[BatchResponse]


# ── Transactions ───────────────────────────────────────
class TransactionResponse(BaseModel):
    id: str
    batch_id: str
    claim_id: str
    amount: float
    status: str
    idempotency_key: str
    gateway_name: str
    gateway_ref_id: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    health_facility: Optional[str] = None
    claim_code: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionDetailResponse(TransactionResponse):
    raw_request_log: Optional[dict] = None
    raw_response_log: Optional[dict] = None
    webhook_received_at: Optional[datetime] = None


# ── Dashboard ──────────────────────────────────────────
class DashboardSummaryResponse(BaseModel):
    total_disbursed: float
    success_rate: float
    pending_count: int
    failed_count: int
    success_count: int
    total_transactions: int


class DailyVolume(BaseModel):
    date: str
    total_amount: float
    count: int


# ── Reconciliation ─────────────────────────────────────
class ReconciliationResultResponse(BaseModel):
    id: str
    claim_code: str
    health_facility: str
    amount: float
    payment_date: Optional[str] = None
    sosys_status: Optional[str] = None
    match_status: str
    notes: Optional[str] = None
    resolved: bool

    class Config:
        from_attributes = True


class ReconciliationSummaryResponse(BaseModel):
    matched: int
    unmatched: int
    flagged: int
    total: int


# Demo data
class MockDataGenerateRequest(BaseModel):
    claim_count: int = 60
    reset: bool = True


class MockDataGenerateResponse(BaseModel):
    ok: bool
    claims: int
    approved: int
    processed: int
    historical_transactions: int
    total_approved_amount: float
    scenario: str


# ── Webhook ────────────────────────────────────────────
class WebhookPayload(BaseModel):
    gateway_ref_id: str
    status: str  # SUCCESS or FAILED
    message: Optional[str] = None
