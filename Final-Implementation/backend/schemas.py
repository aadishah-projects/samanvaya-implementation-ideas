from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ── Claims ─────────────────────────────────────────────
class ClaimResponse(BaseModel):
    id: str
    claim_code: str
    health_facility: str
    insuree_name: str
    employer: Optional[str] = None
    scheme: Optional[str] = None
    claimed_date: Optional[str] = None
    review_status: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_date: Optional[str] = None
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
    batch_code: Optional[str] = None
    health_facility: Optional[str] = None
    created_at: datetime
    total_amount: float
    claim_count: int
    status: str

    class Config:
        from_attributes = True


class BatchDetailTransactionResponse(BaseModel):
    id: str
    claim_id: str
    claim_code: Optional[str] = None
    insuree_name: Optional[str] = None
    health_facility: Optional[str] = None
    amount: float
    claimed_amount: Optional[float] = None
    approved_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: str
    gateway_ref_id: Optional[str] = None
    clinical_screening_reasons: Optional[list[str]] = None
    financial_screening_reason: Optional[str] = None
    financial_screening_notes: Optional[str] = None
    financial_screening_completed: bool = False
    retry_count: int
    created_at: datetime
    updated_at: datetime


class BatchDetailResponse(BatchResponse):
    transactions: list[BatchDetailTransactionResponse]


class ClaimReviewRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class ClaimBulkReviewRequest(BaseModel):
    claim_ids: list[str]
    status: str
    notes: Optional[str] = None


class ClaimReviewListResponse(BaseModel):
    id: str
    claim_code: str
    health_facility: str
    insuree_name: str
    claimed_amount: float
    submitted_date: Optional[str] = None
    review_status: Optional[str] = None

    class Config:
        from_attributes = True


class ClaimDetailResponse(ClaimResponse):
    employer_esaid: Optional[str] = None
    ssid: Optional[str] = None
    relation: Optional[str] = None
    visit_from: Optional[str] = None
    visit_to: Optional[str] = None
    visit_type: Optional[str] = None
    claim_administrator: Optional[str] = None
    issued_by: Optional[str] = None
    is_reclaim: bool = False
    explanation: Optional[str] = None
    policy_information: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    account_name: Optional[str] = None
    account_no: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class BatchAutoCreateResponse(BaseModel):
    created_count: int
    total_claims: int
    total_amount: float
    amount_limit: float
    over_limit_claims: list[str]
    batches: list[BatchResponse]


class FinancialScreeningRequest(BaseModel):
    reason: Optional[str] = None
    notes: Optional[str] = None


# ── Transactions ───────────────────────────────────────
class TransactionResponse(BaseModel):
    id: str
    batch_id: str
    claim_id: str
    amount: float
    claimed_amount: Optional[float] = None
    approved_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: str
    idempotency_key: str
    gateway_name: str
    gateway_ref_id: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    health_facility: Optional[str] = None
    claim_code: Optional[str] = None
    insuree_name: Optional[str] = None
    clinical_screening_reasons: Optional[list[str]] = None
    financial_screening_reason: Optional[str] = None
    financial_screening_notes: Optional[str] = None
    financial_screening_completed: bool = False

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
    claimed_amount: Optional[float] = None
    approved_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    batch_code: Optional[str] = None
    gateway_ref_id: Optional[str] = None
    payment_date: Optional[str] = None
    sosys_status: Optional[str] = None
    source: Optional[str] = None
    match_status: str
    issue_type: Optional[str] = None
    notes: Optional[str] = None
    clinical_difference: float = 0.0
    financial_difference: float = 0.0
    total_difference: float = 0.0
    clinical_reasons: Optional[list[str]] = None
    financial_reason: Optional[str] = None
    financial_notes: Optional[str] = None
    financial_screening_completed: bool = False
    resolved: bool

    class Config:
        from_attributes = True


class ReconciliationSummaryResponse(BaseModel):
    matched: int
    unmatched: int
    flagged: int
    total: int
    ghost_payments: int = 0
    missing_in_sosys: int = 0
    missing_payments: int = 0
    amount_mismatches: int = 0
    duplicates: int = 0
    status_mismatches: int = 0


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
