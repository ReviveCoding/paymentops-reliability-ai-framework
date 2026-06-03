from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class CaseRequest(BaseModel):
    case_id: str
    text: str
    amount: float = 0.0
    payment_status: str = "NA"
    exception_type: str = "none"

class CaseResponse(BaseModel):
    case_id: str
    risk_score: float
    final_action: str
    summary: str
