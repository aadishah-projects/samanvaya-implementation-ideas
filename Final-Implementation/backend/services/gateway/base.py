"""Abstract base class for payment gateway adapters (Strategy Pattern)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PayoutResponse:
    success: bool
    gateway_ref: str
    status: str          # INITIATED, SUCCESS, FAILED, PENDING
    raw_response: dict = field(default_factory=dict)
    request_payload: dict = field(default_factory=dict)
    error_msg: Optional[str] = None


class BasePaymentGateway(ABC):
    @abstractmethod
    def initiate_payout(
        self,
        ref_id: str,
        amount: float,
        recipient: str,
        metadata: dict | None = None,
    ) -> PayoutResponse:
        """Send a payout request to the payment gateway."""
        pass

    @abstractmethod
    def verify_status(self, gateway_ref: str) -> PayoutResponse:
        """Check the current status of a previously initiated payout."""
        pass

    def create_ghost_payment(self, payload: dict) -> dict:
        """Optional demo hook for creating bank-ledger-only anomalies."""
        raise NotImplementedError("This gateway does not support ghost payment simulation.")
