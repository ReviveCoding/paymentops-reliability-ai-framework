from __future__ import annotations


def permission_gate(action: str, risk_score: float, evidence_slots: set[str]) -> dict:
    if action in {"block_payment", "compliance_escalation"} and risk_score < 0.65:
        return {"allowed": False, "reason": "High-impact action requires risk_score >= 0.65."}
    if action == "auto_resolve" and risk_score >= 0.50:
        return {"allowed": False, "reason": "Auto-resolution blocked for non-low-risk cases."}
    if "required_action" not in evidence_slots:
        return {"allowed": False, "reason": "Required action evidence slot missing."}
    return {"allowed": True, "reason": "Permission gate passed."}
