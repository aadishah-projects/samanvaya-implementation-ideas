import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, DateTime, Integer, JSON, Enum,
    ForeignKey, Boolean, Text
)
from sqlalchemy.orm import relationship
from database import Base


# ── Enums ──────────────────────────────────────────────
class ClaimStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    QUEUED = "QUEUED"
    PROCESSED = "PROCESSED"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class BatchStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    DONE = "DONE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class MatchStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    FLAGGED = "FLAGGED"


# ── Models ─────────────────────────────────────────────
class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_code = Column(String, unique=True, nullable=False)
    health_facility = Column(String, nullable=False)
    insuree_name = Column(String, nullable=False)
    claimed_amount = Column(Float, nullable=False)
    approved_amount = Column(Float, nullable=False)
    status = Column(String, default=ClaimStatus.APPROVED.value)
    approved_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transactions = relationship("PaymentTransaction", back_populates="claim")


class PaymentBatch(Base):
    __tablename__ = "payment_batches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_amount = Column(Float, default=0.0)
    claim_count = Column(Integer, default=0)
    status = Column(String, default=BatchStatus.QUEUED.value)

    transactions = relationship("PaymentTransaction", back_populates="batch")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String, ForeignKey("payment_batches.id"), nullable=False)
    claim_id = Column(String, ForeignKey("claims.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default=TransactionStatus.PENDING.value)
    idempotency_key = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    gateway_name = Column(String, default="mock_bank")
    gateway_ref_id = Column(String, unique=True, nullable=True)
    raw_request_log = Column(JSON, nullable=True)
    raw_response_log = Column(JSON, nullable=True)
    webhook_received_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    batch = relationship("PaymentBatch", back_populates="transactions")
    claim = relationship("Claim", back_populates="transactions")


class GatewayConfig(Base):
    __tablename__ = "gateway_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default=dict)


class SOSYSLegacyLog(Base):
    __tablename__ = "sosys_legacy_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_code = Column(String, nullable=False)
    health_facility = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(String, nullable=True)
    sosys_status = Column(String, nullable=True)
    match_status = Column(String, default=MatchStatus.UNMATCHED.value)
    notes = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
