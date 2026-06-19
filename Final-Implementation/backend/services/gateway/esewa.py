"""eSewa gateway stub — swap in for production."""
from .base import BasePaymentGateway, PayoutResponse


class ESewaGateway(BasePaymentGateway):
    """
    Production eSewa integration would:
    1. Format payload to eSewa's FTPL/API standard
    2. Sign the request with HMAC using Merchant Secret Key
    3. POST to eSewa's payout endpoint
    4. Verify webhook signatures on callbacks
    """

    def initiate_payout(
        self,
        ref_id: str,
        amount: float,
        recipient: str,
        metadata: dict | None = None,
    ) -> PayoutResponse:
        raise NotImplementedError(
            "eSewa gateway not implemented. "
            "Use MockBankGateway for development. "
            "For production: implement HMAC signing + FTPL payload format."
        )

    def verify_status(self, gateway_ref: str) -> PayoutResponse:
        raise NotImplementedError(
            "eSewa status verification not implemented. "
            "For production: call eSewa transaction status API with merchant credentials."
        )
