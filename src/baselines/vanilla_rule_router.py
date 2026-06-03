from __future__ import annotations


def route_case_rule(case: dict) -> str:
    text = (case.get("text") or case.get("narrative") or "").lower()
    status = case.get("payment_status", "")
    amount = float(case.get("amount") or 0.0)
    exception = case.get("exception_type", "")
    if status in {"RJCT", "PDNG"} or exception in {"amount_limit", "status_mismatch", "manual_compliance_review"}:
        return "analyst_review" if exception != "manual_compliance_review" else "compliance_review"
    if amount > 25000 or any(w in text for w in ["fraud", "unauthorized", "wrong recipient", "threatened"]):
        return "analyst_review"
    return "auto_resolve"
