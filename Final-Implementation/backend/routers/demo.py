import os

import httpx
from fastapi import APIRouter

from seed import seed

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
