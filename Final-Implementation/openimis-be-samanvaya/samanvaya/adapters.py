"""
Payment Gateway Adapters — Strategy Pattern.
Swap MockBank for eSewa/ConnectIPS with zero logic changes.
"""
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


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
    def initiate_payout(self, ref_id: str, amount: float, recipient: str) -> PayoutResponse:
        pass

    @abstractmethod
    def verify_status(self, gateway_ref: str) -> PayoutResponse:
        pass


class MockBankGateway(BasePaymentGateway):
    """Mock bank adapter — talks to localhost:8001 for demo."""

    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url

    def initiate_payout(self, ref_id, amount, recipient):
        payload = {"ref_id": ref_id, "amount": float(amount), "recipient": recipient}
        try:
            resp = httpx.post(f"{self.base_url}/payout", json=payload, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return PayoutResponse(
                success=True, gateway_ref=data["gateway_ref_id"],
                status=data["status"], raw_response=data, request_payload=payload,
            )
        except Exception as e:
            logger.error(f"MockBank payout failed: {e}")
            return PayoutResponse(
                success=False, gateway_ref="", status="FAILED",
                raw_response={"error": str(e)}, request_payload=payload, error_msg=str(e),
            )

    def verify_status(self, gateway_ref):
        try:
            resp = httpx.get(f"{self.base_url}/status/{gateway_ref}", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return PayoutResponse(
                success=data["status"] == "SUCCESS", gateway_ref=gateway_ref,
                status=data["status"], raw_response=data, request_payload={},
            )
        except Exception as e:
            return PayoutResponse(
                success=False, gateway_ref=gateway_ref, status="UNKNOWN",
                raw_response={"error": str(e)}, request_payload={}, error_msg=str(e),
            )


class ESewaGateway(BasePaymentGateway):
    """eSewa stub — swap in for production."""

    def initiate_payout(self, ref_id, amount, recipient):
        raise NotImplementedError(
            "eSewa gateway not implemented. "
            "For production: implement HMAC signing + FTPL payload format."
        )

    def verify_status(self, gateway_ref):
        raise NotImplementedError("eSewa status verification not implemented.")


def get_active_gateway():
    """Factory: return the active gateway adapter based on GatewayConfig."""
    try:
        from .models import GatewayConfig
        config = GatewayConfig.objects.filter(is_active=True).first()
        if config and config.name == "mock_bank":
            base_url = config.config.get("base_url", "http://localhost:8001")
            return MockBankGateway(base_url)
        elif config and config.name == "esewa":
            return ESewaGateway()
    except Exception:
        pass
    return MockBankGateway()
