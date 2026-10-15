from __future__ import annotations

from math import isfinite
from numbers import Real

_ALLOWED_ACTIONS = frozenset({
    "auto_resolve",
    "analyst_review",
    "block_payment",
    "compliance_escalation",
})


def permission_gate(action: str, risk_score: float, evidence_slots: set[str]) -> dict:
    """Deny unsupported actions or invalid scores before policy comparisons."""
    if not isinstance(action, str) or action not in _ALLOWED_ACTIONS:
        return {"allowed": False, "reason": "Action is not permitted by this gate."}
    if (
        isinstance(risk_score, bool)
        or not isinstance(risk_score, Real)
        or not isfinite(risk_score)
        or not 0.0 <= risk_score <= 1.0
    ):
        return {"allowed": False, "reason": "Risk score must be finite and within [0, 1]."}
    if action in {"block_payment", "compliance_escalation"} and risk_score < 0.65:
        return {"allowed": False, "reason": "High-impact action requires risk_score >= 0.65."}
    if action == "auto_resolve" and risk_score >= 0.50:
        return {"allowed": False, "reason": "Auto-resolution blocked for non-low-risk cases."}
    if "required_action" not in evidence_slots:
        return {"allowed": False, "reason": "Required action evidence slot missing."}
    return {"allowed": True, "reason": "Permission gate passed."}
