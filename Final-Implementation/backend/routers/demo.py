import os

import httpx
from fastapi import APIRouter

from schemas import MockDataGenerateRequest, MockDataGenerateResponse
from seed import seed, seed_mock_data

router = APIRouter(prefix="/api/demo", tags=["Demo"])

MOCK_BANK_URL = os.getenv("MOCK_BANK_URL", "http://localhost:8001")


@router.post("/reset")
def reset_demo():
    """Reset the standalone demo to a known-good state."""
    result = seed(reset=True)
    bank_reset = {"ok": False, "note": "mock_bank_unreachable"}

    try:
        response = httpx.post(f"{MOCK_BANK_URL}/reset", timeout=3.0)
        response.raise_for_status()
        bank_reset = response.json()
    except Exception as exc:
        bank_reset = {"ok": False, "note": str(exc)}

    return {
        "ok": True,
        "database": result,
        "mock_bank": bank_reset,
    }


@router.post("/mock-data", response_model=MockDataGenerateResponse)
def generate_mock_data(req: MockDataGenerateRequest):
    """Generate a larger deterministic demo dataset."""
    result = seed_mock_data(claim_count=req.claim_count, reset=req.reset)
    bank_reset = {"ok": False, "note": "mock_bank_unreachable"}

    try:
        response = httpx.post(f"{MOCK_BANK_URL}/reset", timeout=3.0)
        response.raise_for_status()
        bank_reset = response.json()
    except Exception as exc:
        bank_reset = {"ok": False, "note": str(exc)}

    return MockDataGenerateResponse(
        ok=True,
        claims=result["claims"],
        approved=result["approved"],
        processed=result["processed"],
        historical_transactions=result["transactions"],
        total_approved_amount=result["total_approved_amount"],
        scenario=f"mock_data_{req.claim_count}_claims_bank_reset_{bank_reset.get('ok', False)}",
    )
