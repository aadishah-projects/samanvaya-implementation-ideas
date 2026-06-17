from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class UploadSummary(BaseModel):
    source: str
    filename: str | None = None
    records: int
    stored: int
    reconciliation: dict[str, Any]
