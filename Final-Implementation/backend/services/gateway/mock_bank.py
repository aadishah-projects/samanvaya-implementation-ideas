"""MockBank gateway adapter — talks to the local mock bank server."""
import os

import httpx
from .base import BasePaymentGateway, PayoutResponse

MOCK_BANK_URL = os.getenv("MOCK_BANK_URL", "http://localhost:8001")


class MockBankGateway(BasePaymentGateway):

    def initiate_payout(
        self,
        ref_id: str,
        amount: float,
        recipient: str,
        metadata: dict | None = None,
    ) -> PayoutResponse:
        payload = {
            "ref_id": ref_id,
            "amount": amount,
            "recipient": recipient,
            "metadata": metadata or {},
        }
        try:
            resp = httpx.post(f"{MOCK_BANK_URL}/payout", json=payload, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return PayoutResponse(
                success=True,
                gateway_ref=data["gateway_ref_id"],
                status=data["status"],  # INITIATED
                raw_response=data,
                request_payload=payload,
            )
        except Exception as e:
            return PayoutResponse(
                success=False,
                gateway_ref="",
                status="FAILED",
                raw_response={"error": str(e)},
                request_payload=payload,
                error_msg=str(e),
            )

    def verify_status(self, gateway_ref: str) -> PayoutResponse:
        try:
            resp = httpx.get(f"{MOCK_BANK_URL}/status/{gateway_ref}", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return PayoutResponse(
                success=data["status"] == "SUCCESS",
                gateway_ref=gateway_ref,
                status=data["status"],
                raw_response=data,
                request_payload={},
            )
        except Exception as e:
            return PayoutResponse(
                success=False,
                gateway_ref=gateway_ref,
                status="UNKNOWN",
                raw_response={"error": str(e)},
                request_payload={},
                error_msg=str(e),
            )

    def create_ghost_payment(self, payload: dict) -> dict:
        try:
            resp = httpx.post(f"{MOCK_BANK_URL}/ghost-payment", json=payload, timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"ok": False, "error": str(e), "request_payload": payload}
